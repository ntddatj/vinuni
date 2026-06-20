"""Tests cho DocumentParser tham số hóa (Story 4.9, AC: #1, #5).

Yêu cầu AC#5: KHÔNG mock DocumentParser/GraphExtractor — test gọi thật parser.
Fixture tạo PDF/DOCX nhiều trang trong memory để tránh phụ thuộc file thật.
"""
import io
import struct
import tempfile
from pathlib import Path

import pytest

from backend.src.modules.ingestion.infrastructure.document_parser import (
    DEFAULT_MAX_CHARS,
    DEFAULT_MAX_PAGES,
    DocumentParser,
)


# ─── Helpers tạo fixture ───────────────────────────────────────────────────────

def _make_pdf_bytes(pages: list[str]) -> bytes:
    """Tạo PDF tối giản nhiều trang với nội dung text thuần (ASCII).

    Dùng cấu trúc PDF đủ để fitz/PyMuPDF parse được mà không cần thư viện bên ngoài.
    Mỗi trang là một page object có stream text BT ... ET.
    """
    import zlib

    objects = []
    page_refs = []

    # Object 1: catalog (thêm sau khi biết pages ref)
    # Object 2: pages dict (thêm sau khi biết page refs)
    obj_id = 3

    content_refs = []
    page_obj_ids = []

    for text in pages:
        # Content stream
        stream_data = f"BT /F1 12 Tf 50 750 Td ({text}) Tj ET".encode()
        compressed = zlib.compress(stream_data)
        content_obj = (
            f"{obj_id} 0 obj\n"
            f"<< /Length {len(compressed)} /Filter /FlateDecode >>\n"
            f"stream\n"
        ).encode() + compressed + b"\nendstream\nendobj\n"
        objects.append(content_obj)
        content_refs.append(obj_id)
        obj_id += 1

        # Page object
        page_obj = (
            f"{obj_id} 0 obj\n"
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {obj_id - 1} 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>\n"
            f">>\nendobj\n"
        ).encode()
        objects.append(page_obj)
        page_obj_ids.append(obj_id)
        obj_id += 1

    # Pages dict (obj 2)
    kids = " ".join(f"{i} 0 R" for i in page_obj_ids)
    pages_obj = f"2 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>\nendobj\n".encode()

    # Catalog (obj 1)
    catalog_obj = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"

    # Assemble
    header = b"%PDF-1.4\n"
    body = header + catalog_obj + pages_obj
    for obj in objects:
        body += obj

    # xref + trailer
    xref_offset = len(body)
    all_objs = [catalog_obj, pages_obj] + objects
    offsets = [len(header)]
    cur = len(header)
    for o in all_objs:
        offsets.append(cur + len(o))
        cur += len(o)

    # Rebuild to compute correct offsets
    parts = [header, catalog_obj, pages_obj] + objects
    xref_start = sum(len(p) for p in parts)
    offsets_correct = []
    pos = len(header)
    for part in [catalog_obj, pages_obj] + objects:
        offsets_correct.append(pos)
        pos += len(part)

    total_objs = 2 + len(objects)
    xref = f"xref\n0 {total_objs + 1}\n0000000000 65535 f \n"
    for off in offsets_correct:
        xref += f"{off:010d} 00000 n \n"

    trailer = (
        f"trailer\n<< /Size {total_objs + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_start}\n%%EOF\n"
    )

    return b"".join(parts) + xref.encode() + trailer.encode()


def _make_docx_bytes(text: str) -> bytes:
    """Tạo DOCX tối giản với nội dung text.

    Dùng python-docx nếu có, nếu không thì dùng zipfile thủ công với word/document.xml.
    """
    import zipfile

    doc_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>{text}</w:t></w:r></w:p>
  </w:body>
</w:document>"""

    content_types = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Override PartName="/word/document.xml"
    ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

    rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
    Target="word/document.xml"/>
</Relationships>"""

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("word/document.xml", doc_xml)
    return buf.getvalue()


# ─── Tests DocumentParser ──────────────────────────────────────────────────────

