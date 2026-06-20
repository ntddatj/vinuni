"""Unit tests cho SSE token filter (AC#9) trong _stream_graph_to_queue."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import AIMessage


def _make_chunk_event(node_name: str, text: str) -> dict:
    """Tạo fake on_chat_model_stream event với langgraph_node metadata."""
    chunk = MagicMock()
    chunk.content = text
    return {
        "event": "on_chat_model_stream",
        "metadata": {"langgraph_node": node_name},
        "data": {"chunk": chunk},
    }


def _make_chain_start_event(node_name: str) -> dict:
    return {
        "event": "on_chain_start",
        "metadata": {"langgraph_node": node_name},
        "data": {},
    }


async def _run_stream_to_queue(events: list[dict]) -> list[dict]:
    """Chạy _stream_graph_to_queue với mock graph trả events đã cho."""
    from backend.src.modules.orchestrator.application.use_cases import _stream_graph_to_queue

    queue: asyncio.Queue = asyncio.Queue()

    # Mock state sau khi stream xong
    final_state = MagicMock()
    final_state.values = {
        "messages": [AIMessage(content="Kết quả test")],
        "citation_map": {},
    }

    async def _fake_astream_events(*args, **kwargs):
        for ev in events:
            yield ev

    mock_graph = MagicMock()
    mock_graph.astream_events = _fake_astream_events
    mock_graph.aget_state = AsyncMock(return_value=final_state)

    with patch(
        "backend.src.modules.orchestrator.application.use_cases.get_postgres_checkpointer",
        new=AsyncMock(return_value=MagicMock()),
    ), patch(
        "backend.src.modules.orchestrator.application.use_cases.build_graph",
        return_value=mock_graph,
    ), patch(
        "backend.src.modules.orchestrator.application.use_cases.AsyncSessionMaker",
        return_value=MagicMock(__aenter__=AsyncMock(return_value=MagicMock()), __aexit__=AsyncMock()),
    ), patch(
        "backend.src.modules.orchestrator.application.use_cases.PostgresChatThreadRepository",
    ):
        await _stream_graph_to_queue(
            run_id="run-test",
            thread_id="thread-1",
            user_id="user-1",
            project_id="proj-1",
            message="test",
            queue=queue,
        )

    items = []
    while not queue.empty():
        item = queue.get_nowait()
        if item is not None:
            items.append(item)
    return items


@pytest.mark.asyncio
async def test_supervisor_tokens_not_emitted():
    """AC#9: token của supervisor node KHÔNG được đưa vào queue."""
    events = [
        _make_chain_start_event("supervisor"),
        _make_chunk_event("supervisor", "classification token"),
        _make_chunk_event("research_rag", "kết quả RAG"),
    ]
    items = await _run_stream_to_queue(events)
    chunk_texts = [i["data"] for i in items if i.get("type") == "chunk"]

    assert "classification token" not in chunk_texts
    assert "kết quả RAG" in chunk_texts


@pytest.mark.asyncio
async def test_worker_tokens_are_emitted():
    """Token của research_rag và gap_analyst phải được emit."""
    events = [
        _make_chunk_event("research_rag", "chunk RAG 1"),
        _make_chunk_event("gap_analyst", "chunk gap 1"),
    ]
    items = await _run_stream_to_queue(events)
    chunk_texts = [i["data"] for i in items if i.get("type") == "chunk"]

    assert "chunk RAG 1" in chunk_texts
    assert "chunk gap 1" in chunk_texts


@pytest.mark.asyncio
async def test_agent_thinking_emitted_before_first_chunk():
    """AC#8: frame agent_thinking phải xuất hiện TRƯỚC chunk đầu tiên của worker."""
    events = [
        _make_chain_start_event("research_rag"),
        _make_chunk_event("research_rag", "first token"),
    ]
    items = await _run_stream_to_queue(events)

    type_seq = [i.get("type") for i in items]
    # agent_thinking phải xuất hiện trong sequence
    assert "agent_thinking" in type_seq
    # agent_thinking phải trước chunk đầu tiên
    first_thinking = type_seq.index("agent_thinking")
    first_chunk = type_seq.index("chunk")
    assert first_thinking < first_chunk
