# Sprint Change Proposal — Real RAG Retriever (thay `mock_rag_node`)

- **Ngày:** 2026-06-17
- **Người đề xuất:** Dat
- **Workflow:** correct-course (BMad)
- **Mode review:** Batch
- **Phân loại phạm vi:** **Moderate** (thêm 1 story mới vào Epic 3 đã "done" → mở lại `epic-3` thành in-progress; chạm backend orchestrator + SSE protocol + frontend chat receiver).

---

## Section 1 — Issue Summary

### Vấn đề
Toàn bộ pipeline ingestion → chunking parent-child → embedding (Gemini `text-embedding-004`) → lưu pgvector (HNSW index) đã hoàn tất ở **Story 2.5**. Nhưng node RAG trong orchestrator vẫn là **mock**:

- [graph.py:29](backend/src/modules/orchestrator/application/graph.py#L29) — `mock_rag_node` trả về text cố định và `valid_citation_ids = []`, **chưa hề truy vấn pgvector**.
- Hệ quả dây chuyền: không sinh `[1]`,`[2]` thật → **Citation Guardrail** (Story 3.4) không có gì để kiểm chứng → **tooltip** (Story 3.5) không có dữ liệu thật.

### Bằng chứng phát hiện trong lúc phân tích
Có **một lỗi tích hợp thực sự** (không chỉ là "thiếu dữ liệu thật"):

- [CitationBadge.tsx:23](frontend/src/components/CitationBadge.tsx#L23) truyền **ordinal** (`"1"`) trực tiếp vào `getCitationDetail` → gọi `GET /api/citations/1`.
- Nhưng [citation_router.py:17](backend/src/modules/orchestrator/presentation/citation_router.py#L17) khai báo `chunk_id: UUID` → request `/citations/1` **fail 422** (ordinal không phải UUID).
- ⇒ Dù có bật RAG thật, tooltip **vẫn hỏng** nếu không có lớp ánh xạ `ordinal → chunk UUID`.

Đây chính là lý do `citation_map` (ordinal→UUID) emit qua SSE là **bắt buộc**, không phải "nice to have".

### Ràng buộc thiết kế đã chốt (quan trọng)
- **Citation Guardrail giữ nguyên cơ chế ordinal.** LLM viết `[1]`,`[2]` (ordinal), không viết UUID. [graph.py:15](backend/src/modules/orchestrator/application/graph.py#L15) `apply_citation_guardrail` kiểm `[N]` theo tập ordinal hợp lệ → **không đổi semantics**. Phần "chunk UUID thật" nằm ở `citation_map`, đi song song.
- Vì vậy yêu cầu "trả `valid_citation_ids` là UUID cho Guardrail" được diễn giải đúng kiến trúc thành: **`valid_citation_ids` = ordinals (cho Guardrail)** + **`citation_map: dict[ordinal → chunk UUID]` (cho frontend tooltip)**.

---

## Section 2 — Impact Analysis

### Epic Impact
- **Epic 3** (đang `in-progress` trong sprint-status, ghi "✅ done" trong epics.md): thêm **Story 3.6**. Giữ `epic-3 = in-progress` tới khi 3.6 done. Cập nhật ghi chú trạng thái trong epics.md.
- Epic 4/5: không ảnh hưởng.

### Story Impact
| Story | Ảnh hưởng |
|---|---|
| 3.2 (Chat RAG SSE) | Gỡ nợ kỹ thuật: `mock_rag` → real RAG node. SSE protocol mở rộng thêm frame `citation_map`. Chuyển từ "giả-stream sau ainvoke" sang **stream token thật** (`astream_events`). |
| 3.4 (Citation Guardrail) | **Không đổi logic guardrail** — lần đầu tiên có `valid_citation_ids` thật để hoạt động. |
| 3.5 (Citation Tooltip UI) | Sửa **lỗi ordinal→UUID**: `CitationBadge` nhận UUID thật từ `citation_map` thay vì truyền ordinal vào API. |
| 3.1, 3.3 | Không ảnh hưởng. |

### Artifact Conflicts (cần cập nhật)
- `epics.md`: thêm mục Story 3.6; cập nhật ghi chú nợ kỹ thuật ở 3.2; xóa mục tương ứng trong "Khoảng trống đã biết"; cập nhật dòng trạng thái thực thi.
- `sprint-status.yaml`: thêm `3-6-...: backlog`.
- Architecture: không cần đổi (đã mô tả RAG qua pgvector ở NFR3); chỉ là hiện thực hóa.

### Technical Impact (backend + frontend)
**Backend (`orchestrator`):**
1. `ChatState` thêm `project_id`, `user_id`, `citation_map: dict[int, str]`. (`valid_citation_ids` đổi diễn giải sang ordinals — đã đúng kiểu `list[int]`.)
2. `mock_rag_node` → `real_rag_node`:
   - Embed câu hỏi qua **tái dùng** `GeminiEmbeddingClient(user_id, db).embed_batch([query])` ([embedding_client.py](backend/src/modules/ingestion/infrastructure/embedding_client.py)).
   - **pgvector cosine similarity** trên `child_chunks.embedding` (`<=>`), scope theo `project_id`, lấy top-K (K cấu hình, mặc định 5), kèm `ORDER BY embedding <=> :q LIMIT K`.
   - Gán ordinal 1..K cho các chunk; build context prompt; gọi LLM **stream** qua `LLMRouter(db).get_llm_client(user_id).astream(...)`.
   - Trả `valid_citation_ids=[1..K]` + `citation_map={1: <uuid>, ...}`.
3. **Empty retrieval** (chưa ingest / không đủ similarity): **bỏ qua LLM**, trả câu cố định "Chưa có tài liệu liên quan trong dự án để trích dẫn.", `valid_citation_ids=[]`, `citation_map={}`. (Chống hallucination — đúng tinh thần Epic 3.)
4. **SSE protocol**: `run_registry` queue đổi từ `Queue[str|None]` → carry **structured frames** (`{"type":"chunk",...}`, `{"type":"citation_map","data":{...}}`, `None`). `_stream_graph_to_queue` stream token thật rồi emit `citation_map` (sau khi guardrail chạy xong) ngay trước `done`. `event_generator` ([router.py:165](backend/src/modules/orchestrator/presentation/router.py#L165)) serialize frame mới.
5. `SendMessageUseCase` lấy `project_id` từ thread (đã có) → truyền vào graph config; **không cần đổi API request schema**.

**Frontend:**
6. `ChatbotPanel` SSE receiver xử lý thêm frame `citation_map`, lưu map theo message, truyền xuống `MessageContent`.
7. `MessageContent` + `CitationBadge`: resolve ordinal → UUID qua `citation_map` **trước khi** gọi `getCitationDetail(uuid)`. Nếu thiếu map (tin nhắn lịch sử cũ) → tooltip "không tìm thấy" gracefully (giữ hành vi hiện tại).

> ⚠️ **Lưu ý streaming vs guardrail:** Token stream là bản **trước** guardrail (LLM có thể viết `[7]` ảo). Guardrail chạy ở node sau, làm sạch bản **final** đã lưu DB. Frontend khi `done` thay `streamingContent` bằng message đã lưu (đã sạch) + render citation theo `citation_map`. Hành vi này **nhất quán** với ghi chú 3.5 "streaming KHÔNG parse citation".

### Lưu ý NFR
- **NFR3**: cần HNSW index trên `child_chunks.embedding` cho RAG < 500ms. Story phải kiểm tra index tồn tại (Story 2.5 đã tạo) và dùng cosine ops (`vector_cosine_ops`).

---

## Section 3 — Recommended Approach

**Direct Adjustment** — thêm **Story 3.6** mới trong Epic 3 (không rollback, không cắt scope). Mở lại `epic-3` thành in-progress.

- **Lý do:** Pipeline ingest đã sẵn sàng; đây là việc "nối dây" cuối cùng để FR6 (RAG Chat) + FR10 (Citation) hoạt động end-to-end thật. Tái dùng tối đa adapter có sẵn (`GeminiEmbeddingClient`, `LLMRouter`).
- **Effort ước lượng:** Trung bình–cao. Backend ~60% (node RAG + SSE refactor stream token thật là phần nặng nhất), frontend ~40% (citation_map plumbing + sửa lỗi ordinal→UUID).
- **Rủi ro chính:** (a) Refactor SSE từ giả-stream sang `astream_events` chạm `run_registry`/`_stream_graph_to_queue`/`router`/`ChatbotPanel` — cần test reconnect/last-event. (b) Latency LLM thật + embedding round-trip. (c) Cost/quota API key user.

---

## Section 4 — Detailed Change Proposals

### 4.1 — Story mới (thêm vào `epics.md`, sau Story 3.5)

```
### Story 3.6: [BE+FE] Real RAG Retriever — pgvector Similarity & Citation Map qua SSE — ⏳ backlog

Thay `mock_rag_node` bằng retriever thật: embed câu hỏi (Gemini text-embedding-004),
cosine similarity search trên `child_chunks.embedding` (pgvector, scope project_id, top-K),
sinh câu trả lời có trích dẫn `[N]` bằng LLM (stream token thật), trả `valid_citation_ids`
(ordinals) cho Citation Guardrail và emit `citation_map` (ordinal→chunk UUID) qua SSE để
frontend Story 3.5 hiển thị tooltip thật. Đồng thời sửa lỗi `CitationBadge` đang gửi ordinal
vào API `/citations/{uuid}` (422).

- **Gộp từ kế hoạch cũ:** Hiện thực hóa phần Real RAG của Story 3.3 gốc (LangGraph + RAG),
  vốn bị tách ra dạng Mock ở Story 3.2. Gỡ nợ kỹ thuật ghi ở "Khoảng trống đã biết".
- **FRs:** FR6, FR10, NFR3.

**Acceptance Criteria (nháp — sẽ chi tiết hóa khi create-story):**
1. `real_rag_node` embed câu hỏi qua GeminiEmbeddingClient và truy vấn pgvector cosine
   (`embedding <=> :q`) trên child_chunks scope theo project_id, top-K (mặc định 5).
2. Node build context theo ordinal [1..K] và gọi LLM (LLMRouter) sinh câu trả lời có `[N]`,
   stream token thật qua SSE (astream).
3. Node trả `valid_citation_ids` = danh sách ordinal hợp lệ; Citation Guardrail giữ nguyên
   logic, lần đầu lọc trên dữ liệu thật.
4. Node trả `citation_map` (ordinal→chunk UUID); SSE emit frame `citation_map` ngay trước `done`.
5. Khi retrieval rỗng (chưa ingest / dưới ngưỡng): trả câu cố định "Chưa có tài liệu liên quan
   trong dự án để trích dẫn.", `valid_citation_ids=[]`, `citation_map={}`, KHÔNG gọi LLM.
6. `CitationBadge` resolve ordinal→UUID qua citation_map trước khi gọi `GET /api/citations/{uuid}`;
   tooltip hiển thị title + text chunk thật.
7. RAG query đáp ứng NFR3 (< 500ms khi DB < 100k vector) — dùng HNSW + vector_cosine_ops.
8. Owner scoping: chỉ retrieve chunk thuộc project của user (chống IDOR), nhất quán
   GetCitationDetailUseCase.
```

### 4.2 — Sửa ghi chú nợ kỹ thuật ở Story 3.2 (`epics.md` dòng ~247)

```
OLD:
- **⚠️ Ghi chú nợ kỹ thuật:** RAG hiện là **Mock node** (`mock_rag_node` trong
  `orchestrator/application/graph.py`) trả text cố định, **chưa truy vấn pgvector**.
  Xem mục "Khoảng trống đã biết" cuối tài liệu.

NEW:
- **⚠️ Ghi chú nợ kỹ thuật:** RAG khởi đầu là Mock node; được thay bằng retriever thật
  ở **Story 3.6** (pgvector cosine + citation_map qua SSE).
```

### 4.3 — Cập nhật mục "Khoảng trống đã biết" (`epics.md` cuối file)

Chuyển mục "Real RAG Retrieval Node" từ gap sang đã-có-story:
```
OLD: - **Real RAG Retrieval Node (thay `mock_rag_node`):** ... **Cần một story mới**: ...
NEW: - **Real RAG Retrieval Node (thay `mock_rag_node`):** ✅ Đã tạo **Story 3.6** (2026-06-17,
     correct-course) để hiện thực hóa. Xem Epic 3.
```

### 4.4 — Cập nhật dòng trạng thái thực thi (`epics.md` dòng ~115–116)

```
OLD: > Epic 1 ✅ done · Epic 2 ✅ done · Epic 3 ✅ done · Epic 4 ⏳ backlog · Epic 5 ⏳ backlog
     > Tổng: **25 story** ...
NEW: > Epic 1 ✅ done · Epic 2 ✅ done · Epic 3 ⏳ in-progress (3.1–3.5 done, 3.6 backlog) ·
       Epic 4 ⏳ backlog · Epic 5 ⏳ backlog
     > Tổng: **26 story** ...
```

### 4.5 — `sprint-status.yaml` (thêm dưới `3-5-...`)

```
OLD:
  3-5-giao-dien-tuong-tac-the-trich-dan: done
  epic-3-retrospective: optional
NEW:
  3-5-giao-dien-tuong-tac-the-trich-dan: done
  3-6-real-rag-retriever-pgvector-citation-map-sse: backlog
  epic-3-retrospective: optional
```

---

## Section 5 — Implementation Handoff

- **Phân loại:** Moderate.
- **Bước kế tiếp:** Chạy `bmad-create-story` cho Story 3.6 để sinh file story chi tiết (đầy đủ AC, dev notes, test plan) tại `implementation-artifacts/3-6-real-rag-retriever-pgvector-citation-map-sse.md`, rồi `bmad-dev-story` để triển khai.
- **Người nhận:** Developer agent (Amelia) cho implementation; có thể nhờ Architect (Winston) review điểm SSE token-streaming nếu cần.
- **Success criteria:** 8 AC ở 4.1 pass; tooltip hiển thị text chunk thật end-to-end; guardrail thay `[N]` ảo; NFR3 đạt.

---

## Phụ lục — File sẽ bị chạm khi implement (tham khảo)
- `backend/src/modules/orchestrator/application/graph.py` (node + ChatState)
- `backend/src/modules/orchestrator/application/use_cases.py` (`_stream_graph_to_queue`, `SendMessageUseCase`)
- `backend/src/modules/orchestrator/infrastructure/run_registry.py` (queue frame type)
- `backend/src/modules/orchestrator/presentation/router.py` (`event_generator`)
- `backend/src/modules/ingestion/infrastructure/embedding_client.py` (tái dùng)
- `backend/src/shared/infra/llm/router.py` (tái dùng)
- `frontend/src/features/workspace/ChatbotPanel.tsx`, `frontend/src/components/MessageContent.tsx`, `frontend/src/components/CitationBadge.tsx`, `frontend/src/api/citations.ts`
</content>
</invoke>
