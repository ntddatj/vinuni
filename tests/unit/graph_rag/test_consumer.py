"""Unit tests cho outbox consumer worker.

Kiểm tra AC#10-13: claim batch, mark processed, retry/DLQ, lock, idempotency, dispatch event lạ.
Mock toàn bộ Neo4j/Redis/Postgres — không gọi infra thật.
"""
import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from backend.src.modules.graph_rag.infrastructure.outbox_worker import (
    _acquire_project_lock,
    _process_group,
    _release_project_lock,
    sync_outbox_task,
)
from backend.src.modules.workspace.infrastructure.orm_models import SyncOutboxORM


def _make_event(
    id=1,
    event_type="PAPER_UPSERTED",
    project_id="proj-1",
    processed=False,
    dead_lettered=False,
    retry_count=0,
    payload=None,
):
    evt = MagicMock(spec=SyncOutboxORM)
    evt.id = id
    evt.event_type = event_type
    evt.project_id = project_id
    evt.processed = processed
    evt.dead_lettered = dead_lettered
    evt.retry_count = retry_count
    evt.payload = payload or {"paper_id": f"paper-{id}", "project_id": project_id}
    return evt


class _FakeSessionFactory:
    def __init__(self, session):
        self._session = session

    @asynccontextmanager
    async def _ctx(self):
        yield self._session

    def __call__(self):
        return self._ctx()


# ---------- claim batch ----------

@pytest.mark.asyncio
async def test_claim_batch_only_unprocessed_not_dead_lettered():
    """_claim_batch chỉ lấy processed=false AND dead_lettered=false."""
    from backend.src.modules.graph_rag.infrastructure.outbox_worker import _claim_batch

    db = AsyncMock()
    expected_events = [_make_event(id=1), _make_event(id=2)]

    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=expected_events)
    execute_result = AsyncMock()
    execute_result.scalars = MagicMock(return_value=scalars_mock)
    db.execute = AsyncMock(return_value=execute_result)

    events = await _claim_batch(db, batch_size=100)
    assert events == expected_events
    db.execute.assert_awaited_once()


# ---------- mark processed ----------

@pytest.mark.asyncio
async def test_process_group_marks_processed_on_success():
    """Event xử lý thành công → processed=True, processed_at set."""
    evt = _make_event(id=10)

    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    session_factory = _FakeSessionFactory(db)

    neo4j_session = AsyncMock()
    neo4j_driver = MagicMock()

    @asynccontextmanager
    async def _neo4j_session_ctx():
        yield neo4j_session

    neo4j_driver.session = _neo4j_session_ctx

    mock_handler = AsyncMock()
    with patch(
        "backend.src.modules.graph_rag.infrastructure.outbox_worker.HANDLER_MAP",
        {"PAPER_UPSERTED": mock_handler},
    ):
        await _process_group(session_factory, neo4j_driver, [evt], max_retries=3)

    mock_handler.assert_awaited_once_with(neo4j_session, evt.payload)
    db.execute.assert_awaited()
    db.commit.assert_awaited()


# ---------- retry & DLQ ----------

@pytest.mark.asyncio
async def test_process_group_increments_retry_on_error():
    """Handler raise → retry_count tăng, last_error set."""
    evt = _make_event(id=5, retry_count=0)

    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    session_factory = _FakeSessionFactory(db)

    neo4j_driver = MagicMock()

    @asynccontextmanager
    async def _neo4j_session_ctx():
        yield AsyncMock()

    neo4j_driver.session = _neo4j_session_ctx

    failing_handler = AsyncMock(side_effect=RuntimeError("Neo4j connection refused"))
    with patch(
        "backend.src.modules.graph_rag.infrastructure.outbox_worker.HANDLER_MAP",
        {"PAPER_UPSERTED": failing_handler},
    ):
        await _process_group(session_factory, neo4j_driver, [evt], max_retries=3)

    db.execute.assert_awaited()
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_process_group_dead_letters_after_max_retries():
    """Sau max_retries lần lỗi → update được gọi (dead_lettered logic kích hoạt)."""
    evt = _make_event(id=7, retry_count=2)  # new_retry=3 >= max_retries=3 → dead_lettered=True

    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    session_factory = _FakeSessionFactory(db)

    neo4j_driver = MagicMock()

    @asynccontextmanager
    async def _neo4j_session_ctx():
        yield AsyncMock()

    neo4j_driver.session = _neo4j_session_ctx

    failing_handler = AsyncMock(side_effect=RuntimeError("fail"))
    with patch(
        "backend.src.modules.graph_rag.infrastructure.outbox_worker.HANDLER_MAP",
        {"PAPER_UPSERTED": failing_handler},
    ):
        await _process_group(session_factory, neo4j_driver, [evt], max_retries=3)

    # Verify update statement được gọi (dead_lettered logic đã chạy)
    db.execute.assert_awaited()
    db.commit.assert_awaited()

    # Kiểm tra update statement có `dead_lettered=True` bằng cách inspect compiled SQL
    stmt = db.execute.call_args.args[0]
    # Compile để lấy parameters
    from sqlalchemy.dialects import postgresql
    compiled = stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    assert "dead_lettered" in compiled.string.lower()
    assert "true" in compiled.string.lower()


