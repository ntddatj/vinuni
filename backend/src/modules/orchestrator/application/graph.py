import logging
import re
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from sqlalchemy import select, literal
from pgvector.sqlalchemy import Vector

from backend.src.modules.ingestion.infrastructure.chunk_orm_models import ChildChunkORM
from backend.src.modules.ingestion.infrastructure.embedding_client import GeminiEmbeddingClient
from backend.src.shared.infra.database import AsyncSessionMaker
from backend.src.shared.infra.llm.router import LLMRouter

logger = logging.getLogger(__name__)

TOP_K = 5  # số chunk retrieve tối đa

RAG_SYSTEM_PROMPT = (
    "Bạn là trợ lý nghiên cứu học thuật. Dựa vào các tài liệu sau, hãy trả lời câu hỏi. "
    "Khi trích dẫn, dùng số trong ngoặc vuông như [1], [2] để chỉ tài liệu tương ứng. "
    "Chỉ sử dụng các nguồn được cung cấp, không bịa đặt thông tin."
)

EMPTY_RETRIEVAL_MSG = "Chưa có tài liệu liên quan trong dự án để trích dẫn."


class ChatState(TypedDict):
    messages: Annotated[list, add_messages]
    valid_citation_ids: list[int]   # ordinals [1..K] cho Guardrail
    citation_map: dict[int, str]    # ordinal → chunk UUID cho frontend


def apply_citation_guardrail(answer: str, valid_citation_ids: list[int]) -> str:
    """Thay thế [N] không hợp lệ bằng [Nguồn không xác định].

    valid_citation_ids: danh sách ordinal hợp lệ (ví dụ [1, 2, 3] cho 3 chunks).
    """
    valid_set = set(valid_citation_ids)

    def replace_tag(m: re.Match) -> str:
        n = int(m.group(1))
        return m.group(0) if n in valid_set else "[Nguồn không xác định]"

    return re.sub(r'\[(\d+)\]', replace_tag, answer)


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

    # 6) Gọi LLM (ngoài session đã đóng — chỉ cần llm object)
    prompt = f"{RAG_SYSTEM_PROMPT}\n\nTài liệu nghiên cứu:\n{context}\n\nCâu hỏi: {query}"
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
    builder = StateGraph(ChatState)
    builder.add_node("real_rag", real_rag_node)
    builder.add_node("citation_guardrail", citation_guardrail_node)
    builder.set_entry_point("real_rag")
    builder.add_edge("real_rag", "citation_guardrail")
    builder.set_finish_point("citation_guardrail")
    return builder.compile(checkpointer=checkpointer)
