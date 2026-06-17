"""Unit tests for ingestion use cases."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.src.modules.ingestion.application.use_cases import (
    ConfirmMetadataUseCase,
    UploadDocumentUseCase,
)
from backend.src.modules.ingestion.domain.entities import ExtractedMetadata, UploadedFile
from backend.src.modules.ingestion.domain.exceptions import (
    FileTooLargeError,
    IngestionFileNotFoundError,
    UnsupportedFileTypeError,
)


@pytest.fixture
def db():
    return AsyncMock()


@pytest.fixture
def use_case():
    return UploadDocumentUseCase()


@pytest.fixture
def confirm_use_case():
    return ConfirmMetadataUseCase()


@pytest.mark.asyncio
async def test_upload_raises_file_too_large(use_case, db):
    large_bytes = b"x" * (21 * 1024 * 1024)  # 21MB
    with pytest.raises(FileTooLargeError):
        await use_case.execute(
            file_bytes=large_bytes,
            original_filename="paper.pdf",
            project_id="proj-id",
            user_id="user-id",
            db=db,
        )


@pytest.mark.asyncio
async def test_upload_raises_unsupported_type(use_case, db):
    file_bytes = b"fake content"
    with pytest.raises(UnsupportedFileTypeError):
        await use_case.execute(
            file_bytes=file_bytes,
            original_filename="paper.txt",
            project_id="proj-id",
            user_id="user-id",
            db=db,
        )


@pytest.mark.asyncio
async def test_upload_graceful_fallback_when_llm_fails(use_case, db):
    file_bytes = b"fake pdf content"

    with (
        patch("backend.src.modules.ingestion.application.use_cases.LocalFileStorage") as MockStorage,
        patch("backend.src.modules.ingestion.application.use_cases.PostgresUploadedFileRepository") as MockFileRepo,
        patch("backend.src.modules.ingestion.application.use_cases.DocumentParser") as MockParser,
        patch("backend.src.modules.ingestion.application.use_cases.LLMMetadataExtractor") as MockExtractor,
    ):
        mock_storage = MockStorage.return_value
        mock_storage.save.return_value = ("file-id-123", "/data/uploads/user-id/file-id-123.pdf")

        mock_file_repo = MockFileRepo.return_value
        mock_file_repo.save_uploaded_file = AsyncMock()

        mock_parser = MockParser.return_value
        mock_parser.extract_text.return_value = "some text"

        mock_extractor_instance = MockExtractor.return_value
        mock_extractor_instance.extract = AsyncMock(
            return_value=ExtractedMetadata(title="", authors=[], abstract="", year=None)
        )

        result = await use_case.execute(
            file_bytes=file_bytes,
            original_filename="paper.pdf",
            project_id="proj-id",
            user_id="user-id",
            db=db,
        )

    assert result["title"] == ""
    assert result["authors"] == []
    assert result["abstract"] == ""
    assert result["year"] is None
    assert "file_id" in result


@pytest.mark.asyncio
async def test_confirm_saves_paper_with_pending_status(confirm_use_case, db):
    mock_uploaded_file = UploadedFile(
        id="file-id-123",
        project_id="proj-id",
        user_id="user-id",
        original_filename="paper.pdf",
        file_path="/data/uploads/user-id/file-id-123.pdf",
        mime_type="application/pdf",
        file_size=1000,
    )

    with (
        patch("backend.src.modules.ingestion.application.use_cases.PostgresUploadedFileRepository") as MockFileRepo,
        patch("backend.src.modules.ingestion.application.use_cases.PostgresPaperRepository") as MockPaperRepo,
    ):
        mock_file_repo = MockFileRepo.return_value
        mock_file_repo.find_by_id = AsyncMock(return_value=mock_uploaded_file)

        mock_paper_repo = MockPaperRepo.return_value
        mock_paper_repo.save_paper = AsyncMock(side_effect=lambda entity: entity)

        result = await confirm_use_case.execute(
            file_id="file-id-123",
            title="Deep Learning for NLP",
            authors=["John Doe"],
            abstract="This paper...",
            year=2023,
            project_id="proj-id",
            user_id="user-id",
            db=db,
        )

    assert "document_id" in result
    assert result["message"] == "Tài liệu đã được thêm vào hàng đợi xử lý"

    saved_paper = mock_paper_repo.save_paper.call_args[0][0]
    assert saved_paper.status == "pending"
    assert saved_paper.source == "manual"
    assert saved_paper.title == "Deep Learning for NLP"


@pytest.mark.asyncio
async def test_confirm_raises_when_file_not_found(confirm_use_case, db):
    with patch("backend.src.modules.ingestion.application.use_cases.PostgresUploadedFileRepository") as MockFileRepo:
        mock_file_repo = MockFileRepo.return_value
        mock_file_repo.find_by_id = AsyncMock(return_value=None)

        with pytest.raises(IngestionFileNotFoundError):
            await confirm_use_case.execute(
                file_id="nonexistent-file",
                title="Title",
                authors=[],
                abstract="",
                year=None,
                project_id="proj-id",
                user_id="user-id",
                db=db,
            )
