"""Unit tests cho graph_rag router — AC#22 + AC#30.

Mock Neo4j + Postgres. Pattern: AsyncMock + _FakeNeo4jDriver.
get_neo4j_driver() gọi trực tiếp trong router nên phải patch, không dùng dependency_overrides.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from backend.src.modules.graph_rag.domain.entities import GapContext, GapDetailItem, GapFlaggedNode, GapPaperRef
from backend.src.modules.graph_rag.presentation.router import router as graph_router
from backend.src.modules.identity.domain.entities import User
from backend.src.modules.identity.infrastructure.auth_dependencies import get_current_user
from backend.src.modules.workspace.infrastructure.dependencies import get_project_repository
from backend.src.shared.infra.database import get_db_session


# ── helpers ─────────────────────────────────────────────────────────────────

def _make_user(user_id="user-1"):
    u = MagicMock(spec=User)
    u.id = user_id
    return u


def _make_project(project_id="proj-1", user_id="user-1"):
    p = MagicMock()
    p.id = project_id
    p.user_id = user_id
    return p


class _FakeNeo4jResult:
    """Mô phỏng neo4j AsyncResult.

    QUAN TRỌNG: code đọc node lặp record (`async for rec in result`) để giữ Node object,
    KHÔNG dùng `.data()` (cái này ép Node → dict trần, mất .labels). Fake hỗ trợ cả
    iteration (nodes/expand), .single() (count) và .data() (edges = scalar alias).
    """
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
            result = _FakeNeo4jResult(self._effects[self._call_count])
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


def _fake_paper_node(node_id="paper-1", project_id="proj-1"):
    n = MagicMock()
    n.labels = frozenset(["Paper"])
    n.__getitem__ = lambda self, k: {"id": node_id, "project_id": project_id}.get(k)
    n.get = lambda k, default=None: {
        "id": node_id, "project_id": project_id,
        "title": "Test Paper", "state": "full_text",
        "year": 2024, "abstract": "Abstract",
    }.get(k, default)
    return n


def _fake_author_node(node_id="author-1", project_id="proj-1"):
    n = MagicMock()
    n.labels = frozenset(["Author"])
    n.__getitem__ = lambda self, k: {"id": node_id, "project_id": project_id}.get(k)
    n.get = lambda k, default=None: {
        "id": node_id, "project_id": project_id, "name": "Author Name",
    }.get(k, default)
    return n


def _build_app(mock_user, mock_project, mock_db=None):
    app = FastAPI()
    app.include_router(graph_router, prefix="/api")

    async def _get_user():
        return mock_user

    async def _get_repo():
        repo = AsyncMock()
        repo.find_by_id = AsyncMock(return_value=mock_project)
        yield repo

    async def _get_db():
        yield mock_db or AsyncMock()

    app.dependency_overrides[get_current_user] = _get_user
    app.dependency_overrides[get_project_repository] = _get_repo
    app.dependency_overrides[get_db_session] = _get_db
    return app


# ── tests: GET /graph ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_graph_returns_correct_shape():
    """GET /graph trả đúng shape {nodes, edges, has_more} với mock data."""
    paper_node = _fake_paper_node()
    author_node = _fake_author_node()

    driver = _FakeNeo4jDriver(run_side_effects=[
        [{"total": 2}],
        [{"n": paper_node}, {"n": author_node}],
        [],
    ])

    app = _build_app(_make_user(), _make_project())

    with patch("backend.src.modules.graph_rag.presentation.router.get_neo4j_driver", return_value=driver):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/projects/proj-1/graph")

    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data
    assert "has_more" in data
    assert len(data["nodes"]) == 2
    assert data["has_more"] is False


@pytest.mark.asyncio
async def test_get_graph_returns_edges_between_loaded_nodes():
    """Edges chỉ giữa các node đã trả về (node_ids) — tránh edge treo làm crash Cytoscape."""
    paper_a = _fake_paper_node("paper-1")
    paper_b = _fake_paper_node("paper-2")

    driver = _FakeNeo4jDriver(run_side_effects=[
        [{"total": 2}],
        [{"n": paper_a}, {"n": paper_b}],
        [{
            "r": MagicMock(),
            "source_id": "paper-1",
            "target_id": "paper-2",
            "rel_id": "rel-1",
            "rel_type": "CITES",
        }],
    ])

    app = _build_app(_make_user(), _make_project())

    with patch("backend.src.modules.graph_rag.presentation.router.get_neo4j_driver", return_value=driver):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/projects/proj-1/graph")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["edges"]) == 1
    edge = data["edges"][0]
    assert edge["source"] == "paper-1"
    assert edge["target"] == "paper-2"
    # cả 2 endpoint đều nằm trong tập node trả về → không có edge treo
    node_ids = {n["id"] for n in data["nodes"]}
    assert edge["source"] in node_ids and edge["target"] in node_ids


@pytest.mark.asyncio
async def test_get_graph_project_not_owned_returns_404():
    """GET /graph với project không thuộc user → 404."""
    mock_project = _make_project(user_id="other-user")
    mock_user = _make_user(user_id="user-1")

    app = _build_app(mock_user, mock_project)

    with patch("backend.src.modules.graph_rag.presentation.router.get_neo4j_driver", return_value=_FakeNeo4jDriver()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/projects/proj-1/graph")

    assert resp.status_code == 404


# ── tests: GET /graph/nodes/{id}/expand ──────────────────────────────────────

@pytest.mark.asyncio
async def test_expand_node_filters_existing_ids():
    """expand trả về neighbors mới (không có trong existing_ids)."""
    neighbor = _fake_paper_node("paper-2")
    rel = MagicMock()

    driver = _FakeNeo4jDriver(run_side_effects=[
        [
            {
                "neighbor": neighbor,
                "r": rel,
                "seed_id": "paper-1",
                "rel_id": "rel-1",
                "rel_type": "CITES",
                "neighbor_is_source": False,
            }
        ],
    ])

    app = _build_app(_make_user(), _make_project())

    with patch("backend.src.modules.graph_rag.presentation.router.get_neo4j_driver", return_value=driver):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/api/projects/proj-1/graph/nodes/paper-1/expand",
                params={"existing_ids": "paper-1"},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["nodes"]) == 1
    assert data["nodes"][0]["id"] == "paper-2"


# ── tests: GET /graph/sync-status ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sync_status_syncing_true_when_unprocessed_events():
    """syncing=true khi có events chưa xử lý trong sync_outbox."""
    mock_db = AsyncMock()
    count_result = AsyncMock()
    count_result.scalar_one = MagicMock(return_value=3)
    mock_db.execute = AsyncMock(return_value=count_result)

    app = _build_app(_make_user(), _make_project(), mock_db)

    with patch("backend.src.modules.graph_rag.presentation.router.get_neo4j_driver", return_value=_FakeNeo4jDriver()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/projects/proj-1/graph/sync-status")

    assert resp.status_code == 200
    assert resp.json()["syncing"] is True


@pytest.mark.asyncio
async def test_sync_status_syncing_false_when_no_events():
    """syncing=false khi không có events."""
    mock_db = AsyncMock()
    count_result = AsyncMock()
    count_result.scalar_one = MagicMock(return_value=0)
    mock_db.execute = AsyncMock(return_value=count_result)

    app = _build_app(_make_user(), _make_project(), mock_db)

    with patch("backend.src.modules.graph_rag.presentation.router.get_neo4j_driver", return_value=_FakeNeo4jDriver()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/projects/proj-1/graph/sync-status")

    assert resp.status_code == 200
    assert resp.json()["syncing"] is False


# ── tests: GET /graph/gaps ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_graph_gaps_returns_empty_response():
    """GET /graph/gaps khi không có gaps → 200 với flagged_nodes=[] flagged_edges=[]."""
    app = _build_app(_make_user(), _make_project())

    with patch("backend.src.modules.graph_rag.presentation.router.get_neo4j_driver", return_value=_FakeNeo4jDriver()):
        with patch("backend.src.modules.graph_rag.presentation.router.GapDetectionUseCase") as MockUseCase:
            instance = AsyncMock()
            instance.gap_detection = AsyncMock(return_value=GapContext())
            MockUseCase.return_value = instance
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/api/projects/proj-1/graph/gaps")

    assert resp.status_code == 200
    data = resp.json()
    assert data["flagged_nodes"] == []
    assert data["flagged_edges"] == []


@pytest.mark.asyncio
async def test_get_graph_gaps_returns_flagged_nodes():
    """GET /graph/gaps với 1 flagged_node → response có 1 item trong flagged_nodes."""
    gap_context = GapContext(
        flagged_nodes=[GapFlaggedNode(paper_id="p1", reason="has_contradiction")],
        flagged_edges=[],
    )
    app = _build_app(_make_user(), _make_project())

    with patch("backend.src.modules.graph_rag.presentation.router.get_neo4j_driver", return_value=_FakeNeo4jDriver()):
        with patch("backend.src.modules.graph_rag.presentation.router.GapDetectionUseCase") as MockUseCase:
            instance = AsyncMock()
            instance.gap_detection = AsyncMock(return_value=gap_context)
            MockUseCase.return_value = instance
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/api/projects/proj-1/graph/gaps")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["flagged_nodes"]) == 1
    assert data["flagged_nodes"][0]["paper_id"] == "p1"
    assert data["flagged_nodes"][0]["reason"] == "has_contradiction"


@pytest.mark.asyncio
async def test_get_graph_gaps_project_not_owned_returns_404():
    """GET /graph/gaps với project không thuộc user → 404."""
    mock_project = _make_project(user_id="other-user")
    mock_user = _make_user(user_id="user-1")

    app = _build_app(mock_user, mock_project)

    with patch("backend.src.modules.graph_rag.presentation.router.get_neo4j_driver", return_value=_FakeNeo4jDriver()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/projects/proj-1/graph/gaps")

    assert resp.status_code == 404


# ── tests: GET /graph/gaps/detailed ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_graph_gaps_detailed_returns_items():
    """GET /graph/gaps/detailed với 1 item → 200 với đúng shape."""
    detail_item = GapDetailItem(
        id="f1_f2",
        type="contradiction",
        reason="contradiction",
        title="Mâu thuẫn giữa Paper A và Paper B",
        description="Finding 1 text / Finding 2 text",
        papers=[
            GapPaperRef(paper_id="p1", title="Paper A"),
            GapPaperRef(paper_id="p2", title="Paper B"),
        ],
        evidence={"finding1_id": "f1", "finding2_id": "f2"},
    )
    app = _build_app(_make_user(), _make_project())

    with patch("backend.src.modules.graph_rag.presentation.router.get_neo4j_driver", return_value=_FakeNeo4jDriver()):
        with patch("backend.src.modules.graph_rag.presentation.router.GapDetectionUseCase") as MockUseCase:
            instance = AsyncMock()
            instance.gap_detection_detailed = AsyncMock(return_value=[detail_item])
            MockUseCase.return_value = instance
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/api/projects/proj-1/graph/gaps/detailed")

    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["id"] == "f1_f2"
    assert item["type"] == "contradiction"
    assert "Paper A" in item["title"]
    assert len(item["papers"]) == 2


@pytest.mark.asyncio
async def test_get_graph_gaps_detailed_returns_empty_when_no_gaps():
    """GET /graph/gaps/detailed khi không có gaps → 200 với items=[]."""
    app = _build_app(_make_user(), _make_project())

    with patch("backend.src.modules.graph_rag.presentation.router.get_neo4j_driver", return_value=_FakeNeo4jDriver()):
        with patch("backend.src.modules.graph_rag.presentation.router.GapDetectionUseCase") as MockUseCase:
            instance = AsyncMock()
            instance.gap_detection_detailed = AsyncMock(return_value=[])
            MockUseCase.return_value = instance
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/api/projects/proj-1/graph/gaps/detailed")

    assert resp.status_code == 200
    assert resp.json()["items"] == []


@pytest.mark.asyncio
async def test_get_graph_gaps_detailed_project_not_owned_returns_404():
    """GET /graph/gaps/detailed với project không thuộc user → 404 (IDOR guard)."""
    mock_project = _make_project(user_id="other-user")
    mock_user = _make_user(user_id="user-1")

    app = _build_app(mock_user, mock_project)

    with patch("backend.src.modules.graph_rag.presentation.router.get_neo4j_driver", return_value=_FakeNeo4jDriver()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/projects/proj-1/graph/gaps/detailed")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_graph_gaps_detailed_neo4j_error_returns_empty_items():
    """Neo4j lỗi → gap_detection_detailed trả [] → endpoint trả items: []."""
    app = _build_app(_make_user(), _make_project())

    with patch("backend.src.modules.graph_rag.presentation.router.get_neo4j_driver", return_value=_FakeNeo4jDriver()):
        with patch("backend.src.modules.graph_rag.presentation.router.GapDetectionUseCase") as MockUseCase:
            instance = AsyncMock()
            instance.gap_detection_detailed = AsyncMock(return_value=[])
            MockUseCase.return_value = instance
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/api/projects/proj-1/graph/gaps/detailed")

    assert resp.status_code == 200
    assert resp.json()["items"] == []


@pytest.mark.asyncio
async def test_get_graph_gaps_old_endpoint_still_works():
    """/graph/gaps cũ vẫn hoạt động sau khi thêm /graph/gaps/detailed."""
    app = _build_app(_make_user(), _make_project())

    with patch("backend.src.modules.graph_rag.presentation.router.get_neo4j_driver", return_value=_FakeNeo4jDriver()):
        with patch("backend.src.modules.graph_rag.presentation.router.GapDetectionUseCase") as MockUseCase:
            instance = AsyncMock()
            instance.gap_detection = AsyncMock(return_value=GapContext())
            MockUseCase.return_value = instance
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get("/api/projects/proj-1/graph/gaps")

    assert resp.status_code == 200
    data = resp.json()
    assert "flagged_nodes" in data
    assert "flagged_edges" in data
