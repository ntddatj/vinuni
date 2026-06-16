"""Unit tests for LoginUserUseCase — pure domain logic, no DB."""
import pytest

from backend.src.modules.identity.application.dtos import LoginUserDTO, RegisterUserDTO
from backend.src.modules.identity.application.use_cases import LoginUserUseCase, RegisterUserUseCase
from backend.src.modules.identity.domain.entities import User
from backend.src.modules.identity.domain.exceptions import InvalidCredentialsError
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
def login_use_case(repo: InMemoryUserRepository) -> LoginUserUseCase:
    return LoginUserUseCase(repo)


@pytest.fixture
def register_use_case(repo: InMemoryUserRepository) -> RegisterUserUseCase:
    return RegisterUserUseCase(repo)


@pytest.mark.asyncio
async def test_login_success_returns_dto_with_token(login_use_case, register_use_case):
    await register_use_case.execute(RegisterUserDTO(email="user@test.com", password="password123"))
    result = await login_use_case.execute(LoginUserDTO(email="user@test.com", password="password123"))
    assert result.email == "user@test.com"
    assert result.role == "admin"
    assert result.is_active is True
    assert result.access_token  # JWT string should be non-empty


@pytest.mark.asyncio
async def test_login_wrong_email_raises_invalid_credentials(login_use_case):
    with pytest.raises(InvalidCredentialsError):
        await login_use_case.execute(LoginUserDTO(email="noone@test.com", password="password123"))


@pytest.mark.asyncio
async def test_login_wrong_password_raises_invalid_credentials(login_use_case, register_use_case):
    await register_use_case.execute(RegisterUserDTO(email="user@test.com", password="correctpass"))
    with pytest.raises(InvalidCredentialsError):
        await login_use_case.execute(LoginUserDTO(email="user@test.com", password="wrongpass!!"))


@pytest.mark.asyncio
async def test_login_inactive_user_raises_invalid_credentials(login_use_case, repo):
    import bcrypt
    from datetime import UTC, datetime
    inactive_user = User(
        id="inactive-id",
        email="inactive@test.com",
        hashed_password=bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode(),
        role="user",
        is_active=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    repo._users.append(inactive_user)
    with pytest.raises(InvalidCredentialsError):
        await login_use_case.execute(LoginUserDTO(email="inactive@test.com", password="password123"))


@pytest.mark.asyncio
async def test_login_email_normalized_to_lowercase(login_use_case, register_use_case):
    await register_use_case.execute(RegisterUserDTO(email="user@test.com", password="password123"))
    result = await login_use_case.execute(LoginUserDTO(email="USER@TEST.COM", password="password123"))
    assert result.email == "user@test.com"


@pytest.mark.asyncio
async def test_login_token_contains_user_id(login_use_case, register_use_case):
    import jwt
    from backend.src.shared.infra.settings import get_settings
    settings = get_settings()
    await register_use_case.execute(RegisterUserDTO(email="user@test.com", password="password123"))
    result = await login_use_case.execute(LoginUserDTO(email="user@test.com", password="password123"))
    payload = jwt.decode(result.access_token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    assert payload["sub"] == result.id
    assert payload["role"] == result.role


@pytest.mark.asyncio
async def test_login_error_message_is_generic(login_use_case):
    """Error message should NOT reveal whether email or password is wrong."""
    with pytest.raises(InvalidCredentialsError) as exc_info:
        await login_use_case.execute(LoginUserDTO(email="noone@test.com", password="anypass123"))
    assert "Email hoặc mật khẩu không đúng" in str(exc_info.value)
