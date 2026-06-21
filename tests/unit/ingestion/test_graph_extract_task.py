"""Unit tests cho graph_extract_task (Story 4.3 AC:14 + Story 4.9 AC:5)."""
import json
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


def _make_cand_result(candidates=None):
    """Tạo mock result cho execute thứ 3 (query candidate papers)."""
    cand_result = AsyncMock()
    rows = []
    for c in (candidates or []):
        row = MagicMock()
        row.id = c["id"]
        row.title = c["title"]
        row.doi = c.get("doi")
        rows.append(row)
    cand_result.all = MagicMock(return_value=rows)
    return cand_result


def _make_db(paper=None, chunks=None, candidates=None):
    """Tạo mock DB session.

    Args:
        candidates: nếu không None, thêm execute thứ 3 (query CITES candidates).
                    Nếu None, không cấp execute thứ 3 — phù hợp khi không có references.
    """
    db = AsyncMock()

    paper_result = AsyncMock()
    paper_result.scalar_one_or_none = MagicMock(return_value=paper)

    chunk_result = AsyncMock()
    chunks_list = chunks or []
    chunk_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=chunks_list)))

    side_effects = [paper_result, chunk_result]
    if candidates is not None:
        side_effects.append(_make_cand_result(candidates))

    db.execute = AsyncMock(side_effect=side_effects)
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


# ---------- CITES producer (Story 4.6) ----------

_BASE_DATA = {
    "findings": [{"id": "f1", "description": "Finding 1", "confidence_score": 0.9}],
    "limitations": [],
    "methods": [],
    "datasets": [],
    "topics": [{"id": "t1", "name": "ML"}],
    "problems": [],
    "contradicts": [],
    "supports": [],
}


@pytest.mark.asyncio
async def test_graph_extract_task_emits_cites_on_match():
    """Paper có references, candidate paper trong DB có title khớp → SyncOutboxORM(CITES) được add."""
    paper = _make_paper(id="paper-citing", project_id="proj-1")
    candidates = [{"id": "paper-cited", "title": "Machine Learning Basics", "doi": None}]
    db = _make_db(paper=paper, chunks=[], candidates=candidates)

    data = {
        **_BASE_DATA,
        "references": [{"title": "Machine Learning Basics", "doi": None}],
    }
    ctx = {"session_factory": _FakeSessionFactory(db), "redis": AsyncMock()}

    with patch("backend.worker.GraphExtractor") as MockExtractor:
        instance = AsyncMock()
        instance.extract = AsyncMock(return_value=data)
        MockExtractor.return_value = instance

        await graph_extract_task(ctx, "paper-citing")

    # Phải có ít nhất 2 lần db.add: ONTOLOGY_EXTRACTED + CITES
    assert db.add.call_count >= 2
    added_events = [c[0][0] for c in db.add.call_args_list]
    event_types = [e.event_type for e in added_events]
    assert "CITES" in event_types

    cites_event = next(e for e in added_events if e.event_type == "CITES")
    assert cites_event.payload["citing_paper_id"] == "paper-citing"
    assert cites_event.payload["cited_paper_id"] == "paper-cited"
    assert cites_event.project_id == "proj-1"
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_graph_extract_task_no_cites_when_no_references():
    """Extract trả dict KHÔNG có references → không query candidates, không add CITES."""
    paper = _make_paper()
    db = _make_db(paper=paper, chunks=[])  # không cấp execute thứ 3

    ctx = {"session_factory": _FakeSessionFactory(db), "redis": AsyncMock()}

    with patch("backend.worker.GraphExtractor") as MockExtractor:
        instance = AsyncMock()
        instance.extract = AsyncMock(return_value={**_BASE_DATA})  # không có 'references'
        MockExtractor.return_value = instance

        await graph_extract_task(ctx, "paper-1")

    added_events = [c[0][0] for c in db.add.call_args_list]
    event_types = [e.event_type for e in added_events]
    assert "CITES" not in event_types
    assert "ONTOLOGY_EXTRACTED" in event_types
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_graph_extract_task_no_cites_when_empty_references():
    """Extract trả references=[] → không query candidates, không add CITES."""
    paper = _make_paper()
    db = _make_db(paper=paper, chunks=[])

    ctx = {"session_factory": _FakeSessionFactory(db), "redis": AsyncMock()}

    with patch("backend.worker.GraphExtractor") as MockExtractor:
        instance = AsyncMock()
        instance.extract = AsyncMock(return_value={**_BASE_DATA, "references": []})
        MockExtractor.return_value = instance

        await graph_extract_task(ctx, "paper-1")

    added_events = [c[0][0] for c in db.add.call_args_list]
    assert all(e.event_type != "CITES" for e in added_events)
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_graph_extract_task_skips_self_cite():
    """Reference khớp về chính paper đang xử lý → không add CITES."""
    paper = _make_paper(id="paper-self", project_id="proj-1")
    # Candidate có id trùng paper đang xử lý (giả lập trường hợp edge case)
    candidates = [{"id": "paper-self", "title": "Self Paper Title", "doi": None}]
    db = _make_db(paper=paper, chunks=[], candidates=candidates)

    data = {**_BASE_DATA, "references": [{"title": "Self Paper Title"}]}
    ctx = {"session_factory": _FakeSessionFactory(db), "redis": AsyncMock()}

    with patch("backend.worker.GraphExtractor") as MockExtractor:
        instance = AsyncMock()
        instance.extract = AsyncMock(return_value=data)
        MockExtractor.return_value = instance

        await graph_extract_task(ctx, "paper-self")

    added_events = [c[0][0] for c in db.add.call_args_list]
    assert all(e.event_type != "CITES" for e in added_events)


