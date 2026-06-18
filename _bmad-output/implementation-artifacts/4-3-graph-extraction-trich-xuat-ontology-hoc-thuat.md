---
baseline_commit: 1b048c8
---

# Story 4.3: [Backend] Graph Extraction — Trích xuất Ontology Học thuật (Stage-2 Ingestion)

Status: done

## Story

As a **kỹ sư backend của C2-App-053**,
I want **một arq task Stage-2 chạy ngay sau khi `ingest_paper_task` hoàn thành, gọi `gemini-2.5-pro` trích xuất Nodes học thuật (Finding, Limitation, Method, Dataset, Topic, Problem) và Edges (`[:HAS_FINDING]`, `[:HAS_LIMITATION]`, `[:CONTRADICTS]`, `[:SUPPORTS]`) từ nội dung bài báo đã được chunk, ghi event `ONTOLOGY_EXTRACTED` vào `sync_outbox`, và outbox_worker của Story 4.1 dispatch sang Neo4j MERGE idempotent — đồng thời thêm Unique Constraints ontology cho Neo4j và một endpoint admin backfill cho tài liệu cũ**,
so that **Knowledge Map (Story 4.2) hiển thị không chỉ Paper/Author mà còn Finding/Limitation và các cạnh học thuật, cung cấp dữ liệu thật cho gap_detection (Story 4.4) và Gap Analyst Agent (Story 4.5)**.

## Bối cảnh & Phạm vi

Story này là **[Backend] vertical slice xuyên 2 module**:
- `[ingestion]` — **PRODUCER**: Stage-2 Graph Extraction (`graph_extract_task` + `graph_extractor.py`), mở rộng pipeline arq Story 2.5
- `[graph_rag]` — **CONSUMER**: thêm Unique Constraints ontology vào `neo4j_client.py` + handler `handle_ontology_extracted` đăng ký vào `HANDLER_MAP`

**Phụ thuộc đã done:** Story 2.5 (ingestion worker arq), Story 4.1 (sync_outbox + HANDLER_MAP mở rộng được), Story 4.2 (Knowledge Map FE — sẽ hưởng lợi khi có dữ liệu ontology)

**Ranh giới:**
- ✅ TRONG phạm vi: `graph_extract_task` arq + `GraphExtractor` class (LLM call `gemini-2.5-pro`) + event `ONTOLOGY_EXTRACTED` → Neo4j MERGE Finding/Limitation/Method/Dataset/Topic/Problem + edges HAS_FINDING/HAS_LIMITATION/CONTRADICTS/SUPPORTS + cập nhật `Paper.abstract` trên Neo4j + Unique Constraints ontology + endpoint admin backfill + unit tests
- ❌ NGOÀI phạm vi: FILLS_GAP (cần cross-paper context → Story 4.4); Leiden community detection (Phase 2); FE hiển thị Finding node trên Cytoscape (Story 4.4 sẽ tiêu thụ); `graph_search`/`gap_detection` API (Story 4.4); Author entity resolution nâng cao Jaccard/cosine (Phase 2, MVP chỉ dùng exact normalized name từ 4.1)

### Quyết định kiến trúc đã chốt

1. **Stage-2 là arq task riêng** (`graph_extract_task`), enqueued bởi `ingest_paper_task` sau khi commit thành công. KHÔNG gộp vào cùng task ingestion (tránh timeout 600s khi LLM Pro chậm).
2. **Input cho LLM**: concatenate parent_chunks của paper từ Postgres (đã chunk ở Stage-1, tránh re-parse file). Fallback về `paper.abstract` nếu không có chunk (paper metadata_only).
3. **Giới hạn text**: 30000 chars để phù hợp token budget của `gemini-2.5-pro` (context window đủ lớn).
4. **IDs idempotent**: `{paper_id}:f:{n}`, `{paper_id}:l:{n}`, `{paper_id}:m:{n}`, `{paper_id}:d:{n}`, `{paper_id}:t:{n}`, `{paper_id}:pr:{n}` — đảm bảo MERGE an toàn khi re-run.
5. **Event duy nhất** `ONTOLOGY_EXTRACTED` per paper (payload chứa toàn bộ entities) thay vì nhiều event nhỏ — giữ atomic.
6. **Backfill**: admin endpoint `POST /api/admin/backfill-graph-extraction` (admin role) — re-enqueue `graph_extract_task` cho mọi paper `status="indexed"` và `is_deleted=false`. Idempotent do MERGE.
7. **LLM failures**: graceful — nếu LLM fail/trả JSON lỗi → log warning, KHÔNG viết event, KHÔNG fail paper (paper vẫn `indexed`, chỉ thiếu ontology). Retry không tự động (tránh tốn token); admin dùng backfill endpoint.
8. **`Paper.abstract` update**: handler `handle_ontology_extracted` cũng SET `p.abstract = $abstract` và `p.authors = $authors` trên Paper node trong Neo4j (vá lỗi defer từ Story 4.2 review).

