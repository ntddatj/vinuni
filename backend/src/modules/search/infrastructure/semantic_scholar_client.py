import logging

import httpx
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential

from backend.src.modules.search.domain.entities import PaperResult
from backend.src.modules.search.infrastructure.arxiv_client import _is_retryable

logger = logging.getLogger(__name__)

S2_API = "https://api.semanticscholar.org/graph/v1/paper/search"
S2_FIELDS = "title,authors,year,abstract,externalIds,openAccessPdf"


class SemanticScholarClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=8.0)

    async def search(self, query: str, limit: int = 10) -> list[PaperResult]:
        params = {"query": query, "fields": S2_FIELDS, "limit": limit}
        async for attempt in AsyncRetrying(
            retry=retry_if_exception(_is_retryable),
            stop=stop_after_attempt(2),
            wait=wait_exponential(multiplier=1, min=1, max=4),
            reraise=True,
        ):
            with attempt:
                response = await self._client.get(S2_API, params=params)
                response.raise_for_status()

        data = response.json()
        papers = data.get("data") if isinstance(data, dict) else None
        return self._parse_response(papers if isinstance(papers, list) else [])

    def _parse_response(self, papers: list[dict]) -> list[PaperResult]:
        results = []
        for p in papers:
            external_ids = p.get("externalIds") or {}
            doi = external_ids.get("DOI")
            arxiv_id = external_ids.get("ArXiv")

            open_access = p.get("openAccessPdf") or {}
            pdf_url = open_access.get("url")

            authors = [a.get("name", "") for a in (p.get("authors") or [])]
            arxiv_url = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else (
                f"https://doi.org/{doi}" if doi else ""
            )

            year_raw = p.get("year")
            year = int(year_raw) if year_raw is not None else None

            results.append(PaperResult(
                title=p.get("title") or "",
                authors=authors,
                year=year,
                abstract=p.get("abstract") or "",
                doi=doi,
                arxiv_id=arxiv_id,
                url=arxiv_url,
                pdf_url=pdf_url,
                source="semantic_scholar",
            ))
        return results

    async def aclose(self) -> None:
        await self._client.aclose()
