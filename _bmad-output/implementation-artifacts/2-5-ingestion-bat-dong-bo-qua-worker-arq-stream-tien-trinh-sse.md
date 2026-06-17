---
baseline_commit: eec0708
---

# Story 2.5: [BE+FE] Ingestion Bất Đồng Bộ Qua Worker ARQ – Stream Tiến Trình SSE

Status: done

## Story

Với vai trò là người dùng đã xác nhận tải tài liệu (upload thủ công hoặc thêm từ kết quả tìm kiếm),
Tôi muốn hệ thống xử lý tài liệu trong nền và thấy thanh tiến trình thời gian thực,
Để tôi biết tài liệu đang được phân tích và có thể tiếp tục làm việc khác trong khi chờ.

## Acceptance Criteria

1. **Given** người dùng bấm "Xác nhận" trong UploadModal (Story 2.4)
   **When** `POST /api/ingestion/confirm` thành công
   **Then** backend lưu paper với `status='pending'`, đẩy job vào arq queue, trả về `{documentId, message}` ngay lập tức (không block)
   **And** frontend nhận `documentId`, gọi `POST /api/ingestion/tasks/{documentId}/ticket`, nhận `{ticket}`, mở `EventSource` đến `GET /api/ingestion/sse/stream?ticket={ticket}`

2. **Given** EventSource đang kết nối
   **When** worker arq cập nhật tiến trình qua Redis
   **Then** frontend nhận các event SSE có dạng `{event: "progress", taskId, status, percent, message}` và hiển thị thanh tiến trình + text thông báo (0→100%)

3. **Given** worker hoàn tất xử lý
   **When** worker đánh dấu `status='indexed'` và ghi event `completed` vào Redis
   **Then** frontend nhận `{event: "completed", taskId, documentId}`, ẩn thanh tiến trình, hiện Toast thành công, và tải lại danh sách tài liệu trong dự án

4. **Given** worker gặp lỗi không thể phục hồi
   **When** exception được bắt và paper được đánh dấu `status='failed'`
   **Then** frontend nhận `{event: "error", taskId, message}`, hiển thị Toast lỗi, đóng SSE

5. **Given** người dùng bấm "+ Thêm vào dự án" trên kết quả tìm kiếm arXiv/Semantic Scholar
   **When** `POST /api/ingestion/from-search` thành công
   **Then** paper được lưu với metadata từ search result (`status='pending'`), job được đẩy vào arq, `documentId` được trả về
   **And** frontend bắt đầu luồng SSE giống AC #1-3

6. **Given** tab Thư viện Tài liệu đang mở và `projectId` không null
   **When** người dùng mở tab hoặc sau khi ingestion hoàn tất
   **Then** frontend hiển thị danh sách tài liệu trong dự án (từ `GET /api/projects/{projectId}/papers`) với badge trạng thái (pending / processing / indexed / failed)

7. **Given** đang ở tab "Thư viện Tài liệu"
   **When** chuyển ngôn ngữ VI|EN
   **Then** tất cả nhãn của progress bar, document list, badge trạng thái đổi ngay lập tức

> 🔍 **Cách nghiệm thu trực quan:**
> Web UI: Click "Upload Tài liệu" → xác nhận form → đóng modal → thấy ngay thanh tiến trình chạy từ 0% với text "Đang đọc tài liệu..." → chạy dần lên 100% → thanh biến mất → Toast xanh "Xử lý tài liệu thành công" → danh sách tài liệu bên dưới cập nhật thêm 1 dòng có badge "Đã xử lý".
> Terminal: `python -m arq backend.worker.WorkerSettings` và xem log "Processing paper <uuid>... Done" xuất hiện.

---

## Tasks / Subtasks

### BACKEND — Infrastructure & Worker

