"""Singleton async Neo4j driver cho toàn bộ backend/worker process.

Mirror pattern của redis_client.py: get_neo4j_driver() trả về driver singleton,
close_neo4j_driver() đóng kết nối khi shutdown.
"""
import logging

from neo4j import AsyncDriver, AsyncGraphDatabase

from backend.src.shared.infra.settings import get_settings

logger = logging.getLogger(__name__)

_neo4j_driver: AsyncDriver | None = None


async def get_neo4j_driver() -> AsyncDriver:
    global _neo4j_driver
    if _neo4j_driver is None:
        settings = get_settings()
        _neo4j_driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_username, settings.neo4j_password),
        )
    return _neo4j_driver


async def close_neo4j_driver() -> None:
    global _neo4j_driver
    if _neo4j_driver is not None:
        await _neo4j_driver.close()
        _neo4j_driver = None


# Unique Constraints base (Paper.id, Author.id, Project.id) — idempotent, chạy khi worker startup.
# KHÔNG tạo ontology constraints (Finding/Limitation/…) — đó là việc của Story 4.3.
_BASE_CONSTRAINTS_CQL = [
    "CREATE CONSTRAINT paper_id_unique IF NOT EXISTS FOR (p:Paper) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT author_id_unique IF NOT EXISTS FOR (a:Author) REQUIRE a.id IS UNIQUE",
    "CREATE CONSTRAINT project_id_unique IF NOT EXISTS FOR (proj:Project) REQUIRE proj.id IS UNIQUE",
]


async def create_base_constraints(driver: AsyncDriver) -> None:
    """Tạo Unique Constraints base idempotent. Gọi một lần khi worker on_startup."""
    async with driver.session() as session:
        for cql in _BASE_CONSTRAINTS_CQL:
            try:
                await session.run(cql)
            except Exception as e:
                logger.warning("Không thể tạo Neo4j constraint: %s — %s", cql, e)
    logger.info("Neo4j base constraints đã được đảm bảo.")
