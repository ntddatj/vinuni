from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.modules.orchestrator.domain.repositories import ChatThreadRepository
from backend.src.modules.orchestrator.infrastructure.repository import PostgresChatThreadRepository
from backend.src.shared.infra.database import get_db_session as get_db


def get_thread_repository(
    db: AsyncSession = Depends(get_db),
) -> ChatThreadRepository:
    return PostgresChatThreadRepository(db)
