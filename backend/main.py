from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.src.modules.identity.infrastructure.orm_models import UserCredentialORM, UserORM  # noqa: F401
from backend.src.modules.identity.presentation.router import router as identity_router
from backend.src.modules.workspace.infrastructure.orm_models import ProjectORM, SyncOutboxORM  # noqa: F401
from backend.src.modules.search.presentation.router import router as search_router
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
        await conn.run_sync(Base.metadata.create_all)
    yield
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

app.include_router(identity_router, prefix="/api")
app.include_router(workspace_router, prefix="/api")
app.include_router(search_router, prefix="/api")
register_error_handlers(app)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "env": settings.app_env}
