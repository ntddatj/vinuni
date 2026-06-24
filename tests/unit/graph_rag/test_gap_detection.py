"""Unit tests cho GapDetectionUseCase — AC#29 + Story 4.10 gap_detection_detailed."""
import pytest

from backend.src.modules.graph_rag.application.use_cases import GapDetectionUseCase
from backend.src.modules.graph_rag.domain.entities import GapContext


# ── Fake Neo4j helpers ────────────────────────────────────────────────────────

class _FakeNeo4jResult:
    def __init__(self, records):
        self._records = records

    async def single(self):
        return self._records[0] if self._records else None

    async def data(self):
        return self._records

    async def __aiter__(self):
        for r in self._records:
            yield r


class _FakeNeo4jSession:
    def __init__(self, run_side_effects=None):
        self._effects = list(run_side_effects or [])
        self._call_count = 0

    async def run(self, query, **kwargs):
        if self._call_count < len(self._effects):
            effect = self._effects[self._call_count]
            if isinstance(effect, Exception):
                self._call_count += 1
                raise effect
            result = _FakeNeo4jResult(effect)
        else:
            result = _FakeNeo4jResult([])
        self._call_count += 1
        return result

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class _FakeNeo4jDriver:
    def __init__(self, run_side_effects=None):
        self._effects = run_side_effects or []

    def session(self):
        return _FakeNeo4jSession(self._effects)


class _BrokenNeo4jDriver:
    """Driver mô phỏng Neo4j down: ngay cả việc mở session cũng raise."""

    def session(self):
        raise RuntimeError("Neo4j unavailable")


# ── gap_detection tests ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gap_detection_returns_empty_when_no_gaps():
    """3 queries trả empty → GapContext với 2 list rỗng."""
    driver = _FakeNeo4jDriver(run_side_effects=[[], [], []])
    use_case = GapDetectionUseCase(driver)
    result = await use_case.gap_detection("proj-1")
    assert isinstance(result, GapContext)
    assert result.flagged_nodes == []
    assert result.flagged_edges == []


@pytest.mark.asyncio
async def test_gap_detection_returns_contradiction_nodes():
    """Query 1 trả 1 record CONTRADICTS → 2 flagged_nodes has_contradiction + 1 flagged_edge."""
    driver = _FakeNeo4jDriver(run_side_effects=[
        [{"finding1_id": "f1", "finding2_id": "f2", "paper1_id": "p1", "paper2_id": "p2"}],
        [],
        [],
    ])
    use_case = GapDetectionUseCase(driver)
    result = await use_case.gap_detection("proj-1")
    assert len(result.flagged_edges) == 1
    assert result.flagged_edges[0].finding1_id == "f1"
    assert result.flagged_edges[0].reason == "contradicts"
    node_ids = {n.paper_id for n in result.flagged_nodes}
    assert "p1" in node_ids
    assert "p2" in node_ids
    for n in result.flagged_nodes:
        assert n.reason == "has_contradiction"


@pytest.mark.asyncio
async def test_gap_detection_returns_isolated_cluster():
    """Query 2 trả 1 record → 1 flagged_node isolated_cluster."""
    driver = _FakeNeo4jDriver(run_side_effects=[
        [],
        [{"paper_id": "p-isolated"}],
        [],
    ])
    use_case = GapDetectionUseCase(driver)
    result = await use_case.gap_detection("proj-1")
    assert len(result.flagged_nodes) == 1
    assert result.flagged_nodes[0].paper_id == "p-isolated"
    assert result.flagged_nodes[0].reason == "isolated_cluster"


@pytest.mark.asyncio
async def test_gap_detection_returns_unfilled_limitation():
    """Query 3 trả 1 record → 1 flagged_node has_unfilled_limitation."""
    driver = _FakeNeo4jDriver(run_side_effects=[
        [],
        [],
        [{"paper_id": "p-limit"}],
    ])
    use_case = GapDetectionUseCase(driver)
    result = await use_case.gap_detection("proj-1")
    assert len(result.flagged_nodes) == 1
    assert result.flagged_nodes[0].paper_id == "p-limit"
    assert result.flagged_nodes[0].reason == "has_unfilled_limitation"


