import asyncio
import logging
import uuid
from dataclasses import dataclass

from langchain_core.messages import HumanMessage

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.modules.ingestion.infrastructure.chunk_orm_models import ChildChunkORM
from backend.src.modules.ingestion.infrastructure.orm_models import PaperORM
from backend.src.modules.orchestrator.application.dtos import (
    CreateThreadDTO,
    DeleteThreadDTO,
    GetCitationDetailDTO,
    GetSuggestionsDTO,
    GetThreadMessagesDTO,
    InvokeDTO,
    ListThreadsDTO,
    RenameThreadDTO,
    SendMessageDTO,
)
from backend.src.modules.orchestrator.application.graph import build_graph
from backend.src.modules.orchestrator.domain.entities import ChatMessage, ChatThread
from backend.src.modules.orchestrator.domain.exceptions import ThreadAccessDeniedError, ThreadNotFoundError
from backend.src.modules.orchestrator.domain.repositories import ChatThreadRepository
from backend.src.modules.orchestrator.infrastructure.postgres_checkpointer import get_postgres_checkpointer
from backend.src.modules.orchestrator.infrastructure.repository import PostgresChatThreadRepository
from backend.src.modules.orchestrator.infrastructure.run_registry import create_run, delete_run
from backend.src.modules.workspace.domain.exceptions import ProjectAccessDeniedError, ProjectNotFoundError
from backend.src.modules.workspace.domain.repositories import ProjectRepository
from backend.src.shared.infra.database import AsyncSessionMaker

logger = logging.getLogger(__name__)

# Strong references tới background streaming tasks để event loop không GC chúng giữa chừng.
_background_tasks: set[asyncio.Task] = set()

# Tiêu đề mặc định khi tạo thread mới. Tiêu đề tóm tắt do LLM sinh chỉ ghi đè khi
# thread vẫn còn mang đúng tiêu đề này (tránh đè lên tên user đã tự đổi).
_DEFAULT_THREAD_TITLE = "Cuộc trò chuyện mới"


def _spawn_background(coro) -> None:
    """Tạo background task có strong-ref để không bị GC, tự dọn khi xong."""
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def _generate_thread_title(thread_id: str, user_id: str, message: str) -> None:
    """Sinh tiêu đề tóm tắt từ tin nhắn đầu bằng LLM, lưu vào thread.

    Chạy nền (fire-and-forget): không chặn luồng gửi tin. Mọi lỗi đều nuốt và log —
    tiêu đề mặc định vẫn dùng được nếu sinh thất bại.
    """
    from langchain_core.messages import HumanMessage as _HumanMessage

    from backend.src.shared.infra.llm.router import LLMRouter

    try:
        async with AsyncSessionMaker() as session:
            repo = PostgresChatThreadRepository(session)
            thread = await repo.find_by_id(thread_id)
            # Bỏ qua nếu thread đã bị xóa hoặc đã có tiêu đề (user đổi tên / đã sinh trước đó).
            if thread is None or thread.title != _DEFAULT_THREAD_TITLE:
                return

            llm = await LLMRouter(session).get_llm_client(user_id)
            prompt = (
                "Tóm tắt câu hỏi sau thành một tiêu đề ngắn gọn, tối đa 8 từ, bằng tiếng Việt. "
                "Chỉ trả về tiêu đề, không dùng dấu ngoặc kép, không kết thúc bằng dấu chấm.\n\n"
                f"Câu hỏi: {message}"
            )
            response = await llm.ainvoke([_HumanMessage(content=prompt)])
            raw = response.content if isinstance(response.content, str) else ""
            title = raw.strip().strip('"').strip("'").splitlines()[0].strip() if raw.strip() else ""
            if title:
                await repo.update_title(thread_id, title[:200])
    except Exception:
        logger.warning("Không sinh được tiêu đề cho thread %s", thread_id, exc_info=True)


async def _assert_project_owned_by_user(
    project_repo: ProjectRepository, project_id: str, user_id: str
) -> None:
    """Đảm bảo project tồn tại và thuộc về user. Raise ProjectNotFoundError/ProjectAccessDeniedError."""
    project = await project_repo.find_by_id(project_id)
    if project is None or project.is_deleted:
        raise ProjectNotFoundError(project_id)
    if project.user_id != user_id:
        raise ProjectAccessDeniedError(project_id)


class CreateThreadUseCase:
    def __init__(self, repo: ChatThreadRepository, project_repo: ProjectRepository) -> None:
        self._repo = repo
        self._project_repo = project_repo

    async def execute(self, dto: CreateThreadDTO) -> ChatThread:
        await _assert_project_owned_by_user(self._project_repo, dto.project_id, dto.user_id)
        return await self._repo.create(
            user_id=dto.user_id, project_id=dto.project_id, title=dto.title
        )


