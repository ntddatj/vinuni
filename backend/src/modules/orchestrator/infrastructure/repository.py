from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.modules.orchestrator.domain.entities import ChatMessage, ChatThread
from backend.src.modules.orchestrator.domain.repositories import ChatThreadRepository
from backend.src.modules.orchestrator.infrastructure.orm_models import ChatMessageORM, ChatThreadORM


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
        try:
            await self._db.commit()
        except IntegrityError:
            await self._db.rollback()
            raise
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
            .order_by(ChatThreadORM.updated_at.desc(), ChatThreadORM.id.desc())
        )
        return [_to_thread(row) for row in result.scalars().all()]

    async def list_messages(self, thread_id: str) -> list[ChatMessage]:
        result = await self._db.execute(
            select(ChatMessageORM)
            .where(ChatMessageORM.thread_id == thread_id)
            .order_by(ChatMessageORM.created_at.asc())
        )
        return [_to_message(row) for row in result.scalars().all()]

    async def save_message(self, thread_id: str, role: str, content: str) -> ChatMessage:
        orm = ChatMessageORM(thread_id=thread_id, role=role, content=content)
        self._db.add(orm)
        await self._db.commit()
        await self._db.refresh(orm)
        return _to_message(orm)