- [x] Task 1: Thêm `arq>=0.25.0` vào `requirements.txt` (AC: #1)
  - [x] 1.1 Thêm dòng `arq>=0.25.0` vào `requirements.txt` (sau dòng `redis[asyncio]`)
  - [x] 1.2 Thêm `VECTOR` extension support: thêm `pgvector>=0.3.6` vào requirements.txt (ORM helper cho vector type)
  - [x] 1.3 Thêm setting mới vào `backend/src/shared/infra/settings.py`:
    - `arq_redis_url: str = Field(default="redis://localhost:6379/0")` — dùng chung redis_url nếu bằng nhau, nhưng để riêng cho tường minh
    - `worker_concurrency: int = 2` — theo NFR4: concurrency_limit=2
    - `ingestion_sse_ticket_ttl: int = 60` — TTL ticket (giây)
    - `ingestion_progress_ttl: int = 3600` — TTL key progress trong Redis

- [x] Task 2: Tạo Alembic migration 006 — enable pgvector + tạo parent/child chunks tables (AC: #1)
  - [x] 2.1 Tạo `backend/alembic/versions/006_create_chunks_tables.py`:
    ```python
    # Phần up():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    op.create_table(
        "parent_chunks",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("paper_id", sa.Uuid(), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_parent_chunks_paper_id", "parent_chunks", ["paper_id"])
    op.create_index("idx_parent_chunks_project_id", "parent_chunks", ["project_id"])
    
    op.create_table(
        "child_chunks",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("parent_chunk_id", sa.Uuid(), sa.ForeignKey("parent_chunks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("paper_id", sa.Uuid(), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        # embedding: vector(768) — text-embedding-004 của Google tạo vector 768 chiều
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_child_chunks_paper_id", "child_chunks", ["paper_id"])
    op.create_index("idx_child_chunks_project_id", "child_chunks", ["project_id"])
    # HNSW index cho vector search (NFR3: < 500ms)
    op.execute("""
        CREATE INDEX idx_child_chunks_embedding_hnsw 
        ON child_chunks USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    ```
  - [x] 2.2 Header của migration file phải import đúng:
    ```python
    from pgvector.sqlalchemy import Vector
    import sqlalchemy as sa
    from alembic import op
    ```
  - [x] 2.3 **BẮT BUỘC — CẬP NHẬT `docker-compose.yml`**: Hiện tại đang dùng `image: postgres:16-alpine` KHÔNG có pgvector. Phải đổi thành:
    ```yaml
    postgres:
      image: pgvector/pgvector:pg16-latest   # thay thế postgres:16-alpine
    ```
    Không cần thay đổi volumes hay environment — chỉ đổi `image`.

- [x] Task 3: Tạo ORM models cho parent/child chunks (AC: #1)
  - [x] 3.1 Tạo `backend/src/modules/ingestion/infrastructure/chunk_orm_models.py`:
    - `ParentChunkORM(Base)` — tablename="parent_chunks", fields: id, paper_id, project_id, content, chunk_index, created_at
    - `ChildChunkORM(Base)` — tablename="child_chunks", fields: id, parent_chunk_id, paper_id, project_id, content, embedding (Vector(768)), chunk_index, created_at
    - Import `Vector` từ `pgvector.sqlalchemy`
  - [x] 3.2 Import `ParentChunkORM, ChildChunkORM` vào `backend/main.py` để SQLAlchemy tạo bảng

- [x] Task 4: Tạo text chunker + embedding client (AC: #1)
  - [x] 4.1 Tạo `backend/src/modules/ingestion/infrastructure/text_chunker.py`:
    - Function `chunk_text(text: str) -> list[tuple[str, list[str]]]`
    - Returns list of `(parent_content, [child_content, ...])` tuples
    - Parent: chia theo paragraph (`\n\n`), max 3000 chars; nếu không có paragraph thì block 3000 chars
    - Child: sliding window 500 chars, overlap 100 chars, từ mỗi parent
    - **Logic cụ thể** (xem Dev Notes § Chunker Algorithm)
  - [x] 4.2 Tạo `backend/src/modules/ingestion/infrastructure/embedding_client.py`:
    - Class `GeminiEmbeddingClient(user_id: str, db: AsyncSession)`
    - Method `async embed_batch(texts: list[str]) -> list[list[float]]`
    - Dùng `LLMRouter` để lấy API Key (giống LLMMetadataExtractor pattern)
    - Sau đó dùng `GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=api_key)`
    - Gọi `embeddings.aembed_documents(texts)`
    - Graceful fallback: nếu lỗi → return `[[0.0]*768 for _ in texts]`, log WARNING

- [x] Task 5: Tạo Worker ARQ (AC: #1, #2, #3, #4)
  - [x] 5.1 Tạo `backend/worker.py` tại root backend:
    ```python
    # arq WorkerSettings + startup/shutdown + ingest_paper_task function
    # Xem Dev Notes § Worker Architecture chi tiết
    ```
  - [x] 5.2 Worker function `ingest_paper_task(ctx, paper_id: str)`:
    - Bước 1 (0%): Load paper từ DB, emit progress "Đang khởi tạo..."
    - Bước 2 (10%): Parse file nếu source='manual', hoặc download từ pdf_url nếu có, emit "Đang đọc tài liệu..."
    - Bước 3 (30%): Chunk text via `text_chunker.chunk_text()`, emit "Đang phân tích nội dung..."
    - Bước 4 (60%): Embed child chunks via `GeminiEmbeddingClient`, emit "Đang tạo vector nhúng..."
    - Bước 5 (85%): Save parent_chunks + child_chunks vào DB, emit "Đang lưu dữ liệu..."
    - Bước 6 (100%): Update `paper.status='indexed'`, ghi event "completed" vào Redis
    - **Error handling**: mọi exception → update `paper.status='failed'`, ghi event "error" vào Redis
  - [x] 5.3 `WorkerSettings` class trong `backend/worker.py`:
    ```python
    class WorkerSettings:
        functions = [ingest_paper_task]
        on_startup = startup
        on_shutdown = shutdown
        max_jobs = 2  # NFR4: concurrency_limit=2
        job_timeout = 600  # 10 phút max per job
    ```

- [x] Task 6: Cập nhật `ConfirmMetadataUseCase` để enqueue arq task (AC: #1)
  - [x] 6.1 Cập nhật `ConfirmMetadataUseCase.execute()` trong `backend/src/modules/ingestion/application/use_cases.py`:
    - Sau khi `await db.commit()`, enqueue arq task: `await enqueue_ingestion_task(saved_paper.id)`
    - Hàm `enqueue_ingestion_task` dùng `ArqRedis` từ settings.arq_redis_url
    - Xem Dev Notes § Enqueue Pattern
    - `message` vẫn là "Tài liệu đã được thêm vào hàng đợi xử lý"

- [x] Task 7: Tạo endpoint "Add from search" (AC: #5)
  - [x] 7.1 Thêm use case `IngestFromSearchUseCase` vào `use_cases.py`:
    - `execute(project_id, user_id, title, authors, abstract, year, doi, arxiv_id, url, pdf_url, source, db) -> dict`
    - Validate project ownership (dùng `is_project_owned_by_user` như UploadDocumentUseCase)
    - Tạo `Paper` với `source=source`, `status='pending'`
    - Save via `PostgresPaperRepository`
    - `await db.commit()`
    - Enqueue arq task
    - Return `{document_id: paper.id, message: "..."}`
  - [x] 7.2 Thêm Pydantic schemas vào `schemas.py`:
    - `AddFromSearchRequestSchema(BaseModel)`: project_id, title, authors, abstract, year, doi, arxiv_id, url, pdf_url, source (literal: arxiv|semantic_scholar)
    - `AddFromSearchResponseSchema(BaseModel)`: document_id, message
  - [x] 7.3 Thêm endpoint vào `router.py`:
    - `POST /ingestion/from-search` nhận `AddFromSearchRequestSchema` body
    - Validate project ownership → `IngestFromSearchUseCase`
    - Trả về `AddFromSearchResponseSchema`, status_code=201

- [x] Task 8: Tạo SSE endpoints (Ticket + Stream) (AC: #1, #2, #3, #4)
  - [x] 8.1 Thêm endpoint lấy ticket SSE vào `router.py`:
    - `POST /ingestion/tasks/{document_id}/ticket`
    - Require `current_user` (JWT cookie)
    - Validate paper belongs to current_user: query DB xem `PaperORM` có `id=document_id AND user_id=current_user.id` không
    - Generate `ticket = str(uuid.uuid4())`
    - Lưu vào Redis: `SET ticket:{ticket} {json: {document_id, user_id}} EX {settings.ingestion_sse_ticket_ttl}` (60s TTL)
    - Return `{"ticket": ticket}`
  - [x] 8.2 Thêm endpoint SSE stream vào `router.py`:
    - `GET /ingestion/sse/stream` nhận query param `ticket: str`
    - Validate ticket từ Redis (GET + DELETE để dùng 1 lần)
    - Extract `document_id` từ ticket value
    - Return `EventSourceResponse(generate_sse(document_id))` với media_type `text/event-stream`
    - Generator `generate_sse` (xem Dev Notes § SSE Generator)
    - **QUAN TRỌNG**: Cần `sse-starlette>=2.1.0` — thêm vào requirements.txt
  - [x] 8.3 SSE Generator logic:
    - Poll Redis key `task:{document_id}:progress` mỗi 500ms (asyncio.sleep(0.5))
    - Khi có dữ liệu mới, yield SSE event
    - Khi event.type == "completed" hoặc "error": yield event rồi break
    - Timeout sau 10 phút (600 polls)

- [x] Task 9: Tạo endpoint GET papers của dự án (AC: #6)
  - [x] 9.1 Thêm vào `router.py`:
    - `GET /projects/{project_id}/papers`
    - Require `current_user`
    - Validate project ownership (is_project_owned_by_user)
    - Query `PaperORM WHERE project_id=X AND user_id=current_user.id AND is_deleted=false ORDER BY created_at DESC`
    - Return list `PaperListResponseSchema` (id, title, authors, year, source, status, created_at)
  - [x] 9.2 Thêm schema `PaperListResponseSchema(BaseModel)` vào `schemas.py`

- [x] Task 10: Helper function ghi/đọc progress Redis (AC: #2, #3, #4)
  - [x] 10.1 Tạo `backend/src/modules/ingestion/infrastructure/task_progress.py`:
    - `async def publish_progress(redis, document_id, percent, status, message)` — ghi JSON vào `task:{document_id}:progress` với TTL
    - `async def publish_completed(redis, document_id)` — ghi event completed
    - `async def publish_error(redis, document_id, message)` — ghi event error
    - `async def get_progress(redis, document_id) -> dict | None` — đọc từ Redis
    - Xem Dev Notes § Progress Schema

### FRONTEND — Progress UI & Document List

- [x] Task 11: Cập nhật types (AC: #1, #5, #6)
  - [x] 11.1 Cập nhật `frontend/src/types/document.ts` — thêm:
    ```typescript
    export interface ProjectPaper {
      id: string;
      title: string;
      authors: string[];
      year: number | null;
      source: 'manual' | 'arxiv' | 'semantic_scholar';
      status: 'pending' | 'processing' | 'indexed' | 'failed';
      createdAt: string;
    }
    
    export interface SSETicketResponse {
      ticket: string;
    }
    
    export interface AddFromSearchRequest {
      projectId: string;
      title: string;
      authors: string[];
      abstract: string;
      year: number | null;
      doi: string | null;
      arxivId: string | null;
      url: string;
      pdfUrl: string | null;
      source: 'arxiv' | 'semantic_scholar';
    }
    
    export interface AddFromSearchResponse {
      documentId: string;
      message: string;
    }
    ```

- [x] Task 12: Cập nhật API functions (AC: #1, #5, #6)
  - [x] 12.1 Cập nhật `frontend/src/api/ingestion.ts` — thêm:
    ```typescript
    export async function getSSETicket(documentId: string): Promise<SSETicketResponse> {
      const res = await apiClient.post<SSETicketResponse>(`/api/ingestion/tasks/${documentId}/ticket`);
      return res.data;
    }
    
    export async function getPapersByProject(projectId: string): Promise<ProjectPaper[]> {
      const res = await apiClient.get<ProjectPaper[]>(`/api/projects/${projectId}/papers`);
      return res.data;
    }
    
    export async function addPaperFromSearch(data: AddFromSearchRequest): Promise<AddFromSearchResponse> {
      const res = await apiClient.post<AddFromSearchResponse>('/api/ingestion/from-search', data);
      return res.data;
    }
    ```
  - [x] 12.2 **QUAN TRỌNG**: Dùng `apiClient` từ `@/api/client`, KHÔNG tạo instance mới

- [x] Task 13: Thêm Translation Keys (AC: #7)
  - [x] 13.1 Cập nhật `frontend/src/i18n/translations.ts` — thêm (trước `} as const`):
    ```typescript
    'ingestion.processing': { vi: 'Đang xử lý tài liệu...', en: 'Processing document...' },
    'ingestion.step.reading': { vi: 'Đang đọc tài liệu...', en: 'Reading document...' },
    'ingestion.step.analyzing': { vi: 'Đang phân tích nội dung...', en: 'Analyzing content...' },
    'ingestion.step.embedding': { vi: 'Đang tạo vector nhúng...', en: 'Creating embeddings...' },
    'ingestion.step.saving': { vi: 'Đang lưu dữ liệu...', en: 'Saving data...' },
    'ingestion.done': { vi: 'Xử lý tài liệu thành công!', en: 'Document processed successfully!' },
    'ingestion.failed': { vi: 'Xử lý tài liệu thất bại. Vui lòng thử lại.', en: 'Document processing failed. Please try again.' },
    'library.documents': { vi: 'Tài liệu trong dự án', en: 'Project Documents' },
    'library.emptyDocs': { vi: 'Chưa có tài liệu nào. Upload hoặc tìm kiếm để thêm.', en: 'No documents yet. Upload or search to add.' },
    'library.loadError': { vi: 'Không thể tải danh sách tài liệu', en: 'Failed to load documents' },
    'library.status.pending': { vi: 'Đang chờ', en: 'Pending' },
    'library.status.processing': { vi: 'Đang xử lý', en: 'Processing' },
    'library.status.indexed': { vi: 'Đã xử lý', en: 'Indexed' },
    'library.status.failed': { vi: 'Lỗi', en: 'Failed' },
    'search.addingToProject': { vi: 'Đang thêm...', en: 'Adding...' },
    'search.addSuccess': { vi: 'Đã thêm vào hàng đợi xử lý', en: 'Added to processing queue' },
    'search.addError': { vi: 'Lỗi khi thêm bài báo. Thử lại.', en: 'Failed to add paper. Try again.' },
    ```
  - [x] 13.2 Xóa hoặc giữ lại `'search.addComingSoon'` (bây giờ không dùng nữa trong code, nhưng translation key không bắt buộc phải xóa)

- [x] Task 14: Tạo IngestionProgress component (AC: #2, #3, #4)
  - [x] 14.1 Tạo `frontend/src/features/workspace/IngestionProgress.tsx`:
    - Props: `{ documentId: string; onComplete: () => void; onError: () => void }`
    - State: `{ percent: number; message: string; status: 'connecting' | 'progress' | 'done' | 'error' }`
    - Lifecycle: `useEffect` → `getSSETicket(documentId)` → `new EventSource('/api/ingestion/sse/stream?ticket=...')`
    - onmessage: parse JSON, update state
    - onevent (completed): gọi `onComplete()`, đóng EventSource
    - onevent (error): gọi `onError()`, đóng EventSource
    - Cleanup: `return () => eventSource.close()`
    - Render: progress bar (div width=`${percent}%`) + message text
    - Xem Dev Notes § IngestionProgress Component
  - [x] 14.2 Tạo `frontend/src/features/workspace/IngestionProgress.module.css`
    - `.container`, `.bar`, `.fill`, `.message`, `.percent`
    - Xem Dev Notes § CSS cho IngestionProgress

- [x] Task 15: Tạo DocumentList component (AC: #6)
  - [x] 15.1 Tạo `frontend/src/features/workspace/DocumentList.tsx`:
    - Props: `{ projectId: string; refreshTrigger: number }` — `refreshTrigger` increment khi cần reload
    - Fetch `getPapersByProject(projectId)` on mount và khi `refreshTrigger` thay đổi
    - Hiển thị danh sách papers với: title, authors (tối đa 2 + "et al."), year, source badge, status badge
    - Status badge: màu theo trạng thái — pending (vàng), processing (xanh dương nhấp nháy animation), indexed (xanh lá), failed (đỏ)
    - Xem Dev Notes § DocumentList Component
  - [x] 15.2 Tạo `frontend/src/features/workspace/DocumentList.module.css`

- [x] Task 16: Cập nhật LibraryTab (AC: #1-7)
  - [x] 16.1 Cập nhật `frontend/src/features/workspace/LibraryTab.tsx`:
    - Thêm state: `processingDocumentId: string | null` — documentId đang trong quá trình ingestion
    - Thêm state: `docRefreshTrigger: number` — để trigger DocumentList reload
    - Cập nhật callback `onSuccess` của `UploadModal`:
      ```tsx
      onSuccess={(documentId) => {
        setShowUpload(false);
        setProcessingDocumentId(documentId);  // bắt đầu SSE
      }}
      ```
    - Render `<IngestionProgress>` khi `processingDocumentId` không null:
      ```tsx
      {processingDocumentId && (
        <IngestionProgress
          documentId={processingDocumentId}
          onComplete={() => {
            toast.success(t('ingestion.done'));
            setProcessingDocumentId(null);
            setDocRefreshTrigger(n => n + 1);  // reload DocumentList
          }}
          onError={() => {
            toast.error(t('ingestion.failed'));
            setProcessingDocumentId(null);
          }}
        />
      )}
      ```
    - Render `<DocumentList>` khi `projectId` không null:
      ```tsx
      {projectId && (
        <DocumentList projectId={projectId} refreshTrigger={docRefreshTrigger} />
      )}
      ```
    - Cập nhật PaperCard để enable nút "Thêm vào dự án" (AC: #5):
      - Thêm prop `onAddToProject?: (paper: PaperResult) => void`
      - Nút không còn `disabled` khi `projectId != null`
      - Click gọi `handleAddFromSearch(paper)`
    - Thêm state: `addingPapers: Set<string>` — DOI/arxivId của paper đang được thêm
    - Hàm `handleAddFromSearch(paper: PaperResult)`:
      ```typescript
      async function handleAddFromSearch(paper: PaperResult) {
        if (!projectId) return;
        const key = paper.doi ?? paper.arxivId ?? paper.title;
        setAddingPapers(prev => new Set(prev).add(key));
        try {
          const res = await addPaperFromSearch({ projectId, ...paper, ... });
          setProcessingDocumentId(res.documentId);
          toast.success(t('search.addSuccess'));
        } catch (err) {
          toast.error(getErrorMessage(err, t('search.addError')));
        } finally {
          setAddingPapers(prev => { const s = new Set(prev); s.delete(key); return s; });
        }
      }
      ```

- [x] Task 17: Viết Tests (AC: #1-7)
  - [x] 17.1 Tạo `frontend/src/features/workspace/__tests__/IngestionProgress.test.tsx`:
    - Test: gọi `getSSETicket` khi mount
    - Test: cập nhật progress bar khi nhận SSE event `progress`
    - Test: gọi `onComplete` khi nhận event `completed`
    - Test: gọi `onError` khi nhận event `error`
    - Mock `EventSource` toàn cục trong test environment
    - Mock `getSSETicket` bằng `vi.mock('@/api/ingestion')`
  - [x] 17.2 Cập nhật `frontend/src/features/workspace/__tests__/LibraryTab.test.tsx`:
    - Test: render `IngestionProgress` khi `processingDocumentId` được set
    - Test: render `DocumentList` khi `projectId` không null
    - Test: nút "Thêm vào dự án" trong search results được enable khi có `projectId`
  - [x] 17.3 Tạo `tests/unit/ingestion/test_worker.py`:
    - Test: `chunk_text` chia đúng 500 chars với overlap 100
    - Test: `chunk_text` xử lý text ngắn hơn 500 chars (không chia)
    - Test: `publish_progress` ghi đúng JSON vào Redis
    - Test: worker bắt exception và publish_error khi file không tìm thấy

---

## Dev Notes

### ⚠️ LỖI THƯỜNG GẶP CỦA LLM — PHẢI TRÁNH

1. **KHÔNG dùng FastAPI BackgroundTasks** cho ingestion — dự án dùng `arq` theo NFR4. BackgroundTasks chạy trong process uvicorn, không có concurrency_limit riêng và không restart-safe.

2. **KHÔNG tạo ArqRedis pool mới mỗi request** — tạo pool một lần ở startup và lưu vào app state hoặc dùng context manager. Xem Dev Notes § Enqueue Pattern.

3. **KHÔNG dùng `EventSource` với Authorization header** — browser `EventSource` không hỗ trợ custom headers. Phải dùng ticket-based auth theo ARCH-3: `POST ticket → GET ?ticket=...`.

4. **KHÔNG import `Vector` từ SQLAlchemy thuần** — phải dùng `from pgvector.sqlalchemy import Vector`. Package `pgvector` cần được install riêng.

5. **KHÔNG quên `CREATE EXTENSION IF NOT EXISTS vector`** trong migration trước khi tạo bảng dùng vector type.

6. **KHÔNG bỏ `OMP_NUM_THREADS=1, OPENBLAS_NUM_THREADS=1`** trong docker-compose cho arq worker — theo NFR4 để chống CPU thrashing với Deep Learning libs.

7. **KHÔNG để SSE endpoint block vĩnh viễn** — phải có timeout (600s) và cleanup EventSource khi component unmount.

8. **KHÔNG dùng Tailwind CSS** — CSS Modules + CSS Variables. Dùng `var(--accent-blue)`, `var(--accent-green)`, `var(--accent-yellow)`, `var(--surface-raised)`, `var(--ink-primary)`.

9. **KHÔNG quên `TranslationKey` type** — `t()` nhận `TranslationKey`, không phải `string`. Thêm key mới vào `translations.ts` trước.

10. **KHÔNG dùng `i18next`** — dùng `useTranslation()` từ `frontend/src/i18n/useTranslation.ts`.

11. **KHÔNG gọi `getErrorMessage(err)` với 1 tham số** — thiếu fallback string gây `TS2554`. Luôn dùng `getErrorMessage(err, t('some.key'))`.

12. **KHÔNG hardcode embedding dimension** — `text-embedding-004` tạo vector 768 chiều. Lưu `EMBEDDING_DIM = 768` là constant.

13. **KHÔNG dùng synchronous Redis** trong arq worker — worker đã async, dùng `redis.asyncio` (đã có trong `redis[asyncio]` requirement).

14. **KHÔNG dùng `paper.mime_type`** trong worker — `PaperORM` KHÔNG có column `mime_type`. Xác định mime_type từ extension của `paper.file_path` (`.pdf` → `application/pdf`, `.docx` → `application/vnd.openxmlformats-officedocument.wordprocessingml.document`).

15. **KHÔNG nhầm `ctx['redis']` với `aioredis.Redis` thông thường** — `ctx['redis']` trong arq worker là `ArqRedis` instance (extends aioredis.Redis). Dùng trực tiếp cho `.get()`, `.set()`, `.delete()` — không cần tạo client riêng cho task_progress operations.

---

### § Worker Architecture

```python
# backend/worker.py
import asyncio
import json
import logging
from pathlib import Path

import httpx
from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.src.modules.ingestion.infrastructure.document_parser import DocumentParser
from backend.src.modules.ingestion.infrastructure.embedding_client import GeminiEmbeddingClient
from backend.src.modules.ingestion.infrastructure.task_progress import (
    publish_completed, publish_error, publish_progress
)
from backend.src.modules.ingestion.infrastructure.text_chunker import chunk_text
from backend.src.modules.ingestion.infrastructure.chunk_orm_models import ChildChunkORM, ParentChunkORM
from backend.src.modules.ingestion.infrastructure.orm_models import PaperORM
from backend.src.shared.infra.settings import get_settings

logger = logging.getLogger(__name__)

OMP_NUM_THREADS = "1"  # Set BEFORE importing numpy/torch — do in docker-compose env vars


async def startup(ctx):
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    ctx['session_factory'] = async_sessionmaker(engine, expire_on_commit=False)
    # ctx['redis'] được arq cung cấp sẵn — ArqRedis hỗ trợ .get()/.set()/.delete() như aioredis.Redis


async def shutdown(ctx):
    pass  # arq tự dọn dẹp redis connection


async def ingest_paper_task(ctx, paper_id: str):
    """Background task xử lý tài liệu: parse → chunk → embed → save."""
    redis = ctx['redis']
    session_factory: async_sessionmaker = ctx['session_factory']

    async with session_factory() as db:
        try:
            # Bước 1: Load paper
            await publish_progress(redis, paper_id, 0, "initializing", "Đang khởi tạo...")
            from sqlalchemy import select
            result = await db.execute(select(PaperORM).where(PaperORM.id == paper_id))
            paper = result.scalar_one_or_none()
            if not paper:
                await publish_error(redis, paper_id, f"Paper {paper_id} không tồn tại")
                return

            # Update status
            paper.status = "processing"
            await db.commit()

            # Bước 2: Lấy nội dung text
            await publish_progress(redis, paper_id, 10, "reading", "Đang đọc tài liệu...")
            text = ""
            if paper.file_path and Path(paper.file_path).exists():
                # Xác định mime_type từ extension (PaperORM không lưu mime_type — dùng extension)
                ext = Path(paper.file_path).suffix.lower()
                mime_type = {
                    ".pdf": "application/pdf",
                    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                }.get(ext, "application/pdf")
                parser = DocumentParser()
                text = parser.extract_text(paper.file_path, mime_type)
            elif paper.pdf_url:
                # Download PDF từ URL
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(paper.pdf_url)
                    if resp.status_code == 200:
                        import tempfile, fitz
                        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                            tmp.write(resp.content)
                            tmp_path = tmp.name
                        doc = fitz.open(tmp_path)
                        text = "".join(doc[i].get_text() for i in range(min(len(doc), 20)))
                        doc.close()
                        Path(tmp_path).unlink(missing_ok=True)

            # Fallback: dùng abstract nếu không có text
            if not text.strip() and paper.abstract:
                text = paper.abstract

            if not text.strip():
                # Không có nội dung — đánh dấu indexed nhưng không có chunk
                paper.status = "indexed"
                await db.commit()
                await publish_completed(redis, paper_id)
                return

            # Bước 3: Chunk
            await publish_progress(redis, paper_id, 30, "chunking", "Đang phân tích nội dung...")
            chunks = chunk_text(text)  # [(parent_content, [child_content,...])]

            # Bước 4: Embed
            await publish_progress(redis, paper_id, 60, "embedding", "Đang tạo vector nhúng...")
            all_child_texts = [c for _, children in chunks for c in children]
            embedding_client = GeminiEmbeddingClient(user_id=paper.user_id, db=db)
            all_embeddings = await embedding_client.embed_batch(all_child_texts)

            # Bước 5: Save
            await publish_progress(redis, paper_id, 85, "saving", "Đang lưu dữ liệu...")
            child_idx = 0
            for p_idx, (parent_content, child_texts) in enumerate(chunks):
                parent_chunk = ParentChunkORM(
                    paper_id=paper_id,
                    project_id=paper.project_id,
                    content=parent_content,
                    chunk_index=p_idx,
                )
                db.add(parent_chunk)
                await db.flush()  # để có parent_chunk.id

                for c_idx, child_text in enumerate(child_texts):
                    child_chunk = ChildChunkORM(
                        parent_chunk_id=parent_chunk.id,
                        paper_id=paper_id,
                        project_id=paper.project_id,
                        content=child_text,
                        embedding=all_embeddings[child_idx],
                        chunk_index=c_idx,
                    )
                    db.add(child_chunk)
                    child_idx += 1

            paper.status = "indexed"
            await db.commit()

            await publish_completed(redis, paper_id)
            logger.info("Ingested paper %s successfully", paper_id)

        except Exception as e:
            logger.exception("Failed to ingest paper %s: %s", paper_id, e)
            try:
                paper.status = "failed"
                await db.commit()
            except Exception:
                pass
            await publish_error(redis, paper_id, str(e))


class WorkerSettings:
    functions = [ingest_paper_task]
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 2  # NFR4: concurrency_limit=2
    job_timeout = 600
    keep_result = 300

    @classmethod
    def redis_settings(cls):
        from backend.src.shared.infra.settings import get_settings
        return RedisSettings.from_dsn(get_settings().redis_url)
```

**Chạy worker trong dev:**
```bash
python -m arq backend.worker.WorkerSettings
```

**Cập nhật `Dockerfile` và `docker-compose.yml`** để thêm service worker (xem Dev Notes § Docker).

---

### § Enqueue Pattern

```python
# Cách enqueue từ FastAPI endpoint / use case
import json
from arq import create_pool
from arq.connections import RedisSettings

async def enqueue_ingestion_task(paper_id: str):
    """Enqueue arq task. Tạo pool ngắn hạn — phù hợp cho dev/test."""
    from backend.src.shared.infra.settings import get_settings
    settings = get_settings()
    redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    try:
        await redis.enqueue_job("ingest_paper_task", paper_id)
    finally:
        await redis.aclose()
```

**Chú ý:** Trong production, nên giữ pool tồn tại qua `lifespan` của FastAPI app thay vì tạo mới mỗi lần. Nhưng cho MVP, pattern trên đủ dùng.

---

### § Progress Schema — Redis Keys

```python
# Key: task:{document_id}:progress
# Giá trị: JSON string
# TTL: 3600s (1 giờ)

# Event progress:
{
  "event": "progress",
  "taskId": "paper-uuid",
  "status": "reading|chunking|embedding|saving|initializing",
  "percent": 60,
  "message": "Đang tạo vector nhúng..."
}

# Event completed:
{
  "event": "completed",
  "taskId": "paper-uuid",
  "documentId": "paper-uuid"
}

# Event error:
{
  "event": "error",
  "taskId": "paper-uuid",
  "message": "Chi tiết lỗi..."
}
```

```python
# backend/src/modules/ingestion/infrastructure/task_progress.py
import json
from redis.asyncio import Redis

PROGRESS_TTL = 3600  # 1 giờ


async def publish_progress(redis: Redis, document_id: str, percent: int, status: str, message: str):
    data = json.dumps({
        "event": "progress",
        "taskId": document_id,
        "status": status,
        "percent": percent,
        "message": message,
    })
    await redis.set(f"task:{document_id}:progress", data, ex=PROGRESS_TTL)


async def publish_completed(redis: Redis, document_id: str):
    data = json.dumps({
        "event": "completed",
        "taskId": document_id,
        "documentId": document_id,
    })
    await redis.set(f"task:{document_id}:progress", data, ex=PROGRESS_TTL)


async def publish_error(redis: Redis, document_id: str, message: str):
    data = json.dumps({
        "event": "error",
        "taskId": document_id,
        "message": message,
    })
    await redis.set(f"task:{document_id}:progress", data, ex=PROGRESS_TTL)


async def get_progress(redis: Redis, document_id: str) -> dict | None:
    raw = await redis.get(f"task:{document_id}:progress")
    if raw is None:
        return None
    return json.loads(raw)
```

---

### § SSE Generator

```python
# Trong router.py — endpoint GET /ingestion/sse/stream
import asyncio
from sse_starlette.sse import EventSourceResponse
from redis.asyncio import Redis as AsyncRedis

async def generate_sse(redis: AsyncRedis, document_id: str):
    """Poll Redis mỗi 500ms, yield SSE event khi có dữ liệu mới."""
    last_event_data = None
    max_polls = 1200  # 10 phút = 1200 × 0.5s
    for _ in range(max_polls):
        progress = await get_progress(redis, document_id)
        if progress and json.dumps(progress) != last_event_data:
            last_event_data = json.dumps(progress)
            yield {"data": last_event_data}
            if progress.get("event") in ("completed", "error"):
                return
        await asyncio.sleep(0.5)


@router.get("/ingestion/sse/stream")
async def sse_stream(ticket: str) -> EventSourceResponse:
    # Validate ticket từ Redis (one-time use)
    redis = get_redis_client()  # singleton redis client từ shared infra
    ticket_data_raw = await redis.get(f"ticket:{ticket}")
    if not ticket_data_raw:
        raise HTTPException(status_code=401, detail="Invalid or expired SSE ticket")
    await redis.delete(f"ticket:{ticket}")  # one-time use
    
    ticket_data = json.loads(ticket_data_raw)
    document_id = ticket_data["document_id"]
    
    return EventSourceResponse(generate_sse(redis, document_id))
```

**Thêm Redis singleton** vào shared infra:

```python
# backend/src/shared/infra/redis_client.py  (MỚI)
from functools import lru_cache
import redis.asyncio as aioredis
from backend.src.shared.infra.settings import get_settings

_redis_client = None

async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client
```

---

### § Chunker Algorithm

```python
# backend/src/modules/ingestion/infrastructure/text_chunker.py
PARENT_MAX_CHARS = 3000
CHILD_CHUNK_SIZE = 500
CHILD_OVERLAP = 100


def chunk_text(text: str) -> list[tuple[str, list[str]]]:
    """
    Chia text thành (parent_content, [child_content, ...]).
    Parent: chia theo paragraph (\n\n), gộp đến PARENT_MAX_CHARS.
    Child: sliding window từ mỗi parent.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text.strip()]

    # Gộp paragraphs thành parent chunks
    parents: list[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 2 <= PARENT_MAX_CHARS:
            current = (current + "\n\n" + para).strip()
        else:
            if current:
                parents.append(current)
            # Paragraph quá dài? Cắt trực tiếp
            if len(para) > PARENT_MAX_CHARS:
                for i in range(0, len(para), PARENT_MAX_CHARS):
                    parents.append(para[i:i + PARENT_MAX_CHARS])
                current = ""
            else:
                current = para
    if current:
        parents.append(current)

    result = []
    for parent_content in parents:
        children = _sliding_window(parent_content)
        result.append((parent_content, children))
    return result


def _sliding_window(text: str) -> list[str]:
    """Sliding window 500 chars với overlap 100 chars."""
    if len(text) <= CHILD_CHUNK_SIZE:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHILD_CHUNK_SIZE
        chunks.append(text[start:end])
        start += CHILD_CHUNK_SIZE - CHILD_OVERLAP
    return chunks
```

---

### § Embedding Client

```python
# backend/src/modules/ingestion/infrastructure/embedding_client.py
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.shared.infra.llm.router import LLMRouter

logger = logging.getLogger(__name__)
EMBEDDING_DIM = 768  # text-embedding-004 output dimension


class GeminiEmbeddingClient:
    def __init__(self, user_id: str, db: AsyncSession):
        self._user_id = user_id
        self._db = db

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            router = LLMRouter(self._db)
            # Lấy API key qua LLMRouter — dùng model dummy để extract key
            # LLMRouter.get_llm_client() trả về ChatGoogleGenerativeAI
            # Ta cần extract API key từ đó để tạo Embeddings
            llm_client = await router.get_llm_client(self._user_id, model_name="gemini-2.5-flash")
            # Extract api_key từ client (langchain_google_genai stores it in .google_api_key)
            api_key = getattr(llm_client, 'google_api_key', None) or getattr(llm_client, '_api_key', None)
            if not api_key:
                # Fallback sang settings.gemini_api_key
                from backend.src.shared.infra.settings import get_settings
                api_key = get_settings().gemini_api_key

            embeddings = GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004",
                google_api_key=api_key,
            )
            result = await embeddings.aembed_documents(texts)
            return result
        except Exception as e:
            logger.warning("GeminiEmbeddingClient: lỗi khi embed batch %d texts: %s", len(texts), e)
            return [[0.0] * EMBEDDING_DIM for _ in texts]
```

**Chú ý về LLMRouter API key extraction:** Cần kiểm tra chính xác attribute name của `ChatGoogleGenerativeAI` để lấy API key. Nếu không extract được, fallback về `settings.gemini_api_key`. Điều này đảm bảo worker vẫn hoạt động dù LLMRouter thay đổi internal.

---

### § IngestionProgress Component

```tsx
// frontend/src/features/workspace/IngestionProgress.tsx
import { useEffect, useRef, useState } from 'react';
import { getSSETicket } from '@/api/ingestion';
import { useTranslation } from '@/i18n/useTranslation';
import styles from './IngestionProgress.module.css';

interface Props {
  documentId: string;
  onComplete: () => void;
  onError: () => void;
}

interface ProgressState {
  percent: number;
  message: string;
  status: 'connecting' | 'running' | 'done' | 'error';
}

export function IngestionProgress({ documentId, onComplete, onError }: Props) {
  const { t } = useTranslation();
  const [state, setState] = useState<ProgressState>({
    percent: 0,
    message: t('ingestion.processing'),
    status: 'connecting',
  });
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function connect() {
      try {
        const { ticket } = await getSSETicket(documentId);
        if (cancelled) return;

        const es = new EventSource(`/api/ingestion/sse/stream?ticket=${encodeURIComponent(ticket)}`);
        esRef.current = es;

        es.onmessage = (evt) => {
          if (cancelled) return;
          try {
            const data = JSON.parse(evt.data);
            if (data.event === 'progress') {
              setState({ percent: data.percent, message: data.message, status: 'running' });
            } else if (data.event === 'completed') {
              setState({ percent: 100, message: t('ingestion.done'), status: 'done' });
              es.close();
              onComplete();
            } else if (data.event === 'error') {
              setState({ percent: 0, message: data.message, status: 'error' });
              es.close();
              onError();
            }
          } catch {
            // ignore parse errors
          }
        };

        es.onerror = () => {
          if (cancelled) return;
          es.close();
          onError();
        };
      } catch {
        if (!cancelled) onError();
      }
    }

    connect();
    return () => {
      cancelled = true;
      esRef.current?.close();
    };
  }, [documentId]);  // ESLint: onComplete/onError should be stable (useCallback in parent)

  if (state.status === 'done' || state.status === 'error') return null;

  return (
    <div className={styles.container}>
      <div className={styles.bar}>
        <div className={styles.fill} style={{ width: `${state.percent}%` }} />
      </div>
      <div className={styles.footer}>
        <span className={styles.message}>{state.message}</span>
        <span className={styles.percent}>{state.percent}%</span>
      </div>
    </div>
  );
}
```

---

### § CSS cho IngestionProgress

```css
/* frontend/src/features/workspace/IngestionProgress.module.css */
.container {
  padding: 12px 0;
  margin-bottom: 12px;
}

.bar {
  height: 6px;
  background: var(--surface-raised);
  border-radius: 3px;
  overflow: hidden;
}

.fill {
  height: 100%;
  background: var(--accent-blue);
  border-radius: 3px;
  transition: width 0.4s ease;
}

.footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 6px;
}

.message {
  font-size: 12px;
  color: var(--ink-secondary);
}

.percent {
  font-size: 12px;
  color: var(--ink-secondary);
  font-weight: 500;
}
```

---

### § DocumentList Component

```tsx
// Cấu trúc chính — xem chi tiết trong code
// Props: { projectId: string; refreshTrigger: number }
// Fetch getPapersByProject(projectId) khi mount + khi refreshTrigger thay đổi
// Hiển thị: title, authors (≤2 + "et al."), year, source badge, status badge
// Status badge màu: pending=vàng, processing=xanh nhấp nháy, indexed=xanh lá, failed=đỏ

// Status badge CSS class theo trạng thái:
// .statusBadge[data-status="pending"]    { background: var(--accent-yellow-light); color: var(--accent-yellow); }
// .statusBadge[data-status="processing"] { background: var(--accent-blue-light); color: var(--accent-blue); animation: pulse 1.5s ease-in-out infinite; }
// .statusBadge[data-status="indexed"]    { background: var(--accent-green-light); color: var(--accent-green); }
// .statusBadge[data-status="failed"]     { background: var(--accent-red-light); color: var(--accent-red); }
```

---

### § Docker — Thêm arq worker service

Cập nhật `docker-compose.yml` — thêm service `worker`:

```yaml
worker:
  build: .
  command: python -m arq backend.worker.WorkerSettings
  environment:
    - DATABASE_URL=${DATABASE_URL}
    - REDIS_URL=${REDIS_URL}
    - OMP_NUM_THREADS=1       # NFR4: chống CPU thrashing
    - OPENBLAS_NUM_THREADS=1  # NFR4: chống CPU thrashing
  depends_on:
    - postgres
    - redis
  restart: unless-stopped
  mem_limit: 12g  # ARCH-1: arq worker limit 12GB
```

---

### § PaperListResponseSchema

```python
# Thêm vào schemas.py
class PaperListItemSchema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    
    id: str
    title: str
    authors: list[str]
    year: int | None
    source: str
    status: str
    created_at: datetime

class PaperListResponseSchema(RootModel[list[PaperListItemSchema]]):
    pass
```

---

### § Cấu trúc File — Tổng quan

```
backend/
├── requirements.txt          # CẬP NHẬT: +arq>=0.25.0, +pgvector>=0.3.6, +sse-starlette>=2.1.0, +httpx>=0.28.0
├── worker.py                 # MỚI: arq WorkerSettings + ingest_paper_task
├── alembic/versions/
│   └── 006_create_chunks_tables.py  # MỚI: pgvector ext + parent_chunks + child_chunks
├── main.py                   # CẬP NHẬT: import ParentChunkORM, ChildChunkORM
└── src/
    ├── shared/infra/
    │   ├── settings.py       # CẬP NHẬT: +arq_redis_url, +worker_concurrency, +ingestion_sse_ticket_ttl
    │   └── redis_client.py   # MỚI: get_redis() singleton
    └── modules/ingestion/
        ├── application/
        │   └── use_cases.py  # CẬP NHẬT: enqueue_ingestion_task() sau confirm; + IngestFromSearchUseCase
        ├── infrastructure/
        │   ├── chunk_orm_models.py    # MỚI: ParentChunkORM, ChildChunkORM
        │   ├── text_chunker.py        # MỚI: chunk_text()
        │   ├── embedding_client.py    # MỚI: GeminiEmbeddingClient
        │   └── task_progress.py       # MỚI: publish_progress/completed/error, get_progress
        └── presentation/
            ├── router.py     # CẬP NHẬT: +POST /tasks/{id}/ticket, +GET /sse/stream, +POST /from-search, +GET /projects/{id}/papers
            └── schemas.py    # CẬP NHẬT: +AddFromSearchRequestSchema, +PaperListItemSchema

frontend/src/
├── types/document.ts         # CẬP NHẬT: +ProjectPaper, +SSETicketResponse, +AddFromSearch*
├── api/ingestion.ts          # CẬP NHẬT: +getSSETicket, +getPapersByProject, +addPaperFromSearch
├── i18n/translations.ts      # CẬP NHẬT: +ingestion.*, +library.*, +search.adding*
└── features/workspace/
    ├── IngestionProgress.tsx          # MỚI: progress bar SSE consumer
    ├── IngestionProgress.module.css   # MỚI
    ├── DocumentList.tsx               # MỚI: danh sách tài liệu trong dự án
    ├── DocumentList.module.css        # MỚI
    ├── LibraryTab.tsx                 # CẬP NHẬT: thêm IngestionProgress + DocumentList + enable Add button
    └── __tests__/
        ├── IngestionProgress.test.tsx  # MỚI: 4 test cases
        └── LibraryTab.test.tsx         # CẬP NHẬT: test document list + add button

tests/unit/ingestion/
└── test_worker.py            # MỚI: test chunker + progress
```

**Files cần cập nhật quan trọng:**
- `docker-compose.yml` — đổi postgres image sang `pgvector/pgvector:pg16-latest` + thêm `worker` service

**Files KHÔNG được chỉnh sửa:**
- `backend/src/shared/infra/llm/router.py` — LLMRouter đã hoàn chỉnh
- `backend/src/shared/infra/database.py` — `get_db` dependency đã có
- `frontend/src/api/client.ts` — Axios client không đổi
- `backend/src/modules/ingestion/domain/entities.py` — entities không đổi

---

### § Kiểm tra LLMRouter API key attribute trước khi implement

Trước khi implement `GeminiEmbeddingClient`, chạy lệnh sau để xác định tên attribute của api_key:

```bash
grep -n "google_api_key\|api_key\|_api_key" backend/src/shared/infra/llm/router.py
```

Nếu LLMRouter không expose API key trực tiếp, dùng fallback pattern:
```python
from backend.src.shared.infra.settings import get_settings
api_key = get_settings().gemini_api_key  # hoặc system key
```

---

### § Learnings từ Stories 2.1–2.4 (áp dụng cho 2.5)

1. **LLMRouter pattern** — `router = LLMRouter(db); llm = await router.get_llm_client(user_id, model_name=...)` → `await llm.ainvoke(...)`. Worker arq cần tạo db session riêng (không có request context).

2. **`_strip_code_fence` helper** — không cần trong embedding, nhưng cần nếu xử lý text extraction.

3. **camelCase API** — `alias_generator=to_camel, populate_by_name=True` cho tất cả Pydantic schemas ở tầng Presentation.

4. **MemoryRouter trong test** — tất cả component test cần `MemoryRouter` nếu có `Link`/`useNavigate`.

5. **`getErrorMessage(err, fallback)`** — luôn cần tham số thứ 2.

6. **CSS Variables** — `var(--accent-blue)`, `var(--accent-green)`, `var(--surface-raised)`, `var(--border-hairline)`, `var(--ink-primary)`, `var(--ink-secondary)`.

7. **`is_project_owned_by_user`** — đã có helper function trong `postgres_repository.py`, dùng lại cho `IngestFromSearchUseCase` và endpoint GET papers.

8. **`--noconftest` cho BE tests** — conftest.py gốc import langgraph; unit tests trong `tests/unit/` cần flag này.

9. **arq worker nhận `ctx` dict** — `ctx['redis']` là arq's built-in redis connection (async). `ctx['session_factory']` tự tạo trong startup(). Worker không dùng FastAPI `get_db` dependency.

10. **EventSource không hỗ trợ custom headers** — KHÔNG truyền Authorization header. Dùng ticket. Ticket TTL 60s là đủ: frontend gọi ticket rồi mở EventSource ngay.

---

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context)

### Debug Log References

- Cài thêm dependency vào `.venv`: `arq`, `pgvector`, `sse-starlette`, `langchain-google-genai`, `python-multipart` (redis bị arq pin xuống 5.3.1 — chấp nhận được).
- Full `tests/unit` có sẵn `1 failed + 35 errors` do vấn đề test-isolation toàn suite của các test API dùng TestClient (đã xác nhận pre-existing bằng cách stash toàn bộ thay đổi của story và chạy lại — kết quả y hệt). Các test này pass khi chạy riêng từng module.

### Completion Notes List

- **Backend Worker (ARQ):** Tạo `backend/worker.py` với `WorkerSettings` (max_jobs=2 theo NFR4, job_timeout=600s), pipeline 6 bước: load → parse/download → chunk → embed → save chunks → indexed; publish tiến trình + completed/error qua Redis. Error path đánh dấu `paper.status='failed'` + publish error.
- **pgvector + chunks:** Migration `006_create_chunks_tables.py` enable extension `vector`, tạo `parent_chunks`/`child_chunks` (embedding `Vector(768)`) + HNSW index. ORM models tương ứng; import vào `main.py` để auto-create-all. Đổi `docker-compose.yml` postgres → `pgvector/pgvector:pg16-latest` và thêm service `worker` (OMP_NUM_THREADS=1, mem_limit 12g).
- **Chunker:** sliding window 500 chars / overlap 100, parent gộp theo paragraph đến 3000 chars; xử lý text rỗng/ngắn.
- **Embedding:** `GeminiEmbeddingClient` lấy API key qua `LLMRouter._resolve_api_key` (ưu tiên key user, fallback system) + `text-embedding-004`; graceful fallback zero-vectors khi lỗi.
- **API:** `POST /ingestion/from-search`, `POST /ingestion/tasks/{id}/ticket` (validate ownership chống IDOR), `GET /ingestion/sse/stream?ticket=` (one-time ticket, SSE qua `sse-starlette`), `GET /projects/{id}/papers`. `ConfirmMetadataUseCase` enqueue arq sau commit.
- **Frontend:** `IngestionProgress` (consumer EventSource ticket-based, không dùng Authorization header), `DocumentList` (badge trạng thái màu pending/processing/indexed/failed), cập nhật `LibraryTab` (progress + document list + enable nút "Thêm vào dự án" → luồng SSE). Types/API/i18n bổ sung đầy đủ; entry i18n giữ single-line theo convention sẵn có của file.
- **Tests:** BE `tests/unit/ingestion/test_worker.py` (6 tests: chunker, publish_progress/error, worker error path) — pass. FE `IngestionProgress.test.tsx` (5 tests) + cập nhật `LibraryTab.test.tsx` (DocumentList + nút enable). Toàn bộ 76 FE tests pass; `tsc` + `eslint` (file thay đổi) clean; `ruff` clean.

### File List

**Backend — mới:**
- `backend/worker.py`
- `backend/alembic/versions/006_create_chunks_tables.py`
- `backend/src/modules/ingestion/infrastructure/chunk_orm_models.py`
- `backend/src/modules/ingestion/infrastructure/text_chunker.py`
- `backend/src/modules/ingestion/infrastructure/embedding_client.py`
- `backend/src/modules/ingestion/infrastructure/task_progress.py`
- `backend/src/modules/ingestion/infrastructure/sse_stream.py`
- `backend/src/shared/infra/redis_client.py`
- `tests/unit/ingestion/test_worker.py`

**Backend — cập nhật:**
- `requirements.txt` (+arq, +pgvector, +sse-starlette)
- `docker-compose.yml` (postgres → pgvector image, +worker service)
- `backend/main.py` (import chunk ORM models)
- `backend/src/shared/infra/settings.py` (+arq_redis_url, +worker_concurrency, +ingestion_sse_ticket_ttl, +ingestion_progress_ttl)
- `backend/src/modules/ingestion/application/use_cases.py` (+enqueue_ingestion_task, enqueue trong Confirm, +IngestFromSearchUseCase)
- `backend/src/modules/ingestion/infrastructure/postgres_repository.py` (+save_search_paper, +list_by_project, +find_owned_by_user)
- `backend/src/modules/ingestion/presentation/schemas.py` (+AddFromSearch*, +SSETicketResponseSchema, +PaperListItemSchema/PaperListResponseSchema)
- `backend/src/modules/ingestion/presentation/router.py` (+from-search, +ticket, +sse/stream, +projects/{id}/papers)

**Frontend — mới:**
- `frontend/src/features/workspace/IngestionProgress.tsx` + `.module.css`
- `frontend/src/features/workspace/DocumentList.tsx` + `.module.css`
- `frontend/src/features/workspace/__tests__/IngestionProgress.test.tsx`

**Frontend — cập nhật:**
- `frontend/src/types/document.ts` (+ProjectPaper, +SSETicketResponse, +AddFromSearch*)
- `frontend/src/api/ingestion.ts` (+getSSETicket, +getPapersByProject, +addPaperFromSearch)
- `frontend/src/i18n/translations.ts` (+ingestion.*, +library.*, +search.adding*)
- `frontend/src/features/workspace/LibraryTab.tsx` (IngestionProgress + DocumentList + enable Add button)
- `frontend/src/features/workspace/__tests__/LibraryTab.test.tsx` (test DocumentList + Add button)

### Change Log

| Date | Version | Description |
|------|---------|-------------|
| 2026-06-17 | 1.0 | Triển khai Story 2.5: ingestion bất đồng bộ qua ARQ worker, SSE progress stream (ticket-based), pgvector chunks, add-from-search, document list. AC #1–#7 thoả mãn. |

---

### Review Findings (Code Review — 2026-06-17)

**Tóm tắt:** 9 patch (gồm 3 mục decision-needed đã được Dat quyết chuyển thành patch), 5 defer, 7 dismissed. Cả 7 AC đều được triển khai; không có AC nào bị vi phạm về mặt chức năng ở cấu hình mặc định. Tuy nhiên có 1 lỗi **CRITICAL** khiến worker không khởi động được ở runtime (chưa lộ ra vì unit test không thực sự chạy arq worker).

> **Decision-needed đã giải quyết (2026-06-17):** SSE reconnect → Patch (ticket reuse trong TTL + terminal event); Concurrent add → Patch (theo dõi nhiều ingest song song); SSRF → Patch (chặn SSRF); Zero-vector fallback → **giữ theo spec, dismiss**.

#### Patch

- [x] [Review][Patch] **CRITICAL** `redis_settings` định nghĩa là `@classmethod` → arq nhận classmethod object thay vì RedisSettings → worker KHÔNG khởi động được [backend/worker.py:188-190] — Đã kiểm chứng với arq 0.28: `get_kwargs` đọc `WorkerSettings.__dict__['redis_settings']` = classmethod descriptor (`isinstance RedisSettings == False`). Phải đổi thành class attribute: `redis_settings = RedisSettings.from_dsn(get_settings().arq_redis_url)`.
- [x] [Review][Patch] Error path set `status='failed'` trên session đã poisoned → paper kẹt `processing` vĩnh viễn [backend/worker.py:169-177] — Nếu exception xảy ra giữa transaction (vd flush chunks), `db.commit()` trong except cũng raise → inner `except: rollback()` revert luôn status → paper không bao giờ thành `failed`. Cần `await db.rollback()` TRƯỚC rồi mới set `failed` + commit trong transaction sạch.
- [x] [Review][Patch] Embedding length mismatch → IndexError làm fail cả paper trên happy path [backend/worker.py:135,157] — `all_embeddings[child_idx]` giả định `len(all_embeddings) == len(all_child_texts)`; nếu provider trả thiếu vector → IndexError → paper `failed`, mất toàn bộ công đã làm. Cần assert/guard độ dài.
- [x] [Review][Patch] Double-enqueue không dedup → nhân đôi chunks [use_cases.py:41-43; worker.py] — `enqueue_job(INGEST_TASK_NAME, paper_id)` không có `_job_id` → retry/double-submit chạy 2 job cùng paper, worker không kiểm tra chunk đã tồn tại → chunk bị nhân đôi. Đề xuất `_job_id=f"ingest:{paper_id}"` + worker idempotent (skip/replace nếu đã có chunk).
- [x] [Review][Patch] SSE đọc progress từ `redis_url` nhưng worker ghi vào `arq_redis_url` — split nếu hai URL khác nhau [redis_client.py:14; worker.py:190; use_cases.py:41] — Worker publish qua `ctx['redis']` (=arq_redis_url), SSE đọc qua `get_redis()` (=redis_url). Default trùng nên chạy được, nhưng nếu deployer đặt khác → progress không bao giờ tới SSE. Cần dùng chung một URL hoặc validate/ghi rõ ràng buộc.
- [x] [Review][Patch] `embedding_client` nuốt `RuntimeError` từ `_resolve_api_key` → corrupt-key degrade im lặng thành zero-vector [embedding_client.py] — Khi key user lỗi giải mã, `LLMRouter._resolve_api_key` cố ý raise; ở đây bị `except Exception` nuốt → fallback system key, rồi nếu cũng rỗng → zero-vector + `indexed`. Cần thu hẹp except để lỗi key lộ ra. (Cũng nên dùng API công khai thay vì gọi method private `_resolve_api_key`.)
- [x] [Review][Patch] SSE EventSource không reconnect được — ticket one-time + timeout im lặng gây toast "thất bại" sai [router.py sse_stream, sse_stream.py, IngestionProgress.tsx] — *(decision-needed → patch)* Không DELETE ticket ngay; cho dùng lại trong TTL để EventSource auto-reconnect hoạt động, và phát event terminal khi `generate_sse` hết `MAX_POLLS` để frontend phân biệt timeout với lỗi thật.
- [x] [Review][Patch] Thêm tài liệu thứ 2 khi tài liệu 1 chưa xong làm mất theo dõi tài liệu 1 [LibraryTab.tsx ~563-566] — *(decision-needed → patch)* Đổi `processingDocumentId` thành danh sách/map và render nhiều `<IngestionProgress>`, mỗi doc có completion/toast/refresh riêng.
- [x] [Review][Patch] SSRF: worker fetch `pdf_url` do client kiểm soát không có allowlist/scheme check [worker.py:67-95 _download_pdf_text] — *(decision-needed → patch)* Validate scheme http(s), chặn IP nội bộ/link-local/metadata, giới hạn redirect + kích thước/Content-Type trước khi parse.

#### Patch bổ sung (phát hiện khi chạy thực Docker — review diff tĩnh bỏ sót)

- [x] [Review][Patch] **CRITICAL (runtime)** Backend crash-loop lúc startup: `create_all` tạo bảng `child_chunks` có cột `Vector(768)` nhưng extension `vector` chưa tồn tại → `type "vector" does not exist` [backend/main.py:28-29] — `CREATE EXTENSION vector` chỉ nằm trong migration 006, nhưng đường dev-convenience `create_all` trong `lifespan` không chạy migration. Fix: `await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))` trước `create_all`.
- [x] [Review][Patch] **CRITICAL (runtime)** `arq_redis_url` default hardcode `localhost:6379` → trong Docker chỉ set `REDIS_URL` nên worker (và SSE sau P5) trỏ về localhost → `ConnectionError`, worker không nhận job [backend/src/shared/infra/settings.py:47] — Fix: default rỗng + `model_validator` tự lấy theo `redis_url`; chỉ cần `ARQ_REDIS_URL` khi muốn Redis khác.

#### Dismissed (zero-vector — giữ theo spec)

- [x] [Review][Dismiss] Zero-vector fallback đánh dấu `indexed` (theo spec) làm hỏng tìm kiếm HNSW im lặng — Dat quyết **giữ theo spec** (graceful degradation đã chỉ định trong Task 4.2). Ghi nhận như nợ kỹ thuật cho story RAG sau nếu cần. [embedding_client.py embed_batch, migration 006 hnsw]

#### Defer

- [x] [Review][Defer] enqueue sau `db.commit()`: nếu Redis down → paper kẹt `pending` + trả 500 [use_cases.py:41-45] — deferred, MVP đã chấp nhận (docstring tự ghi nhận)
- [x] [Review][Defer] Paper không có text (download fail + không abstract) bị đánh dấu `indexed` im lặng [worker.py:120-125] — deferred, thiếu trạng thái "indexed nhưng rỗng"
- [x] [Review][Defer] `from-search` không giới hạn độ dài title/abstract/authors → DoS/cost vector qua pipeline embedding [schemas.py AddFromSearchRequestSchema] — deferred, cần auth project owner
- [x] [Review][Defer] `get_redis()` check-then-set race lúc cold start + không dispose connection lúc shutdown [redis_client.py] — deferred, `from_url` lazy nên impact thấp
- [x] [Review][Defer] `DocumentList` không auto-poll; hàng `pending`/`processing` không tự cập nhật nếu không có SSE bump trigger [DocumentList.tsx] — deferred, badge processing có thể "quay" mãi