class GetThreadMessagesUseCase:
    def __init__(self, repo: ChatThreadRepository) -> None:
        self._repo = repo

    async def execute(self, dto: GetThreadMessagesDTO) -> list[ChatMessage]:
        thread = await self._repo.find_by_id(dto.thread_id)
        if thread is None:
            raise ThreadNotFoundError(dto.thread_id)
        if thread.user_id != dto.requesting_user_id:
            raise ThreadAccessDeniedError(dto.thread_id)
        return await self._repo.list_messages(dto.thread_id)


class ListThreadsUseCase:
    def __init__(self, repo: ChatThreadRepository, project_repo: ProjectRepository) -> None:
        self._repo = repo
        self._project_repo = project_repo

    async def execute(self, dto: ListThreadsDTO) -> list[ChatThread]:
        await _assert_project_owned_by_user(self._project_repo, dto.project_id, dto.user_id)
        return await self._repo.list_by_project(
            user_id=dto.user_id, project_id=dto.project_id
        )


class RenameThreadUseCase:
    def __init__(self, repo: ChatThreadRepository) -> None:
        self._repo = repo

    async def execute(self, dto: RenameThreadDTO) -> ChatThread:
        thread = await self._repo.find_by_id(dto.thread_id)
        if thread is None:
            raise ThreadNotFoundError(dto.thread_id)
        if thread.user_id != dto.user_id:
            raise ThreadAccessDeniedError(dto.thread_id)
        updated = await self._repo.update_title(dto.thread_id, dto.title)
        if updated is None:
            raise ThreadNotFoundError(dto.thread_id)
        return updated


class DeleteThreadUseCase:
    def __init__(self, repo: ChatThreadRepository) -> None:
        self._repo = repo

    async def execute(self, dto: DeleteThreadDTO) -> None:
        thread = await self._repo.find_by_id(dto.thread_id)
        if thread is None:
            raise ThreadNotFoundError(dto.thread_id)
        if thread.user_id != dto.user_id:
            raise ThreadAccessDeniedError(dto.thread_id)
        await self._repo.delete(dto.thread_id)


class InvokeUseCase:
    """Chạy LangGraph graph, trả về câu trả lời ngay lập tức (không SSE)."""

    def __init__(self, repo: ChatThreadRepository) -> None:
        self._repo = repo

    async def execute(self, dto: InvokeDTO) -> str:
        thread = await self._repo.find_by_id(dto.thread_id)
        if thread is None:
            raise ThreadNotFoundError(dto.thread_id)
        if thread.user_id != dto.user_id:
            raise ThreadAccessDeniedError(dto.thread_id)

        checkpointer = await get_postgres_checkpointer()
        graph = build_graph(checkpointer)
        config = {
            "configurable": {
                "thread_id": dto.thread_id,
                "user_id": dto.user_id,
                "project_id": thread.project_id,
            }
        }
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=dto.message)]},
            config=config,
        )
        return result["messages"][-1].content


class SendMessageUseCase:
    """Lưu user message, tạo run_id, kick off background streaming task."""

    def __init__(self, repo: ChatThreadRepository) -> None:
        self._repo = repo

    async def execute(self, dto: SendMessageDTO) -> str:
        thread = await self._repo.find_by_id(dto.thread_id)
        if thread is None:
            raise ThreadNotFoundError(dto.thread_id)
        if thread.user_id != dto.user_id:
            raise ThreadAccessDeniedError(dto.thread_id)

        await self._repo.save_message(dto.thread_id, "user", dto.message)

        # Tin nhắn đầu của thread mới → sinh tiêu đề tóm tắt bằng LLM (chạy nền).
        # Gate theo tiêu đề mặc định nên các lượt sau không sinh lại, và tên do user
        # tự đổi không bị ghi đè.
        if thread.title == _DEFAULT_THREAD_TITLE:
            _spawn_background(_generate_thread_title(dto.thread_id, dto.user_id, dto.message))

        run_id = f"run_{uuid.uuid4().hex[:12]}"
        queue = create_run(run_id, dto.user_id)

        # Giữ strong reference để task không bị GC; tự dọn khi xong.
        _spawn_background(
            _stream_graph_to_queue(
                run_id=run_id,
                thread_id=dto.thread_id,
                user_id=dto.user_id,
                project_id=thread.project_id,
                message=dto.message,
                queue=queue,
            )
        )
        return run_id


@dataclass
class SuggestionItem:
    label: str
    action_key: str


class GetSuggestionsUseCase:
    """Trả về danh sách gợi ý hành động dựa trên trạng thái dự án.
    Mock LLM adapter — logic thuần Python, không gọi vector DB hay LLM thật.
    """

    def execute(self, dto: "GetSuggestionsDTO") -> list[SuggestionItem]:
        if dto.document_count == 0:
            return [
                SuggestionItem(label="Tải tài liệu lên", action_key="open_upload"),
                SuggestionItem(label="Tìm kiếm bài báo", action_key="focus_search"),
                SuggestionItem(label="Xem bản đồ tri thức", action_key="navigate_graph"),
            ]
        if dto.has_draft:
            return [
                SuggestionItem(label="Tiếp tục soạn thảo", action_key="navigate_writing"),
                SuggestionItem(label="Tìm kiếm thêm tài liệu", action_key="focus_search"),
                SuggestionItem(label="Xem bản đồ tri thức", action_key="navigate_graph"),
            ]
        return [
            SuggestionItem(label="Xem bản đồ tri thức", action_key="navigate_graph"),
            SuggestionItem(label="Tìm kiếm thêm tài liệu", action_key="focus_search"),
            SuggestionItem(label="Bắt đầu soạn thảo", action_key="navigate_writing"),
        ]


