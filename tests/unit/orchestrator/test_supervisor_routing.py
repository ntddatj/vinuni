"""Unit tests cho supervisor_node heuristic routing (AC#1, #2)."""
import pytest
from langchain_core.messages import HumanMessage

from backend.src.modules.orchestrator.application.graph import supervisor_node, _route_supervisor


def _make_state(message: str) -> dict:
    return {"messages": [HumanMessage(content=message)]}


def test_gap_prefill_routes_to_gap_analyst():
    """AC#1a: chuỗi prefill từ NodeDetailCard.tsx phải route gap_analyst."""
    msg = "Phân tích paper về CNN. Hãy chỉ rõ mâu thuẫn, hạn chế và cơ hội nghiên cứu."
    state = _make_state(msg)
    result = supervisor_node(state, config={"configurable": {}})
    assert result["route"] == "gap_analyst"


def test_gap_keyword_routes_to_gap_analyst():
    """Keyword 'khoảng trống' phải route gap_analyst."""
    state = _make_state("Phân tích khoảng trống nghiên cứu trong dự án này?")
    result = supervisor_node(state, config={"configurable": {}})
    assert result["route"] == "gap_analyst"


def test_contradiction_keyword_routes_to_gap_analyst():
    """Keyword 'mâu thuẫn' phải route gap_analyst."""
    state = _make_state("Có mâu thuẫn gì giữa các kết quả nghiên cứu không?")
    result = supervisor_node(state, config={"configurable": {}})
    assert result["route"] == "gap_analyst"


def test_normal_academic_question_routes_to_research_rag():
    """AC#1b: câu hỏi học thuật thông thường phải route research_rag."""
    state = _make_state("CNN được dùng cho bài toán gì trong xử lý ảnh?")
    result = supervisor_node(state, config={"configurable": {}})
    assert result["route"] == "research_rag"


def test_phan_tich_alone_does_not_route_gap_analyst():
    """Regression: 'phân tích' (analyze) là từ học thuật phổ biến, KHÔNG được ép
    route gap_analyst (giữ AC#2 — RAG là nhánh mặc định)."""
    state = _make_state("Phân tích cấu trúc của mạng CNN cho xử lý ảnh.")
    result = supervisor_node(state, config={"configurable": {}})
    assert result["route"] == "research_rag"


def test_hi_substring_does_not_route_chitchat():
    """Regression: 'hi' là substring của 'machine'/'history' — câu hỏi học thuật
    ngắn KHÔNG được route nhầm sang chitchat (word-boundary match)."""
    for q in ("machine learning là gì?", "history of NLP models"):
        result = supervisor_node(_make_state(q), config={"configurable": {}})
        assert result["route"] == "research_rag", q


def test_chitchat_routes_to_chitchat():
    """AC#1c: giao tiếp thông thường phải route chitchat."""
    state = _make_state("xin chào")
    result = supervisor_node(state, config={"configurable": {}})
    assert result["route"] == "chitchat"


def test_who_are_you_routes_to_chitchat():
    """'bạn là ai' phải route chitchat."""
    state = _make_state("bạn là ai vậy?")
    result = supervisor_node(state, config={"configurable": {}})
    assert result["route"] == "chitchat"


def test_no_messages_defaults_to_research_rag():
    """State không có HumanMessage → route mặc định research_rag."""
    state = {"messages": []}
    result = supervisor_node(state, config={"configurable": {}})
    assert result["route"] == "research_rag"


def test_route_supervisor_fn_returns_route_key():
    """_route_supervisor() đọc state.route và trả về đúng key."""
    assert _route_supervisor({"messages": [], "route": "gap_analyst"}) == "gap_analyst"
    assert _route_supervisor({"messages": [], "route": "chitchat"}) == "chitchat"
    assert _route_supervisor({"messages": [], "route": "research_rag"}) == "research_rag"
    # Fallback khi thiếu key
    assert _route_supervisor({"messages": []}) == "research_rag"
