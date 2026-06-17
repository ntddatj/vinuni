"""Unit tests cho GetSuggestionsUseCase (AC #1, #2)."""
import pytest
from backend.src.modules.orchestrator.application.dtos import GetSuggestionsDTO
from backend.src.modules.orchestrator.application.use_cases import GetSuggestionsUseCase


def _uc() -> GetSuggestionsUseCase:
    return GetSuggestionsUseCase()


def test_suggestions_empty_project_returns_upload_first():
    result = _uc().execute(GetSuggestionsDTO(active_tab="library", document_count=0, has_draft=False))
    assert len(result) == 3
    assert result[0].action_key == "open_upload"


def test_suggestions_with_documents_no_draft():
    result = _uc().execute(GetSuggestionsDTO(active_tab="library", document_count=5, has_draft=False))
    assert len(result) == 3
    action_keys = [r.action_key for r in result]
    assert "open_upload" not in action_keys
    assert "navigate_graph" in action_keys


def test_suggestions_with_draft():
    result = _uc().execute(GetSuggestionsDTO(active_tab="library", document_count=5, has_draft=True))
    assert result[0].action_key == "navigate_writing"


def test_suggestions_all_have_label_and_action_key():
    result = _uc().execute(GetSuggestionsDTO(active_tab="library", document_count=0, has_draft=False))
    for item in result:
        assert item.label
        assert item.action_key
