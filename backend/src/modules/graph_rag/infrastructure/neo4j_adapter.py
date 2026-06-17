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


# Dispatch map: event_type → handler. Mở rộng được: Story 4.3 chỉ cần thêm entry vào đây
# (không sửa worker core). Key = event_type string, value = async callable(session, payload).
HANDLER_MAP: dict = {
    "PAPER_UPSERTED": handle_paper_upserted,
    "PROJECT_DELETED": handle_project_deleted,
    "PAPER_DELETED": handle_paper_deleted,
    "CITES": handle_cites,
}
