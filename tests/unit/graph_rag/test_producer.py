"""Unit tests cho producer PAPER_UPSERTED trong ingest_paper_task.

Kiểm tra AC#8: ghi đúng 1 event PAPER_UPSERTED khi ingest thành công;
nhánh paper-đã-xóa KHÔNG ghi event; nhánh failed KHÔNG ghi event.
"""
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class _FakeSessionFactory:
    def __init__(self, session):
        self._session = session

    @asynccontextmanager
    async def _ctx(self):
        yield self._session

    def __call__(self):
        return self._ctx()


def _make_paper(is_deleted=False, file_path=None):
    paper = MagicMock()
    paper.id = "paper-uuid-1"
    paper.project_id = "project-uuid-1"
    paper.user_id = "user-uuid-1"
    paper.title = "Test Paper"
    paper.authors = ["Author One", "Author Two"]
    paper.year = 2024
    paper.doi = "10.1234/test"
    paper.arxiv_id = None
    paper.source = "manual"
    paper.url = None
    paper.file_path = file_path
    paper.abstract = "Abstract text."
    paper.status = "pending"
    paper.is_deleted = is_deleted
    return paper


@pytest.mark.asyncio
async def test_producer_writes_paper_upserted_on_success():
    """Ingest thành công (có nội dung + chunks) → ghi đúng 1 SyncOutboxORM PAPER_UPSERTED."""
    paper = _make_paper(file_path="/data/papers/test.pdf")

    db = AsyncMock()
    added_objects = []
    db.add = lambda obj: added_objects.append(obj)

    execute_result = AsyncMock()
    execute_result.scalar_one_or_none = MagicMock(return_value=paper)
    db.execute = AsyncMock(return_value=execute_result)
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock(side_effect=lambda p: setattr(p, "is_deleted", False))

    redis = AsyncMock()
    ctx = {"redis": redis, "session_factory": _FakeSessionFactory(db)}

    with (
        patch("backend.worker._extract_text", return_value="Nội dung bài báo thật."),
        patch("backend.worker.chunk_text", return_value=[("parent text", ["child text"])]),
        patch("backend.worker.GeminiEmbeddingClient") as MockEmbed,
        patch("backend.worker.publish_progress", new_callable=AsyncMock),
        patch("backend.worker.publish_completed", new_callable=AsyncMock),
    ):
        mock_client = AsyncMock()
        mock_client.embed_batch = AsyncMock(return_value=[[0.0] * 1536])
        MockEmbed.return_value = mock_client

        from backend.worker import ingest_paper_task
        await ingest_paper_task(ctx, "paper-uuid-1")

    from backend.src.modules.workspace.infrastructure.orm_models import SyncOutboxORM
    outbox_events = [o for o in added_objects if isinstance(o, SyncOutboxORM)]
    upserted_events = [e for e in outbox_events if e.event_type == "PAPER_UPSERTED"]

    assert len(upserted_events) == 1, "Phải ghi đúng 1 event PAPER_UPSERTED"
    evt = upserted_events[0]
    assert evt.project_id == "project-uuid-1"
    payload = evt.payload
    assert payload["paper_id"] == "paper-uuid-1"
    assert payload["project_id"] == "project-uuid-1"
    assert payload["title"] == "Test Paper"
    assert "authors" in payload
    assert "file_path" in payload


@pytest.mark.asyncio
async def test_producer_writes_paper_upserted_when_no_text():
    """Paper không trích được nội dung (metadata-only) vẫn ghi PAPER_UPSERTED để lên Neo4j."""
    paper = _make_paper(file_path=None)

    db = AsyncMock()
    added_objects = []
    db.add = lambda obj: added_objects.append(obj)

    execute_result = AsyncMock()
    execute_result.scalar_one_or_none = MagicMock(return_value=paper)
    db.execute = AsyncMock(return_value=execute_result)
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock(side_effect=lambda p: setattr(p, "is_deleted", False))

    redis = AsyncMock()
    ctx = {"redis": redis, "session_factory": _FakeSessionFactory(db)}

    with (
        patch("backend.worker._extract_text", return_value="   "),  # rỗng → nhánh no-text
        patch("backend.worker.publish_progress", new_callable=AsyncMock),
        patch("backend.worker.publish_completed", new_callable=AsyncMock),
    ):
        from backend.worker import ingest_paper_task
        await ingest_paper_task(ctx, "paper-uuid-1")

    from backend.src.modules.workspace.infrastructure.orm_models import SyncOutboxORM
    upserted = [
        o for o in added_objects
        if isinstance(o, SyncOutboxORM) and o.event_type == "PAPER_UPSERTED"
    ]
    assert len(upserted) == 1, "Paper metadata-only vẫn phải ghi 1 PAPER_UPSERTED"
    assert paper.status == "indexed"


@pytest.mark.asyncio
async def test_producer_no_event_when_paper_deleted():
    """Nhánh paper-đã-xóa (is_deleted=True) → KHÔNG ghi event PAPER_UPSERTED."""
    paper = _make_paper(is_deleted=False)

    db = AsyncMock()
    added_objects = []
    db.add = lambda obj: added_objects.append(obj)

    execute_result = AsyncMock()
    execute_result.scalar_one_or_none = MagicMock(return_value=paper)
    db.execute = AsyncMock(return_value=execute_result)
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    # Simulate race condition: paper bị xóa trong lúc ingest (sau db.refresh)
    def _refresh_sets_deleted(p):
        p.is_deleted = True

    db.refresh = AsyncMock(side_effect=_refresh_sets_deleted)

    redis = AsyncMock()
    ctx = {"redis": redis, "session_factory": _FakeSessionFactory(db)}

    with (
        patch("backend.worker._extract_text", return_value="some text content"),
        patch("backend.worker.chunk_text", return_value=[("parent", ["child"])]),
        patch("backend.worker.GeminiEmbeddingClient") as MockEmbed,
        patch("backend.worker.publish_progress", new_callable=AsyncMock),
        patch("backend.worker.publish_completed", new_callable=AsyncMock),
    ):
        mock_client = AsyncMock()
        mock_client.embed_batch = AsyncMock(return_value=[[0.0] * 1536])
        MockEmbed.return_value = mock_client

        from backend.worker import ingest_paper_task
        await ingest_paper_task(ctx, "paper-uuid-1")

    from backend.src.modules.workspace.infrastructure.orm_models import SyncOutboxORM
    outbox_events = [o for o in added_objects if isinstance(o, SyncOutboxORM)]
    upserted_events = [e for e in outbox_events if e.event_type == "PAPER_UPSERTED"]
    assert len(upserted_events) == 0, "Nhánh paper-đã-xóa KHÔNG được ghi PAPER_UPSERTED"
