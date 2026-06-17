"""Singleton async Redis client cho FastAPI process (SSE stream + ticket).

Worker ARQ KHÔNG dùng client này — worker dùng ``ctx['redis']`` của arq.

QUAN TRỌNG: progress key được worker publish qua ``ctx['redis']`` (tức ``arq_redis_url``),
nên SSE endpoint phải đọc từ CÙNG Redis đó. Vì vậy client này dùng ``arq_redis_url``
(mặc định trùng ``redis_url``) để tránh worker ghi một nơi còn SSE đọc một nơi khác.
"""
import redis.asyncio as aioredis

from backend.src.shared.infra.settings import get_settings

_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = aioredis.from_url(settings.arq_redis_url, decode_responses=True)
    return _redis_client
