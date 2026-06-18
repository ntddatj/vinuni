"""Unit tests cho GraphExtractor (Story 4.3, AC: 12)."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.src.modules.ingestion.infrastructure.graph_extractor import GraphExtractor


def _make_extractor() -> GraphExtractor:
    db = AsyncMock()
    return GraphExtractor(user_id="user-1", db=db)


def _make_llm_mock(response_text: str):
    """Tạo mock LLM trả response_text."""
    llm = AsyncMock()
    result = MagicMock()
    result.content = response_text
    llm.ainvoke = AsyncMock(return_value=result)
    return llm


_VALID_JSON = json.dumps({
    "findings": [{"id": "f1", "description": "Test finding", "confidence_score": 0.9}],
    "limitations": [{"id": "l1", "description": "Test limitation"}],
    "methods": [],
    "datasets": [],
    "topics": [{"id": "t1", "name": "Machine Learning"}],
    "problems": [],
    "contradicts": [],
    "supports": [],
})


@pytest.mark.asyncio
async def test_extract_returns_dict_on_valid_json():
    extractor = _make_extractor()
    llm = _make_llm_mock(_VALID_JSON)
    with patch(
        "backend.src.modules.ingestion.infrastructure.graph_extractor.LLMRouter"
    ) as MockRouter:
        MockRouter.return_value.get_llm_client = AsyncMock(return_value=llm)
        result = await extractor.extract(
            paper_id="p1",
            project_id="proj1",
            title="Test Paper",
            abstract="Abstract text",
            text="Full paper text",
        )
    assert result is not None
    assert isinstance(result, dict)
    assert "findings" in result
    assert result["findings"][0]["description"] == "Test finding"


@pytest.mark.asyncio
async def test_extract_returns_none_on_invalid_json():
    extractor = _make_extractor()
    llm = _make_llm_mock("not json")
    with patch(
        "backend.src.modules.ingestion.infrastructure.graph_extractor.LLMRouter"
    ) as MockRouter:
        MockRouter.return_value.get_llm_client = AsyncMock(return_value=llm)
        result = await extractor.extract(
            paper_id="p1",
            project_id="proj1",
            title="Test Paper",
            abstract="Abstract",
            text="Full text",
        )
    assert result is None


@pytest.mark.asyncio
async def test_extract_returns_none_on_llm_exception():
    extractor = _make_extractor()
    with patch(
        "backend.src.modules.ingestion.infrastructure.graph_extractor.LLMRouter"
    ) as MockRouter:
        MockRouter.return_value.get_llm_client = AsyncMock(side_effect=Exception("LLM error"))
        result = await extractor.extract(
            paper_id="p1",
            project_id="proj1",
            title="Test Paper",
            abstract="Abstract",
            text="Full text",
        )
    assert result is None


@pytest.mark.asyncio
async def test_extract_returns_none_on_empty_entities():
    empty_json = json.dumps({
        "findings": [],
        "limitations": [],
        "methods": [],
        "datasets": [],
        "topics": [],
        "problems": [],
        "contradicts": [],
        "supports": [],
    })
    extractor = _make_extractor()
    llm = _make_llm_mock(empty_json)
    with patch(
        "backend.src.modules.ingestion.infrastructure.graph_extractor.LLMRouter"
    ) as MockRouter:
        MockRouter.return_value.get_llm_client = AsyncMock(return_value=llm)
        result = await extractor.extract(
            paper_id="p1",
            project_id="proj1",
            title="Test Paper",
            abstract="Abstract",
            text="Full text",
        )
    assert result is None


@pytest.mark.asyncio
async def test_extract_parses_json_with_surrounding_prose():
    """LLM kèm prose trước/sau JSON → fallback cắt object {...} vẫn parse được (P3)."""
    noisy = f"Here is the JSON you requested:\n```json\n{_VALID_JSON}\n```\nHope it helps!"
    extractor = _make_extractor()
    llm = _make_llm_mock(noisy)
    with patch(
        "backend.src.modules.ingestion.infrastructure.graph_extractor.LLMRouter"
    ) as MockRouter:
        MockRouter.return_value.get_llm_client = AsyncMock(return_value=llm)
        result = await extractor.extract(
            paper_id="p1",
            project_id="proj1",
            title="Test Paper",
            abstract="Abstract",
            text="Full text",
        )
    assert result is not None
    assert result["findings"][0]["description"] == "Test finding"


@pytest.mark.asyncio
async def test_extract_strips_code_fence():
    fenced = f"```json\n{_VALID_JSON}\n```"
    extractor = _make_extractor()
    llm = _make_llm_mock(fenced)
    with patch(
        "backend.src.modules.ingestion.infrastructure.graph_extractor.LLMRouter"
    ) as MockRouter:
        MockRouter.return_value.get_llm_client = AsyncMock(return_value=llm)
        result = await extractor.extract(
            paper_id="p1",
            project_id="proj1",
            title="Test Paper",
            abstract="Abstract",
            text="Full text",
        )
    assert result is not None
    assert "findings" in result
