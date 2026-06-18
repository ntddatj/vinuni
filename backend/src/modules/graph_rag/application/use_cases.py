"""Application layer graph_rag — re-export entry points cho worker + read use cases."""
from backend.src.modules.graph_rag.domain.entities import GraphData, GraphEdge, GraphNode
from backend.src.modules.graph_rag.infrastructure.outbox_worker import sync_outbox_task

__all__ = ["sync_outbox_task", "GraphReadUseCase"]

_NODE_LIMIT = 150
_EDGE_LIMIT = 300
_EXPAND_LIMIT = 20


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
            node_result = await session.run(
                """
                MATCH (n)
                WHERE n.project_id = $pid AND NOT n:Deleted
                RETURN n LIMIT $limit
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
                labels = list(n.labels)
                if "Author" in labels:
                    label = "author"
                    title = n.get("name", "")
                else:
                    label = "paper"
                    title = n.get("title", "")
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
            labels = list(n.labels)
            if "Author" in labels:
                label = "author"
                title = n.get("name", "")
            else:
                label = "paper"
                title = n.get("title", "")
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
