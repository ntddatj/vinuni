"""Unit tests cho real_rag_node — AC#1, #2, #3, #6, #9."""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from langchain_core.messages import HumanMessage

from backend.src.modules.orchestrator.application.graph import (
    ChatState,
    EMPTY_RETRIEVAL_MSG,
    real_rag_node,
)


def _make_config(user_id: str = "u1", project_id: str = "p1") -> dict:
    return {"configurable": {"thread_id": "t1", "user_id": user_id, "project_id": project_id}}


def _make_state(query: str = "Câu hỏi về nghiên cứu") -> ChatState:
    return ChatState(
        messages=[HumanMessage(content=query)],
        valid_citation_ids=[],
        citation_map={},
    )


# ---------------------------------------------------------------------------
# AC#3 — Empty retrieval không gọi LLM
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_real_rag_node_empty_retrieval_no_llm():
    """Khi pgvector trả [] → trả EMPTY_RETRIEVAL_MSG, không gọi LLM."""
    state = _make_state()
    config = _make_config()

    mock_result = MagicMock()
    mock_result.fetchall.return_value = []

    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=None)
    mock_db.execute = AsyncMock(return_value=mock_result)

    mock_embed_client = AsyncMock()
    mock_embed_client.embed_batch = AsyncMock(return_value=[[0.0] * 768])

    with patch("backend.src.modules.orchestrator.application.graph.AsyncSessionMaker", return_value=mock_db), \
         patch("backend.src.modules.orchestrator.application.graph.GeminiEmbeddingClient", return_value=mock_embed_client), \
         patch("backend.src.modules.orchestrator.application.graph.LLMRouter") as mock_router_cls:

        result = await real_rag_node(state, config)

    # LLM không được khởi tạo hay gọi
    mock_router_cls.assert_not_called()

    assert result["messages"][0].content == EMPTY_RETRIEVAL_MSG
    assert result["citation_map"] == {}
    assert result["valid_citation_ids"] == []


# ---------------------------------------------------------------------------
# AC#2, #9 — Build citation_map đúng ordinal và scope project_id
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_real_rag_node_builds_citation_map():
    """Khi pgvector trả 3 chunks → citation_map = {1: uuid1, 2: uuid2, 3: uuid3}."""
    uuid1, uuid2, uuid3 = str(uuid4()), str(uuid4()), str(uuid4())

    row1 = MagicMock()
    row1.id = uuid1
    row1.content = "Nội dung chunk 1"

    row2 = MagicMock()
    row2.id = uuid2
    row2.content = "Nội dung chunk 2"

    row3 = MagicMock()
    row3.id = uuid3
    row3.content = "Nội dung chunk 3"

    mock_result = MagicMock()
    mock_result.fetchall.return_value = [row1, row2, row3]

    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=None)
    mock_db.execute = AsyncMock(return_value=mock_result)

    mock_embed_client = AsyncMock()
    mock_embed_client.embed_batch = AsyncMock(return_value=[[0.1] * 768])

    mock_llm = AsyncMock()

    async def fake_astream(messages):
        chunk = MagicMock()
        chunk.content = "Câu trả lời từ LLM với [1] và [2]"
        yield chunk

    mock_llm.astream = fake_astream

    mock_llm_router = AsyncMock()
    mock_llm_router.get_llm_client = AsyncMock(return_value=mock_llm)

    state = _make_state()
    config = _make_config(project_id="proj-abc")

    with patch("backend.src.modules.orchestrator.application.graph.AsyncSessionMaker", return_value=mock_db), \
         patch("backend.src.modules.orchestrator.application.graph.GeminiEmbeddingClient", return_value=mock_embed_client), \
         patch("backend.src.modules.orchestrator.application.graph.LLMRouter", return_value=mock_llm_router):

        result = await real_rag_node(state, config)

    assert result["citation_map"] == {1: uuid1, 2: uuid2, 3: uuid3}
    assert result["valid_citation_ids"] == [1, 2, 3]
    assert "Câu trả lời" in result["messages"][0].content


