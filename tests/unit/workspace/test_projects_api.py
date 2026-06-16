"""Integration tests for /api/projects endpoints using SQLite in-memory DB."""
import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.src.modules.identity.infrastructure.dependencies import get_user_repository
from backend.src.modules.identity.infrastructure.postgres_repository import PostgresUserRepository
from backend.src.modules.identity.infrastructure.auth_dependencies import get_current_user
from backend.src.modules.identity.presentation.router import router as identity_router
from backend.src.modules.workspace.infrastructure.dependencies import get_project_repository
from backend.src.modules.workspace.infrastructure.orm_models import SyncOutboxORM
from backend.src.modules.workspace.infrastructure.postgres_repository import PostgresProjectRepository
from backend.src.modules.workspace.presentation.router import router as workspace_router
from backend.src.shared.infra.database import Base, get_db_session

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


def make_client():
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

    async def override_get_project_repository():
        async with test_async_session() as session:
            yield PostgresProjectRepository(session)

    async def create_tables():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(create_tables())

    test_app = FastAPI()
    test_app.include_router(identity_router, prefix="/api")
    test_app.include_router(workspace_router, prefix="/api")
    test_app.dependency_overrides[get_db_session] = override_get_db
    test_app.dependency_overrides[get_user_repository] = override_get_user_repository
    test_app.dependency_overrides[get_project_repository] = override_get_project_repository

    return TestClient(test_app, raise_server_exceptions=True)


def make_client_with_session():
    """Returns (TestClient context manager, async_sessionmaker) for tests needing DB access."""
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

    async def override_get_project_repository():
        async with test_async_session() as session:
            yield PostgresProjectRepository(session)

    async def create_tables():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(create_tables())

    test_app = FastAPI()
    test_app.include_router(identity_router, prefix="/api")
    test_app.include_router(workspace_router, prefix="/api")
    test_app.dependency_overrides[get_db_session] = override_get_db
    test_app.dependency_overrides[get_user_repository] = override_get_user_repository
    test_app.dependency_overrides[get_project_repository] = override_get_project_repository

    return TestClient(test_app, raise_server_exceptions=True), test_async_session


@pytest.fixture
def client():
    with make_client() as c:
        yield c


def _register_and_login(client: TestClient, email: str, password: str = "password123"):
    client.post("/api/auth/register", json={"email": email, "password": password})
    client.post("/api/auth/login", json={"email": email, "password": password})


# ── AC#1: POST /api/projects ──────────────────────────────────────────────────