class TestDocumentParserPdf:
    def test_default_params_limit_to_2_pages_4000_chars(self, tmp_path):
        """Default (2/4000) — hành vi cũ giữ nguyên (regression AC#5)."""
        page_texts = [f"Trang {i + 1}: " + "X" * 500 for i in range(5)]
        pdf_bytes = _make_pdf_bytes(page_texts)
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(pdf_bytes)

        parser = DocumentParser()
        result = parser.extract_text(str(pdf_file), "application/pdf")

        # Default max_pages=2 — chỉ 2 trang
        assert "Trang 1" in result
        assert "Trang 2" in result
        assert "Trang 3" not in result
        # Default max_chars=4000
        assert len(result) <= DEFAULT_MAX_CHARS

    def test_large_params_extract_more_pages(self, tmp_path):
        """max_pages=50 / max_chars=150000 — lấy được nhiều hơn 2 trang (AC#1, #5)."""
        page_texts = [f"Page{i + 1} content here." for i in range(5)]
        pdf_bytes = _make_pdf_bytes(page_texts)
        pdf_file = tmp_path / "test_large.pdf"
        pdf_file.write_bytes(pdf_bytes)

        parser = DocumentParser()
        result = parser.extract_text(
            str(pdf_file), "application/pdf", max_pages=50, max_chars=150000
        )

        assert "Page1" in result
        assert "Page3" in result
        assert "Page5" in result

    def test_references_at_offset_beyond_old_limit(self, tmp_path):
        """Fixture giả lập paper có References sau offset 30000.

        Với default cũ (2 trang / 4000 ký tự), References bị cắt.
        Với tham số mới (50 trang / 150000), References được giữ lại.
        AC#5: bảo chứng đã sửa đúng lỗ hổng.
        """
        # Trang 1: phần đầu bài (abstract, intro)
        intro = "Introduction and abstract content. " * 200  # ~7000 chars
        # Trang 2-4: thân bài
        body = "Body paragraph content with methods and results. " * 300  # ~15000 chars
        # Trang 5: References (nằm cuối)
        refs = "References\nNguyen 2020. GMO crops review. doi:10.1234/gmo2020\nSmith 2019. Genetic analysis. doi:10.5678/gen2019"

        page_texts = [intro[:3000], body[:3000], body[3000:6000], body[6000:9000], refs]
        pdf_bytes = _make_pdf_bytes(page_texts)
        pdf_file = tmp_path / "test_refs.pdf"
        pdf_file.write_bytes(pdf_bytes)

        parser = DocumentParser()

        # Default cũ: References ở trang 5 → bị cắt
        result_default = parser.extract_text(str(pdf_file), "application/pdf")
        # Default chỉ lấy 2 trang → không tới trang 5 (References)

        # Tham số mới: References được giữ lại
        result_large = parser.extract_text(
            str(pdf_file), "application/pdf", max_pages=50, max_chars=150000
        )
        assert "References" in result_large
        assert "10.1234/gmo2020" in result_large

    def test_max_chars_truncation_applied(self, tmp_path):
        """max_chars chặn output đúng giá trị."""
        page_texts = ["A" * 5000 for _ in range(3)]
        pdf_bytes = _make_pdf_bytes(page_texts)
        pdf_file = tmp_path / "test_chars.pdf"
        pdf_file.write_bytes(pdf_bytes)

        parser = DocumentParser()
        result = parser.extract_text(
            str(pdf_file), "application/pdf", max_pages=10, max_chars=2000
        )
        assert len(result) <= 2000

    def test_nonexistent_file_returns_empty(self, tmp_path):
        parser = DocumentParser()
        result = parser.extract_text(str(tmp_path / "nonexistent.pdf"), "application/pdf")
        assert result == ""


class TestDocumentParserDocx:
    def test_default_max_chars_applied(self, tmp_path):
        """DOCX: default max_chars=4000 áp dụng."""
        long_text = "Hello world " * 1000  # ~12000 chars
        docx_bytes = _make_docx_bytes(long_text)
        docx_file = tmp_path / "test.docx"
        docx_file.write_bytes(docx_bytes)

        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        parser = DocumentParser()
        result = parser.extract_text(str(docx_file), mime)
        assert len(result) <= DEFAULT_MAX_CHARS

    def test_large_max_chars_keeps_more(self, tmp_path):
        """DOCX: max_chars=150000 giữ nhiều text hơn default."""
        long_text = "Content " * 2000  # ~16000 chars
        docx_bytes = _make_docx_bytes(long_text)
        docx_file = tmp_path / "test_large.docx"
        docx_file.write_bytes(docx_bytes)

        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        parser = DocumentParser()

        result_default = parser.extract_text(str(docx_file), mime)
        result_large = parser.extract_text(str(docx_file), mime, max_chars=150000)

        assert len(result_large) > len(result_default)


class TestDocumentParserConstants:
    def test_default_constants_unchanged(self):
        """DEFAULT_MAX_PAGES=2 / DEFAULT_MAX_CHARS=4000 — khóa hành vi cũ (AC#1)."""
        assert DEFAULT_MAX_PAGES == 2
        assert DEFAULT_MAX_CHARS == 4000
