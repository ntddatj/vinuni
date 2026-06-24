"""Application layer graph_rag — re-export entry points cho worker + read use cases."""
import logging

from backend.src.modules.graph_rag.domain.entities import (
    GapContext,
    GapDetailItem,
    GapFlaggedEdge,
    GapFlaggedNode,
    GapPaperRef,
    GraphContext,
    GraphData,
    GraphEdge,
    GraphNode,
)
from backend.src.modules.graph_rag.infrastructure.outbox_worker import sync_outbox_task

__all__ = ["sync_outbox_task", "GraphReadUseCase", "GapDetectionUseCase"]

_logger = logging.getLogger(__name__)

_NODE_LIMIT = 250
_EDGE_LIMIT = 400
_EXPAND_LIMIT = 20

# Neo4j label → nhãn hiển thị UI. Paper/Author xử lý riêng (lấy title/name);
# entity ontology lấy name (Method/Dataset/Topic) hoặc description (Finding/Limitation/Problem).
_ENTITY_LABEL_MAP = {
    "Finding": "finding",
    "Limitation": "limitation",
    "Method": "method",
    "Dataset": "dataset",
    "Topic": "topic",
    "Problem": "problem",
}


def _classify_node(n) -> tuple[str, str]:
    """Map 1 Neo4j Node → (label hiển thị, title). Dùng chung cho get_graph + expand_node."""
    labels = list(n.labels)
    if "Author" in labels:
        return "author", n.get("name", "")
    if "Paper" in labels:
        return "paper", n.get("title", "")
    for neo_label, ui_label in _ENTITY_LABEL_MAP.items():
        if neo_label in labels:
            return ui_label, (n.get("name") or n.get("description") or "")
    return "paper", n.get("title", "")


