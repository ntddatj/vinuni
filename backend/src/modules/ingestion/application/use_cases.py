import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.modules.ingestion.domain.entities import Paper, UploadedFile
from backend.src.modules.ingestion.domain.exceptions import (
    FileTooLargeError,
    IngestionFileNotFoundError,
    ProjectAccessDeniedError,
    UnsupportedFileTypeError,
)
from backend.src.modules.ingestion.infrastructure.document_parser import DocumentParser
from backend.src.modules.ingestion.infrastructure.file_storage import LocalFileStorage
from backend.src.modules.ingestion.infrastructure.metadata_extractor import LLMMetadataExtractor
from backend.src.modules.ingestion.infrastructure.postgres_repository import (
    PostgresPaperRepository,
    PostgresUploadedFileRepository,
    is_project_owned_by_user,
)
from backend.src.shared.infra.settings import get_settings

ALLOWED_EXTENSIONS: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class UploadDocumentUseCase:
    async def execute(
        self,
        file_bytes: bytes,
        original_filename: str,
        project_id: str,
        user_id: str,
        db: AsyncSession,
    ) -> dict:
        settings = get_settings()
        if len(file_bytes) > settings.max_upload_size_mb * 1024 * 1024:
            raise FileTooLargeError(settings.max_upload_size_mb)

        ext = Path(original_filename).suffix.lower()
        mime_type = ALLOWED_EXTENSIONS.get(ext)
        if mime_type is None:
            raise UnsupportedFileTypeError(ext or original_filename)

        if not await is_project_owned_by_user(db, project_id, user_id):
            raise ProjectAccessDeniedError(project_id)

        storage = LocalFileStorage()
        file_id, file_path = storage.save(file_bytes, original_filename, user_id)

        uploaded_file = UploadedFile(
            id=file_id,
            project_id=project_id,
            user_id=user_id,
            original_filename=original_filename,
            file_path=file_path,
            mime_type=mime_type,
            file_size=len(file_bytes),
        )
        file_repo = PostgresUploadedFileRepository(db)
        await file_repo.save_uploaded_file(uploaded_file)
        await db.commit()

        parser = DocumentParser()
        text = parser.extract_text(file_path, mime_type)

        extractor = LLMMetadataExtractor(user_id=user_id, db=db)
        metadata = await extractor.extract(text, original_filename)

        return {
            "file_id": file_id,
            "title": metadata.title,
            "authors": metadata.authors,
            "abstract": metadata.abstract,
            "year": metadata.year,
        }


class ConfirmMetadataUseCase:
    async def execute(
        self,
        file_id: str,
        title: str,
        authors: list[str],
        abstract: str,
        year: int | None,
        project_id: str,
        user_id: str,
        db: AsyncSession,
    ) -> dict:
        file_repo = PostgresUploadedFileRepository(db)
        uploaded_file = await file_repo.find_by_id(file_id)
        # Chặn IDOR: file phải tồn tại VÀ thuộc về user hiện tại. Trả 404 (không phải 403)
        # để không tiết lộ sự tồn tại của file thuộc user khác.
        if uploaded_file is None or uploaded_file.user_id != user_id:
            raise IngestionFileNotFoundError(file_id)

        # Lấy project_id từ chính uploaded_file (đã được validate ownership lúc upload),
        # bỏ qua project_id client gửi để tránh cross-project confirm.
        paper = Paper(
            id=str(uuid.uuid4()),
            project_id=uploaded_file.project_id,
            user_id=user_id,
            title=title,
            authors=authors,
            abstract=abstract,
            year=year,
            source="manual",
            file_path=uploaded_file.file_path,
            status="pending",
        )
        paper_repo = PostgresPaperRepository(db)
        saved_paper = await paper_repo.save_paper(paper)
        await db.commit()

        return {
            "document_id": saved_paper.id,
            "message": "Tài liệu đã được thêm vào hàng đợi xử lý",
        }
