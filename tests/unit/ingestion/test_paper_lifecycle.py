"""Unit tests cho paper lifecycle — xóa, sửa metadata, file serve (AC #1-#5)."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_paper_orm(
    paper_id: str = "paper-1",
    project_id: str = "proj-1",
    user_id: str = "user-1",
    is_deleted: bool = False,
    file_path: str | None = None,
):
    paper = MagicMock()
    paper.id = paper_id
    paper.project_id = project_id
    paper.user_id = user_id
    paper.is_deleted = is_deleted
    paper.file_path = file_path
    paper.title = "Test Paper"
    paper.authors = ["Author A"]
    paper.abstract = "Abstract text"
    paper.year = 2024
    paper.updated_at = MagicMock()
    return paper


def _make_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    return db


# ---------------------------------------------------------------------------
# Repository function tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_paper_soft_success():
    """delete_paper_soft trả True, xóa chunks, ghi sync_outbox khi paper tồn tại."""
    from backend.src.modules.ingestion.infrastructure.postgres_repository import delete_paper_soft

    db = _make_db()
    paper = _make_paper_orm()

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = paper
    db.execute = AsyncMock(return_value=result_mock)
    db.commit = AsyncMock()

    with patch(
        "backend.src.modules.ingestion.infrastructure.postgres_repository.SyncOutboxORM"
    ) as MockOutbox:
        mock_outbox_instance = MagicMock()
        MockOutbox.return_value = mock_outbox_instance

        success = await delete_paper_soft(db, "paper-1", "proj-1", "user-1")

    assert success is True
    assert paper.is_deleted is True
    db.add.assert_called_once_with(mock_outbox_instance)
    db.commit.assert_awaited_once()
    # Phải gọi execute ít nhất 3 lần: 1 SELECT + 2 DELETE (child + parent chunks)
    assert db.execute.await_count >= 3


@pytest.mark.asyncio
async def test_delete_paper_soft_not_found_returns_false():
    """delete_paper_soft trả False khi paper không tồn tại hoặc không có quyền."""
    from backend.src.modules.ingestion.infrastructure.postgres_repository import delete_paper_soft

    db = _make_db()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)

    success = await delete_paper_soft(db, "paper-X", "proj-1", "user-1")

    assert success is False
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_paper_metadata_success():
    """update_paper_metadata cập nhật fields và trả PaperORM."""
    from backend.src.modules.ingestion.infrastructure.postgres_repository import update_paper_metadata

    db = _make_db()
    paper = _make_paper_orm()

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = paper
    db.execute = AsyncMock(return_value=result_mock)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    updated = await update_paper_metadata(
        db, "paper-1", "proj-1", "user-1",
        title="New Title", authors=["Author B"], abstract=None, year=2025,
    )

    assert updated is paper
    assert paper.title == "New Title"
    assert paper.authors == ["Author B"]
    assert paper.year == 2025
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(paper)


@pytest.mark.asyncio
async def test_update_paper_metadata_not_found_returns_none():
    """update_paper_metadata trả None khi paper không tìm thấy."""
    from backend.src.modules.ingestion.infrastructure.postgres_repository import update_paper_metadata

    db = _make_db()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)

    result = await update_paper_metadata(
        db, "paper-X", "proj-1", "user-1",
        title="Title", authors=None, abstract=None, year=None,
    )

    assert result is None
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_paper_metadata_none_year_not_overwritten():
    """Không truyền year (None) thì year của paper không bị xóa."""
    from backend.src.modules.ingestion.infrastructure.postgres_repository import update_paper_metadata

    db = _make_db()
    paper = _make_paper_orm()
    paper.year = 2020

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = paper
    db.execute = AsyncMock(return_value=result_mock)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    await update_paper_metadata(
        db, "paper-1", "proj-1", "user-1",
        title="New Title", authors=None, abstract=None, year=None,
    )

    assert paper.year == 2020  # không bị ghi đè


@pytest.mark.asyncio
async def test_find_paper_for_file_serve_returns_paper():
    """find_paper_for_file_serve trả paper khi tìm thấy và chưa xóa."""
    from backend.src.modules.ingestion.infrastructure.postgres_repository import find_paper_for_file_serve

    db = _make_db()
    paper = _make_paper_orm(file_path="/data/papers/user-1/paper-1.pdf")

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = paper
    db.execute = AsyncMock(return_value=result_mock)

    result = await find_paper_for_file_serve(db, "paper-1", "proj-1", "user-1")

    assert result is paper


@pytest.mark.asyncio
async def test_find_paper_for_file_serve_deleted_returns_none():
    """find_paper_for_file_serve trả None khi paper đã bị xóa (is_deleted filter)."""
    from backend.src.modules.ingestion.infrastructure.postgres_repository import find_paper_for_file_serve

    db = _make_db()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None  # is_deleted filter loại ra
    db.execute = AsyncMock(return_value=result_mock)

    result = await find_paper_for_file_serve(db, "paper-1", "proj-1", "user-1")

    assert result is None


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_paper_endpoint_returns_200():
    """DELETE /projects/{project_id}/papers/{paper_id} trả 200 khi xóa thành công."""
    from fastapi import HTTPException

    from backend.src.modules.ingestion.presentation.router import delete_paper

    db = AsyncMock()
    user = MagicMock()
    user.id = "user-1"

    with (
        patch(
            "backend.src.modules.ingestion.presentation.router.is_project_owned_by_user",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "backend.src.modules.ingestion.presentation.router.delete_paper_soft",
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        result = await delete_paper("proj-1", "paper-1", current_user=user, db=db)

    assert result.message == "Tài liệu đã được xóa thành công"


@pytest.mark.asyncio
async def test_delete_paper_endpoint_returns_403_no_permission():
    """DELETE endpoint trả 403 khi user không có quyền truy cập dự án (IDOR)."""
    from fastapi import HTTPException

    from backend.src.modules.ingestion.presentation.router import delete_paper

    db = AsyncMock()
    user = MagicMock()
    user.id = "user-other"

    with patch(
        "backend.src.modules.ingestion.presentation.router.is_project_owned_by_user",
        new_callable=AsyncMock,
        return_value=False,
    ):
        with pytest.raises(HTTPException) as exc:
            await delete_paper("proj-1", "paper-1", current_user=user, db=db)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_delete_paper_endpoint_returns_404_not_found():
    """DELETE endpoint trả 404 khi paper không tồn tại."""
    from fastapi import HTTPException

    from backend.src.modules.ingestion.presentation.router import delete_paper

    db = AsyncMock()
    user = MagicMock()
    user.id = "user-1"

    with (
        patch(
            "backend.src.modules.ingestion.presentation.router.is_project_owned_by_user",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "backend.src.modules.ingestion.presentation.router.delete_paper_soft",
            new_callable=AsyncMock,
            return_value=False,
        ),
    ):
        with pytest.raises(HTTPException) as exc:
            await delete_paper("proj-1", "paper-X", current_user=user, db=db)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_patch_paper_metadata_endpoint_returns_200():
    """PATCH endpoint trả 200 với metadata mới khi update thành công."""
    from backend.src.modules.ingestion.presentation.router import patch_paper_metadata
    from backend.src.modules.ingestion.presentation.schemas import PatchPaperRequestSchema

    db = AsyncMock()
    user = MagicMock()
    user.id = "user-1"

    paper = _make_paper_orm()
    paper.title = "Updated Title"
    paper.authors = ["New Author"]
    paper.abstract = "Abstract text"
    paper.year = 2025

    body = PatchPaperRequestSchema(title="Updated Title", authors=["New Author"], year=2025)

    with (
        patch(
            "backend.src.modules.ingestion.presentation.router.is_project_owned_by_user",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "backend.src.modules.ingestion.presentation.router.update_paper_metadata",
            new_callable=AsyncMock,
            return_value=paper,
        ),
    ):
        result = await patch_paper_metadata("proj-1", "paper-1", body, current_user=user, db=db)

    assert result.id == "paper-1"
    assert result.title == "Updated Title"
    assert result.year == 2025


@pytest.mark.asyncio
async def test_serve_paper_file_endpoint_returns_404_when_no_file():
    """GET file endpoint trả 404 khi paper.file_path là None."""
    from fastapi import HTTPException

    from backend.src.modules.ingestion.presentation.router import serve_paper_file

    db = AsyncMock()
    user = MagicMock()
    user.id = "user-1"

    paper = _make_paper_orm(file_path=None)

    with (
        patch(
            "backend.src.modules.ingestion.presentation.router.is_project_owned_by_user",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "backend.src.modules.ingestion.presentation.router.find_paper_for_file_serve",
            new_callable=AsyncMock,
            return_value=paper,
        ),
    ):
        with pytest.raises(HTTPException) as exc:
            await serve_paper_file("proj-1", "paper-1", current_user=user, db=db)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_serve_paper_file_endpoint_returns_403_no_permission():
    """GET file endpoint trả 403 khi user không có quyền truy cập dự án (IDOR)."""
    from fastapi import HTTPException

    from backend.src.modules.ingestion.presentation.router import serve_paper_file

    db = AsyncMock()
    user = MagicMock()
    user.id = "user-other"

    with patch(
        "backend.src.modules.ingestion.presentation.router.is_project_owned_by_user",
        new_callable=AsyncMock,
        return_value=False,
    ):
        with pytest.raises(HTTPException) as exc:
            await serve_paper_file("proj-1", "paper-1", current_user=user, db=db)

    assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# Request validation tests (PatchPaperRequestSchema ràng buộc khớp DB)
# ---------------------------------------------------------------------------


def test_patch_request_schema_rejects_invalid_year():
    """year ngoài khoảng 1000–2100 bị từ chối ở tầng schema (422, không lọt xuống DB)."""
    from pydantic import ValidationError

    from backend.src.modules.ingestion.presentation.schemas import PatchPaperRequestSchema

    with pytest.raises(ValidationError):
        PatchPaperRequestSchema(year=999999999999)
    with pytest.raises(ValidationError):
        PatchPaperRequestSchema(year=-5)


def test_patch_request_schema_rejects_overlong_title():
    """title dài hơn 500 ký tự bị từ chối ở tầng schema (khớp String(500))."""
    from pydantic import ValidationError

    from backend.src.modules.ingestion.presentation.schemas import PatchPaperRequestSchema

    with pytest.raises(ValidationError):
        PatchPaperRequestSchema(title="x" * 501)

    # Hợp lệ: đúng 500 ký tự, year trong khoảng
    ok = PatchPaperRequestSchema(title="x" * 500, year=2024)
    assert ok.year == 2024
