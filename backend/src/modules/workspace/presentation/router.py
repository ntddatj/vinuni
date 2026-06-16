from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.src.modules.identity.domain.entities import User
from backend.src.modules.identity.infrastructure.auth_dependencies import get_current_user
from backend.src.modules.workspace.application.dtos import CreateProjectDTO, UpdateProjectDTO
from backend.src.modules.workspace.application.use_cases import (
    CreateProjectUseCase,
    DeleteProjectUseCase,
    GetProjectUseCase,
    ListProjectsUseCase,
    UpdateProjectUseCase,
)
from backend.src.modules.workspace.domain.exceptions import ProjectAccessDeniedError, ProjectNotFoundError
from backend.src.modules.workspace.domain.repositories import ProjectRepository
from backend.src.modules.workspace.infrastructure.dependencies import get_project_repository
from backend.src.modules.workspace.presentation.schemas import (
    CreateProjectRequest,
    ProjectResponse,
    ProjectsListResponse,
    UpdateProjectRequest,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    request: CreateProjectRequest,
    current_user: User = Depends(get_current_user),
    repo: ProjectRepository = Depends(get_project_repository),
) -> ProjectResponse:
    use_case = CreateProjectUseCase(repo)
    result = await use_case.execute(
        CreateProjectDTO(user_id=current_user.id, name=request.name, description=request.description)
    )
    return ProjectResponse.model_validate(result, from_attributes=True)


@router.get("", response_model=ProjectsListResponse)
async def list_projects(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    name: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    repo: ProjectRepository = Depends(get_project_repository),
) -> ProjectsListResponse:
    use_case = ListProjectsUseCase(repo)
    results = await use_case.execute(user_id=current_user.id, limit=limit, offset=offset, name=name)
    total = await use_case.count(user_id=current_user.id, name=name)
    items = [ProjectResponse.model_validate(p, from_attributes=True) for p in results]
    return ProjectsListResponse(items=items, total=total)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    repo: ProjectRepository = Depends(get_project_repository),
) -> ProjectResponse:
    use_case = GetProjectUseCase(repo)
    try:
        result = await use_case.execute(project_id=project_id, requesting_user_id=current_user.id)
    except ProjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dự án không tồn tại")
    except ProjectAccessDeniedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền truy cập")
    return ProjectResponse.model_validate(result, from_attributes=True)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    request: UpdateProjectRequest,
    current_user: User = Depends(get_current_user),
    repo: ProjectRepository = Depends(get_project_repository),
) -> ProjectResponse:
    use_case = UpdateProjectUseCase(repo)
    try:
        result = await use_case.execute(
            UpdateProjectDTO(
                project_id=project_id,
                user_id=current_user.id,
                name=request.name,
                description=request.description,
            )
        )
    except ProjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dự án không tồn tại")
    except ProjectAccessDeniedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền truy cập")
    return ProjectResponse.model_validate(result, from_attributes=True)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    repo: ProjectRepository = Depends(get_project_repository),
) -> None:
    use_case = DeleteProjectUseCase(repo)
    try:
        await use_case.execute(project_id=project_id, requesting_user_id=current_user.id)
    except ProjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dự án không tồn tại")
    except ProjectAccessDeniedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền truy cập")
