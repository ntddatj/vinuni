"""Outbox Worker — consumer đọc sync_outbox và đồng bộ sang Neo4j.

Vòng lặp:
1. Claim batch (SKIP LOCKED, processed=false AND dead_lettered=false)
2. Group theo project_id
3. Lấy Redis lock theo project_id (compare-and-delete, heartbeat 60s)
4. Dispatch event → Cypher MERGE qua neo4j_adapter
5. Mark processed=true / retry / DLQ

Pattern Redis lock tái dùng từ ingestion/application/use_cases.py (AC#11).
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.src.modules.admin.infrastructure.settings_orm import get_setting
from backend.src.modules.graph_rag.infrastructure.neo4j_adapter import HANDLER_MAP
from backend.src.modules.workspace.infrastructure.orm_models import SyncOutboxORM
from backend.src.shared.infra.settings import get_settings

logger = logging.getLogger(__name__)

# Fallback khi system_settings chưa seed / không đọc được. Giá trị chính thức do Admin cấu hình
# ở system_settings (key MAX_SYNC_RETRIES) — mirror pattern MAX_PAPERS_PER_PROJECT.
_DEFAULT_MAX_SYNC_RETRIES = 3


async def _get_int_setting(db: AsyncSession, key: str, default: int) -> int:
    """Đọc setting số nguyên từ system_settings (Admin cấu hình), fallback về default."""
    raw = await get_setting(db, key, None)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        logger.warning("Setting %s='%s' không phải int — dùng default %d", key, raw, default)
        return default

# Lua compare-and-delete — tái dùng pattern từ ingestion/use_cases.py
_RELEASE_LOCK_LUA = (
    "if redis.call('get', KEYS[1]) == ARGV[1] then "
    "return redis.call('del', KEYS[1]) else return 0 end"
)

_LOCK_LEASE_SECONDS = 120
_HEARTBEAT_INTERVAL = 60


async def _acquire_project_lock(redis, project_id: str) -> str | None:
    """Cố lấy lock graph_sync_lock:{project_id}. Trả token nếu thành công, None nếu không."""
    lock_key = f"graph_sync_lock:{project_id}"
    token = str(uuid.uuid4())
    acquired = await redis.set(lock_key, token, nx=True, ex=_LOCK_LEASE_SECONDS)
    return token if acquired else None


async def _release_project_lock(redis, project_id: str, token: str) -> None:
    lock_key = f"graph_sync_lock:{project_id}"
    try:
        await redis.eval(_RELEASE_LOCK_LUA, 1, lock_key, token)
    except Exception as e:
        logger.warning("Không thể giải phóng lock %s: %s", lock_key, e)


async def _heartbeat_loop(redis, project_id: str, token: str, stop_event: asyncio.Event) -> None:
    """Gia hạn lock lease mỗi HEARTBEAT_INTERVAL giây khi batch còn chạy."""
    lock_key = f"graph_sync_lock:{project_id}"
    while not stop_event.is_set():
        await asyncio.sleep(_HEARTBEAT_INTERVAL)
        if stop_event.is_set():
            break
        try:
            current = await redis.get(lock_key)
            # arq cung cấp redis pool KHÔNG decode_responses → get() trả bytes.
            # So sánh bytes==str luôn False, khiến lease không bao giờ được gia hạn.
            if isinstance(current, bytes):
                current = current.decode()
            if current == token:
                await redis.expire(lock_key, _LOCK_LEASE_SECONDS)
        except Exception as e:
            logger.warning("Heartbeat lỗi cho lock %s: %s", lock_key, e)


async def sync_outbox_task(ctx) -> None:
    """arq task: drain một batch từ sync_outbox và đồng bộ sang Neo4j.

    Đăng ký trong WorkerSettings.cron_jobs để chạy mỗi 5 giây.
    """
    redis = ctx["redis"]
    session_factory: async_sessionmaker = ctx["session_factory"]
    neo4j_driver = ctx.get("neo4j_driver")
    if neo4j_driver is None:
        logger.error("neo4j_driver chưa được khởi tạo trong ctx — bỏ qua sync cycle")
        return

    # batch_size: knob hạ tầng (RAM/ARCH-1) → giữ ở env. max_retries: Admin cấu hình runtime.
    batch_size = get_settings().sync_outbox_batch_size

    async with session_factory() as db:
        max_retries = await _get_int_setting(db, "MAX_SYNC_RETRIES", _DEFAULT_MAX_SYNC_RETRIES)
        # Claim batch với SKIP LOCKED — chỉ lấy processed=false AND dead_lettered=false
        events = await _claim_batch(db, batch_size)
        if not events:
            return

    # Group theo project_id (None → group sentinel "__no_project__")
    groups: dict[str | None, list] = {}
    for evt in events:
        key = evt.project_id
        groups.setdefault(key, []).append(evt)

    for project_id, group_events in groups.items():
        # MỌI group đều phải lấy lock — kể cả group project_id=None (sentinel).
        # _claim_batch dùng SKIP LOCKED nhưng nhả row-lock ngay khi tx claim đóng (trước khi
        # xử lý Neo4j), nên một cron tick chồng lấn có thể claim lại cùng event. Redis lock theo
        # project là lớp đảm bảo mutual-exclusion thật; group None trước đây chạy KHÔNG lock →
        # bị xử lý trùng song song. Sentinel lock vá lỗ hổng này.
        lock_id = project_id if project_id is not None else "__no_project__"
        token = await _acquire_project_lock(redis, lock_id)
        if token is None:
            logger.debug("Không lấy được lock cho %s — bỏ qua lần này", lock_id)
            continue

        stop_hb = asyncio.Event()
        hb_task = asyncio.create_task(
            _heartbeat_loop(redis, lock_id, token, stop_hb)
        )

        try:
            await _process_group(session_factory, neo4j_driver, group_events, max_retries)
        finally:
            stop_hb.set()
            hb_task.cancel()
            try:
                await hb_task
            except asyncio.CancelledError:
                pass
            await _release_project_lock(redis, lock_id, token)


async def _claim_batch(db: AsyncSession, batch_size: int) -> list[SyncOutboxORM]:
    """SELECT FOR UPDATE SKIP LOCKED — claim batch chưa xử lý."""
    result = await db.execute(
        select(SyncOutboxORM)
        .where(
            SyncOutboxORM.processed.is_(False),
            SyncOutboxORM.dead_lettered.is_(False),
        )
        .order_by(SyncOutboxORM.id.asc())
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    return list(result.scalars().all())


async def _process_group(
    session_factory: async_sessionmaker,
    neo4j_driver,
    events: list[SyncOutboxORM],
    max_retries: int,
) -> None:
    """Xử lý từng event trong group. Lỗi 1 event không phá batch."""
    for evt in events:
        try:
            handler = HANDLER_MAP.get(evt.event_type)
            if handler is None:
                # Forward-compat: event lạ (vd ontology 4.3 chưa deploy) → WARN + tăng retry
                logger.warning(
                    "Không có handler cho event_type=%s (id=%d) — để lại cho lần sau",
                    evt.event_type,
                    evt.id,
                )
                async with session_factory() as db:
                    await db.execute(
                        update(SyncOutboxORM)
                        .where(SyncOutboxORM.id == evt.id)
                        .values(
                            retry_count=SyncOutboxORM.retry_count + 1,
                            last_error=f"No handler for event_type={evt.event_type}",
                            dead_lettered=(evt.retry_count + 1) >= max_retries,
                        )
                    )
                    await db.commit()
                continue

            # Thực thi Cypher MERGE
            async with neo4j_driver.session() as neo4j_session:
                await handler(neo4j_session, evt.payload)

            # Mark processed
            async with session_factory() as db:
                await db.execute(
                    update(SyncOutboxORM)
                    .where(SyncOutboxORM.id == evt.id)
                    .values(
                        processed=True,
                        processed_at=datetime.now(timezone.utc),
                    )
                )
                await db.commit()

        except Exception as e:
            logger.exception("Lỗi xử lý event id=%d type=%s: %s", evt.id, evt.event_type, e)
            new_retry = evt.retry_count + 1
            async with session_factory() as db:
                await db.execute(
                    update(SyncOutboxORM)
                    .where(SyncOutboxORM.id == evt.id)
                    .values(
                        retry_count=new_retry,
                        last_error=str(e)[:2000],
                        dead_lettered=new_retry >= max_retries,
                    )
                )
                await db.commit()
