---
baseline_commit: a2ec1a7
---

# Story 3.1: [Backend] Định Tuyến & Quản Lý Phiên Chat với PostgresSaver

Status: done

## Story

Với vai trò là người dùng,
Tôi muốn tạo phiên chat mới và xem lịch sử chat,
Để tôi lưu lại mạch suy nghĩ nghiên cứu theo từng dự án.

## Acceptance Criteria

1. **Given** DB có bảng `chat_threads` và `chat_messages` (migration 008)
   **When** gọi `POST /api/chat/threads` với `project_id` và `title` (tùy chọn)
   **Then** tạo thread mới liên kết với `user_id` và `project_id`, trả về `201` với object thread

2. **Given** thread tồn tại và thuộc về user hiện tại
   **When** gọi `GET /api/chat/threads/{thread_id}/messages`
   **Then** trả về danh sách tin nhắn (có thể rỗng) theo thứ tự `created_at` tăng dần

3. **Given** user đã có nhiều threads trong các dự án khác nhau
   **When** gọi `GET /api/chat/threads?project_id={project_id}`
   **Then** trả về danh sách threads của user trong dự án đó, sắp xếp mới nhất trước

4. **Given** user cố gắng truy cập thread của user khác
   **When** gọi `GET /api/chat/threads/{thread_id}/messages`
   **Then** trả về `HTTP 403 Forbidden`