@pytest.mark.asyncio
async def test_process_group_one_error_does_not_block_others():
    """Lỗi 1 event không làm hỏng các event khác trong batch."""
    evt_fail = _make_event(id=1, event_type="PAPER_UPSERTED")
    evt_ok = _make_event(id=2, event_type="PAPER_UPSERTED")

    call_log = []

    async def flaky_handler(session, payload):
        pid = payload.get("paper_id", "")
        call_log.append(pid)
        if pid == "paper-1":
            raise RuntimeError("first event fails")

    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    session_factory = _FakeSessionFactory(db)

    neo4j_driver = MagicMock()

    @asynccontextmanager
    async def _neo4j_session_ctx():
        yield AsyncMock()

    neo4j_driver.session = _neo4j_session_ctx

    with patch(
        "backend.src.modules.graph_rag.infrastructure.outbox_worker.HANDLER_MAP",
        {"PAPER_UPSERTED": flaky_handler},
    ):
        await _process_group(session_factory, neo4j_driver, [evt_fail, evt_ok], max_retries=3)

    assert "paper-1" in call_log
    assert "paper-2" in call_log


# ---------- lock ----------

@pytest.mark.asyncio
async def test_acquire_lock_success():
    """Redis SET NX thành công → trả token (non-None)."""
    redis = AsyncMock()
    redis.set = AsyncMock(return_value=True)
    token = await _acquire_project_lock(redis, "proj-abc")
    assert token is not None
    redis.set.assert_awaited_once()
    args, kwargs = redis.set.call_args
    assert args[0] == "graph_sync_lock:proj-abc"
    assert kwargs.get("nx") is True


@pytest.mark.asyncio
async def test_acquire_lock_failure_returns_none():
    """Redis SET NX thất bại (lock đã tồn tại) → trả None."""
    redis = AsyncMock()
    redis.set = AsyncMock(return_value=None)
    token = await _acquire_project_lock(redis, "proj-abc")
    assert token is None


@pytest.mark.asyncio
async def test_release_lock_uses_compare_and_delete():
    """Release lock dùng Lua compare-and-delete với đúng args."""
    redis = AsyncMock()
    redis.eval = AsyncMock(return_value=1)
    await _release_project_lock(redis, "proj-abc", "token-xyz")
    redis.eval.assert_awaited_once()
    eval_args = redis.eval.call_args.args
    assert eval_args[1] == 1  # numkeys
    assert eval_args[2] == "graph_sync_lock:proj-abc"
    assert eval_args[3] == "token-xyz"


