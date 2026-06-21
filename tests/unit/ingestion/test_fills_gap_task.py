"""Unit tests cho fills_gap_task (AC: 14, Story 4.7)."""
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.worker import fills_gap_task


class _FakeSessionFactory:
    def __init__(self, session):
        self._session = session

    @asynccontextmanager
    async def _ctx(self):
        yield self._session

    def __call__(self):
        return self._ctx()


def _make_paper_row(user_id="user-1", title="Owner Paper"):
    row = MagicMock()
    row.user_id = user_id
    row.title = title
    return row


def _make_cand_row(title="Candidate Paper", abstract="Abstract text"):
    row = MagicMock()
    row.title = title
    row.abstract = abstract
    return row


def _make_chunk(content="chunk content"):
    c = MagicMock()
    c.content = content
    return c


def _make_db_with_side_effects(side_effects):
    """Tạo mock db với execute side_effect tuần tự."""
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=side_effects)
    db.add = MagicMock()
    db.commit = AsyncMock()
    return db


def _scalar_result(value):
    r = AsyncMock()
    r.scalar_one_or_none = MagicMock(return_value=value)
    return r


def _first_result(value):
    r = AsyncMock()
    r.first = MagicMock(return_value=value)
    return r


def _scalars_result(items):
    r = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=items)
    r.scalars = MagicMock(return_value=scalars_mock)
    return r


def _all_result(rows):
    r = AsyncMock()
    r.all = MagicMock(return_value=rows)
    return r


def _make_neo4j_ctx(limitations):
    driver = MagicMock()

    @asynccontextmanager
    async def _session_ctx():
        yield AsyncMock()

    driver.session = _session_ctx
    return driver


@pytest.mark.asyncio
async def test_fills_gap_task_noop_when_no_unfilled():
    """list_unfilled_limitations trả [] → không embed, không judge, không add event."""
    driver = _make_neo4j_ctx([])
    db = AsyncMock()
    db.add = MagicMock()

    ctx = {
        "session_factory": _FakeSessionFactory(db),
        "neo4j_driver": driver,
    }

    with patch("backend.worker.list_unfilled_limitations", new=AsyncMock(return_value=[])):
        await fills_gap_task(ctx, "proj-1")

    db.add.assert_not_called()
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_fills_gap_task_emits_event_on_fill():
    """1 limitation + 1 candidate → judge fills=true → emit FILLS_GAP + cache."""
    limitations = [
        {"limitation_id": "lim-1", "description": "Limitation desc", "owner_paper_id": "paper-owner"}
    ]

    # Thứ tự execute: owner_paper, pgvector, cache_check, cand_paper, cand_chunks
    vec = [0.5] * 768
    pgvec_row = MagicMock()
    pgvec_row.paper_id = "paper-cand"
    pgvec_row.dist = 0.2  # similarity = 1 - 0.2 = 0.8 >= 0.65

    side_effects = [
        _first_result(_make_paper_row()),       # owner paper query
        _all_result([pgvec_row]),               # pgvector tiền lọc
        _scalar_result(None),                   # cache check → không có cache
        _first_result(_make_cand_row()),        # candidate paper info
        _scalars_result([_make_chunk()]),       # candidate chunks
    ]

    db = _make_db_with_side_effects(side_effects)
    driver = _make_neo4j_ctx(limitations)
    ctx = {
        "session_factory": _FakeSessionFactory(db),
        "neo4j_driver": driver,
    }

    with (
        patch("backend.worker.list_unfilled_limitations", new=AsyncMock(return_value=limitations)),
        patch("backend.worker.GeminiEmbeddingClient") as MockEmbed,
        patch("backend.worker.FillsGapJudge") as MockJudge,
    ):
        MockEmbed.return_value.embed_batch = AsyncMock(return_value=[vec])
        MockJudge.return_value.judge = AsyncMock(return_value={"fills": True, "reason": "resolves it"})
        await fills_gap_task(ctx, "proj-1")

    added = [c[0][0] for c in db.add.call_args_list]
    event_types = [getattr(o, "event_type", None) for o in added]
    assert "FILLS_GAP" in event_types
    # Cache row cũng được add
    cache_rows = [o for o in added if not hasattr(o, "event_type")]
    assert len(cache_rows) >= 1


