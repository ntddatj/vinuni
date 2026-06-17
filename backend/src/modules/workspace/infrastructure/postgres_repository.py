from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.modules.workspace.domain.entities import Project
from backend.src.modules.workspace.domain.repositories import ProjectRepository
from backend.src.modules.workspace.infrastructure.orm_models import ProjectORM, SyncOutboxORM


def _orm_to_entity(orm: ProjectORM) -> Project:
    return Project(
        id=orm.id,
        user_id=orm.user_id,
        name=orm.name,
        description=orm.description,
        is_deleted=orm.is_deleted,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class PostgresProjectRepository(ProjectRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def save(self, project: Project) -> Project:
        orm = ProjectORM(
            id=project.id,
            user_id=project.user_id,
            name=project.name,
            description=project.description,
            is_deleted=project.is_deleted,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )
        self._db.add(orm)
        await self._db.commit()
        await self._db.refresh(orm)
        return _orm_to_entity(orm)

    async def find_by_id(self, project_id: str) -> Project | None:
        result = await self._db.execute(
            select(ProjectORM).where(ProjectORM.id == project_id, ProjectORM.is_deleted.is_(False))
        )
        orm = result.scalar_one_or_none()
        return _orm_to_entity(orm) if orm else None

    async def list_by_user(self, user_id: str, limit: int = 10, offset: int = 0, name: str | None = None) -> list[Project]:
        stmt = (
            select(ProjectORM)
            .where(ProjectORM.user_id == user_id, ProjectORM.is_deleted.is_(False))
        )
        if name:
            stmt = stmt.where(ProjectORM.name.ilike(f"%{name}%"))
        stmt = stmt.order_by(ProjectORM.updated_at.desc()).limit(limit).offset(offset)
        result = await self._db.execute(stmt)
        return [_orm_to_entity(row) for row in result.scalars().all()]

    async def count_by_user(self, user_id: str, name: str | None = None) -> int:
        stmt = select(func.count()).select_from(ProjectORM).where(
            ProjectORM.user_id == user_id,
            ProjectORM.is_deleted.is_(False),
        )
        if name:
            stmt = stmt.where(ProjectORM.name.ilike(f"%{name}%"))
        result = await self._db.execute(stmt)
        return result.scalar_one()

    async def update(self, project: Project) -> Project:
        result = await self._db.execute(
            select(ProjectORM).where(ProjectORM.id == project.id)
        )
        orm = result.scalar_one_or_none()
        if not orm:
            return project
        orm.name = project.name
        orm.description = project.description
        orm.updated_at = project.updated_at
        await self._db.commit()
        await self._db.refresh(orm)
        return _orm_to_entity(orm)

    async def soft_delete(self, project: Project) -> None:
        result = await self._db.execute(
            select(ProjectORM).where(ProjectORM.id == project.id)
        )
        orm = result.scalar_one_or_none()
        if not orm:
            return

        now = datetime.now(timezone.utc)
        orm.is_deleted = True
        orm.deleted_at = now
        orm.updated_at = now

        outbox_event = SyncOutboxORM(
            event_type="PROJECT_DELETED",
            project_id=project.id,
            payload={"project_id": project.id, "user_id": project.user_id},
        )
        self._db.add(outbox_event)
        await self._db.commit()
