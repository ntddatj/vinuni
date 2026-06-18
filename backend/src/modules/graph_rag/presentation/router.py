"""Graph RAG read API router — 3 endpoints: graph, expand, sync-status."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.modules.graph_rag.application.use_cases import GraphReadUseCase
from backend.src.modules.graph_rag.presentation.schemas import (
    GraphResponse,
    NodeResponse,
    EdgeResponse,
    SyncStatusResponse,
)
from backend.src.modules.identity.domain.entities import User
from backend.src.modules.identity.infrastructure.auth_dependencies import get_current_user
from backend.src.modules.workspace.domain.repositories import ProjectRepository
from backend.src.modules.workspace.infrastructure.dependencies import get_project_repository
from backend.src.modules.workspace.infrastructure.orm_models import SyncOutboxORM
from backend.src.shared.infra.database import get_db_session
from backend.src.shared.infra.neo4j_client import get_neo4j_driver

router = APIRouter(prefix="/projects", tags=["graph"])


async def _get_project_or_404(
    project_id: str,
    current_user: User,
    repo: ProjectRepository,
):
    """Verify project exists và thuộc user hiện tại, raise 404 nếu không."""
    project = await repo.find_by_id(project_id)
    if project is None or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dự án không tồn tại")
    return project


@router.get("/{project_id}/graph", response_model=GraphResponse)
async def get_graph(
    project_id: str,
    current_user: User = Depends(get_current_user),
    repo: ProjectRepository = Depends(get_project_repository),
) -> GraphResponse:
    await _get_project_or_404(project_id, current_user, repo)
    driver = await get_neo4j_driver()
    use_case = GraphReadUseCase(driver)
    graph_data = await use_case.get_graph(project_id)
    return GraphResponse(
        nodes=[NodeResponse(**node.__dict__) for node in graph_data.nodes],
        edges=[EdgeResponse(**edge.__dict__) for edge in graph_data.edges],
        has_more=graph_data.has_more,
    )


@router.get("/{project_id}/graph/nodes/{node_id}/expand", response_model=GraphResponse)
async def expand_node(
    project_id: str,
    node_id: str,
    existing_ids: str = Query("", description="Comma-separated list of existing node IDs"),
    current_user: User = Depends(get_current_user),
    repo: ProjectRepository = Depends(get_project_repository),
) -> GraphResponse:
    await _get_project_or_404(project_id, current_user, repo)
    parsed_ids = [x for x in existing_ids.split(",") if x.strip()] if existing_ids else []
    driver = await get_neo4j_driver()
    use_case = GraphReadUseCase(driver)
    graph_data = await use_case.expand_node(project_id, node_id, parsed_ids)
    return GraphResponse(
        nodes=[NodeResponse(**node.__dict__) for node in graph_data.nodes],
        edges=[EdgeResponse(**edge.__dict__) for edge in graph_data.edges],
        has_more=graph_data.has_more,
    )


@router.get("/{project_id}/graph/sync-status", response_model=SyncStatusResponse)
async def get_sync_status(
    project_id: str,
    current_user: User = Depends(get_current_user),
    repo: ProjectRepository = Depends(get_project_repository),
    db: AsyncSession = Depends(get_db_session),
) -> SyncStatusResponse:
    await _get_project_or_404(project_id, current_user, repo)
    result = await db.execute(
        select(func.count()).select_from(SyncOutboxORM).where(
            SyncOutboxORM.project_id == project_id,
            SyncOutboxORM.processed.is_(False),
            SyncOutboxORM.dead_lettered.is_(False),
        )
    )
    count = result.scalar_one()
    return SyncStatusResponse(syncing=count > 0)
