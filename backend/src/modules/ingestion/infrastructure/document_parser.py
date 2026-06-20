import logging

logger = logging.getLogger(__name__)

DEFAULT_MAX_PAGES = 2
DEFAULT_MAX_CHARS = 4000


class DocumentParser:
    def extract_text(
        self,
        file_path: str,
        mime_type: str,
        max_pages: int = DEFAULT_MAX_PAGES,
        max_chars: int = DEFAULT_MAX_CHARS,
    ) -> str:
        try:
            if mime_type == "application/pdf":
                return self._extract_pdf(file_path, max_pages, max_chars)
            elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                return self._extract_docx(file_path, max_chars)
        except Exception as e:
            logger.warning("DocumentParser: lỗi đọc '%s': %s", file_path, e)
        return ""

    def _extract_pdf(self, file_path: str, max_pages: int, max_chars: int) -> str:
        import fitz  # PyMuPDF

        doc = fitz.open(file_path)
        try:
            text = ""
            for page_num in range(min(max_pages, len(doc))):
                text += doc[page_num].get_text()
        finally:
            doc.close()
        return text[:max_chars]

    def _extract_docx(self, file_path: str, max_chars: int) -> str:
        import mammoth

        with open(file_path, "rb") as f:
            result = mammoth.extract_raw_text(f)
        return result.value[:max_chars]
