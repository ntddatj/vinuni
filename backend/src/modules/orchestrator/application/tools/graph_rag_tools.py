"""Thin wrappers gọi graph_rag use cases qua Port (§9.6).

Orchestrator KHÔNG truy cập Neo4j/Cypher trực tiếp — chỉ gọi qua
GapDetectionUseCase (application layer của graph_rag).
"""
import logging

from backend.src.modules.graph_rag.application.use_cases import GapDetectionUseCase
from backend.src.modules.graph_rag.domain.entities import GapContext, GraphContext  # noqa: F401
from backend.src.shared.infra.neo4j_client import get_neo4j_driver

_logger = logging.getLogger(__name__)


async def gap_detection_tool(project_id: str) -> GapContext:
    """Phát hiện khoảng trống/mâu thuẫn trong đồ thị tri thức.

    NEVER raises — GapDetectionUseCase.gap_detection() đã bọc toàn bộ exception.
    """
    driver = await get_neo4j_driver()
    return await GapDetectionUseCase(driver).gap_detection(project_id)


async def graph_search_tool(entities: list[str], project_id: str) -> GraphContext:
    """Tìm kiếm quan hệ đồ thị cho các thực thể đã cho.

    Bọc try/except vì graph_search có thể raise khi session-acquire thất bại.
    Guard nợ kỹ thuật 4.4: node thiếu id hoặc label không phải paper/author
    được lọc khi caller dùng kết quả (xem gap_analyst_node).
    """
    driver = await get_neo4j_driver()
    try:
        return await GapDetectionUseCase(driver).graph_search(entities, project_id)
    except Exception:
        _logger.warning("graph_search_tool: failed, returning empty GraphContext", exc_info=True)
        return GraphContext()