@pytest.mark.asyncio
async def test_fills_gap_task_no_event_when_not_fill():
    """judge fills=false → KHÔNG add FILLS_GAP event, NHƯNG cache vẫn ghi."""
    limitations = [
        {"limitation_id": "lim-1", "description": "Limitation desc", "owner_paper_id": "paper-owner"}
    ]

    vec = [0.5] * 768
    pgvec_row = MagicMock()
    pgvec_row.paper_id = "paper-cand"
    pgvec_row.dist = 0.2

    side_effects = [
        _first_result(_make_paper_row()),
        _all_result([pgvec_row]),
        _scalar_result(None),
        _first_result(_make_cand_row()),
        _scalars_result([]),
    ]

    db = _make_db_with_side_effects(side_effects)
    driver = _make_neo4j_ctx(limitations)
    ctx = {
        "session_factory": _FakeSessionFactory(db),
        "neo4j_driver": driver,
    }

    with (
        patch("backend.worker.list_unfilled_limitations", new=AsyncMock(return_value=limitations)),
        patch("backend.worker.GeminiEmbeddingClient") as MockEmbed,
        patch("backend.worker.FillsGapJudge") as MockJudge,
    ):
        MockEmbed.return_value.embed_batch = AsyncMock(return_value=[vec])
        MockJudge.return_value.judge = AsyncMock(return_value={"fills": False, "reason": "not related"})
        await fills_gap_task(ctx, "proj-1")

    added = [c[0][0] for c in db.add.call_args_list]
    event_types = [getattr(o, "event_type", None) for o in added]
    assert "FILLS_GAP" not in event_types
    # Cache vẫn ghi dù fills=false
    assert len(added) >= 1


@pytest.mark.asyncio
async def test_fills_gap_task_skips_cached_pair():
    """Cặp đã có trong cache → KHÔNG gọi judge."""
    limitations = [
        {"limitation_id": "lim-1", "description": "Limitation desc", "owner_paper_id": "paper-owner"}
    ]

    vec = [0.5] * 768
    pgvec_row = MagicMock()
    pgvec_row.paper_id = "paper-cand"
    pgvec_row.dist = 0.2

    cached_row = MagicMock()  # Đã có cache

    side_effects = [
        _first_result(_make_paper_row()),
        _all_result([pgvec_row]),
        _scalar_result(cached_row),  # cache-hit → skip judge
    ]

    db = _make_db_with_side_effects(side_effects)
    driver = _make_neo4j_ctx(limitations)
    ctx = {
        "session_factory": _FakeSessionFactory(db),
        "neo4j_driver": driver,
    }

    mock_judge = AsyncMock()
    with (
        patch("backend.worker.list_unfilled_limitations", new=AsyncMock(return_value=limitations)),
        patch("backend.worker.GeminiEmbeddingClient") as MockEmbed,
        patch("backend.worker.FillsGapJudge") as MockJudge,
    ):
        MockEmbed.return_value.embed_batch = AsyncMock(return_value=[vec])
        MockJudge.return_value.judge = mock_judge
        await fills_gap_task(ctx, "proj-1")

    mock_judge.assert_not_awaited()


@pytest.mark.asyncio
async def test_fills_gap_task_skips_self_fill():
    """candidate == owner_paper_id → KHÔNG add FILLS_GAP event."""
    limitations = [
        {"limitation_id": "lim-1", "description": "Limitation desc", "owner_paper_id": "paper-owner"}
    ]

    vec = [0.5] * 768
    # Candidate trùng với owner
    pgvec_row = MagicMock()
    pgvec_row.paper_id = "paper-owner"
    pgvec_row.dist = 0.1

    side_effects = [
        _first_result(_make_paper_row()),
        _all_result([pgvec_row]),
        # pgvector query không lọc được owner do test dùng mock, nhưng worker.py có guard
        # candidate_paper_id != owner_paper_id ở vòng lặp
    ]

    db = _make_db_with_side_effects(side_effects)
    driver = _make_neo4j_ctx(limitations)
    ctx = {
        "session_factory": _FakeSessionFactory(db),
        "neo4j_driver": driver,
    }

    with (
        patch("backend.worker.list_unfilled_limitations", new=AsyncMock(return_value=limitations)),
        patch("backend.worker.GeminiEmbeddingClient") as MockEmbed,
        patch("backend.worker.FillsGapJudge") as MockJudge,
    ):
        MockEmbed.return_value.embed_batch = AsyncMock(return_value=[vec])
        await fills_gap_task(ctx, "proj-1")

    # Không add FILLS_GAP vì self-fill bị guard
    added = [c[0][0] for c in db.add.call_args_list]
    event_types = [getattr(o, "event_type", None) for o in added]
    assert "FILLS_GAP" not in event_types
