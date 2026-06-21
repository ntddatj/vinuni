"""FillsGapJudge — LLM judge kiểm tra Paper ứng viên có thực sự giải quyết một Limitation không.

Story 4.7: Chạy ngầm qua fills_gap_task (arq). Graceful failure: lỗi/JSON sai → None, KHÔNG raise.
"""
import json
import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.shared.infra.llm.router import LLMRouter

logger = logging.getLogger(__name__)

# Hằng module-level — chỉnh bằng cách sửa code; KHÔNG dùng admin setting (float, không phải int).
FILLS_GAP_SIM_THRESHOLD = 0.65   # cosine similarity tối thiểu để lọc candidate
FILLS_GAP_TOP_K_CANDIDATES = 5   # số paper ứng viên tối đa per limitation
FILLS_GAP_JUDGE_MODEL = "gemini-2.5-flash"
CANDIDATE_TEXT_LIMIT = 4000       # chars tối đa candidate text truyền vào LLM

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)

FILLS_GAP_JUDGE_PROMPT = """You are an academic reviewer. Decide if a CANDIDATE paper genuinely
RESOLVES or FILLS a specific LIMITATION stated by another (SOURCE) paper.

SOURCE paper title: {owner_title}
LIMITATION to evaluate: {limitation_desc}

CANDIDATE paper title: {candidate_title}
CANDIDATE paper content (may be truncated):
{candidate_text}

Answer ONLY with a JSON object (no markdown):
{{"fills": true_or_false, "reason": "one short sentence"}}

Rules:
- fills=true ONLY if the candidate paper directly addresses/solves/overcomes THIS limitation
  (e.g. provides the missing method, larger dataset, or resolves the stated gap).
- Mere topical similarity, citing the same domain, or partial relevance => fills=false.
- Be conservative: when unsure, fills=false.
- JSON only."""


class FillsGapJudge:
    def __init__(self, user_id: str, db: AsyncSession) -> None:
        self._user_id = user_id
        self._db = db

    async def judge(
        self,
        limitation_desc: str,
        owner_title: str,
        candidate_title: str,
        candidate_text: str,
    ) -> dict | None:
        """Gọi LLM để phán xét. Trả {"fills": bool, "reason": str} hoặc None nếu lỗi/JSON sai."""
        try:
            router = LLMRouter(self._db)
            llm = await router.get_llm_client(self._user_id, model_name=FILLS_GAP_JUDGE_MODEL)
            prompt = FILLS_GAP_JUDGE_PROMPT.format(
                owner_title=owner_title,
                limitation_desc=limitation_desc,
                candidate_title=candidate_title,
                candidate_text=candidate_text[:CANDIDATE_TEXT_LIMIT],
            )
            result = await llm.ainvoke(prompt)
            content = self._coerce_to_text(result.content)
            data = self._parse_json(content)
        except Exception as e:
            logger.warning("FillsGapJudge: lỗi gọi LLM: %s", e)
            return None

        if not isinstance(data, dict):
            logger.warning("FillsGapJudge: kết quả không phải dict")
            return None

        if not isinstance(data.get("fills"), bool):
            logger.warning("FillsGapJudge: fills không phải bool: %s", data.get("fills"))
            return None

        # reason là output LLM untrusted → ép về str an toàn (tránh dict/list/int rơi vào
        # cột Text fills_gap_judgement.reason gây DataError khi commit).
        reason = data.get("reason")
        if reason is None:
            reason = ""
        elif not isinstance(reason, str):
            reason = str(reason)

        return {"fills": data["fills"], "reason": reason}

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
