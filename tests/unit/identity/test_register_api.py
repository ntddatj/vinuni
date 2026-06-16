"""Integration tests for POST /api/auth/register endpoint using TestClient."""
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

    # Minimal test app — no lifespan, just the router under test
    test_app = FastAPI()
    test_app.include_router(identity_router, prefix="/api")
    test_app.dependency_overrides[get_db_session] = override_get_db
    test_app.dependency_overrides[get_user_repository] = override_get_user_repository

    with TestClient(test_app, raise_server_exceptions=True) as c:
        yield c


def test_register_first_user_returns_admin(client: TestClient):
    response = client.post(
        "/api/auth/register",
        json={"email": "admin@example.com", "password": "strongpass123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "admin@example.com"
    assert data["role"] == "admin"
    assert data["isActive"] is True
    assert "id" in data
    assert "createdAt" in data


def test_register_second_user_returns_user_role(client: TestClient):
    client.post("/api/auth/register", json={"email": "first@example.com", "password": "password1"})
    response = client.post(
        "/api/auth/register",
        json={"email": "second@example.com", "password": "password2"},
    )
    assert response.status_code == 201
    assert response.json()["role"] == "user"


def test_register_duplicate_email_returns_400(client: TestClient):
    client.post("/api/auth/register", json={"email": "dup@example.com", "password": "password1"})
    response = client.post(
        "/api/auth/register",
        json={"email": "dup@example.com", "password": "password2"},
    )
    assert response.status_code == 400
    assert "đã tồn tại" in response.json()["detail"]


def test_register_invalid_email_returns_422(client: TestClient):
    response = client.post(
        "/api/auth/register",
        json={"email": "not-an-email", "password": "password1"},
    )
    assert response.status_code == 422


def test_register_short_password_returns_422(client: TestClient):
    response = client.post(
        "/api/auth/register",
        json={"email": "user@example.com", "password": "short"},
    )
    assert response.status_code == 422


def test_response_uses_camel_case(client: TestClient):
    response = client.post(
        "/api/auth/register",
        json={"email": "camel@example.com", "password": "password123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "isActive" in data
    assert "createdAt" in data
    assert "updatedAt" in data
    assert "is_active" not in data
    assert "created_at" not in data


def test_email_normalized_to_lowercase(client: TestClient):
    response = client.post(
        "/api/auth/register",
        json={"email": "User@Example.COM", "password": "password123"},
    )
    assert response.status_code == 201
    assert response.json()["email"] == "user@example.com"