@pytest.mark.asyncio
async def test_graph_extract_task_skips_unmatched_reference():
    """Reference không khớp candidate nào → không add CITES (không tạo paper ma)."""
    paper = _make_paper(id="paper-1", project_id="proj-1")
    candidates = [{"id": "paper-other", "title": "Completely Unrelated Topic", "doi": None}]
    db = _make_db(paper=paper, chunks=[], candidates=candidates)

    data = {**_BASE_DATA, "references": [{"title": "Quantum Gravity Theory"}]}
    ctx = {"session_factory": _FakeSessionFactory(db), "redis": AsyncMock()}

    with patch("backend.worker.GraphExtractor") as MockExtractor:
        instance = AsyncMock()
        instance.extract = AsyncMock(return_value=data)
        MockExtractor.return_value = instance

        await graph_extract_task(ctx, "paper-1")

    added_events = [c[0][0] for c in db.add.call_args_list]
    assert all(e.event_type != "CITES" for e in added_events)


@pytest.mark.asyncio
async def test_graph_extract_task_tolerates_malformed_references():
    """LLM trả references có title=null / không phải dict → bỏ qua an toàn, KHÔNG crash.

    Regression (code review 4.6): r.get('title','').strip() từng AttributeError khi
    title=None hoặc ref là string, cuốn theo cả commit ONTOLOGY_EXTRACTED.
    """
    paper = _make_paper(id="paper-1", project_id="proj-1")
    candidates = [{"id": "paper-cited", "title": "Machine Learning Basics", "doi": None}]
    db = _make_db(paper=paper, chunks=[], candidates=candidates)

    data = {
        **_BASE_DATA,
        "references": [
            {"title": None, "doi": "10.1/x"},   # title null → bỏ
            "Smith 2020, A Paper",               # không phải dict → bỏ
            {"doi": "10.2/y"},                    # thiếu title → bỏ
            {"title": "   "},                     # title rỗng sau strip → bỏ
            {"title": "Machine Learning Basics"}, # hợp lệ → khớp candidate
        ],
    }
    ctx = {"session_factory": _FakeSessionFactory(db), "redis": AsyncMock()}

    with patch("backend.worker.GraphExtractor") as MockExtractor:
        instance = AsyncMock()
        instance.extract = AsyncMock(return_value=data)
        MockExtractor.return_value = instance

        await graph_extract_task(ctx, "paper-1")

    added_events = [c[0][0] for c in db.add.call_args_list]
    cites = [e for e in added_events if e.event_type == "CITES"]
    assert len(cites) == 1
    assert cites[0].payload["cited_paper_id"] == "paper-cited"
    db.commit.assert_awaited_once()


