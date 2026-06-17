---
baseline_commit: a2ec1a7
---

# Story 3.2: Chat RAG Stream Kết Quả Qua Server-Sent Events (SSE)

Status: done

## Story

Với vai trò là người dùng,
Tôi muốn giao diện chat đầy đủ để gửi tin nhắn và nhận câu trả lời AI stream từng chữ, đồng thời xem lại lịch sử các phiên chat trước,
Để tôi có thể trao đổi trơn tru với trợ lý nghiên cứu mà không phải chờ đợi phản hồi dài.

> **Phạm vi Sprint Story này** bao gồm 4 epic story liên tiếp (3.2 → 3.5) được gộp lại vì tạo thành một luồng end-to-end không thể tách rời:
> - Epic 3.2: [Frontend] Chat UI Shell & History Sidebar
> - Epic 3.3: [Backend] LangGraph Foundation & Mock RAG
> - Epic 3.4: [Backend] SSE Chat Streaming API
> - Epic 3.5: [Frontend] Typewriter UI & SSE Receiver

## Acceptance Criteria

1. **AC#1 — History Popover [Frontend]**
   **Given** đang ở trang dashboard (có `activeProjectId`),
   **When** bấm nút biểu tượng Lịch sử (🕐) trong `ChatbotPanel`,
   **Then** Popover mở ra hiển thị danh sách threads của project hiện tại (tên + thời gian cập nhật), lấy từ `GET /api/chat/threads?projectId={activeProjectId}`, sắp xếp mới nhất đầu.

2. **AC#2 — Load Thread Messages [Frontend]**
   **Given** Popover đang mở với danh sách threads,
   **When** bấm vào một thread,
   **Then** Popover đóng lại, tin nhắn được load từ `GET /api/chat/threads/{thread_id}/messages` và hiển thị đúng thứ tự trong vùng chat. Thread đó trở thành active thread.

3. **AC#3 — New Thread [Frontend]**
   **Given** đang ở bất kỳ trạng thái chat nào (có/không có active thread),
   **When** bấm nút "+ New Chat" (✏️),
   **Then** gọi `POST /api/chat/threads` tạo thread mới, set làm active thread, reset vùng chat về trống.

4. **AC#4 — Fix PostgresSaver Singleton [Backend - Deferred từ Story 3.1]**
   **Given** backend khởi động,
   **When** lifespan function chạy `setup_postgres_checkpointer()`,
   **Then** `AsyncPostgresSaver` được khởi tạo với `AsyncConnectionPool` (từ `psycopg[pool]`) duy trì pool kết nối mở; `get_postgres_checkpointer()` trả về instance sẵn sàng dùng; khi shutdown, pool được đóng lại.

5. **AC#5 — Mock Invoke Endpoint [Backend]**
   **Given** `POST /api/chat/invoke` với body `{"message": "any text", "threadId": "valid-uuid"}`,
   **When** endpoint xử lý,
   **Then** chạy LangGraph graph với một node đơn `mock_rag_node` (DummyRetriever, không gọi Vector DB), dùng `AsyncPostgresSaver` làm checkpointer, trả về JSON `{"answer": "Đây là câu trả lời mock từ hệ thống RAG. Tính năng RAG thực tế sẽ được kích hoạt ở story sau.", "threadId": "..."}` với HTTP 200.

6. **AC#6 — Gửi Message & Nhận Run ID [Backend]**
   **Given** thread tồn tại và thuộc về user,
   **When** gọi `POST /api/chat/threads/{thread_id}/messages` với body `{"message": "câu hỏi..."}`,
   **Then** backend lưu user message vào bảng `chat_messages` (role="user"), tạo `run_id` duy nhất (UUID), kick off background asyncio task chạy LangGraph graph, trả về `{"runId": "run_xxx"}` HTTP 202.

7. **AC#7 — SSE Stream Endpoint [Backend]**
   **Given** `run_id` hợp lệ đang được xử lý,
   **When** kết nối `GET /api/chat/stream?runId=run_xxx`,
   **Then** backend stream SSE events `data: {"chunk": "X"}\n\n` yield từng ký tự với delay 50ms, kết thúc bằng `data: {"event": "done"}\n\n`.
   **And** sau khi stream xong, assistant message đầy đủ được lưu vào `chat_messages` (role="assistant").

8. **AC#8 — Typewriter UI & Auto-scroll [Frontend]**
   **Given** có active thread và activeProjectId,
   **When** user gõ tin nhắn và nhấn Enter hoặc bấm nút Gửi,
   **Then**:
   - User message hiển thị ngay trong chat area với bubble riêng
   - "AI đang suy nghĩ..." spinner icon xuất hiện dưới cùng
   - Frontend kết nối SSE `GET /api/chat/stream?runId=...`
   - Khi nhận chunk đầu tiên, spinner biến mất, AI message bubble xuất hiện
   - Các chunk tiếp theo nối tiếp vào AI message bubble (typewriter effect)
   - Chat area tự động scroll xuống cuối mỗi khi nhận chunk mới
   - Sau khi nhận `done` event, input được re-enable

> 🔍 **Cách nghiệm thu trực quan:**
> 1. **AC#1-3**: Trình duyệt → Dashboard → click 🕐 → thấy danh sách threads → click vào thread → tin nhắn load. Bấm ✏️ → vùng chat trắng, thread ID thay đổi.
> 2. **AC#5**: Swagger UI → `POST /api/chat/invoke` với `{"message": "test", "threadId": "valid-uuid"}` → nhận JSON mock.
> 3. **AC#6-7**: Swagger UI → `POST /api/chat/threads/{id}/messages` nhận `runId`. Terminal: `curl -N "http://localhost:8000/api/chat/stream?runId=run_xxx"` thấy `data: {"chunk":"Đ"}` ... rồi `data: {"event":"done"}`.
> 4. **AC#8**: Mở Web → gõ tin nhắn → thấy spinner → chữ xuất hiện từng ký tự → auto-scroll.

---

## Tasks / Subtasks

### BACKEND — Fix PostgresSaver Singleton (AC#4)

