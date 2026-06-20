import logging
import re
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from sqlalchemy import select, select as sa_select, literal
from pgvector.sqlalchemy import Vector

from backend.src.modules.ingestion.infrastructure.chunk_orm_models import ChildChunkORM
from backend.src.modules.ingestion.infrastructure.embedding_client import GeminiEmbeddingClient
from backend.src.modules.orchestrator.application.tools.graph_rag_tools import (
    gap_detection_tool,
    graph_search_tool,
)
from backend.src.shared.infra.database import AsyncSessionMaker
from backend.src.shared.infra.llm.router import LLMRouter

logger = logging.getLogger(__name__)

TOP_K = 5  # số chunk retrieve tối đa

RAG_SYSTEM_PROMPT = (
    "Bạn là trợ lý nghiên cứu học thuật. Dựa vào các tài liệu sau, hãy trả lời câu hỏi. "
    "Khi trích dẫn, dùng số trong ngoặc vuông như [1], [2] để chỉ tài liệu tương ứng. "
    "Chỉ sử dụng các nguồn được cung cấp, không bịa đặt thông tin."
)

GAP_ANALYST_SYSTEM_PROMPT = (
    "Bạn là chuyên gia phân tích khoảng trống nghiên cứu. "
    "Dựa vào dữ liệu đồ thị tri thức bên dưới, hãy phân tích và chỉ rõ:\n"
    "1. Các mâu thuẫn (CONTRADICTS) giữa kết quả nghiên cứu.\n"
    "2. Các hạn chế chưa được giải quyết (Limitation chưa có FILLS_GAP).\n"
    "3. Các cụm nghiên cứu bị cô lập (isolated cluster).\n"
    "Với mỗi luận điểm, hãy kèm thẻ trích dẫn [N] trỏ tới tài liệu nguồn. "
    "Chỉ dựa vào dữ liệu được cung cấp, không bịa đặt thông tin."
)

EMPTY_RETRIEVAL_MSG = "Chưa có tài liệu liên quan trong dự án để trích dẫn."
EMPTY_GAP_MSG = "Chưa phát hiện khoảng trống/mâu thuẫn rõ ràng trong dữ liệu đồ thị của dự án."

# Keywords cho heuristic routing — giữ SM-3, không dùng LLM để phân loại.
# Lưu ý: KHÔNG thêm từ quá phổ biến như "phân tích" (analyze) vào đây — nó match
# mọi câu hỏi học thuật bình thường ("phân tích cấu trúc CNN") và làm hỏng AC#2
# (RAG phải là nhánh mặc định). Chuỗi prefill Gap→Chat vẫn match qua
# "mâu thuẫn"/"hạn chế"/"cơ hội nghiên cứu".
_GAP_KEYWORDS = [
    "khoảng trống", "mâu thuẫn", "hạn chế", "contradiction", "gap",
    "cơ hội nghiên cứu", "limitation", "isolated",
]
# Chitchat match theo RANH GIỚI TỪ (word boundary), không substring — tránh "hi"
# lọt vào "machine"/"history", "chào" vào từ khác... làm câu hỏi học thuật bị
# định tuyến nhầm sang chitchat.
_CHITCHAT_KEYWORDS = [
    "xin chào", "chào", "hello", "hi", "bạn là ai", "bạn tên gì",
    "bạn có thể làm gì", "cảm ơn", "thank",
]
_CHITCHAT_PATTERN = re.compile(
    "|".join(rf"(?<!\w){re.escape(kw)}(?!\w)" for kw in _CHITCHAT_KEYWORDS)
)


class ChatState(TypedDict):
    messages: Annotated[list, add_messages]
    valid_citation_ids: list[int]   # ordinals [1..K] cho Guardrail
    citation_map: dict[int, str]    # ordinal → chunk UUID cho frontend
    route: str                      # "research_rag" | "gap_analyst" | "chitchat"


