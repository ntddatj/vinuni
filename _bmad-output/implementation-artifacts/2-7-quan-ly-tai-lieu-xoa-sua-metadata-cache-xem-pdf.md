---
baseline_commit: fbf805ea528adaab8887c20395244948b35c4496
---

# Story 2.7: [BE+FE] Quản lý Tài liệu trong Dự án — Xóa, Sửa Metadata & Cache/Xem PDF Nguồn

Status: done

## Story

Với vai trò là Người dùng (User),
Tôi muốn xóa và chỉnh sửa metadata của tài liệu đã nạp trong dự án, đồng thời xem lại file PDF nguồn đã được cache trên server,
Để quản lý thư viện tài liệu của mình một cách linh hoạt mà không cần gọi lại arXiv/Scholar.

## Acceptance Criteria

1. **Given** người dùng ấn nút Xóa tài liệu (có popup xác nhận)
   **When** xác nhận xóa
   **Then** `DELETE /api/projects/{project_id}/papers/{paper_id}` trả về `HTTP 200`
   **And** `paper.is_deleted = True`, `paper.updated_at` được cập nhật
   **And** bảng `sync_outbox` có event mới `event_type="PAPER_DELETED"` với payload `{paper_id, project_id}`
   **And** tất cả `parent_chunks` và `child_chunks` của paper này bị xóa vĩnh viễn (xóa ngay, không đợi GC)
   **And** `DocumentList` cập nhật tức thì (xóa tài liệu khỏi danh sách)
   **And** bộ đếm giới hạn giải phóng — gọi `count_papers_by_project` sau khi xóa cho kết quả giảm 1

2. **Given** người dùng cố xóa tài liệu không thuộc dự án của mình (IDOR)
   **When** gọi DELETE với `project_id` / `paper_id` không hợp lệ
   **Then** server trả `HTTP 403 Forbidden` (không leak data)

3. **Given** người dùng ấn nút "Sửa" trên một tài liệu đã ingest
   **When** chỉnh sửa `{title, authors, abstract, year}` và bấm Lưu
   **Then** `PATCH /api/projects/{project_id}/papers/{paper_id}` trả về `HTTP 200` với metadata mới
   **And** metadata cập nhật hiển thị tức thì trong `DocumentList`
   **And** vector embedding KHÔNG bị re-generate (chỉ metadata)

4. **Given** người dùng xem tài liệu đã được cache file PDF (Open Access)
   **When** ấn nút "Xem file nguồn" trong `DocumentList`
   **Then** `GET /api/projects/{project_id}/papers/{paper_id}/file` trả về `FileResponse` (application/pdf)
   **And** JWT cookie + quyền sở hữu dự án được kiểm tra trước (mirror ARCH-9)
   **And** file mở xem inline trong browser (Content-Disposition: inline)

5. **Given** tài liệu từ nguồn trả phí (paywalled) hoặc tải file PDF thất bại
   **When** `paper.file_path` là NULL
   **Then** `DocumentList` ẩn nút "Xem file nguồn", hiển thị link ngoài + nhãn "nguồn cần trả phí"
   **And** `GET /api/projects/{project_id}/papers/{paper_id}/file` trả `HTTP 404`

6. **Given** worker ARQ đang ingest tài liệu có `pdf_url` (Open Access)
   **When** tải PDF thành công (kích thước ≤ 20MB, SSRF guard pass)
   **Then** file được lưu vào `data/papers/{user_id}/{paper_id}.pdf`
   **And** `paper.file_path` được cập nhật trong DB (qua `db.commit()`)
   **And** quá trình chunking/embedding vẫn tiếp tục bình thường sau khi persist

7. **Given** file PDF tải về có kích thước > 20MB hoặc SSRF guard fail
   **When** worker xử lý
   **Then** `paper.file_path` vẫn NULL (không persist)
   **And** ingestion vẫn tiếp tục với text đã trích xuất (không fail toàn bộ job)

8. **Given** chuyển ngôn ngữ VI|EN trong khi xem tab Thư viện có nút xóa/sửa/xem
   **When** chuyển đổi
   **Then** tất cả label (nút Xóa, Sửa, Xem file nguồn, nhãn "nguồn cần trả phí") đổi ngôn ngữ ngay lập tức

> 🔍 **Cách nghiệm thu trực quan:**
> 1. Upload 1 PDF thủ công. Tab Library → thấy tài liệu.
> 2. Ấn "Sửa" → đổi Title → Lưu → Title cập nhật ngay.
> 3. Ấn "Xóa" → popup xác nhận → OK → tài liệu biến khỏi danh sách.
> 4. Gọi `GET /api/projects/{id}/papers` → paper không còn trong list (is_deleted=True lọc ra).
> 5. Nạp paper từ arXiv → ấn "Xem file nguồn" → PDF mở inline (nếu Open Access).
> 6. Paper paywalled → nút ẩn, hiện link ngoài.

---

## Tasks / Subtasks

### BACKEND — DELETE Tài liệu

