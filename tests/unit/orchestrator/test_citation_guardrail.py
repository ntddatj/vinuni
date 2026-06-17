"""Unit tests cho citation_guardrail — AC#1, #2, #3, #4."""
from backend.src.modules.orchestrator.application.graph import apply_citation_guardrail, build_graph


def test_guardrail_replaces_invalid_citation():
    result = apply_citation_guardrail(
        answer="Apple is red [1] và blue [99]",
        valid_citation_ids=[1],
    )
    assert result == "Apple is red [1] và blue [Nguồn không xác định]"


def test_guardrail_keeps_valid_citations():
    result = apply_citation_guardrail(
        answer="Research shows [1] and [2]",
        valid_citation_ids=[1, 2],
    )
    assert result == "Research shows [1] and [2]"


def test_guardrail_replaces_all_when_no_valid():
    result = apply_citation_guardrail(
        answer="Text [1] text [2]",
        valid_citation_ids=[],
    )
    assert result == "Text [Nguồn không xác định] text [Nguồn không xác định]"


def test_guardrail_no_citation_tags_unchanged():
    text = "Đây là câu trả lời không có trích dẫn."
    assert apply_citation_guardrail(text, []) == text


def test_graph_has_guardrail_node():
    # LangGraph accepts None as a valid no-op checkpointer
    graph = build_graph(None)
    assert "citation_guardrail" in graph.nodes


def test_guardrail_node_runs_after_real_rag():
    # AC#6: node citation_guardrail phải chạy SAU real_rag (không chỉ tồn tại).
    graph = build_graph(None)
    edges = {(e.source, e.target) for e in graph.get_graph().edges}
    assert ("real_rag", "citation_guardrail") in edges
