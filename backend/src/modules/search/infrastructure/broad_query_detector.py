import json
import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.shared.infra.llm.router import LLMRouter
from backend.src.shared.infra.settings import get_settings

logger = logging.getLogger(__name__)

# Độ dài tối đa cho mỗi gợi ý — khớp giới hạn `q` (max_length=200) ở router,
# tránh chip sinh ra query 422 khi click.
_MAX_SUGGESTION_LEN = 200
_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def _coerce_to_text(content: object) -> str:
    """ChatGoogleGenerativeAI có thể trả `content` là str hoặc list content-block."""
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


def _strip_code_fence(text: str) -> str:
    """Gỡ bọc markdown ```json ... ``` mà model thường thêm vào."""
    return _CODE_FENCE_RE.sub("", text).strip()


def _clean_suggestions(raw: list) -> list[str]:
    """Lọc về danh sách chuỗi không rỗng, bỏ trùng (giữ thứ tự), cắt độ dài, tối đa 5."""
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, str):
            continue
        s = item.strip()[:_MAX_SUGGESTION_LEN]
        if not s or s in seen:
            continue
        seen.add(s)
        cleaned.append(s)
        if len(cleaned) == 5:
            break
    return cleaned


MECE_PROMPT = """You are a research assistant helping to narrow down a broad academic search query.

The user searched for: "{query}"
The search returned {total} total available results, indicating this is a very broad topic.

Generate 4-5 MECE (Mutually Exclusive, Collectively Exhaustive) subfield suggestions to help the user narrow down their search.

Rules:
- Each suggestion must be a specific, well-known subfield or application area
- Suggestions must be in English (academic field names)
- Keep each suggestion short (1-4 words max)
- Suggestions must be relevant to the original query
- Return ONLY a JSON array of strings, nothing else

Example for "Machine Learning": ["Natural Language Processing", "Computer Vision", "Reinforcement Learning", "Graph Neural Networks"]

Respond with ONLY the JSON array:"""


class BroadQueryDetector:
    def __init__(self, user_id: str, db: AsyncSession) -> None:
        self._user_id = user_id
        self._db = db

    async def detect(self, query: str, total_available: int) -> tuple[bool, list[str]]:
        settings = get_settings()
        threshold = settings.broad_query_threshold

        if total_available <= threshold:
            return False, []

        try:
            router = LLMRouter(self._db)
            llm = await router.get_llm_client(self._user_id, model_name="gemini-2.5-flash")
            prompt = MECE_PROMPT.format(query=query, total=total_available)
            result = await llm.ainvoke(prompt)
            content = _coerce_to_text(result.content)
            parsed = json.loads(_strip_code_fence(content))
            # Một số model bọc mảng trong object (vd: {"suggestions": [...]})
            if isinstance(parsed, dict):
                parsed = next(
                    (v for v in parsed.values() if isinstance(v, list)), []
                )
            if isinstance(parsed, list):
                return True, _clean_suggestions(parsed)
        except Exception as e:
            logger.warning(
                "BroadQueryDetector: không thể sinh gợi ý MECE cho query '%s': %s",
                query, e,
            )

        return True, []