## Acceptance Criteria

### A. [ingestion] Stage-2 Graph Extraction — `GraphExtractor`

1. Tạo `backend/src/modules/ingestion/infrastructure/graph_extractor.py` với class `GraphExtractor`:
   - `__init__(self, user_id: str, db: AsyncSession)` — inject user_id + db cho LLMRouter
   - `async def extract(self, paper_id: str, project_id: str, title: str, abstract: str, text: str) -> dict | None` — gọi LLM, trả dict JSON parsed hoặc `None` nếu lỗi
   - Dùng `LLMRouter(db).get_llm_client(user_id, model_name="gemini-2.5-pro")` (mirror pattern `LLMMetadataExtractor`)
   - Prompt trích xuất học thuật chi tiết (xem Dev Notes §Prompt)
   - Giới hạn `text[:30000]`
   - Strip code fence (```` ```json ... ``` ````) trước khi parse JSON (tái dùng pattern `_strip_code_fence` từ `metadata_extractor.py`)
   - Nếu `json.loads` fail hoặc LLM exception → `logger.warning(...)` + trả `None` (KHÔNG raise)
   - Validate: result phải là dict với ít nhất 1 key trong `{findings, limitations, methods, datasets, topics, problems}` — nếu không → trả `None`

2. `GraphExtractor.extract` trả dict có cấu trúc:
   ```python
   {
     "findings": [{"id": "f1", "description": "...", "confidence_score": 0.85}],
     "limitations": [{"id": "l1", "description": "..."}],
     "methods": [{"id": "m1", "name": "...", "description": "..."}],
     "datasets": [{"id": "d1", "name": "...", "description": "..."}],
     "topics": [{"id": "t1", "name": "..."}],
     "problems": [{"id": "pr1", "description": "..."}],
     "contradicts": [{"from_id": "f1", "to_id": "f2"}],
     "supports": [{"from_id": "f1", "to_id": "f2"}],
   }
   ```

### B. [ingestion] `graph_extract_task` arq task

3. Tạo hàm `async def graph_extract_task(ctx, paper_id: str) -> None` trong `backend/worker.py`:
   - Load `PaperORM` từ DB; skip nếu `None` hoặc `paper.is_deleted` hoặc `paper.status != "indexed"`
   - Lấy text: đọc `ParentChunkORM` của paper (order by `chunk_index`), join content. Nếu không có chunk → dùng `paper.abstract or ""`
   - Tạo `GraphExtractor(user_id=paper.user_id, db=db)`, gọi `.extract(...)`
   - Nếu `None` → log + return (no-op)
   - Chuẩn hóa IDs: thay `id` LLM trả (vd `"f1"`) thành `f"{paper_id}:f:{n}"` theo index (Finding), `f"{paper_id}:l:{n}"` (Limitation), `f"{paper_id}:m:{n}"` (Method), `f"{paper_id}:d:{n}"` (Dataset), `f"{paper_id}:t:{n}"` (Topic), `f"{paper_id}:pr:{n}"` (Problem). Map old→new IDs cho edges `contradicts`/`supports`.
   - Ghi `SyncOutboxORM(event_type="ONTOLOGY_EXTRACTED", project_id=paper.project_id, payload={...})` vào DB + commit (transaction riêng — paper đã committed ở ingest_paper_task)
   - Payload đầy đủ: `{paper_id, project_id, abstract: paper.abstract, authors: paper.authors, findings: [...], limitations: [...], methods: [...], datasets: [...], topics: [...], problems: [...], contradicts: [...], supports: [...]}`

4. `graph_extract_task` được đăng ký vào `WorkerSettings.functions` (thêm vào list hiện tại `[ingest_paper_task]`).

5. `ingest_paper_task` enqueue `graph_extract_task` sau khi commit thành công:
   - Thêm `await redis.enqueue_job("graph_extract_task", paper_id, _job_id=f"graph_extract:{paper_id}")` ngay SAU `await publish_completed(redis, paper_id)` trong nhánh success
   - `_job_id` cố định theo `paper_id` để arq tự khử trùng (re-enqueue khi backfill không tạo job trùng)
   - KHÔNG thêm vào nhánh `except` hoặc nhánh "paper đã bị xóa"

6. `ingest_paper_task` nhánh "không có text → metadata_only" (line ~307-315 hiện tại) **cũng enqueue** `graph_extract_task` vì abstract vẫn có thể có Finding/Limitation (fallback text = abstract).

### C. [graph_rag] Unique Constraints Ontology