# ─── Story 4.9 AC#5: Integration test — GraphExtractor THẬT, mock chỉ ainvoke ───────────

_REFS_JSON_RESPONSE = json.dumps({
    "findings": [{"id": "f1", "description": "Finding about GMO", "confidence_score": 0.9}],
    "limitations": [],
    "methods": [],
    "datasets": [],
    "topics": [{"id": "t1", "name": "Genetics"}],
    "problems": [],
    "contradicts": [],
    "supports": [],
    "references": [
        {"title": "Cited GMO Paper", "doi": "10.1234/gmo"},
    ],
})


@pytest.mark.asyncio
async def test_graph_extract_task_real_extractor_emits_cites():
    """Story 4.9 AC#5: GraphExtractor THẬT (chỉ mock ainvoke tầng LLM) + DB candidate khớp
    → emit SyncOutboxORM(event_type='CITES').

    Lấp đúng lỗ hổng mà test 4.6 để lọt do mock toàn bộ extractor.extract() —
    ở đây ta KHÔNG mock GraphExtractor, chỉ mock LLMRouter để tránh gọi API thật.
    """
    paper = _make_paper(id="paper-citing", project_id="proj-1")
    candidates = [{"id": "paper-cited", "title": "Cited GMO Paper", "doi": "10.1234/gmo"}]
    db = _make_db(paper=paper, chunks=[], candidates=candidates)
    ctx = {"session_factory": _FakeSessionFactory(db), "redis": AsyncMock()}

    # Mock chỉ ở tầng LLM (ainvoke) — giữ GraphExtractor.extract() thật
    mock_llm_result = MagicMock()
    mock_llm_result.content = _REFS_JSON_RESPONSE

    with patch(
        "backend.src.modules.ingestion.infrastructure.graph_extractor.LLMRouter"
    ) as MockRouter:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_llm_result)
        MockRouter.return_value.get_llm_client = AsyncMock(return_value=mock_llm)

        await graph_extract_task(ctx, "paper-citing")

    added_events = [c[0][0] for c in db.add.call_args_list]
    event_types = [e.event_type for e in added_events]

    # Phải có ONTOLOGY_EXTRACTED
    assert "ONTOLOGY_EXTRACTED" in event_types

    # Phải có CITES — đây là điểm mà test 4.6 KHÔNG bắt được do mock extractor
    assert "CITES" in event_types, (
        "CITES event không được emit. Kiểm tra: (1) references trong JSON LLM response, "
        "(2) candidate paper có title khớp, (3) GraphExtractor.extract() không bị mock."
    )

    cites_event = next(e for e in added_events if e.event_type == "CITES")
    assert cites_event.payload["citing_paper_id"] == "paper-citing"
    assert cites_event.payload["cited_paper_id"] == "paper-cited"
    db.commit.assert_awaited_once()


# ─── Story 4.7: enqueue fills_gap_task sau graph_extract_task ────────────────

