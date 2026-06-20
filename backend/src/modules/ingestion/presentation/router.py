import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from backend.src.modules.identity.domain.entities import User
from backend.src.modules.identity.infrastructure.auth_dependencies import get_current_user
from backend.src.modules.ingestion.application.use_cases import (
    ConfirmMetadataUseCase,
    IngestFromSearchUseCase,
    UploadDocumentUseCase,
)
from backend.src.modules.ingestion.domain.exceptions import (
    FileStorageError,
    FileTooLargeError,
    IngestionFileNotFoundError,
    ProjectAccessDeniedError,
    ProjectPaperLimitExceededError,
    UnsupportedFileTypeError,
)
from backend.src.modules.ingestion.infrastructure.postgres_repository import (
    PostgresPaperRepository,
    delete_paper_soft,
    find_paper_for_file_serve,
    is_project_owned_by_user,
    update_paper_metadata,
)
from backend.src.modules.ingestion.infrastructure.sse_stream import generate_sse
from backend.src.modules.ingestion.presentation.schemas import (
    AddFromSearchRequestSchema,
    AddFromSearchResponseSchema,
    ConfirmRequestSchema,
    ConfirmResponseSchema,
    DeletePaperResponseSchema,
    PaperListItemSchema,
    PaperListResponseSchema,
    PatchPaperRequestSchema,
    PatchPaperResponseSchema,
    SSETicketResponseSchema,
    UploadResponseSchema,
)
from backend.src.shared.infra.database import get_db_session as get_db
from backend.src.shared.infra.redis_client import get_redis
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
        doi=result.get("doi"),
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
            doi=body.doi,
        )
    except IngestionFileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ProjectPaperLimitExceededError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e

    return ConfirmResponseSchema(
        document_id=result["document_id"],
        message=result["message"],
    )