7. Thêm hàm `async def create_ontology_constraints(driver: AsyncDriver) -> None` vào `backend/src/shared/infra/neo4j_client.py`:
   - Tạo idempotent 6 constraints: `Finding.id UNIQUE`, `Limitation.id UNIQUE`, `Method.id UNIQUE`, `Dataset.id UNIQUE`, `Topic.id UNIQUE`, `Problem.id UNIQUE`
   - Pattern giống `create_base_constraints` hiện có (IF NOT EXISTS, try/except per constraint)
   - Log `"Neo4j ontology constraints đã được đảm bảo."`

8. `startup(ctx)` trong `worker.py` gọi `await create_ontology_constraints(neo4j_driver)` ngay SAU `await create_base_constraints(neo4j_driver)` (dòng ~153 hiện tại).

### D. [graph_rag] Handler Neo4j cho ONTOLOGY_EXTRACTED

9. Thêm handler `async def handle_ontology_extracted(session: AsyncSession, payload: dict) -> None` vào `backend/src/modules/graph_rag/infrastructure/neo4j_adapter.py`:
   - **Bước 0 — Cập nhật Paper node** (vá defer Story 4.2): SET `p.abstract = $abstract` và `p.authors = $authors` nếu có trong payload
   - **Bước 1 — Finding nodes + HAS_FINDING edges** (idempotent MERGE):
     ```cypher
     MERGE (f:Finding {id: $id})
     ON CREATE SET f.description=$desc, f.confidence_score=$score, f.project_id=$project_id, f.created_at=datetime()
     ON MATCH SET f.description=$desc, f.confidence_score=$score, f.updated_at=datetime()
     WITH f MATCH (p:Paper {id: $paper_id}) MERGE (p)-[:HAS_FINDING]->(f)
     ```
   - **Bước 2 — Limitation nodes + HAS_LIMITATION edges** (pattern tương tự)
   - **Bước 3 — Method/Dataset/Topic/Problem nodes + edges** (HAS_METHOD, USES_DATASET, HAS_TOPIC, ADDRESSES):
     - Method/Dataset có property `name` + `description`
     - Topic/Problem có property `name`/`description`
   - **Bước 4 — CONTRADICTS/SUPPORTS edges giữa Findings**:
     ```cypher
     MATCH (f1:Finding {id: $from_id}), (f2:Finding {id: $to_id})
     WHERE f1.project_id=$project_id AND f2.project_id=$project_id
     MERGE (f1)-[:CONTRADICTS]->(f2)
     ```
     (scope `project_id` trên Finding chống IDOR; dùng MATCH không phải MERGE node để tránh tạo Finding rác)
   - Skip gracefully nếu bất kỳ entity list nào rỗng (không crash)
   - Mỗi bước chạy trong cùng session Neo4j (transaction manager do driver xử lý)

10. Đăng ký vào `HANDLER_MAP` (cuối file `neo4j_adapter.py`):
    ```python
    HANDLER_MAP["ONTOLOGY_EXTRACTED"] = handle_ontology_extracted
    ```
    (KHÔNG xóa các entry cũ)

### E. Admin Backfill Endpoint

11. Thêm endpoint `POST /api/admin/backfill-graph-extraction` vào admin router (file tại `backend/src/modules/admin/presentation/router.py` hoặc bất kỳ router nào hiện đăng ký admin routes — dev cần tìm và xác nhận):
    - Requires `current_user.role == "admin"` (pattern hiện có trong codebase)
    - Query tất cả papers: `status="indexed"`, `is_deleted=False`
    - Enqueue `graph_extract_task` cho từng paper (dùng `arq.create_pool` + `_job_id=f"graph_extract:{paper_id}"` để idempotent)
    - Response: `{"enqueued": N, "message": "Đã đưa N tài liệu vào hàng đợi trích xuất ontology"}`
    - Chạy OK ngay cả khi N=0

### F. Tests

12. Unit tests tại `tests/unit/ingestion/test_graph_extractor.py`:
    - `test_extract_returns_dict_on_valid_json`: mock LLM trả valid JSON → trả dict (không raise)
    - `test_extract_returns_none_on_invalid_json`: mock LLM trả `"not json"` → trả `None` (không raise)
    - `test_extract_returns_none_on_llm_exception`: mock LLM raise `Exception` → trả `None`
    - `test_extract_returns_none_on_empty_entities`: mock LLM trả `{"findings":[], "limitations":[], "methods":[], "datasets":[], "topics":[], "problems":[]}` → trả `None` (không có entity nào)

13. Unit tests tại `tests/unit/graph_rag/test_ontology_handler.py`:
    - `test_handle_ontology_extracted_merges_finding_and_edge`: mock session, gọi handler với payload có 1 finding → session.run được gọi, query chứa "MERGE" và "Finding" và "HAS_FINDING"
    - `test_handle_ontology_extracted_merges_limitation`: payload có 1 limitation → query chứa "Limitation" và "HAS_LIMITATION"
    - `test_handle_ontology_extracted_merges_contradicts`: payload có 1 contradicts edge → query chứa "CONTRADICTS"
    - `test_handle_ontology_extracted_empty_payload`: payload với tất cả lists rỗng → không crash, session.run có thể được gọi hoặc không
    - `test_handle_ontology_extracted_updates_paper_abstract`: payload có `abstract` → query chứa SET + abstract
    - `test_ontology_handler_in_handler_map`: import `HANDLER_MAP`, assert `"ONTOLOGY_EXTRACTED" in HANDLER_MAP`