@pytest.mark.asyncio
async def test_gap_detection_dedup_priority_contradiction_over_isolated():
    """Paper xuất hiện ở cả query 1 và query 2 → chỉ 1 entry với has_contradiction."""
    driver = _FakeNeo4jDriver(run_side_effects=[
        [{"finding1_id": "f1", "finding2_id": "f2", "paper1_id": "p-shared", "paper2_id": "p2"}],
        [{"paper_id": "p-shared"}],
        [],
    ])
    use_case = GapDetectionUseCase(driver)
    result = await use_case.gap_detection("proj-1")
    shared_nodes = [n for n in result.flagged_nodes if n.paper_id == "p-shared"]
    assert len(shared_nodes) == 1
    assert shared_nodes[0].reason == "has_contradiction"


@pytest.mark.asyncio
async def test_gap_detection_dedup_priority_unfilled_over_isolated():
    """Paper xuất hiện ở query 2 (isolated) rồi query 3 (unfilled) → has_unfilled_limitation."""
    driver = _FakeNeo4jDriver(run_side_effects=[
        [],
        [{"paper_id": "p-both"}],
        [{"paper_id": "p-both"}],
    ])
    use_case = GapDetectionUseCase(driver)
    result = await use_case.gap_detection("proj-1")
    matching = [n for n in result.flagged_nodes if n.paper_id == "p-both"]
    assert len(matching) == 1
    assert matching[0].reason == "has_unfilled_limitation"


@pytest.mark.asyncio
async def test_gap_detection_graceful_on_neo4j_exception():
    """Mock session.run raise Exception → trả GapContext() rỗng, không raise."""
    driver = _FakeNeo4jDriver(run_side_effects=[
        Exception("Neo4j connection error"),
        Exception("Neo4j connection error"),
        Exception("Neo4j connection error"),
    ])
    use_case = GapDetectionUseCase(driver)
    result = await use_case.gap_detection("proj-1")
    assert result.flagged_nodes == []
    assert result.flagged_edges == []


@pytest.mark.asyncio
async def test_gap_detection_graceful_on_session_acquisition_failure():
    """Neo4j down: driver.session() raise → trả GapContext() rỗng, không raise (AC#4)."""
    use_case = GapDetectionUseCase(_BrokenNeo4jDriver())
    result = await use_case.gap_detection("proj-1")
    assert isinstance(result, GapContext)
    assert result.flagged_nodes == []
    assert result.flagged_edges == []


# ── gap_detection_detailed tests ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gap_detection_detailed_returns_empty_when_no_data():
    """3 queries trả empty → list rỗng."""
    driver = _FakeNeo4jDriver(run_side_effects=[[], [], []])
    use_case = GapDetectionUseCase(driver)
    result = await use_case.gap_detection_detailed("proj-1")
    assert result == []


@pytest.mark.asyncio
async def test_gap_detection_detailed_contradiction_builds_title_and_description():
    """Query CONTRADICTS_DETAILED → 1 item với title/description ghép từ entity thật."""
    driver = _FakeNeo4jDriver(run_side_effects=[
        [{
            "finding1_id": "f1", "finding2_id": "f2",
            "paper1_id": "p1", "paper2_id": "p2",
            "finding1_text": "Phương pháp A hiệu quả hơn B",
            "finding2_text": "Phương pháp B hiệu quả hơn A",
            "paper1_title": "Paper Alpha", "paper2_title": "Paper Beta",
        }],
        [],
        [],
    ])
    use_case = GapDetectionUseCase(driver)
    result = await use_case.gap_detection_detailed("proj-1")

    assert len(result) == 1
    item = result[0]
    assert item.type == "contradiction"
    assert item.reason == "contradiction"
    # Tiêu đề ngắn gọn theo loại (giữa hai bài khác nhau) — tên bài ở papers, không nhồi tiêu đề.
    assert item.title == "Hai nghiên cứu đưa ra kết luận trái ngược nhau"
    assert "Phương pháp A hiệu quả hơn B" in item.description
    assert "Phương pháp B hiệu quả hơn A" in item.description
    assert len(item.papers) == 2
    paper_ids = {p.paper_id for p in item.papers}
    assert "p1" in paper_ids and "p2" in paper_ids
    assert {p.title for p in item.papers} == {"Paper Alpha", "Paper Beta"}