@router.post("/ingestion/from-search", response_model=AddFromSearchResponseSchema, status_code=201)
async def add_from_search(
    body: AddFromSearchRequestSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AddFromSearchResponseSchema:
    use_case = IngestFromSearchUseCase()
    try:
        result = await use_case.execute(
            project_id=body.project_id,
            user_id=str(current_user.id),
            title=body.title,
            authors=body.authors,
            abstract=body.abstract,
            year=body.year,
            doi=body.doi,
            arxiv_id=body.arxiv_id,
            url=body.url,
            pdf_url=body.pdf_url,
            source=body.source,
            db=db,
        )
    except ProjectAccessDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ProjectPaperLimitExceededError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e

    return AddFromSearchResponseSchema(
        document_id=result["document_id"],
        message=result["message"],
    )


@router.post("/ingestion/tasks/{document_id}/ticket", response_model=SSETicketResponseSchema)
async def create_sse_ticket(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SSETicketResponseSchema:
    # Validate paper thuộc về user hiện tại (chống IDOR). Trả 404 nếu không thấy/không sở hữu.
    paper_repo = PostgresPaperRepository(db)
    paper = await paper_repo.find_owned_by_user(document_id, str(current_user.id))
    if paper is None:
        raise HTTPException(status_code=404, detail="Tài liệu không tồn tại")

    settings = get_settings()
    ticket = str(uuid.uuid4())
    redis = await get_redis()
    await redis.set(
        f"ticket:{ticket}",
        json.dumps({"document_id": document_id, "user_id": str(current_user.id)}),
        ex=settings.ingestion_sse_ticket_ttl,
    )
    return SSETicketResponseSchema(ticket=ticket)


@router.get("/ingestion/sse/stream")
async def sse_stream(ticket: str = Query(...)) -> EventSourceResponse:
    # Validate ticket từ Redis (one-time use: GET + DELETE).
    # EventSource không gửi được Authorization header nên dùng ticket ngắn hạn.
    redis = await get_redis()
    ticket_key = f"ticket:{ticket}"
    raw = await redis.get(ticket_key)
    if not raw:
        raise HTTPException(status_code=401, detail="Ticket SSE không hợp lệ hoặc đã hết hạn")
    # KHÔNG xóa ticket ngay: EventSource của browser tự reconnect khi rớt mạng tạm thời và sẽ
    # gọi lại cùng URL ?ticket=. Cho phép dùng lại trong thời gian TTL (ngắn) để reconnect
    # hoạt động; ticket tự hết hạn theo TTL nên vẫn an toàn (capability ngắn hạn).

    ticket_data = json.loads(raw)
    document_id = ticket_data["document_id"]
    return EventSourceResponse(generate_sse(redis, document_id))


@router.get("/projects/{project_id}/papers", response_model=PaperListResponseSchema)
async def list_project_papers(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaperListResponseSchema:
    if not await is_project_owned_by_user(db, project_id, str(current_user.id)):
        raise HTTPException(status_code=403, detail="Không có quyền truy cập dự án này")

    paper_repo = PostgresPaperRepository(db)
    papers = await paper_repo.list_by_project(project_id, str(current_user.id))
    items = [
        PaperListItemSchema(
            id=str(p.id),
            title=p.title,
            authors=list(p.authors or []),
            year=p.year,
            source=p.source,
            status=p.status,
            created_at=p.created_at,
            abstract=p.abstract,
            has_file=bool(p.file_path),
            pdf_url=p.pdf_url,
            url=p.url,
        )
        for p in papers
    ]
    return PaperListResponseSchema(items)


@router.delete("/projects/{project_id}/papers/{paper_id}", response_model=DeletePaperResponseSchema)
async def delete_paper(
    project_id: str,
    paper_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeletePaperResponseSchema:
    if not await is_project_owned_by_user(db, project_id, str(current_user.id)):
        raise HTTPException(status_code=403, detail="Không có quyền truy cập dự án này")

    deleted = await delete_paper_soft(db, paper_id, project_id, str(current_user.id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Tài liệu không tồn tại hoặc đã bị xóa")
    return DeletePaperResponseSchema(message="Tài liệu đã được xóa thành công")


@router.patch("/projects/{project_id}/papers/{paper_id}", response_model=PatchPaperResponseSchema)
async def patch_paper_metadata(
    project_id: str,
    paper_id: str,
    body: PatchPaperRequestSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PatchPaperResponseSchema:
    if not await is_project_owned_by_user(db, project_id, str(current_user.id)):
        raise HTTPException(status_code=403, detail="Không có quyền truy cập dự án này")

    paper = await update_paper_metadata(
        db, paper_id, project_id, str(current_user.id),
        title=body.title, authors=body.authors,
        abstract=body.abstract, year=body.year,
    )
    if paper is None:
        raise HTTPException(status_code=404, detail="Tài liệu không tồn tại")
    return PatchPaperResponseSchema(
        id=str(paper.id),
        title=paper.title,
        authors=list(paper.authors or []),
        abstract=paper.abstract,
        year=paper.year,
        updated_at=paper.updated_at,
    )


@router.get("/projects/{project_id}/papers/{paper_id}/file")
async def serve_paper_file(
    project_id: str,
    paper_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    if not await is_project_owned_by_user(db, project_id, str(current_user.id)):
        raise HTTPException(status_code=403, detail="Không có quyền truy cập dự án này")

    paper = await find_paper_for_file_serve(db, paper_id, project_id, str(current_user.id))
    if paper is None:
        raise HTTPException(status_code=404, detail="Tài liệu không tồn tại")
    if not paper.file_path or not Path(paper.file_path).exists():
        raise HTTPException(status_code=404, detail="File nguồn chưa được cache hoặc không tồn tại")

    return FileResponse(
        path=paper.file_path,
        media_type="application/pdf",
        filename=f"{paper.id}.pdf",
        headers={"Content-Disposition": f'inline; filename="{paper.id}.pdf"'},
    )
