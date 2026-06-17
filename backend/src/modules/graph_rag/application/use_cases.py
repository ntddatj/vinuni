"""Application layer graph_rag — re-export entry points cho worker."""
from backend.src.modules.graph_rag.infrastructure.outbox_worker import sync_outbox_task

__all__ = ["sync_outbox_task"]
