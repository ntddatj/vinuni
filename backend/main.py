from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from backend.src.modules.admin.infrastructure.settings_orm import SystemSettingORM  # noqa: F401
from backend.src.modules.admin.presentation.router import router as admin_router
from backend.src.modules.identity.infrastructure.orm_models import UserCredentialORM, UserORM  # noqa: F401
from backend.src.modules.identity.presentation.router import router as identity_router
from backend.src.modules.ingestion.infrastructure.chunk_orm_models import (  # noqa: F401
    ChildChunkORM,
    ParentChunkORM,
)
from backend.src.modules.ingestion.infrastructure.orm_models import PaperORM, UploadedFileORM  # noqa: F401
from backend.src.modules.ingestion.presentation.router import router as ingestion_router
from backend.src.modules.orchestrator.infrastructure.orm_models import ChatMessageORM, ChatThreadORM  # noqa: F401
from backend.src.modules.orchestrator.infrastructure.postgres_checkpointer import (
    close_postgres_checkpointer,
    setup_postgres_checkpointer,
)
from backend.src.modules.orchestrator.presentation.router import router as orchestrator_router
from backend.src.modules.search.presentation.router import router as search_router
from backend.src.modules.workspace.infrastructure.orm_models import ProjectORM, SyncOutboxORM  # noqa: F401
from backend.src.modules.workspace.presentation.router import router as workspace_router
from backend.src.shared.api.error_handlers import register_error_handlers
from backend.src.shared.infra.database import Base, engine
from backend.src.shared.infra.settings import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience: auto-create tables if they don't exist.
    # Production uses Alembic migrations explicitly.
    async with engine.begin() as conn:
        # pgvector extension phải tồn tại TRƯỚC create_all, vì child_chunks có cột Vector(768).
        # (Migration 006 tạo extension này; đường dev create_all phải tự lo để không vỡ startup.)
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    await setup_postgres_checkpointer()
    yield
    await close_postgres_checkpointer()
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    description="AI Literature Review Assistant — Backend API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router, prefix="/api")
app.include_router(identity_router, prefix="/api")
app.include_router(workspace_router, prefix="/api")
app.include_router(search_router, prefix="/api")
app.include_router(ingestion_router, prefix="/api")
app.include_router(orchestrator_router, prefix="/api")
register_error_handlers(app)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "env": settings.app_env}
