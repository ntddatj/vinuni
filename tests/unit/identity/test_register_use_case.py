"""Unit tests for RegisterUserUseCase — pure domain logic, no DB."""
import pytest

from backend.src.modules.identity.application.dtos import RegisterUserDTO
from backend.src.modules.identity.application.use_cases import RegisterUserUseCase
from backend.src.modules.identity.domain.entities import User
from backend.src.modules.identity.domain.exceptions import EmailAlreadyExistsError
from backend.src.modules.identity.domain.repositories import UserRepository


class InMemoryUserRepository(UserRepository):
    """Fake in-memory repo for unit tests."""

    def __init__(self):
        self._users: list[User] = []

    async def find_by_email(self, email: str) -> User | None:
        return next((u for u in self._users if u.email == email), None)

    async def find_by_id(self, user_id: str) -> User | None:
        return next((u for u in self._users if u.id == user_id), None)

    async def count_all(self) -> int:
        return len(self._users)

    async def save(self, user: User) -> User:
        self._users.append(user)
        return user


@pytest.fixture
def repo() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def use_case(repo: InMemoryUserRepository) -> RegisterUserUseCase:
    return RegisterUserUseCase(repo)


@pytest.mark.asyncio
async def test_first_user_gets_admin_role(use_case: RegisterUserUseCase):
    result = await use_case.execute(RegisterUserDTO(email="admin@test.com", password="secret123"))
    assert result.role == "admin"


@pytest.mark.asyncio
async def test_second_user_gets_user_role(use_case: RegisterUserUseCase):
    await use_case.execute(RegisterUserDTO(email="first@test.com", password="secret123"))
    result = await use_case.execute(RegisterUserDTO(email="second@test.com", password="secret123"))
    assert result.role == "user"


@pytest.mark.asyncio
async def test_password_is_hashed(use_case: RegisterUserUseCase, repo: InMemoryUserRepository):
    import bcrypt

    dto = RegisterUserDTO(email="user@test.com", password="myplainpassword")
    await use_case.execute(dto)
    saved = await repo.find_by_email("user@test.com")
    assert saved is not None
    assert saved.hashed_password != "myplainpassword"
    assert bcrypt.checkpw(b"myplainpassword", saved.hashed_password.encode())


@pytest.mark.asyncio
async def test_duplicate_email_raises_error(use_case: RegisterUserUseCase):
    await use_case.execute(RegisterUserDTO(email="dup@test.com", password="secret123"))
    with pytest.raises(EmailAlreadyExistsError):
        await use_case.execute(RegisterUserDTO(email="dup@test.com", password="another123"))


@pytest.mark.asyncio
async def test_user_is_active_by_default(use_case: RegisterUserUseCase):
    result = await use_case.execute(RegisterUserDTO(email="active@test.com", password="secret123"))
    assert result.is_active is True


@pytest.mark.asyncio
async def test_returned_dto_has_correct_email(use_case: RegisterUserUseCase):
    result = await use_case.execute(RegisterUserDTO(email="match@test.com", password="secret123"))
    assert result.email == "match@test.com"


@pytest.mark.asyncio
async def test_email_normalized_to_lowercase(use_case: RegisterUserUseCase):
    result = await use_case.execute(RegisterUserDTO(email="User@Test.COM", password="secret123"))
    assert result.email == "user@test.com"
