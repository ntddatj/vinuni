from datetime import datetime, timezone

from backend.src.modules.workspace.application.dtos import CreateProjectDTO, UpdateProjectDTO
from backend.src.modules.workspace.domain.entities import Project
from backend.src.modules.workspace.domain.exceptions import ProjectAccessDeniedError, ProjectNotFoundError
from backend.src.modules.workspace.domain.repositories import ProjectRepository


class CreateProjectUseCase:
    def __init__(self, repo: ProjectRepository) -> None:
        self._repo = repo

    async def execute(self, dto: CreateProjectDTO) -> Project:
        project = Project.create(
            user_id=dto.user_id,
            name=dto.name,
            description=dto.description,
        )
        return await self._repo.save(project)


class ListProjectsUseCase:
    def __init__(self, repo: ProjectRepository) -> None:
        self._repo = repo

    async def execute(self, user_id: str, limit: int = 10, offset: int = 0, name: str | None = None) -> list[Project]:
        return await self._repo.list_by_user(user_id, limit=limit, offset=offset, name=name)

    async def count(self, user_id: str, name: str | None = None) -> int:
        return await self._repo.count_by_user(user_id, name=name)


class GetProjectUseCase:
    def __init__(self, repo: ProjectRepository) -> None:
        self._repo = repo

    async def execute(self, project_id: str, requesting_user_id: str) -> Project:
        project = await self._repo.find_by_id(project_id)
        if not project:
            raise ProjectNotFoundError(f"Project {project_id} not found")
        if project.user_id != requesting_user_id:
            raise ProjectAccessDeniedError("Access denied")
        return project


class UpdateProjectUseCase:
    def __init__(self, repo: ProjectRepository) -> None:
        self._repo = repo

    async def execute(self, dto: UpdateProjectDTO) -> Project:
        project = await self._repo.find_by_id(dto.project_id)
        if not project:
            raise ProjectNotFoundError(f"Project {dto.project_id} not found")
        if project.user_id != dto.user_id:
            raise ProjectAccessDeniedError("Access denied")

        if dto.name is not None:
            project.name = dto.name
        if dto.description is not None:
            project.description = dto.description
        project.updated_at = datetime.now(timezone.utc)

        return await self._repo.update(project)


class DeleteProjectUseCase:
    def __init__(self, repo: ProjectRepository) -> None:
        self._repo = repo

    async def execute(self, project_id: str, requesting_user_id: str) -> None:
        project = await self._repo.find_by_id(project_id)
        if not project:
            raise ProjectNotFoundError(f"Project {project_id} not found")
        if project.user_id != requesting_user_id:
            raise ProjectAccessDeniedError("Access denied")
        await self._repo.soft_delete(project)