class GraphReadUseCase:
    """Đọc đồ thị từ Neo4j và trả về GraphData domain object."""

    def __init__(self, neo4j_driver) -> None:
        self._driver = neo4j_driver

    async def get_graph(self, project_id: str) -> GraphData:
        async with self._driver.session() as session:
            # Count total nodes để xác định has_more
            count_result = await session.run(
                "MATCH (n) WHERE n.project_id = $pid AND NOT n:Deleted RETURN count(n) AS total",
                pid=project_id,
            )
            count_record = await count_result.single()
            total_nodes = count_record["total"] if count_record else 0
            has_more = total_nodes > _NODE_LIMIT

            # Lấy nodes
            # ORDER BY ưu tiên Paper > Author > entity: khi tổng node > _NODE_LIMIT, các node
            # cấu trúc (paper/tác giả/cạnh CITES) LUÔN lọt vào khung hiển thị, entity ontology
            # lấp phần còn lại — tránh tình trạng paper bị "trống" do entity chiếm hết budget.
            node_result = await session.run(
                """
                MATCH (n)
                WHERE n.project_id = $pid AND NOT n:Deleted
                RETURN n
                ORDER BY CASE
                    WHEN n:Paper THEN 0
                    WHEN n:Author THEN 1
                    ELSE 2
                END
                LIMIT $limit
                """,
                pid=project_id,
                limit=_NODE_LIMIT,
            )
            # KHÔNG dùng result.data(): nó ép Node → dict thuộc tính trần (mất .labels).
            # Lặp record để giữ nguyên Node object (có .labels, .get, ["id"]).
            node_records = [rec async for rec in node_result]

            nodes: list[GraphNode] = []
            node_ids: set[str] = set()
            for rec in node_records:
                n = rec["n"]
                label, title = _classify_node(n)
                node = GraphNode(
                    id=n["id"],
                    label=label,
                    title=title,
                    authors=n.get("authors") or [],
                    year=n.get("year"),
                    abstract=n.get("abstract"),
                    state=n.get("state"),
                    project_id=n.get("project_id"),
                )
                nodes.append(node)
                node_ids.add(n["id"])

            # Lấy edges CHỈ giữa các nodes đã trả về (node_ids) để tránh edge "treo"
            # tham chiếu node ngoài cửa sổ 150 → Cytoscape cy.add() sẽ throw.
            edge_records = []
            if node_ids:
                edge_result = await session.run(
                    """
                    MATCH (a)-[r]->(b)
                    WHERE a.id IN $node_ids AND b.id IN $node_ids
                    RETURN r, a.id AS source_id, b.id AS target_id,
                           elementId(r) AS rel_id, type(r) AS rel_type
                    LIMIT $limit
                    """,
                    node_ids=list(node_ids),
                    limit=_EDGE_LIMIT,
                )
                edge_records = await edge_result.data()

            edges: list[GraphEdge] = []
            for rec in edge_records:
                edges.append(GraphEdge(
                    id=rec["rel_id"],
                    source=rec["source_id"],
                    target=rec["target_id"],
                    type=rec["rel_type"],
                ))

        return GraphData(nodes=nodes, edges=edges, has_more=has_more)

    async def expand_node(self, project_id: str, node_id: str, existing_ids: list[str]) -> GraphData:
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (seed {id: $node_id})-[r]-(neighbor)
                WHERE seed.project_id = $pid
                  AND NOT seed:Deleted
                  AND neighbor.project_id = $pid
                  AND NOT neighbor:Deleted
                  AND NOT neighbor.id IN $existing_ids
                RETURN neighbor, r, seed.id AS seed_id,
                       elementId(r) AS rel_id, type(r) AS rel_type,
                       neighbor.id = startNode(r).id AS neighbor_is_source
                LIMIT $limit
                """,
                node_id=node_id,
                pid=project_id,
                existing_ids=existing_ids,
                limit=_EXPAND_LIMIT,
            )
            # Giữ Node object (xem ghi chú ở get_graph) — không dùng result.data().
            records = [rec async for rec in result]

        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        for rec in records:
            n = rec["neighbor"]
            label, title = _classify_node(n)
            nodes.append(GraphNode(
                id=n["id"],
                label=label,
                title=title,
                authors=n.get("authors") or [],
                year=n.get("year"),
                abstract=n.get("abstract"),
                state=n.get("state"),
                project_id=n.get("project_id"),
            ))
            # Xác định hướng edge
            if rec["neighbor_is_source"]:
                source_id = n["id"]
                target_id = rec["seed_id"]
            else:
                source_id = rec["seed_id"]
                target_id = n["id"]
            edges.append(GraphEdge(
                id=rec["rel_id"],
                source=source_id,
                target=target_id,
                type=rec["rel_type"],
            ))

        return GraphData(nodes=nodes, edges=edges, has_more=False)


_PRIORITY: dict[str, int] = {
    "has_contradiction": 3,
    "has_unfilled_limitation": 2,
    "isolated_cluster": 1,
}

_CYPHER_CONTRADICTS = """
MATCH (f1:Finding {project_id: $pid})-[:CONTRADICTS]->(f2:Finding {project_id: $pid})
MATCH (p1:Paper {project_id: $pid})-[:HAS_FINDING]->(f1)
MATCH (p2:Paper {project_id: $pid})-[:HAS_FINDING]->(f2)
WHERE NOT p1:Deleted AND NOT p2:Deleted
RETURN DISTINCT f1.id AS finding1_id, f2.id AS finding2_id,
       p1.id AS paper1_id, p2.id AS paper2_id
"""

_CYPHER_ISOLATED = """
MATCH (p:Paper {project_id: $pid}) WHERE NOT p:Deleted
OPTIONAL MATCH (p)-[:CITES]-(other:Paper {project_id: $pid})
WHERE NOT other:Deleted
WITH p, count(other) AS cites_count
WHERE cites_count = 0
RETURN p.id AS paper_id
"""

_CYPHER_UNFILLED_LIMITATION = """
MATCH (p:Paper {project_id: $pid})-[:HAS_LIMITATION]->(l:Limitation {project_id: $pid})
WHERE NOT p:Deleted
  AND NOT EXISTS {
    MATCH (filler:Paper {project_id: $pid})-[:FILLS_GAP]->(l) WHERE NOT filler:Deleted
  }
RETURN DISTINCT p.id AS paper_id
"""

_CYPHER_UNFILLED_LIMITATION_FULL = """
MATCH (p:Paper {project_id: $pid})-[:HAS_LIMITATION]->(l:Limitation {project_id: $pid})
WHERE NOT p:Deleted
  AND NOT EXISTS {
    MATCH (filler:Paper {project_id: $pid})-[:FILLS_GAP]->(l) WHERE NOT filler:Deleted
  }