5. **Given** backend khởi động
   **When** lifespan function chạy
   **Then** PostgresSaver (`AsyncPostgresSaver`) gọi `saver.setup()` để tạo các bảng checkpoint LangGraph (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations`) nếu chưa tồn tại

> 🔍 **Cách nghiệm thu trực quan:**
> 1. Swagger UI: gọi `POST /api/chat/threads` với `{"projectId": "<valid_project_id>"}` — nhận 201 với thread object.
> 2. Swagger UI: gọi `GET /api/chat/threads/{thread_id}/messages` — nhận 200 với list rỗng `[]`.
> 3. Swagger UI: gọi `GET /api/chat/threads?projectId=<valid_project_id>` — thấy thread vừa tạo.
> 4. Dùng token của user khác, gọi GET messages của thread trên — nhận 403.
> 5. Kiểm tra DB (DBeaver): thấy bảng `chat_threads`, `chat_messages`, `checkpoints`, `checkpoint_blobs` tồn tại.

---

## Tasks / Subtasks

### BACKEND — Migration & Module Foundation

- [x] Task 1: Tạo Alembic migration 008 — bảng `chat_threads` và `chat_messages` (AC: #1, #2)
  - [x] 1.1 Tạo `backend/alembic/versions/008_create_chat_tables.py` với `revision="008"`, `down_revision="007"`:
    ```python
    def upgrade() -> None:
        op.create_table(
            "chat_threads",
            sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("project_id", sa.UUID(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("title", sa.String(500), nullable=False, server_default="Cuộc trò chuyện mới"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("idx_chat_threads_user_id", "chat_threads", ["user_id"])
        op.create_index("idx_chat_threads_project_id", "chat_threads", ["project_id"])
        op.create_index("idx_chat_threads_project_user", "chat_threads", ["project_id", "user_id"])

        op.create_table(
            "chat_messages",
            sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("thread_id", sa.UUID(), sa.ForeignKey("chat_threads.id", ondelete="CASCADE"), nullable=False),
            sa.Column("role", sa.String(50), nullable=False),  # 'user' | 'assistant'
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("idx_chat_messages_thread_id", "chat_messages", ["thread_id"])

    def downgrade() -> None:
        op.drop_table("chat_messages")
        op.drop_table("chat_threads")
    ```

- [x] Task 2: Cập nhật `backend/requirements.txt` — thêm LangGraph dependencies (AC: #5)
  - [x] 2.1 Thêm vào `backend/requirements.txt`:
    ```
    # LangGraph & Chat (Story 3.1)
    langgraph>=0.2.0
    langgraph-checkpoint-postgres>=2.0.0
    psycopg[binary]>=3.1.0
    ```
  - [x] 2.2 Chạy `pip install langgraph langgraph-checkpoint-postgres "psycopg[binary]"` trong `.venv` để cài ngay
  - **Lưu ý:** `psycopg[binary]` dùng riêng cho `AsyncPostgresSaver`, KHÔNG thay thế `asyncpg` (vẫn giữ `asyncpg` cho SQLAlchemy)

- [x] Task 3: Tạo cấu trúc module `orchestrator` (AC: #1–#5)
  - [x] 3.1 Tạo thư mục và `__init__.py` cho tất cả sublayers:
    ```
    backend/src/modules/orchestrator/
    ├── __init__.py
    ├── domain/
    │   ├── __init__.py
    │   ├── entities.py
    │   ├── repositories.py
    │   └── exceptions.py
    ├── application/
    │   ├── __init__.py
    │   ├── dtos.py
    │   └── use_cases.py
    ├── infrastructure/
    │   ├── __init__.py
    │   ├── orm_models.py
    │   ├── postgres_checkpointer.py
    │   ├── repository.py
    │   └── dependencies.py
    └── presentation/
        ├── __init__.py
        ├── router.py
        └── schemas.py
    ```

### BACKEND — Domain Layer

- [x] Task 4: Tạo Domain Entities và Exceptions (AC: #1, #2, #4)
  - [x] 4.1 Tạo `backend/src/modules/orchestrator/domain/entities.py`:
    ```python
    from dataclasses import dataclass, field
    from datetime import datetime


    @dataclass
    class ChatThread:
        id: str
        user_id: str
        project_id: str
        title: str
        created_at: datetime
        updated_at: datetime


    @dataclass
    class ChatMessage:
        id: str
        thread_id: str
        role: str  # 'user' | 'assistant'
        content: str
        created_at: datetime
    ```
  - [x] 4.2 Tạo `backend/src/modules/orchestrator/domain/exceptions.py`:
    ```python
    class ThreadNotFoundError(Exception):
        def __init__(self, thread_id: str) -> None:
            super().__init__(f"Thread {thread_id} không tồn tại")
            self.thread_id = thread_id

    class ThreadAccessDeniedError(Exception):
        def __init__(self, thread_id: str) -> None:
            super().__init__(f"Không có quyền truy cập thread {thread_id}")
            self.thread_id = thread_id
    ```
  - [x] 4.3 Tạo `backend/src/modules/orchestrator/domain/repositories.py`:
    ```python
    from abc import ABC, abstractmethod
    from backend.src.modules.orchestrator.domain.entities import ChatThread, ChatMessage


    class ChatThreadRepository(ABC):
        @abstractmethod
        async def create(self, user_id: str, project_id: str, title: str) -> ChatThread: ...

        @abstractmethod
        async def find_by_id(self, thread_id: str) -> ChatThread | None: ...

        @abstractmethod
        async def list_by_project(self, user_id: str, project_id: str) -> list[ChatThread]: ...

        @abstractmethod
        async def list_messages(self, thread_id: str) -> list[ChatMessage]: ...
    ```

### BACKEND — Infrastructure Layer

- [x] Task 5: Tạo ORM Models (AC: #1, #2)
  - [x] 5.1 Tạo `backend/src/modules/orchestrator/infrastructure/orm_models.py`:
    ```python
    import uuid
    from datetime import datetime
    from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, func, text
    from sqlalchemy.orm import Mapped, mapped_column
    from backend.src.shared.infra.database import Base


    class ChatThreadORM(Base):
        __tablename__ = "chat_threads"

        id: Mapped[str] = mapped_column(
            Uuid(as_uuid=False), primary_key=True,
            default=lambda: str(uuid.uuid4()), server_default=text("gen_random_uuid()"),
        )
        user_id: Mapped[str] = mapped_column(
            Uuid(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False, index=True,
        )
        project_id: Mapped[str] = mapped_column(
            Uuid(as_uuid=False), ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False, index=True,
        )
        title: Mapped[str] = mapped_column(String(500), nullable=False, server_default="Cuộc trò chuyện mới")
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
        updated_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
        )


    class ChatMessageORM(Base):
        __tablename__ = "chat_messages"

        id: Mapped[str] = mapped_column(
            Uuid(as_uuid=False), primary_key=True,
            default=lambda: str(uuid.uuid4()), server_default=text("gen_random_uuid()"),
        )
        thread_id: Mapped[str] = mapped_column(
            Uuid(as_uuid=False), ForeignKey("chat_threads.id", ondelete="CASCADE"),
            nullable=False, index=True,
        )
        role: Mapped[str] = mapped_column(String(50), nullable=False)
        content: Mapped[str] = mapped_column(Text, nullable=False)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ```

- [x] Task 6: Tạo PostgresSaver infrastructure (AC: #5)
  - [x] 6.1 Tạo `backend/src/modules/orchestrator/infrastructure/postgres_checkpointer.py`:
    ```python
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from backend.src.shared.infra.settings import get_settings

    _checkpointer: AsyncPostgresSaver | None = None


    async def get_postgres_checkpointer() -> AsyncPostgresSaver:
        """Trả về singleton AsyncPostgresSaver. Phải gọi setup_postgres_checkpointer() trước."""
        global _checkpointer
        if _checkpointer is None:
            raise RuntimeError("PostgresSaver chưa được khởi tạo. Gọi setup_postgres_checkpointer() trong lifespan.")
        return _checkpointer


    async def setup_postgres_checkpointer() -> AsyncPostgresSaver:
        """Khởi tạo AsyncPostgresSaver và tạo các bảng checkpoint LangGraph nếu chưa có.
        Gọi từ lifespan() trong main.py.
        Dùng connection string postgres:// (psycopg3 format), KHÔNG phải postgresql+asyncpg://.
        """
        global _checkpointer
        settings = get_settings()
        # AsyncPostgresSaver dùng psycopg3, cần postgresql:// scheme (không phải +asyncpg)
        conn_str = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        _checkpointer = AsyncPostgresSaver.from_conn_string(conn_str)
        async with _checkpointer as saver:
            await saver.setup()
        return _checkpointer
    ```
  - **Lưu ý quan trọng:** `AsyncPostgresSaver.from_conn_string()` dùng `psycopg3` (không phải `asyncpg`). Connection string phải dùng `postgresql://` scheme, không phải `postgresql+asyncpg://` (dùng cho SQLAlchemy). Convert bằng `.replace("postgresql+asyncpg://", "postgresql://")`.

- [x] Task 7: Tạo Repository Implementation và Dependencies
  - [x] 7.1 Tạo `backend/src/modules/orchestrator/infrastructure/repository.py`:
    ```python
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession
    from backend.src.modules.orchestrator.domain.entities import ChatThread, ChatMessage
    from backend.src.modules.orchestrator.domain.repositories import ChatThreadRepository
    from backend.src.modules.orchestrator.infrastructure.orm_models import ChatThreadORM, ChatMessageORM


    def _to_thread(orm: ChatThreadORM) -> ChatThread:
        return ChatThread(
            id=orm.id, user_id=orm.user_id, project_id=orm.project_id,
            title=orm.title, created_at=orm.created_at, updated_at=orm.updated_at,
        )


    def _to_message(orm: ChatMessageORM) -> ChatMessage:
        return ChatMessage(
            id=orm.id, thread_id=orm.thread_id, role=orm.role,
            content=orm.content, created_at=orm.created_at,
        )


    class PostgresChatThreadRepository(ChatThreadRepository):
        def __init__(self, db: AsyncSession) -> None:
            self._db = db

        async def create(self, user_id: str, project_id: str, title: str) -> ChatThread:
            orm = ChatThreadORM(user_id=user_id, project_id=project_id, title=title)
            self._db.add(orm)
            await self._db.commit()
            await self._db.refresh(orm)
            return _to_thread(orm)

        async def find_by_id(self, thread_id: str) -> ChatThread | None:
            result = await self._db.execute(
                select(ChatThreadORM).where(ChatThreadORM.id == thread_id)
            )
            orm = result.scalar_one_or_none()
            return _to_thread(orm) if orm else None

        async def list_by_project(self, user_id: str, project_id: str) -> list[ChatThread]:
            result = await self._db.execute(
                select(ChatThreadORM)
                .where(ChatThreadORM.user_id == user_id, ChatThreadORM.project_id == project_id)
                .order_by(ChatThreadORM.updated_at.desc())
            )
            return [_to_thread(row) for row in result.scalars().all()]

        async def list_messages(self, thread_id: str) -> list[ChatMessage]:
            result = await self._db.execute(
                select(ChatMessageORM)
                .where(ChatMessageORM.thread_id == thread_id)
                .order_by(ChatMessageORM.created_at.asc())
            )
            return [_to_message(row) for row in result.scalars().all()]
    ```
  - [x] 7.2 Tạo `backend/src/modules/orchestrator/infrastructure/dependencies.py`:
    ```python
    from fastapi import Depends
    from sqlalchemy.ext.asyncio import AsyncSession
    from backend.src.shared.infra.database import get_db_session as get_db
    from backend.src.modules.orchestrator.domain.repositories import ChatThreadRepository
    from backend.src.modules.orchestrator.infrastructure.repository import PostgresChatThreadRepository


    def get_thread_repository(
        db: AsyncSession = Depends(get_db),
    ) -> ChatThreadRepository:
        return PostgresChatThreadRepository(db)
    ```

### BACKEND — Application Layer

- [x] Task 8: Tạo DTOs và Use Cases (AC: #1–#4)
  - [x] 8.1 Tạo `backend/src/modules/orchestrator/application/dtos.py`:
    ```python
    from dataclasses import dataclass


    @dataclass
    class CreateThreadDTO:
        user_id: str
        project_id: str
        title: str = "Cuộc trò chuyện mới"


    @dataclass
    class GetThreadMessagesDTO:
        thread_id: str
        requesting_user_id: str


    @dataclass
    class ListThreadsDTO:
        user_id: str
        project_id: str
    ```
  - [x] 8.2 Tạo `backend/src/modules/orchestrator/application/use_cases.py`:
    ```python
    from backend.src.modules.orchestrator.application.dtos import CreateThreadDTO, GetThreadMessagesDTO, ListThreadsDTO
    from backend.src.modules.orchestrator.domain.entities import ChatThread, ChatMessage
    from backend.src.modules.orchestrator.domain.exceptions import ThreadAccessDeniedError, ThreadNotFoundError
    from backend.src.modules.orchestrator.domain.repositories import ChatThreadRepository


    class CreateThreadUseCase:
        def __init__(self, repo: ChatThreadRepository) -> None:
            self._repo = repo

        async def execute(self, dto: CreateThreadDTO) -> ChatThread:
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
        def __init__(self, repo: ChatThreadRepository) -> None:
            self._repo = repo

        async def execute(self, dto: ListThreadsDTO) -> list[ChatThread]:
            return await self._repo.list_by_project(
                user_id=dto.user_id, project_id=dto.project_id
            )
    ```

### BACKEND — Presentation Layer

- [x] Task 9: Tạo Schemas và Router (AC: #1–#4)
  - [x] 9.1 Tạo `backend/src/modules/orchestrator/presentation/schemas.py`:
    ```python
    from datetime import datetime
    from pydantic import BaseModel, ConfigDict, Field
    from pydantic.alias_generators import to_camel


    class CreateThreadRequest(BaseModel):
        model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
        project_id: str
        title: str = Field(default="Cuộc trò chuyện mới", max_length=500)


    class ChatThreadResponse(BaseModel):
        model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
        id: str
        user_id: str
        project_id: str
        title: str
        created_at: datetime
        updated_at: datetime


    class ChatMessageResponse(BaseModel):
        model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
        id: str
        thread_id: str
        role: str
        content: str
        created_at: datetime
    ```
  - [x] 9.2 Tạo `backend/src/modules/orchestrator/presentation/router.py`:
    ```python
    from fastapi import APIRouter, Depends, HTTPException, Query, status
    from backend.src.modules.identity.domain.entities import User
    from backend.src.modules.identity.infrastructure.auth_dependencies import get_current_user
    from backend.src.modules.orchestrator.application.dtos import CreateThreadDTO, GetThreadMessagesDTO, ListThreadsDTO
    from backend.src.modules.orchestrator.application.use_cases import (
        CreateThreadUseCase, GetThreadMessagesUseCase, ListThreadsUseCase,
    )
    from backend.src.modules.orchestrator.domain.exceptions import ThreadAccessDeniedError, ThreadNotFoundError
    from backend.src.modules.orchestrator.domain.repositories import ChatThreadRepository
    from backend.src.modules.orchestrator.infrastructure.dependencies import get_thread_repository
    from backend.src.modules.orchestrator.presentation.schemas import (
        ChatMessageResponse, ChatThreadResponse, CreateThreadRequest,
    )

    router = APIRouter(prefix="/chat", tags=["chat"])


    @router.post("/threads", response_model=ChatThreadResponse, status_code=201)
    async def create_thread(
        request: CreateThreadRequest,
        current_user: User = Depends(get_current_user),
        repo: ChatThreadRepository = Depends(get_thread_repository),
    ) -> ChatThreadResponse:
        use_case = CreateThreadUseCase(repo)
        result = await use_case.execute(
            CreateThreadDTO(user_id=current_user.id, project_id=request.project_id, title=request.title)
        )
        return ChatThreadResponse.model_validate(result, from_attributes=True)


    @router.get("/threads", response_model=list[ChatThreadResponse])
    async def list_threads(
        project_id: str = Query(..., alias="projectId"),
        current_user: User = Depends(get_current_user),
        repo: ChatThreadRepository = Depends(get_thread_repository),
    ) -> list[ChatThreadResponse]:
        use_case = ListThreadsUseCase(repo)
        results = await use_case.execute(ListThreadsDTO(user_id=current_user.id, project_id=project_id))
        return [ChatThreadResponse.model_validate(t, from_attributes=True) for t in results]


    @router.get("/threads/{thread_id}/messages", response_model=list[ChatMessageResponse])
    async def get_thread_messages(
        thread_id: str,
        current_user: User = Depends(get_current_user),
        repo: ChatThreadRepository = Depends(get_thread_repository),
    ) -> list[ChatMessageResponse]:
        use_case = GetThreadMessagesUseCase(repo)
        try:
            messages = await use_case.execute(
                GetThreadMessagesDTO(thread_id=thread_id, requesting_user_id=current_user.id)
            )
        except ThreadNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except ThreadAccessDeniedError as e:
            raise HTTPException(status_code=403, detail=str(e)) from e
        return [ChatMessageResponse.model_validate(m, from_attributes=True) for m in messages]
    ```
  - **Lưu ý:** `GET /api/chat/threads` dùng query param `projectId` (camelCase để nhất quán với frontend) qua `Query(..., alias="projectId")`.

### BACKEND — Wire Up trong main.py

- [x] Task 10: Cập nhật `backend/main.py` (AC: #1, #5)
  - [x] 10.1 Thêm import ORM models (để `create_all` tạo bảng trong dev mode):
    ```python
    from backend.src.modules.orchestrator.infrastructure.orm_models import ChatMessageORM, ChatThreadORM  # noqa: F401
    ```
  - [x] 10.2 Thêm import router:
    ```python
    from backend.src.modules.orchestrator.presentation.router import router as orchestrator_router
    ```
  - [x] 10.3 Thêm import PostgresSaver setup:
    ```python
    from backend.src.modules.orchestrator.infrastructure.postgres_checkpointer import setup_postgres_checkpointer
    ```
  - [x] 10.4 Trong `lifespan()`, thêm sau `create_all`:
    ```python
    await setup_postgres_checkpointer()
    ```
  - [x] 10.5 Thêm include_router TRƯỚC `register_error_handlers(app)`:
    ```python
    app.include_router(orchestrator_router, prefix="/api")
    ```
  - **Thứ tự import ORM**: Đặt import `ChatThreadORM, ChatMessageORM` gần các ORM import khác (theo alphabet: sau `ingestion`, trước `workspace`).

### BACKEND — Error Handlers

- [x] Task 11: Cập nhật error handlers (AC: #4)
  - [x] 11.1 Cập nhật `backend/src/shared/api/error_handlers.py` — thêm handlers cho orchestrator exceptions:
    ```python
    from backend.src.modules.orchestrator.domain.exceptions import ThreadAccessDeniedError, ThreadNotFoundError

    # Trong register_error_handlers():
    @app.exception_handler(ThreadNotFoundError)
    async def thread_not_found_handler(request: Request, exc: ThreadNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ThreadAccessDeniedError)
    async def thread_access_denied_handler(request: Request, exc: ThreadAccessDeniedError) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": str(exc)})
    ```
  - **Lưu ý:** Dù router đã có try/except, thêm global handlers theo pattern nhất quán của codebase (xem `ProjectAccessDeniedError` pattern từ workspace).

### BACKEND — Tests

- [x] Task 12: Viết unit tests (AC: #1, #2, #3, #4)
  - [x] 12.1 Tạo `tests/unit/orchestrator/__init__.py` (file rỗng)
  - [x] 12.2 Tạo `tests/unit/orchestrator/test_chat_threads.py`:
    ```python
    """Unit tests cho chat thread use cases (AC #1–#4)."""
    from unittest.mock import AsyncMock
    import pytest
    from backend.src.modules.orchestrator.application.dtos import CreateThreadDTO, GetThreadMessagesDTO
    from backend.src.modules.orchestrator.application.use_cases import (
        CreateThreadUseCase, GetThreadMessagesUseCase,
    )
    from backend.src.modules.orchestrator.domain.entities import ChatThread, ChatMessage
    from backend.src.modules.orchestrator.domain.exceptions import ThreadAccessDeniedError, ThreadNotFoundError
    from datetime import datetime, timezone


    def _make_thread(user_id: str = "user-1", project_id: str = "proj-1") -> ChatThread:
        now = datetime.now(timezone.utc)
        return ChatThread(id="thread-1", user_id=user_id, project_id=project_id,
                          title="Test", created_at=now, updated_at=now)


    @pytest.mark.asyncio
    async def test_create_thread_success():
        """CreateThreadUseCase tạo thread thành công."""
        repo = AsyncMock()
        thread = _make_thread()
        repo.create.return_value = thread
        use_case = CreateThreadUseCase(repo)
        result = await use_case.execute(CreateThreadDTO(user_id="user-1", project_id="proj-1"))
        repo.create.assert_called_once_with(user_id="user-1", project_id="proj-1", title="Cuộc trò chuyện mới")
        assert result.id == "thread-1"


    @pytest.mark.asyncio
    async def test_get_messages_raises_not_found():
        """GetThreadMessagesUseCase raise ThreadNotFoundError khi thread không tồn tại."""
        repo = AsyncMock()
        repo.find_by_id.return_value = None
        use_case = GetThreadMessagesUseCase(repo)
        with pytest.raises(ThreadNotFoundError):
            await use_case.execute(GetThreadMessagesDTO(thread_id="ghost", requesting_user_id="user-1"))


    @pytest.mark.asyncio
    async def test_get_messages_raises_access_denied_for_other_user():
        """GetThreadMessagesUseCase raise ThreadAccessDeniedError khi user không sở hữu thread."""
        repo = AsyncMock()
        repo.find_by_id.return_value = _make_thread(user_id="owner-99")
        use_case = GetThreadMessagesUseCase(repo)
        with pytest.raises(ThreadAccessDeniedError):
            await use_case.execute(GetThreadMessagesDTO(thread_id="thread-1", requesting_user_id="other-user"))


    @pytest.mark.asyncio
    async def test_get_messages_returns_empty_list():
        """GetThreadMessagesUseCase trả về list rỗng khi không có tin nhắn."""
        repo = AsyncMock()
        repo.find_by_id.return_value = _make_thread(user_id="user-1")
        repo.list_messages.return_value = []
        use_case = GetThreadMessagesUseCase(repo)
        result = await use_case.execute(GetThreadMessagesDTO(thread_id="thread-1", requesting_user_id="user-1"))
        assert result == []
    ```
  - [x] 12.3 Chạy tests: `cd /home/agent/github/C2-App-053 && python -m pytest tests/unit/orchestrator/ --noconftest -v`

---

## Dev Notes

### ⚠️ LỖI THƯỜNG GẶP — PHẢI TRÁNH

1. **KHÔNG dùng `postgresql+asyncpg://` cho AsyncPostgresSaver** — AsyncPostgresSaver dùng `psycopg3`, cần URL scheme `postgresql://`. SQLAlchemy dùng `postgresql+asyncpg://` (khác nhau). Phải convert: `url.replace("postgresql+asyncpg://", "postgresql://")`.

2. **KHÔNG quên import ORM vào `main.py`** — Pattern bắt buộc: `ChatThreadORM` và `ChatMessageORM` phải import với `# noqa: F401` để `Base.metadata.create_all` tạo bảng trong dev mode.

3. **KHÔNG dùng `asyncpg` cho PostgresSaver** — `langgraph-checkpoint-postgres` cần `psycopg[binary]>=3.1.0`. Đây là hai thư viện riêng biệt phục vụ mục đích khác nhau và hoàn toàn có thể coexist.

4. **KHÔNG gọi `saver.setup()` ngoài context manager** — `AsyncPostgresSaver.from_conn_string()` trả về async context manager. Phải dùng `async with saver as s: await s.setup()`.

5. **KHÔNG bỏ qua alias `projectId` trong GET /chat/threads** — Frontend gửi `projectId` (camelCase). Dùng `Query(..., alias="projectId")` để FastAPI nhận đúng.

6. **KHÔNG dùng Tailwind CSS** — Codebase dùng CSS Modules + CSS Variables. (Không áp dụng cho story này vì toàn Backend.)

7. **KHÔNG thêm ChatThreadRepository vào Domain ngoài Abstract Base** — Repository implementation phải ở `infrastructure/repository.py`, KHÔNG ở `domain/`. Domain chỉ định nghĩa interface (ABC).

8. **KHÔNG quên `--noconftest` khi chạy unit tests** — Pattern từ story 2.6: `pytest tests/unit/ --noconftest` để tránh import LangGraph trong conftest.py gây lỗi khi library chưa cài.

9. **KHÔNG đặt PostgresSaver singleton ở global scope trực tiếp** — Dùng hàm `get_postgres_checkpointer()` để lazy-load và handle trường hợp chưa setup. Pattern giống `get_redis()` trong story 2.6.

10. **KHÔNG tạo thêm endpoint DELETE thread trong story này** — Scope story 3.1 chỉ có POST (tạo), GET list, GET messages. DELETE sẽ implement ở story sau nếu cần.

---

### § Cấu Trúc Bảng Database (story 3.1)

```sql
-- Bảng thread chat (do chúng ta quản lý)
CREATE TABLE chat_threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL DEFAULT 'Cuộc trò chuyện mới',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);
CREATE INDEX idx_chat_threads_user_id ON chat_threads(user_id);
CREATE INDEX idx_chat_threads_project_id ON chat_threads(project_id);
CREATE INDEX idx_chat_threads_project_user ON chat_threads(project_id, user_id);

-- Bảng tin nhắn (do chúng ta quản lý, riêng với PostgresSaver checkpoints)
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL REFERENCES chat_threads(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,  -- 'user' | 'assistant'
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);
CREATE INDEX idx_chat_messages_thread_id ON chat_messages(thread_id);

-- Các bảng PostgresSaver (tự tạo bởi saver.setup()) — KHÔNG tạo trong migration:
-- checkpoints, checkpoint_blobs, checkpoint_writes, checkpoint_migrations
```

**Phân biệt 2 hệ thống lưu trữ:**
- `chat_threads` + `chat_messages`: Do chúng ta kiểm soát, phục vụ API history (story 3.1, 3.2)
- `checkpoints` + ...: Do LangGraph quản lý hoàn toàn qua `PostgresSaver`, lưu trạng thái Agent (story 3.3+)

---

### § PostgresSaver Setup Flow

```python
# Trong backend/main.py — lifespan function
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    # [MỚI story 3.1] Khởi tạo LangGraph PostgresSaver
    await setup_postgres_checkpointer()
    yield
    await engine.dispose()
```

```python
# backend/src/modules/orchestrator/infrastructure/postgres_checkpointer.py
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

async def setup_postgres_checkpointer() -> None:
    settings = get_settings()
    # Chuyển từ SQLAlchemy URL sang psycopg3 URL
    conn_str = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    async with AsyncPostgresSaver.from_conn_string(conn_str) as saver:
        await saver.setup()  # Tạo checkpoints, checkpoint_blobs, checkpoint_writes, checkpoint_migrations
    # Lưu ý: singleton saver sẽ được khởi tạo lại khi cần dùng trong story 3.3+
```

---

### § Kiến Trúc Module Orchestrator (theo Architecture 9.7)

Module `orchestrator` được thiết kế theo Hexagonal Architecture (như tất cả modules khác):

```
backend/src/modules/orchestrator/
├── domain/          # Không phụ thuộc bất kỳ thư viện nào
│   ├── entities.py  # ChatThread, ChatMessage (dataclass, no ORM)
│   ├── repositories.py  # Abstract interfaces (ABC)
│   └── exceptions.py    # ThreadNotFoundError, ThreadAccessDeniedError
├── application/     # Business logic thuần túy
│   ├── dtos.py      # CreateThreadDTO, GetThreadMessagesDTO, ListThreadsDTO
│   └── use_cases.py # CreateThreadUseCase, GetThreadMessagesUseCase, ListThreadsUseCase
├── infrastructure/  # Triển khai cụ thể — SQLAlchemy, psycopg3
│   ├── orm_models.py              # ChatThreadORM, ChatMessageORM
│   ├── postgres_checkpointer.py  # AsyncPostgresSaver setup & singleton
│   ├── repository.py              # PostgresChatThreadRepository
│   └── dependencies.py           # FastAPI Depends factory
└── presentation/    # HTTP layer
    ├── router.py    # 3 endpoints: POST /threads, GET /threads, GET /threads/{id}/messages
    └── schemas.py   # CreateThreadRequest, ChatThreadResponse, ChatMessageResponse
```

---

### § API Endpoints Tổng Quan

| Method | Endpoint | Auth | Request | Response |
|--------|----------|------|---------|----------|
| POST | `/api/chat/threads` | JWT cookie | `{projectId, title?}` | `ChatThreadResponse` (201) |
| GET | `/api/chat/threads?projectId=<uuid>` | JWT cookie | query param | `list[ChatThreadResponse]` (200) |
| GET | `/api/chat/threads/{thread_id}/messages` | JWT cookie | path param | `list[ChatMessageResponse]` (200) |

**Không có endpoint POST message trong story này** — Gửi message là story 3.4 (Chat SSE Streaming).

---

### § Pattern Import ORM trong main.py

Pattern bắt buộc (xem các stories trước):
```python
# Thêm gần các import ORM khác (theo alphabet)
from backend.src.modules.orchestrator.infrastructure.orm_models import ChatMessageORM, ChatThreadORM  # noqa: F401
```

Thứ tự import trong `main.py` (sau khi thêm):
1. `admin.infrastructure.settings_orm` — SystemSettingORM
2. `identity.infrastructure.orm_models` — UserCredentialORM, UserORM
3. `ingestion.infrastructure.chunk_orm_models` — ChildChunkORM, ParentChunkORM
4. `ingestion.infrastructure.orm_models` — PaperORM, UploadedFileORM
5. **[MỚI]** `orchestrator.infrastructure.orm_models` — ChatMessageORM, ChatThreadORM
6. `workspace.infrastructure.orm_models` — ProjectORM, SyncOutboxORM

---

### § Learnings từ Stories Trước

1. **`get_db_session as get_db` pattern** — Tất cả routers import: `from backend.src.shared.infra.database import get_db_session as get_db`. Xem ingestion/presentation/router.py.

2. **Pydantic `alias_generator=to_camel, populate_by_name=True`** — Bắt buộc cho tất cả Presentation schemas. Frontend nhận `camelCase`, backend internal dùng `snake_case`.

3. **`model_validate(obj, from_attributes=True)`** — Khi convert từ dataclass sang Pydantic schema.

4. **`@dataclass` cho Domain Entities** — Không dùng Pydantic ở Domain layer. Xem workspace/domain/entities.py cho pattern.

5. **Repository Pattern với ABC** — Domain định nghĩa abstract, Infrastructure implement cụ thể. Xem workspace/domain/repositories.py + workspace/infrastructure/repository.py.

6. **`--noconftest` cho pytest** — Dùng khi chạy unit tests riêng lẻ để tránh import LangGraph chưa cài.

7. **Error handler global vs try/except trong router** — Codebase dùng cả hai: global handlers trong `error_handlers.py` AND try/except trong router. Thêm cả hai cho nhất quán.

---

### § Files Cần Đọc Trước Khi Implement

Đây là các file UPDATE (không phải mới) — phải đọc kỹ trước khi sửa:
- `backend/main.py` — hiểu lifespan pattern và import order
- `backend/src/shared/api/error_handlers.py` — hiểu pattern thêm exception handler
- `backend/requirements.txt` — thêm đúng chỗ, không duplicate

Pattern tham khảo (READ-ONLY):
- `backend/src/modules/workspace/` — hexagonal architecture đầy đủ nhất để tham khảo
- `backend/src/modules/ingestion/presentation/router.py` — pattern try/except và Depends(get_db)
- `backend/alembic/versions/007_create_system_settings_table.py` — migration pattern gần nhất

---

### § Cấu Trúc File — Tổng Quan

```
backend/
├── requirements.txt                                    # CẬP NHẬT: +langgraph, +langgraph-checkpoint-postgres, +psycopg[binary]
├── main.py                                             # CẬP NHẬT: +ChatThreadORM/ChatMessageORM import, +orchestrator_router, +setup_postgres_checkpointer()
├── alembic/versions/
│   └── 008_create_chat_tables.py                      # MỚI: bảng chat_threads, chat_messages
└── src/modules/
    ├── orchestrator/                                   # MỚI module (toàn bộ)
    │   ├── __init__.py
    │   ├── domain/
    │   │   ├── __init__.py
    │   │   ├── entities.py          # ChatThread, ChatMessage
    │   │   ├── repositories.py      # ChatThreadRepository (ABC)
    │   │   └── exceptions.py        # ThreadNotFoundError, ThreadAccessDeniedError
    │   ├── application/
    │   │   ├── __init__.py
    │   │   ├── dtos.py              # CreateThreadDTO, GetThreadMessagesDTO, ListThreadsDTO
    │   │   └── use_cases.py         # 3 use cases
    │   ├── infrastructure/
    │   │   ├── __init__.py
    │   │   ├── orm_models.py        # ChatThreadORM, ChatMessageORM
    │   │   ├── postgres_checkpointer.py  # AsyncPostgresSaver setup
    │   │   ├── repository.py        # PostgresChatThreadRepository
    │   │   └── dependencies.py      # get_thread_repository()
    │   └── presentation/
    │       ├── __init__.py
    │       ├── router.py            # POST /chat/threads, GET /chat/threads, GET /chat/threads/{id}/messages
    │       └── schemas.py           # Request/Response schemas
    └── shared/api/
        └── error_handlers.py        # CẬP NHẬT: +ThreadNotFoundError, +ThreadAccessDeniedError handlers

tests/unit/
└── orchestrator/
    ├── __init__.py                  # MỚI
    └── test_chat_threads.py         # MỚI: 4 unit tests
```

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- ✅ Tạo Alembic migration 008 với bảng `chat_threads` và `chat_messages` (AC #1, #2)
- ✅ Thêm LangGraph dependencies vào requirements.txt: `langgraph`, `langgraph-checkpoint-postgres`, `psycopg[binary]` (AC #5)
- ✅ Tạo toàn bộ module `orchestrator` theo Hexagonal Architecture: domain/application/infrastructure/presentation
- ✅ Implement `AsyncPostgresSaver` setup trong lifespan qua `setup_postgres_checkpointer()` — dùng `postgresql://` scheme cho psycopg3 (AC #5)
- ✅ 3 endpoints: `POST /api/chat/threads` (201), `GET /api/chat/threads?projectId=...` (200), `GET /api/chat/threads/{id}/messages` (200) (AC #1, #2, #3)
- ✅ Authorization check: thread không thuộc user → `ThreadAccessDeniedError` → HTTP 403 (AC #4)
- ✅ 4 unit tests pass: create_thread_success, not_found_error, access_denied_error, empty_messages (AC #1–#4)
- ✅ Không có regression trong test suite (pre-existing failures từ trước story này không thay đổi)

### File List

**Tạo mới:**
- `backend/alembic/versions/008_create_chat_tables.py`
- `backend/src/modules/orchestrator/__init__.py`
- `backend/src/modules/orchestrator/domain/__init__.py`
- `backend/src/modules/orchestrator/domain/entities.py`
- `backend/src/modules/orchestrator/domain/exceptions.py`
- `backend/src/modules/orchestrator/domain/repositories.py`
- `backend/src/modules/orchestrator/application/__init__.py`
- `backend/src/modules/orchestrator/application/dtos.py`
- `backend/src/modules/orchestrator/application/use_cases.py`
- `backend/src/modules/orchestrator/infrastructure/__init__.py`
- `backend/src/modules/orchestrator/infrastructure/orm_models.py`
- `backend/src/modules/orchestrator/infrastructure/postgres_checkpointer.py`
- `backend/src/modules/orchestrator/infrastructure/repository.py`
- `backend/src/modules/orchestrator/infrastructure/dependencies.py`
- `backend/src/modules/orchestrator/presentation/__init__.py`
- `backend/src/modules/orchestrator/presentation/schemas.py`
- `backend/src/modules/orchestrator/presentation/router.py`
- `tests/unit/orchestrator/__init__.py`
- `tests/unit/orchestrator/test_chat_threads.py`

**Cập nhật:**
- `requirements.txt` — thêm LangGraph dependencies
- `backend/main.py` — thêm ORM imports, orchestrator_router, setup_postgres_checkpointer()
- `backend/src/shared/api/error_handlers.py` — thêm ThreadNotFoundError, ThreadAccessDeniedError handlers
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — cập nhật story 3.1 status

### Change Log

| Date | Version | Description |
|------|---------|-------------|
| 2026-06-17 | 1.0 | Tạo story 3.1: Chat Session DB & Core APIs với PostgresSaver. AC #1–#5 được định nghĩa. |
| 2026-06-17 | 1.1 | Triển khai hoàn chỉnh: migration 008, module orchestrator (Hexagonal Architecture), 3 API endpoints, PostgresSaver setup, 4 unit tests pass. |

---

## Review Findings

> Code review adversarial (Blind Hunter + Edge Case Hunter + Acceptance Auditor) — 2026-06-17. Baseline `a2ec1a7`.
> AC Coverage: AC #1–#5 đều SATISFIED về mặt chức năng của story 3.1. Các finding dưới đây là lỗi tiềm ẩn / bảo mật / độ bền chưa phá vỡ AC hiện tại nhưng cần xử lý.

### Decision-needed (đã giải quyết 2026-06-17)

- Đã giải quyết tất cả. ① PostgresSaver singleton → **defer** sang story 3.3. ② Authorization cấp project (IDOR) → **patch** (làm ngay). ③ `setup_postgres_checkpointer` fail-fast lúc startup → **dismiss** (giữ nguyên, coi checkpoint DB là hard dependency).

### Patch (đã áp dụng 2026-06-17)

- [x] [Review][Patch] Thiếu authorization cấp project khi tạo/list thread (IDOR) → thêm `_assert_project_owned_by_user` (inject `ProjectRepository`); raise `ProjectNotFoundError`/`ProjectAccessDeniedError` → 404/403 ở router [use_cases.py, router.py]
- [x] [Review][Patch] UUID không hợp lệ → 500 → type `thread_id`/`projectId` là `uuid.UUID` (path/query) + `project_id: UUID` trong `CreateThreadRequest` → FastAPI trả 422 thay vì 500 [router.py, schemas.py]
- [x] [Review][Patch] Convert conn string thiếu scheme → thêm `_to_psycopg_conn_str` xử lý `postgresql+asyncpg`/`+psycopg`/`+psycopg2`/`postgres://` [postgres_checkpointer.py]
- [x] [Review][Patch] `create()` không rollback khi commit fail → bọc `try/except IntegrityError: rollback; raise` [repository.py:create]
- [x] [Review][Patch] `list_by_project` thiếu tiebreaker → thêm `.order_by(updated_at.desc(), id.desc())` [repository.py:list_by_project]
- [x] [Review][Patch] `title` không strip → thêm `field_validator` strip + fallback về default khi rỗng [schemas.py:CreateThreadRequest]

### Deferred

- [x] [Review][Defer] PostgresSaver singleton lưu context manager chưa mở — deferred sang story 3.3: AC#5 (tạo bảng checkpoint lúc startup) hiện vẫn đúng vì `setup()` chạy trong `async with`; `get_postgres_checkpointer()` chưa có caller. Quyết định vòng đời connection (AsyncConnectionPool / enter CM trong lifespan) sẽ có ngữ cảnh tốt hơn khi story 3.3 thực sự dùng checkpointer. [postgres_checkpointer.py:16-28]
- [x] [Review][Defer] Cột `role` (chat_messages) không có CHECK/enum constraint, chỉ comment `'user' | 'assistant'` — deferred, chưa có write-path message ở story 3.1, đúng theo spec [orm_models.py, 008_create_chat_tables.py]
- [x] [Review][Defer] `updated_at` chỉ có `onupdate=func.now()` ở ORM, migration không tạo DB trigger — deferred, nhất quán với pattern workspace ORM hiện có [orm_models.py:ChatThreadORM]
- [x] [Review][Defer] Index trùng phần tiền tố: `idx_chat_threads_project_id` + composite `idx_chat_threads_project_user` — deferred, khớp spec verbatim, ảnh hưởng nhỏ [008_create_chat_tables.py]
