import asyncio
import logging
import re
from itertools import zip_longest

from backend.src.modules.search.domain.entities import ClientSearchResult, PaperResult, SearchResponse
from backend.src.modules.search.infrastructure.arxiv_client import ArxivClient
from backend.src.modules.search.infrastructure.broad_query_detector import BroadQueryDetector
from backend.src.modules.search.infrastructure.search_cache import SearchCache
from backend.src.modules.search.infrastructure.semantic_scholar_client import SemanticScholarClient

logger = logging.getLogger(__name__)


class SearchPapersUseCase:
    def __init__(
        self,
        arxiv: ArxivClient,
        s2: SemanticScholarClient,
        cache: SearchCache,
        detector: BroadQueryDetector,
    ) -> None:
        self._arxiv = arxiv
        self._s2 = s2
        self._cache = cache
        self._detector = detector

    async def execute(self, query: str, limit: int = 10) -> SearchResponse:
        cached = await self._cache.get(query, limit)
        if cached is not None:
            return cached

        arxiv_task = asyncio.create_task(self._arxiv.search(query, limit))
        s2_task = asyncio.create_task(self._s2.search(query, limit))

        arxiv_client_result: ClientSearchResult | None = None
        s2_client_result: ClientSearchResult | None = None
        warnings: list[str] = []

        for coro, name in [
            (arxiv_task, "arxiv_timeout"),
            (s2_task, "semantic_scholar_timeout"),
        ]:
            try:
                result = await coro
                if name == "arxiv_timeout":
                    arxiv_client_result = result
                else:
                    s2_client_result = result
            except Exception as e:
                logger.warning("Tìm kiếm %s thất bại: %s", name, e, exc_info=True)
                warnings.append(name)

        arxiv_papers = arxiv_client_result.papers if arxiv_client_result else []
        s2_papers = s2_client_result.papers if s2_client_result else []
        arxiv_total = arxiv_client_result.total_available if arxiv_client_result else 0
        s2_total = s2_client_result.total_available if s2_client_result else 0

        interleaved = [p for pair in zip_longest(arxiv_papers, s2_papers) for p in pair if p is not None]
        combined = self._deduplicate(interleaved)

        max_total = max(arxiv_total, s2_total)
        is_broad, suggestions = await self._detector.detect(query, max_total)

        response = SearchResponse(
            results=combined[:limit],
            warnings=warnings,
            is_broad_query=is_broad,
            suggestions=suggestions,
        )

        # Chỉ cache khi đủ 2 nguồn VÀ không phải broad-query-thiếu-suggestions.
        # Tránh "đầu độc" cache khi Gemini lỗi tạm thời (is_broad=True, suggestions=[]):
        # bỏ qua cache để lần tìm kiếm sau retry LLM.
        if not warnings and (not is_broad or suggestions):
            await self._cache.set(query, limit, response)

        return response

    def _deduplicate(self, papers: list[PaperResult]) -> list[PaperResult]:
        seen_dois: set[str] = set()
        seen_arxiv_ids: set[str] = set()
        unique: list[PaperResult] = []

        for p in papers:
            normalized_doi = p.doi.strip().lower() if p.doi else None
            base_id = re.sub(r'v\d+$', '', p.arxiv_id).strip() if p.arxiv_id else None

            if (normalized_doi and normalized_doi in seen_dois) or \
               (base_id and base_id in seen_arxiv_ids):
                continue

            if normalized_doi:
                seen_dois.add(normalized_doi)
            if base_id:
                seen_arxiv_ids.add(base_id)

            unique.append(p)

        return unique
