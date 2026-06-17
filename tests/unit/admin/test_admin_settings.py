"""Unit tests cho admin settings API (AC #3, #4, #5)."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.src.modules.admin.presentation.router import require_admin
from backend.src.modules.identity.domain.entities import User


def _make_user(role: str = "user") -> User:
    return User(id="user-id", email="test@test.com", hashed_password="hashed", role=role)


def test_require_admin_raises_403_for_regular_user():
    """require_admin phải raise 403 cho user thường."""
    user = _make_user(role="user")
    with pytest.raises(HTTPException) as exc_info:
        require_admin(current_user=user)
    assert exc_info.value.status_code == 403


def test_require_admin_passes_for_admin():
    """require_admin trả về user nếu là admin."""
    user = _make_user(role="admin")
    result = require_admin(current_user=user)
    assert result is user


@pytest.mark.asyncio
async def test_get_settings_returns_list():
    """GET /admin/settings trả về danh sách settings."""
    from backend.src.modules.admin.presentation.router import get_settings

    mock_db = AsyncMock()
    mock_settings = [
        MagicMock(key="MAX_PAPERS_PER_PROJECT", value="15"),
        MagicMock(key="BROAD_QUERY_THRESHOLD", value="50"),
    ]

    with patch(
        "backend.src.modules.admin.presentation.router.list_settings",
        new_callable=AsyncMock,
        return_value=mock_settings,
    ):
        admin_user = _make_user(role="admin")
        result = await get_settings(_=admin_user, db=mock_db)
        assert result == mock_settings


@pytest.mark.asyncio
async def test_update_setting_saves_new_value():
    """PUT /admin/settings/{key} cập nhật giá trị trong DB."""
    from backend.src.modules.admin.presentation.router import update_setting
    from backend.src.modules.admin.presentation.schemas import UpdateSettingRequest

    mock_db = AsyncMock()
    updated_row = MagicMock(key="MAX_PAPERS_PER_PROJECT", value="20")

    with patch(
        "backend.src.modules.admin.presentation.router.upsert_setting",
        new_callable=AsyncMock,
        return_value=updated_row,
    ):
        admin_user = _make_user(role="admin")
        body = UpdateSettingRequest(value="20")
        result = await update_setting(
            key="MAX_PAPERS_PER_PROJECT",
            body=body,
            _=admin_user,
            db=mock_db,
        )
        assert result == updated_row
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(updated_row)
