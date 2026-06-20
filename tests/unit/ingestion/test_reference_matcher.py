"""Unit tests cho reference_matcher.py (Story 4.6, AC: 9)."""
import pytest

from backend.src.modules.ingestion.infrastructure.reference_matcher import (
    match_reference,
    normalize_doi,
    normalize_title,
)


# ---------- normalize_title ----------

def test_normalize_title_strips_diacritics_punct_case():
    result = normalize_title("Đánh Giá: Mô-hình AI!")
    # lowercase, bỏ dấu, bỏ ký tự đặc biệt (: - !)
    assert result == result.lower()
    assert ":" not in result
    assert "!" not in result
    assert "-" not in result
    # ký tự có dấu phải được bỏ dấu
    assert "a" in result  # Đánh → danh (a)
    assert "i" in result  # AI → ai


def test_normalize_title_empty_input():
    assert normalize_title("") == ""
    assert normalize_title("   ") == ""


def test_normalize_title_collapses_whitespace():
    result = normalize_title("  Deep   Learning  ")
    assert result == "deep learning"


def test_normalize_title_removes_special_chars():
    result = normalize_title("Attention Is All You Need (2017)")
    assert "(" not in result
    assert ")" not in result
    assert result == "attention is all you need 2017"


# ---------- normalize_doi ----------

def test_normalize_doi_strips_https_prefix():
    assert normalize_doi("https://doi.org/10.1/AbC") == "10.1/abc"


def test_normalize_doi_strips_http_dx_prefix():
    assert normalize_doi("http://dx.doi.org/10.2/XYZ") == "10.2/xyz"


def test_normalize_doi_strips_doi_colon_prefix():
    assert normalize_doi("doi:10.3/test") == "10.3/test"


def test_normalize_doi_lowercases():
    assert normalize_doi("10.1000/XYZ123") == "10.1000/xyz123"


def test_normalize_doi_returns_none_for_empty():
    assert normalize_doi(None) is None
    assert normalize_doi("") is None
    assert normalize_doi("   ") is None


# ---------- match_reference ----------

def test_match_by_doi_exact():
    """DOI exact match (khác hoa thường/tiền tố) → trả đúng id."""
    ref = {"title": "Some Paper", "doi": "https://doi.org/10.1234/abc"}
    candidates = [
        {"id": "paper-1", "title": "Different Title", "doi": "10.1234/abc"},
        {"id": "paper-2", "title": "Another", "doi": "10.9999/xyz"},
    ]
    assert match_reference(ref, candidates) == "paper-1"


def test_match_by_fuzzy_title_above_threshold():
    """Title gần giống (ratio >= 0.85) → khớp."""
    ref = {"title": "Attention Is All You Need"}
    candidates = [
        {"id": "paper-1", "title": "Attention Is All You Need", "doi": None},
    ]
    assert match_reference(ref, candidates) == "paper-1"


def test_match_returns_none_when_title_too_different():
    """Title khác hẳn → None."""
    ref = {"title": "Quantum Computing Fundamentals"}
    candidates = [
        {"id": "paper-1", "title": "Deep Learning for NLP", "doi": None},
    ]
    assert match_reference(ref, candidates) is None


def test_match_returns_none_when_no_candidate():
    """Candidates rỗng → None."""
    ref = {"title": "Any Paper", "doi": "10.1/x"}
    assert match_reference(ref, []) is None


def test_match_prefers_doi_over_title():
    """DOI khớp candidate A nhưng title gần candidate B → trả A."""
    ref = {"title": "Paper B Similar Title", "doi": "10.111/aaa"}
    candidates = [
        {"id": "paper-A", "title": "Completely Different", "doi": "10.111/aaa"},
        {"id": "paper-B", "title": "Paper B Similar Title", "doi": "10.999/zzz"},
    ]
    assert match_reference(ref, candidates) == "paper-A"


def test_match_ignores_ref_without_title():
    """Reference với title rỗng sau normalize → None (không crash)."""
    ref = {"title": "", "doi": None}
    candidates = [{"id": "paper-1", "title": "Some Paper", "doi": None}]
    assert match_reference(ref, candidates) is None


def test_match_handles_ref_without_doi_key():
    """Reference không có key 'doi' → fallback fuzzy title an toàn."""
    ref = {"title": "Attention Is All You Need"}
    candidates = [
        {"id": "paper-1", "title": "Attention Is All You Need", "doi": None},
    ]
    assert match_reference(ref, candidates) == "paper-1"


def test_match_no_doi_falls_back_to_title():
    """Ref không có DOI → chỉ dùng title matching."""
    ref = {"title": "BERT Pre-training of Deep Bidirectional Transformers"}
    candidates = [
        {"id": "paper-1", "title": "BERT Pre-training of Deep Bidirectional Transformers", "doi": None},
    ]
    result = match_reference(ref, candidates)
    assert result == "paper-1"
