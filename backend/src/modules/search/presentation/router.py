from fastapi import APIRouter, Depends, HTTPException, Query

from backend.src.modules.identity.domain.entities import User
from backend.src.modules.identity.infrastructure.auth_dependencies import get_current_user
from backend.src.modules.search.application.use_cases import SearchPapersUseCase
from backend.src.modules.search.infrastructure.arxiv_client import ArxivClient
from backend.src.modules.search.infrastructure.search_cache import SearchCache
from backend.src.modules.search.infrastructure.semantic_scholar_client import SemanticScholarClient
from backend.src.modules.search.presentation.schemas import PaperResultSchema, SearchResponseSchema

router = APIRouter(tags=["search"])


@router.get("/search", response_model=SearchResponseSchema)
async def search_papers(
    q: str = Query(..., min_length=1, max_length=200, description="Từ khóa tìm kiếm"),
    limit: int = Query(default=10, ge=1, le=50),
    _current_user: User = Depends(get_current_user),
) -> SearchResponseSchema:
    q_stripped = q.strip()
    if not q_stripped:
        raise HTTPException(status_code=422, detail="Query không được chỉ gồm khoảng trắng")

    arxiv = ArxivClient()
    s2 = SemanticScholarClient()
    cache = SearchCache()
    try:
        use_case = SearchPapersUseCase(arxiv=arxiv, s2=s2, cache=cache)
        response = await use_case.execute(q_stripped, limit)
        return SearchResponseSchema(
            results=[
                PaperResultSchema(
                    title=r.title,
                    authors=r.authors,
                    year=r.year,
                    abstract=r.abstract,
                    doi=r.doi,
                    arxiv_id=r.arxiv_id,
                    url=r.url,
                    pdf_url=r.pdf_url,
                    source=r.source,
                )
                for r in response.results
            ],
            warnings=response.warnings,
        )
    finally:
        await arxiv.aclose()
        await s2.aclose()