- [x] **Task 1**: Sửa `postgres_checkpointer.py` để dùng `AsyncConnectionPool` (AC#4)
  - [x] 1.1 Cập nhật `requirements.txt`: đổi `psycopg[binary]>=3.1.0` → `psycopg[binary,pool]>=3.1.0` để cài `psycopg_pool`
  - [x] 1.2 Rewrite `backend/src/modules/orchestrator/infrastructure/postgres_checkpointer.py`:
    ```python
    from psycopg_pool import AsyncConnectionPool
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from backend.src.shared.infra.settings import get_settings

    _pool: AsyncConnectionPool | None = None
    _checkpointer: AsyncPostgresSaver | None = None

    _SQLALCHEMY_SCHEME_PREFIXES = (
        "postgresql+asyncpg://",
        "postgresql+psycopg://",
        "postgresql+psycopg2://",
        "postgres://",
    )

    def _to_psycopg_conn_str(database_url: str) -> str:
        for prefix in _SQLALCHEMY_SCHEME_PREFIXES:
            if database_url.startswith(prefix):
                return "postgresql://" + database_url[len(prefix):]
        return database_url

    async def setup_postgres_checkpointer() -> AsyncPostgresSaver:
        global _checkpointer, _pool
        settings = get_settings()
        conn_str = _to_psycopg_conn_str(settings.database_url)
        _pool = AsyncConnectionPool(conninfo=conn_str, min_size=2, max_size=10, open=False)
        await _pool.open()
        _checkpointer = AsyncPostgresSaver(_pool)
        await _checkpointer.setup()
        return _checkpointer

    async def close_postgres_checkpointer() -> None:
        global _pool
        if _pool is not None:
            await _pool.close()
            _pool = None

    async def get_postgres_checkpointer() -> AsyncPostgresSaver:
        if _checkpointer is None:
            raise RuntimeError("PostgresSaver chưa được khởi tạo. Gọi setup_postgres_checkpointer() trong lifespan.")
        return _checkpointer
    ```
  - [x] 1.3 Cập nhật `backend/main.py` lifespan để gọi `close_postgres_checkpointer()` khi shutdown:
    ```python
    from backend.src.modules.orchestrator.infrastructure.postgres_checkpointer import (
        setup_postgres_checkpointer,
        close_postgres_checkpointer,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)
        await setup_postgres_checkpointer()
        yield
        await close_postgres_checkpointer()
        await engine.dispose()
    ```

### BACKEND — Domain & Infrastructure mở rộng (AC#6, #7)

- [x] **Task 2**: Thêm method `save_message` vào `ChatThreadRepository` (AC#6, #7)
  - [x] 2.1 Cập nhật `backend/src/modules/orchestrator/domain/repositories.py`:
    ```python
    @abstractmethod
    async def save_message(self, thread_id: str, role: str, content: str) -> ChatMessage: ...
    ```
  - [x] 2.2 Cập nhật `backend/src/modules/orchestrator/infrastructure/repository.py`:
    ```python
    async def save_message(self, thread_id: str, role: str, content: str) -> ChatMessage:
        orm = ChatMessageORM(thread_id=thread_id, role=role, content=content)
        self._db.add(orm)
        await self._db.commit()
        await self._db.refresh(orm)
        return _to_message(orm)
    ```

- [x] **Task 3**: Tạo `run_registry.py` — in-memory store cho run_id → asyncio.Queue (AC#6, #7)
  - [x] 3.1 Tạo `backend/src/modules/orchestrator/infrastructure/run_registry.py`:
    ```python
    import asyncio

    _registry: dict[str, asyncio.Queue[str | None]] = {}

    def create_run(run_id: str) -> asyncio.Queue[str | None]:
        queue: asyncio.Queue[str | None] = asyncio.Queue()
        _registry[run_id] = queue
        return queue

    def get_run_queue(run_id: str) -> asyncio.Queue[str | None] | None:
        return _registry.get(run_id)

    def delete_run(run_id: str) -> None:
        _registry.pop(run_id, None)
    ```
    **Lưu ý:** In-memory phù hợp cho single-server MVP. Nếu scale-out, cần chuyển sang Redis Pub/Sub.

### BACKEND — LangGraph Foundation & Mock Graph (AC#5)

- [x] **Task 4**: Tạo LangGraph mock graph (AC#5)
  - [x] 4.1 Tạo `backend/src/modules/orchestrator/application/graph.py`:
    ```python
    from langchain_core.messages import AIMessage
    from langgraph.graph import StateGraph, MessagesState
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver


    def mock_rag_node(state: MessagesState) -> dict:
        """DummyRetriever: trả về câu trả lời cố định, không gọi Vector DB."""
        return {
            "messages": [
                AIMessage(
                    content="Đây là câu trả lời mock từ hệ thống RAG. "
                    "Tính năng RAG thực tế sẽ được kích hoạt ở story sau."
                )
            ]
        }


    def build_graph(checkpointer: AsyncPostgresSaver):
        builder = StateGraph(MessagesState)
        builder.add_node("mock_rag", mock_rag_node)
        builder.set_entry_point("mock_rag")
        builder.set_finish_point("mock_rag")
        return builder.compile(checkpointer=checkpointer)
    ```
  - [x] 4.2 Thêm dependency LangChain Core vào `requirements.txt` nếu chưa có:
    ```
    langchain-core>=0.3.0
    ```
    **Kiểm tra trước:** `langchain-google-genai` đã pull `langchain-core` transitively. Nếu đã có thì bỏ qua.

### BACKEND — Application Use Cases (AC#5, #6, #7)

- [x] **Task 5**: Thêm DTOs mới vào `dtos.py` (AC#5, #6, #7)
  - [x] 5.1 Cập nhật `backend/src/modules/orchestrator/application/dtos.py`:
    ```python
    @dataclass
    class InvokeDTO:
        thread_id: str
        message: str
        user_id: str

    @dataclass
    class SendMessageDTO:
        thread_id: str
        message: str
        user_id: str

    @dataclass
    class StreamDTO:
        run_id: str
    ```

- [x] **Task 6**: Tạo `InvokeUseCase` và `SendMessageUseCase` (AC#5, #6)
  - [x] 6.1 Cập nhật `backend/src/modules/orchestrator/application/use_cases.py` — thêm vào cuối file:
    ```python
    from langchain_core.messages import HumanMessage

    from backend.src.modules.orchestrator.application.graph import build_graph
    from backend.src.modules.orchestrator.infrastructure.postgres_checkpointer import get_postgres_checkpointer
    from backend.src.modules.orchestrator.infrastructure.run_registry import create_run, delete_run


    class InvokeUseCase:
        """AC#5: chạy LangGraph mock graph, trả về câu trả lời ngay lập tức (không SSE)."""

        def __init__(self, repo: ChatThreadRepository) -> None:
            self._repo = repo

        async def execute(self, dto: "InvokeDTO") -> str:
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

        async def execute(self, dto: "SendMessageDTO") -> str:
            thread = await self._repo.find_by_id(dto.thread_id)
            if thread is None:
                raise ThreadNotFoundError(dto.thread_id)
            if thread.user_id != dto.user_id:
                raise ThreadAccessDeniedError(dto.thread_id)

            await self._repo.save_message(dto.thread_id, "user", dto.message)

            import uuid
            import asyncio
            run_id = f"run_{uuid.uuid4().hex[:12]}"
            queue = create_run(run_id)

            asyncio.create_task(
                _stream_graph_to_queue(
                    run_id=run_id,
                    thread_id=dto.thread_id,
                    message=dto.message,
                    repo=self._repo,
                    queue=queue,
                )
            )
            return run_id


    async def _stream_graph_to_queue(
        run_id: str,
        thread_id: str,
        message: str,
        repo: ChatThreadRepository,
        queue: "asyncio.Queue[str | None]",
    ) -> None:
        """Background task: chạy LangGraph graph, đẩy từng ký tự vào queue, lưu assistant message."""
        import asyncio
        from backend.src.modules.orchestrator.infrastructure.run_registry import delete_run

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

            await repo.save_message(thread_id, "assistant", answer)
        except Exception:
            pass  # Không để exception unhandled kill event loop
        finally:
            await queue.put(None)  # Sentinel — kết thúc SSE stream
            delete_run(run_id)
    ```

    **Lưu ý Import:** Các type hints `InvokeDTO`, `SendMessageDTO` cần import từ `.dtos` — thêm ở đầu file sau khi cập nhật dtos.py.

### BACKEND — Presentation Layer (AC#5, #6, #7)

- [x] **Task 7**: Cập nhật Pydantic schemas (AC#5, #6, #7)
  - [x] 7.1 Cập nhật `backend/src/modules/orchestrator/presentation/schemas.py` — thêm vào cuối:
    ```python
    class InvokeRequest(BaseModel):
        model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
        thread_id: UUID
        message: str = Field(..., min_length=1, max_length=4000)


    class InvokeResponse(BaseModel):
        model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
        answer: str
        thread_id: str


    class SendMessageRequest(BaseModel):
        model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
        message: str = Field(..., min_length=1, max_length=4000)


    class SendMessageResponse(BaseModel):
        model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
        run_id: str
    ```

- [x] **Task 8**: Thêm 3 endpoints vào `router.py` (AC#5, #6, #7)
  - [x] 8.1 Cập nhật `backend/src/modules/orchestrator/presentation/router.py` — thêm imports và 3 route mới:

    Thêm imports:
    ```python
    import json
    from fastapi import Query
    from fastapi.responses import StreamingResponse
    from backend.src.modules.orchestrator.application.dtos import InvokeDTO, SendMessageDTO
    from backend.src.modules.orchestrator.application.use_cases import InvokeUseCase, SendMessageUseCase
    from backend.src.modules.orchestrator.infrastructure.run_registry import get_run_queue
    from backend.src.modules.orchestrator.presentation.schemas import (
        InvokeRequest, InvokeResponse, SendMessageRequest, SendMessageResponse
    )
    ```

    Thêm 3 routes vào router (sau các routes hiện có):

    ```python
    @router.post("/chat/invoke", response_model=InvokeResponse)
    async def invoke_chat(
        request: InvokeRequest,
        current_user: User = Depends(get_current_user),
        repo: ChatThreadRepository = Depends(get_thread_repository),
    ) -> InvokeResponse:
        use_case = InvokeUseCase(repo)
        try:
            answer = await use_case.execute(
                InvokeDTO(thread_id=str(request.thread_id), message=request.message, user_id=current_user.id)
            )
        except ThreadNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except ThreadAccessDeniedError as e:
            raise HTTPException(status_code=403, detail=str(e)) from e
        return InvokeResponse(answer=answer, thread_id=str(request.thread_id))


    @router.post("/chat/threads/{thread_id}/messages", response_model=SendMessageResponse, status_code=202)
    async def send_message(
        thread_id: UUID,
        request: SendMessageRequest,
        current_user: User = Depends(get_current_user),
        repo: ChatThreadRepository = Depends(get_thread_repository),
    ) -> SendMessageResponse:
        use_case = SendMessageUseCase(repo)
        try:
            run_id = await use_case.execute(
                SendMessageDTO(thread_id=str(thread_id), message=request.message, user_id=current_user.id)
            )
        except ThreadNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except ThreadAccessDeniedError as e:
            raise HTTPException(status_code=403, detail=str(e)) from e
        return SendMessageResponse(run_id=run_id)


    @router.get("/chat/stream")
    async def stream_chat(
        run_id: str = Query(..., alias="runId"),
        current_user: User = Depends(get_current_user),
    ):
        queue = get_run_queue(run_id)
        if queue is None:
            raise HTTPException(status_code=404, detail=f"Run {run_id} không tồn tại hoặc đã hoàn thành")

        async def event_generator():
            while True:
                item = await queue.get()
                if item is None:
                    yield f"data: {json.dumps({'event': 'done'})}\n\n"
                    break
                yield f"data: {json.dumps({'chunk': item})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )
    ```

### FRONTEND — Types & API Client (AC#1, #2, #3, #6, #7, #8)

- [x] **Task 9**: Tạo `frontend/src/types/chat.ts`
  - [x] 9.1 Tạo file:
    ```typescript
    export interface ChatThread {
      id: string;
      userId: string;
      projectId: string;
      title: string;
      createdAt: string;
      updatedAt: string;
    }

    export interface ChatMessage {
      id: string;
      threadId: string;
      role: 'user' | 'assistant';
      content: string;
      createdAt: string;
    }

    export interface SendMessageResponse {
      runId: string;
    }
    ```

- [x] **Task 10**: Tạo `frontend/src/api/chat.ts`
  - [x] 10.1 Tạo file:
    ```typescript
    import apiClient from './client';
    import type { ChatThread, ChatMessage, SendMessageResponse } from '@/types/chat';

    export async function listThreads(projectId: string): Promise<ChatThread[]> {
      const { data } = await apiClient.get<ChatThread[]>('/api/chat/threads', {
        params: { projectId },
      });
      return data;
    }

    export async function createThread(projectId: string, title?: string): Promise<ChatThread> {
      const { data } = await apiClient.post<ChatThread>('/api/chat/threads', {
        projectId,
        title: title ?? 'Cuộc trò chuyện mới',
      });
      return data;
    }

    export async function getThreadMessages(threadId: string): Promise<ChatMessage[]> {
      const { data } = await apiClient.get<ChatMessage[]>(
        `/api/chat/threads/${threadId}/messages`
      );
      return data;
    }

    export async function sendMessage(
      threadId: string,
      message: string
    ): Promise<SendMessageResponse> {
      const { data } = await apiClient.post<SendMessageResponse>(
        `/api/chat/threads/${threadId}/messages`,
        { message }
      );
      return data;
    }
    ```
    **Lưu ý:** SSE dùng native `EventSource` (không qua axios) — xem Task 13.

### FRONTEND — Chat Store (AC#1, #2, #3, #8)

- [x] **Task 11**: Tạo `frontend/src/store/chatStore.ts`
  - [x] 11.1 Tạo file:
    ```typescript
    import { create } from 'zustand';
    import type { ChatThread, ChatMessage } from '@/types/chat';

    interface ChatState {
      threads: ChatThread[];
      activeThreadId: string | null;
      messages: ChatMessage[];
      isLoadingThreads: boolean;
      isLoadingMessages: boolean;
      isStreaming: boolean;
      streamingContent: string;

      setThreads: (threads: ChatThread[]) => void;
      setActiveThreadId: (id: string | null) => void;
      setMessages: (messages: ChatMessage[]) => void;
      appendChunk: (chunk: string) => void;
      commitStreamingMessage: () => void;
      setLoadingThreads: (v: boolean) => void;
      setLoadingMessages: (v: boolean) => void;
      setStreaming: (v: boolean) => void;
      addOptimisticUserMessage: (content: string) => void;
      reset: () => void;
    }

    const INIT: Pick<
      ChatState,
      'threads' | 'activeThreadId' | 'messages' | 'isLoadingThreads' |
      'isLoadingMessages' | 'isStreaming' | 'streamingContent'
    > = {
      threads: [],
      activeThreadId: null,
      messages: [],
      isLoadingThreads: false,
      isLoadingMessages: false,
      isStreaming: false,
      streamingContent: '',
    };

    export const useChatStore = create<ChatState>()((set, get) => ({
      ...INIT,

      setThreads: (threads) => set({ threads }),
      setActiveThreadId: (id) => set({ activeThreadId: id }),
      setMessages: (messages) => set({ messages }),
      setLoadingThreads: (v) => set({ isLoadingThreads: v }),
      setLoadingMessages: (v) => set({ isLoadingMessages: v }),
      setStreaming: (v) => set({ isStreaming: v }),

      appendChunk: (chunk) =>
        set((s) => ({ streamingContent: s.streamingContent + chunk })),

      commitStreamingMessage: () => {
        const content = get().streamingContent;
        if (!content) return;
        const assistantMsg: ChatMessage = {
          id: `stream-${Date.now()}`,
          threadId: get().activeThreadId ?? '',
          role: 'assistant',
          content,
          createdAt: new Date().toISOString(),
        };
        set((s) => ({
          messages: [...s.messages, assistantMsg],
          streamingContent: '',
          isStreaming: false,
        }));
      },

      addOptimisticUserMessage: (content) => {
        const msg: ChatMessage = {
          id: `optimistic-${Date.now()}`,
          threadId: get().activeThreadId ?? '',
          role: 'user',
          content,
          createdAt: new Date().toISOString(),
        };
        set((s) => ({ messages: [...s.messages, msg] }));
      },

      reset: () => set(INIT),
    }));
    ```

### FRONTEND — Chat UI Components (AC#1, #2, #3, #8)

- [x] **Task 12**: Thêm i18n keys vào `translations.ts`
  - [x] 12.1 Cập nhật `frontend/src/i18n/translations.ts` — thêm các keys mới (thay thế `chat.comingSoon`):
    ```typescript
    'chat.historyBtn': { vi: 'Lịch sử trò chuyện', en: 'Chat History' },
    'chat.newChatBtn': { vi: 'Cuộc trò chuyện mới', en: 'New Chat' },
    'chat.historyEmpty': { vi: 'Chưa có phiên chat nào.', en: 'No chat sessions yet.' },
    'chat.historyTitle': { vi: 'Lịch sử Chat', en: 'Chat History' },
    'chat.thinking': { vi: 'AI đang suy nghĩ...', en: 'AI is thinking...' },
    'chat.sendBtn': { vi: 'Gửi', en: 'Send' },
    'chat.noProject': { vi: 'Chọn một dự án để bắt đầu chat.', en: 'Select a project to start chatting.' },
    'chat.inputDisabled': { vi: 'Chọn dự án để chat...', en: 'Select a project to chat...' },
    ```
    Xóa `'chat.comingSoon'` khỏi file (không còn dùng).

- [x] **Task 13**: Tạo `ChatHistoryPopover.tsx`
  - [x] 13.1 Tạo `frontend/src/features/workspace/ChatHistoryPopover.tsx`:
    ```typescript
    import { useEffect, useRef } from 'react';
    import { useChatStore } from '@/store/chatStore';
    import { useTranslation } from '@/i18n/useTranslation';
    import { listThreads, getThreadMessages } from '@/api/chat';
    import type { ChatThread } from '@/types/chat';
    import styles from './ChatHistoryPopover.module.css';

    interface Props {
      projectId: string;
      onClose: () => void;
    }

    export function ChatHistoryPopover({ projectId, onClose }: Props) {
      const { t } = useTranslation();
      const threads = useChatStore((s) => s.threads);
      const isLoading = useChatStore((s) => s.isLoadingThreads);
      const setThreads = useChatStore((s) => s.setThreads);
      const setLoadingThreads = useChatStore((s) => s.setLoadingThreads);
      const setActiveThreadId = useChatStore((s) => s.setActiveThreadId);
      const setMessages = useChatStore((s) => s.setMessages);
      const setLoadingMessages = useChatStore((s) => s.setLoadingMessages);
      const popoverRef = useRef<HTMLDivElement>(null);

      useEffect(() => {
        setLoadingThreads(true);
        listThreads(projectId)
          .then(setThreads)
          .finally(() => setLoadingThreads(false));
      }, [projectId]);

      useEffect(() => {
        function handleClickOutside(e: MouseEvent) {
          if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
            onClose();
          }
        }
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
      }, [onClose]);

      async function handleSelectThread(thread: ChatThread) {
        setActiveThreadId(thread.id);
        setLoadingMessages(true);
        onClose();
        try {
          const msgs = await getThreadMessages(thread.id);
          setMessages(msgs);
        } finally {
          setLoadingMessages(false);
        }
      }

      return (
        <div ref={popoverRef} className={styles.popover} role="dialog" aria-label={t('chat.historyTitle')}>
          <div className={styles.header}>{t('chat.historyTitle')}</div>
          {isLoading ? (
            <div className={styles.loading}>…</div>
          ) : threads.length === 0 ? (
            <div className={styles.empty}>{t('chat.historyEmpty')}</div>
          ) : (
            <ul className={styles.list}>
              {threads.map((thread) => (
                <li key={thread.id}>
                  <button
                    className={styles.threadItem}
                    onClick={() => handleSelectThread(thread)}
                    type="button"
                  >
                    <span className={styles.threadTitle}>{thread.title}</span>
                    <span className={styles.threadDate}>
                      {new Date(thread.updatedAt).toLocaleDateString('vi-VN')}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      );
    }
    ```
  - [x] 13.2 Tạo `frontend/src/features/workspace/ChatHistoryPopover.module.css` với styles cơ bản:
    - `.popover`: `position: absolute; top: 48px; left: 0; right: 0; z-index: 100; background: var(--surface-raised); border: 1px solid var(--border-hairline); border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.12); max-height: 320px; overflow-y: auto;`
    - `.header`: `padding: 8px 12px; font-weight: 600; font-size: 12px; color: var(--ink-secondary); border-bottom: 1px solid var(--border-hairline);`
    - `.list`: `list-style: none; margin: 0; padding: 4px 0;`
    - `.threadItem`: `width: 100%; display: flex; justify-content: space-between; padding: 8px 12px; background: none; border: none; cursor: pointer; text-align: left;`
    - `.threadItem:hover`: `background: var(--surface-hover);`
    - `.threadTitle`: `font-size: 13px; color: var(--ink-primary); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;`
    - `.threadDate`: `font-size: 11px; color: var(--ink-tertiary); margin-left: 8px; white-space: nowrap;`
    - `.empty`, `.loading`: `padding: 16px 12px; font-size: 13px; color: var(--ink-secondary); text-align: center;`

- [x] **Task 14**: Rewrite `ChatbotPanel.tsx` — thêm đầy đủ chat UI (AC#1, #2, #3, #8)
  - [x] 14.1 Rewrite `frontend/src/features/workspace/ChatbotPanel.tsx`:

    **Logic chính cần implement:**
    - State: `showHistory` (boolean), `inputValue` (string)
    - Đọc từ store: `messages`, `activeThreadId`, `isStreaming`, `streamingContent`, `isLoadingMessages`
    - Đọc từ `projectStore`: `activeProjectId`
    - `messagesEndRef` + `useEffect` scroll xuống cuối khi `messages` hoặc `streamingContent` thay đổi
    - Hàm `handleNewChat()`: gọi `createThread(activeProjectId)`, set activeThreadId, reset messages
    - Hàm `handleSend()`:
      1. Guard: nếu `!inputValue.trim() || !activeThreadId || isStreaming` → return
      2. `addOptimisticUserMessage(inputValue)`
      3. `setInputValue('')`
      4. `setStreaming(true)`, `appendChunk('')` (reset streamingContent)
      5. `const { runId } = await sendMessage(activeThreadId, inputValue)`
      6. Tạo `EventSource('/api/chat/stream?runId=' + runId)` với `withCredentials: true`

          **Lưu ý:** `EventSource` không hỗ trợ `withCredentials` trực tiếp — cần dùng `new EventSource(url, { withCredentials: true })`. Cookie được gửi tự động nếu `withCredentials: true`.
      7. `es.onmessage = (e) => { const data = JSON.parse(e.data); if (data.event === 'done') { commitStreamingMessage(); es.close(); } else { appendChunk(data.chunk); } }`
      8. `es.onerror = () => { setStreaming(false); es.close(); toast.error('Lỗi kết nối stream'); }`
    - **Render messages**: map `messages` thành bubbles (`role === 'user'` → align right, `role === 'assistant'` → align left)
    - **Streaming bubble**: khi `isStreaming`, render thêm AI bubble với nội dung `streamingContent + '▋'` (cursor nhấp nháy)
    - **Thinking indicator**: khi `isStreaming && streamingContent === ''`, hiển thị spinner thay vì cursor

    **Cấu trúc JSX (giữ lại resize/collapse logic hiện có):**
    ```tsx
    <div className={styles.content}>
      <div className={styles.header}>
        <h3 className={styles.title}>{t('chat.title')}</h3>
        <div className={styles.actions}>
          <button onClick={() => setShowHistory(!showHistory)} title={t('chat.historyBtn')}>🕐</button>
          <button onClick={handleNewChat} title={t('chat.newChatBtn')} disabled={!activeProjectId}>✏️</button>
        </div>
        {showHistory && activeProjectId && (
          <ChatHistoryPopover
            projectId={activeProjectId}
            onClose={() => setShowHistory(false)}
          />
        )}
      </div>

      <div className={styles.messages} ref={messagesContainerRef}>
        {!activeProjectId && <p className={styles.hint}>{t('chat.noProject')}</p>}
        {messages.map((msg) => (
          <div key={msg.id} className={`${styles.bubble} ${msg.role === 'user' ? styles.userBubble : styles.aiBubble}`}>
            {msg.content}
          </div>
        ))}
        {isStreaming && (
          <div className={`${styles.bubble} ${styles.aiBubble}`}>
            {streamingContent === '' ? (
              <span className={styles.thinking}>{t('chat.thinking')}</span>
            ) : (
              <>{streamingContent}<span className={styles.cursor}>▋</span></>
            )}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className={styles.inputArea}>
        <input
          className={styles.input}
          placeholder={activeProjectId ? t('chat.placeholder') : t('chat.inputDisabled')}
          disabled={!activeProjectId || isStreaming}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
          type="text"
        />
        <button
          className={styles.sendBtn}
          onClick={handleSend}
          disabled={!activeProjectId || isStreaming || !inputValue.trim()}
          type="button"
        >
          {t('chat.sendBtn')}
        </button>
      </div>
    </div>
    ```

  - [x] 14.2 Cập nhật `ChatbotPanel.module.css` — thêm styles mới:
    - `.header`: `display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; border-bottom: 1px solid var(--border-hairline); position: relative;`
    - `.actions`: `display: flex; gap: 4px;`
    - `.actions button`: `background: none; border: none; cursor: pointer; padding: 4px 6px; border-radius: 4px; font-size: 14px;`
    - `.actions button:hover`: `background: var(--surface-hover);`
    - `.messages`: `flex: 1; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 8px;`
    - `.bubble`: `max-width: 85%; padding: 8px 12px; border-radius: 8px; font-size: 13px; line-height: 1.5; word-break: break-word;`
    - `.userBubble`: `align-self: flex-end; background: var(--accent-blue); color: white;`
    - `.aiBubble`: `align-self: flex-start; background: var(--surface-hover);`
    - `.cursor`: `display: inline-block; animation: blink 1s step-end infinite;`
    - `@keyframes blink`: `{ 0%, 100% { opacity: 1; } 50% { opacity: 0; } }`
    - `.thinking`: `color: var(--ink-secondary); font-style: italic;`
    - `.sendBtn`: `padding: 6px 12px; background: var(--accent-blue); color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;`
    - `.sendBtn:disabled`: `opacity: 0.5; cursor: not-allowed;`
    - `.inputArea`: `display: flex; gap: 4px; padding: 8px 12px; border-top: 1px solid var(--border-hairline);`
    - `.input`: `flex: 1;`
    - `.hint`: `color: var(--ink-secondary); font-size: 12px; text-align: center; padding: 16px;`

### BACKEND — Unit Tests (AC#4, #5, #6)

- [x] **Task 15**: Viết unit tests
  - [x] 15.1 Tạo `tests/unit/orchestrator/test_send_message_use_case.py`:
    ```python
    """Unit tests cho SendMessageUseCase và InvokeUseCase."""
    import asyncio
    from unittest.mock import AsyncMock, MagicMock, patch
    import pytest
    from backend.src.modules.orchestrator.application.dtos import SendMessageDTO, InvokeDTO
    from backend.src.modules.orchestrator.application.use_cases import SendMessageUseCase, InvokeUseCase
    from backend.src.modules.orchestrator.domain.exceptions import ThreadNotFoundError, ThreadAccessDeniedError
    # Tái dùng _make_thread() từ test_chat_threads.py
    from tests.unit.orchestrator.test_chat_threads import _make_thread

    @pytest.mark.asyncio
    async def test_send_message_raises_not_found_when_thread_missing():
        repo = AsyncMock(); repo.find_by_id.return_value = None
        uc = SendMessageUseCase(repo)
        with pytest.raises(ThreadNotFoundError):
            await uc.execute(SendMessageDTO(thread_id="ghost", message="hi", user_id="u1"))

    @pytest.mark.asyncio
    async def test_send_message_raises_access_denied_when_wrong_user():
        repo = AsyncMock(); repo.find_by_id.return_value = _make_thread(user_id="owner")
        uc = SendMessageUseCase(repo)
        with pytest.raises(ThreadAccessDeniedError):
            await uc.execute(SendMessageDTO(thread_id="t1", message="hi", user_id="other"))

    @pytest.mark.asyncio
    async def test_send_message_saves_user_message_and_returns_run_id():
        repo = AsyncMock(); repo.find_by_id.return_value = _make_thread(user_id="u1")
        repo.save_message.return_value = AsyncMock()
        with patch("backend.src.modules.orchestrator.application.use_cases.get_postgres_checkpointer") as mock_cp, \
             patch("asyncio.create_task"):
            mock_cp.return_value = AsyncMock()
            uc = SendMessageUseCase(repo)
            run_id = await uc.execute(SendMessageDTO(thread_id="t1", message="hi", user_id="u1"))
        repo.save_message.assert_called_once_with("t1", "user", "hi")
        assert run_id.startswith("run_")
    ```

---

## Dev Notes

### Bối cảnh & Mục tiêu

Story này tạo nên **toàn bộ khung chat end-to-end**: frontend shell + lịch sử + gửi/nhận tin nhắn + SSE streaming + typewriter. Nền tảng LangGraph (Mock RAG) được dựng ở đây để các story sau (3.3-3.5 trong sprint plan = 3.6-3.10 epic) có thể thay thế node mock bằng RAG thực.

### Deferred Work cần giải quyết

**CRITICAL (phải sửa trong story này):**
- `_checkpointer` trong `postgres_checkpointer.py` hiện lưu **context manager chưa enter** (`AsyncPostgresSaver.from_conn_string()` trả về CM, không phải saver). Sẽ crash ngay khi LangGraph graph cố dùng checkpointer. Fix bằng `AsyncConnectionPool` (Task 1). [Xem deferred-work.md dòng 1]

### Pitfalls Cần Tránh

1. **EventSource không hỗ trợ custom headers** — không thể truyền Authorization header. Auth qua cookie `httponly` là đủ vì `withCredentials: true`. Đảm bảo `Access-Control-Allow-Credentials: true` đã có trong CORS (đã có từ `allow_credentials=True`).

2. **asyncio.create_task() trong endpoint async** — phải đảm bảo task được tạo trong event loop đang chạy. Dùng `asyncio.create_task()` trực tiếp trong async function là đúng (FastAPI endpoints là async).

3. **`_stream_graph_to_queue` không bắt exception -> queue không có sentinel** — luôn đặt `await queue.put(None)` trong `finally`. Task 6 đã cover.

4. **StreamingResponse & middleware** — nếu có response body middleware nó sẽ buffer toàn bộ SSE. Header `X-Accel-Buffering: no` giúp Nginx không buffer. CORS middleware của FastAPI không buffer.

5. **`useChatStore.reset()` khi đổi project** — khi `activeProjectId` thay đổi trong `ChatbotPanel`, nên gọi `reset()` để tránh tin nhắn project cũ bị giữ lại. Thêm `useEffect([activeProjectId], () => reset())`.

6. **`EventSource` không có `onclose`** — khi server đóng stream, `onerror` được gọi. Phân biệt bằng `readyState === EventSource.CLOSED` trong `onerror` handler.

7. **Không dùng `asyncio.sleep()` blocking** — `asyncio.sleep(0.05)` trong `_stream_graph_to_queue` là async, không block event loop. Đúng pattern.

8. **CSS variable names** — dùng đúng CSS variables từ theme hiện có: `--surface-raised`, `--surface-hover`, `--border-hairline`, `--accent-blue`, `--ink-primary`, `--ink-secondary`, `--ink-tertiary`. Xem `frontend/src/index.css` hoặc `App.css` để verify.

9. **`ChatHistoryPopover` leak event listener** — luôn return cleanup function từ `useEffect` để remove `mousedown` listener.

10. **`psycopg[binary,pool]` vs `psycopg[pool]`** — dùng `psycopg[binary,pool]` để giữ binary driver (performance) + thêm pool. Không cài riêng `psycopg_pool`.

### Module & File Map

**Backend — Files UPDATE:**
- `requirements.txt` (line `psycopg[binary]` → `psycopg[binary,pool]`)
- `backend/src/modules/orchestrator/infrastructure/postgres_checkpointer.py` (full rewrite)
- `backend/src/modules/orchestrator/domain/repositories.py` (thêm `save_message`)
- `backend/src/modules/orchestrator/infrastructure/repository.py` (thêm `save_message`)
- `backend/src/modules/orchestrator/application/dtos.py` (thêm DTOs)
- `backend/src/modules/orchestrator/application/use_cases.py` (thêm use cases)
- `backend/src/modules/orchestrator/presentation/schemas.py` (thêm schemas)
- `backend/src/modules/orchestrator/presentation/router.py` (thêm 3 routes)
- `backend/main.py` (thêm `close_postgres_checkpointer` trong lifespan)

**Backend — Files NEW:**
- `backend/src/modules/orchestrator/application/graph.py`
- `backend/src/modules/orchestrator/infrastructure/run_registry.py`
- `tests/unit/orchestrator/test_send_message_use_case.py`

**Frontend — Files UPDATE:**
- `frontend/src/features/workspace/ChatbotPanel.tsx` (major rewrite)
- `frontend/src/features/workspace/ChatbotPanel.module.css` (thêm styles)
- `frontend/src/i18n/translations.ts` (thêm/xóa keys)

**Frontend — Files NEW:**
- `frontend/src/types/chat.ts`
- `frontend/src/api/chat.ts`
- `frontend/src/store/chatStore.ts`
- `frontend/src/features/workspace/ChatHistoryPopover.tsx`
- `frontend/src/features/workspace/ChatHistoryPopover.module.css`

### API Endpoints Summary

| Method | Path | Auth | Mô tả |
|--------|------|------|-------|
| POST | `/api/chat/invoke` | JWT cookie | Mock invoke (không SSE), trả JSON ngay |
| POST | `/api/chat/threads/{thread_id}/messages` | JWT cookie | Gửi message, nhận `runId`, bắt đầu stream |
| GET | `/api/chat/stream?runId=xxx` | JWT cookie | SSE stream từng chunk |

(Các endpoints của Story 3.1 — POST/GET threads, GET messages — không thay đổi)

### Import Pattern

Backend follow convention hiện có trong codebase:
```python
from backend.src.modules.orchestrator.application.dtos import InvokeDTO, SendMessageDTO
```
Frontend follow path alias `@/`:
```typescript
import { useChatStore } from '@/store/chatStore';
```

### Testing Pattern

Dùng `pytest.mark.asyncio` + `AsyncMock` như `tests/unit/orchestrator/test_chat_threads.py`. Không cần database thật cho unit tests — mock repository.

### Learnings từ Story 3.1

- Pattern `_assert_project_owned_by_user()` đã có trong `use_cases.py` — không cần duplicate. `SendMessageUseCase` chỉ cần verify thread ownership (không cần verify project ownership thêm vì thread đã gắn với project).
- `from_attributes=True` trên Pydantic response schema để `model_validate` từ ORM.
- `alias_generator=to_camel` là convention toàn codebase — giữ nhất quán.
- Import UUID validation: dùng `UUID` type trong FastAPI path/query param — FastAPI tự validate.

### Learnings từ Story 2.5 (SSE pattern)

Story 2.5 đã implement SSE (`IngestionProgress`) — xem pattern tại:
- Backend: `backend/src/modules/ingestion/presentation/router.py` (SSE ticket endpoint)
- Frontend: `frontend/src/features/workspace/IngestionProgress.tsx`

Pattern ở story này khác một chút: dùng `asyncio.Queue` thay vì Redis Pub/Sub (MVP). Khi scale-out cần chuyển sang Redis.

### Project Structure Notes

Module `orchestrator` đã được setup đầy đủ từ Story 3.1 theo Hexagonal Architecture:
```
backend/src/modules/orchestrator/
├── domain/         (entities, repositories, exceptions)
├── infrastructure/ (orm, repository, dependencies, checkpointer, + run_registry mới)
├── application/    (dtos, use_cases, + graph mới)
└── presentation/   (router, schemas)
```

Frontend theo pattern `features/workspace/` với CSS Modules đã được áp dụng nhất quán.

### References

- [Source: architecture.md Section 7.4] — Luồng xử lý 4 bước, SSE streaming pattern
- [Source: architecture.md Section 7.5] — Sequence diagram: POST /api/chat → SSE
- [Source: architecture.md Section 8.1] — PostgresSaver + Chat History management
- [Source: epics.md Story 3.2] — Frontend Chat UI Shell & History Sidebar
- [Source: epics.md Story 3.3] — LangGraph Foundation & Mock RAG
- [Source: epics.md Story 3.4] — SSE Chat Streaming API
- [Source: epics.md Story 3.5] — Typewriter UI & SSE Receiver
- [Source: ux-designs/DESIGN.md Section 4] — Right Resizable Chatbot Panel UX spec
- [Source: deferred-work.md] — PostgresSaver singleton bug (phải fix ở story này)
- [Source: backend/src/modules/orchestrator/infrastructure/postgres_checkpointer.py] — Current buggy implementation

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- ✅ Task 1: Fix PostgresSaver singleton — rewrite dùng `AsyncConnectionPool` (psycopg_pool), đảm bảo pool kết nối mở thực sự; thêm `close_postgres_checkpointer()` vào lifespan. Sửa bug critical: trước đây `_checkpointer` lưu context manager chưa enter.
- ✅ Task 2-3: Mở rộng domain/infrastructure — thêm `save_message` vào repository; tạo `run_registry.py` in-memory queue store cho SSE streaming.
- ✅ Task 4: LangGraph mock graph với `mock_rag_node` (DummyRetriever, không gọi Vector DB). Đã dùng `langchain-core` có sẵn từ `langchain-google-genai`.
- ✅ Task 5-8: Backend application + presentation layer — `InvokeUseCase` (sync, không SSE), `SendMessageUseCase` (async + background task), 3 endpoints mới: `POST /api/chat/invoke`, `POST /api/chat/threads/{thread_id}/messages` (202), `GET /api/chat/stream?runId=xxx` (SSE).
- ✅ Task 9-11: Frontend types, API client (axios), chatStore (zustand) với đầy đủ state cho streaming.
- ✅ Task 12-14: Frontend UI — i18n keys mới, `ChatHistoryPopover` (AC#1,2), `ChatbotPanel` rewrite với typewriter effect + auto-scroll + SSE EventSource (AC#3,8).
- ✅ Task 15: 6 unit tests mới (InvokeUseCase + SendMessageUseCase) — tất cả pass. Tổng 12/12 orchestrator tests pass.
- ✅ Linting: ruff auto-fix 8 import order issues; TypeScript tsc --noEmit sạch.

### File List

**Backend — Updated:**
- `requirements.txt`
- `backend/main.py`
- `backend/src/modules/orchestrator/infrastructure/postgres_checkpointer.py`
- `backend/src/modules/orchestrator/domain/repositories.py`
- `backend/src/modules/orchestrator/infrastructure/repository.py`
- `backend/src/modules/orchestrator/application/dtos.py`
- `backend/src/modules/orchestrator/application/use_cases.py`
- `backend/src/modules/orchestrator/presentation/schemas.py`
- `backend/src/modules/orchestrator/presentation/router.py`

**Backend — New:**
- `backend/src/modules/orchestrator/application/graph.py`
- `backend/src/modules/orchestrator/infrastructure/run_registry.py`
- `tests/unit/orchestrator/test_send_message_use_case.py`

**Frontend — Updated:**
- `frontend/src/features/workspace/ChatbotPanel.tsx`
- `frontend/src/features/workspace/ChatbotPanel.module.css`
- `frontend/src/i18n/translations.ts`

**Frontend — New:**
- `frontend/src/types/chat.ts`
- `frontend/src/api/chat.ts`
- `frontend/src/store/chatStore.ts`
- `frontend/src/features/workspace/ChatHistoryPopover.tsx`
- `frontend/src/features/workspace/ChatHistoryPopover.module.css`

## Change Log

- 2026-06-17: Story 3.2 implementation — Chat RAG Stream end-to-end: fix PostgresSaver singleton, LangGraph mock graph, SSE streaming API (3 endpoints mới), frontend Chat UI với history popover và typewriter effect. (Agent: claude-sonnet-4-6)
- 2026-06-17: Code review (Blind Hunter + Edge Case Hunter + Acceptance Auditor) — 12 patch áp dụng, 4 defer, 2 dismiss. Xem `### Review Findings`. (Agent: claude-opus-4-8)

## Review Findings

> Code review 2026-06-17 — 3 lớp adversarial. Tất cả `patch` đã được áp dụng & verify (ruff pass, 12/12 orchestrator tests pass, tsc --noEmit exit 0, eslint 0 error). `defer` là giới hạn MVP đã ghi nhận.

### Patches (đã sửa)

- [x] [Review][Patch][CRITICAL — phát hiện lúc chạy thật] AC#4: `AsyncPostgresSaver.setup()` chạy `CREATE INDEX CONCURRENTLY` nhưng `AsyncConnectionPool` mặc định ở transaction mode → `psycopg.errors.ActiveSqlTransaction` → **backend crash loop khi startup → không đăng nhập được**. Fix: pool dùng `kwargs={"autocommit": True, "prepare_threshold": 0}`. Đã rebuild container, health 200, login 401-on-wrong-pw OK. [backend/src/modules/orchestrator/infrastructure/postgres_checkpointer.py:24-42]
- [x] [Review][Patch] `react-hot-toast` không cài → vỡ build, đổi sang `sonner` [frontend/src/features/workspace/ChatbotPanel.tsx:8]
- [x] [Review][Patch] Background task dùng DB session request-scoped đã đóng → assistant message không lưu (vi phạm AC#7); tạo `AsyncSessionMaker()` riêng trong `_stream_graph_to_queue` [backend/src/modules/orchestrator/application/use_cases.py:124-159]
- [x] [Review][Patch] `asyncio.create_task` fire-and-forget có thể bị GC giữa chừng; giữ strong reference qua `_background_tasks` + `add_done_callback` [backend/src/modules/orchestrator/application/use_cases.py:109-122]
- [x] [Review][Patch] SSE `/stream` không kiểm tra owner của `run_id` (IDOR — user khác đọc được stream); thêm `_owners` registry + check `get_run_owner == current_user.id` → 403 [backend/src/modules/orchestrator/presentation/router.py:139-143, infrastructure/run_registry.py]
- [x] [Review][Patch] EventSource không được `close()` khi unmount/đổi project → leak + nhiễm hội thoại; lưu `eventSourceRef` + `closeStream()` ở unmount/project-change/trước send mới [frontend/src/features/workspace/ChatbotPanel.tsx:23,44-59,143-167]
- [x] [Review][Patch] `commitStreamingMessage` early-return khi content rỗng → `isStreaming` kẹt true khoá input vĩnh viễn; luôn reset isStreaming [frontend/src/store/chatStore.ts:60-66]
- [x] [Review][Patch] `JSON.parse` trong `onmessage` không bọc try/catch → frame lỗi làm treo stream; thêm try/catch + guard `typeof chunk === 'string'` [frontend/src/features/workspace/ChatbotPanel.tsx:147-160]
- [x] [Review][Patch] `except Exception: pass` nuốt mọi lỗi không log; đổi sang `logger.exception(...)` [backend/src/modules/orchestrator/application/use_cases.py:152-153]
- [x] [Review][Patch] `appendChunk('')` "reset streamingContent" là no-op; thay bằng `beginStreaming()` reset đúng [frontend/src/store/chatStore.ts:58, ChatbotPanel.tsx:130]
- [x] [Review][Patch] Không rollback optimistic user message khi POST lỗi → hiển thị tin chưa gửi được; thêm `removeMessage(optimisticId)` trong catch [frontend/src/features/workspace/ChatbotPanel.tsx:128-141, chatStore.ts:96]
- [x] [Review][Patch] `getThreadMessages` trong popover không có `catch` → lỗi tải tin im lặng; thêm catch + toast [frontend/src/features/workspace/ChatHistoryPopover.tsx:48-51]
- [x] [Review][Patch] `close_postgres_checkpointer` không reset `_checkpointer = None` (stale ref sau shutdown); thêm reset [backend/src/modules/orchestrator/infrastructure/postgres_checkpointer.py:35-40]

### Deferred (giới hạn MVP đã ghi nhận — xem deferred-work.md)

- [x] [Review][Defer] In-memory `run_registry` không hoạt động đa worker — `send_message` và `/stream` có thể rơi vào process khác → 404. Spec đã ghi nhận: single-server MVP, Redis Pub/Sub khi scale-out. [backend/src/modules/orchestrator/infrastructure/run_registry.py] — deferred, accepted MVP design
- [x] [Review][Defer] TOCTOU: với answer rất ngắn/rỗng, background task có thể `delete_run` trước khi client mở `/stream` → 404 mất câu trả lời. Mock answer hiện đủ dài (≈80 ký tự × 50ms). [backend/src/modules/orchestrator/application/use_cases.py] — deferred, low-risk với mock hiện tại
- [x] [Review][Defer] Gửi đồng thời cùng `thread_id` (2 tab) không serialize ở backend → race checkpoint LangGraph. Frontend đã chặn bằng `isStreaming`. [backend/src/modules/orchestrator/application/use_cases.py] — deferred, MVP
- [x] [Review][Defer] `POST /invoke` (AC#5, endpoint test) không lưu user/assistant message vào `chat_messages` — chỉ checkpointer; frontend không dùng. [backend/src/modules/orchestrator/application/use_cases.py:71-91] — deferred, endpoint chỉ phục vụ kiểm thử AC#5

### Dismissed (false positive)

- EventSource "không gửi được auth header" → auth qua cookie httponly + `withCredentials: true` là đủ (đã verify `get_current_user` đọc `request.cookies`).
- CORS cho SSE `withCredentials` → `CORSMiddleware(allow_credentials=True)` đã xử lý header cho mọi response gồm StreamingResponse.