@pytest.mark.asyncio
async def test_gap_detection_detailed_contradiction_same_paper_title():
    """Mâu thuẫn nội tại (2 finding cùng 1 bài, paper1_id == paper2_id) → tiêu đề riêng + paper_count=1."""
    driver = _FakeNeo4jDriver(run_side_effects=[
        [{
            "finding1_id": "f1", "finding2_id": "f2",
            "paper1_id": "p1", "paper2_id": "p1",
            "finding1_text": "Tăng đa dạng vi sinh", "finding2_text": "Giảm đa dạng vi sinh",
            "paper1_title": "Tổng quan ngô Bt", "paper2_title": "Tổng quan ngô Bt",
        }],
        [],
        [],
    ])
    use_case = GapDetectionUseCase(driver)
    result = await use_case.gap_detection_detailed("proj-1")
    assert len(result) == 1
    item = result[0]
    assert item.title == "Hai kết luận trái ngược trong cùng một nghiên cứu"
    assert item.evidence.get("paper_count") == 1


@pytest.mark.asyncio
async def test_gap_detection_detailed_contradiction_dedup_reciprocal_edges():
    """CONTRADICTS có hướng — cả f1→f2 lẫn f2→f1 cho cùng cặp → chỉ 1 card (khử trùng theo cặp)."""
    driver = _FakeNeo4jDriver(run_side_effects=[
        [
            {
                "finding1_id": "f1", "finding2_id": "f2",
                "paper1_id": "p1", "paper2_id": "p2",
                "finding1_text": "A", "finding2_text": "B",
                "paper1_title": "Paper Alpha", "paper2_title": "Paper Beta",
            },
            {
                "finding1_id": "f2", "finding2_id": "f1",
                "paper1_id": "p2", "paper2_id": "p1",
                "finding1_text": "B", "finding2_text": "A",
                "paper1_title": "Paper Beta", "paper2_title": "Paper Alpha",
            },
        ],
        [],
        [],
    ])
    use_case = GapDetectionUseCase(driver)
    result = await use_case.gap_detection_detailed("proj-1")
    contradictions = [i for i in result if i.type == "contradiction"]
    assert len(contradictions) == 1


@pytest.mark.asyncio
async def test_gap_detection_detailed_evidence_has_no_internal_ids():
    """Evidence chỉ chứa số liệu (count) — KHÔNG lộ id nội bộ (finding/limitation id) ra UI."""
    driver = _FakeNeo4jDriver(run_side_effects=[
        [{
            "finding1_id": "f1", "finding2_id": "f2",
            "paper1_id": "p1", "paper2_id": "p2",
            "finding1_text": "A", "finding2_text": "B",
            "paper1_title": "Paper Alpha", "paper2_title": "Paper Beta",
        }],
        [],
        [{
            "limitation_id": "lim-1", "description": "Chưa kiểm chứng",
            "owner_paper_id": "p-owner", "owner_paper_title": "Owner Paper",
        }],
    ])
    use_case = GapDetectionUseCase(driver)
    result = await use_case.gap_detection_detailed("proj-1")
    for item in result:
        keys = set(item.evidence.keys())
        assert not any(k.endswith("_id") for k in keys), f"evidence lộ id nội bộ: {keys}"
        assert all(isinstance(v, (int, float, str, bool)) for v in item.evidence.values())


@pytest.mark.asyncio
async def test_gap_detection_detailed_isolated_cluster():
    """Query ISOLATED_DETAILED → 1 item isolated_cluster với paper title."""
    driver = _FakeNeo4jDriver(run_side_effects=[
        [],
        [{"paper_id": "p-iso", "paper_title": "Isolated Paper"}],
        [],
    ])
    use_case = GapDetectionUseCase(driver)
    result = await use_case.gap_detection_detailed("proj-1")

    assert len(result) == 1
    item = result[0]
    assert item.type == "isolated_cluster"
    assert item.id == "p-iso"
    assert item.title == "Nghiên cứu chưa có liên kết trích dẫn"
    assert item.evidence.get("neighbor_count") == 0
    assert len(item.papers) == 1
    assert item.papers[0].paper_id == "p-iso"
    assert item.papers[0].title == "Isolated Paper"


