"""Garbage Collection cron task — ARCH-2.

Chạy lúc 2h sáng mỗi ngày:
1. Postgres hard-delete papers/projects is_deleted=true AND deleted_at < now-7d
   (chunks cascade FK; xóa file vật lý paper.file_path)
2. Neo4j DETACH DELETE node :Deleted đã quá ngưỡng
3. Dọn sync_outbox: processed=true AND processed_at < now-30d

Hai store xử lý độc lập — lỗi Neo4j không rollback Postgres đã commit.
"""
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from backend.src.modules.admin.infrastructure.settings_orm import get_setting
from backend.src.modules.ingestion.infrastructure.orm_models import PaperORM
from backend.src.modules.workspace.infrastructure.orm_models import ProjectORM, SyncOutboxORM

logger = logging.getLogger(__name__)

# Fallback khi system_settings chưa seed / DB không đọc được. Giá trị "chính thức" do Admin
# cấu hình ở system_settings (key GC_RETENTION_DAYS) — mirror pattern MAX_PAPERS_PER_PROJECT.
_DEFAULT_GC_RETENTION_DAYS = 7


async def _get_int_setting(session_factory: async_sessionmaker, key: str, default: int) -> int:
    """Đọc setting số nguyên từ system_settings (Admin cấu hình), fallback về default."""
    try:
        async with session_factory() as db:
            raw = await get_setting(db, key, None)
    except Exception as e:
        logger.warning("Không đọc được setting %s từ DB (%s) — dùng default %d", key, e, default)
        return default
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        logger.warning("Setting %s='%s' không phải int — dùng default %d", key, raw, default)
        return default


async def garbage_collection_task(ctx) -> None:
    """arq cron task: hard-delete dữ liệu đã xóa mềm quá ngưỡng + dọn Neo4j + dọn outbox."""
    session_factory: async_sessionmaker = ctx["session_factory"]
    neo4j_driver = ctx.get("neo4j_driver")
    retention_days = await _get_int_setting(
        session_factory, "GC_RETENTION_DAYS", _DEFAULT_GC_RETENTION_DAYS
    )

    threshold = datetime.now(timezone.utc) - timedelta(days=retention_days)
    outbox_threshold = datetime.now(timezone.utc) - timedelta(days=30)

    # --- Bước 1: Postgres hard-delete ---
    await _gc_postgres(session_factory, threshold, outbox_threshold)

    # --- Bước 2: Neo4j hard-delete (độc lập — lỗi không rollback Postgres) ---
    if neo4j_driver is not None:
        await _gc_neo4j(neo4j_driver, threshold)
    else:
        logger.warning("GC: neo4j_driver không có trong ctx — bỏ qua bước Neo4j")


async def _gc_postgres(
    session_factory: async_sessionmaker,
    threshold: datetime,
    outbox_threshold: datetime,
) -> None:
    """Hard-delete papers và projects quá hạn + dọn outbox."""
    async with session_factory() as db:
        try:
            # Hard-delete papers. Bao gồm cả paper thuộc project hết hạn: khi xóa project,
            # FK ondelete=CASCADE xóa các paper rows trong DB nhưng KHÔNG xóa file vật lý →
            # rò rỉ file. Chọn cả 2 nhóm để unlink file rồi xóa tường minh trước khi xóa project.
            expiring_projects = select(ProjectORM.id).where(
                and_(
                    ProjectORM.is_deleted.is_(True),
                    ProjectORM.deleted_at < threshold,
                )
            )
            result = await db.execute(
                select(PaperORM).where(
                    or_(
                        and_(
                            PaperORM.is_deleted.is_(True),
                            PaperORM.deleted_at < threshold,
                        ),
                        PaperORM.project_id.in_(expiring_projects),
                    )
                )
            )
            papers = result.scalars().all()
            deleted_papers = 0
            for paper in papers:
                # Xóa file vật lý nếu tồn tại
                if paper.file_path:
                    try:
                        Path(paper.file_path).unlink(missing_ok=True)
                    except Exception as e:
                        logger.warning("GC: không xóa được file %s: %s", paper.file_path, e)
                await db.delete(paper)
                deleted_papers += 1

            # Hard-delete projects quá hạn (papers/chunks cascade)
            delete_projects_result = await db.execute(
                delete(ProjectORM).where(
                    and_(
                        ProjectORM.is_deleted.is_(True),
                        ProjectORM.deleted_at < threshold,
                    )
                )
            )
            deleted_projects = delete_projects_result.rowcount

            # Dọn sync_outbox cũ
            delete_outbox_result = await db.execute(
                delete(SyncOutboxORM).where(
                    and_(
                        SyncOutboxORM.processed.is_(True),
                        SyncOutboxORM.processed_at < outbox_threshold,
                    )
                )
            )
            deleted_outbox = delete_outbox_result.rowcount

            await db.commit()
            logger.info(
                "GC Postgres: xóa %d papers, %d projects, %d outbox rows",
                deleted_papers,
                deleted_projects,
                deleted_outbox,
            )
        except Exception as e:
            logger.exception("GC Postgres thất bại: %s", e)
            await db.rollback()


async def _gc_neo4j(neo4j_driver, threshold: datetime) -> None:
    """DETACH DELETE node :Deleted đã quá ngưỡng."""
    try:
        async with neo4j_driver.session() as session:
            # n.deleted_at là Neo4j DateTime (ghi bằng datetime() trong handler). $threshold là
            # chuỗi ISO → phải ép datetime($threshold) để so sánh theo thời gian, nếu không
            # Cypher so sánh DateTime với String → trả null → KHÔNG xóa node nào.
            result = await session.run(
                "MATCH (n:Deleted) WHERE n.deleted_at < datetime($threshold) "
                "DETACH DELETE n "
                "RETURN count(*) AS deleted",
                threshold=threshold.isoformat(),
            )
            record = await result.single()
            deleted_count = record["deleted"] if record else 0
            logger.info("GC Neo4j: DETACH DELETE %d node :Deleted", deleted_count)
    except Exception as e:
        logger.exception("GC Neo4j thất bại (Postgres đã commit — lần GC sau sẽ dọn nốt): %s", e)
