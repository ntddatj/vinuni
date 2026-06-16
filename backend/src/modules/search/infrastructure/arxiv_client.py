import logging
import re
import xml.etree.ElementTree as ET

import httpx
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential

from backend.src.modules.search.domain.entities import PaperResult

logger = logging.getLogger(__name__)

ARXIV_API = "https://export.arxiv.org/api/query"
ATOM_NS = "http://www.w3.org/2005/Atom"
ARXIV_NS = "http://arxiv.org/schemas/atom"


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (429, 500, 502, 503, 504)
    return False


class ArxivClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=8.0)

    async def search(self, query: str, limit: int = 10) -> list[PaperResult]:
        params = {
            "search_query": f"all:{query}",
            "max_results": limit,
            "sortBy": "relevance",
        }
        async for attempt in AsyncRetrying(
            retry=retry_if_exception(_is_retryable),
            stop=stop_after_attempt(2),
            wait=wait_exponential(multiplier=1, min=1, max=4),
            reraise=True,
        ):
            with attempt:
                response = await self._client.get(ARXIV_API, params=params)
                response.raise_for_status()

        return self._parse_atom(response.text)

    def _parse_atom(self, xml_text: str) -> list[PaperResult]:
        results = []
        root = ET.fromstring(xml_text)
        for entry in root.findall(f"{{{ATOM_NS}}}entry"):
            title_el = entry.find(f"{{{ATOM_NS}}}title")
            abstract_el = entry.find(f"{{{ATOM_NS}}}summary")
            published_el = entry.find(f"{{{ATOM_NS}}}published")
            id_el = entry.find(f"{{{ATOM_NS}}}id")

            title = (title_el.text or "").strip() if title_el is not None else ""
            abstract = (abstract_el.text or "").strip() if abstract_el is not None else ""
            pub_text = published_el.text if published_el is not None else None
            year_str = pub_text[:4] if pub_text and len(pub_text) >= 4 else None
            year = int(year_str) if year_str and year_str.isdigit() else None

            arxiv_url = (id_el.text or "").strip() if id_el is not None else ""
            if "/abs/" in arxiv_url:
                raw_id = arxiv_url.split("/abs/")[-1]
                arxiv_id = re.sub(r'v\d+$', '', raw_id).strip() or None
            else:
                arxiv_id = None

            authors = [
                (name_el.text or "").strip()
                for author in entry.findall(f"{{{ATOM_NS}}}author")
                for name_el in [author.find(f"{{{ATOM_NS}}}name")]
                if name_el is not None
            ]

            doi_el = entry.find(f"{{{ARXIV_NS}}}doi")
            doi = (doi_el.text or "").strip() or None if doi_el is not None else None

            pdf_url = None
            for link in entry.findall(f"{{{ATOM_NS}}}link"):
                if link.get("title") == "pdf":
                    pdf_url = link.get("href")
                    break

            results.append(PaperResult(
                title=title,
                authors=authors,
                year=year,
                abstract=abstract,
                doi=doi,
                arxiv_id=arxiv_id,
                url=arxiv_url,
                pdf_url=pdf_url,
                source="arxiv",
            ))
        return results

    async def aclose(self) -> None:
        await self._client.aclose()
