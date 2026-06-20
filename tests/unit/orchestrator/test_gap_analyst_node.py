"""Unit tests cho gap_analyst_node (AC#3, AC#4, AC#7)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage

from backend.src.modules.graph_rag.domain.entities import (
    GapContext,
    GapFlaggedNode,
    GapFlaggedEdge,
    GraphContext,
)
from backend.src.modules.orchestrator.application.graph import gap_analyst_node, EMPTY_GAP_MSG


def _make_config(user_id="user-1", project_id="proj-1"):
    return {"configurable": {"user_id": user_id, "project_id": project_id}}


def _make_state(message="Phân tích khoảng trống"):
    return {"messages": [HumanMessage(content=message)]}


# ── AC#4: Empty GapContext → trả EMPTY_GAP_MSG, KHÔNG gọi LLM ──────────────

@pytest.mark.asyncio
async def test_gap_analyst_empty_context_no_llm():
    """AC#4: GapContext rỗng → trả câu cố định, không gọi LLM."""
    empty_gap = GapContext(flagged_nodes=[], flagged_edges=[])

    with patch(
        "backend.src.modules.orchestrator.application.graph.gap_detection_tool",
        new=AsyncMock(return_value=empty_gap),
    ), patch(
        "backend.src.modules.orchestrator.application.tools.graph_rag_tools.get_neo4j_driver",
    ):
        result = await gap_analyst_node(_make_state(), _make_config())

    assert result["messages"][0].content == EMPTY_GAP_MSG
    assert result["valid_citation_ids"] == []
    assert result["citation_map"] == {}


# ── AC#3: GapContext có data → build citation_map, gọi LLM ──────────────────

@pytest.mark.asyncio
async def test_gap_analyst_builds_citation_map_and_calls_llm():
    """AC#3: GapContext có flagged_nodes → lookup chunk → gọi LLM → trả [N]."""
    gap_ctx = GapContext(
        flagged_nodes=[GapFlaggedNode(paper_id="paper-uuid-1", reason="has_contradiction")],
        flagged_edges=[],
    )

    # Mock session DB: trả 1 chunk UUID cho paper-uuid-1
    mock_chunk_id = "chunk-uuid-abc"
    mock_row = MagicMock()
    mock_row.__str__ = lambda self: mock_chunk_id
    mock_scalar = MagicMock(return_value=mock_chunk_id)

    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one_or_none = mock_scalar

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_execute_result)
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)

    # Mock LLM
    mock_llm = MagicMock()
    async def _fake_astream(msgs):
        msg = MagicMock()
        msg.content = "Phân tích: mâu thuẫn giữa [1] và kết quả khác."
        yield msg
    mock_llm.astream = _fake_astream

    mock_llm_router = MagicMock()
    mock_llm_router.get_llm_client = AsyncMock(return_value=mock_llm)

    with patch(
        "backend.src.modules.orchestrator.application.graph.gap_detection_tool",
        new=AsyncMock(return_value=gap_ctx),
    ), patch(
        "backend.src.modules.orchestrator.application.graph.graph_search_tool",
        new=AsyncMock(return_value=GraphContext()),
    ), patch(
        "backend.src.modules.orchestrator.application.graph.AsyncSessionMaker",
        return_value=mock_db,
    ), patch(
        "backend.src.modules.orchestrator.application.graph.LLMRouter",
        return_value=mock_llm_router,
    ):
        result = await gap_analyst_node(_make_state(), _make_config())

    assert result["valid_citation_ids"] == [1]
    assert result["citation_map"][1] == mock_chunk_id
    content = result["messages"][0].content
    assert isinstance(content, str)
    assert len(content) > 0


# ── AC#4: chunk lookup trả None → trả EMPTY_GAP_MSG ────────────────────────

@pytest.mark.asyncio
async def test_gap_analyst_no_chunk_found_returns_safe_msg():
    """Nếu không lookup được chunk nào → trả EMPTY_GAP_MSG."""
    gap_ctx = GapContext(
        flagged_nodes=[GapFlaggedNode(paper_id="paper-no-chunk", reason="isolated_cluster")],
        flagged_edges=[],
    )

    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one_or_none = MagicMock(return_value=None)

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_execute_result)
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)

    mock_llm_router = MagicMock()
    mock_llm_router.get_llm_client = AsyncMock()

    with patch(
        "backend.src.modules.orchestrator.application.graph.gap_detection_tool",
        new=AsyncMock(return_value=gap_ctx),
    ), patch(
        "backend.src.modules.orchestrator.application.graph.AsyncSessionMaker",
        return_value=mock_db,
    ), patch(
        "backend.src.modules.orchestrator.application.graph.LLMRouter",
        return_value=mock_llm_router,
    ):
        result = await gap_analyst_node(_make_state(), _make_config())

    assert result["messages"][0].content == EMPTY_GAP_MSG
    # LLM không được gọi khi không có chunk
    mock_llm_router.get_llm_client.assert_not_called()


# ── Regression: ordinal liền mạch từ 1 khi paper đầu thiếu chunk ────────────

@pytest.mark.asyncio
async def test_gap_analyst_ordinals_contiguous_when_first_paper_missing_chunk():
    """Paper đầu không có chunk, paper sau có → citation_map phải bắt đầu từ [1]
    (không để lỗ hổng ordinal [2] thiếu [1])."""
    gap_ctx = GapContext(
        flagged_nodes=[
            GapFlaggedNode(paper_id="paper-no-chunk", reason="isolated_cluster"),
            GapFlaggedNode(paper_id="paper-has-chunk", reason="has_contradiction"),
        ],
        flagged_edges=[],
    )

    mock_execute_result = MagicMock()
    # Lookup 1 → None (paper-no-chunk), lookup 2 → chunk uuid (paper-has-chunk)
    mock_execute_result.scalar_one_or_none = MagicMock(side_effect=[None, "chunk-uuid-2"])

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_execute_result)
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)

    mock_llm = MagicMock()
    async def _fake_astream(msgs):
        msg = MagicMock()
        msg.content = "Phân tích [1]."
        yield msg
    mock_llm.astream = _fake_astream
    mock_llm_router = MagicMock()
    mock_llm_router.get_llm_client = AsyncMock(return_value=mock_llm)

    with patch(
        "backend.src.modules.orchestrator.application.graph.gap_detection_tool",
        new=AsyncMock(return_value=gap_ctx),
    ), patch(
        "backend.src.modules.orchestrator.application.graph.graph_search_tool",
        new=AsyncMock(return_value=GraphContext()),
    ), patch(
        "backend.src.modules.orchestrator.application.graph.AsyncSessionMaker",
        return_value=mock_db,
    ), patch(
        "backend.src.modules.orchestrator.application.graph.LLMRouter",
        return_value=mock_llm_router,
    ):
        result = await gap_analyst_node(_make_state(), _make_config())

    # Ordinal liền mạch: chỉ [1], trỏ tới chunk của paper-has-chunk
    assert result["valid_citation_ids"] == [1]
    assert result["citation_map"] == {1: "chunk-uuid-2"}
