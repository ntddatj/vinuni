"""ARQ worker xử lý ingestion tài liệu bất đồng bộ.

Chạy: ``python -m arq backend.worker.WorkerSettings``

Pipeline: load paper → parse/download text → chunk → embed → save chunks → indexed.
Tiến trình được publish vào Redis để SSE endpoint stream về frontend.
"""
import ipaddress
import logging
import socket
from pathlib import Path
from urllib.parse import urlparse

from arq.connections import RedisSettings
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.src.modules.identity.infrastructure.orm_models import (  # noqa: F401
    UserCredentialORM,
    UserORM,
)
from backend.src.modules.ingestion.infrastructure.chunk_orm_models import (
    ChildChunkORM,
    ParentChunkORM,
)
from backend.src.modules.ingestion.infrastructure.document_parser import DocumentParser
from backend.src.modules.ingestion.infrastructure.embedding_client import (
    EMBEDDING_DIM,
    GeminiEmbeddingClient,
)
from backend.src.modules.ingestion.infrastructure.orm_models import PaperORM
from backend.src.modules.ingestion.infrastructure.task_progress import (
    publish_completed,
    publish_error,
    publish_progress,
)
from backend.src.modules.ingestion.infrastructure.text_chunker import chunk_text
from backend.src.modules.workspace.infrastructure.orm_models import (  # noqa: F401
    ProjectORM,
    SyncOutboxORM,
)
from backend.src.shared.infra.settings import get_settings

logger = logging.getLogger(__name__)

_EXT_TO_MIME = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

_MAX_PDF_BYTES = 50 * 1024 * 1024  # 50MB — chặn tải file quá lớn