def test_create_project_authenticated_returns_201(client: TestClient):
    _register_and_login(client, "user@example.com")
    response = client.post("/api/projects", json={"name": "Nghiên cứu NLP"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Nghiên cứu NLP"
    assert "id" in data
    assert "userId" in data
    assert "createdAt" in data
    assert "updatedAt" in data


def test_create_project_stores_user_id(client: TestClient):
    client.post("/api/auth/register", json={"email": "owner@example.com", "password": "password123"})
    login_res = client.post("/api/auth/login", json={"email": "owner@example.com", "password": "password123"})
    me_res = client.get("/api/auth/me")
    user_id = me_res.json()["id"]

    response = client.post("/api/projects", json={"name": "My Project"})
    assert response.status_code == 201
    assert response.json()["userId"] == user_id


def test_create_project_camelcase_response(client: TestClient):
    _register_and_login(client, "camel@example.com")
    response = client.post("/api/projects", json={"name": "Test"})
    data = response.json()
    assert "userId" in data
    assert "createdAt" in data
    assert "updatedAt" in data
    assert "isDeleted" in data
    assert "user_id" not in data


# ── AC#2: GET /api/projects ───────────────────────────────────────────────────

def test_list_projects_returns_only_own_projects(client: TestClient):
    # User A creates a project
    client.post("/api/auth/register", json={"email": "userA@example.com", "password": "password123"})
    client.post("/api/auth/login", json={"email": "userA@example.com", "password": "password123"})
    client.post("/api/projects", json={"name": "Project A"})

    # User B registers, logs in, and should NOT see user A's project
    client.post("/api/auth/register", json={"email": "userB@example.com", "password": "password123"})
    client.post("/api/auth/login", json={"email": "userB@example.com", "password": "password123"})
    client.post("/api/projects", json={"name": "Project B"})

    response = client.get("/api/projects")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data and "total" in data
    names = [p["name"] for p in data["items"]]
    assert "Project B" in names
    assert "Project A" not in names


def test_list_projects_sorted_by_updated_at_desc(client: TestClient):
    _register_and_login(client, "sort@example.com")
    client.post("/api/projects", json={"name": "First"})
    client.post("/api/projects", json={"name": "Second"})
    client.post("/api/projects", json={"name": "Third"})

    response = client.get("/api/projects")
    assert response.status_code == 200
    data = response.json()
    names = [p["name"] for p in data["items"]]
    assert names[0] == "Third"


def test_list_projects_pagination_envelope(client: TestClient):
    _register_and_login(client, "envelope@example.com")
    for i in range(3):
        client.post("/api/projects", json={"name": f"Project {i}"})

    response = client.get("/api/projects?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2


def test_list_projects_name_filter(client: TestClient):
    _register_and_login(client, "filter@example.com")
    client.post("/api/projects", json={"name": "Machine Learning"})
    client.post("/api/projects", json={"name": "Natural Language"})

    response = client.get("/api/projects?name=Machine")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Machine Learning"


# ── AC#3: PATCH /api/projects/{id} ───────────────────────────────────────────

def test_update_project_returns_updated_data(client: TestClient):
    _register_and_login(client, "update@example.com")
    create_res = client.post("/api/projects", json={"name": "Original"})
    project_id = create_res.json()["id"]

    response = client.patch(f"/api/projects/{project_id}", json={"name": "Updated"})
    assert response.status_code == 200
    assert response.json()["name"] == "Updated"


def test_update_project_other_user_returns_403(client: TestClient):
    client.post("/api/auth/register", json={"email": "ownerA@example.com", "password": "password123"})
    client.post("/api/auth/login", json={"email": "ownerA@example.com", "password": "password123"})
    create_res = client.post("/api/projects", json={"name": "A's Project"})
    project_id = create_res.json()["id"]

    client.post("/api/auth/register", json={"email": "intruder@example.com", "password": "password123"})
    client.post("/api/auth/login", json={"email": "intruder@example.com", "password": "password123"})
    response = client.patch(f"/api/projects/{project_id}", json={"name": "Hacked"})
    assert response.status_code == 403


# ── AC#4: DELETE /api/projects/{id} ──────────────────────────────────────────

def test_delete_project_returns_204(client: TestClient):
    _register_and_login(client, "delete@example.com")
    create_res = client.post("/api/projects", json={"name": "To Delete"})
    project_id = create_res.json()["id"]

    response = client.delete(f"/api/projects/{project_id}")
    assert response.status_code == 204


def test_delete_project_soft_deletes_and_not_in_list(client: TestClient):
    _register_and_login(client, "softdel@example.com")
    create_res = client.post("/api/projects", json={"name": "Will be deleted"})
    project_id = create_res.json()["id"]

    client.delete(f"/api/projects/{project_id}")

    list_res = client.get("/api/projects")
    ids = [p["id"] for p in list_res.json()["items"]]
    assert project_id not in ids


def test_delete_project_other_user_returns_403(client: TestClient):
    client.post("/api/auth/register", json={"email": "ownerDel@example.com", "password": "password123"})
    client.post("/api/auth/login", json={"email": "ownerDel@example.com", "password": "password123"})
    create_res = client.post("/api/projects", json={"name": "Owner's project"})
    project_id = create_res.json()["id"]

    client.post("/api/auth/register", json={"email": "intruder2@example.com", "password": "password123"})
    client.post("/api/auth/login", json={"email": "intruder2@example.com", "password": "password123"})
    response = client.delete(f"/api/projects/{project_id}")
    assert response.status_code == 403


# ── AC#5: Unauthenticated → 401 ──────────────────────────────────────────────

def test_unauthenticated_create_returns_401(client: TestClient):
    response = client.post("/api/projects", json={"name": "No auth"})
    assert response.status_code == 401


def test_unauthenticated_list_returns_401(client: TestClient):
    response = client.get("/api/projects")
    assert response.status_code == 401


def test_unauthenticated_delete_returns_401(client: TestClient):
    response = client.delete("/api/projects/some-id")
    assert response.status_code == 401


# ── AC#4 ARCH-2: DELETE writes sync_outbox in same transaction ────────────────

def test_delete_project_writes_sync_outbox_event():
    test_client, session_maker = make_client_with_session()
    with test_client as client:
        _register_and_login(client, "outbox@example.com")
        create_res = client.post("/api/projects", json={"name": "Outbox Test"})
        project_id = create_res.json()["id"]

        del_res = client.delete(f"/api/projects/{project_id}")
        assert del_res.status_code == 204

        async def query_outbox():
            async with session_maker() as session:
                result = await session.execute(
                    select(SyncOutboxORM).where(SyncOutboxORM.event_type == "PROJECT_DELETED")
                )
                return result.scalars().all()

        rows = asyncio.run(query_outbox())
        assert len(rows) == 1
        assert rows[0].event_type == "PROJECT_DELETED"
        assert rows[0].payload["project_id"] == project_id
        assert rows[0].processed is False
