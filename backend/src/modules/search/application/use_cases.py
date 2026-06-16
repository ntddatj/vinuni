import asyncio
import logging
import re
from itertools import zip_longest

from backend.src.modules.search.domain.entities import PaperResult, SearchResponse
from backend.src.modules.search.infrastructure.arxiv_client import ArxivClient
from backend.src.modules.search.infrastructure.search_cache import SearchCache
from backend.src.modules.search.infrastructure.semantic_scholar_client import SemanticScholarClient

logger = logging.getLogger(__name__)


class SearchPapersUseCase:
    def __init__(
        self,
        arxiv: ArxivClient,
        s2: SemanticScholarClient,
        cache: SearchCache,
    ) -> None:
        self._arxiv = arxiv
        self._s2 = s2
        self._cache = cache

    async def execute(self, query: str, limit: int = 10) -> SearchResponse:
        cached = await self._cache.get(query, limit)
        if cached is not None:
            return cached

        arxiv_task = asyncio.create_task(self._arxiv.search(query, limit))
        s2_task = asyncio.create_task(self._s2.search(query, limit))

        arxiv_results: list[PaperResult] = []
        s2_results: list[PaperResult] = []
        warnings: list[str] = []

        for coro, name, bucket in [
            (arxiv_task, "arxiv_timeout", arxiv_results),
            (s2_task, "semantic_scholar_timeout", s2_results),
        ]:
            try:
                results = await coro
                bucket.extend(results)
            except Exception as e:
                logger.warning("Tìm kiếm %s thất bại: %s", name, e, exc_info=True)
                warnings.append(name)

        # Interleave cả 2 nguồn để đảm bảo đại diện công bằng trước khi cắt [:limit]
        interleaved = [p for pair in zip_longest(arxiv_results, s2_results) for p in pair if p is not None]
        combined = self._deduplicate(interleaved)
        response = SearchResponse(results=combined[:limit], warnings=warnings)

        # Chỉ cache khi đủ cả 2 nguồn thành công (không cache bản degraded)
        if not warnings:
            await self._cache.set(query, limit, response)

        return response

    def _deduplicate(self, papers: list[PaperResult]) -> list[PaperResult]:
        seen_dois: set[str] = set()
        seen_arxiv_ids: set[str] = set()
        unique: list[PaperResult] = []

        for p in papers:
            normalized_doi = p.doi.strip().lower() if p.doi else None
            base_id = re.sub(r'v\d+$', '', p.arxiv_id).strip() if p.arxiv_id else None

            # Bỏ qua nếu BẤT KỲ định danh nào đã thấy
            if (normalized_doi and normalized_doi in seen_dois) or \
               (base_id and base_id in seen_arxiv_ids):
                continue

            # Đăng ký TẤT CẢ định danh của bài không trùng
            if normalized_doi:
                seen_dois.add(normalized_doi)
            if base_id:
                seen_arxiv_ids.add(base_id)

            unique.append(p)

        return unique
