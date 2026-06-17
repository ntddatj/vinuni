"""Unit tests cho chat thread use cases (AC #1–#4)."""
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from backend.src.modules.orchestrator.application.dtos import CreateThreadDTO, GetThreadMessagesDTO
from backend.src.modules.orchestrator.application.use_cases import (
    CreateThreadUseCase,
    GetThreadMessagesUseCase,
)
from backend.src.modules.orchestrator.domain.entities import ChatThread
from backend.src.modules.orchestrator.domain.exceptions import ThreadAccessDeniedError, ThreadNotFoundError
from backend.src.modules.workspace.domain.entities import Project
from backend.src.modules.workspace.domain.exceptions import ProjectAccessDeniedError, ProjectNotFoundError


def _make_thread(user_id: str = "user-1", project_id: str = "proj-1") -> ChatThread:
    now = datetime.now(UTC)
    return ChatThread(id="thread-1", user_id=user_id, project_id=project_id,
                      title="Test", created_at=now, updated_at=now)


def _make_project(user_id: str = "user-1", is_deleted: bool = False) -> Project:
    now = datetime.now(UTC)
    return Project(id="proj-1", user_id=user_id, name="P", description=None,
                   is_deleted=is_deleted, created_at=now, updated_at=now)


def _project_repo(project: Project | None) -> AsyncMock:
    repo = AsyncMock()
    repo.find_by_id.return_value = project
    return repo


@pytest.mark.asyncio
async def test_create_thread_success():
    """CreateThreadUseCase tạo thread thành công khi user sở hữu project."""
    repo = AsyncMock()
    thread = _make_thread()
    repo.create.return_value = thread
    use_case = CreateThreadUseCase(repo, _project_repo(_make_project(user_id="user-1")))
    result = await use_case.execute(CreateThreadDTO(user_id="user-1", project_id="proj-1"))
    repo.create.assert_called_once_with(user_id="user-1", project_id="proj-1", title="Cuộc trò chuyện mới")
    assert result.id == "thread-1"


@pytest.mark.asyncio
async def test_create_thread_raises_not_found_for_missing_project():
    """CreateThreadUseCase raise ProjectNotFoundError khi project không tồn tại/đã xóa mềm."""
    repo = AsyncMock()
    use_case = CreateThreadUseCase(repo, _project_repo(None))
    with pytest.raises(ProjectNotFoundError):
        await use_case.execute(CreateThreadDTO(user_id="user-1", project_id="ghost"))
    repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_create_thread_raises_access_denied_for_other_users_project():
    """CreateThreadUseCase raise ProjectAccessDeniedError khi project thuộc user khác."""
    repo = AsyncMock()
    use_case = CreateThreadUseCase(repo, _project_repo(_make_project(user_id="owner-99")))
    with pytest.raises(ProjectAccessDeniedError):
        await use_case.execute(CreateThreadDTO(user_id="user-1", project_id="proj-1"))
    repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_get_messages_raises_not_found():
    """GetThreadMessagesUseCase raise ThreadNotFoundError khi thread không tồn tại."""
    repo = AsyncMock()
    repo.find_by_id.return_value = None
    use_case = GetThreadMessagesUseCase(repo)
    with pytest.raises(ThreadNotFoundError):
        await use_case.execute(GetThreadMessagesDTO(thread_id="ghost", requesting_user_id="user-1"))


@pytest.mark.asyncio
async def test_get_messages_raises_access_denied_for_other_user():
    """GetThreadMessagesUseCase raise ThreadAccessDeniedError khi user không sở hữu thread."""
    repo = AsyncMock()
    repo.find_by_id.return_value = _make_thread(user_id="owner-99")
    use_case = GetThreadMessagesUseCase(repo)
    with pytest.raises(ThreadAccessDeniedError):
        await use_case.execute(GetThreadMessagesDTO(thread_id="thread-1", requesting_user_id="other-user"))


@pytest.mark.asyncio
async def test_get_messages_returns_empty_list():
    """GetThreadMessagesUseCase trả về list rỗng khi không có tin nhắn."""
    repo = AsyncMock()
    repo.find_by_id.return_value = _make_thread(user_id="user-1")
    repo.list_messages.return_value = []
    use_case = GetThreadMessagesUseCase(repo)
    result = await use_case.execute(GetThreadMessagesDTO(thread_id="thread-1", requesting_user_id="user-1"))
    assert result == []
