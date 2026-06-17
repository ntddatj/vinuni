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
_REDIRECT_CODES = {301, 302, 303, 307, 308}
_MAX_REDIRECTS = 5

# PostgreSQL TEXT không cho phép NUL (\x00); fitz/PyMuPDF hay sinh NUL + control char C0 với
# một số font/encoding PDF → insert chunk sẽ raise và cả paper fail. Bỏ NUL + C0 (giữ \t \n \r)
# và DEL (\x7f). Dùng translate(None) để xoá thay vì thay khoảng trắng.
_CONTROL_CHAR_MAP = {
    c: None for c in range(0x20) if c not in (0x09, 0x0A, 0x0D)
}
_CONTROL_CHAR_MAP[0x7F] = None


def _sanitize_text(text: str) -> str:
    """Loại NUL + control char C0/DEL khỏi text trích từ PDF để chunk/insert an toàn vào Postgres."""
    if not text:
        return text
    return text.translate(_CONTROL_CHAR_MAP)


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


async def _get_following_redirects(client, url: str):
    """GET tự follow redirect THỦ CÔNG, re-validate mỗi hop bằng SSRF guard.

    Tại sao không dùng follow_redirects=True của httpx: nguồn miễn phí như arXiv trả
    pdf_url dạng ``http://arxiv.org/pdf/...`` rồi 301 sang ``https://`` — phải follow thì
    mới tải được. Nhưng để httpx tự follow sẽ bỏ qua SSRF guard ở mỗi Location mới (có thể
    bị redirect về host nội bộ). Nên ta tự lặp và kiểm tra từng URL đích.

    Trả về Response cuối (status không phải redirect), hoặc None nếu redirect tới URL không
    an toàn / vượt quá _MAX_REDIRECTS.
    """
    current = url
    for _ in range(_MAX_REDIRECTS + 1):
        resp = await client.get(current)
        if resp.status_code not in _REDIRECT_CODES:
            return resp
        location = resp.headers.get("location")
        if not location:
            return resp
        next_url = str(resp.url.join(location))
        if not _is_public_http_url(next_url):
            logger.warning("Bỏ qua redirect tới URL không an toàn (SSRF guard): %s", next_url)
            return None
        current = next_url
    logger.warning("Quá nhiều redirect khi tải PDF: %s", url)
    return None


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


async def _extract_text(paper: PaperORM, session_factory=None) -> str:
    """Lấy text từ file local, hoặc download PDF từ pdf_url, fallback abstract."""
    text = ""
    if paper.file_path and Path(paper.file_path).exists():
        ext = Path(paper.file_path).suffix.lower()
        mime_type = _EXT_TO_MIME.get(ext, "application/pdf")
        try:
            text = DocumentParser().extract_text(paper.file_path, mime_type)
        except Exception as e:
            # File local hỏng/cụt (vd crash giữa lúc persist) — không fail cả paper,
            # để fallback abstract bên dưới xử lý.
            logger.warning("Không thể parse file local %s: %s", paper.file_path, e)
            text = ""
    elif paper.pdf_url:
        text = await _download_and_persist_pdf(paper.pdf_url, paper, session_factory)

    if not text.strip() and paper.abstract:
        text = paper.abstract
    return _sanitize_text(text)


async def _download_and_persist_pdf(pdf_url: str, paper: PaperORM, session_factory) -> str:
    """Download PDF từ URL. Nếu Open Access & ≤ 20MB: persist vào disk, set paper.file_path.
    Luôn trả về text (để chunking). File > 20MB: không persist nhưng vẫn trả text."""
    import tempfile

    import fitz
    import httpx

    settings = get_settings()
    _MAX_PERSIST_BYTES = settings.max_upload_size_mb * 1024 * 1024

    if not _is_public_http_url(pdf_url):
        logger.warning("Bỏ qua pdf_url không an toàn (SSRF guard): %s", pdf_url)
        return ""

    try:
        # follow_redirects=False: tự follow thủ công qua _get_following_redirects để re-validate
        # mỗi hop bằng SSRF guard (arXiv 301 http→https cần follow mới tải được).
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
            resp = await _get_following_redirects(client, pdf_url)
        if resp is None or resp.status_code != 200:
            return ""
        if len(resp.content) > _MAX_PDF_BYTES:
            logger.warning("PDF quá lớn (%d bytes) — bỏ qua parse", len(resp.content))
            return ""
        ctype = resp.headers.get("content-type", "").lower()
        if ctype and "application/pdf" not in ctype and "octet-stream" not in ctype:
            logger.warning("Content-Type không phải PDF (%s) — bỏ qua", ctype)
            return ""

        # Persist nếu ≤ 20MB (NFR2)
        if len(resp.content) > _MAX_PERSIST_BYTES:
            logger.info(
                "PDF %d bytes > %dMB — không persist, chỉ extract text",
                len(resp.content), settings.max_upload_size_mb,
            )
        elif session_factory is not None:
            target_dir = Path(settings.papers_dir) / paper.user_id
            target_dir.mkdir(parents=True, exist_ok=True)
            file_path = str(target_dir / f"{paper.id}.pdf")
            try:
                Path(file_path).write_bytes(resp.content)
                # Update file_path trong DB qua session riêng để không ảnh hưởng transaction chính
                async with session_factory() as update_db:
                    result = await update_db.execute(
                        select(PaperORM).where(PaperORM.id == paper.id)
                    )
                    p = result.scalar_one_or_none()
                    if p:
                        p.file_path = file_path
                        await update_db.commit()
            except Exception as e:
                # Lỗi persist (đĩa đầy, DB lỗi...) KHÔNG được làm hỏng cả job ingestion (Dev Note #8)
                # — vẫn extract text bên dưới. Dọn file ghi dở để không serve PDF cụt sau này.
                logger.warning("Không thể persist PDF cho paper %s: %s", paper.id, e)
                Path(file_path).unlink(missing_ok=True)

        # Extract text từ resp.content (đã có trong memory)
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
            text = await _extract_text(paper, session_factory)

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
            # Race guard: user có thể đã xóa paper trong lúc embedding. delete_paper_soft đã
            # xóa chunks + set is_deleted; nếu ta ghi chunk mới lúc này thì paper đã xóa lại
            # xuất hiện trong RAG (phá vỡ AC#1). Refresh trạng thái mới nhất rồi bỏ qua nếu đã xóa.
            await db.refresh(paper)
            if paper.is_deleted:
                logger.info("Paper %s đã bị xóa trong lúc ingest — bỏ qua lưu chunks", paper_id)
                await publish_completed(redis, paper_id)
                return
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