- [x] Task 1: Thêm repository methods cho delete và patch (AC: #1, #2, #3)
  - [x] 1.1 Thêm `delete_paper_soft` vào `backend/src/modules/ingestion/infrastructure/postgres_repository.py`:
    ```python
    from sqlalchemy import delete as sql_delete
    from backend.src.modules.ingestion.infrastructure.chunk_orm_models import ChildChunkORM, ParentChunkORM
    from backend.src.modules.workspace.infrastructure.orm_models import SyncOutboxORM

    async def delete_paper_soft(db: AsyncSession, paper_id: str, project_id: str, user_id: str) -> bool:
        """Soft-delete paper + cascade chunks + ghi sync_outbox. Trả True nếu thành công."""
        result = await db.execute(
            select(PaperORM).where(
                PaperORM.id == paper_id,
                PaperORM.project_id == project_id,
                PaperORM.user_id == user_id,
                PaperORM.is_deleted.is_(False),
            )
        )
        paper = result.scalar_one_or_none()
        if paper is None:
            return False

        # 1) Xóa chunks ngay (không đợi GC) để RAG không trả kết quả từ paper đã xóa
        await db.execute(sql_delete(ChildChunkORM).where(ChildChunkORM.paper_id == paper_id))
        await db.execute(sql_delete(ParentChunkORM).where(ParentChunkORM.paper_id == paper_id))

        # 2) Soft-delete paper
        paper.is_deleted = True

        # 3) Ghi sync_outbox cho Neo4j GC (ARCH-2)
        db.add(SyncOutboxORM(
            event_type="PAPER_DELETED",
            payload={"paper_id": paper_id, "project_id": project_id},
        ))

        await db.commit()
        return True
    ```
  - [x] 1.2 Thêm `update_paper_metadata` vào cùng file:
    ```python
    async def update_paper_metadata(
        db: AsyncSession,
        paper_id: str,
        project_id: str,
        user_id: str,
        title: str | None,
        authors: list[str] | None,
        abstract: str | None,
        year: int | None,
    ) -> PaperORM | None:
        """PATCH metadata paper. Trả None nếu không tìm thấy/không có quyền."""
        result = await db.execute(
            select(PaperORM).where(
                PaperORM.id == paper_id,
                PaperORM.project_id == project_id,
                PaperORM.user_id == user_id,
                PaperORM.is_deleted.is_(False),
            )
        )
        paper = result.scalar_one_or_none()
        if paper is None:
            return None

        if title is not None:
            paper.title = title
        if authors is not None:
            paper.authors = authors
        if abstract is not None:
            paper.abstract = abstract
        if year is not None:
            paper.year = year
        # Không set year=None khi year không truyền — tránh xóa năm hợp lệ

        await db.commit()
        await db.refresh(paper)
        return paper
    ```
  - [x] 1.3 Thêm `find_paper_for_file_serve` vào cùng file:
    ```python
    async def find_paper_for_file_serve(
        db: AsyncSession, paper_id: str, project_id: str, user_id: str
    ) -> PaperORM | None:
        """Lấy PaperORM để phục vụ file — kiểm tra ownership + chưa xóa."""
        result = await db.execute(
            select(PaperORM).where(
                PaperORM.id == paper_id,
                PaperORM.project_id == project_id,
                PaperORM.user_id == user_id,
                PaperORM.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()
    ```

- [x] Task 2: Thêm schemas mới (AC: #1, #3, #4)
  - [x] 2.1 Cập nhật `backend/src/modules/ingestion/presentation/schemas.py` — thêm:
    ```python
    class DeletePaperResponseSchema(BaseModel):
        model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
        message: str

    class PatchPaperRequestSchema(BaseModel):
        model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
        title: str | None = None
        authors: list[str] | None = None
        abstract: str | None = None
        year: int | None = None

    class PatchPaperResponseSchema(BaseModel):
        model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
        id: str
        title: str
        authors: list[str]
        abstract: str | None
        year: int | None
        updated_at: datetime
    ```
  - [x] 2.2 Cập nhật `PaperListItemSchema` — thêm các field cần thiết cho frontend biết có file hay không:
    ```python
    class PaperListItemSchema(BaseModel):
        model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
        id: str
        title: str
        authors: list[str]
        year: int | None
        source: str
        status: str
        created_at: datetime
        file_path: str | None = None   # MỚI: để FE biết có file cached chưa
        pdf_url: str | None = None      # MỚI: link ngoài (paywalled/fallback)
        url: str | None = None          # MỚI: link bài báo gốc
    ```

- [x] Task 3: Thêm endpoints vào router (AC: #1, #2, #3, #4, #5)
  - [x] 3.1 Cập nhật `backend/src/modules/ingestion/presentation/router.py` — thêm imports:
    ```python
    from pathlib import Path
    from fastapi.responses import FileResponse
    from backend.src.modules.ingestion.infrastructure.postgres_repository import (
        ...,
        delete_paper_soft,
        update_paper_metadata,
        find_paper_for_file_serve,
    )
    from backend.src.modules.ingestion.presentation.schemas import (
        ...,
        DeletePaperResponseSchema,
        PatchPaperRequestSchema,
        PatchPaperResponseSchema,
    )
    ```
  - [x] 3.2 Thêm DELETE endpoint:
    ```python
    @router.delete("/projects/{project_id}/papers/{paper_id}", response_model=DeletePaperResponseSchema)
    async def delete_paper(
        project_id: str,
        paper_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> DeletePaperResponseSchema:
        # Validate project ownership trước (chống IDOR)
        if not await is_project_owned_by_user(db, project_id, str(current_user.id)):
            raise HTTPException(status_code=403, detail="Không có quyền truy cập dự án này")

        deleted = await delete_paper_soft(db, paper_id, project_id, str(current_user.id))
        if not deleted:
            raise HTTPException(status_code=404, detail="Tài liệu không tồn tại hoặc đã bị xóa")
        return DeletePaperResponseSchema(message="Tài liệu đã được xóa thành công")
    ```
  - [x] 3.3 Thêm PATCH endpoint:
    ```python
    @router.patch("/projects/{project_id}/papers/{paper_id}", response_model=PatchPaperResponseSchema)
    async def patch_paper_metadata(
        project_id: str,
        paper_id: str,
        body: PatchPaperRequestSchema,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> PatchPaperResponseSchema:
        if not await is_project_owned_by_user(db, project_id, str(current_user.id)):
            raise HTTPException(status_code=403, detail="Không có quyền truy cập dự án này")

        paper = await update_paper_metadata(
            db, paper_id, project_id, str(current_user.id),
            title=body.title, authors=body.authors,
            abstract=body.abstract, year=body.year,
        )
        if paper is None:
            raise HTTPException(status_code=404, detail="Tài liệu không tồn tại")
        return PatchPaperResponseSchema(
            id=str(paper.id),
            title=paper.title,
            authors=list(paper.authors or []),
            abstract=paper.abstract,
            year=paper.year,
            updated_at=paper.updated_at,
        )
    ```
  - [x] 3.4 Thêm GET file endpoint (mirror ARCH-9):
    ```python
    @router.get("/projects/{project_id}/papers/{paper_id}/file")
    async def serve_paper_file(
        project_id: str,
        paper_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> FileResponse:
        if not await is_project_owned_by_user(db, project_id, str(current_user.id)):
            raise HTTPException(status_code=403, detail="Không có quyền truy cập dự án này")

        paper = await find_paper_for_file_serve(db, paper_id, project_id, str(current_user.id))
        if paper is None:
            raise HTTPException(status_code=404, detail="Tài liệu không tồn tại")
        if not paper.file_path or not Path(paper.file_path).exists():
            raise HTTPException(status_code=404, detail="File nguồn chưa được cache hoặc không tồn tại")

        return FileResponse(
            path=paper.file_path,
            media_type="application/pdf",
            filename=f"{paper.id}.pdf",
            headers={"Content-Disposition": f'inline; filename="{paper.id}.pdf"'},
        )
    ```
  - [x] 3.5 Cập nhật `list_project_papers` endpoint để trả các field mới từ `PaperListItemSchema`:
    ```python
    items = [
        PaperListItemSchema(
            id=str(p.id),
            title=p.title,
            authors=list(p.authors or []),
            year=p.year,
            source=p.source,
            status=p.status,
            created_at=p.created_at,
            file_path=p.file_path,        # MỚI
            pdf_url=p.pdf_url,             # MỚI
            url=p.url,                     # MỚI
        )
        for p in papers
    ]
    ```

### BACKEND — Worker: Persist PDF

- [x] Task 4: Cập nhật worker để persist PDF và set file_path (AC: #6, #7)
  - [x] 4.1 Thêm setting `papers_dir` vào `backend/src/shared/infra/settings.py`:
    ```python
    papers_dir: str = "data/papers"    # MỚI: thư mục lưu PDF đã cache từ arXiv/Scholar
    ```
  - [x] 4.2 Cập nhật `_download_pdf_text` trong `backend/worker.py` để nhận thêm `paper` param và persist:
    ```python
    # Thay thế _download_pdf_text thành:
    async def _download_and_persist_pdf(pdf_url: str, paper: PaperORM, session_factory) -> str:
        """Download PDF từ URL. Nếu Open Access & ≤ 20MB: persist vào disk, set paper.file_path.
        Luôn trả về text (để chunking). File > 20MB: không persist nhưng vẫn trả text."""
        import httpx
        settings = get_settings()
        _MAX_PERSIST_BYTES = settings.max_upload_size_mb * 1024 * 1024  # 20MB theo NFR2

        if not _is_public_http_url(pdf_url):
            logger.warning("Bỏ qua pdf_url không an toàn (SSRF guard): %s", pdf_url)
            return ""

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
                resp = await client.get(pdf_url)
            if resp.status_code != 200:
                return ""
            if len(resp.content) > _MAX_PDF_BYTES:  # 50MB hard cap (quá lớn để parse)
                logger.warning("PDF quá lớn (%d bytes) — bỏ qua parse", len(resp.content))
                return ""
            ctype = resp.headers.get("content-type", "").lower()
            if ctype and "application/pdf" not in ctype and "octet-stream" not in ctype:
                logger.warning("Content-Type không phải PDF (%s) — bỏ qua", ctype)
                return ""

            # Persist nếu ≤ 20MB (NFR2)
            if len(resp.content) <= _MAX_PERSIST_BYTES:
                target_dir = Path(settings.papers_dir) / paper.user_id
                target_dir.mkdir(parents=True, exist_ok=True)
                file_path = str(target_dir / f"{paper.id}.pdf")
                try:
                    Path(file_path).write_bytes(resp.content)
                    # Update file_path trong DB (session riêng để không ảnh hưởng transaction chính)
                    async with session_factory() as update_db:
                        result = await update_db.execute(
                            select(PaperORM).where(PaperORM.id == paper.id)
                        )
                        p = result.scalar_one_or_none()
                        if p:
                            p.file_path = file_path
                            await update_db.commit()
                except OSError as e:
                    logger.warning("Không thể persist PDF cho paper %s: %s", paper.id, e)
                    # Không fail — vẫn tiếp tục extract text
            else:
                logger.info("PDF %d bytes > %dMB — không persist, chỉ extract text", len(resp.content), settings.max_upload_size_mb)

            # Extract text từ resp.content (đã có trong memory)
            import fitz
            import tempfile
            tmp_path = ""
            try:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp.write(resp.content)
                    tmp_path = tmp.name
                doc = fitz.open(tmp_path)
                try:
                    text = "".join(doc[i].get_text() for i in range(min(len(doc), 20)))
                finally:
                    doc.close()
                return text
            finally:
                if tmp_path:
                    Path(tmp_path).unlink(missing_ok=True)
        except Exception as e:
            logger.warning("Không thể download/parse PDF từ %s: %s", pdf_url, e)
            return ""
    ```
  - [x] 4.3 Cập nhật `_extract_text` trong `worker.py` để gọi hàm mới, truyền thêm `paper` và `session_factory`:
    ```python
    async def _extract_text(paper: PaperORM, session_factory) -> str:
        text = ""
        if paper.file_path and Path(paper.file_path).exists():
            ext = Path(paper.file_path).suffix.lower()
            mime_type = _EXT_TO_MIME.get(ext, "application/pdf")
            text = DocumentParser().extract_text(paper.file_path, mime_type)
        elif paper.pdf_url:
            text = await _download_and_persist_pdf(paper.pdf_url, paper, session_factory)

        if not text.strip() and paper.abstract:
            text = paper.abstract
        return text
    ```
  - [x] 4.4 Cập nhật `ingest_paper_task` để truyền `session_factory` vào `_extract_text`:
    ```python
    text = await _extract_text(paper, ctx["session_factory"])
    ```

### FRONTEND — DocumentList & API

- [x] Task 5: Cập nhật types (AC: #1, #3, #4, #5)
  - [x] 5.1 Cập nhật `frontend/src/types/document.ts` — thêm fields vào `ProjectPaper`:
    ```typescript
    export interface ProjectPaper {
      id: string;
      title: string;
      authors: string[];
      year: number | null;
      source: 'manual' | 'arxiv' | 'semantic_scholar';
      status: 'pending' | 'processing' | 'indexed' | 'failed';
      createdAt: string;
      filePath: string | null;    // MỚI: null = chưa cache
      pdfUrl: string | null;      // MỚI: link ngoài (paywalled fallback)
      url: string | null;         // MỚI: link bài báo
    }

    // MỚI
    export interface PatchPaperRequest {
      title?: string;
      authors?: string[];
      abstract?: string;
      year?: number | null;
    }

    export interface PatchPaperResponse {
      id: string;
      title: string;
      authors: string[];
      abstract: string | null;
      year: number | null;
      updatedAt: string;
    }
    ```

- [x] Task 6: Thêm API client functions (AC: #1, #3, #4)
  - [x] 6.1 Cập nhật `frontend/src/api/ingestion.ts` — thêm:
    ```typescript
    import type { ..., PatchPaperRequest, PatchPaperResponse } from '@/types/document';

    export async function deletePaper(projectId: string, paperId: string): Promise<void> {
      await apiClient.delete(`/api/projects/${projectId}/papers/${paperId}`);
    }

    export async function patchPaperMetadata(
      projectId: string,
      paperId: string,
      data: PatchPaperRequest,
    ): Promise<PatchPaperResponse> {
      const res = await apiClient.patch<PatchPaperResponse>(
        `/api/projects/${projectId}/papers/${paperId}`,
        data,
      );
      return res.data;
    }

    export function getPaperFileUrl(projectId: string, paperId: string): string {
      // Trả URL thay vì gọi API — dùng <a href> hoặc window.open() để trình duyệt mở inline
      return `/api/projects/${projectId}/papers/${paperId}/file`;
    }
    ```

- [x] Task 7: Thêm Translation Keys (AC: #8)
  - [x] 7.1 Cập nhật `frontend/src/i18n/translations.ts` — thêm:
    ```typescript
    'library.delete': { vi: 'Xóa', en: 'Delete' },
    'library.deleteConfirmTitle': { vi: 'Xác nhận xóa tài liệu', en: 'Confirm Delete' },
    'library.deleteConfirmMessage': { vi: 'Bạn có chắc muốn xóa tài liệu này? Hành động này không thể hoàn tác.', en: 'Are you sure you want to delete this document? This action cannot be undone.' },
    'library.deleteSuccess': { vi: 'Đã xóa tài liệu', en: 'Document deleted' },
    'library.deleteError': { vi: 'Không thể xóa tài liệu', en: 'Failed to delete document' },
    'library.edit': { vi: 'Sửa', en: 'Edit' },
    'library.editTitle': { vi: 'Chỉnh sửa thông tin tài liệu', en: 'Edit Document Metadata' },
    'library.editSave': { vi: 'Lưu', en: 'Save' },
    'library.editCancel': { vi: 'Hủy', en: 'Cancel' },
    'library.editSuccess': { vi: 'Đã cập nhật thông tin tài liệu', en: 'Document metadata updated' },
    'library.editError': { vi: 'Không thể cập nhật thông tin', en: 'Failed to update metadata' },
    'library.viewSource': { vi: 'Xem file nguồn', en: 'View Source File' },
    'library.paywallSource': { vi: 'nguồn cần trả phí', en: 'paywalled source' },
    'library.titleField': { vi: 'Tiêu đề', en: 'Title' },
    'library.authorsField': { vi: 'Tác giả (cách nhau bởi dấu phẩy)', en: 'Authors (comma separated)' },
    'library.abstractField': { vi: 'Tóm tắt', en: 'Abstract' },
    'library.yearField': { vi: 'Năm xuất bản', en: 'Publication Year' },
    ```

- [x] Task 8: Cập nhật DocumentList và DocumentRow (AC: #1, #3, #4, #5, #8)
  - [x] 8.1 Cập nhật `frontend/src/features/workspace/DocumentList.tsx` — thêm interface Props:
    ```typescript
    interface Props {
      projectId: string;
      refreshTrigger: number;
      onPapersLoad?: (papers: ProjectPaper[]) => void;
      onDeleteSuccess?: () => void;  // MỚI: callback để trigger refresh LibraryTab
    }
    ```
  - [x] 8.2 Cập nhật `DocumentRow` thành component có state (confirm delete + edit form):
    ```typescript
    function DocumentRow({ paper, projectId, t, onDeleted, onEdited }: RowProps) {
      const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
      const [isDeleting, setIsDeleting] = useState(false);
      const [showEditForm, setShowEditForm] = useState(false);
      const [isSaving, setIsSaving] = useState(false);
      // Edit form state
      const [editTitle, setEditTitle] = useState(paper.title);
      const [editAuthors, setEditAuthors] = useState(paper.authors.join(', '));
      const [editAbstract, setEditAbstract] = useState('');
      const [editYear, setEditYear] = useState(String(paper.year ?? ''));

      async function handleDelete() {
        setIsDeleting(true);
        try {
          await deletePaper(projectId, paper.id);
          toast.success(t('library.deleteSuccess'));
          onDeleted();
        } catch (err) {
          toast.error(getErrorMessage(err, t('library.deleteError')));
        } finally {
          setIsDeleting(false);
          setShowDeleteConfirm(false);
        }
      }

      async function handleSaveEdit() {
        setIsSaving(true);
        try {
          await patchPaperMetadata(projectId, paper.id, {
            title: editTitle.trim() || undefined,
            authors: editAuthors.split(',').map(a => a.trim()).filter(Boolean),
            year: editYear ? parseInt(editYear, 10) : undefined,
          });
          toast.success(t('library.editSuccess'));
          onEdited();
          setShowEditForm(false);
        } catch (err) {
          toast.error(getErrorMessage(err, t('library.editError')));
        } finally {
          setIsSaving(false);
        }
      }

      const fileUrl = getPaperFileUrl(projectId, paper.id);
      const hasLocalFile = Boolean(paper.filePath);
      const hasExternalLink = Boolean(paper.pdfUrl || paper.url);

      return (
        <li className={styles.row}>
          {/* ... existing row content ... */}

          {/* Action buttons */}
          <div className={styles.actions}>
            {hasLocalFile ? (
              <a href={fileUrl} target="_blank" rel="noopener noreferrer" className={styles.viewFileBtn}>
                {t('library.viewSource')}
              </a>
            ) : hasExternalLink ? (
              <a href={paper.pdfUrl ?? paper.url!} target="_blank" rel="noopener noreferrer" className={styles.paywallLink}>
                {t('library.paywallSource')}
              </a>
            ) : null}

            <button type="button" className={styles.editBtn} onClick={() => setShowEditForm(true)}>
              {t('library.edit')}
            </button>
            <button type="button" className={styles.deleteBtn} onClick={() => setShowDeleteConfirm(true)}>
              {t('library.delete')}
            </button>
          </div>

          {/* Delete confirmation modal */}
          {showDeleteConfirm && (
            <div className={styles.confirmOverlay}>
              <div className={styles.confirmBox}>
                <p>{t('library.deleteConfirmMessage')}</p>
                <button type="button" onClick={handleDelete} disabled={isDeleting} className={styles.confirmDeleteBtn}>
                  {isDeleting ? '...' : t('library.delete')}
                </button>
                <button type="button" onClick={() => setShowDeleteConfirm(false)} className={styles.cancelBtn}>
                  {t('library.editCancel')}
                </button>
              </div>
            </div>
          )}

          {/* Edit form */}
          {showEditForm && (
            <div className={styles.editFormOverlay}>
              <div className={styles.editForm}>
                <label>{t('library.titleField')}
                  <input value={editTitle} onChange={e => setEditTitle(e.target.value)} />
                </label>
                <label>{t('library.authorsField')}
                  <input value={editAuthors} onChange={e => setEditAuthors(e.target.value)} />
                </label>
                <label>{t('library.yearField')}
                  <input type="number" value={editYear} onChange={e => setEditYear(e.target.value)} />
                </label>
                <button type="button" onClick={handleSaveEdit} disabled={isSaving}>
                  {isSaving ? '...' : t('library.editSave')}
                </button>
                <button type="button" onClick={() => setShowEditForm(false)}>
                  {t('library.editCancel')}
                </button>
              </div>
            </div>
          )}
        </li>
      );
    }
    ```
  - [x] 8.3 Cập nhật `DocumentList` để truyền `projectId` xuống `DocumentRow` và xử lý delete/edit callbacks:
    ```typescript
    // Khi delete thành công → trigger lại useEffect bằng cách gọi load() thủ công
    // Cách đơn giản: giữ local `papers` state, filter ra paper bị xóa ngay (optimistic)
    // hoặc gọi lại API (conservative). Dùng conservative để đảm bảo đồng bộ:
    function handleItemDeleted() {
      // trigger reload qua useEffect
      setRefreshKey(k => k + 1);  // internal refresh trigger
      onDeleteSuccess?.();  // notify LibraryTab để cập nhật isAtLimit
    }
    function handleItemEdited() {
      setRefreshKey(k => k + 1);
    }
    ```
  - [x] 8.4 Cập nhật `LibraryTab.tsx` — truyền `onDeleteSuccess` vào `DocumentList`:
    ```typescript
    <DocumentList
      projectId={projectId}
      refreshTrigger={docRefreshTrigger}
      onPapersLoad={setPapers}
      onDeleteSuccess={() => setDocRefreshTrigger(n => n + 1)}
    />
    ```

- [x] Task 9: CSS cho actions mới (AC: #1, #3, #4, #8)
  - [x] 9.1 Cập nhật `frontend/src/features/workspace/DocumentList.module.css` — thêm:
    ```css
    .actions {
      display: flex;
      gap: 6px;
      align-items: center;
      flex-shrink: 0;
    }
    .editBtn, .deleteBtn, .viewFileBtn {
      font-size: 12px;
      padding: 3px 8px;
      border-radius: 4px;
      border: 1px solid var(--border-hairline);
      cursor: pointer;
      background: var(--surface-raised);
      color: var(--ink-primary);
      text-decoration: none;
      display: inline-block;
    }
    .deleteBtn {
      border-color: var(--state-danger);
      color: var(--state-danger);
    }
    .deleteBtn:hover {
      background: var(--accent-red-light, #FEE2E2);
    }
    .viewFileBtn {
      border-color: var(--accent-blue);
      color: var(--accent-blue);
    }
    .paywallLink {
      font-size: 11px;
      color: var(--ink-secondary);
      text-decoration: underline;
      font-style: italic;
    }
    .confirmOverlay, .editFormOverlay {
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.4);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 100;
    }
    .confirmBox, .editForm {
      background: var(--surface-raised);
      border-radius: 8px;
      padding: 24px;
      min-width: 300px;
      max-width: 480px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .confirmDeleteBtn {
      background: var(--state-danger);
      color: #fff;
      border: none;
      border-radius: 6px;
      padding: 8px 16px;
      cursor: pointer;
    }
    .cancelBtn {
      background: var(--surface-raised);
      border: 1px solid var(--border-hairline);
      border-radius: 6px;
      padding: 8px 16px;
      cursor: pointer;
    }
    .editForm label {
      display: flex;
      flex-direction: column;
      gap: 4px;
      font-size: 13px;
      color: var(--ink-secondary);
    }
    .editForm input, .editForm textarea {
      border: 1px solid var(--border-hairline);
      border-radius: 4px;
      padding: 6px 8px;
      font-size: 14px;
      background: var(--surface-raised);
      color: var(--ink-primary);
    }
    ```

### BACKEND — Tests

- [x] Task 10: Viết unit tests (AC: #1, #2, #3, #4, #5)
  - [x] 10.1 Tạo `tests/unit/ingestion/test_paper_lifecycle.py`:
    - Test: `delete_paper_soft` — xóa paper, chunks bị delete, sync_outbox được ghi, trả True
    - Test: `delete_paper_soft` — paper không tồn tại/không quyền → trả False
    - Test: `update_paper_metadata` — cập nhật fields, không re-embed
    - Test: `update_paper_metadata` — paper không tồn tại → trả None
    - Test: `find_paper_for_file_serve` — trả đúng paper, là_deleted=True → None
    - Test: DELETE endpoint trả 200 khi thành công
    - Test: DELETE endpoint trả 403 khi không có quyền
    - Test: PATCH endpoint trả 200 với metadata mới
    - Test: GET file endpoint trả 404 khi `file_path` là None
  - [x] 10.2 Chạy với `pytest tests/unit/ingestion/test_paper_lifecycle.py --noconftest`

---

## Dev Notes

### ⚠️ LỖI THƯỜNG GẶP — PHẢI TRÁNH

1. **KHÔNG dùng `ondelete=CASCADE` thay thế xóa chunk thủ công** — CASCADE chỉ chạy khi xóa cứng PaperORM row. Với soft-delete (`is_deleted=True`), chunks vẫn tồn tại. Phải xóa thủ công bằng `DELETE FROM child_chunks WHERE paper_id=...` và `DELETE FROM parent_chunks WHERE paper_id=...` trước khi set `is_deleted=True`.

2. **KHÔNG quên ghi sync_outbox** — event `PAPER_DELETED` là cam kết với Neo4j GC (ARCH-2). Story 4.1 sẽ xử lý event này. Thiếu → Neo4j không bao giờ gỡ node Paper.

3. **KHÔNG dùng Redis lock khi xóa** — delete không gây race condition nhân đôi. Chỉ lock khi thêm (Story 2.6). Xóa đơn giản: validate ownership → delete chunks → soft-delete paper → commit.

4. **KHÔNG re-embed khi PATCH metadata** — chỉ cập nhật fields `title, authors, abstract, year`. Chunks và embeddings giữ nguyên. Re-embed sẽ gây tốn Gemini API quota không cần thiết.

5. **KHÔNG trả `file_path` thật (server path) cho FE** — `PaperListItemSchema.file_path` dùng để FE biết **có file cached hay không** (truthy/falsy). FE gọi `/api/.../file` để get actual file, KHÔNG dùng server path để fetch trực tiếp.

6. **KHÔNG bỏ qua SSRF guard khi persist PDF** — `_is_public_http_url` phải được gọi trước khi tải. Guard đã có, không viết lại.

7. **KHÔNG persist PDF vào `data/uploads/`** — Upload thủ công của user đặt ở `data/uploads/{user_id}/`. PDF từ arXiv/Scholar đặt ở `data/papers/{user_id}/{paper_id}.pdf`. Hai thư mục riêng biệt.

8. **KHÔNG fail toàn bộ ingestion job khi persist PDF lỗi** — Lỗi OSError khi persist chỉ log WARNING, vẫn extract text và tiếp tục chunking/embedding. `paper.file_path` sẽ là NULL.

9. **KHÔNG dùng Tailwind CSS** — CSS Modules + CSS Variables. Xem danh sách biến ở Dev Notes §CSS.

10. **KHÔNG tạo ApiClient mới trong ingestion.ts** — Dùng `apiClient` từ `@/api/client` (import default), nhất quán toàn frontend.

11. **KHÔNG để test import LangGraph** — Dùng `--noconftest` cho unit tests. Pattern đã có ở `test_paper_limit.py`.

12. **KHÔNG set `year=None` khi PatchPaperRequest.year không truyền** — Dùng `if year is not None:` trong `update_paper_metadata`. Nếu user không gửi `year`, không xóa năm hợp lệ.

---

### § Luồng Xóa Tài liệu — Thứ tự Chính xác

```
DELETE /api/projects/{project_id}/papers/{paper_id}
  │
  ├─ 1. is_project_owned_by_user(db, project_id, user_id)  → 403 nếu sai
  │
  ├─ 2. delete_paper_soft(db, paper_id, project_id, user_id):
  │     ├─ SELECT PaperORM WHERE id + project_id + user_id + is_deleted=False → None = return False
  │     ├─ DELETE child_chunks WHERE paper_id = paper_id
  │     ├─ DELETE parent_chunks WHERE paper_id = paper_id
  │     ├─ paper.is_deleted = True
  │     ├─ db.add(SyncOutboxORM(event_type="PAPER_DELETED", payload={...}))
  │     └─ await db.commit()  → trả True
  │
  └─ 3. Trả 200 DeletePaperResponseSchema hoặc 404 nếu trả False
```

**Tác động đến MAX_PAPERS counter:** `count_papers_by_project` filter `is_deleted.is_(False)` → sau khi xóa, count tự giảm 1 → slot mới mở tự động. **Không cần Redis lock khi xóa.**

---

### § Worker: Chi tiết Persist PDF

```
ingest_paper_task → _extract_text(paper, session_factory)
  │
  ├─ Nếu paper.file_path (manual upload) → DocumentParser.extract_text()
  └─ Nếu paper.pdf_url → _download_and_persist_pdf(pdf_url, paper, session_factory)
       ├─ SSRF guard → bỏ qua nếu không an toàn
       ├─ httpx.get(pdf_url, timeout=30, follow_redirects=False)
       ├─ status != 200 → return ""
       ├─ content > 50MB → return "" (hard cap)
       ├─ content-type không phải PDF → return ""
       │
       ├─ [Nếu len(content) <= 20MB (settings.max_upload_size_mb * 1024²)]:
       │   ├─ mkdir data/papers/{user_id}/
       │   ├─ write {paper_id}.pdf
       │   └─ UPDATE papers SET file_path = ... (session mới, commit)
       │
       └─ Extract text từ resp.content (dùng tempfile + fitz)
```

**Tại sao dùng session mới để update file_path?** Session chính của `ingest_paper_task` đang trong giữa transaction (đã commit status="processing"). Mở session riêng để update file_path đảm bảo commit ngay, không phụ thuộc vào trạng thái transaction chính.

---

### § API Endpoints Summary

| Method | URL | Auth | Tác dụng |
|--------|-----|------|----------|
| DELETE | `/api/projects/{pid}/papers/{id}` | JWT cookie | Soft-delete + cascade chunks + sync_outbox |
| PATCH  | `/api/projects/{pid}/papers/{id}` | JWT cookie | Update metadata (title/authors/abstract/year) |
| GET    | `/api/projects/{pid}/papers/{id}/file` | JWT cookie | FileResponse PDF (inline) |
| GET    | `/api/projects/{pid}/papers` | JWT cookie | List papers (đã có, thêm fields mới) |

Pattern xác thực: `Depends(get_current_user)` + `is_project_owned_by_user` — giống mọi endpoint ingestion khác.

---

### § Frontend: Cập nhật `ProjectPaper` type

`PaperListItemSchema` backend trả thêm `file_path`, `pdf_url`, `url`. FE type `ProjectPaper` cần 3 fields mới này. `getPapersByProject()` trong `api/ingestion.ts` tự nhận data mới qua TypeScript generics.

**FE logic để hiện nút/link:**
```typescript
const hasLocalFile = Boolean(paper.filePath);     // server đã cache PDF
const hasExternalLink = Boolean(paper.pdfUrl || paper.url);  // link ngoài
// Ưu tiên: hasLocalFile → nút "Xem file nguồn" (internal endpoint)
// Nếu không: hasExternalLink → link ngoài với nhãn "nguồn cần trả phí"
// Nếu không có gì: ẩn hết
```

---

### § CSS Variables hiện có (KHÔNG dùng Tailwind)

```css
var(--accent-blue)        /* primary action */
var(--accent-green)       /* success */
var(--accent-yellow)      /* warning */
var(--state-danger)       /* #EF4444 - danger/delete */
var(--accent-red-light)   /* #FEE2E2 - danger background */
var(--surface-raised)     /* card/modal background */
var(--ink-primary)        /* main text */
var(--ink-secondary)      /* muted text */
var(--border-hairline)    /* border */
```

---

### § Migration — Không cần migration mới

`papers` table đã có đủ: `is_deleted`, `file_path`, `pdf_url`, `url` (migration 004). Chỉ cần thêm `papers_dir` vào settings.py và tạo thư mục `data/papers/` khi persist.

---

### § Files cần ĐỌC trước khi implement

**Update (không phải mới):**
- [backend/src/modules/ingestion/infrastructure/postgres_repository.py](backend/src/modules/ingestion/infrastructure/postgres_repository.py) — nơi thêm 3 hàm mới
- [backend/src/modules/ingestion/presentation/router.py](backend/src/modules/ingestion/presentation/router.py) — nơi thêm 3 endpoints mới + cập nhật list endpoint
- [backend/src/modules/ingestion/presentation/schemas.py](backend/src/modules/ingestion/presentation/schemas.py) — nơi thêm schemas mới + cập nhật PaperListItemSchema
- [backend/worker.py](backend/worker.py) — cập nhật `_download_pdf_text` → `_download_and_persist_pdf`, cập nhật `_extract_text`
- [backend/src/shared/infra/settings.py](backend/src/shared/infra/settings.py) — thêm `papers_dir`
- [frontend/src/types/document.ts](frontend/src/types/document.ts) — thêm fields mới vào `ProjectPaper`
- [frontend/src/api/ingestion.ts](frontend/src/api/ingestion.ts) — thêm 3 hàm mới
- [frontend/src/i18n/translations.ts](frontend/src/i18n/translations.ts) — thêm translation keys
- [frontend/src/features/workspace/DocumentList.tsx](frontend/src/features/workspace/DocumentList.tsx) — thêm delete/edit UI, actions
- [frontend/src/features/workspace/LibraryTab.tsx](frontend/src/features/workspace/LibraryTab.tsx) — thêm `onDeleteSuccess` prop

---

### § Learnings từ Story 2.6 (áp dụng cho 2.7)

1. **Import SyncOutboxORM từ workspace module** — `from backend.src.modules.workspace.infrastructure.orm_models import SyncOutboxORM`. Đây là nơi nó sống (xem pattern ghi outbox trong `workspace/infrastructure/postgres_repository.py:95`).

2. **`alias_generator=to_camel, populate_by_name=True`** — tất cả Pydantic schemas ở tầng Presentation phải có config này.

3. **`getErrorMessage(err, fallback)`** — luôn cần 2 tham số; import từ `@/api/errors`.

4. **`useTranslation()` từ `@/i18n/useTranslation`** — không dùng i18next.

5. **`TranslationKey` type** — thêm key mới vào `translations.ts` trước khi dùng trong component, vì `t()` nhận `TranslationKey` không phải `string` tuỳ ý.

6. **Ingestion router đã có pattern exception handling** — `except ProjectAccessDeniedError as e: raise HTTPException(status_code=403, ...)`. Làm tương tự cho các endpoint mới (inline try/except trong endpoint).

7. **`is_project_owned_by_user`** — helper có sẵn trong `postgres_repository.py`, tái sử dụng trong mọi endpoint mới.

8. **`toast` từ `sonner`** — pattern thống nhất toàn FE. `toast.success()`, `toast.error()`, `toast.warning()`.

---

### § Cấu trúc File — Tổng quan

```
backend/
├── src/shared/infra/
│   └── settings.py                    # CẬP NHẬT: +papers_dir
├── src/modules/ingestion/
│   ├── infrastructure/
│   │   └── postgres_repository.py     # CẬP NHẬT: +delete_paper_soft, +update_paper_metadata, +find_paper_for_file_serve
│   └── presentation/
│       ├── router.py                  # CẬP NHẬT: +DELETE, +PATCH, +GET file endpoints; sửa list_project_papers
│       └── schemas.py                 # CẬP NHẬT: +DeletePaperResponseSchema, +PatchPaper*; sửa PaperListItemSchema
└── worker.py                          # CẬP NHẬT: _download_pdf_text → _download_and_persist_pdf, _extract_text nhận session_factory

frontend/src/
├── types/
│   └── document.ts                    # CẬP NHẬT: +filePath, +pdfUrl, +url vào ProjectPaper; +PatchPaper*
├── api/
│   └── ingestion.ts                   # CẬP NHẬT: +deletePaper, +patchPaperMetadata, +getPaperFileUrl
├── i18n/translations.ts               # CẬP NHẬT: +16 keys library.*
└── features/workspace/
    ├── DocumentList.tsx               # CẬP NHẬT: +delete/edit UI per row, +onDeleteSuccess prop
    ├── DocumentList.module.css        # CẬP NHẬT: +.actions, .editBtn, .deleteBtn, .viewFileBtn, overlay styles
    └── LibraryTab.tsx                 # CẬP NHẬT: truyền onDeleteSuccess vào DocumentList

tests/unit/ingestion/
└── test_paper_lifecycle.py            # MỚI
```

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_Không có vấn đề đặc biệt trong quá trình triển khai._

### Completion Notes List

- ✅ Task 1: Thêm 3 hàm module-level vào `postgres_repository.py`: `delete_paper_soft`, `update_paper_metadata`, `find_paper_for_file_serve`. `delete_paper_soft` xóa chunks trước khi soft-delete và ghi `SyncOutboxORM(event_type="PAPER_DELETED")`.
- ✅ Task 2: Thêm `DeletePaperResponseSchema`, `PatchPaperRequestSchema`, `PatchPaperResponseSchema`. Cập nhật `PaperListItemSchema` với `file_path`, `pdf_url`, `url`.
- ✅ Task 3: Thêm DELETE, PATCH, GET file endpoints với IDOR guard. Cập nhật `list_project_papers` trả 3 fields mới.
- ✅ Task 4: Thêm `papers_dir` vào settings. Cập nhật worker: `_download_and_persist_pdf` persist PDF ≤ 20MB vào `data/papers/{user_id}/{paper_id}.pdf` qua session riêng.
- ✅ Task 5-7: Cập nhật `ProjectPaper` type, thêm API functions, thêm 16 translation keys.
- ✅ Task 8-9: `DocumentRow` stateful với delete confirm modal + edit form. `onDeleteSuccess` prop. CSS overlays/modals.
- ✅ Task 10: 12 unit tests pass (repository functions + endpoint 200/403/404).

### File List

- `backend/src/modules/ingestion/infrastructure/postgres_repository.py`
- `backend/src/modules/ingestion/presentation/schemas.py`
- `backend/src/modules/ingestion/presentation/router.py`
- `backend/src/shared/infra/settings.py`
- `backend/worker.py`
- `frontend/src/types/document.ts`
- `frontend/src/api/ingestion.ts`
- `frontend/src/i18n/translations.ts`
- `frontend/src/features/workspace/DocumentList.tsx`
- `frontend/src/features/workspace/DocumentList.module.css`
- `frontend/src/features/workspace/LibraryTab.tsx`
- `tests/unit/ingestion/test_paper_lifecycle.py`

### Change Log

| Date | Version | Description |
|------|---------|-------------|
| 2026-06-17 | 1.0 | Tạo story 2.7: quản lý tài liệu — xóa, sửa metadata, cache/xem PDF nguồn. |
| 2026-06-17 | 1.1 | Triển khai hoàn chỉnh: DELETE/PATCH/GET file endpoints, persist PDF worker, frontend delete/edit UI, 12 unit tests. |
| 2026-06-17 | 1.2 | Code review (Blind Hunter + Edge Case Hunter + Acceptance Auditor): 9 patch đã sửa, 1 defer, 5 dismiss. Thêm 3 unit test (15 tổng). |

---

## Review Findings

_Code review 2026-06-17 (3 lớp adversarial: Blind Hunter, Edge Case Hunter, Acceptance Auditor). 9 patch đã áp dụng, 1 defer, 5 dismiss._

### Patch (đã sửa)

- [x] [Review][Patch][High] AC#3 — wire trường `abstract` vào FE (input textarea + payload PATCH + type + prefill từ list); thêm `abstract` vào `PaperListItemSchema` & list endpoint [DocumentList.tsx, document.ts, schemas.py, router.py]
- [x] [Review][Patch][Med] Dev Note #5 — list endpoint không leak server path nữa: đổi `file_path` → `has_file: bool` ở schema/router; FE dùng `paper.hasFile` [schemas.py:95, router.py:219, document.ts:31, DocumentList.tsx:142]
- [x] [Review][Patch][Med] PATCH thiếu validate → DB 500: thêm ràng buộc `title max_length=500`, `year 1000–2100` vào `PatchPaperRequestSchema` (trả 422) [schemas.py:109]
- [x] [Review][Patch][Med] FE year `parseInt` không guard NaN/`"0"`/số thập phân → validate `Number.isInteger` + khoảng 1000–2100, thêm min/max input [DocumentList.tsx:123]
- [x] [Review][Patch][Med] FE title rỗng "thành công thầm lặng" → bắt buộc title không rỗng trước khi lưu (toast lỗi) [DocumentList.tsx:123]
- [x] [Review][Patch][Med] Dev Note #8 — persist PDF lỗi non-OSError (lỗi DB) làm mất text đã trích xuất: mở rộng `except OSError` → `except Exception`, dọn file ghi dở [worker.py:165]
- [x] [Review][Patch][Low] `_extract_text` nhánh file local không guard → PDF cache hỏng làm fail vĩnh viễn paper: bọc `try/except`, fallback abstract [worker.py:111]
- [x] [Review][Patch][Med] Race AC#1 — xóa paper trong lúc ingest tái tạo chunks: `db.refresh(paper)` + check `is_deleted` trước khi lưu chunks [worker.py:248]
- [x] [Review][Patch][Low] Log "PDF quá lớn" sai khi `session_factory is None`: tách điều kiện persist [worker.py:149]

### Defer

- [x] [Review][Defer][Low] File-serve `FileResponse` chưa kiểm tra containment/TOCTOU trên `paper.file_path` — deferred: `user_id`/`paper_id` là UUID server-sinh, không do người dùng kiểm soát; chỉ là defense-in-depth.

### Dismiss (đã loại)

- Hard-delete chunks khi soft-delete paper → đúng chủ ý AC#1 ("xóa vĩnh viễn, không đợi GC"), không có tính năng undo.
- AC#2 trả 404 (không phải 403) cho paper lạ trong dự án sở hữu → 404 đúng chuẩn REST và không leak, thỏa ý "không leak data".
- `scalar_one_or_none` `MultipleResultsFound` → lọc theo PK, không thể trùng.
- Modal stale state khi list refresh → đã được re-seed state lúc mở form.
- Footprint bộ nhớ 3× (memory + temp + disk) → file ≤ 20MB, chấp nhận được.
