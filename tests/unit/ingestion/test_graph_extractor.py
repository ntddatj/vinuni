"""Unit tests cho GraphExtractor (Story 4.3 + Story 4.9).

Story 4.9 AC#5: test_graph_extractor_passes_full_text_to_llm bảo chứng
rằng cơ chế head/tail trimming đã bị xoá — prompt gửi LLM chứa nguyên đoạn
References nằm ở offset ~37000 (vượt mốc head cũ 30000).
"""
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


# ─── Story 4.9: AC#5 — bảo chứng bỏ trimming head/tail ──────────────────────

@pytest.mark.asyncio
async def test_extract_passes_references_at_offset_37000_to_llm():
    """Story 4.9 AC#5: References nằm ở offset ~37000 PHẢI xuất hiện trong prompt LLM.

    Trước story này, _build_extraction_text cắt head=30000 + tail=8000 →
    References@37000 rơi vào khoảng trống giữa head và tail → bị mất.
    Sau story này, text được truyền thẳng → References luôn lọt prompt.
    """
    # Tạo text có References ở offset ~37000 (vượt mốc head cũ 30000)
    body = "Academic body content. " * 1500  # ~33000 chars
    # References nằm sau 37000 chars
    padding = "X" * (37000 - len(body))
    refs_section = (
        "\n\nReferences\n"
        "Nguyen 2020. GMO crop analysis. doi:10.1234/gmo2020\n"
        "Smith 2019. Genetic modification study. doi:10.5678/gen2019\n"
    )
    text_with_refs = body + padding + refs_section
    # Tổng ~37000 + refs → nằm trong INGEST_MAX_EXTRACT_CHARS=150000, ngoài head cũ=30000

    captured_prompts = []

    async def _capture_invoke(prompt):
        captured_prompts.append(prompt)
        mock_result = MagicMock()
        mock_result.content = _VALID_JSON
        return mock_result

    extractor = _make_extractor()
    with patch(
        "backend.src.modules.ingestion.infrastructure.graph_extractor.LLMRouter"
    ) as MockRouter:
        llm = AsyncMock()
        llm.ainvoke = _capture_invoke
        MockRouter.return_value.get_llm_client = AsyncMock(return_value=llm)

        await extractor.extract(
            paper_id="p1",
            project_id="proj1",
            title="Test Paper",
            abstract="Abstract",
            text=text_with_refs,
        )

    assert len(captured_prompts) == 1
    prompt_sent = captured_prompts[0]
    # Bảo chứng References và DOI xuất hiện nguyên vẹn trong prompt
    assert "References" in prompt_sent
    assert "10.1234/gmo2020" in prompt_sent
    assert "10.5678/gen2019" in prompt_sent
