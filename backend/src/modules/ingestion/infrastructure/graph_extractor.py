"""GraphExtractor — Stage-2 ingestion: trích xuất ontology học thuật bằng LLM (gemini-2.5-pro).

Story 4.3: gọi LLM trả JSON cấu trúc Finding/Limitation/Method/Dataset/Topic/Problem
và edges CONTRADICTS/SUPPORTS. Graceful failure: lỗi/JSON sai → trả None, KHÔNG raise.
"""
import json
import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.shared.infra.llm.router import LLMRouter

logger = logging.getLogger(__name__)

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)

GRAPH_EXTRACTION_PROMPT = """You are an academic knowledge graph extractor. Analyze this academic paper and extract structured academic entities.

Paper metadata:
- Title: {title}
- Authors: {authors}
- Abstract: {abstract}

Full text (may be truncated):
{text}

Return ONLY a valid JSON object (no markdown, no explanation):
{{
  "findings": [
    {{"id": "f1", "description": "Specific research finding or result", "confidence_score": 0.85}}
  ],
  "limitations": [
    {{"id": "l1", "description": "Research limitation or gap explicitly mentioned"}}
  ],
  "methods": [
    {{"id": "m1", "name": "Method name", "description": "Brief description"}}
  ],
  "datasets": [
    {{"id": "d1", "name": "Dataset name", "description": "Brief description"}}
  ],
  "topics": [
    {{"id": "t1", "name": "Research topic or domain"}}
  ],
  "problems": [
    {{"id": "pr1", "description": "Core research problem being addressed"}}
  ],
  "contradicts": [
    {{"from_id": "f1", "to_id": "f2"}}
  ],
  "supports": [
    {{"from_id": "f1", "to_id": "f2"}}
  ]
}}

Rules:
- findings: 3-7 key findings with confidence 0.0-1.0 (how well-supported the finding is)
- limitations: 1-5 explicit limitations stated in the paper
- methods: named methodologies, algorithms, techniques used (0-5)
- datasets: named datasets, benchmarks (0-5)
- topics: 1-4 main research domains
- problems: 1-3 core problems addressed
- contradicts/supports: ONLY within findings extracted from THIS paper
- Use simple IDs like "f1", "f2", "l1" (no special chars, no spaces)
- Empty array [] if none found for a category
- JSON only, no markdown"""

_ENTITY_KEYS = {"findings", "limitations", "methods", "datasets", "topics", "problems"}


class GraphExtractor:
    def __init__(self, user_id: str, db: AsyncSession) -> None:
        self._user_id = user_id
        self._db = db

    async def extract(
        self,
        paper_id: str,
        project_id: str,
        title: str,
        abstract: str,
        text: str,
    ) -> dict | None:
        try:
            router = LLMRouter(self._db)
            llm = await router.get_llm_client(self._user_id, model_name="gemini-2.5-pro")
            prompt = GRAPH_EXTRACTION_PROMPT.format(
                title=title,
                authors="",
                abstract=abstract,
                text=text[:30000],
            )
            result = await llm.ainvoke(prompt)
            content = self._coerce_to_text(result.content)
            data = self._parse_json(content)
        except Exception as e:
            logger.warning(
                "GraphExtractor: lỗi trích xuất ontology cho paper %s: %s", paper_id, e
            )
            return None

        if not isinstance(data, dict):
            logger.warning("GraphExtractor: kết quả không phải dict cho paper %s", paper_id)
            return None

        has_entity = any(data.get(k) for k in _ENTITY_KEYS)
        if not has_entity:
            logger.warning(
                "GraphExtractor: không có entity nào được trích xuất cho paper %s", paper_id
            )
            return None

        return data

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

    @classmethod
    def _parse_json(cls, content: str) -> dict | None:
        """Parse JSON từ output LLM. Tái dùng strip code fence; fallback cắt object {...}
        đầu tiên khi LLM kèm prose/fence lệch (giữ graceful: trả None nếu vẫn lỗi)."""
        stripped = cls._strip_code_fence(content)
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            start = stripped.find("{")
            end = stripped.rfind("}")
            if start != -1 and end > start:
                try:
                    return json.loads(stripped[start : end + 1])
                except json.JSONDecodeError:
                    return None
            return None
