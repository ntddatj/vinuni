import asyncio
import logging
import uuid

from langchain_core.messages import HumanMessage

from backend.src.modules.orchestrator.application.dtos import (
    CreateThreadDTO,
    GetThreadMessagesDTO,
    InvokeDTO,
    ListThreadsDTO,
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


class InvokeUseCase:
    """AC#5: chạy LangGraph mock graph, trả về câu trả lời ngay lập tức (không SSE)."""

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
        config = {"configurable": {"thread_id": dto.thread_id}}
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=dto.message)]},
            config=config,
        )
        return result["messages"][-1].content


class SendMessageUseCase:
    """AC#6: lưu user message, tạo run_id, kick off background streaming task."""

    def __init__(self, repo: ChatThreadRepository) -> None:
        self._repo = repo

    async def execute(self, dto: SendMessageDTO) -> str:
        thread = await self._repo.find_by_id(dto.thread_id)
        if thread is None:
            raise ThreadNotFoundError(dto.thread_id)
        if thread.user_id != dto.user_id:
            raise ThreadAccessDeniedError(dto.thread_id)

        await self._repo.save_message(dto.thread_id, "user", dto.message)

        run_id = f"run_{uuid.uuid4().hex[:12]}"
        queue = create_run(run_id, dto.user_id)

        task = asyncio.create_task(
            _stream_graph_to_queue(
                run_id=run_id,
                thread_id=dto.thread_id,
                message=dto.message,
                queue=queue,
            )
        )
        # Giữ strong reference để task không bị GC; tự dọn khi xong.
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
        return run_id


async def _stream_graph_to_queue(
    run_id: str,
    thread_id: str,
    message: str,
    queue: "asyncio.Queue[str | None]",
) -> None:
    """Background task: chạy LangGraph graph, đẩy từng ký tự vào queue, lưu assistant message.

    Tự tạo DB session riêng — KHÔNG tái dùng session request-scoped (đã bị đóng
    khi endpoint trả về), nếu không save_message assistant sẽ thất bại.
    """
    try:
        checkpointer = await get_postgres_checkpointer()
        graph = build_graph(checkpointer)
        config = {"configurable": {"thread_id": thread_id}}
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=message)]},
            config=config,
        )
        answer: str = result["messages"][-1].content

        for char in answer:
            await queue.put(char)
            await asyncio.sleep(0.05)  # 50ms per character

        async with AsyncSessionMaker() as session:
            repo = PostgresChatThreadRepository(session)
            await repo.save_message(thread_id, "assistant", answer)
    except Exception:
        logger.exception("Lỗi khi stream/lưu assistant message cho run_id=%s thread_id=%s", run_id, thread_id)
    finally:
        await queue.put(None)  # Sentinel — kết thúc SSE stream
        delete_run(run_id)
