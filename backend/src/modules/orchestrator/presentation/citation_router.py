from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.modules.identity.domain.entities import User
from backend.src.modules.identity.infrastructure.auth_dependencies import get_current_user
from backend.src.modules.orchestrator.application.dtos import GetCitationDetailDTO
from backend.src.modules.orchestrator.application.use_cases import GetCitationDetailUseCase
from backend.src.modules.orchestrator.presentation.schemas import CitationDetailResponse
from backend.src.shared.infra.database import get_db_session

router = APIRouter(prefix="/citations", tags=["citations"])


@router.get("/{chunk_id}", response_model=CitationDetailResponse)
async def get_citation_detail(
    chunk_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> CitationDetailResponse:
    use_case = GetCitationDetailUseCase(db)
    result = await use_case.execute(
        GetCitationDetailDTO(chunk_id=str(chunk_id), user_id=current_user.id)
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chunk trích dẫn không tồn tại",
        )
    return CitationDetailResponse(title=result.title, text=result.text)