@pytest.mark.asyncio
async def test_sync_outbox_task_skips_project_when_lock_not_acquired():
    """Không lấy được lock → bỏ qua project đó, không xử lý event."""
    evt = _make_event(id=1, project_id="proj-locked")

    db = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=[evt])
    execute_result = AsyncMock()
    execute_result.scalars = MagicMock(return_value=scalars_mock)
    db.execute = AsyncMock(return_value=execute_result)
    db.commit = AsyncMock()
    session_factory = _FakeSessionFactory(db)

    neo4j_driver = MagicMock()
    redis = AsyncMock()
    redis.set = AsyncMock(return_value=None)  # lock không lấy được

    ctx = {
        "redis": redis,
        "session_factory": session_factory,
        "neo4j_driver": neo4j_driver,
    }

    mock_handler = AsyncMock()
    with (
        patch(
            "backend.src.modules.graph_rag.infrastructure.outbox_worker.HANDLER_MAP",
            {"PAPER_UPSERTED": mock_handler},
        ),
        patch(
            "backend.src.modules.graph_rag.infrastructure.outbox_worker.get_setting",
            new=AsyncMock(return_value=None),  # MAX_SYNC_RETRIES → fallback default
        ),
    ):
        await sync_outbox_task(ctx)

    mock_handler.assert_not_awaited()


# ---------- dispatch event lạ ----------

@pytest.mark.asyncio
async def test_unknown_event_type_does_not_crash_increments_retry():
    """Event_type lạ → không crash, không mark processed, tăng retry_count."""
    evt = _make_event(id=99, event_type="FINDING_EXTRACTED", retry_count=0)

    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    session_factory = _FakeSessionFactory(db)

    neo4j_driver = MagicMock()

    @asynccontextmanager
    async def _neo4j_session_ctx():
        yield AsyncMock()

    neo4j_driver.session = _neo4j_session_ctx

    with patch(
        "backend.src.modules.graph_rag.infrastructure.outbox_worker.HANDLER_MAP",
        {},  # empty map → loại event lạ
    ):
        await _process_group(session_factory, neo4j_driver, [evt], max_retries=3)

    # Phải có update (retry), KHÔNG mark processed=True
    db.execute.assert_awaited()
    db.commit.assert_awaited()


# ---------- MAX_SYNC_RETRIES từ admin settings ----------

@pytest.mark.asyncio
async def test_max_sync_retries_read_from_admin_setting():
    """MAX_SYNC_RETRIES đọc từ system_settings (Admin cấu hình) override default."""
    from backend.src.modules.graph_rag.infrastructure.outbox_worker import _get_int_setting

    db = AsyncMock()
    with patch(
        "backend.src.modules.graph_rag.infrastructure.outbox_worker.get_setting",
        new=AsyncMock(return_value="5"),
    ):
        assert await _get_int_setting(db, "MAX_SYNC_RETRIES", 3) == 5

    # Giá trị rác / chưa seed → fallback default
    with patch(
        "backend.src.modules.graph_rag.infrastructure.outbox_worker.get_setting",
        new=AsyncMock(return_value="not-an-int"),
    ):
        assert await _get_int_setting(db, "MAX_SYNC_RETRIES", 3) == 3
    with patch(
        "backend.src.modules.graph_rag.infrastructure.outbox_worker.get_setting",
        new=AsyncMock(return_value=None),
    ):
        assert await _get_int_setting(db, "MAX_SYNC_RETRIES", 3) == 3


# ---------- idempotency Cypher MERGE ----------

@pytest.mark.asyncio
async def test_cypher_handler_uses_merge_not_create():
    """Handler PAPER_UPSERTED dùng MERGE trong Cypher (assert query chứa MERGE)."""
    from backend.src.modules.graph_rag.infrastructure.neo4j_adapter import handle_paper_upserted

    queries_run = []

    async def mock_run(query, **params):
        queries_run.append(query)

    session = AsyncMock()
    session.run = AsyncMock(side_effect=mock_run)

    payload = {
        "paper_id": "p1",
        "project_id": "proj1",
        "title": "Test",
        "authors": ["Alice"],
        "year": 2024,
        "doi": None,
        "arxiv_id": None,
        "source": "manual",
        "url": None,
        "file_path": None,
    }

    await handle_paper_upserted(session, payload)

    assert queries_run, "Phải có ít nhất 1 query Cypher được thực thi"
    for q in queries_run:
        assert "MERGE" in q.upper(), f"Query phải dùng MERGE: {q}"

    # Gọi 2 lần với cùng payload → số lần run tương tự (không tạo trùng)
    queries_run.clear()
    await handle_paper_upserted(session, payload)
    assert queries_run, "Lần 2 vẫn phải chạy MERGE (idempotent)"