14. Tests worker (thêm vào `tests/unit/ingestion/test_worker.py` hoặc tạo file mới `test_graph_extract_task.py`):
    - `test_graph_extract_task_skips_deleted_paper`: paper `is_deleted=True` → không gọi GraphExtractor, không ghi outbox
    - `test_graph_extract_task_skips_non_indexed_paper`: paper `status="processing"` → skip
    - `test_graph_extract_task_writes_ontology_event`: paper indexed + GraphExtractor trả dict → SyncOutboxORM được add + commit

## Tasks / Subtasks

- [x] **Task 1 — [ingestion] GraphExtractor LLM client** (AC: 1,2)
  - [x] Tạo `backend/src/modules/ingestion/infrastructure/graph_extractor.py`
  - [x] Class `GraphExtractor` với `__init__` + `extract()` method
  - [x] Prompt học thuật + JSON parsing + strip code fence (tái dùng pattern `metadata_extractor.py`)
  - [x] Graceful failure: exception/invalid JSON → return `None`
  - [x] Unit tests `tests/unit/ingestion/test_graph_extractor.py` (AC: 12)

- [x] **Task 2 — [ingestion] `graph_extract_task` arq task** (AC: 3,4,5,6)
  - [x] Thêm hàm `graph_extract_task(ctx, paper_id)` vào `backend/worker.py`
  - [x] Load paper, skip guards (deleted/not-indexed)
  - [x] Lấy text từ `ParentChunkORM` (join content) + fallback abstract
  - [x] Gọi `GraphExtractor`, chuẩn hóa IDs, ghi `SyncOutboxORM(ONTOLOGY_EXTRACTED)`
  - [x] Đăng ký vào `WorkerSettings.functions`
  - [x] Sửa `ingest_paper_task`: enqueue `graph_extract_task` sau success (cả nhánh full-text lẫn metadata-only)
  - [x] Unit tests `test_graph_extract_task` (AC: 14)

- [x] **Task 3 — [graph_rag] Ontology Constraints Neo4j** (AC: 7,8)
  - [x] Thêm `create_ontology_constraints(driver)` vào `backend/src/shared/infra/neo4j_client.py`
  - [x] 6 constraints: Finding, Limitation, Method, Dataset, Topic, Problem — IF NOT EXISTS
  - [x] Gọi từ `startup(ctx)` trong `worker.py` ngay sau `create_base_constraints`

- [x] **Task 4 — [graph_rag] Handler `handle_ontology_extracted`** (AC: 9,10)
  - [x] Thêm handler vào `backend/src/modules/graph_rag/infrastructure/neo4j_adapter.py`
  - [x] Bước 0: SET Paper.abstract + Paper.authors
  - [x] Bước 1-3: MERGE Finding/Limitation/Method/Dataset/Topic/Problem + edges
  - [x] Bước 4: MERGE CONTRADICTS/SUPPORTS edges giữa Findings (scope project_id)
  - [x] Đăng ký `HANDLER_MAP["ONTOLOGY_EXTRACTED"] = handle_ontology_extracted`
  - [x] Unit tests `tests/unit/graph_rag/test_ontology_handler.py` (AC: 13)

- [x] **Task 5 — [admin] Backfill Endpoint** (AC: 11)
  - [x] Tìm file admin router (xem `backend/main.py` để xác định path)
  - [x] Thêm `POST /api/admin/backfill-graph-extraction` với admin role check
  - [x] Query indexed papers + enqueue graph_extract_task + response JSON

## Dev Notes

### Kiến trúc & ràng buộc bắt buộc

- **Hexagonal Architecture §9.5**: `GraphExtractor` đặt tại `ingestion/infrastructure/` (driven adapter, gọi LLM external). Logic orchestrate (load chunks, ghi outbox) ở `graph_extract_task` trong `worker.py` (ingestion worker = composition root, được phép gọi infra). Handler `handle_ontology_extracted` ở `graph_rag/infrastructure/neo4j_adapter.py`.
- **Module boundaries §9.6**: `worker.py` (ingestion boundary) ghi `SyncOutboxORM` (chủ sở hữu: `workspace`). `graph_rag/infrastructure/` CONSUME event qua `HANDLER_MAP`. Không module nào gọi trực tiếp neo4j_adapter từ ingestion.
- **KHÔNG sửa** `neo4j_adapter.py` `HANDLER_MAP` từ `worker.py` (không cross-module infra call). `HANDLER_MAP` được sửa ngay trong file `neo4j_adapter.py`.
- **Outbox_worker forward-compat**: `outbox_worker.py` dòng 171-188 đã có guard "event lạ" tăng retry + warn. Khi deploy Story 4.3, event `ONTOLOGY_EXTRACTED` trước khi code deploy sẽ bị retry rồi DLQ → **OK** vì backfill endpoint sẽ re-enqueue sau deploy.

