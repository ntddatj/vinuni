"""Unit tests cho handle_ontology_extracted (Story 4.3, AC: 13)."""
from unittest.mock import AsyncMock

import pytest

from backend.src.modules.graph_rag.infrastructure.neo4j_adapter import (
    HANDLER_MAP,
    handle_ontology_extracted,
)


def _make_session() -> tuple:
    queries_run = []

    async def mock_run(query, **params):
        queries_run.append(query)

    session = AsyncMock()
    session.run = AsyncMock(side_effect=mock_run)
    return session, queries_run


def _base_payload(**overrides) -> dict:
    payload = {
        "paper_id": "paper-1",
        "project_id": "proj-1",
        "abstract": "Test abstract",
        "authors": ["Alice"],
        "findings": [],
        "limitations": [],
        "methods": [],
        "datasets": [],
        "topics": [],
        "problems": [],
        "contradicts": [],
        "supports": [],
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_handle_ontology_extracted_merges_finding_and_edge():
    session, queries = _make_session()
    payload = _base_payload(
        findings=[{"id": "paper-1:f:0", "description": "Finding 1", "confidence_score": 0.9}]
    )
    await handle_ontology_extracted(session, payload)

    assert any("MERGE" in q for q in queries)
    assert any("Finding" in q for q in queries)
    assert any("HAS_FINDING" in q for q in queries)


@pytest.mark.asyncio
async def test_handle_ontology_extracted_merges_limitation():
    session, queries = _make_session()
    payload = _base_payload(
        limitations=[{"id": "paper-1:l:0", "description": "Limitation 1"}]
    )
    await handle_ontology_extracted(session, payload)

    assert any("Limitation" in q for q in queries)
    assert any("HAS_LIMITATION" in q for q in queries)


@pytest.mark.asyncio
async def test_handle_ontology_extracted_merges_contradicts():
    session, queries = _make_session()
    payload = _base_payload(
        findings=[
            {"id": "paper-1:f:0", "description": "F1", "confidence_score": 0.8},
            {"id": "paper-1:f:1", "description": "F2", "confidence_score": 0.7},
        ],
        contradicts=[{"from_id": "paper-1:f:0", "to_id": "paper-1:f:1"}],
    )
    await handle_ontology_extracted(session, payload)

    assert any("CONTRADICTS" in q for q in queries)


@pytest.mark.asyncio
async def test_handle_ontology_extracted_empty_payload():
    session, queries = _make_session()
    payload = _base_payload()
    # Không nên raise
    await handle_ontology_extracted(session, payload)
    # Chỉ query SET Paper.abstract được gọi (bước 0)
    assert all(q is not None for q in queries)


@pytest.mark.asyncio
async def test_handle_ontology_extracted_updates_paper_abstract():
    session, queries = _make_session()
    payload = _base_payload(abstract="Updated abstract")
    await handle_ontology_extracted(session, payload)

    assert any("abstract" in q.lower() or "SET" in q for q in queries)


@pytest.mark.asyncio
async def test_handle_ontology_extracted_skips_finding_without_id():
    """Payload có finding thiếu 'id' → bỏ qua, KHÔNG raise KeyError, không MERGE Finding (P2)."""
    session, queries = _make_session()
    payload = _base_payload(
        findings=[{"description": "Finding không có id", "confidence_score": 0.5}]
    )
    await handle_ontology_extracted(session, payload)

    assert not any("HAS_FINDING" in q for q in queries)


@pytest.mark.asyncio
async def test_handle_ontology_extracted_skips_edge_without_ids():
    """Edge contradicts thiếu from_id/to_id → bỏ qua, không raise (P2)."""
    session, queries = _make_session()
    payload = _base_payload(contradicts=[{"from_id": "paper-1:f:0"}])
    await handle_ontology_extracted(session, payload)

    assert not any("CONTRADICTS" in q for q in queries)


@pytest.mark.asyncio
async def test_ontology_handler_in_handler_map():
    assert "ONTOLOGY_EXTRACTED" in HANDLER_MAP
    assert HANDLER_MAP["ONTOLOGY_EXTRACTED"] is handle_ontology_extracted


@pytest.mark.asyncio
async def test_handle_ontology_extracted_merges_method():
    session, queries = _make_session()
    payload = _base_payload(
        methods=[{"id": "paper-1:m:0", "name": "SVM", "description": "Support Vector Machine"}]
    )
    await handle_ontology_extracted(session, payload)

    assert any("Method" in q for q in queries)
    assert any("HAS_METHOD" in q for q in queries)


@pytest.mark.asyncio
async def test_handle_ontology_extracted_merges_dataset():
    session, queries = _make_session()
    payload = _base_payload(
        datasets=[{"id": "paper-1:d:0", "name": "ImageNet", "description": "Large image dataset"}]
    )
    await handle_ontology_extracted(session, payload)

    assert any("Dataset" in q for q in queries)
    assert any("USES_DATASET" in q for q in queries)


@pytest.mark.asyncio
async def test_handle_ontology_extracted_merges_topic():
    session, queries = _make_session()
    payload = _base_payload(
        topics=[{"id": "paper-1:t:0", "name": "Computer Vision"}]
    )
    await handle_ontology_extracted(session, payload)

    assert any("Topic" in q for q in queries)
    assert any("HAS_TOPIC" in q for q in queries)


@pytest.mark.asyncio
async def test_handle_ontology_extracted_merges_supports():
    session, queries = _make_session()
    payload = _base_payload(
        findings=[
            {"id": "paper-1:f:0", "description": "F1", "confidence_score": 0.8},
            {"id": "paper-1:f:1", "description": "F2", "confidence_score": 0.7},
        ],
        supports=[{"from_id": "paper-1:f:0", "to_id": "paper-1:f:1"}],
    )
    await handle_ontology_extracted(session, payload)

    assert any("SUPPORTS" in q for q in queries)
