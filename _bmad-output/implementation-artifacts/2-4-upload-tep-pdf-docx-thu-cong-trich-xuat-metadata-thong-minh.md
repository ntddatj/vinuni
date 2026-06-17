---
baseline_commit: eec0708
---

# Story 2.4: [BE+FE] Upload tệp PDF/DOCX thủ công – Trích xuất metadata thông minh

Status: done

## Story

Với vai trò là người dùng đã đăng nhập,
Tôi muốn upload tệp PDF hoặc DOCX cá nhân và để AI tự động trích xuất tiêu đề, tác giả, năm, tóm tắt,
Để tôi có thể xem lại, chỉnh sửa thông tin AI đề xuất rồi xác nhận đưa tài liệu vào dự án.

## Acceptance Criteria

1. **Given** người dùng click "Upload" trong Tab Thư viện
   **When** chọn file PDF hoặc DOCX (≤ 20MB)
   **Then** frontend gửi `POST /api/ingestion/upload` (multipart/form-data, field `file` + `project_id`)
   **And** backend lưu file vào disk, đọc text từ 2 trang đầu, gọi LLM (gemini-2.5-flash) trích xuất JSON `{title, authors, abstract, year}`
   **And** trả về `{fileId, title, authors, abstract, year}` — HTTP 200

2. **Given** upload thành công, response JSON metadata trả về
   **When** frontend nhận JSON
   **Then** bật Modal "Xác nhận Thông tin" chứa form có 4 trường: Tiêu đề, Tác giả, Năm, Tóm tắt
   **And** mỗi trường có badge `"AI Suggested"` màu `var(--accent-violet)` (nền nhạt, chữ đậm)
   **And** các trường có thể chỉnh sửa trực tiếp

3. **Given** người dùng đã xem/sửa form
   **When** click "Xác nhận"
   **Then** frontend gọi `POST /api/ingestion/confirm` với `{fileId, title, authors, abstract, year, projectId}`
   **And** backend lưu bản ghi `papers` (status=`pending`) và trả về `{documentId, message}` — HTTP 201
   **And** frontend đóng modal, hiển thị Toast thành công "Đã thêm vào hàng đợi xử lý"

4. **Given** file vượt quá 20MB hoặc không phải PDF/DOCX
   **When** user cố gắng upload
   **Then** backend trả về HTTP 422 với message lỗi phù hợp
   **And** frontend hiển thị Toast lỗi

5. **Given** LLM (Gemini) lỗi hoặc timeout khi trích xuất metadata
   **When** xảy ra lỗi LLM
   **Then** backend vẫn trả về HTTP 200 với `{fileId, title: "", authors: [], abstract: "", year: null}`
   **And** lỗi được log WARNING, KHÔNG raise exception
   **And** frontend mở form với các trường rỗng để user tự điền

6. **Given** đang ở tab "Thư viện Tài liệu"
   **When** chuyển ngôn ngữ VI|EN
   **Then** tất cả nhãn button, title modal, label field đổi ngôn ngữ ngay lập tức

> 🔍 **Cách nghiệm thu trực quan:**
> Web UI: Click "Upload Tài liệu", chọn file PDF → chờ ~2s → Modal bật lên với form có các trường điền sẵn từ AI (mỗi trường có badge tím "AI Suggested"). Sửa Tên bài báo, bấm "Xác nhận" → Modal đóng, Toast xanh "Đã thêm vào hàng đợi xử lý" xuất hiện.
> Backend: `curl -X POST http://localhost:8000/api/ingestion/upload -H "Cookie: access_token=..." -F "file=@paper.pdf" -F "project_id=<uuid>"` → nhận JSON `{fileId, title, authors, abstract, year}`.

---

## Tasks / Subtasks

### BACKEND — Module `ingestion` mới