@pytest.mark.asyncio
async def test_graph_extract_task_enqueues_fills_gap():
    """Sau commit thành công → ctx['redis'].enqueue_job được gọi với 'fills_gap_task' + project_id."""
    paper = _make_paper(id="paper-1", project_id="proj-1")
    db = _make_db(paper=paper, chunks=[])
    redis = AsyncMock()
    ctx = {"session_factory": _FakeSessionFactory(db), "redis": redis}

    with patch("backend.worker.GraphExtractor") as MockExtractor:
        instance = AsyncMock()
        instance.extract = AsyncMock(return_value={**_BASE_DATA})
        MockExtractor.return_value = instance

        await graph_extract_task(ctx, "paper-1")

    # Kiểm tra enqueue_job đã được gọi với "fills_gap_task"
    redis.enqueue_job.assert_awaited()
    call_args = redis.enqueue_job.call_args
    assert call_args.args[0] == "fills_gap_task"
    assert call_args.args[1] == "proj-1"
    assert call_args.kwargs.get("_job_id") == "fills_gap:proj-1"


@pytest.mark.asyncio
async def test_graph_extract_task_real_extractor_text_with_references_at_offset():
    """Story 4.9 AC#5: với text có References ở offset ~37000, GraphExtractor THẬT gửi đủ
    text tới LLM (không bị cắt head/tail) → LLM nhận JSON có references → CITES được emit.

    Bảo chứng: nếu còn _build_extraction_text, References@37000 sẽ bị cắt và test thấy
    prompt KHÔNG chứa references → LLM mock trả [] → CITES không được add → test FAIL.
    """
    paper = _make_paper(id="paper-long", project_id="proj-1")
    candidates = [{"id": "paper-ref", "title": "Referenced Academic Paper", "doi": None}]

    # Tạo chunk content có References ở vị trí sau 37000 chars
    body = "Academic content paragraph. " * 1300  # ~36400 chars
    refs_suffix = "\n\nReferences\nReferenced Academic Paper (2020). doi:10.99/ref"
    long_text = body + refs_suffix  # ~37000+ chars

    # Tạo chunk mock với nội dung dài
    chunk = MagicMock()
    chunk.content = long_text

    db_with_chunk = AsyncMock()
    paper_result = AsyncMock()
    paper_result.scalar_one_or_none = MagicMock(return_value=paper)
    chunk_result = AsyncMock()
    chunk_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[chunk])))
    cand_result = _make_cand_result(candidates)
    db_with_chunk.execute = AsyncMock(side_effect=[paper_result, chunk_result, cand_result])
    db_with_chunk.add = MagicMock()
    db_with_chunk.commit = AsyncMock()

    ctx = {"session_factory": _FakeSessionFactory(db_with_chunk), "redis": AsyncMock()}

    mock_llm_result = MagicMock()
    mock_llm_result.content = json.dumps({
        "findings": [{"id": "f1", "description": "Long paper finding", "confidence_score": 0.8}],
        "limitations": [],
        "methods": [],
        "datasets": [],
        "topics": [{"id": "t1", "name": "Academic"}],
        "problems": [],
        "contradicts": [],
        "supports": [],
        "references": [{"title": "Referenced Academic Paper"}],
    })

    # Capture prompt thật sự gửi tới LLM. KHÔNG trả references vô điều kiện — nếu mock bỏ qua
    # prompt, test sẽ PASS kể cả khi trimming còn (docstring sẽ thành lời hứa rỗng).
    captured_prompts: list[str] = []

    async def _capture_invoke(prompt):
        captured_prompts.append(prompt)
        return mock_llm_result

    with patch(
        "backend.src.modules.ingestion.infrastructure.graph_extractor.LLMRouter"
    ) as MockRouter:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = _capture_invoke
        MockRouter.return_value.get_llm_client = AsyncMock(return_value=mock_llm)

        await graph_extract_task(ctx, "paper-long")

    # Bảo chứng trimming đã bị bỏ: References@offset ~37000 PHẢI lọt vào prompt gửi LLM.
    # Nếu còn _build_extraction_text / cắt head 30000 → đoạn này bị rớt → assert FAIL.
    assert len(captured_prompts) == 1
    assert "Referenced Academic Paper" in captured_prompts[0]
    assert len(captured_prompts[0]) > 30000

    added_events = [c[0][0] for c in db_with_chunk.add.call_args_list]
    event_types = [e.event_type for e in added_events]
    assert "CITES" in event_types
