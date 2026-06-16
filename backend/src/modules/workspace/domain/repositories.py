from abc import ABC, abstractmethod

from backend.src.modules.workspace.domain.entities import Project


class ProjectRepository(ABC):
    @abstractmethod
    async def save(self, project: Project) -> Project: ...

    @abstractmethod
    async def find_by_id(self, project_id: str) -> Project | None: ...

    @abstractmethod
    async def list_by_user(self, user_id: str, limit: int = 10, offset: int = 0, name: str | None = None) -> list[Project]: ...

    @abstractmethod
    async def count_by_user(self, user_id: str, name: str | None = None) -> int: ...

    @abstractmethod
    async def update(self, project: Project) -> Project: ...

    @abstractmethod
    async def soft_delete(self, project: Project) -> None: ...
