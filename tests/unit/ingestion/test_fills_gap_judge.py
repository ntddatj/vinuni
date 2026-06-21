"""Unit tests cho FillsGapJudge (AC: 12, Story 4.7)."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.src.modules.ingestion.infrastructure.fills_gap_judge import FillsGapJudge


def _make_judge():
    db = AsyncMock()
    return FillsGapJudge(user_id="user-1", db=db)


def _mock_llm_response(text: str):
    msg = MagicMock()
    msg.content = text
    return msg


@pytest.mark.asyncio
async def test_judge_returns_dict_on_valid_json():
    """LLM trả JSON hợp lệ fills=true → trả dict."""
    judge = _make_judge()
    llm = AsyncMock()
    llm.ainvoke = AsyncMock(return_value=_mock_llm_response('{"fills": true, "reason": "resolves the gap"}'))

    with patch(
        "backend.src.modules.ingestion.infrastructure.fills_gap_judge.LLMRouter"
    ) as MockRouter:
        MockRouter.return_value.get_llm_client = AsyncMock(return_value=llm)
        result = await judge.judge("limitation desc", "Source Title", "Candidate Title", "candidate text")

    assert result is not None
    assert result["fills"] is True
    assert result["reason"] == "resolves the gap"


@pytest.mark.asyncio
async def test_judge_returns_none_on_invalid_json():
    """LLM trả chuỗi không phải JSON → None."""
    judge = _make_judge()
    llm = AsyncMock()
    llm.ainvoke = AsyncMock(return_value=_mock_llm_response("not json at all"))

    with patch(
        "backend.src.modules.ingestion.infrastructure.fills_gap_judge.LLMRouter"
    ) as MockRouter:
        MockRouter.return_value.get_llm_client = AsyncMock(return_value=llm)
        result = await judge.judge("limitation desc", "Source Title", "Candidate Title", "text")

    assert result is None


@pytest.mark.asyncio
async def test_judge_returns_none_on_llm_exception():
    """LLM raise exception → None, không raise ra ngoài."""
    judge = _make_judge()

    with patch(
        "backend.src.modules.ingestion.infrastructure.fills_gap_judge.LLMRouter"
    ) as MockRouter:
        MockRouter.return_value.get_llm_client = AsyncMock(side_effect=RuntimeError("LLM down"))
        result = await judge.judge("limitation desc", "Source Title", "Candidate Title", "text")

    assert result is None


@pytest.mark.asyncio
async def test_judge_returns_none_when_fills_not_bool():
    """LLM trả fills="maybe" (không phải bool) → None."""
    judge = _make_judge()
    llm = AsyncMock()
    llm.ainvoke = AsyncMock(return_value=_mock_llm_response('{"fills": "maybe", "reason": "unclear"}'))

    with patch(
        "backend.src.modules.ingestion.infrastructure.fills_gap_judge.LLMRouter"
    ) as MockRouter:
        MockRouter.return_value.get_llm_client = AsyncMock(return_value=llm)
        result = await judge.judge("limitation desc", "Source Title", "Candidate Title", "text")

    assert result is None


@pytest.mark.asyncio
async def test_judge_strips_code_fence():
    """LLM bọc ```json ... ``` → parse đúng."""
    judge = _make_judge()
    llm = AsyncMock()
    llm.ainvoke = AsyncMock(return_value=_mock_llm_response(
        '```json\n{"fills": false, "reason": "not related"}\n```'
    ))

    with patch(
        "backend.src.modules.ingestion.infrastructure.fills_gap_judge.LLMRouter"
    ) as MockRouter:
        MockRouter.return_value.get_llm_client = AsyncMock(return_value=llm)
        result = await judge.judge("limitation desc", "Source Title", "Candidate Title", "text")

    assert result is not None
    assert result["fills"] is False
