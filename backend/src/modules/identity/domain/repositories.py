from abc import ABC, abstractmethod

from backend.src.modules.identity.domain.entities import User


class UserRepository(ABC):
    @abstractmethod
    async def find_by_email(self, email: str) -> User | None:
        ...

    @abstractmethod
    async def find_by_id(self, user_id: str) -> User | None:
        ...

    @abstractmethod
    async def count_all(self) -> int:
        ...

    @abstractmethod
    async def save(self, user: User) -> User:
        ...