### Pattern code cần tái dùng

- **LLMRouter pattern**: xem `backend/src/modules/ingestion/infrastructure/metadata_extractor.py:37-41`
  ```python
  router = LLMRouter(self._db)
  llm = await router.get_llm_client(self._user_id, model_name="gemini-2.5-pro")
  result = await llm.ainvoke(prompt)
  content = self._coerce_to_text(result.content)  # handle str | list
  content = self._strip_code_fence(content)
  data = json.loads(content)
  ```
  Copy `_coerce_to_text` + `_strip_code_fence` hoặc extract sang shared util.

- **arq enqueue pattern**: xem `ingest_paper_task` → `enqueue_ingestion_task` trong `use_cases.py:90-106`. Nhưng trong `graph_extract_task` enqueue từ `ingest_paper_task`, dùng trực tiếp `ctx["redis"]` (đã có arq pool):
  ```python
  await ctx["redis"].enqueue_job("graph_extract_task", paper_id, _job_id=f"graph_extract:{paper_id}")
  ```

- **Test pattern Neo4j handler**: xem `test_consumer.py:351-386` (`test_cypher_handler_uses_merge_not_create`):
  ```python
  queries_run = []
  async def mock_run(query, **params): queries_run.append(query)
  session = AsyncMock()
  session.run = AsyncMock(side_effect=mock_run)
  await handle_ontology_extracted(session, payload)
  assert any("MERGE" in q for q in queries_run)
  ```

- **Test pattern worker task**: xem `tests/unit/ingestion/test_worker.py` — `AsyncMock` + `_FakeSessionFactory` (lines 72+). Pattern ctx:
  ```python
  ctx = {"redis": AsyncMock(), "session_factory": session_factory, "neo4j_driver": mock_driver}
  ```

- **SyncOutboxORM**: import từ `backend.src.modules.workspace.infrastructure.orm_models`. Fields: `event_type` (str), `project_id` (str UUID), `payload` (dict). Auto-id + timestamps. Xem `worker.py:261-278` cho `_build_paper_upserted_event` làm mẫu.

- **ParentChunkORM**: import từ `backend.src.modules.ingestion.infrastructure.chunk_orm_models`. Fields: `paper_id`, `project_id`, `content` (text), `chunk_index` (int). Query:
  ```python
  result = await db.execute(
      select(ParentChunkORM)
      .where(ParentChunkORM.paper_id == paper_id)
      .order_by(ParentChunkORM.chunk_index)
  )
  chunks = result.scalars().all()
  full_text = "\n\n".join(c.content for c in chunks)
  ```

- **Admin role check**: tìm pattern trong codebase trước khi code (likely `if current_user.role != "admin": raise HTTPException(403)`). Xem admin router hiện có trong `main.py`.

### Prompt cho `graph_extractor.py`

```python
GRAPH_EXTRACTION_PROMPT = """You are an academic knowledge graph extractor. Analyze this academic paper and extract structured academic entities.

Paper metadata:
- Title: {title}
- Authors: {authors}
- Abstract: {abstract}

Full text (may be truncated):
{text}

Return ONLY a valid JSON object (no markdown, no explanation):
{{
  "findings": [
    {{"id": "f1", "description": "Specific research finding or result", "confidence_score": 0.85}}
  ],
  "limitations": [
    {{"id": "l1", "description": "Research limitation or gap explicitly mentioned"}}
  ],
  "methods": [
    {{"id": "m1", "name": "Method name", "description": "Brief description"}}
  ],
  "datasets": [
    {{"id": "d1", "name": "Dataset name", "description": "Brief description"}}
  ],
  "topics": [
    {{"id": "t1", "name": "Research topic or domain"}}
  ],
  "problems": [
    {{"id": "pr1", "description": "Core research problem being addressed"}}
  ],
  "contradicts": [
    {{"from_id": "f1", "to_id": "f2"}}
  ],
  "supports": [
    {{"from_id": "f1", "to_id": "f2"}}
  ]
}}

Rules:
- findings: 3-7 key findings with confidence 0.0-1.0 (how well-supported the finding is)
- limitations: 1-5 explicit limitations stated in the paper
- methods: named methodologies, algorithms, techniques used (0-5)
- datasets: named datasets, benchmarks (0-5)
- topics: 1-4 main research domains
- problems: 1-3 core problems addressed
- contradicts/supports: ONLY within findings extracted from THIS paper
- Use simple IDs like "f1", "f2", "l1" (no special chars, no spaces)
- Empty array [] if none found for a category
- JSON only, no markdown"""
```

