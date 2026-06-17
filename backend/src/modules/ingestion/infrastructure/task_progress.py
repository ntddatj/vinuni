"""Ghi/đọc tiến trình ingestion qua Redis key ``task:{document_id}:progress``.

Worker ARQ ghi event (progress/completed/error); SSE endpoint poll & đọc lại.
Giá trị là JSON string với TTL theo settings.ingestion_progress_ttl.
"""
import json

from backend.src.shared.infra.settings import get_settings


def _progress_key(document_id: str) -> str:
    return f"task:{document_id}:progress"


async def publish_progress(
    redis, document_id: str, percent: int, status: str, message: str
) -> None:
    data = json.dumps(
        {
            "event": "progress",
            "taskId": document_id,
            "status": status,
            "percent": percent,
            "message": message,
        }
    )
    await redis.set(_progress_key(document_id), data, ex=get_settings().ingestion_progress_ttl)


async def publish_completed(redis, document_id: str) -> None:
    data = json.dumps(
        {
            "event": "completed",
            "taskId": document_id,
            "documentId": document_id,
        }
    )
    await redis.set(_progress_key(document_id), data, ex=get_settings().ingestion_progress_ttl)


async def publish_error(redis, document_id: str, message: str) -> None:
    data = json.dumps(
        {
            "event": "error",
            "taskId": document_id,
            "message": message,
        }
    )
    await redis.set(_progress_key(document_id), data, ex=get_settings().ingestion_progress_ttl)


async def get_progress(redis, document_id: str) -> dict | None:
    raw = await redis.get(_progress_key(document_id))
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw)
