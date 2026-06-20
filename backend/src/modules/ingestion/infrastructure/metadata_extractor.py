import json
import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.modules.ingestion.domain.entities import ExtractedMetadata
from backend.src.shared.infra.llm.router import LLMRouter

logger = logging.getLogger(__name__)

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)

METADATA_EXTRACTION_PROMPT = """Extract bibliographic metadata from this academic text.
Return ONLY a JSON object with these exact keys: title, authors, abstract, year, doi.

Rules:
- title: string (full paper title, empty string if not found)
- authors: list of strings (author names, empty list if not found)
- abstract: string (paper abstract or summary, empty string if not found)
- year: integer or null (publication year 4 digits, null if not found)
- doi: string or null (the DOI OF THIS paper, e.g. "10.1234/abcd". Strip any "https://doi.org/" prefix. null if not found. Do NOT invent a DOI.)

Text to analyze (first pages):
{text}

Filename hint: {filename}

Respond with ONLY the JSON object, no markdown:"""

# DOI hợp lệ bắt đầu bằng "10." + registrant + "/" + suffix (Crossref pattern).
_DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")


class LLMMetadataExtractor:
    def __init__(self, user_id: str, db: AsyncSession) -> None:
        self._user_id = user_id
        self._db = db

    async def extract(self, text: str, filename: str) -> ExtractedMetadata:
        try:
            router = LLMRouter(self._db)
            llm = await router.get_llm_client(self._user_id, model_name="gemini-2.5-flash")
            prompt = METADATA_EXTRACTION_PROMPT.format(text=text[:4000], filename=filename)
            result = await llm.ainvoke(prompt)
            content = self._coerce_to_text(result.content)
            content = self._strip_code_fence(content)
            data = json.loads(content)
            return ExtractedMetadata(
                title=str(data.get("title", "")) or "",
                authors=self._parse_authors(data.get("authors")),
                abstract=str(data.get("abstract", "")) or "",
                year=self._parse_year(data.get("year")),
                doi=self._parse_doi(data.get("doi")),
            )
        except Exception as e:
            logger.warning("LLMMetadataExtractor: lỗi trích xuất metadata từ '%s': %s", filename, e)
            return ExtractedMetadata(title="", authors=[], abstract="", year=None, doi=None)

    @staticmethod
    def _parse_authors(raw: object) -> list[str]:
        """LLM có thể trả list hoặc string ('A, B'). Tránh iterate string theo ký tự."""
        if isinstance(raw, list):
            return [str(a).strip() for a in raw if a is not None and str(a).strip()]
        if isinstance(raw, str):
            return [a.strip() for a in raw.split(",") if a.strip()]
        return []

    @staticmethod
    def _parse_doi(raw: object) -> str | None:
        """Chuẩn hóa DOI: bỏ tiền tố URL/'doi:', lowercase, validate pattern Crossref.
        Trả None nếu không phải DOI hợp lệ (chống lưu rác/LLM bịa link)."""
        if not isinstance(raw, str):
            return None
        s = raw.strip().lower()
        for prefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/",
                       "http://dx.doi.org/", "doi:"):
            if s.startswith(prefix):
                s = s[len(prefix):]
                break
        s = s.strip()
        return s if _DOI_RE.match(s) else None

    @staticmethod
    def _parse_year(raw: object) -> int | None:
        """Chấp nhận 2023, '2023', 2023.0, '2023.0'; chặn năm vô lý (vd 99999)."""
        if raw is None or raw == "":
            return None
        try:
            year = int(float(raw))
        except (TypeError, ValueError):
            return None
        return year if 1000 <= year <= 2100 else None

    @staticmethod
    def _coerce_to_text(content: object) -> str:
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = [
                p if isinstance(p, str) else p.get("text", "")
                for p in content
                if isinstance(p, (str, dict))
            ]
            return "".join(parts).strip()
        return str(content).strip()

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        return _CODE_FENCE_RE.sub("", text).strip()