### Hiện trạng code sẽ ĐỘNG TỚI (xác minh kỹ trước khi code)

- **`backend/worker.py`**:
  - `WorkerSettings.functions = [ingest_paper_task]` (line 411) → thêm `graph_extract_task`
  - `startup(ctx)` (line 143-153) → thêm `await create_ontology_constraints(neo4j_driver)` sau line 153
  - `ingest_paper_task` nhánh thành công (line ~389 hiện tại `await publish_completed`) → thêm enqueue `graph_extract_task`
  - `ingest_paper_task` nhánh metadata_only (line ~307-315) → thêm enqueue `graph_extract_task`
  - `ingest_paper_task` nhánh `except` (line ~393-407) → **KHÔNG** enqueue
  - Import thêm: `ParentChunkORM`, `GraphExtractor`, `create_ontology_constraints`

- **`backend/src/shared/infra/neo4j_client.py`**:
  - Thêm hàm `create_ontology_constraints(driver)` sau `create_base_constraints` (line 44)
  - Comment tại line 37 hiện có: "KHÔNG tạo ontology constraints (Finding/Limitation/…) — đó là việc của Story 4.3" → Story này thực hiện đúng điểm này

- **`backend/src/modules/graph_rag/infrastructure/neo4j_adapter.py`**:
  - Comment tại line 148 hiện có: "Mở rộng được: Story 4.3 chỉ cần thêm entry vào đây" → đúng chiến lược
  - Thêm `handle_ontology_extracted` + cập nhật `HANDLER_MAP`
  - `HANDLER_MAP` hiện có 4 entries: `PAPER_UPSERTED`, `PROJECT_DELETED`, `PAPER_DELETED`, `CITES`
  - **KHÔNG sửa** các handler hiện có

- **`backend/main.py`**:
  - Tìm admin router (xem đầu file để biết đường dẫn import). Backfill endpoint cần đăng ký đúng router đã mount với prefix `/api/admin`.

### Cypher patterns MERGE ontology (tham khảo cho handler)

```cypher
-- Bước 0: Cập nhật Paper.abstract (chỉ khi có)
MATCH (p:Paper {id: $paper_id})
SET p.abstract = $abstract, p.authors = $authors, p.updated_at = datetime()

-- Finding + HAS_FINDING (lặp cho từng finding)
MERGE (f:Finding {id: $finding_id})
ON CREATE SET f.description=$description, f.confidence_score=$score,
              f.project_id=$project_id, f.created_at=datetime()
ON MATCH SET f.description=$description, f.confidence_score=$score, f.updated_at=datetime()
WITH f
MATCH (p:Paper {id: $paper_id})
MERGE (p)-[:HAS_FINDING]->(f)

-- Limitation + HAS_LIMITATION (lặp cho từng limitation)
MERGE (l:Limitation {id: $limitation_id})
ON CREATE SET l.description=$description, l.project_id=$project_id, l.created_at=datetime()
ON MATCH SET l.description=$description, l.updated_at=datetime()
WITH l
MATCH (p:Paper {id: $paper_id})
MERGE (p)-[:HAS_LIMITATION]->(l)

-- Method + HAS_METHOD
MERGE (m:Method {id: $method_id})
ON CREATE SET m.name=$name, m.description=$description,
              m.project_id=$project_id, m.created_at=datetime()
ON MATCH SET m.name=$name, m.description=$description, m.updated_at=datetime()
WITH m
MATCH (p:Paper {id: $paper_id})
MERGE (p)-[:HAS_METHOD]->(m)

-- CONTRADICTS (lặp cho từng cặp)
MATCH (f1:Finding {id: $from_id}), (f2:Finding {id: $to_id})
WHERE f1.project_id=$project_id AND f2.project_id=$project_id
MERGE (f1)-[:CONTRADICTS]->(f2)

-- SUPPORTS (pattern tương tự CONTRADICTS)
```

### Design tokens / CSS — Story này Backend only, không có FE

### Learnings từ Story 4.2 (áp dụng vào 4.3)

- **`result.data()` bug**: Trong Story 4.2, `result.data()` ép Node thành dict thuần làm mất `.labels`. Với 4.3, handler neo4j_adapter KHÔNG dùng `result.data()` — chỉ chạy câu lệnh WRITE (MERGE), không cần đọc lại Node object. Safe.
- **Test mock Neo4j**: Mock `AsyncSession.run()` trả `MagicMock()` là đủ cho WRITE operations. Không cần mock `.data()`.
- **Pre-existing failures**: `tests/unit/workspace/test_projects_api.py` có 35+ lỗi SQLite isolation — không liên quan, KHÔNG debug.
- **`abstract` và `authors` chưa có trên Paper Neo4j node** (defer từ 4.2): handler của 4.3 vá điều này bằng `SET p.abstract = $abstract`.
- **JSON parse lỗi từ LLM**: `gemini-2.5-flash` đôi khi trả JSON bọc trong code fence. `gemini-2.5-pro` có thể tương tự. Dùng `_strip_code_fence` bắt buộc.