# ---------------------------------------------------------------------------
# AC#9 — Query scope bao gồm project_id (kiểm tra WHERE clause)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_real_rag_node_scopes_by_project_id():
    """Query luôn scope theo project_id để không leak chunk của project khác."""
    target_project_id = "proj-xyz-secure"
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []  # empty → không cần LLM

    executed_stmts = []

    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=None)

    async def capture_execute(stmt):
        executed_stmts.append(stmt)
        return mock_result

    mock_db.execute = capture_execute

    mock_embed_client = AsyncMock()
    mock_embed_client.embed_batch = AsyncMock(return_value=[[0.0] * 768])

    state = _make_state()
    config = _make_config(project_id=target_project_id)

    with patch("backend.src.modules.orchestrator.application.graph.AsyncSessionMaker", return_value=mock_db), \
         patch("backend.src.modules.orchestrator.application.graph.GeminiEmbeddingClient", return_value=mock_embed_client), \
         patch("backend.src.modules.orchestrator.application.graph.LLMRouter"):

        await real_rag_node(state, config)

    # Phải có ít nhất 1 câu query được thực thi
    assert len(executed_stmts) >= 1
    # Kiểm tra WHERE clause có filter project_id (SQLAlchemy strip hyphens khi compile UUID)
    stmt = executed_stmts[0]
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    normalized_project_id = target_project_id.replace("-", "")
    assert normalized_project_id in compiled
    assert "project_id" in compiled


# ---------------------------------------------------------------------------
# AC#1 — Embed được gọi với đúng query
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_real_rag_node_embeds_query():
    """Embed được gọi 1 lần với câu hỏi của user."""
    query = "Hỏi về phương pháp nghiên cứu"
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []

    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=None)
    mock_db.execute = AsyncMock(return_value=mock_result)

    mock_embed_client = AsyncMock()
    mock_embed_client.embed_batch = AsyncMock(return_value=[[0.0] * 768])

    state = _make_state(query=query)
    config = _make_config()

    with patch("backend.src.modules.orchestrator.application.graph.AsyncSessionMaker", return_value=mock_db), \
         patch("backend.src.modules.orchestrator.application.graph.GeminiEmbeddingClient", return_value=mock_embed_client), \
         patch("backend.src.modules.orchestrator.application.graph.LLMRouter"):

        await real_rag_node(state, config)

    mock_embed_client.embed_batch.assert_called_once_with([query])


# ---------------------------------------------------------------------------
# AC#3 — Query rỗng/khoảng trắng → empty retrieval, không embed/query/LLM
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_real_rag_node_blank_query_no_embed():
    """Query toàn khoảng trắng → trả EMPTY_RETRIEVAL_MSG, không embed/gọi DB/LLM.

    Tránh zero-vector → NaN cosine ordering → retrieve chunk vô nghĩa.
    """
    state = _make_state(query="   ")
    config = _make_config()

    mock_embed_client = AsyncMock()
    mock_embed_client.embed_batch = AsyncMock(return_value=[[0.0] * 768])
    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=None)

    with patch("backend.src.modules.orchestrator.application.graph.AsyncSessionMaker", return_value=mock_db) as mk_db, \
         patch("backend.src.modules.orchestrator.application.graph.GeminiEmbeddingClient", return_value=mock_embed_client), \
         patch("backend.src.modules.orchestrator.application.graph.LLMRouter") as mock_router_cls:

        result = await real_rag_node(state, config)

    mk_db.assert_not_called()
    mock_embed_client.embed_batch.assert_not_called()
    mock_router_cls.assert_not_called()
    assert result["messages"][0].content == EMPTY_RETRIEVAL_MSG
    assert result["citation_map"] == {}
    assert result["valid_citation_ids"] == []


# ---------------------------------------------------------------------------
# AC#3 — No HumanMessage → trả fallback
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_real_rag_node_no_human_message():
    """Khi không có HumanMessage trong state → trả fallback không crash."""
    from langchain_core.messages import AIMessage

    state = ChatState(
        messages=[AIMessage(content="Bot nói")],
        valid_citation_ids=[],
        citation_map={},
    )
    config = _make_config()

    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=None)

    with patch("backend.src.modules.orchestrator.application.graph.AsyncSessionMaker", return_value=mock_db):
        result = await real_rag_node(state, config)

    assert result["citation_map"] == {}
    assert result["valid_citation_ids"] == []
    assert "Không có câu hỏi" in result["messages"][0].content
