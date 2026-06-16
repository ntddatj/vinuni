from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.modules.workspace.domain.repositories import ProjectRepository
from backend.src.modules.workspace.infrastructure.postgres_repository import PostgresProjectRepository
from backend.src.shared.infra.database import get_db_session


async def get_project_repository(
    db: AsyncSession = Depends(get_db_session),
) -> AsyncGenerator[ProjectRepository, None]:
    yield PostgresProjectRepository(db)
