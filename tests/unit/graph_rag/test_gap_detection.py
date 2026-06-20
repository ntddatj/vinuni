"""Unit tests cho GapDetectionUseCase — AC#29."""
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
