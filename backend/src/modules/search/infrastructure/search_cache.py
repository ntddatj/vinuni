import hashlib
import json
import logging
from dataclasses import asdict

import redis.asyncio as aioredis

from backend.src.modules.search.domain.entities import PaperResult, SearchResponse
from backend.src.shared.infra.settings import get_settings

logger = logging.getLogger(__name__)
CACHE_TTL_SECONDS = 86400  # 24 giờ


class SearchCache:
    def __init__(self) -> None:
        try:
            settings = get_settings()
            self._redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        except Exception:
            logger.warning("Không thể khởi tạo Redis client, cache bị tắt.")
            self._redis = None

    def _make_key(self, query: str, limit: int) -> str:
        normalized = query.strip().lower()
        return "search:" + hashlib.md5(f"{normalized}:{limit}".encode(), usedforsecurity=False).hexdigest()

    async def get(self, query: str, limit: int) -> SearchResponse | None:
        if self._redis is None:
            return None
        try:
            key = self._make_key(query, limit)
            raw = await self._redis.get(key)
            if raw is None:
                return None
            data = json.loads(raw)
            return SearchResponse(
                results=[PaperResult(**r) for r in data["results"]],
                warnings=data["warnings"],
                is_broad_query=data.get("is_broad_query", False),
                suggestions=data.get("suggestions", []),
            )
        except Exception as e:
            logger.warning("Redis cache get thất bại: %s", e)
            return None

    async def set(self, query: str, limit: int, response: SearchResponse) -> None:
        if self._redis is None:
            return
        try:
            key = self._make_key(query, limit)
            data = {
                "results": [asdict(r) for r in response.results],
                "warnings": response.warnings,
                "is_broad_query": response.is_broad_query,
                "suggestions": response.suggestions,
            }
            await self._redis.setex(key, CACHE_TTL_SECONDS, json.dumps(data))
        except Exception as e:
            logger.warning("Redis cache set thất bại: %s", e)
