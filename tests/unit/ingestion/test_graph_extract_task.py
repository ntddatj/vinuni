"""Unit tests cho graph_extract_task (Story 4.3, AC: 14)."""
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.worker import graph_extract_task


class _FakeSessionFactory:
    def __init__(self, session):
        self._session = session

    @asynccontextmanager
    async def _ctx(self):
        yield self._session

    def __call__(self):
        return self._ctx()


def _make_paper(
    id="paper-1",
    user_id="user-1",
    project_id="proj-1",
    status="indexed",
    is_deleted=False,
    abstract="Abstract text",
    authors=None,
    title="Test Paper",
):
    paper = MagicMock()
    paper.id = id
    paper.user_id = user_id
    paper.project_id = project_id
    paper.status = status
    paper.is_deleted = is_deleted
    paper.abstract = abstract
    paper.authors = authors or ["Alice"]
    paper.title = title
    return paper


def _make_db(paper=None, chunks=None):
    db = AsyncMock()

    paper_result = AsyncMock()
    paper_result.scalar_one_or_none = MagicMock(return_value=paper)

    chunk_result = AsyncMock()
    chunks_list = chunks or []
    chunk_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=chunks_list)))

    db.execute = AsyncMock(side_effect=[paper_result, chunk_result])
    db.add = MagicMock()
    db.commit = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_graph_extract_task_skips_deleted_paper():
    paper = _make_paper(is_deleted=True)
    db = _make_db(paper=paper)
    ctx = {"session_factory": _FakeSessionFactory(db), "redis": AsyncMock()}

    with patch(
        "backend.worker.GraphExtractor"
    ) as MockExtractor:
        await graph_extract_task(ctx, "paper-1")
        MockExtractor.assert_not_called()

    db.add.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_graph_extract_task_skips_non_indexed_paper():
    paper = _make_paper(status="processing")
    db = _make_db(paper=paper)
    ctx = {"session_factory": _FakeSessionFactory(db), "redis": AsyncMock()}

    with patch(
        "backend.worker.GraphExtractor"
    ) as MockExtractor:
        await graph_extract_task(ctx, "paper-1")
        MockExtractor.assert_not_called()

    db.add.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_graph_extract_task_writes_ontology_event():
    paper = _make_paper()
    db = _make_db(paper=paper, chunks=[])

    _VALID_DATA = {
        "findings": [{"id": "f1", "description": "Finding 1", "confidence_score": 0.9}],
        "limitations": [{"id": "l1", "description": "Limitation 1"}],
        "methods": [],
        "datasets": [],
        "topics": [{"id": "t1", "name": "ML"}],
        "problems": [],
        "contradicts": [],
        "supports": [],
    }

    ctx = {"session_factory": _FakeSessionFactory(db), "redis": AsyncMock()}

    with patch(
        "backend.worker.GraphExtractor"
    ) as MockExtractor:
        instance = AsyncMock()
        instance.extract = AsyncMock(return_value=_VALID_DATA)
        MockExtractor.return_value = instance

        await graph_extract_task(ctx, "paper-1")

    db.add.assert_called_once()
    db.commit.assert_awaited_once()
    added_event = db.add.call_args[0][0]
    assert added_event.event_type == "ONTOLOGY_EXTRACTED"
    assert added_event.project_id == "proj-1"
    payload = added_event.payload
    assert payload["paper_id"] == "paper-1"
    assert payload["project_id"] == "proj-1"
    assert len(payload["findings"]) == 1
    assert "paper-1:f:0" == payload["findings"][0]["id"]


@pytest.mark.asyncio
async def test_graph_extract_task_clamps_confidence_score():
    """confidence_score ngoài [0,1] hoặc sai kiểu → ép về float hợp lệ trong payload (P4)."""
    paper = _make_paper()
    db = _make_db(paper=paper, chunks=[])

    data = {
        "findings": [
            {"id": "f1", "description": "F1", "confidence_score": 5.0},
            {"id": "f2", "description": "F2", "confidence_score": "bad"},
        ],
        "limitations": [],
        "methods": [],
        "datasets": [],
        "topics": [{"id": "t1", "name": "ML"}],
        "problems": [],
        "contradicts": [],
        "supports": [],
    }

    ctx = {"session_factory": _FakeSessionFactory(db), "redis": AsyncMock()}

    with patch("backend.worker.GraphExtractor") as MockExtractor:
        instance = AsyncMock()
        instance.extract = AsyncMock(return_value=data)
        MockExtractor.return_value = instance

        await graph_extract_task(ctx, "paper-1")

    payload = db.add.call_args[0][0].payload
    scores = [f["confidence_score"] for f in payload["findings"]]
    assert scores == [1.0, 0.0]


@pytest.mark.asyncio
async def test_graph_extract_task_skips_when_extractor_returns_none():
    paper = _make_paper()
    db = _make_db(paper=paper, chunks=[])
    ctx = {"session_factory": _FakeSessionFactory(db), "redis": AsyncMock()}

    with patch(
        "backend.worker.GraphExtractor"
    ) as MockExtractor:
        instance = AsyncMock()
        instance.extract = AsyncMock(return_value=None)
        MockExtractor.return_value = instance

        await graph_extract_task(ctx, "paper-1")

    db.add.assert_not_called()
    db.commit.assert_not_called()
