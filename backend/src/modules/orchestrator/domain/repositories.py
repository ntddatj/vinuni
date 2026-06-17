from abc import ABC, abstractmethod

from backend.src.modules.orchestrator.domain.entities import ChatMessage, ChatThread


class ChatThreadRepository(ABC):
    @abstractmethod
    async def create(self, user_id: str, project_id: str, title: str) -> ChatThread: ...

    @abstractmethod
    async def find_by_id(self, thread_id: str) -> ChatThread | None: ...

    @abstractmethod
    async def list_by_project(self, user_id: str, project_id: str) -> list[ChatThread]: ...

    @abstractmethod
    async def list_messages(self, thread_id: str) -> list[ChatMessage]: ...

    @abstractmethod
    async def save_message(self, thread_id: str, role: str, content: str) -> ChatMessage: ...
