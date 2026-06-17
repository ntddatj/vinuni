"""Unit tests for SearchPapersUseCase với BroadQueryDetector."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.src.modules.search.application.use_cases import SearchPapersUseCase
from backend.src.modules.search.domain.entities import (
    ClientSearchResult,
    PaperResult,
    SearchResponse,
)
from backend.src.modules.search.infrastructure.broad_query_detector import BroadQueryDetector


def make_paper(title: str, doi: str | None = None, arxiv_id: str | None = None) -> PaperResult:
    return PaperResult(
        title=title,
        authors=["Author"],
        year=2024,
        abstract="Abstract",
        doi=doi,
        arxiv_id=arxiv_id,
        url="https://example.com",
        pdf_url=None,
        source="arxiv",
    )


@pytest.fixture
def arxiv_client():
    client = AsyncMock()
    client.search.return_value = ClientSearchResult(
        papers=[make_paper("Paper A", arxiv_id="1234.5678")],
        total_available=5,
    )
    return client


@pytest.fixture
def s2_client():
    client = AsyncMock()
    client.search.return_value = ClientSearchResult(
        papers=[make_paper("Paper B", doi="10.1234/test")],
        total_available=3,
    )
    return client


@pytest.fixture
def cache():
    c = AsyncMock()
    c.get.return_value = None
    return c


@pytest.fixture
def detector():
    d = AsyncMock(spec=BroadQueryDetector)
    d.detect.return_value = (False, [])
    return d


@pytest.fixture
def use_case(arxiv_client, s2_client, cache, detector):
    return SearchPapersUseCase(arxiv=arxiv_client, s2=s2_client, cache=cache, detector=detector)


@pytest.mark.asyncio
async def test_execute_returns_merged_results(use_case, detector):
    response = await use_case.execute("transformer", 10)

    assert len(response.results) == 2
    assert response.is_broad_query is False
    assert response.suggestions == []
    assert response.warnings == []


@pytest.mark.asyncio
async def test_broad_query_detected(use_case, arxiv_client, s2_client, detector):
    arxiv_client.search.return_value = ClientSearchResult(
        papers=[make_paper("Paper A", arxiv_id="1234.5678")],
        total_available=200,
    )
    s2_client.search.return_value = ClientSearchResult(
        papers=[],
        total_available=100,
    )
    detector.detect.return_value = (True, ["NLP", "Computer Vision", "RL"])

    response = await use_case.execute("AI", 10)

    assert response.is_broad_query is True
    assert response.suggestions == ["NLP", "Computer Vision", "RL"]
    detector.detect.assert_called_once_with("AI", 200)


@pytest.mark.asyncio
async def test_broad_query_detector_receives_max_total(use_case, arxiv_client, s2_client, detector):
    arxiv_client.search.return_value = ClientSearchResult(papers=[], total_available=30)
    s2_client.search.return_value = ClientSearchResult(papers=[], total_available=80)
    detector.detect.return_value = (True, ["Subfield A"])

    await use_case.execute("Machine Learning", 10)

    detector.detect.assert_called_once_with("Machine Learning", 80)


@pytest.mark.asyncio
async def test_broad_query_gemini_fails_graceful_fallback(use_case, arxiv_client, s2_client, cache, detector):
    arxiv_client.search.return_value = ClientSearchResult(papers=[], total_available=200)
    s2_client.search.return_value = ClientSearchResult(papers=[], total_available=100)
    detector.detect.return_value = (True, [])

    response = await use_case.execute("AI", 10)

    assert response.is_broad_query is True
    assert response.suggestions == []
    # Không cache khi broad nhưng không có suggestions (Gemini lỗi) → lần sau retry LLM
    cache.set.assert_not_called()


@pytest.mark.asyncio
async def test_broad_query_with_suggestions_is_cached(use_case, arxiv_client, s2_client, cache, detector):
    arxiv_client.search.return_value = ClientSearchResult(papers=[], total_available=200)
    s2_client.search.return_value = ClientSearchResult(papers=[], total_available=100)
    detector.detect.return_value = (True, ["NLP", "Computer Vision"])

    await use_case.execute("AI", 10)

    cache.set.assert_called_once()


@pytest.mark.asyncio
async def test_not_broad_query_when_below_threshold(use_case, arxiv_client, s2_client, detector):
    arxiv_client.search.return_value = ClientSearchResult(papers=[], total_available=10)
    s2_client.search.return_value = ClientSearchResult(papers=[], total_available=8)
    detector.detect.return_value = (False, [])

    response = await use_case.execute("specific narrow query", 10)

    assert response.is_broad_query is False
    assert response.suggestions == []


@pytest.mark.asyncio
async def test_cache_hit_skips_search(arxiv_client, s2_client, cache, detector):
    cached = SearchResponse(
        results=[make_paper("Cached Paper")],
        warnings=[],
        is_broad_query=True,
        suggestions=["NLP"],
    )
    cache.get.return_value = cached
    use_case = SearchPapersUseCase(arxiv=arxiv_client, s2=s2_client, cache=cache, detector=detector)

    response = await use_case.execute("AI", 10)

    assert response.is_broad_query is True
    assert response.suggestions == ["NLP"]
    arxiv_client.search.assert_not_called()
    detector.detect.assert_not_called()


@pytest.mark.asyncio
async def test_degraded_result_not_cached(arxiv_client, s2_client, cache, detector):
    s2_client.search.side_effect = Exception("S2 down")
    arxiv_client.search.return_value = ClientSearchResult(papers=[], total_available=5)
    detector.detect.return_value = (False, [])

    use_case = SearchPapersUseCase(arxiv=arxiv_client, s2=s2_client, cache=cache, detector=detector)
    response = await use_case.execute("query", 10)

    assert "semantic_scholar_timeout" in response.warnings
    cache.set.assert_not_called()
