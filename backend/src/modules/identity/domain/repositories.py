from abc import ABC, abstractmethod

from backend.src.modules.identity.domain.entities import User, UserCredential


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


class UserCredentialRepository(ABC):
    @abstractmethod
    async def find_by_user_and_provider(self, user_id: str, provider: str) -> UserCredential | None:
        ...

    @abstractmethod
    async def list_by_user(self, user_id: str) -> list[UserCredential]:
        ...

    @abstractmethod
    async def upsert(self, credential: UserCredential) -> UserCredential:
        ...

    @abstractmethod
    async def update_test_result(self, credential_id: str, is_valid: bool) -> None:
        ...

    @abstractmethod
    async def delete(self, credential_id: str) -> None:
        ...
