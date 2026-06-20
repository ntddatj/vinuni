"""Reference matcher — khớp references thô (từ LLM) với Paper đã có trong DB.

Thuần Python (unicodedata + difflib stdlib), không I/O, không async → dễ unit test.
Dùng trong graph_extract_task để emit CITES events (Story 4.6).
"""
import difflib
import re
import unicodedata

TITLE_MATCH_THRESHOLD = 0.85

_DOI_PREFIXES = (
    "https://doi.org/",
    "http://doi.org/",
    "https://dx.doi.org/",
    "http://dx.doi.org/",
    "doi:",
)


def normalize_title(s: str) -> str:
    """Chuẩn hóa title: lowercase, bỏ dấu, bỏ ký tự đặc biệt, gộp khoảng trắng."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def normalize_doi(s: str | None) -> str | None:
    """Chuẩn hóa DOI: lowercase, bỏ tiền tố URL/doi:. Trả None nếu rỗng."""
    if not s:
        return None
    s = s.strip().lower()
    for prefix in _DOI_PREFIXES:
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    return s or None


def match_reference(ref: dict, candidates: list[dict]) -> str | None:
    """Khớp 1 reference với danh sách candidate papers trong cùng project.

    Thứ tự ưu tiên:
    1. DOI exact (sau normalize) — nếu cả 2 có DOI.
    2. Fuzzy title (difflib.SequenceMatcher ratio >= TITLE_MATCH_THRESHOLD).

    Args:
        ref: dict có keys 'title', 'doi' (optional).
        candidates: list dict có keys 'id', 'title', 'doi'.

    Returns:
        id của candidate khớp, hoặc None nếu không khớp.
    """
    ref_doi = normalize_doi(ref.get("doi"))
    if ref_doi:
        for c in candidates:
            if normalize_doi(c.get("doi")) == ref_doi:
                return c["id"]

    ref_title = normalize_title(ref.get("title", ""))
    if not ref_title:
        return None

    best_id, best_ratio = None, 0.0
    for c in candidates:
        ratio = difflib.SequenceMatcher(
            None, ref_title, normalize_title(c.get("title", ""))
        ).ratio()
        if ratio > best_ratio:
            best_id, best_ratio = c["id"], ratio

    return best_id if best_ratio >= TITLE_MATCH_THRESHOLD else None