### Learnings từ Story 4.1 (tránh lặp lỗi)

- **Author.id format**: `"{project_id}:{normalized_name}"` — Story 4.3 KHÔNG thêm Author entity (4.1 đã xử lý). Chỉ SET `p.authors` (list strings) trên Paper node để FE có thể đọc.
- **`project_id` scope trong mọi Cypher**: mọi MERGE ontology phải kèm `project_id` property để IDOR safe.
- **Async session Neo4j trong handler**: handler nhận `session: AsyncSession` (từ `neo4j_driver.session()`). `await session.run(query, **params)` — không wrap thêm transaction.

### Project Structure Notes

**Files MỚI tạo:**
```
backend/src/modules/ingestion/
└── infrastructure/
    └── graph_extractor.py          # GraphExtractor class (LLM gemini-2.5-pro)

tests/unit/
├── ingestion/
│   └── test_graph_extractor.py     # Unit tests GraphExtractor (AC: 12)
│   └── test_graph_extract_task.py  # Unit tests arq task (AC: 14)
└── graph_rag/
    └── test_ontology_handler.py    # Unit tests handler + HANDLER_MAP (AC: 13)
```

**Files CẬP NHẬT:**
```
backend/worker.py                   # +graph_extract_task, +WorkerSettings, +enqueue từ ingest_paper_task
backend/src/shared/infra/neo4j_client.py          # +create_ontology_constraints()
backend/src/modules/graph_rag/infrastructure/neo4j_adapter.py  # +handle_ontology_extracted, +HANDLER_MAP
backend/src/modules/admin/presentation/router.py  # +backfill endpoint (xác nhận path)
```

**KHÔNG SỬA:** `outbox_worker.py`, `ingest_paper_task` logic ngoài điểm enqueue, `metadata_extractor.py`, `neo4j_adapter.py` handlers cũ (`handle_paper_upserted` v.v.), Alembic migrations (không có schema DB mới), `docker-compose.yml`, FE code.

### References

- [Source: architecture.md §6.2] — Two-Stage Ingestion Pipeline: Stage-2 = Graph Extraction dùng `gemini-2.5-pro`, từ Markdown cấu trúc hóa GĐ1 → trích xuất Nodes/Edges học thuật; retry độc lập từng stage
- [Source: architecture.md §5.2] — Graph Schema Phase 1: Finding{id,description,confidence_score}, Limitation, Method, Dataset, Topic, Problem; Edges HAS_FINDING, HAS_LIMITATION, CONTRADICTS, SUPPORTS, FILLS_GAP
- [Source: architecture.md §9.5] — Hexagonal Architecture: infrastructure/ = driven adapters gọi external; worker.py = composition root ingestion
- [Source: architecture.md §9.6] — Role-clarity table: ingestion là PRODUCER ontology events; graph_rag là CONSUMER MERGE ontology. Story xuyên 2 module.
- [Source: epics.md §Story 4.3] — Phạm vi: MỞ RỘNG arq worker 2.5, backfill bắt buộc, chốt model version (gemini-2.5-pro), quyết định Architect 2026-06-17
- [Source: sprint-change-proposal-2026-06-17-gap-detection.md] — Quyết định gộp story + vai trò producer/consumer ontology
- [Source: backend/worker.py:281-408] — `ingest_paper_task`: điểm enqueue `graph_extract_task` (sau `publish_completed`, cả 2 nhánh success)
- [Source: backend/worker.py:410-427] — `WorkerSettings`: thêm `graph_extract_task` vào functions
- [Source: backend/src/shared/infra/neo4j_client.py:37-52] — `create_base_constraints()` pattern để tái dùng cho `create_ontology_constraints()`
- [Source: backend/src/modules/graph_rag/infrastructure/neo4j_adapter.py:148-155] — `HANDLER_MAP` mở rộng được, comment "Story 4.3 chỉ cần thêm entry"
- [Source: backend/src/modules/ingestion/infrastructure/metadata_extractor.py:31-53] — `LLMMetadataExtractor` pattern tái dùng cho `GraphExtractor`
- [Source: backend/src/modules/ingestion/infrastructure/chunk_orm_models.py] — `ParentChunkORM` schema (paper_id, content, chunk_index)
- [Source: tests/unit/graph_rag/test_consumer.py:351-386] — Pattern test Cypher handler (mock session.run)
- [Source: 4-2-knowledge-map-ui-doc-ve-do-thi-va-node-detail-card.md — Review Findings] — Defer: abstract/authors chưa có trên Paper Neo4j node → 4.3 vá bằng SET trong handler

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed — comprehensive developer guide created (2026-06-18)
- Story 4.3 triển khai hoàn thành (2026-06-18): GraphExtractor + graph_extract_task + ontology constraints + handle_ontology_extracted + admin backfill endpoint. 19 unit tests mới, tất cả pass. Regression: 157 pass, 20 lỗi pre-existing (SQLite ARRAY trong identity tests).

