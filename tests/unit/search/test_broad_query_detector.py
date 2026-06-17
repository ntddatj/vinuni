"""Unit tests for BroadQueryDetector."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.src.modules.search.infrastructure.broad_query_detector import BroadQueryDetector


@pytest.fixture
def db():
    return AsyncMock()


@pytest.fixture
def detector(db):
    return BroadQueryDetector(user_id="user-123", db=db)


@pytest.mark.asyncio
async def test_detect_below_threshold_returns_false(detector):
    with patch("backend.src.modules.search.infrastructure.broad_query_detector.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(broad_query_threshold=50)
        is_broad, suggestions = await detector.detect("narrow query", total_available=10)

    assert is_broad is False
    assert suggestions == []


@pytest.mark.asyncio
async def test_detect_at_threshold_returns_false(detector):
    with patch("backend.src.modules.search.infrastructure.broad_query_detector.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(broad_query_threshold=50)
        is_broad, suggestions = await detector.detect("query", total_available=50)

    assert is_broad is False
    assert suggestions == []


@pytest.mark.asyncio
async def test_detect_above_threshold_calls_llm(detector, db):
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = MagicMock(
        content='["NLP", "Computer Vision", "Reinforcement Learning"]'
    )

    with patch("backend.src.modules.search.infrastructure.broad_query_detector.get_settings") as mock_settings, \
         patch("backend.src.modules.search.infrastructure.broad_query_detector.LLMRouter") as mock_router_cls:

        mock_settings.return_value = MagicMock(broad_query_threshold=50)
        mock_router = AsyncMock()
        mock_router.get_llm_client.return_value = mock_llm
        mock_router_cls.return_value = mock_router

        is_broad, suggestions = await detector.detect("AI", total_available=200)

    assert is_broad is True
    assert suggestions == ["NLP", "Computer Vision", "Reinforcement Learning"]


@pytest.mark.asyncio
async def test_detect_llm_error_graceful_fallback(detector):
    with patch("backend.src.modules.search.infrastructure.broad_query_detector.get_settings") as mock_settings, \
         patch("backend.src.modules.search.infrastructure.broad_query_detector.LLMRouter") as mock_router_cls:

        mock_settings.return_value = MagicMock(broad_query_threshold=50)
        mock_router = AsyncMock()
        mock_router.get_llm_client.side_effect = RuntimeError("No API key configured")
        mock_router_cls.return_value = mock_router

        is_broad, suggestions = await detector.detect("AI", total_available=200)

    assert is_broad is True
    assert suggestions == []


@pytest.mark.asyncio
async def test_detect_llm_invalid_json_graceful_fallback(detector):
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = MagicMock(content="not valid json {")

    with patch("backend.src.modules.search.infrastructure.broad_query_detector.get_settings") as mock_settings, \
         patch("backend.src.modules.search.infrastructure.broad_query_detector.LLMRouter") as mock_router_cls:

        mock_settings.return_value = MagicMock(broad_query_threshold=50)
        mock_router = AsyncMock()
        mock_router.get_llm_client.return_value = mock_llm
        mock_router_cls.return_value = mock_router

        is_broad, suggestions = await detector.detect("AI", total_available=200)

    assert is_broad is True
    assert suggestions == []


@pytest.mark.asyncio
async def test_detect_llm_caps_at_5_suggestions(detector):
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = MagicMock(
        content='["A", "B", "C", "D", "E", "F", "G"]'
    )

    with patch("backend.src.modules.search.infrastructure.broad_query_detector.get_settings") as mock_settings, \
         patch("backend.src.modules.search.infrastructure.broad_query_detector.LLMRouter") as mock_router_cls:

        mock_settings.return_value = MagicMock(broad_query_threshold=50)
        mock_router = AsyncMock()
        mock_router.get_llm_client.return_value = mock_llm
        mock_router_cls.return_value = mock_router

        is_broad, suggestions = await detector.detect("broad", total_available=200)

    assert len(suggestions) == 5
    assert suggestions == ["A", "B", "C", "D", "E"]


def _mock_llm(content):
    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = MagicMock(content=content)
    return mock_llm


async def _detect_with_content(detector, content, total_available=200):
    with patch("backend.src.modules.search.infrastructure.broad_query_detector.get_settings") as mock_settings, \
         patch("backend.src.modules.search.infrastructure.broad_query_detector.LLMRouter") as mock_router_cls:
        mock_settings.return_value = MagicMock(broad_query_threshold=50)
        mock_router = AsyncMock()
        mock_router.get_llm_client.return_value = _mock_llm(content)
        mock_router_cls.return_value = mock_router
        return await detector.detect("AI", total_available=total_available)


@pytest.mark.asyncio
async def test_detect_strips_markdown_code_fence(detector):
    """Gemini thường bọc JSON trong ```json ... ``` — phải parse được."""
    is_broad, suggestions = await _detect_with_content(
        detector, '```json\n["NLP", "Computer Vision"]\n```'
    )
    assert is_broad is True
    assert suggestions == ["NLP", "Computer Vision"]


@pytest.mark.asyncio
async def test_detect_unwraps_object_with_array(detector):
    """Model bọc mảng trong object {"suggestions": [...]} vẫn lấy được mảng."""
    is_broad, suggestions = await _detect_with_content(
        detector, '{"suggestions": ["NLP", "Computer Vision"]}'
    )
    assert is_broad is True
    assert suggestions == ["NLP", "Computer Vision"]


@pytest.mark.asyncio
async def test_detect_filters_non_strings_and_dedupes(detector):
    """Lọc phần tử không phải chuỗi, chuỗi rỗng và trùng lặp (giữ thứ tự)."""
    is_broad, suggestions = await _detect_with_content(
        detector, '["NLP", "NLP", {"x": 1}, 42, "", "  ", "Computer Vision"]'
    )
    assert is_broad is True
    assert suggestions == ["NLP", "Computer Vision"]


@pytest.mark.asyncio
async def test_detect_content_as_list_blocks(detector):
    """ChatGoogleGenerativeAI có thể trả content là list content-block."""
    is_broad, suggestions = await _detect_with_content(
        detector, [{"type": "text", "text": '["NLP", "Vision"]'}]
    )
    assert is_broad is True
    assert suggestions == ["NLP", "Vision"]
