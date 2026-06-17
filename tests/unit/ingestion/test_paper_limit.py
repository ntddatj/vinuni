"""Unit tests cho giới hạn tài liệu (AC #1, #2)."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.src.modules.ingestion.application.use_cases import (
    ConfirmMetadataUseCase,
    IngestFromSearchUseCase,
)
from backend.src.modules.ingestion.domain.entities import UploadedFile
from backend.src.modules.ingestion.domain.exceptions import ProjectPaperLimitExceededError


@pytest.fixture
def db():
    return AsyncMock()


def _make_uploaded_file(project_id: str = "proj-1") -> UploadedFile:
    return UploadedFile(
        id="file-id",
        project_id=project_id,
        user_id="user-1",
        original_filename="paper.pdf",
        file_path="/tmp/paper.pdf",
        mime_type="application/pdf",
        file_size=1024,
    )


@pytest.mark.asyncio
async def test_confirm_raises_limit_exceeded_when_at_limit(db):
    """ConfirmMetadataUseCase phải raise ProjectPaperLimitExceededError khi count >= limit."""
    use_case = ConfirmMetadataUseCase()

    with (
        patch(
            "backend.src.modules.ingestion.application.use_cases.PostgresUploadedFileRepository"
        ) as MockFileRepo,
        patch(
            "backend.src.modules.ingestion.application.use_cases.get_max_papers_limit",
            new_callable=AsyncMock,
            return_value=5,
        ),
        patch(
            "backend.src.modules.ingestion.application.use_cases.count_papers_by_project",
            new_callable=AsyncMock,
            return_value=5,
        ),
        patch(
            "backend.src.modules.ingestion.application.use_cases.get_redis",
            new_callable=AsyncMock,
        ) as mock_get_redis,
    ):
        mock_repo = AsyncMock()
        mock_repo.find_by_id.return_value = _make_uploaded_file()
        MockFileRepo.return_value = mock_repo

        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.delete = AsyncMock()
        mock_get_redis.return_value = mock_redis

        with pytest.raises(ProjectPaperLimitExceededError):
            await use_case.execute(
                file_id="file-id",
                title="Test paper",
                authors=["Author A"],
                abstract="Abstract",
                year=2024,
                project_id="proj-1",
                user_id="user-1",
                db=db,
            )


@pytest.mark.asyncio
async def test_confirm_proceeds_when_below_limit(db):
    """ConfirmMetadataUseCase tiếp tục bình thường khi count < limit."""
    use_case = ConfirmMetadataUseCase()

    with (
        patch(
            "backend.src.modules.ingestion.application.use_cases.PostgresUploadedFileRepository"
        ) as MockFileRepo,
        patch(
            "backend.src.modules.ingestion.application.use_cases.PostgresPaperRepository"
        ) as MockPaperRepo,
        patch(
            "backend.src.modules.ingestion.application.use_cases.get_max_papers_limit",
            new_callable=AsyncMock,
            return_value=15,
        ),
        patch(
            "backend.src.modules.ingestion.application.use_cases.count_papers_by_project",
            new_callable=AsyncMock,
            return_value=3,
        ),
        patch(
            "backend.src.modules.ingestion.application.use_cases.get_redis",
            new_callable=AsyncMock,
        ) as mock_get_redis,
        patch(
            "backend.src.modules.ingestion.application.use_cases.enqueue_ingestion_task",
            new_callable=AsyncMock,
        ),
    ):
        mock_file_repo = AsyncMock()
        mock_file_repo.find_by_id.return_value = _make_uploaded_file()
        MockFileRepo.return_value = mock_file_repo

        mock_paper = MagicMock()
        mock_paper.id = "saved-paper-id"
        mock_paper_repo = AsyncMock()
        mock_paper_repo.save_paper.return_value = mock_paper
        MockPaperRepo.return_value = mock_paper_repo

        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.delete = AsyncMock()
        mock_get_redis.return_value = mock_redis

        result = await use_case.execute(
            file_id="file-id",
            title="Test paper",
            authors=["Author A"],
            abstract="Abstract",
            year=2024,
            project_id="proj-1",
            user_id="user-1",
            db=db,
        )
        assert result["document_id"] == "saved-paper-id"


@pytest.mark.asyncio
async def test_ingest_from_search_raises_limit_exceeded(db):
    """IngestFromSearchUseCase phải raise ProjectPaperLimitExceededError khi count >= limit."""
    use_case = IngestFromSearchUseCase()

    with (
        patch(
            "backend.src.modules.ingestion.application.use_cases.is_project_owned_by_user",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "backend.src.modules.ingestion.application.use_cases.get_max_papers_limit",
            new_callable=AsyncMock,
            return_value=10,
        ),
        patch(
            "backend.src.modules.ingestion.application.use_cases.count_papers_by_project",
            new_callable=AsyncMock,
            return_value=10,
        ),
        patch(
            "backend.src.modules.ingestion.application.use_cases.get_redis",
            new_callable=AsyncMock,
        ) as mock_get_redis,
    ):
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.delete = AsyncMock()
        mock_get_redis.return_value = mock_redis

        with pytest.raises(ProjectPaperLimitExceededError):
            await use_case.execute(
                project_id="proj-1",
                user_id="user-1",
                title="Paper",
                authors=["Author"],
                abstract="Abstract",
                year=2024,
                doi=None,
                arxiv_id=None,
                url=None,
                pdf_url=None,
                source="arxiv",
                db=db,
            )


@pytest.mark.asyncio
async def test_ingest_from_search_proceeds_when_below_limit(db):
    """IngestFromSearchUseCase tiếp tục bình thường khi count < limit."""
    use_case = IngestFromSearchUseCase()

    with (
        patch(
            "backend.src.modules.ingestion.application.use_cases.is_project_owned_by_user",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "backend.src.modules.ingestion.application.use_cases.get_max_papers_limit",
            new_callable=AsyncMock,
            return_value=15,
        ),
        patch(
            "backend.src.modules.ingestion.application.use_cases.count_papers_by_project",
            new_callable=AsyncMock,
            return_value=0,
        ),
        patch(
            "backend.src.modules.ingestion.application.use_cases.get_redis",
            new_callable=AsyncMock,
        ) as mock_get_redis,
        patch(
            "backend.src.modules.ingestion.application.use_cases.PostgresPaperRepository"
        ) as MockPaperRepo,
        patch(
            "backend.src.modules.ingestion.application.use_cases.enqueue_ingestion_task",
            new_callable=AsyncMock,
        ),
    ):
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.delete = AsyncMock()
        mock_get_redis.return_value = mock_redis

        mock_paper_repo = AsyncMock()
        mock_paper_repo.save_search_paper = AsyncMock(return_value="paper-id")
        MockPaperRepo.return_value = mock_paper_repo

        result = await use_case.execute(
            project_id="proj-1",
            user_id="user-1",
            title="Paper",
            authors=["Author"],
            abstract="Abstract",
            year=2024,
            doi=None,
            arxiv_id=None,
            url=None,
            pdf_url=None,
            source="arxiv",
            db=db,
        )
        assert "document_id" in result


@pytest.mark.asyncio
async def test_confirm_returns_503_when_lock_unavailable(db):
    """Không acquire được Redis lock (request khác đang giữ) → HTTP 503, không nhân đôi."""
    from fastapi import HTTPException

    use_case = ConfirmMetadataUseCase()
    with (
        patch(
            "backend.src.modules.ingestion.application.use_cases.PostgresUploadedFileRepository"
        ) as MockFileRepo,
        patch(
            "backend.src.modules.ingestion.application.use_cases.get_redis",
            new_callable=AsyncMock,
        ) as mock_get_redis,
    ):
        mock_repo = AsyncMock()
        mock_repo.find_by_id.return_value = _make_uploaded_file()
        MockFileRepo.return_value = mock_repo

        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(return_value=None)  # luôn thất bại acquire
        mock_get_redis.return_value = mock_redis

        with pytest.raises(HTTPException) as exc:
            await use_case.execute(
                file_id="file-id",
                title="t",
                authors=[],
                abstract="a",
                year=None,
                project_id="proj-1",
                user_id="user-1",
                db=db,
            )
        assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_confirm_returns_503_when_redis_down(db):
    """Redis sập (set ném RedisError) → fail-closed HTTP 503, không phải 500."""
    from fastapi import HTTPException
    from redis.exceptions import RedisError

    use_case = ConfirmMetadataUseCase()
    with (
        patch(
            "backend.src.modules.ingestion.application.use_cases.PostgresUploadedFileRepository"
        ) as MockFileRepo,
        patch(
            "backend.src.modules.ingestion.application.use_cases.get_redis",
            new_callable=AsyncMock,
        ) as mock_get_redis,
    ):
        mock_repo = AsyncMock()
        mock_repo.find_by_id.return_value = _make_uploaded_file()
        MockFileRepo.return_value = mock_repo

        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(side_effect=RedisError("connection refused"))
        mock_get_redis.return_value = mock_redis

        with pytest.raises(HTTPException) as exc:
            await use_case.execute(
                file_id="file-id",
                title="t",
                authors=[],
                abstract="a",
                year=None,
                project_id="proj-1",
                user_id="user-1",
                db=db,
            )
        assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_get_max_papers_limit_fallback():
    """get_max_papers_limit đọc đúng số hợp lệ; fallback 15 khi None/không parse được."""
    from backend.src.modules.ingestion.application.use_cases import get_max_papers_limit

    mock_db = AsyncMock()
    with patch(
        "backend.src.modules.admin.infrastructure.settings_orm.get_setting",
        new_callable=AsyncMock,
    ) as mock_get_setting:
        mock_get_setting.return_value = "20"
        assert await get_max_papers_limit(mock_db) == 20
        mock_get_setting.return_value = "abc"
        assert await get_max_papers_limit(mock_db) == 15
        mock_get_setting.return_value = None
        assert await get_max_papers_limit(mock_db) == 15


@pytest.mark.asyncio
async def test_ingest_from_search_dedupes_by_arxiv_id(db):
    """Double-submit cùng arxiv_id -> trả paper hiện có, KHÔNG tạo trùng / enqueue lại."""
    use_case = IngestFromSearchUseCase()

    with (
        patch(
            "backend.src.modules.ingestion.application.use_cases.is_project_owned_by_user",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "backend.src.modules.ingestion.application.use_cases.get_redis",
            new_callable=AsyncMock,
        ) as mock_get_redis,
        patch(
            "backend.src.modules.ingestion.application.use_cases.PostgresPaperRepository"
        ) as MockPaperRepo,
        patch(
            "backend.src.modules.ingestion.application.use_cases.enqueue_ingestion_task",
            new_callable=AsyncMock,
        ) as mock_enqueue,
    ):
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.delete = AsyncMock()
        mock_get_redis.return_value = mock_redis

        existing = MagicMock()
        existing.id = "existing-paper-id"
        mock_paper_repo = AsyncMock()
        mock_paper_repo.find_active_by_identity = AsyncMock(return_value=existing)
        MockPaperRepo.return_value = mock_paper_repo

        result = await use_case.execute(
            project_id="proj-1",
            user_id="user-1",
            title="Paper",
            authors=["Author"],
            abstract="Abstract",
            year=2024,
            doi=None,
            arxiv_id="2501.12345",
            url=None,
            pdf_url=None,
            source="arxiv",
            db=db,
        )

        assert result["document_id"] == "existing-paper-id"
        mock_paper_repo.save_search_paper.assert_not_called()
        mock_enqueue.assert_not_called()
