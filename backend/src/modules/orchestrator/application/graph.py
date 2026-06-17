from langchain_core.messages import AIMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import MessagesState, StateGraph


def mock_rag_node(state: MessagesState) -> dict:
    """DummyRetriever: trả về câu trả lời cố định, không gọi Vector DB."""
    return {
        "messages": [
            AIMessage(
                content="Đây là câu trả lời mock từ hệ thống RAG. "
                "Tính năng RAG thực tế sẽ được kích hoạt ở story sau."
            )
        ]
    }


def build_graph(checkpointer: AsyncPostgresSaver):
    builder = StateGraph(MessagesState)
    builder.add_node("mock_rag", mock_rag_node)
    builder.set_entry_point("mock_rag")
    builder.set_finish_point("mock_rag")
    return builder.compile(checkpointer=checkpointer)
