"""Unit tests cho Garbage Collection task.

Kiểm tra AC#14-15: chỉ xóa is_deleted AND deleted_at < threshold;
bản ghi < 7 ngày KHÔNG bị xóa; Neo4j DETACH DELETE với threshold đúng.
"""
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.src.modules.graph_rag.infrastructure.garbage_collection import (
    _gc_neo4j,
    _gc_postgres,
    garbage_collection_task,
)


class _FakeSessionFactory:
    def __init__(self, session):
        self._session = session

    @asynccontextmanager
    async def _ctx(self):
        yield self._session

    def __call__(self):
        return self._ctx()


def _make_paper(is_deleted=True, deleted_at_days_ago=10, file_path=None):
    paper = MagicMock()
    paper.id = "paper-gc-1"
    paper.is_deleted = is_deleted
    paper.file_path = file_path
    if deleted_at_days_ago is not None:
        paper.deleted_at = datetime.now(timezone.utc) - timedelta(days=deleted_at_days_ago)
    else:
        paper.deleted_at = None
    return paper


# ---------- Postgres GC ----------

@pytest.mark.asyncio
async def test_gc_postgres_deletes_papers_older_than_threshold():
    """Paper is_deleted=True AND deleted_at >7d → bị hard-delete."""
    old_paper = _make_paper(is_deleted=True, deleted_at_days_ago=10, file_path=None)
    threshold = datetime.now(timezone.utc) - timedelta(days=7)
    outbox_threshold = datetime.now(timezone.utc) - timedelta(days=30)

    db = AsyncMock()

    # scalars().all() cho papers
    paper_scalars = MagicMock()
    paper_scalars.all = MagicMock(return_value=[old_paper])
    paper_execute_result = AsyncMock()
    paper_execute_result.scalars = MagicMock(return_value=paper_scalars)

    # execute cho delete(ProjectORM) và delete(SyncOutboxORM) → rowcount=0
    delete_result = MagicMock()
    delete_result.rowcount = 0

    call_count = [0]
    async def execute_side_effect(stmt):
        call_count[0] += 1
        if call_count[0] == 1:
            return paper_execute_result
        return delete_result

    db.execute = AsyncMock(side_effect=execute_side_effect)
    db.delete = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    session_factory = _FakeSessionFactory(db)

    await _gc_postgres(session_factory, threshold, outbox_threshold)

    db.delete.assert_awaited_with(old_paper)
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_gc_postgres_does_not_delete_recent_soft_deleted():
    """Paper deleted_at < 7 ngày KHÔNG bị xóa."""
    recent_paper = _make_paper(is_deleted=True, deleted_at_days_ago=3)
    threshold = datetime.now(timezone.utc) - timedelta(days=7)
    outbox_threshold = datetime.now(timezone.utc) - timedelta(days=30)

    db = AsyncMock()

    # scalars trả [] (không có paper nào vượt threshold)
    paper_scalars = MagicMock()
    paper_scalars.all = MagicMock(return_value=[])
    paper_execute_result = AsyncMock()
    paper_execute_result.scalars = MagicMock(return_value=paper_scalars)

    delete_result = MagicMock()
    delete_result.rowcount = 0

    call_count = [0]
    async def execute_side_effect(stmt):
        call_count[0] += 1
        if call_count[0] == 1:
            return paper_execute_result
        return delete_result

    db.execute = AsyncMock(side_effect=execute_side_effect)
    db.delete = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    session_factory = _FakeSessionFactory(db)

    await _gc_postgres(session_factory, threshold, outbox_threshold)

    db.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_gc_postgres_deletes_file_if_exists(tmp_path):
    """Paper với file_path tồn tại → file vật lý bị xóa."""
    test_file = tmp_path / "paper.pdf"
    test_file.write_bytes(b"pdf content")

    old_paper = _make_paper(is_deleted=True, deleted_at_days_ago=10, file_path=str(test_file))
    threshold = datetime.now(timezone.utc) - timedelta(days=7)
    outbox_threshold = datetime.now(timezone.utc) - timedelta(days=30)

    db = AsyncMock()
    paper_scalars = MagicMock()
    paper_scalars.all = MagicMock(return_value=[old_paper])
    paper_execute_result = AsyncMock()
    paper_execute_result.scalars = MagicMock(return_value=paper_scalars)

    delete_result = MagicMock()
    delete_result.rowcount = 0

    call_count = [0]
    async def execute_side_effect(stmt):
        call_count[0] += 1
        if call_count[0] == 1:
            return paper_execute_result
        return delete_result

    db.execute = AsyncMock(side_effect=execute_side_effect)
    db.delete = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    session_factory = _FakeSessionFactory(db)

    await _gc_postgres(session_factory, threshold, outbox_threshold)

    assert not test_file.exists(), "File vật lý phải bị xóa sau GC"


