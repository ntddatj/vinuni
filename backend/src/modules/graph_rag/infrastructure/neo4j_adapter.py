"""Neo4j adapter — Cypher handlers idempotent cho từng loại event.

Mỗi handler nhận payload dict và async session Neo4j, thực thi MERGE.
Đăng ký vào HANDLER_MAP để outbox_worker dispatch.

Scope: Story 4.1 — base handlers (PAPER_UPSERTED, PROJECT_DELETED, PAPER_DELETED, CITES).
Constraints ontology (Finding/Limitation/…) và handlers tương ứng → Story 4.3.
"""
import logging
import re

from neo4j import AsyncSession

logger = logging.getLogger(__name__)


def _normalize_author_name(name: str) -> str:
    """Chuẩn hóa tên tác giả: lower + trim + collapse whitespace (MVP entity resolution)."""
    return re.sub(r"\s+", " ", name.strip()).lower()


async def handle_paper_upserted(session: AsyncSession, payload: dict) -> None:
    """MERGE Paper node + Author nodes + [:AUTHORED_BY] edges idempotent."""
    paper_id = payload["paper_id"]
    project_id = payload["project_id"]
    title = payload.get("title", "")
    authors = payload.get("authors") or []
    year = payload.get("year")
    doi = payload.get("doi")
    arxiv_id = payload.get("arxiv_id")
    source = payload.get("source")
    url = payload.get("url")
    file_path = payload.get("file_path")
    state = "full_text" if file_path else "metadata_only"

    # MERGE Paper — idempotent upsert
    await session.run(
        """
        MERGE (p:Paper {id: $id})
        ON CREATE SET
            p.project_id   = $project_id,
            p.title        = $title,
            p.year         = $year,
            p.doi          = $doi,
            p.arxiv_id     = $arxiv_id,
            p.source       = $source,
            p.url          = $url,
            p.state        = $state,
            p.created_at   = datetime()
        ON MATCH SET
            p.title        = $title,
            p.year         = $year,
            p.doi          = $doi,
            p.arxiv_id     = $arxiv_id,
            p.source       = $source,
            p.url          = $url,
            p.state        = $state,
            p.updated_at   = datetime()
        """,
        id=paper_id,
        project_id=project_id,
        title=title,
        year=year,
        doi=doi,
        arxiv_id=arxiv_id,
        source=source,
        url=url,
        state=state,
    )

    # MERGE Author nodes + [:AUTHORED_BY] edges
    for raw_name in authors:
        if not raw_name or not raw_name.strip():
            continue
        norm = _normalize_author_name(raw_name)
        if not norm:
            # Tên sau chuẩn hóa rỗng (vd chỉ gồm ký tự bị strip) → bỏ qua, tránh tạo
            # node Author rác id="{project_id}:" gom nhầm mọi paper vào một tác giả ảo.
            continue
        author_id = f"{project_id}:{norm}"
        await session.run(
            """
            MERGE (a:Author {id: $author_id})
            ON CREATE SET a.name = $raw_name, a.project_id = $project_id, a.created_at = datetime()
            WITH a
            MATCH (p:Paper {id: $paper_id})
            MERGE (p)-[:AUTHORED_BY]->(a)
            """,
            author_id=author_id,
            raw_name=raw_name,
            project_id=project_id,
            paper_id=paper_id,
        )


async def handle_project_deleted(session: AsyncSession, payload: dict) -> None:
    """Đánh nhãn :Deleted cho Project và mọi Paper thuộc project_id."""
    project_id = payload["project_id"]
    await session.run(
        """
        MATCH (proj:Project {id: $project_id})
        SET proj:Deleted, proj.deleted_at = datetime()
        """,
        project_id=project_id,
    )
    await session.run(
        """
        MATCH (p:Paper {project_id: $project_id})
        WHERE NOT p:Deleted
        SET p:Deleted, p.deleted_at = datetime()
        """,
        project_id=project_id,
    )


