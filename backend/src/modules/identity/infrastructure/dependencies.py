from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.modules.identity.domain.repositories import UserRepository
from backend.src.modules.identity.infrastructure.postgres_repository import PostgresUserRepository
from backend.src.shared.infra.database import get_db_session


async def get_user_repository(
    db: AsyncSession = Depends(get_db_session),
) -> AsyncGenerator[UserRepository, None]:
    yield PostgresUserRepository(db)
