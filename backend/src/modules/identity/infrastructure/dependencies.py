from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.modules.identity.domain.repositories import UserCredentialRepository, UserRepository
from backend.src.modules.identity.infrastructure.credential_repository import PostgresUserCredentialRepository
from backend.src.modules.identity.infrastructure.postgres_repository import PostgresUserRepository
from backend.src.shared.infra.database import get_db_session


async def get_user_repository(
    db: AsyncSession = Depends(get_db_session),
) -> AsyncGenerator[UserRepository, None]:
    yield PostgresUserRepository(db)


async def get_credential_repository(
    db: AsyncSession = Depends(get_db_session),
) -> AsyncGenerator[UserCredentialRepository, None]:
    yield PostgresUserCredentialRepository(db)
