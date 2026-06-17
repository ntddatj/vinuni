from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.modules.identity.domain.entities import User
from backend.src.modules.identity.infrastructure.auth_dependencies import get_current_user
from backend.src.modules.ingestion.application.use_cases import ConfirmMetadataUseCase, UploadDocumentUseCase
from backend.src.modules.ingestion.domain.exceptions import (
    FileStorageError,
    FileTooLargeError,
    IngestionFileNotFoundError,
    ProjectAccessDeniedError,
    UnsupportedFileTypeError,
)
from backend.src.modules.ingestion.presentation.schemas import (
    ConfirmRequestSchema,
    ConfirmResponseSchema,
    UploadResponseSchema,
)
from backend.src.shared.infra.database import get_db_session as get_db
from backend.src.shared.infra.settings import get_settings

router = APIRouter(tags=["ingestion"])


@router.post("/ingestion/upload", response_model=UploadResponseSchema)
async def upload_document(
    file: UploadFile = File(...),
    project_id: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UploadResponseSchema:
    # Chặn nạp toàn bộ file lớn vào RAM: từ chối sớm dựa trên Content-Length nếu biết.
    settings = get_settings()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if file.size is not None and file.size > max_bytes:
        raise HTTPException(
            status_code=422, detail=str(FileTooLargeError(settings.max_upload_size_mb))
        )

    file_bytes = await file.read()
    use_case = UploadDocumentUseCase()
    try:
        result = await use_case.execute(
            file_bytes=file_bytes,
            original_filename=file.filename or "",
            project_id=project_id,
            user_id=str(current_user.id),
            db=db,
        )
    except FileTooLargeError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except UnsupportedFileTypeError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except ProjectAccessDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except FileStorageError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return UploadResponseSchema(
        file_id=result["file_id"],
        title=result["title"],
        authors=result["authors"],
        abstract=result["abstract"],
        year=result["year"],
    )


@router.post("/ingestion/confirm", response_model=ConfirmResponseSchema, status_code=201)
async def confirm_metadata(
    body: ConfirmRequestSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConfirmResponseSchema:
    use_case = ConfirmMetadataUseCase()
    try:
        result = await use_case.execute(
            file_id=body.file_id,
            title=body.title,
            authors=body.authors,
            abstract=body.abstract,
            year=body.year,
            project_id=body.project_id,
            user_id=str(current_user.id),
            db=db,
        )
    except IngestionFileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return ConfirmResponseSchema(
        document_id=result["document_id"],
        message=result["message"],
    )