### File List

**Mới tạo:**
- `backend/src/modules/ingestion/infrastructure/graph_extractor.py`
- `tests/unit/ingestion/test_graph_extractor.py`
- `tests/unit/ingestion/test_graph_extract_task.py`
- `tests/unit/graph_rag/test_ontology_handler.py`

**Cập nhật:**
- `backend/worker.py` — thêm graph_extract_task, đăng ký WorkerSettings, enqueue từ ingest_paper_task (cả 2 nhánh success), import GraphExtractor + create_ontology_constraints, gọi create_ontology_constraints trong startup
- `backend/src/shared/infra/neo4j_client.py` — thêm create_ontology_constraints() với 6 constraints IF NOT EXISTS
- `backend/src/modules/graph_rag/infrastructure/neo4j_adapter.py` — thêm handle_ontology_extracted + HANDLER_MAP["ONTOLOGY_EXTRACTED"]
- `backend/src/modules/admin/presentation/router.py` — thêm POST /admin/backfill-graph-extraction endpoint

### Change Log

- 2026-06-18: Story 4.3 — Graph Extraction / Trích xuất Ontology Học thuật. Thêm Stage-2 ingestion pipeline: GraphExtractor (gemini-2.5-pro), graph_extract_task arq, ontology Neo4j constraints (Finding/Limitation/Method/Dataset/Topic/Problem), handler ONTOLOGY_EXTRACTED với MERGE idempotent và cập nhật Paper.abstract, admin backfill endpoint.

### Review Findings

**Code review 2026-06-18** (bmad-code-review, 3 lớp: Blind Hunter + Edge Case Hunter + Acceptance Auditor). Acceptance Auditor: **0 vi phạm AC** — toàn bộ AC A1-2, B3-6, C7-8, D9-10, E11, F12-14 + Decision #7/#8 đều đạt. 7 patch độ bền/chính xác đã sửa ngay; 23 unit test (19 cũ + 4 mới) pass.

Patch (đã áp dụng):

- [x] [Review][Patch] `enqueue_job` lỗi sau commit lật paper `indexed` thành `failed` — bọc best-effort `_enqueue_graph_extract` [backend/worker.py]
- [x] [Review][Patch] Handler KeyError khi payload thiếu `id`/`from_id`/`to_id` (đầu độc outbox→DLQ) — guard `.get()` + skip cho 6 loop node + 2 loop edge [backend/src/modules/graph_rag/infrastructure/neo4j_adapter.py]
- [x] [Review][Patch] Parse JSON thất bại khi LLM kèm prose quanh JSON (mất trắng ontology) — thêm fallback cắt object `{...}` trong `_parse_json` [backend/src/modules/ingestion/infrastructure/graph_extractor.py]
- [x] [Review][Patch] `confidence_score` không ép kiểu → Neo4j lưu kiểu không nhất quán — `_clamp_score` ép float [0,1] [backend/worker.py]
- [x] [Review][Patch] Paper rỗng (no chunk + no abstract) vẫn gọi LLM gemini-2.5-pro tốn phí — short-circuit return [backend/worker.py]
- [x] [Review][Patch] Cạnh CONTRADICTS/SUPPORTS tự trỏ chính nó (self-loop) — guard `new_from == new_to` trong `_remap_edge` [backend/worker.py]
- [x] [Review][Patch] Backfill load full `PaperORM` row khi chỉ cần id — `select(PaperORM.id)` [backend/src/modules/admin/presentation/router.py]

Defer (rủi ro thấp, không chặn):

- [x] [Review][Defer] Handler `handle_ontology_extracted` không bọc 1 transaction atomic — deferred. MERGE idempotent + guard `id` (P2) khiến retry tự lành; nhất quán với các handler hiện hữu.
- [x] [Review][Defer] Backfill chưa phân trang khi corpus rất lớn — deferred. Đã giảm tải bằng select-id-only; có giới hạn số tài liệu (Story 2.6).

Dismiss (by-design / false positive):

- Orphan ontology node do `MATCH (p:Paper)` khi Paper chưa tồn tại — by design: outbox xử lý theo `id.asc()` nên `PAPER_UPSERTED` (id thấp hơn) luôn sync trước `ONTOLOGY_EXTRACTED`; backfill MERGE tự lành. Cypher theo đúng spec.
- `authors`/`abstract` bị ghi đè rỗng — producer luôn gửi `paper.authors`/`paper.abstract` thật.
