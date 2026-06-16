"""Integration tests for login/me/logout endpoints using TestClient with SQLite."""
import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.src.modules.identity.infrastructure.dependencies import get_user_repository
from backend.src.modules.identity.infrastructure.postgres_repository import PostgresUserRepository
from backend.src.modules.identity.presentation.router import router as identity_router
from backend.src.shared.infra.database import Base, get_db_session

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
def client():
    """TestClient using SQLite in-memory — no real Postgres, no lifespan needed."""
    test_engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    test_async_session = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db():
        async with test_async_session() as session:
            yield session

    async def override_get_user_repository():
        async with test_async_session() as session:
            yield PostgresUserRepository(session)

    async def create_tables():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(create_tables())

    test_app = FastAPI()
    test_app.include_router(identity_router, prefix="/api")
    test_app.dependency_overrides[get_db_session] = override_get_db
    test_app.dependency_overrides[get_user_repository] = override_get_user_repository

    with TestClient(test_app, raise_server_exceptions=True) as c:
        yield c


def _register_and_login(client: TestClient, email: str = "user@example.com", password: str = "password123"):
    client.post("/api/auth/register", json={"email": email, "password": password})
    return client.post("/api/auth/login", json={"email": email, "password": password})


# --- Login endpoint ---

def test_login_success_returns_200_and_user_info(client: TestClient):
    client.post("/api/auth/register", json={"email": "user@example.com", "password": "password123"})
    response = client.post("/api/auth/login", json={"email": "user@example.com", "password": "password123"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "user@example.com"
    assert data["role"] == "admin"
    assert data["isActive"] is True
    assert "id" in data
    assert "createdAt" in data


def test_login_sets_httponly_cookie(client: TestClient):
    client.post("/api/auth/register", json={"email": "user@example.com", "password": "password123"})
    response = client.post("/api/auth/login", json={"email": "user@example.com", "password": "password123"})
    assert response.status_code == 200
    assert "access_token" in response.cookies
    # Kiểm tra trực tiếp header Set-Cookie để chắc chắn các cờ bảo mật được set
    set_cookie = response.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie


def test_login_long_password_returns_401_not_500(client: TestClient):
    """Mật khẩu > 72 byte phải quy về 401 generic, không được vỡ thành 500."""
    client.post("/api/auth/register", json={"email": "user@example.com", "password": "password123"})
    response = client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "x" * 100},
    )
    assert response.status_code == 401


def test_login_short_password_reaches_auth_not_422(client: TestClient):
    """Login không áp lại min_length: mật khẩu ngắn -> 401 (sai credential), không phải 422."""
    client.post("/api/auth/register", json={"email": "user@example.com", "password": "password123"})
    response = client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "short"},
    )
    assert response.status_code == 401


def test_login_wrong_password_returns_401(client: TestClient):
    client.post("/api/auth/register", json={"email": "user@example.com", "password": "correctpass"})
    response = client.post("/api/auth/login", json={"email": "user@example.com", "password": "wrongpass!!"})
    assert response.status_code == 401
    assert "Email hoặc mật khẩu không đúng" in response.json()["detail"]


def test_login_wrong_email_returns_401(client: TestClient):
    response = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "password123"})
    assert response.status_code == 401


def test_login_response_uses_camel_case(client: TestClient):
    _register_and_login(client)
    response = client.post("/api/auth/login", json={"email": "user@example.com", "password": "password123"})
    data = response.json()
    assert "isActive" in data
    assert "createdAt" in data
    assert "is_active" not in data


def test_login_does_not_expose_access_token_in_body(client: TestClient):
    _register_and_login(client)
    response = client.post("/api/auth/login", json={"email": "user@example.com", "password": "password123"})
    data = response.json()
    assert "accessToken" not in data
    assert "access_token" not in data


# --- /me endpoint ---

def test_get_me_without_cookie_returns_401(client: TestClient):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_get_me_with_valid_cookie_returns_user(client: TestClient):
    _register_and_login(client)
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "user@example.com"
    assert data["role"] == "admin"
    assert "isActive" in data


def test_get_me_returns_camel_case(client: TestClient):
    _register_and_login(client)
    response = client.get("/api/auth/me")
    data = response.json()
    assert "isActive" in data
    assert "createdAt" in data


# --- Logout endpoint ---

def test_logout_returns_200(client: TestClient):
    _register_and_login(client)
    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    assert "Đã đăng xuất thành công" in response.json()["message"]


def test_logout_clears_cookie(client: TestClient):
    _register_and_login(client)
    logout_response = client.post("/api/auth/logout")
    # Header Set-Cookie của logout phải xóa cookie qua Max-Age=0
    set_cookie = logout_response.headers["set-cookie"].lower()
    assert "access_token=" in set_cookie
    assert "max-age=0" in set_cookie
    # After logout, /me should return 401
    response = client.get("/api/auth/me")
    assert response.status_code == 401
