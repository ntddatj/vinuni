"""Unit tests cho worker ingestion: text_chunker, task_progress, error handling."""
import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest

from backend.src.modules.ingestion.infrastructure.task_progress import (
    publish_error,
    publish_progress,
)
from backend.src.modules.ingestion.infrastructure.text_chunker import (
    CHILD_CHUNK_SIZE,
    CHILD_OVERLAP,
    chunk_text,
)
from backend.worker import ingest_paper_task

# ---------- text_chunker ----------

def test_chunk_text_sliding_window_500_overlap_100():
    # 1 đoạn dài 1200 ký tự (không có \n\n) → 1 parent, child sliding window
    text = "a" * 1200
    result = chunk_text(text)
    assert len(result) == 1
    parent_content, children = result[0]
    assert parent_content == text
    # Bước nhảy = 500 - 100 = 400 → offsets 0,400,800; cửa sổ thứ 3 (800:1300) chạm hết
    assert len(children) == 3
    assert children[0] == text[0:CHILD_CHUNK_SIZE]
    # overlap: 100 ký tự cuối của child[0] trùng 100 ký tự đầu child[1]
    step = CHILD_CHUNK_SIZE - CHILD_OVERLAP
    assert children[1] == text[step : step + CHILD_CHUNK_SIZE]


def test_chunk_text_short_text_not_split():
    text = "Một đoạn ngắn."  # < 500 chars
    result = chunk_text(text)
    assert len(result) == 1
    parent_content, children = result[0]
    assert parent_content == text
    assert children == [text]


def test_chunk_text_empty_returns_empty():
    assert chunk_text("   ") == []


# ---------- task_progress ----------

@pytest.mark.asyncio
async def test_publish_progress_writes_json_to_redis():
    redis = AsyncMock()
    await publish_progress(redis, "doc-1", 60, "embedding", "Đang tạo vector nhúng...")

    redis.set.assert_awaited_once()
    args, kwargs = redis.set.call_args
    assert args[0] == "task:doc-1:progress"
    payload = json.loads(args[1])
    assert payload == {
        "event": "progress",
        "taskId": "doc-1",
        "status": "embedding",
        "percent": 60,
        "message": "Đang tạo vector nhúng...",
    }
    assert "ex" in kwargs  # có TTL


# ---------- worker error handling ----------

class _FakeSessionFactory:
    def __init__(self, session):
        self._session = session

    @asynccontextmanager
    async def _ctx(self):
        yield self._session

    def __call__(self):
        return self._ctx()


@pytest.mark.asyncio
async def test_ingest_paper_task_publishes_error_when_paper_not_found():
    # DB trả về None (paper không tồn tại) → worker publish_error, không raise
    db = AsyncMock()
    execute_result = AsyncMock()
    execute_result.scalar_one_or_none = lambda: None
    db.execute = AsyncMock(return_value=execute_result)

    redis = AsyncMock()
    ctx = {"redis": redis, "session_factory": _FakeSessionFactory(db)}

    await ingest_paper_task(ctx, "missing-paper-id")

    # Phải có ít nhất 1 lần set với event=error
    error_calls = [
        c for c in redis.set.call_args_list if '"event": "error"' in c.args[1]
    ]
    assert error_calls, "Worker phải publish event error khi paper không tồn tại"
    payload = json.loads(error_calls[-1].args[1])
    assert payload["event"] == "error"
    assert payload["taskId"] == "missing-paper-id"


@pytest.mark.asyncio
async def test_publish_error_payload():
    redis = AsyncMock()
    await publish_error(redis, "doc-2", "Lỗi không xác định")
    args, _ = redis.set.call_args
    payload = json.loads(args[1])
    assert payload["event"] == "error"
    assert payload["message"] == "Lỗi không xác định"


# ---------- _get_following_redirects (SSRF-safe redirect follow) ----------


class _FakeResp:
    def __init__(self, status_code, location=None, url="https://arxiv.org/pdf/x"):
        import httpx

        self.status_code = status_code
        self.headers = {"location": location} if location else {}
        self.url = httpx.URL(url)


class _FakeRedirectClient:
    """Trả lần lượt các response đã nạp sẵn cho mỗi .get()."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.requested = []

    async def get(self, url):
        self.requested.append(url)
        return self._responses.pop(0)


@pytest.mark.asyncio
async def test_get_following_redirects_follows_arxiv_http_to_https():
    # arXiv: http://arxiv.org/pdf/... 301 -> https://arxiv.org/pdf/... 200
    from backend.worker import _get_following_redirects

    client = _FakeRedirectClient([
        _FakeResp(301, location="https://arxiv.org/pdf/2501.12345",
                  url="http://arxiv.org/pdf/2501.12345"),
        _FakeResp(200, url="https://arxiv.org/pdf/2501.12345"),
    ])
    resp = await _get_following_redirects(client, "http://arxiv.org/pdf/2501.12345")
    assert resp is not None and resp.status_code == 200
    assert client.requested[-1] == "https://arxiv.org/pdf/2501.12345"


@pytest.mark.asyncio
async def test_get_following_redirects_blocks_ssrf_redirect():
    # Redirect tới loopback phải bị SSRF guard chặn -> trả None (không tải)
    from backend.worker import _get_following_redirects

    client = _FakeRedirectClient([
        _FakeResp(302, location="http://127.0.0.1/secret",
                  url="https://evil.example.com/pdf"),
    ])
    resp = await _get_following_redirects(client, "https://evil.example.com/pdf")
    assert resp is None


# ---------- _sanitize_text (NUL / control char khỏi text PDF) ----------


def test_sanitize_text_strips_nul_and_control_chars():
    from backend.worker import _sanitize_text

    raw = "Hello\x00World\x0c\x07 line2"
    out = _sanitize_text(raw)
    assert "\x00" not in out
    assert "\x0c" not in out and "\x07" not in out
    assert out == "HelloWorld line2"


def test_sanitize_text_keeps_tab_newline_cr():
    from backend.worker import _sanitize_text

    raw = "a\tb\nc\rd"
    assert _sanitize_text(raw) == "a\tb\nc\rd"


def test_sanitize_text_handles_empty():
    from backend.worker import _sanitize_text

    assert _sanitize_text("") == ""
