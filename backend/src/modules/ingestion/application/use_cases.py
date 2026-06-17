import asyncio
import contextlib
import uuid
from pathlib import Path

from fastapi import HTTPException
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.modules.ingestion.domain.entities import Paper, UploadedFile
from backend.src.modules.ingestion.domain.exceptions import (
    FileTooLargeError,
    IngestionFileNotFoundError,
    ProjectAccessDeniedError,
    ProjectPaperLimitExceededError,
    UnsupportedFileTypeError,
)
from backend.src.modules.ingestion.infrastructure.document_parser import DocumentParser
from backend.src.modules.ingestion.infrastructure.file_storage import LocalFileStorage
from backend.src.modules.ingestion.infrastructure.metadata_extractor import LLMMetadataExtractor
from backend.src.modules.ingestion.infrastructure.postgres_repository import (
    PostgresPaperRepository,
    PostgresUploadedFileRepository,
    count_papers_by_project,
    is_project_owned_by_user,
)
from backend.src.shared.infra.redis_client import get_redis
from backend.src.shared.infra.settings import get_settings

INGEST_TASK_NAME = "ingest_paper_task"

# Lua: chỉ xoá lock nếu token khớp (compare-and-delete nguyên tử).
_RELEASE_LOCK_LUA = (
    "if redis.call('get', KEYS[1]) == ARGV[1] then "
    "return redis.call('del', KEYS[1]) else return 0 end"
)


@contextlib.asynccontextmanager
async def _paper_limit_lock(redis, project_id: str):
    """Distributed lock chống TOCTOU khi check+save paper.

    Dùng token duy nhất + Lua compare-and-delete để KHÔNG xoá nhầm lock của
    request khác khi TTL (10s) hết giữa chừng. Redis sập → fail-closed (503).
    """
    lock_key = f"paper_limit_lock:{project_id}"
    token = str(uuid.uuid4())
    acquired = None
    try:
        for attempt in range(2):
            acquired = await redis.set(lock_key, token, nx=True, ex=10)
            if acquired:
                break
            if attempt == 0:
                await asyncio.sleep(0.2)
    except RedisError as e:
        raise HTTPException(
            status_code=503, detail="Hệ thống đang bận, vui lòng thử lại"
        ) from e

    if not acquired:
        raise HTTPException(status_code=503, detail="Hệ thống đang bận, vui lòng thử lại")

    try:
        yield
    finally:
        with contextlib.suppress(RedisError):
            await redis.eval(_RELEASE_LOCK_LUA, 1, lock_key, token)


async def get_max_papers_limit(db: AsyncSession) -> int:
    """Đọc MAX_PAPERS_PER_PROJECT từ DB, fallback về 15 nếu không có hoặc parse lỗi."""
    import logging

    from backend.src.modules.admin.infrastructure.settings_orm import get_setting

    raw = await get_setting(db, "MAX_PAPERS_PER_PROJECT", default="15")
    try:
        return int(raw)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        logging.warning("MAX_PAPERS_PER_PROJECT value '%s' is not a valid int, fallback to 15", raw)
        return 15

ALLOWED_EXTENSIONS: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


async def enqueue_ingestion_task(paper_id: str) -> None:
    """Đẩy job ingestion vào arq queue.

    Tạo pool ngắn hạn từ settings.arq_redis_url rồi đóng — đủ dùng cho MVP.
    (Production nên giữ pool qua lifespan của FastAPI app.)
    """
    from arq import create_pool
    from arq.connections import RedisSettings

    settings = get_settings()
    redis = await create_pool(RedisSettings.from_dsn(settings.arq_redis_url))
    try:
        # _job_id cố định theo paper_id để arq tự khử trùng: double-submit / retry sẽ không
        # đẩy thêm job khi job cùng paper đang pending/running → tránh nhân đôi chunk.
        await redis.enqueue_job(INGEST_TASK_NAME, paper_id, _job_id=f"ingest:{paper_id}")
    finally:
        await redis.aclose()


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
        the_project_id = uploaded_file.project_id
        redis = await get_redis()

        saved_paper_id: str
        async with _paper_limit_lock(redis, the_project_id):
            max_limit = await get_max_papers_limit(db)
            current_count = await count_papers_by_project(db, the_project_id)
            if current_count >= max_limit:
                raise ProjectPaperLimitExceededError(the_project_id, max_limit)

            paper = Paper(
                id=str(uuid.uuid4()),
                project_id=the_project_id,
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
            saved_paper_id = saved_paper.id

        # Đẩy job ingestion vào arq queue (bất đồng bộ — không block response)
        await enqueue_ingestion_task(saved_paper_id)

        return {
            "document_id": saved_paper_id,
            "message": "Tài liệu đã được thêm vào hàng đợi xử lý",
        }


class IngestFromSearchUseCase:
    async def execute(
        self,
        *,
        project_id: str,
        user_id: str,
        title: str,
        authors: list[str],
        abstract: str,
        year: int | None,
        doi: str | None,
        arxiv_id: str | None,
        url: str | None,
        pdf_url: str | None,
        source: str,
        db: AsyncSession,
    ) -> dict:
        if not await is_project_owned_by_user(db, project_id, user_id):
            raise ProjectAccessDeniedError(project_id)

        redis = await get_redis()

        paper_id = str(uuid.uuid4())
        async with _paper_limit_lock(redis, project_id):
            max_limit = await get_max_papers_limit(db)
            current_count = await count_papers_by_project(db, project_id)
            if current_count >= max_limit:
                raise ProjectPaperLimitExceededError(project_id, max_limit)

            paper_repo = PostgresPaperRepository(db)
            await paper_repo.save_search_paper(
                paper_id=paper_id,
                project_id=project_id,
                user_id=user_id,
                title=title,
                authors=authors,
                abstract=abstract,
                year=year,
                source=source,
                doi=doi,
                arxiv_id=arxiv_id,
                url=url,
                pdf_url=pdf_url,
                status="pending",
            )
            await db.commit()

        await enqueue_ingestion_task(paper_id)

        return {
            "document_id": paper_id,
            "message": "Tài liệu đã được thêm vào hàng đợi xử lý",
        }