- [x] Task 1: Thêm dependencies vào requirements.txt (AC: #1)
  - [x] 1.1 Thêm `PyMuPDF>=1.24.0` (import `fitz`) — đọc text PDF
  - [x] 1.2 Thêm `mammoth>=1.9.0` — chuyển DOCX sang plain text
  - [x] 1.3 Thêm `python-multipart>=0.0.12` — FastAPI multipart/form-data upload

- [x] Task 2: Tạo Alembic migration cho bảng `papers` (AC: #3)
  - [x] 2.1 Tạo `backend/alembic/versions/004_create_papers_table.py` với schema đầy đủ (xem Dev Notes § DB Schema)
  - [x] 2.2 Tạo `backend/alembic/versions/005_create_uploaded_files_table.py` cho bảng `uploaded_files` (xem Dev Notes § DB Schema)

- [x] Task 3: Tạo module `ingestion` — Domain Layer (AC: #1, #3)
  - [x] 3.1 Tạo `backend/src/modules/ingestion/__init__.py` (rỗng)
  - [x] 3.2 Tạo `backend/src/modules/ingestion/domain/__init__.py` (rỗng)
  - [x] 3.3 Tạo `backend/src/modules/ingestion/domain/entities.py`:
    - Dataclass `UploadedFile(id, project_id, user_id, original_filename, file_path, mime_type, file_size)`
    - Dataclass `ExtractedMetadata(title, authors, abstract, year)` — tất cả nullable
    - Dataclass `Paper(id, project_id, user_id, title, authors, abstract, year, source, file_path, status)`
  - [x] 3.4 Tạo `backend/src/modules/ingestion/domain/exceptions.py`:
    - `FileTooLargeError(max_mb: int)`
    - `UnsupportedFileTypeError(mime_type: str)`
    - `IngestionFileNotFoundError(file_id: str)`

- [x] Task 4: Tạo Infrastructure Layer (AC: #1, #5)
  - [x] 4.1 Tạo `backend/src/modules/ingestion/infrastructure/__init__.py` (rỗng)
  - [x] 4.2 Tạo `backend/src/modules/ingestion/infrastructure/orm_models.py`:
    - `UploadedFileORM` (SQLAlchemy ORM cho bảng `uploaded_files`)
    - `PaperORM` (SQLAlchemy ORM cho bảng `papers`) — xem Dev Notes § DB Schema
  - [x] 4.3 Tạo `backend/src/modules/ingestion/infrastructure/file_storage.py`:
    - Class `LocalFileStorage` với method `save(file_bytes, original_filename, user_id) -> (file_id, file_path)`
    - Lưu vào `data/uploads/{user_id}/{file_id}{ext}`
    - Tạo dir nếu chưa có (`Path.mkdir(parents=True, exist_ok=True)`)
  - [x] 4.4 Tạo `backend/src/modules/ingestion/infrastructure/document_parser.py`:
    - Class `DocumentParser`
    - Method `_extract_pdf(file_path: str) -> str` — dùng `fitz.open()`, lấy text từ trang 0 và 1 (2 trang đầu)
    - Method `_extract_docx(file_path: str) -> str` — dùng `mammoth.extract_raw_text()`, trả về `.value` (first 4000 chars)
    - Method `extract_text(file_path: str, mime_type: str) -> str` — dispatcher theo mime_type
    - Xử lý lỗi: nếu không đọc được → return empty string (KHÔNG raise)
  - [x] 4.5 Tạo `backend/src/modules/ingestion/infrastructure/metadata_extractor.py`:
    - Class `LLMMetadataExtractor` nhận `user_id: str, db: AsyncSession`
    - Method `async extract(text: str, filename: str) -> ExtractedMetadata`
    - Dùng LLMRouter → gemini-2.5-flash, gọi `llm.ainvoke(METADATA_PROMPT)`
    - Parse JSON từ response content (xem Dev Notes § Metadata Extractor Prompt)
    - Graceful fallback: mọi exception → log WARNING, return `ExtractedMetadata(title="", authors=[], abstract="", year=None)`
    - Thêm `_strip_code_fence()` helper (giống BroadQueryDetector pattern đã implement ở Story 2.3)
  - [x] 4.6 Tạo `backend/src/modules/ingestion/infrastructure/postgres_repository.py`:
    - `PostgresUploadedFileRepository` với `save_uploaded_file(entity) -> UploadedFile` và `find_by_id(file_id) -> UploadedFile | None`
    - `PostgresPaperRepository` với `save_paper(entity) -> Paper`

- [x] Task 5: Tạo Application Layer (AC: #1, #2, #3, #4, #5)
  - [x] 5.1 Tạo `backend/src/modules/ingestion/application/__init__.py` (rỗng)
  - [x] 5.2 Tạo `backend/src/modules/ingestion/application/use_cases.py`:
    - `UploadDocumentUseCase.execute(file_bytes, original_filename, project_id, user_id, db) -> dict`
      - Validate: file_size ≤ 20MB (raise `FileTooLargeError`), mime_type in `[application/pdf, application/vnd.openxmlformats-officedocument.wordprocessingml.document]` (raise `UnsupportedFileTypeError`)
      - Determine MIME từ filename extension (.pdf / .docx) nếu không có header
      - Lưu file qua `LocalFileStorage`
      - Lưu bản ghi `UploadedFileORM`
      - Parse text qua `DocumentParser`
      - Extract metadata qua `LLMMetadataExtractor`
      - Return `{file_id, title, authors, abstract, year}`
    - `ConfirmMetadataUseCase.execute(file_id, title, authors, abstract, year, project_id, user_id, db) -> dict`
      - Load `UploadedFileORM` by file_id (raise `IngestionFileNotFoundError` nếu không có)
      - Tạo `PaperORM` với source='manual', status='pending'
      - Lưu vào DB
      - Return `{document_id, message}`

- [x] Task 6: Tạo Presentation Layer (AC: #1, #3, #4)
  - [x] 6.1 Tạo `backend/src/modules/ingestion/presentation/__init__.py` (rỗng)
  - [x] 6.2 Tạo `backend/src/modules/ingestion/presentation/schemas.py`:
    - `UploadResponseSchema(BaseModel)`: `fileId, title, authors, abstract, year` — dùng `alias_generator=to_camel`
    - `ConfirmRequestSchema(BaseModel)`: `fileId, title, authors, abstract, year, projectId`
    - `ConfirmResponseSchema(BaseModel)`: `documentId, message`
  - [x] 6.3 Tạo `backend/src/modules/ingestion/presentation/router.py`:
    - `POST /ingestion/upload` (multipart/form-data): nhận `file: UploadFile`, `project_id: str = Form(...)`
    - `POST /ingestion/confirm`: nhận `ConfirmRequestSchema` body JSON
    - Dùng `get_current_user` dependency từ `backend.src.modules.identity.infrastructure.auth_dependencies`
    - Dùng `get_db` từ `backend.src.shared.infra.database`
    - Map `FileTooLargeError` → HTTP 422, `UnsupportedFileTypeError` → HTTP 422, `IngestionFileNotFoundError` → HTTP 404

- [x] Task 7: Đăng ký router vào main.py (AC: #1)
  - [x] 7.1 Import `IngestionORM` (UploadedFileORM, PaperORM) vào main.py (như pattern của các module khác)
  - [x] 7.2 Import và `app.include_router(ingestion_router, prefix="/api")`

- [x] Task 8: Cập nhật Settings (AC: #1)
  - [x] 8.1 Thêm `upload_dir: str = "data/uploads"` và `max_upload_size_mb: int = 20` vào class `Settings` trong `backend/src/shared/infra/settings.py`

### FRONTEND — Upload UI & Metadata Form

- [x] Task 9: Thêm Types (AC: #1, #3)
  - [x] 9.1 Tạo `frontend/src/types/document.ts`:
    ```typescript
    export interface UploadResponse {
      fileId: string;
      title: string;
      authors: string[];
      abstract: string;
      year: number | null;
    }
    export interface ConfirmRequest {
      fileId: string;
      title: string;
      authors: string[];
      abstract: string;
      year: number | null;
      projectId: string;
    }
    export interface ConfirmResponse {
      documentId: string;
      message: string;
    }
    ```

- [x] Task 10: Thêm API functions (AC: #1, #3)
  - [x] 10.1 Tạo `frontend/src/api/ingestion.ts`:
    - `uploadDocument(file: File, projectId: string): Promise<UploadResponse>` — dùng `FormData`, gọi `apiClient.post('/api/ingestion/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } })`
    - `confirmMetadata(data: ConfirmRequest): Promise<ConfirmResponse>` — gọi `apiClient.post('/api/ingestion/confirm', data)`
    - **QUAN TRỌNG:** dùng `apiClient` từ `@/api/client`, KHÔNG tạo instance mới

- [x] Task 11: Thêm Translation Keys (AC: #6)
  - [x] 11.1 Cập nhật `frontend/src/i18n/translations.ts` — thêm:
    - `'upload.button'`, `'upload.modalTitle'`, `'upload.fieldTitle'`, `'upload.fieldAuthors'`, `'upload.fieldYear'`, `'upload.fieldAbstract'`, `'upload.aiBadge'`, `'upload.confirm'`, `'upload.cancel'`, `'upload.extracting'`, `'upload.successToast'`, `'upload.errorToast'`, `'upload.fileTooLarge'`, `'upload.unsupportedType'`
    - Xem Dev Notes § Translation Keys cho giá trị VI/EN

- [x] Task 12: Tạo UploadModal component (AC: #2, #3, #4, #5, #6)
  - [x] 12.1 Tạo `frontend/src/features/workspace/UploadModal.tsx`:
    - State: `phase: 'idle' | 'extracting' | 'form' | 'confirming'`
    - Phase `idle`: input file ẩn, khi chọn file → validate size ≤ 20MB client-side, validate extension .pdf/.docx → chuyển sang `extracting`
    - Phase `extracting`: hiển thị spinner + `t('upload.extracting')`
    - Phase `form`: hiển thị form 4 trường (Title, Authors, Year, Abstract) — mỗi trường có badge `"AI Suggested"` màu violet
    - Phase `confirming`: disable nút, hiển thị spinner
    - Click "Xác nhận" → `confirmMetadata()` → toast success → `onSuccess(documentId)` callback → `onClose()`
    - Xem Dev Notes § UploadModal State Machine cho chi tiết
  - [x] 12.2 Tạo `frontend/src/features/workspace/UploadModal.module.css`:
    - `.overlay`, `.modal`, `.header`, `.form`, `.fieldGroup`, `.label`, `.aiBadge`, `.input`, `.textarea`, `.footer`, `.confirmButton`, `.cancelButton`, `.spinner`
    - `.aiBadge`: background `rgba(124, 58, 237, 0.1)`, color `var(--accent-violet)`, border-radius 4px, padding 2px 6px, font-size 11px, font-weight 600
    - Xem Dev Notes § CSS Variables cho giá trị

- [x] Task 13: Cập nhật LibraryTab (AC: #1, #2, #3, #6)
  - [x] 13.1 Cập nhật `frontend/src/features/workspace/LibraryTab.tsx`:
    - Nhận prop `projectId: string | null` từ component cha (CenterWorkspace)
    - Thêm state `showUpload: boolean`
    - Thêm nút "Upload Tài liệu" bên cạnh search bar (chỉ render khi `projectId` không null)
    - Render `<UploadModal>` khi `showUpload=true`
    - `onSuccess` callback của UploadModal: close modal + toast + (story 2.5 sẽ refresh library)
    - Xem Dev Notes § LibraryTab Updates

- [x] Task 14: Cập nhật CenterWorkspace để truyền projectId (AC: #1)
  - [x] 14.1 Kiểm tra `frontend/src/features/workspace/CenterWorkspace.tsx` hiện tại có truyền `projectId` vào `LibraryTab` không
  - [x] 14.2 Nếu chưa: cập nhật props của LibraryTab để nhận `projectId`

- [x] Task 15: Viết Tests (AC: #1-6)
  - [x] 15.1 Tạo `frontend/src/features/workspace/__tests__/UploadModal.test.tsx`:
    - Test: hiển thị pha "extracting" khi đang gọi API upload
    - Test: hiển thị form với badge "AI Suggested" sau khi API upload thành công
    - Test: gọi `confirmMetadata` khi click "Xác nhận"
    - Test: hiển thị Toast lỗi khi file quá 20MB
    - Test: đóng modal khi click "Hủy"
  - [x] 15.2 Tạo `tests/unit/ingestion/__init__.py` và `tests/unit/ingestion/test_upload_use_case.py`:
    - Test: `UploadDocumentUseCase` raise `FileTooLargeError` khi file > 20MB
    - Test: `UploadDocumentUseCase` raise `UnsupportedFileTypeError` khi không phải PDF/DOCX
    - Test: Graceful fallback khi LLM lỗi → trả về metadata rỗng
    - Test: `ConfirmMetadataUseCase` lưu Paper với status='pending'

---

## Dev Notes

### ⚠️ LỖI THƯỜNG GẶP CỦA LLM — PHẢI TRÁNH

1. **KHÔNG dùng Tailwind** — CSS Modules + CSS Variables. Dùng `var(--accent-violet)`, `var(--surface-raised)`, `var(--border-hairline)`, `var(--rounded-md)`, `var(--ink-primary)`, `var(--ink-secondary)`.

2. **KHÔNG dùng `i18next`** — dùng `useTranslation()` từ `frontend/src/i18n/useTranslation.ts`.

3. **KHÔNG quên tham số thứ 2 của `getErrorMessage(err, 'fallback')`** — thiếu sẽ lỗi `TS2554`.

4. **KHÔNG tạo Axios client mới** — dùng `apiClient` từ `frontend/src/api/client.ts`. Import: `import apiClient from '@/api/client'`.

5. **KHÔNG dùng `apiClient.post(url, formData)` thuần** — phải set header `'Content-Type': 'multipart/form-data'` khi upload file. Axios sẽ tự thêm boundary nếu truyền FormData.

6. **KHÔNG bỏ `MemoryRouter`** khi render component có `Link`/`useNavigate` trong test.

7. **KHÔNG tự detect MIME type bằng Content-Type header từ browser** — browser gửi `application/octet-stream` với tên không quen. Detect MIME bằng **extension filename** (`.pdf` → `application/pdf`, `.docx` → `application/vnd.openxmlformats-officedocument.wordprocessingml.document`).

8. **KHÔNG để LLM failure block upload** — `LLMMetadataExtractor` phải wrap mọi LLM call trong try/except, graceful fallback return `ExtractedMetadata` với tất cả field rỗng.

9. **KHÔNG hardcode đường dẫn file** — dùng `settings.upload_dir` từ `get_settings()`.

10. **KHÔNG quên TranslationKey type** — `t()` nhận `TranslationKey`, không phải `string`. Thêm key mới vào `translations.ts` trước khi dùng trong `t()`.

11. **KHÔNG dùng `alias_generator=to_camel` mà thiếu `populate_by_name=True`** — thiếu field sẽ báo validation error khi khởi tạo schema bằng snake_case.

12. **KHÔNG quên import PaperORM và UploadedFileORM** vào `main.py` để SQLAlchemy auto-create tables trong dev.

13. **KHÔNG dùng `PyPDF2` hay `pdfplumber`** — dự án dùng `PyMuPDF` (import `fitz`). Module tên là `fitz`, cài qua `PyMuPDF`.

---

### § DB Schema — Bảng `papers` và `uploaded_files`

**Migration 004 — bảng `papers`:**
```python
# backend/alembic/versions/004_create_papers_table.py
op.create_table(
    "papers",
    sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
    sa.Column("title", sa.String(500), nullable=False, server_default=""),
    sa.Column("authors", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
    sa.Column("abstract", sa.Text(), nullable=True),
    sa.Column("year", sa.Integer(), nullable=True),
    sa.Column("source", sa.String(50), nullable=False, server_default="manual"),
    # 'manual' | 'arxiv' | 'semantic_scholar'
    sa.Column("doi", sa.String(200), nullable=True),
    sa.Column("arxiv_id", sa.String(100), nullable=True),
    sa.Column("url", sa.String(2000), nullable=True),
    sa.Column("pdf_url", sa.String(2000), nullable=True),
    sa.Column("file_path", sa.String(500), nullable=True),  # chỉ có với source='manual'
    sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
    # 'pending' | 'processing' | 'indexed' | 'failed'
    sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
)
op.create_index("idx_papers_project_id", "papers", ["project_id"])
op.create_index("idx_papers_user_id", "papers", ["user_id"])
op.create_index("idx_papers_status", "papers", ["status"])
```

**Migration 005 — bảng `uploaded_files`:**
```python
# backend/alembic/versions/005_create_uploaded_files_table.py
op.create_table(
    "uploaded_files",
    sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
    sa.Column("original_filename", sa.String(255), nullable=False),
    sa.Column("file_path", sa.String(500), nullable=False),
    sa.Column("mime_type", sa.String(100), nullable=False),
    sa.Column("file_size", sa.BigInteger(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
)
op.create_index("idx_uploaded_files_project_id", "uploaded_files", ["project_id"])
```

---

### § Metadata Extractor Prompt

```python
METADATA_EXTRACTION_PROMPT = """Extract bibliographic metadata from this academic text.
Return ONLY a JSON object with these exact keys: title, authors, abstract, year.

Rules:
- title: string (full paper title, empty string if not found)
- authors: list of strings (author names, empty list if not found)
- abstract: string (paper abstract or summary, empty string if not found)
- year: integer or null (publication year 4 digits, null if not found)

Text to analyze (first pages):
{text}

Filename hint: {filename}

Respond with ONLY the JSON object, no markdown:"""
```

**Parse pattern (giống BroadQueryDetector đã implement):**
```python
async def extract(self, text: str, filename: str) -> ExtractedMetadata:
    try:
        router = LLMRouter(self._db)
        llm = await router.get_llm_client(self._user_id, model_name="gemini-2.5-flash")
        prompt = METADATA_EXTRACTION_PROMPT.format(text=text[:4000], filename=filename)
        result = await llm.ainvoke(prompt)
        content = self._strip_code_fence(result.content.strip())
        data = json.loads(content)
        return ExtractedMetadata(
            title=str(data.get("title", "")) or "",
            authors=[str(a) for a in data.get("authors", []) if a],
            abstract=str(data.get("abstract", "")) or "",
            year=int(data["year"]) if data.get("year") and str(data["year"]).isdigit() else None,
        )
    except Exception as e:
        logger.warning("LLMMetadataExtractor: lỗi trích xuất metadata từ '%s': %s", filename, e)
        return ExtractedMetadata(title="", authors=[], abstract="", year=None)

@staticmethod
def _strip_code_fence(text: str) -> str:
    """Gỡ bỏ ```json ... ``` wrapper nếu LLM thêm vào."""
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return text.strip()
```

---

### § Document Parser

```python
# backend/src/modules/ingestion/infrastructure/document_parser.py
import logging
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)
MAX_TEXT_LENGTH = 4000  # chars — gửi tối đa 4000 ký tự đầu lên LLM

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
        doc = fitz.open(file_path)
        text = ""
        for page_num in range(min(2, len(doc))):  # tối đa 2 trang đầu
            text += doc[page_num].get_text()
        doc.close()
        return text[:MAX_TEXT_LENGTH]

    def _extract_docx(self, file_path: str) -> str:
        import mammoth
        with open(file_path, "rb") as f:
            result = mammoth.extract_raw_text(f)
        return result.value[:MAX_TEXT_LENGTH]
```

---

### § File Storage Pattern

```python
# backend/src/modules/ingestion/infrastructure/file_storage.py
import uuid
from pathlib import Path
from backend.src.shared.infra.settings import get_settings

class LocalFileStorage:
    def save(self, file_bytes: bytes, original_filename: str, user_id: str) -> tuple[str, str]:
        """Returns (file_id, file_path)"""
        settings = get_settings()
        file_id = str(uuid.uuid4())
        ext = Path(original_filename).suffix.lower()
        target_dir = Path(settings.upload_dir) / user_id
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = str(target_dir / f"{file_id}{ext}")
        Path(file_path).write_bytes(file_bytes)
        return file_id, file_path
```

---

### § Router Pattern — Upload Endpoint

```python
# backend/src/modules/ingestion/presentation/router.py
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.modules.identity.domain.entities import User
from backend.src.modules.identity.infrastructure.auth_dependencies import get_current_user
from backend.src.shared.infra.database import get_db

router = APIRouter(tags=["ingestion"])

MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20MB

ALLOWED_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

@router.post("/ingestion/upload", response_model=UploadResponseSchema)
async def upload_document(
    file: UploadFile = File(...),
    project_id: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UploadResponseSchema:
    file_bytes = await file.read()
    # Detect MIME từ extension
    ext = Path(file.filename or "").suffix.lower()
    mime_type = ALLOWED_MIME_TYPES.get(ext)
    ...
```

---

### § UploadModal State Machine

```
[idle] → user chọn file → validate (size, type) → [extracting] → gọi uploadDocument() API
  → success: set metadata → [form]
  → error: toast lỗi → [idle]

[form] → user chỉnh sửa trường → click "Xác nhận" → [confirming]
  → gọi confirmMetadata() API
  → success: onSuccess(documentId) + toast → close modal
  → error: toast lỗi → [form]

[form] → click "Hủy" → close modal / onClose()
```

**State trong React:**
```tsx
type Phase = 'idle' | 'extracting' | 'form' | 'confirming';
const [phase, setPhase] = useState<Phase>('idle');
const [uploadResponse, setUploadResponse] = useState<UploadResponse | null>(null);
const [title, setTitle] = useState('');
const [authors, setAuthors] = useState(''); // comma-separated string
const [year, setYear] = useState('');
const [abstract, setAbstract] = useState('');
```

**Handling file input:**
```tsx
const fileInputRef = useRef<HTMLInputElement>(null);

async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
  const file = e.target.files?.[0];
  if (!file) return;
  
  // Validate size client-side
  if (file.size > 20 * 1024 * 1024) {
    toast.error(t('upload.fileTooLarge'));
    return;
  }
  // Validate extension
  const ext = file.name.split('.').pop()?.toLowerCase();
  if (!['pdf', 'docx'].includes(ext ?? '')) {
    toast.error(t('upload.unsupportedType'));
    return;
  }
  
  setPhase('extracting');
  try {
    const result = await uploadDocument(file, projectId!);
    setUploadResponse(result);
    setTitle(result.title);
    setAuthors(result.authors.join(', '));
    setYear(result.year?.toString() ?? '');
    setAbstract(result.abstract);
    setPhase('form');
  } catch (err) {
    toast.error(getErrorMessage(err, t('upload.errorToast')));
    setPhase('idle');
  }
}
```

**Confirm handler:**
```tsx
async function handleConfirm() {
  if (!uploadResponse || !projectId) return;
  setPhase('confirming');
  try {
    const result = await confirmMetadata({
      fileId: uploadResponse.fileId,
      title: title.trim(),
      authors: authors.split(',').map(a => a.trim()).filter(Boolean),
      abstract: abstract.trim(),
      year: year ? parseInt(year, 10) : null,
      projectId,
    });
    toast.success(t('upload.successToast'));
    onSuccess(result.documentId);
    onClose();
  } catch (err) {
    toast.error(getErrorMessage(err, t('upload.errorToast')));
    setPhase('form');
  }
}
```

---

### § CSS Variables — UploadModal

```css
/* frontend/src/features/workspace/UploadModal.module.css */
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: var(--surface-base);
  border: 1px solid var(--border-hairline);
  border-radius: var(--rounded-lg);
  width: 480px;
  max-width: 95vw;
  max-height: 90vh;
  overflow-y: auto;
  padding: 24px;
}

.aiBadge {
  background: rgba(124, 58, 237, 0.1); /* accent-violet ~10% */
  color: var(--accent-violet);
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 11px;
  font-weight: 600;
  display: inline-block;
  margin-left: 6px;
}

.fieldGroup {
  margin-bottom: 16px;
}

.label {
  display: flex;
  align-items: center;
  font-size: 13px;
  font-weight: 500;
  color: var(--ink-primary);
  margin-bottom: 6px;
}

.input {
  width: 100%;
  border: 1px solid var(--border-hairline);
  border-radius: var(--rounded-md);
  padding: 8px 10px;
  font-size: 14px;
  background: var(--surface-base);
  color: var(--ink-primary);
  box-sizing: border-box;
}

.input:focus {
  outline: none;
  border-color: var(--accent-blue);
}

.textarea {
  resize: vertical;
  min-height: 80px;
}

.confirmButton {
  background: var(--accent-blue);
  color: white;
  border: none;
  border-radius: var(--rounded-md);
  padding: 8px 20px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
}

.confirmButton:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.cancelButton {
  background: transparent;
  color: var(--ink-secondary);
  border: 1px solid var(--border-hairline);
  border-radius: var(--rounded-md);
  padding: 8px 20px;
  font-size: 14px;
  cursor: pointer;
  margin-right: 8px;
}
```

---

### § Translation Keys

```typescript
// Thêm vào translations.ts (bên trên `} as const;`)
'upload.button': { vi: 'Upload Tài liệu', en: 'Upload Document' },
'upload.modalTitle': { vi: 'Xác nhận Thông tin Tài liệu', en: 'Confirm Document Info' },
'upload.fieldTitle': { vi: 'Tiêu đề', en: 'Title' },
'upload.fieldAuthors': { vi: 'Tác giả (phân cách bằng dấu phẩy)', en: 'Authors (comma-separated)' },
'upload.fieldYear': { vi: 'Năm xuất bản', en: 'Publication Year' },
'upload.fieldAbstract': { vi: 'Tóm tắt', en: 'Abstract' },
'upload.aiBadge': { vi: 'AI Suggested', en: 'AI Suggested' },
'upload.confirm': { vi: 'Xác nhận', en: 'Confirm' },
'upload.cancel': { vi: 'Hủy', en: 'Cancel' },
'upload.extracting': { vi: 'Đang trích xuất metadata...', en: 'Extracting metadata...' },
'upload.successToast': { vi: 'Đã thêm vào hàng đợi xử lý', en: 'Added to processing queue' },
'upload.errorToast': { vi: 'Lỗi upload tài liệu. Vui lòng thử lại.', en: 'Document upload failed. Please try again.' },
'upload.fileTooLarge': { vi: 'File vượt quá giới hạn 20MB', en: 'File exceeds 20MB limit' },
'upload.unsupportedType': { vi: 'Chỉ hỗ trợ định dạng PDF và DOCX', en: 'Only PDF and DOCX formats are supported' },
```

---

### § LibraryTab Updates

```tsx
// frontend/src/features/workspace/LibraryTab.tsx
// Thêm props interface:
interface LibraryTabProps {
  projectId: string | null;
}

export function LibraryTab({ projectId }: LibraryTabProps) {
  // ... (existing code)
  const [showUpload, setShowUpload] = useState(false);
  
  // Thêm nút Upload vào JSX (sau searchButton):
  // {projectId && (
  //   <button className={styles.uploadButton} onClick={() => setShowUpload(true)}>
  //     {t('upload.button')}
  //   </button>
  // )}
  
  // Thêm UploadModal vào JSX:
  // {showUpload && projectId && (
  //   <UploadModal
  //     projectId={projectId}
  //     onClose={() => setShowUpload(false)}
  //     onSuccess={(documentId) => { setShowUpload(false); /* Story 2.5 sẽ refresh list */ }}
  //   />
  // )}
}
```

**CSS — thêm vào `LibraryTab.module.css`:**
```css
.uploadButton {
  background: var(--surface-raised);
  color: var(--ink-primary);
  border: 1px solid var(--border-hairline);
  border-radius: var(--rounded-md);
  padding: 8px 14px;
  font-size: 14px;
  cursor: pointer;
  white-space: nowrap;
  transition: border-color 0.15s ease;
}

.uploadButton:hover {
  border-color: var(--accent-blue);
  color: var(--accent-blue);
}
```

---

### § API Contract

**`POST /api/ingestion/upload`** — multipart/form-data
- Fields: `file` (UploadFile), `project_id` (str Form)
- Response 200:
```json
{
  "fileId": "uuid-string",
  "title": "Deep Learning for NLP",
  "authors": ["John Doe", "Jane Smith"],
  "abstract": "This paper presents...",
  "year": 2023
}
```
- Response 422: File quá lớn hoặc sai định dạng
- Response 200 với metadata rỗng khi LLM lỗi:
```json
{"fileId": "uuid-string", "title": "", "authors": [], "abstract": "", "year": null}
```

**`POST /api/ingestion/confirm`** — JSON body
- Request:
```json
{
  "fileId": "uuid-string",
  "title": "Deep Learning for NLP",
  "authors": ["John Doe"],
  "abstract": "...",
  "year": 2023,
  "projectId": "project-uuid"
}
```
- Response 201:
```json
{"documentId": "paper-uuid", "message": "Tài liệu đã được thêm vào hàng đợi xử lý"}
```
- Response 404: fileId không tồn tại

---

### § Cấu trúc File — Tổng quan

```
backend/
├── requirements.txt                    # CẬP NHẬT: +PyMuPDF, +mammoth, +python-multipart
├── alembic/versions/
│   ├── 004_create_papers_table.py     # MỚI
│   └── 005_create_uploaded_files_table.py # MỚI
├── main.py                            # CẬP NHẬT: +import ingestion ORM + router
└── src/
    ├── shared/infra/settings.py       # CẬP NHẬT: +upload_dir, +max_upload_size_mb
    └── modules/ingestion/             # MỚI: toàn bộ module
        ├── __init__.py
        ├── domain/
        │   ├── __init__.py
        │   ├── entities.py            # UploadedFile, ExtractedMetadata, Paper
        │   └── exceptions.py         # FileTooLargeError, UnsupportedFileTypeError, FileNotFoundError
        ├── application/
        │   ├── __init__.py
        │   └── use_cases.py          # UploadDocumentUseCase, ConfirmMetadataUseCase
        ├── infrastructure/
        │   ├── __init__.py
        │   ├── orm_models.py         # UploadedFileORM, PaperORM (SQLAlchemy)
        │   ├── file_storage.py       # LocalFileStorage
        │   ├── document_parser.py    # DocumentParser (PyMuPDF + mammoth)
        │   ├── metadata_extractor.py # LLMMetadataExtractor (gemini-2.5-flash)
        │   └── postgres_repository.py # PostgresUploadedFileRepository, PostgresPaperRepository
        └── presentation/
            ├── __init__.py
            ├── router.py             # POST /ingestion/upload, POST /ingestion/confirm
            └── schemas.py           # UploadResponseSchema, ConfirmRequestSchema, ConfirmResponseSchema

frontend/src/
├── types/document.ts                  # MỚI: UploadResponse, ConfirmRequest, ConfirmResponse
├── api/ingestion.ts                   # MỚI: uploadDocument(), confirmMetadata()
├── i18n/translations.ts              # CẬP NHẬT: +upload.* keys (13 keys)
└── features/workspace/
    ├── LibraryTab.tsx                 # CẬP NHẬT: +projectId prop, +uploadButton, +UploadModal
    ├── LibraryTab.module.css         # CẬP NHẬT: +.uploadButton
    ├── UploadModal.tsx               # MỚI: modal với state machine idle→extracting→form→confirming
    ├── UploadModal.module.css        # MỚI: overlay, modal, aiBadge, fieldGroup, input, textarea...
    └── __tests__/
        └── UploadModal.test.tsx      # MỚI: 5 test cases
tests/unit/ingestion/
    ├── __init__.py                   # MỚI
    └── test_upload_use_case.py       # MỚI: 4 unit tests
```

**Files KHÔNG được chỉnh sửa:**
- `backend/src/shared/infra/llm/router.py` — LLMRouter đã hoàn chỉnh, KHÔNG sửa
- `backend/src/shared/infra/database.py` — `get_db` dependency đã có
- `frontend/src/api/client.ts` — Axios client không đổi
- `backend/src/modules/search/` — module search không liên quan

---

### § Learnings từ Stories 2.1–2.3 (áp dụng cho 2.4)

1. **LLMRouter pattern** — `router = LLMRouter(db); llm = await router.get_llm_client(user_id, model_name=...)` → `await llm.ainvoke(prompt)` → `result.content`. **Đã hoạt động tốt ở Stories 2.1 và 2.3.**
2. **`_strip_code_fence` helper** — LLM hay bọc JSON trong ```json ... ```. Cần helper này. **Pattern đã dùng ở Story 2.3 BroadQueryDetector.**
3. **camelCase qua `alias_generator=to_camel`** — `file_id` → `fileId`, `project_id` → `projectId`. Cần `populate_by_name=True`. **Chuẩn dự án.**
4. **searchIdRef race condition pattern** — UploadModal KHÔNG cần pattern này (single upload at a time), nhưng nên disable nút trong lúc processing.
5. **`int(data.get("year"))` cần bọc try/except** — LLM có thể trả `"year": "2023"` (string) thay vì int. Dùng `str(data["year"]).isdigit()` check. **Pattern đã học từ Story 2.2.**
6. **CSS `var(--accent-violet)` cho AI Suggested badge** — Không hardcode màu. Không dùng Tailwind.
7. **MemoryRouter trong test** — tất cả component test cần `import { MemoryRouter }` nếu có navigate.
8. **Multipart/form-data** — đây là lần đầu dự án xử lý file upload. Cần `python-multipart` cho FastAPI và `FormData` cho Axios.

---

### § Kiểm tra CenterWorkspace trước khi implement

Trước khi implement LibraryTab, xác nhận `projectId` được truyền vào:
```bash
grep -n "LibraryTab\|projectId\|selectedProject" frontend/src/features/workspace/CenterWorkspace.tsx
```
Nếu chưa có prop `projectId`, cập nhật signature `LibraryTab({ projectId })` **đồng thời** cập nhật nơi render `<LibraryTab>` trong `CenterWorkspace.tsx`.

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_Không có debug log đặc biệt._

### Completion Notes List

- **Backend module `ingestion` hoàn chỉnh**: Domain Layer (entities, exceptions), Infrastructure Layer (orm_models, file_storage, document_parser, metadata_extractor, postgres_repository), Application Layer (use_cases), Presentation Layer (schemas, router).
- **Migrations**: 004 tạo bảng `papers`, 005 tạo bảng `uploaded_files` theo schema spec.
- **LLMMetadataExtractor**: Follow pattern BroadQueryDetector từ Story 2.3, graceful fallback khi LLM lỗi → trả về metadata rỗng (log WARNING, không raise).
- **Document parsing**: PyMuPDF cho PDF (2 trang đầu, max 4000 chars), mammoth cho DOCX.
- **File storage**: `data/uploads/{user_id}/{file_id}{ext}` via `LocalFileStorage`.
- **Frontend UploadModal**: State machine `idle → extracting → form → confirming`. AI badge màu violet trên 4 trường.
- **LibraryTab**: Thêm prop `projectId: string | null`, nút Upload chỉ hiện khi `projectId != null`.
- **CenterWorkspace**: Truyền `activeProjectId` vào `<LibraryTab projectId={activeProjectId} />`.
- **Tests**: 5 BE unit tests (pytest --noconftest) + 5 FE component tests. 68 FE tests tổng cộng PASSED.
- **Lưu ý**: Conftest.py gốc (boilerplate) import langgraph nên `--noconftest` cần thiết cho BE unit tests — đây là vấn đề pre-existing, không phải do story 2.4.

### File List

**Backend — MỚI:**
- `backend/alembic/versions/004_create_papers_table.py`
- `backend/alembic/versions/005_create_uploaded_files_table.py`
- `backend/src/modules/ingestion/__init__.py`
- `backend/src/modules/ingestion/domain/__init__.py`
- `backend/src/modules/ingestion/domain/entities.py`
- `backend/src/modules/ingestion/domain/exceptions.py`
- `backend/src/modules/ingestion/application/__init__.py`
- `backend/src/modules/ingestion/application/use_cases.py`
- `backend/src/modules/ingestion/infrastructure/__init__.py`
- `backend/src/modules/ingestion/infrastructure/orm_models.py`
- `backend/src/modules/ingestion/infrastructure/file_storage.py`
- `backend/src/modules/ingestion/infrastructure/document_parser.py`
- `backend/src/modules/ingestion/infrastructure/metadata_extractor.py`
- `backend/src/modules/ingestion/infrastructure/postgres_repository.py`
- `backend/src/modules/ingestion/presentation/__init__.py`
- `backend/src/modules/ingestion/presentation/schemas.py`
- `backend/src/modules/ingestion/presentation/router.py`
- `tests/unit/ingestion/__init__.py`
- `tests/unit/ingestion/test_upload_use_case.py`

**Backend — CẬP NHẬT:**
- `requirements.txt` (+PyMuPDF, +mammoth, +python-multipart)
- `backend/main.py` (+ingestion ORM imports + router)
- `backend/src/shared/infra/settings.py` (+upload_dir, +max_upload_size_mb)

**Frontend — MỚI:**
- `frontend/src/types/document.ts`
- `frontend/src/api/ingestion.ts`
- `frontend/src/features/workspace/UploadModal.tsx`
- `frontend/src/features/workspace/UploadModal.module.css`
- `frontend/src/features/workspace/__tests__/UploadModal.test.tsx`

**Frontend — CẬP NHẬT:**
- `frontend/src/i18n/translations.ts` (+14 upload.* keys)
- `frontend/src/features/workspace/LibraryTab.tsx` (+projectId prop, +upload button, +UploadModal)
- `frontend/src/features/workspace/LibraryTab.module.css` (+.uploadButton)
- `frontend/src/features/workspace/CenterWorkspace.tsx` (truyền projectId vào LibraryTab)
- `frontend/src/features/workspace/__tests__/LibraryTab.test.tsx` (cập nhật renderTab signature)

### Change Log

- 2026-06-17: Triển khai Story 2.4 — upload PDF/DOCX thủ công với AI metadata extraction. Module `ingestion` mới (BE), UploadModal + LibraryTab/CenterWorkspace integration (FE). 5 BE unit tests + 5 FE component tests. 68 FE tests tổng cộng PASSED.

---

## Review Findings

> Code review (bmad-code-review) — 2026-06-17. 3 lớp: Blind Hunter, Edge Case Hunter, Acceptance Auditor.
> Kết quả: 0 decision-needed · 10 patch · 6 defer · 8 dismissed.
> Acceptance Auditor: cả 6 AC ĐẠT, 13 mục "LỖI THƯỜNG GẶP" đều được tôn trọng, `status_code=201` đúng.

### Patch (cần sửa)

- [x] [Review][Patch] ✅ FIXED — 🔴 CRITICAL — IDOR: `confirm` không kiểm tra quyền sở hữu `file_id`. `find_by_id` chỉ lọc theo `id`, không theo `user_id`; user A có thể confirm `file_id` của user B (UUID có thể lộ) → chiếm `uploaded_file.file_path` của người khác vào project mình. [backend/src/modules/ingestion/infrastructure/postgres_repository.py:26-27] [backend/src/modules/ingestion/application/use_cases.py:90-93]
- [x] [Review][Patch] ✅ FIXED — 🔴 CRITICAL — `project_id` không được validate ownership ở cả upload và confirm. Client truyền `project_id` tùy ý, lưu thẳng vào DB; user gắn tài liệu vào project người khác. Dự án đã có pattern `if project.user_id != requesting_user_id` (workspace/application/use_cases.py:41) nhưng ingestion bỏ qua. [backend/src/modules/ingestion/application/use_cases.py:33-37,86-89]
- [x] [Review][Patch] ✅ FIXED — 🟠 MEDIUM — Confirm dùng `body.project_id` thay vì `uploaded_file.project_id` → upload vào project X, confirm vào project Y. Nên derive project_id từ uploaded_file (hoặc validate trùng khớp). [backend/src/modules/ingestion/application/use_cases.py:95-106]
- [x] [Review][Patch] ✅ FIXED — 🟠 MEDIUM — Memory DoS: `await file.read()` nạp toàn bộ body vào RAM trước khi check size. File 2GB nạp hết rồi mới reject. Check `file.size`/`Content-Length` trước khi đọc. [backend/src/modules/ingestion/presentation/router.py upload_document]
- [x] [Review][Patch] ✅ FIXED — 🟠 MEDIUM — `authors` không phải list (LLM trả `"John, Jane"` string) → list comprehension iterate theo TỪNG KÝ TỰ → `['J','o','h','n',...]`. Thêm `isinstance(authors, list)` check. [backend/src/modules/ingestion/infrastructure/metadata_extractor.py:453]
- [x] [Review][Patch] ✅ FIXED — 🟠 MEDIUM — `max_upload_size_mb` setting bị bỏ qua: threshold hardcode `20*1024*1024`, nhưng message lỗi dùng `settings.max_upload_size_mb` → hai nguồn mâu thuẫn. Dùng settings cho cả threshold. [backend/src/modules/ingestion/application/use_cases.py:21,38-40]
- [x] [Review][Patch] ✅ FIXED — 🟡 LOW — File handle leak: `_extract_pdf` gọi `fitz.open()` rồi `doc.close()` không trong try/finally; nếu `get_text()` raise thì handle leak. Dùng `with fitz.open(...)` hoặc try/finally. [backend/src/modules/ingestion/infrastructure/document_parser.py _extract_pdf]
- [x] [Review][Patch] ✅ FIXED — 🟡 LOW — Year parsing: `str(year_raw).isdigit()` drop năm hợp lệ dạng float `"2023.0"` về null; backend confirm cũng không giới hạn range (LLM/user gửi `99999` lưu thẳng DB). Parse robust + clamp range. [backend/src/modules/ingestion/infrastructure/metadata_extractor.py:450]
- [x] [Review][Patch] ✅ FIXED — 🟡 LOW — FE: click overlay đóng modal giữa lúc `extracting` không bị chặn (`onClick={onClose}` không tôn trọng `isProcessing`) → setState trên component đã unmount. Guard overlay close khi đang xử lý. [frontend/src/features/workspace/UploadModal.tsx overlay]
- [x] [Review][Patch] ✅ FIXED — 🟡 LOW — FE: `fileInputRef.value` chỉ reset trong nhánh catch → chọn lại cùng file sau success không trigger `onChange`. Reset value sau mỗi lần xử lý. [frontend/src/features/workspace/UploadModal.tsx handleFileChange]

### Deferred (thực, ngoài scope / pre-existing)

- [x] [Review][Defer] 🟠 MIME spoofing — chỉ validate extension, không kiểm magic bytes. File `.pdf` thực chất là zip/exe pass validation (fitz fail → graceful empty). Deferred — spec § Dev Notes #7 cố ý mandate detect MIME bằng extension; content-sniffing là hardening enhancement, rủi ro thấp nhờ graceful fallback. [use_cases.py:42-45]
- [x] [Review][Defer] 🟠 Orphaned files — uploaded_files được commit + ghi disk trước; nếu không confirm thì file/row tồn tại vĩnh viễn, không TTL/cleanup. Deferred — cần cơ chế cleanup, liên quan Story 2.5 (worker ingestion). [use_cases.py:47-61]
- [x] [Review][Defer] 🟡 Double-confirm tạo duplicate Paper trên cùng `file_id` (không idempotency). Deferred — cần thiết kế idempotency/mark-consumed. [use_cases.py:78-109]
- [x] [Review][Defer] 🟡 `gen_random_uuid()` cần Postgres 13+/pgcrypto; migration không `CREATE EXTENSION pgcrypto`. Deferred — ORM có app-level uuid default nên hiếm khi chạm; pattern pre-existing ở migrations 001-003, nên xử lý đồng nhất toàn dự án. [alembic/versions/004,005]
- [x] [Review][Defer] 🟡 File 0-byte qua mọi check → tạo Paper rỗng (rác). Deferred — tác động thấp. [use_cases.py:38-67]
- [x] [Review][Defer] 🟡 Backend confirm không validate year range; gộp một phần vào patch year parsing nhưng range-clamp đầy đủ để sau. [use_cases.py:78-109]