async def handle_paper_deleted(session: AsyncSession, payload: dict) -> None:
    """Đánh nhãn :Deleted + deleted_at cho Paper {id}."""
    paper_id = payload["paper_id"]
    await session.run(
        """
        MATCH (p:Paper {id: $paper_id})
        SET p:Deleted, p.deleted_at = datetime()
        """,
        paper_id=paper_id,
    )


async def handle_cites(session: AsyncSession, payload: dict) -> None:
    """MERGE [:CITES] edge idempotent — handler sẵn sàng nhưng chưa có producer ở MVP.
    Bảng papers không lưu danh sách references → Story 4.1 không có producer sự kiện này.
    Handler viết sẵn để forward-compat: khi có dữ liệu references ở Story sau, chỉ cần thêm producer.
    """
    citing_id = payload.get("citing_paper_id")
    cited_id = payload.get("cited_paper_id")
    if not citing_id or not cited_id:
        logger.warning("CITES payload thiếu citing_paper_id hoặc cited_paper_id: %s", payload)
        return
    await session.run(
        """
        MATCH (a:Paper {id: $citing_id}), (b:Paper {id: $cited_id})
        MERGE (a)-[:CITES]->(b)
        """,
        citing_id=citing_id,
        cited_id=cited_id,
    )


async def handle_ontology_extracted(session: AsyncSession, payload: dict) -> None:
    """MERGE ontology nodes + edges cho ONTOLOGY_EXTRACTED event (Story 4.3).

    Bước 0: SET Paper.abstract + Paper.authors.
    Bước 1-3: MERGE Finding/Limitation/Method/Dataset/Topic/Problem + edges tới Paper.
    Bước 4: MERGE CONTRADICTS/SUPPORTS edges giữa Findings (scope project_id).
    """
    paper_id = payload.get("paper_id", "")
    project_id = payload.get("project_id", "")
    abstract = payload.get("abstract")
    authors = payload.get("authors")

    # Bước 0: Cập nhật Paper.abstract + Paper.authors
    if abstract is not None or authors is not None:
        await session.run(
            """
            MATCH (p:Paper {id: $paper_id})
            SET p.abstract = $abstract, p.authors = $authors, p.updated_at = datetime()
            """,
            paper_id=paper_id,
            abstract=abstract or "",
            authors=authors or [],
        )

    # Bước 1: Finding nodes + HAS_FINDING edges
    for finding in payload.get("findings") or []:
        if not finding.get("id"):
            continue
        await session.run(
            """
            MERGE (f:Finding {id: $id})
            ON CREATE SET f.description = $description, f.confidence_score = $score,
                          f.project_id = $project_id, f.created_at = datetime()
            ON MATCH SET f.description = $description, f.confidence_score = $score,
                         f.updated_at = datetime()
            WITH f
            MATCH (p:Paper {id: $paper_id})
            MERGE (p)-[:HAS_FINDING]->(f)
            """,
            id=finding["id"],
            description=finding.get("description", ""),
            score=finding.get("confidence_score", 0.0),
            project_id=project_id,
            paper_id=paper_id,
        )

    # Bước 2: Limitation nodes + HAS_LIMITATION edges
    for limitation in payload.get("limitations") or []:
        if not limitation.get("id"):
            continue
        await session.run(
            """
            MERGE (l:Limitation {id: $id})
            ON CREATE SET l.description = $description, l.project_id = $project_id,
                          l.created_at = datetime()
            ON MATCH SET l.description = $description, l.updated_at = datetime()
            WITH l
            MATCH (p:Paper {id: $paper_id})
            MERGE (p)-[:HAS_LIMITATION]->(l)
            """,
            id=limitation["id"],
            description=limitation.get("description", ""),
            project_id=project_id,
            paper_id=paper_id,
        )

    # Bước 3a: Method nodes + HAS_METHOD edges
    for method in payload.get("methods") or []:
        if not method.get("id"):
            continue
        await session.run(
            """
            MERGE (m:Method {id: $id})
            ON CREATE SET m.name = $name, m.description = $description,
                          m.project_id = $project_id, m.created_at = datetime()
            ON MATCH SET m.name = $name, m.description = $description, m.updated_at = datetime()
            WITH m
            MATCH (p:Paper {id: $paper_id})
            MERGE (p)-[:HAS_METHOD]->(m)
            """,
            id=method["id"],
            name=method.get("name", ""),
            description=method.get("description", ""),
            project_id=project_id,
            paper_id=paper_id,
        )

    # Bước 3b: Dataset nodes + USES_DATASET edges
    for dataset in payload.get("datasets") or []:
        if not dataset.get("id"):
            continue
        await session.run(
            """
            MERGE (d:Dataset {id: $id})
            ON CREATE SET d.name = $name, d.description = $description,
                          d.project_id = $project_id, d.created_at = datetime()
            ON MATCH SET d.name = $name, d.description = $description, d.updated_at = datetime()
            WITH d
            MATCH (p:Paper {id: $paper_id})
            MERGE (p)-[:USES_DATASET]->(d)
            """,
            id=dataset["id"],
            name=dataset.get("name", ""),
            description=dataset.get("description", ""),
            project_id=project_id,
            paper_id=paper_id,
        )

    # Bước 3c: Topic nodes + HAS_TOPIC edges
    for topic in payload.get("topics") or []:
        if not topic.get("id"):
            continue
        await session.run(
            """
            MERGE (t:Topic {id: $id})
            ON CREATE SET t.name = $name, t.project_id = $project_id, t.created_at = datetime()
            ON MATCH SET t.name = $name, t.updated_at = datetime()
            WITH t
            MATCH (p:Paper {id: $paper_id})
            MERGE (p)-[:HAS_TOPIC]->(t)
            """,
            id=topic["id"],
            name=topic.get("name", ""),
            project_id=project_id,
            paper_id=paper_id,
        )

    # Bước 3d: Problem nodes + ADDRESSES edges
    for problem in payload.get("problems") or []:
        if not problem.get("id"):
            continue
        await session.run(
            """
            MERGE (pr:Problem {id: $id})
            ON CREATE SET pr.description = $description, pr.project_id = $project_id,
                          pr.created_at = datetime()
            ON MATCH SET pr.description = $description, pr.updated_at = datetime()
            WITH pr
            MATCH (p:Paper {id: $paper_id})
            MERGE (p)-[:ADDRESSES]->(pr)
            """,
            id=problem["id"],
            description=problem.get("description", ""),
            project_id=project_id,
            paper_id=paper_id,
        )

    # Bước 4: CONTRADICTS edges giữa Findings (scope project_id)
    for edge in payload.get("contradicts") or []:
        if not edge.get("from_id") or not edge.get("to_id"):
            continue
        await session.run(
            """
            MATCH (f1:Finding {id: $from_id}), (f2:Finding {id: $to_id})
            WHERE f1.project_id = $project_id AND f2.project_id = $project_id
            MERGE (f1)-[:CONTRADICTS]->(f2)
            """,
            from_id=edge["from_id"],
            to_id=edge["to_id"],
            project_id=project_id,
        )

    # Bước 4b: SUPPORTS edges giữa Findings
    for edge in payload.get("supports") or []:
        if not edge.get("from_id") or not edge.get("to_id"):
            continue
        await session.run(
            """
            MATCH (f1:Finding {id: $from_id}), (f2:Finding {id: $to_id})
            WHERE f1.project_id = $project_id AND f2.project_id = $project_id
            MERGE (f1)-[:SUPPORTS]->(f2)
            """,
            from_id=edge["from_id"],
            to_id=edge["to_id"],
            project_id=project_id,
        )


# Dispatch map: event_type → handler. Mở rộng được: Story 4.3 chỉ cần thêm entry vào đây
# (không sửa worker core). Key = event_type string, value = async callable(session, payload).
HANDLER_MAP: dict = {
    "PAPER_UPSERTED": handle_paper_upserted,
    "PROJECT_DELETED": handle_project_deleted,
    "PAPER_DELETED": handle_paper_deleted,
    "CITES": handle_cites,
    "ONTOLOGY_EXTRACTED": handle_ontology_extracted,
}