@pytest.mark.asyncio
async def test_gap_detection_detailed_unfilled_limitation():
    """Query UNFILLED_DETAILED → 1 item unfilled_limitation với description từ l.description."""
    driver = _FakeNeo4jDriver(run_side_effects=[
        [],
        [],
        [{
            "limitation_id": "lim-1",
            "description": "Phương pháp chưa được kiểm chứng trên dữ liệu lớn",
            "owner_paper_id": "p-owner",
            "owner_paper_title": "Owner Paper",
        }],
    ])
    use_case = GapDetectionUseCase(driver)
    result = await use_case.gap_detection_detailed("proj-1")

    assert len(result) == 1
    item = result[0]
    assert item.type == "unfilled_limitation"
    assert item.id == "lim-1"
    assert item.title == "Hạn chế nghiên cứu chưa được giải quyết"
    assert item.description == "Phương pháp chưa được kiểm chứng trên dữ liệu lớn"
    assert item.papers[0].paper_id == "p-owner"
    assert item.papers[0].title == "Owner Paper"


@pytest.mark.asyncio
async def test_gap_detection_detailed_skips_limitation_with_empty_description():
    """Limitation có description None/empty → bỏ qua (không tạo card rỗng)."""
    driver = _FakeNeo4jDriver(run_side_effects=[
        [],
        [],
        [{"limitation_id": "lim-empty", "description": "", "owner_paper_id": "p1", "owner_paper_title": "P1"}],
    ])
    use_case = GapDetectionUseCase(driver)
    result = await use_case.gap_detection_detailed("proj-1")
    assert result == []


@pytest.mark.asyncio
async def test_gap_detection_detailed_neo4j_down_returns_empty():
    """Neo4j down (session acquisition fail) → trả [], không raise."""
    use_case = GapDetectionUseCase(_BrokenNeo4jDriver())
    result = await use_case.gap_detection_detailed("proj-1")
    assert result == []


@pytest.mark.asyncio
async def test_gap_detection_detailed_query_exception_returns_partial():
    """Query 1 raise, query 2 + 3 OK → chỉ trả items từ query 2 và 3."""
    driver = _FakeNeo4jDriver(run_side_effects=[
        Exception("Neo4j error"),
        [{"paper_id": "p-iso", "paper_title": "Isolated Paper"}],
        [],
    ])
    use_case = GapDetectionUseCase(driver)
    result = await use_case.gap_detection_detailed("proj-1")
    assert len(result) == 1
    assert result[0].type == "isolated_cluster"


# ── graph_search tests ────────────────────────────────────────────────────────

from unittest.mock import MagicMock


def _fake_node(nid, labels, title_or_name):
    n = MagicMock()
    n.labels = frozenset(labels)
    n.__getitem__ = lambda self, k: {"id": nid}.get(k)
    data = {"id": nid, "project_id": "proj-1"}
    if "Author" in labels:
        data["name"] = title_or_name
    else:
        data["title"] = title_or_name
        data["state"] = "full_text"
    n.get = lambda k, default=None: data.get(k, default)
    return n


@pytest.mark.asyncio
async def test_graph_search_returns_nodes_and_edges():
    """Mock trả 1 record → GraphContext có nodes và edges."""
    start_node = _fake_node("p1", ["Paper"], "Paper One")
    neighbor_node = _fake_node("a1", ["Author"], "Author One")
    rel = MagicMock()

    record = {
        "start": start_node,
        "neighbor": neighbor_node,
        "r": rel,
        "start_id": "p1",
        "neighbor_id": "a1",
        "rel_id": "rel-1",
        "rel_type": "AUTHORED_BY",
        "start_is_source": True,
    }

    driver = _FakeNeo4jDriver(run_side_effects=[[record]])
    use_case = GapDetectionUseCase(driver)
    result = await use_case.graph_search(["Paper One"], "proj-1")

    node_ids = {n.id for n in result.nodes}
    assert "p1" in node_ids
    assert "a1" in node_ids
    assert len(result.edges) == 1
    assert result.edges[0].source == "p1"
    assert result.edges[0].target == "a1"


@pytest.mark.asyncio
async def test_graph_search_returns_empty_when_no_match():
    """Mock trả empty → GraphContext() rỗng."""
    driver = _FakeNeo4jDriver(run_side_effects=[[]])
    use_case = GapDetectionUseCase(driver)
    result = await use_case.graph_search(["NonExistent"], "proj-1")
    assert result.nodes == []
    assert result.edges == []