RETURN DISTINCT l.id AS limitation_id, l.description AS description, p.id AS owner_paper_id
"""

_CYPHER_CONTRADICTS_DETAILED = """
MATCH (f1:Finding {project_id: $pid})-[:CONTRADICTS]->(f2:Finding {project_id: $pid})
MATCH (p1:Paper {project_id: $pid})-[:HAS_FINDING]->(f1)
MATCH (p2:Paper {project_id: $pid})-[:HAS_FINDING]->(f2)
WHERE NOT p1:Deleted AND NOT p2:Deleted
RETURN DISTINCT f1.id AS finding1_id, f2.id AS finding2_id,
       p1.id AS paper1_id, p2.id AS paper2_id,
       f1.description AS finding1_text, f2.description AS finding2_text,
       p1.title AS paper1_title, p2.title AS paper2_title
"""

_CYPHER_ISOLATED_DETAILED = """
MATCH (p:Paper {project_id: $pid}) WHERE NOT p:Deleted
OPTIONAL MATCH (p)-[:CITES]-(other:Paper {project_id: $pid})
WHERE NOT other:Deleted
WITH p, count(other) AS cites_count
WHERE cites_count = 0
RETURN p.id AS paper_id, p.title AS paper_title
"""

_CYPHER_UNFILLED_LIMITATION_DETAILED = """
MATCH (p:Paper {project_id: $pid})-[:HAS_LIMITATION]->(l:Limitation {project_id: $pid})
WHERE NOT p:Deleted
  AND NOT EXISTS {
    MATCH (filler:Paper {project_id: $pid})-[:FILLS_GAP]->(l) WHERE NOT filler:Deleted
  }
RETURN DISTINCT l.id AS limitation_id, l.description AS description,
       p.id AS owner_paper_id, p.title AS owner_paper_title
"""

_CYPHER_GRAPH_SEARCH = """
MATCH (start {project_id: $pid})-[r]-(neighbor {project_id: $pid})
WHERE (start.title IN $entities OR start.name IN $entities)
  AND NOT start:Deleted AND NOT neighbor:Deleted
RETURN DISTINCT start, neighbor, r,
       start.id AS start_id, neighbor.id AS neighbor_id,
       elementId(r) AS rel_id, type(r) AS rel_type,
       start.id = startNode(r).id AS start_is_source