def apply_citation_guardrail(answer: str, valid_citation_ids: list[int]) -> str:
    """Thay thế [N] không hợp lệ bằng [Nguồn không xác định].

    valid_citation_ids: danh sách ordinal hợp lệ (ví dụ [1, 2, 3] cho 3 chunks).
    """
    valid_set = set(valid_citation_ids)

    def replace_tag(m: re.Match) -> str:
        n = int(m.group(1))
        return m.group(0) if n in valid_set else "[Nguồn không xác định]"

    return re.sub(r'\[(\d+)\]', replace_tag, answer)


def _route_supervisor(state: ChatState) -> str:
    """Route function cho conditional_edges — trả tên node kế tiếp."""
    return state.get("route", "research_rag")


def supervisor_node(state: ChatState, config: RunnableConfig) -> dict:
    """Heuristic router — KHÔNG gọi LLM để giữ SM-3 (first-chunk < 3s).

    Route gap_analyst khi query chứa keyword khoảng trống/mâu thuẫn/hạn chế.
    Route chitchat cho giao tiếp thông thường. Mặc định research_rag.
    Chuỗi prefill từ NodeDetailCard ("Phân tích ... mâu thuẫn, hạn chế và cơ hội nghiên cứu")
    luôn match _GAP_KEYWORDS → route gap_analyst (AC#1).
    """
    last_human = next(
        (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
        None,
    )
    if not last_human:
        return {"route": "research_rag"}

    query = (last_human.content if isinstance(last_human.content, str) else "").lower()

    # Kiểm tra gap keywords trước (ưu tiên cao hơn chitchat — tránh false positive
    # khi "hi" là substring của "nghiên" hoặc các từ tiếng Việt khác)
    if any(kw in query for kw in _GAP_KEYWORDS):
        return {"route": "gap_analyst"}

    # Kiểm tra chitchat (câu ngắn, không có keyword nghiên cứu) — match theo
    # ranh giới từ để "hi"/"chào"... không lọt vào từ dài hơn (machine, history).
    if len(query) < 100 and _CHITCHAT_PATTERN.search(query):
        return {"route": "chitchat"}

    return {"route": "research_rag"}


def chitchat_node(state: ChatState, config: RunnableConfig) -> dict:
    """Trả lời giao tiếp thông thường — không cần retrieval."""
    return {
        "messages": [AIMessage(content="Xin chào! Tôi là trợ lý nghiên cứu học thuật. Tôi có thể giúp bạn tìm kiếm tài liệu, trả lời câu hỏi học thuật, và phân tích khoảng trống nghiên cứu trong dự án của bạn.")],
        "valid_citation_ids": [],
        "citation_map": {},
    }


async def real_rag_node(state: ChatState, config: RunnableConfig) -> dict:
    """RAG thật: embed câu hỏi, cosine search pgvector, stream LLM."""
    user_id: str = config["configurable"]["user_id"]
    project_id: str = config["configurable"]["project_id"]

    # Lấy câu hỏi mới nhất từ state
    last_human = next(
        (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
        None,
    )
    if not last_human:
        return {
            "messages": [AIMessage(content="Không có câu hỏi để trả lời.")],
            "valid_citation_ids": [],
            "citation_map": {},
        }
    query = last_human.content if isinstance(last_human.content, str) else ""
    # Query rỗng/toàn khoảng trắng → embedding sẽ là zero-vector, khiến cosine
    # distance (<=>) trả NaN và pgvector xếp hạng tùy ý → retrieve chunk vô nghĩa.
    # Trả empty retrieval thay vì trích dẫn tài liệu không liên quan.
    if not query.strip():
        return {
            "messages": [AIMessage(content=EMPTY_RETRIEVAL_MSG)],
            "valid_citation_ids": [],
            "citation_map": {},
        }

    async with AsyncSessionMaker() as db:
        # 1) Embed câu hỏi
        embedding_client = GeminiEmbeddingClient(user_id, db)
        embeddings = await embedding_client.embed_batch([query])
        query_embedding = embeddings[0]

        # 2) Cosine similarity search (HNSW index vector_cosine_ops)
        query_vec = literal(query_embedding, Vector(768))
        stmt = (
            select(ChildChunkORM.id, ChildChunkORM.content)
            .where(ChildChunkORM.project_id == project_id)
            .where(ChildChunkORM.embedding.is_not(None))
            .order_by(ChildChunkORM.embedding.op("<=>")(query_vec))
            .limit(TOP_K)
        )
        result = await db.execute(stmt)
        rows = result.fetchall()

        # 3) Empty retrieval → trả câu cố định, không gọi LLM
        if not rows:
            return {
                "messages": [AIMessage(content=EMPTY_RETRIEVAL_MSG)],
                "valid_citation_ids": [],
                "citation_map": {},
            }

        # 4) Build citation_map và context
        citation_map: dict[int, str] = {i + 1: str(row.id) for i, row in enumerate(rows)}
        valid_citation_ids: list[int] = list(citation_map.keys())
        context = "\n\n".join(
            f"[{ordinal}] {row.content}"
            for ordinal, row in zip(citation_map.keys(), rows)
        )

        # 5) LLM client (lấy trong cùng session để resolve API key)
        llm_router = LLMRouter(db)
        llm = await llm_router.get_llm_client(user_id)

    # 6) Bổ sung graph_search context (fusion — AC#5)
    # Trích thực thể đơn giản: lấy 3-5 từ đầu của query làm entities
    graph_context_section = ""
    try:
        # Heuristic entity extraction: lấy cụm từ 2+ ký tự không phải stopword
        stop = {"là", "và", "của", "cho", "với", "trong", "này", "đó", "các", "những",
                "một", "có", "không", "để", "từ", "theo", "về", "được", "bị", "tại"}
        tokens = [w for w in query.split() if len(w) > 2 and w.lower() not in stop]
        entities = tokens[:5]
        if entities:
            graph_ctx = await graph_search_tool(entities, project_id)
            graph_lines = []
            for n in graph_ctx.nodes:
                # Guard nợ kỹ thuật 4.4
                if not getattr(n, "id", None):
                    continue
                if n.label not in {"paper", "author"}:
                    continue
                graph_lines.append(f"- [{n.label}] {n.title} (id: {n.id})")
            if graph_lines:
                graph_context_section = "\n\n[Quan hệ Đồ thị tri thức]\n" + "\n".join(graph_lines)
    except Exception:
        logger.warning("real_rag_node: graph_search fusion failed, skipping", exc_info=True)

    # Giới hạn ~8000 token tổng context (rough: 1 token ≈ 4 chars → 32000 chars)
    combined = context + graph_context_section
    if len(combined) > 32000:
        combined = combined[:32000]

    # 7) Gọi LLM (ngoài session đã đóng — chỉ cần llm object)
    prompt = f"{RAG_SYSTEM_PROMPT}\n\nTài liệu nghiên cứu:\n{combined}\n\nCâu hỏi: {query}"
    full_response = ""
    async for chunk in llm.astream([HumanMessage(content=prompt)]):
        if isinstance(chunk.content, str):
            full_response += chunk.content

    return {
        "messages": [AIMessage(content=full_response)],
        "valid_citation_ids": valid_citation_ids,
        "citation_map": citation_map,
    }


async def gap_analyst_node(state: ChatState, config: RunnableConfig) -> dict:
    """Gap Analyst Agent — phân tích khoảng trống/mâu thuẫn từ đồ thị tri thức.

    1. Gọi gap_detection_tool để lấy GapContext.
    2. Empty-safe (AC#4): nếu không có flagged_nodes/flagged_edges → trả câu cố định.
    3. Lookup chunk đại diện của mỗi paper_id để giữ cùng contract ordinal→chunk UUID
       với tooltip Story 3.5/3.6 (tránh đẻ thêm endpoint).
    4. Gọi LLM với model pro để sinh phân tích có trích dẫn [N].
    """
    user_id: str = config["configurable"]["user_id"]
    project_id: str = config["configurable"]["project_id"]

    # 1) Phát hiện khoảng trống — NEVER raises
    gap_ctx = await gap_detection_tool(project_id)

    # 2) Empty-safe guard (AC#4)
    if not gap_ctx.flagged_nodes and not gap_ctx.flagged_edges:
        return {
            "messages": [AIMessage(content=EMPTY_GAP_MSG)],
            "valid_citation_ids": [],
            "citation_map": {},
        }

    # 3) Thu thập paper_ids từ flagged nodes + edges
    paper_ids: list[str] = []
    seen_pids: set[str] = set()
    for node in gap_ctx.flagged_nodes:
        if node.paper_id not in seen_pids:
            paper_ids.append(node.paper_id)
            seen_pids.add(node.paper_id)
    for edge in gap_ctx.flagged_edges:
        for pid in (edge.paper1_id, edge.paper2_id):
            if pid not in seen_pids:
                paper_ids.append(pid)
                seen_pids.add(pid)

    # 4) Lookup chunk đại diện (1 chunk/paper) để ánh xạ ordinal → chunk UUID
    # Giữ cùng contract /api/citations/{chunk_id} của Story 3.5/3.6.
    citation_map: dict[int, str] = {}
    paper_to_ordinal: dict[str, int] = {}

    async with AsyncSessionMaker() as db:
        for pid in paper_ids:
            stmt = (
                sa_select(ChildChunkORM.id)
                .where(ChildChunkORM.paper_id == pid)
                .where(ChildChunkORM.project_id == project_id)
                .limit(1)
            )
            result = await db.execute(stmt)
            row = result.scalar_one_or_none()
            if row is not None:
                # Ordinal cấp phát theo thứ tự CHUNK TÌM ĐƯỢC để [N] liền mạch từ 1
                # (paper thiếu chunk bị bỏ qua, không để lại lỗ hổng ordinal).
                ordinal = len(citation_map) + 1
                citation_map[ordinal] = str(row)
                paper_to_ordinal[pid] = ordinal

        valid_citation_ids = list(citation_map.keys())

        # Nếu không lookup được chunk nào → trả empty (tránh citation ảo), không gọi LLM
        if not valid_citation_ids:
            return {
                "messages": [AIMessage(content=EMPTY_GAP_MSG)],
                "valid_citation_ids": [],
                "citation_map": {},
            }

        # 5) Resolve LLM client trong cùng session (chỉ khi có dữ liệu để phân tích)
        llm_router = LLMRouter(db)
        llm = await llm_router.get_llm_client(user_id, model_name="gemini-2.5-pro")

    # 6) Build context gap
    gap_lines: list[str] = []
    for node in gap_ctx.flagged_nodes:
        ordinal = paper_to_ordinal.get(node.paper_id)
        if ordinal is None:
            continue
        reason_label = {
            "has_contradiction": "Mâu thuẫn trong kết quả nghiên cứu",
            "has_unfilled_limitation": "Hạn chế chưa được giải quyết",
            "isolated_cluster": "Cụm nghiên cứu cô lập",
        }.get(node.reason, node.reason)
        gap_lines.append(f"[{ordinal}] {reason_label} (paper_id: {node.paper_id})")

    for edge in gap_ctx.flagged_edges:
        ord1 = paper_to_ordinal.get(edge.paper1_id)
        ord2 = paper_to_ordinal.get(edge.paper2_id)
        refs = " ".join(f"[{o}]" for o in [ord1, ord2] if o is not None)
        # Bỏ qua edge không trỏ tới ordinal nào — tránh feed LLM luận điểm mâu thuẫn
        # không có nguồn [N] (dễ dẫn tới trích dẫn bịa).
        if not refs:
            continue
        gap_lines.append(f"{refs} Mâu thuẫn giữa finding {edge.finding1_id} và {edge.finding2_id}")

    # 7) Tùy chọn bổ sung graph_search context cho các thực thể chính
    graph_lines: list[str] = []
    try:
        # Lấy tối đa 5 paper_id đầu làm entities để graph_search
        sample_entities = paper_ids[:5]
        if sample_entities:
            graph_ctx = await graph_search_tool(sample_entities, project_id)
            for n in graph_ctx.nodes:
                # Guard nợ kỹ thuật 4.4: bỏ node thiếu id hoặc label không phải paper/author
                if not getattr(n, "id", None):
                    continue
                if n.label not in {"paper", "author"}:
                    continue
                graph_lines.append(f"- [{n.label}] {n.title} (id: {n.id})")
    except Exception:
        logger.warning("gap_analyst_node: graph_search_tool failed, skipping", exc_info=True)

    context_parts = ["[Khoảng trống phát hiện được]\n" + "\n".join(gap_lines)]
    if graph_lines:
        total_tokens_estimate = sum(len(p) for p in context_parts) + sum(len(g) for g in graph_lines)
        if total_tokens_estimate < 30000:  # ~8000 token limit (rough: 1 token ≈ 4 chars)
            context_parts.append("[Quan hệ Đồ thị tri thức]\n" + "\n".join(graph_lines))

    context = "\n\n".join(context_parts)

    last_human = next(
        (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
        None,
    )
    query = (last_human.content if last_human and isinstance(last_human.content, str) else "Phân tích khoảng trống nghiên cứu")

    prompt = f"{GAP_ANALYST_SYSTEM_PROMPT}\n\nDữ liệu đồ thị:\n{context}\n\nYêu cầu: {query}"

    full_response = ""
    async for chunk in llm.astream([HumanMessage(content=prompt)]):
        if isinstance(chunk.content, str):
            full_response += chunk.content

    return {
        "messages": [AIMessage(content=full_response)],
        "valid_citation_ids": valid_citation_ids,
        "citation_map": citation_map,
    }


def citation_guardrail_node(state: ChatState) -> dict:
    """Kiểm chứng và thay thế citation ảo trong câu trả lời cuối."""
    last = state["messages"][-1]
    # Chỉ xử lý content dạng chuỗi. Real RAG node có thể trả content
    # dạng list content-block (multimodal) — bỏ qua để tránh TypeError trong re.sub.
    if not isinstance(last.content, str):
        return {}
    cleaned = apply_citation_guardrail(
        answer=last.content,
        valid_citation_ids=state.get("valid_citation_ids", []),
    )
    if cleaned == last.content:
        return {}  # không thay đổi
    # Trả AIMessage cùng id để add_messages GHI ĐÈ message gốc thay vì append thêm.
    # Nếu không, bản chưa kiểm duyệt (còn citation ảo) vẫn nằm trong checkpoint và bị
    # replay ở các lượt invoke sau, làm hỏng mục đích của guardrail.
    return {
        "messages": [AIMessage(content=cleaned, id=last.id)]
    }


def build_graph(checkpointer: AsyncPostgresSaver):
    """Router-Worker topology (Story 4.5).

    supervisor → (research_rag | gap_analyst | chitchat) → citation_guardrail
    GIỮ signature build_graph(checkpointer) để không vỡ InvokeUseCase/test.
    build_graph(None) dựng topology không cần DB (cho test).
    """
    builder = StateGraph(ChatState)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("research_rag", real_rag_node)
    builder.add_node("gap_analyst", gap_analyst_node)
    builder.add_node("chitchat", chitchat_node)
    builder.add_node("citation_guardrail", citation_guardrail_node)

    builder.set_entry_point("supervisor")
    builder.add_conditional_edges(
        "supervisor",
        _route_supervisor,
        {
            "research_rag": "research_rag",
            "gap_analyst": "gap_analyst",
            "chitchat": "chitchat",
        },
    )
    # Mọi worker hội tụ tại citation_guardrail (AC#6)
    builder.add_edge("research_rag", "citation_guardrail")
    builder.add_edge("gap_analyst", "citation_guardrail")
    builder.add_edge("chitchat", "citation_guardrail")
    builder.set_finish_point("citation_guardrail")
    return builder.compile(checkpointer=checkpointer)
