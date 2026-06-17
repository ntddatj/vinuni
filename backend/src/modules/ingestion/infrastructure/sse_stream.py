"""SSE generator: poll Redis progress key mỗi 500ms, yield event khi có dữ liệu mới."""
import asyncio
import json
from collections.abc import AsyncGenerator

from backend.src.modules.ingestion.infrastructure.task_progress import get_progress

POLL_INTERVAL = 0.5  # giây
MAX_POLLS = 1200  # 10 phút = 1200 × 0.5s


async def generate_sse(redis, document_id: str) -> AsyncGenerator[dict, None]:
    """Yield dict {data: json} cho EventSourceResponse. Kết thúc khi completed/error/timeout."""
    last_event_data: str | None = None
    for _ in range(MAX_POLLS):
        progress = await get_progress(redis, document_id)
        if progress is not None:
            serialized = json.dumps(progress)
            if serialized != last_event_data:
                last_event_data = serialized
                yield {"data": serialized}
                if progress.get("event") in ("completed", "error"):
                    return
        await asyncio.sleep(POLL_INTERVAL)

    # Hết thời gian poll mà chưa có completed/error: phát event terminal 'timeout' để frontend
    # phân biệt "stream im lặng quá lâu" với lỗi thật, thay vì để EventSource đóng âm thầm.
    yield {"data": json.dumps({"event": "timeout", "taskId": document_id})}