LIMIT 50
"""


class GapDetectionUseCase:
    """Gap detection và graph search cho GraphRAG — dùng Cypher traversal thuần."""

    def __init__(self, neo4j_driver) -> None:
        self._driver = neo4j_driver

    async def gap_detection(self, project_id: str) -> GapContext:
        seen: dict[str, str] = {}  # paper_id → reason với priority
        flagged_edges: list[GapFlaggedEdge] = []

        def _add_node(paper_id: str, reason: str) -> None:
            current = seen.get(paper_id)
            if current is None or _PRIORITY[reason] > _PRIORITY[current]:
                seen[paper_id] = reason

        # AC#4: gap_detection KHÔNG bao giờ raise — bọc cả việc mở session (Neo4j
        # down / driver lỗi) lẫn từng query để luôn trả GapContext (rỗng khi sự cố).
        try:
            async with self._driver.session() as session:
                # Query 1: CONTRADICTS
                try:
                    result = await session.run(_CYPHER_CONTRADICTS, pid=project_id)
                    records = [rec async for rec in result]
                    for rec in records:
                        flagged_edges.append(GapFlaggedEdge(
                            finding1_id=rec["finding1_id"],
                            finding2_id=rec["finding2_id"],
                            paper1_id=rec["paper1_id"],
                            paper2_id=rec["paper2_id"],
                            reason="contradicts",
                        ))
                        _add_node(rec["paper1_id"], "has_contradiction")
                        _add_node(rec["paper2_id"], "has_contradiction")
                except Exception:
                    _logger.warning("gap_detection: query 1 (CONTRADICTS) failed", exc_info=True)

                # Query 2: Isolated Cluster
                try:
                    result = await session.run(_CYPHER_ISOLATED, pid=project_id)
                    records = [rec async for rec in result]
                    for rec in records:
                        _add_node(rec["paper_id"], "isolated_cluster")
                except Exception:
                    _logger.warning("gap_detection: query 2 (ISOLATED) failed", exc_info=True)

                # Query 3: Unfilled Limitations
                try:
                    result = await session.run(_CYPHER_UNFILLED_LIMITATION, pid=project_id)
                    records = [rec async for rec in result]
                    for rec in records:
                        _add_node(rec["paper_id"], "has_unfilled_limitation")
                except Exception:
                    _logger.warning("gap_detection: query 3 (UNFILLED_LIMITATION) failed", exc_info=True)
        except Exception:
            _logger.warning("gap_detection: session acquisition failed", exc_info=True)
            return GapContext()

        flagged_nodes = [GapFlaggedNode(paper_id=pid, reason=r) for pid, r in seen.items()]
        return GapContext(flagged_nodes=flagged_nodes, flagged_edges=flagged_edges)

    async def gap_detection_detailed(self, project_id: str) -> list[GapDetailItem]:
        """Trả danh sách card giàu cho 3 loại gap — không gọi LLM, text từ entity thật.

        Pattern không-raise: bọc toàn bộ (mở session + từng query) → trả [] khi sự cố.
        """
        items: list[GapDetailItem] = []

        try:
            async with self._driver.session() as session:
                # Query 1: CONTRADICTS DETAILED
                try:
                    result = await session.run(_CYPHER_CONTRADICTS_DETAILED, pid=project_id)
                    records = [rec async for rec in result]
                    # CONTRADICTS là cạnh có hướng — extractor có thể tạo cả f1→f2 lẫn f2→f1
                    # cho cùng một mâu thuẫn. Khử trùng theo cặp finding không phân biệt thứ tự
                    # để không hiện 2 card trùng (id f1_f2 và f2_f1 vốn khác nhau).
                    seen_pairs: set[frozenset[str]] = set()
                    for rec in records:
                        pair = frozenset((rec["finding1_id"], rec["finding2_id"]))
                        if pair in seen_pairs:
                            continue
                        seen_pairs.add(pair)
                        f1_text = rec.get("finding1_text") or ""
                        f2_text = rec.get("finding2_text") or ""
                        p1_title = rec.get("paper1_title") or rec["paper1_id"]
                        p2_title = rec.get("paper2_title") or rec["paper2_id"]
                        item_id = f"{rec['finding1_id']}_{rec['finding2_id']}"
                        # Tiêu đề ngắn gọn theo LOẠI khoảng trống (tên bài báo hiển thị ở
                        # dòng "Nghiên cứu liên quan", không nhồi vào tiêu đề). Phân biệt
                        # mâu thuẫn nội tại (cùng 1 bài) vs giữa hai bài khác nhau.
                        same_paper = rec["paper1_id"] == rec["paper2_id"]
                        title = (
                            "Hai kết luận trái ngược trong cùng một nghiên cứu"
                            if same_paper
                            else "Hai nghiên cứu đưa ra kết luận trái ngược nhau"
                        )
                        parts = [p for p in [f1_text, f2_text] if p]
                        description = (
                            " ⟷ ".join(parts) if parts
                            else "Hai phát hiện trong dữ liệu đưa ra kết luận trái ngược nhau."
                        )
                        items.append(GapDetailItem(
                            id=item_id,
                            type="contradiction",
                            reason="contradiction",
                            title=title,
                            description=description,
                            papers=[
                                GapPaperRef(paper_id=rec["paper1_id"], title=p1_title),
                                GapPaperRef(paper_id=rec["paper2_id"], title=p2_title),
                            ],
                            # Số liệu cho dòng "bằng chứng" — KHÔNG lộ id nội bộ ra UI.
                            evidence={"finding_count": 2, "paper_count": 1 if same_paper else 2},
                        ))
                except Exception:
                    _logger.warning("gap_detection_detailed: query CONTRADICTS failed", exc_info=True)

                # Query 2: ISOLATED DETAILED
                try:
                    result = await session.run(_CYPHER_ISOLATED_DETAILED, pid=project_id)
                    records = [rec async for rec in result]
                    for rec in records:
                        paper_title = rec.get("paper_title") or rec["paper_id"]
                        items.append(GapDetailItem(
                            id=rec["paper_id"],
                            type="isolated_cluster",
                            reason="isolated_cluster",
                            title="Nghiên cứu chưa có liên kết trích dẫn",
                            description="Bài báo này không có cạnh trích dẫn (CITES) với bất kỳ nghiên cứu nào khác trong dự án, cho thấy nó đang đứng tách biệt.",
                            papers=[GapPaperRef(paper_id=rec["paper_id"], title=paper_title)],
                            evidence={"neighbor_count": 0},
                        ))
                except Exception:
                    _logger.warning("gap_detection_detailed: query ISOLATED failed", exc_info=True)

                # Query 3: UNFILLED LIMITATION DETAILED
                try:
                    result = await session.run(_CYPHER_UNFILLED_LIMITATION_DETAILED, pid=project_id)
                    records = [rec async for rec in result]
                    for rec in records:
                        paper_title = rec.get("owner_paper_title") or rec["owner_paper_id"]
                        description = rec.get("description") or ""
                        if not description:
                            continue
                        items.append(GapDetailItem(
                            id=rec["limitation_id"],
                            type="unfilled_limitation",
                            reason="unfilled_limitation",
                            title="Hạn chế nghiên cứu chưa được giải quyết",
                            description=description,
                            papers=[GapPaperRef(paper_id=rec["owner_paper_id"], title=paper_title)],
                            # 0 bài báo nào lấp khoảng trống này (không [:FILLS_GAP]).
                            evidence={"filler_count": 0},
                        ))
                except Exception:
                    _logger.warning("gap_detection_detailed: query UNFILLED_LIMITATION failed", exc_info=True)

        except Exception:
            _logger.warning("gap_detection_detailed: session acquisition failed", exc_info=True)
            return []

        return items

    async def graph_search(self, entities: list[str], project_id: str) -> GraphContext:
        async with self._driver.session() as session:
            try:
                result = await session.run(
                    _CYPHER_GRAPH_SEARCH,
                    pid=project_id,
                    entities=entities,
                )
                records = [rec async for rec in result]
            except Exception:
                _logger.warning("graph_search: query failed", exc_info=True)
                return GraphContext()

        nodes_map: dict[str, GraphNode] = {}
        edges: list[GraphEdge] = []

        for rec in records:
            for node_key in ("start", "neighbor"):
                n = rec[node_key]
                nid = n["id"]
                if nid not in nodes_map:
                    labels = list(n.labels)
                    if "Author" in labels:
                        label = "author"
                        title = n.get("name", "")
                    else:
                        label = "paper"
                        title = n.get("title", "")
                    nodes_map[nid] = GraphNode(
                        id=nid,
                        label=label,
                        title=title,
                        authors=n.get("authors") or [],
                        year=n.get("year"),
                        abstract=n.get("abstract"),
                        state=n.get("state"),
                        project_id=n.get("project_id"),
                    )

            neighbor_id = rec["neighbor_id"]
            start_id = rec["start_id"]
            if rec["start_is_source"]:
                source_id = start_id
                target_id = neighbor_id
            else:
                source_id = neighbor_id
                target_id = start_id
            edges.append(GraphEdge(
                id=rec["rel_id"],
                source=source_id,
                target=target_id,
                type=rec["rel_type"],
            ))

        return GraphContext(nodes=list(nodes_map.values()), edges=edges)


async def list_unfilled_limitations(session, project_id: str) -> list[dict]:
    """Đọc Neo4j trả về Limitation chưa được lấp (chưa có [:FILLS_GAP]) trong project.

    Dùng bởi fills_gap_task (ingestion producer) — graph_rag sở hữu mọi đọc Neo4j.
    Trả [{"limitation_id", "description", "owner_paper_id"}]. Lỗi Neo4j → trả [].
    """
    try:
        result = await session.run(_CYPHER_UNFILLED_LIMITATION_FULL, pid=project_id)
        records = [rec async for rec in result]
        return [
            {
                "limitation_id": rec["limitation_id"],
                "description": rec["description"],
                "owner_paper_id": rec["owner_paper_id"],
            }
            for rec in records
            if rec["description"]  # bỏ qua description rỗng/None
        ]
    except Exception:
        _logger.warning(
            "list_unfilled_limitations: Neo4j query failed cho project %s", project_id, exc_info=True
        )
        return []
