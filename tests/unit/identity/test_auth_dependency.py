"""Unit tests for the get_current_user FastAPI dependency — pure logic, no DB/HTTP server."""
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import HTTPException
from starlette.requests import Request

from backend.src.modules.identity.domain.entities import User
from backend.src.modules.identity.domain.repositories import UserRepository
from backend.src.modules.identity.infrastructure.auth_dependencies import get_current_user
from backend.src.shared.infra.jwt_utils import create_access_token
from backend.src.shared.infra.settings import get_settings

settings = get_settings()


class InMemoryUserRepository(UserRepository):
    """Fake in-memory repo for unit tests."""

    def __init__(self) -> None:
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


def _make_request(cookies: dict[str, str] | None = None) -> Request:
    """Build a minimal Starlette Request carrying the given cookies."""
    headers = []
    if cookies:
        cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())
        headers.append((b"cookie", cookie_header.encode()))
    return Request({"type": "http", "headers": headers})


def _make_user(user_id: str = "user-1", *, is_active: bool = True, role: str = "admin") -> User:
    return User(
        id=user_id,
        email="user@test.com",
        hashed_password="x",
        role=role,
        is_active=is_active,
    )


@pytest.fixture
def repo() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.mark.asyncio
async def test_no_cookie_returns_401(repo: InMemoryUserRepository):
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(_make_request(None), repo)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_garbage_token_returns_401(repo: InMemoryUserRepository):
    request = _make_request({"access_token": "not.a.valid.jwt"})
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request, repo)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_expired_token_returns_401(repo: InMemoryUserRepository):
    expired_token = jwt.encode(
        {"sub": "user-1", "role": "admin", "exp": datetime.now(UTC) - timedelta(hours=1)},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(_make_request({"access_token": expired_token}), repo)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_token_missing_sub_returns_401(repo: InMemoryUserRepository):
    """Token thiếu claim `sub` bị decode require từ chối -> 401."""
    token = jwt.encode(
        {"role": "admin", "exp": datetime.now(UTC) + timedelta(hours=1)},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(_make_request({"access_token": token}), repo)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_user_not_found_returns_401(repo: InMemoryUserRepository):
    token = create_access_token("ghost-id", "admin")
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(_make_request({"access_token": token}), repo)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_inactive_user_returns_403(repo: InMemoryUserRepository):
    user = _make_user(user_id="inactive-1", is_active=False)
    repo._users.append(user)
    token = create_access_token(user.id, user.role)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(_make_request({"access_token": token}), repo)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_valid_token_returns_user(repo: InMemoryUserRepository):
    user = _make_user(user_id="user-1")
    repo._users.append(user)
    token = create_access_token(user.id, user.role)
    result = await get_current_user(_make_request({"access_token": token}), repo)
    assert result.id == "user-1"
    assert result.email == "user@test.com"