def _is_public_http_url(url: str) -> bool:
    """SSRF guard: chỉ cho http/https tới host công khai.

    Chặn IP nội bộ/loopback/link-local (vd 169.254.169.254 metadata), reserved, multicast.
    Best-effort (có TOCTOU với httpx re-resolve) nhưng đủ cho MVP.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = parsed.hostname
    if not host:
        return False
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(host, port)
    except Exception:
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return False
    return True


async def startup(ctx) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    ctx["engine"] = engine
    ctx["session_factory"] = async_sessionmaker(engine, expire_on_commit=False)
    # ctx['redis'] do arq cung cấp sẵn (ArqRedis) — hỗ trợ .get()/.set()/.delete()


async def shutdown(ctx) -> None:
    engine = ctx.get("engine")
    if engine is not None:
        await engine.dispose()


async def _extract_text(paper: PaperORM) -> str:
    """Lấy text từ file local, hoặc download PDF từ pdf_url, fallback abstract."""
    text = ""
    if paper.file_path and Path(paper.file_path).exists():
        ext = Path(paper.file_path).suffix.lower()
        mime_type = _EXT_TO_MIME.get(ext, "application/pdf")
        text = DocumentParser().extract_text(paper.file_path, mime_type)
    elif paper.pdf_url:
        text = await _download_pdf_text(paper.pdf_url)

    if not text.strip() and paper.abstract:
        text = paper.abstract
    return text


async def _download_pdf_text(pdf_url: str) -> str:
    import tempfile

    import httpx

    if not _is_public_http_url(pdf_url):
        logger.warning("Bỏ qua pdf_url không an toàn (SSRF guard): %s", pdf_url)
        return ""

    try:
        # follow_redirects=False để tránh bị redirect tới host nội bộ sau khi đã qua guard.
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
            resp = await client.get(pdf_url)
        if resp.status_code != 200:
            return ""
        if len(resp.content) > _MAX_PDF_BYTES:
            logger.warning("PDF quá lớn (%d bytes) từ %s — bỏ qua", len(resp.content), pdf_url)
            return ""
        ctype = resp.headers.get("content-type", "").lower()
        if ctype and "application/pdf" not in ctype and "octet-stream" not in ctype:
            logger.warning("Content-Type không phải PDF (%s) từ %s — bỏ qua", ctype, pdf_url)
            return ""
        import fitz  # PyMuPDF

        tmp_path = ""
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(resp.content)
                tmp_path = tmp.name
            doc = fitz.open(tmp_path)
            try:
                text = "".join(doc[i].get_text() for i in range(min(len(doc), 20)))
            finally:
                doc.close()
            return text
        finally:
            if tmp_path:
                Path(tmp_path).unlink(missing_ok=True)
    except Exception as e:
        logger.warning("Không thể download/parse PDF từ %s: %s", pdf_url, e)
        return ""


async def ingest_paper_task(ctx, paper_id: str) -> None:
    """Background task: parse → chunk → embed → save. Publish tiến trình qua Redis."""
    redis = ctx["redis"]
    session_factory: async_sessionmaker = ctx["session_factory"]

    async with session_factory() as db:
        paper: PaperORM | None = None
        try:
            await publish_progress(redis, paper_id, 0, "initializing", "Đang khởi tạo...")
            result = await db.execute(select(PaperORM).where(PaperORM.id == paper_id))
            paper = result.scalar_one_or_none()
            if paper is None:
                await publish_error(redis, paper_id, f"Paper {paper_id} không tồn tại")
                return

            paper.status = "processing"
            await db.commit()

            # Bước 2: lấy text
            await publish_progress(redis, paper_id, 10, "reading", "Đang đọc tài liệu...")
            text = await _extract_text(paper)

            if not text.strip():
                # Không có nội dung — đánh dấu indexed nhưng không có chunk
                paper.status = "indexed"
                await db.commit()
                await publish_completed(redis, paper_id)
                return

            # Bước 3: chunk
            await publish_progress(redis, paper_id, 30, "chunking", "Đang phân tích nội dung...")
            chunks = chunk_text(text)

            # Bước 4: embed
            await publish_progress(redis, paper_id, 60, "embedding", "Đang tạo vector nhúng...")
            all_child_texts = [c for _, children in chunks for c in children]
            embedding_client = GeminiEmbeddingClient(user_id=paper.user_id, db=db)
            all_embeddings = await embedding_client.embed_batch(all_child_texts)

            # Chuẩn hóa độ dài: provider có thể trả thiếu/thừa vector. Pad zero-vector / cắt bớt
            # để tránh IndexError làm fail cả paper trên happy path.
            if len(all_embeddings) != len(all_child_texts):
                logger.warning(
                    "Embedding trả %d vector nhưng có %d child chunk — chuẩn hóa độ dài",
                    len(all_embeddings),
                    len(all_child_texts),
                )
                if len(all_embeddings) < len(all_child_texts):
                    all_embeddings = all_embeddings + [
                        [0.0] * EMBEDDING_DIM
                        for _ in range(len(all_child_texts) - len(all_embeddings))
                    ]
                else:
                    all_embeddings = all_embeddings[: len(all_child_texts)]

            # Bước 5: save
            await publish_progress(redis, paper_id, 85, "saving", "Đang lưu dữ liệu...")
            # Idempotent: xóa chunk cũ của paper này (re-ingest / job trùng) trước khi ghi mới.
            await db.execute(delete(ChildChunkORM).where(ChildChunkORM.paper_id == paper_id))
            await db.execute(delete(ParentChunkORM).where(ParentChunkORM.paper_id == paper_id))
            child_idx = 0
            for p_idx, (parent_content, child_texts) in enumerate(chunks):
                parent_chunk = ParentChunkORM(
                    paper_id=paper_id,
                    project_id=paper.project_id,
                    content=parent_content,
                    chunk_index=p_idx,
                )
                db.add(parent_chunk)
                await db.flush()  # để có parent_chunk.id

                for c_idx, child_text in enumerate(child_texts):
                    db.add(
                        ChildChunkORM(
                            parent_chunk_id=parent_chunk.id,
                            paper_id=paper_id,
                            project_id=paper.project_id,
                            content=child_text,
                            embedding=all_embeddings[child_idx],
                            chunk_index=c_idx,
                        )
                    )
                    child_idx += 1

            paper.status = "indexed"
            await db.commit()

            await publish_completed(redis, paper_id)
            logger.info("Ingested paper %s successfully", paper_id)

        except Exception as e:
            logger.exception("Failed to ingest paper %s: %s", paper_id, e)
            # Session có thể đã hỏng do lỗi giữa transaction (vd flush chunks). Rollback TRƯỚC
            # rồi cập nhật status trong transaction sạch, nếu không commit 'failed' cũng raise
            # và paper kẹt vĩnh viễn ở 'processing'.
            try:
                await db.rollback()
                result = await db.execute(select(PaperORM).where(PaperORM.id == paper_id))
                failed_paper = result.scalar_one_or_none()
                if failed_paper is not None:
                    failed_paper.status = "failed"
                    await db.commit()
            except Exception:
                logger.exception("Không thể cập nhật trạng thái 'failed' cho paper %s", paper_id)
                await db.rollback()
            await publish_error(redis, paper_id, str(e))


class WorkerSettings:
    functions = [ingest_paper_task]
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 2  # NFR4: concurrency_limit=2
    job_timeout = 600  # 10 phút max per job
    keep_result = 300

    # arq đọc redis_settings như một ATTRIBUTE (RedisSettings), không gọi như method.
    # Để @classmethod sẽ khiến arq nhận classmethod object → worker không kết nối được Redis.
    redis_settings = RedisSettings.from_dsn(get_settings().arq_redis_url)
