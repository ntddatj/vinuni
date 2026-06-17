import logging

logger = logging.getLogger(__name__)

MAX_TEXT_LENGTH = 4000


class DocumentParser:
    def extract_text(self, file_path: str, mime_type: str) -> str:
        try:
            if mime_type == "application/pdf":
                return self._extract_pdf(file_path)
            elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                return self._extract_docx(file_path)
        except Exception as e:
            logger.warning("DocumentParser: lỗi đọc '%s': %s", file_path, e)
        return ""

    def _extract_pdf(self, file_path: str) -> str:
        import fitz  # PyMuPDF

        doc = fitz.open(file_path)
        try:
            text = ""
            for page_num in range(min(2, len(doc))):
                text += doc[page_num].get_text()
        finally:
            doc.close()
        return text[:MAX_TEXT_LENGTH]

    def _extract_docx(self, file_path: str) -> str:
        import mammoth

        with open(file_path, "rb") as f:
            result = mammoth.extract_raw_text(f)
        return result.value[:MAX_TEXT_LENGTH]