@dataclass
class CitationDetail:
    title: str
    text: str


class GetCitationDetailUseCase:
    """Tra cứu nội dung chunk trích dẫn từ DB."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def execute(self, dto: GetCitationDetailDTO) -> CitationDetail | None:
        stmt = (
            select(ChildChunkORM.content, PaperORM.title)
            .join(PaperORM, ChildChunkORM.paper_id == PaperORM.id)
            .where(ChildChunkORM.id == dto.chunk_id)
            .where(PaperORM.user_id == dto.user_id)
        )
        row = (await self._db.execute(stmt)).first()
        if row is None:
            return None
        return CitationDetail(title=row.title, text=row.content)


async def _stream_graph_to_queue(
    run_id: str,
    thread_id: str,
    user_id: str,
    project_id: str,
    message: str,
    queue: "asyncio.Queue[dict | None]",
) -> None:
    """Background task: stream token thật từ LangGraph, lưu assistant message, emit citation_map.

    Dùng astream_events (version v2) thay vì ainvoke + fake char loop.
    Session DB tự tạo trong node — không leak session request-scoped.
    """
    try:
        checkpointer = await get_postgres_checkpointer()
        graph = build_graph(checkpointer)
        config = {
            "configurable": {
                "thread_id": thread_id,
                "user_id": user_id,
                "project_id": project_id,
            }
        }

        # Worker nodes được phép stream token ra UI (AC#9: bỏ token của supervisor)
        _WORKER_NODES = {"research_rag", "gap_analyst"}
        _agent_thinking_emitted = False

        # AC#8: phát status "routing" ngay đầu luồng (trong lúc supervisor phân loại)
        # để UI có phản hồi tức thì trước khi worker bắt đầu sinh token.
        await queue.put({"type": "agent_thinking", "status": "routing"})

        # Stream token thật qua astream_events
        async for event in graph.astream_events(
            {"messages": [HumanMessage(content=message)]},
            config=config,
            version="v2",
        ):
            kind = event["event"]
            node_name = event.get("metadata", {}).get("langgraph_node", "")

            # Emit agent_thinking khi worker bắt đầu (trước chunk đầu tiên — AC#8)
            if kind in ("on_chain_start", "on_chat_model_start") and node_name in _WORKER_NODES and not _agent_thinking_emitted:
                status = "retrieving_rag_context" if node_name == "research_rag" else "analyzing_gaps"
                await queue.put({"type": "agent_thinking", "status": status})
                _agent_thinking_emitted = True

            # Chỉ stream token của worker nodes, bỏ supervisor (AC#9)
            if kind == "on_chat_model_stream" and node_name in _WORKER_NODES:
                chunk = event["data"]["chunk"]
                if isinstance(chunk.content, str) and chunk.content:
                    await queue.put({"type": "chunk", "data": chunk.content})

        # Lấy state cuối (sau khi guardrail đã sửa) qua checkpointer
        final_snapshot = await graph.aget_state(config)
        final_state = final_snapshot.values

        citation_map: dict[int, str] = final_state.get("citation_map", {})
        msgs = final_state.get("messages", [])
        final_content: str = ""
        if msgs:
            last = msgs[-1]
            final_content = last.content if isinstance(last.content, str) else ""

        # Lưu vào DB
        async with AsyncSessionMaker() as session:
            repo = PostgresChatThreadRepository(session)
            await repo.save_message(thread_id, "assistant", final_content)

        # Emit citation_map rồi done (frontend sẽ replace streamingContent bằng final_content đã sạch)
        if citation_map:
            await queue.put({"type": "citation_map", "data": citation_map})
        await queue.put({"type": "done", "content": final_content})

    except Exception:
        logger.exception(
            "Lỗi khi stream graph run_id=%s thread_id=%s", run_id, thread_id
        )
        # Emit done có content lỗi để frontend hiển thị phản hồi thay vì im lặng
        # bỏ qua (commitStreamingMessage('') sẽ drop message, người dùng mất tăm).
        await queue.put(
            {
                "type": "done",
                "content": "Xin lỗi, đã xảy ra lỗi khi tạo câu trả lời. Vui lòng thử lại.",
            }
        )
    finally:
        # Sentinel failsafe: khi exception xảy ra trước khi emit done, event_generator không bị block mãi.
        await queue.put(None)
        delete_run(run_id)
