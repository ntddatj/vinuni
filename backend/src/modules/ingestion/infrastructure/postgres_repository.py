from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.modules.ingestion.domain.entities import Paper, UploadedFile
from backend.src.modules.ingestion.infrastructure.orm_models import PaperORM, UploadedFileORM
from backend.src.modules.workspace.infrastructure.orm_models import ProjectORM


async def is_project_owned_by_user(db: AsyncSession, project_id: str, user_id: str) -> bool:
    """True nếu project tồn tại, chưa xoá, và thuộc về user_id. Dùng để chặn IDOR."""
    result = await db.execute(
        select(ProjectORM.id).where(
            ProjectORM.id == project_id,
            ProjectORM.user_id == user_id,
            ProjectORM.is_deleted.is_(False),
        )
    )
    return result.scalar_one_or_none() is not None


class PostgresUploadedFileRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def save_uploaded_file(self, entity: UploadedFile) -> UploadedFile:
        orm = UploadedFileORM(
            id=entity.id,
            project_id=entity.project_id,
            user_id=entity.user_id,
            original_filename=entity.original_filename,
            file_path=entity.file_path,
            mime_type=entity.mime_type,
            file_size=entity.file_size,
        )
        self._db.add(orm)
        await self._db.flush()
        return entity

    async def find_by_id(self, file_id: str) -> UploadedFile | None:
        result = await self._db.execute(select(UploadedFileORM).where(UploadedFileORM.id == file_id))
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return UploadedFile(
            id=str(orm.id),
            project_id=str(orm.project_id),
            user_id=str(orm.user_id),
            original_filename=orm.original_filename,
            file_path=orm.file_path,
            mime_type=orm.mime_type,
            file_size=orm.file_size,
        )


class PostgresPaperRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def save_paper(self, entity: Paper) -> Paper:
        orm = PaperORM(
            id=entity.id,
            project_id=entity.project_id,
            user_id=entity.user_id,
            title=entity.title,
            authors=entity.authors,
            abstract=entity.abstract,
            year=entity.year,
            source=entity.source,
            file_path=entity.file_path,
            status=entity.status,
        )
        self._db.add(orm)
        await self._db.flush()
        return entity