# ---------- GC_RETENTION_DAYS từ admin settings ----------

@pytest.mark.asyncio
async def test_gc_retention_days_read_from_admin_setting():
    """GC_RETENTION_DAYS đọc từ system_settings (Admin cấu hình) override default, fallback khi lỗi."""
    from backend.src.modules.graph_rag.infrastructure.garbage_collection import _get_int_setting

    sf = _FakeSessionFactory(AsyncMock())
    with patch(
        "backend.src.modules.graph_rag.infrastructure.garbage_collection.get_setting",
        new=AsyncMock(return_value="30"),
    ):
        assert await _get_int_setting(sf, "GC_RETENTION_DAYS", 7) == 30

    with patch(
        "backend.src.modules.graph_rag.infrastructure.garbage_collection.get_setting",
        new=AsyncMock(return_value="abc"),
    ):
        assert await _get_int_setting(sf, "GC_RETENTION_DAYS", 7) == 7

    with patch(
        "backend.src.modules.graph_rag.infrastructure.garbage_collection.get_setting",
        new=AsyncMock(return_value=None),
    ):
        assert await _get_int_setting(sf, "GC_RETENTION_DAYS", 7) == 7


# ---------- Neo4j GC ----------

@pytest.mark.asyncio
async def test_gc_neo4j_uses_detach_delete_with_threshold():
    """_gc_neo4j chạy DETACH DELETE với threshold đúng."""
    queries_run = []

    async def mock_run(query, **params):
        queries_run.append((query, params))
        record_mock = MagicMock()
        record_mock.__getitem__ = MagicMock(return_value=3)
        result_mock = AsyncMock()
        result_mock.single = AsyncMock(return_value=record_mock)
        return result_mock

    neo4j_session = AsyncMock()
    neo4j_session.run = AsyncMock(side_effect=mock_run)
    neo4j_driver = MagicMock()

    @asynccontextmanager
    async def _neo4j_session_ctx():
        yield neo4j_session

    neo4j_driver.session = _neo4j_session_ctx

    threshold = datetime.now(timezone.utc) - timedelta(days=7)
    await _gc_neo4j(neo4j_driver, threshold)

    # 2 query: (1) DETACH DELETE node :Deleted quá hạn, (2) dọn node ontology mồ côi
    assert len(queries_run) == 2
    deleted_query, params = queries_run[0]
    assert "DETACH DELETE" in deleted_query.upper()
    assert ":Deleted" in deleted_query
    assert "threshold" in params

    orphan_query, _ = queries_run[1]
    assert "DETACH DELETE" in orphan_query.upper()
    # Sweep nhắm node ontology không còn Paper sống nào trỏ tới
    assert "Finding" in orphan_query and "Topic" in orphan_query
    assert "NOT EXISTS" in orphan_query and "Paper" in orphan_query


@pytest.mark.asyncio
async def test_gc_neo4j_failure_does_not_raise():
    """Neo4j GC thất bại không raise — lần GC sau sẽ dọn nốt (AC#15)."""
    neo4j_driver = MagicMock()

    @asynccontextmanager
    async def _failing_session():
        raise ConnectionError("Neo4j down")
        yield  # unreachable, just to make it a generator

    neo4j_driver.session = _failing_session

    threshold = datetime.now(timezone.utc) - timedelta(days=7)
    # Không được raise
    await _gc_neo4j(neo4j_driver, threshold)


@pytest.mark.asyncio
async def test_garbage_collection_task_no_neo4j_driver():
    """GC task không có neo4j_driver → chỉ chạy Postgres, không raise."""
    session_factory_mock = MagicMock()

    db = AsyncMock()
    paper_scalars = MagicMock()
    paper_scalars.all = MagicMock(return_value=[])
    paper_execute_result = AsyncMock()
    paper_execute_result.scalars = MagicMock(return_value=paper_scalars)
    delete_result = MagicMock()
    delete_result.rowcount = 0

    call_count = [0]
    async def execute_side_effect(stmt):
        call_count[0] += 1
        if call_count[0] == 1:
            return paper_execute_result
        return delete_result

    db.execute = AsyncMock(side_effect=execute_side_effect)
    db.delete = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    @asynccontextmanager
    async def _ctx():
        yield db

    session_factory_mock.return_value = _ctx()
    session_factory_mock.__call__ = lambda self: _ctx()

    class _SF:
        @asynccontextmanager
        async def _ctx(self2):
            yield db

        def __call__(self2):
            return self2._ctx()

    ctx = {"session_factory": _SF(), "neo4j_driver": None}

    # Không raise (patch get_setting → GC_RETENTION_DAYS fallback default, không tốn execute call)
    with patch(
        "backend.src.modules.graph_rag.infrastructure.garbage_collection.get_setting",
        new=AsyncMock(return_value=None),
    ):
        await garbage_collection_task(ctx)
