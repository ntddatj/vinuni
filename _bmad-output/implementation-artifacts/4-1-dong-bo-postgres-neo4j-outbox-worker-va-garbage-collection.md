---
baseline_commit: 493d257bbe485bf7cc9ce90c5faf5595633d347b
---

# Story 4.1: Đồng bộ Postgres → Neo4j Event-Driven qua Outbox Worker (+ Garbage Collection)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **kỹ sư nền tảng dữ liệu (backend) của C2-App-053**,
I want **một worker nền đọc bảng `sync_outbox` của Postgres và dịch các sự kiện thành câu lệnh Cypher MERGE idempotent đẩy sang Neo4j (kèm khóa hàng `FOR UPDATE SKIP LOCKED`, khóa phân tán Redis theo `project_id` có heartbeat, retry/DLQ), đồng thời một producer ghi sự kiện `PAPER_UPSERTED` khi ingest xong và một cronjob 2h sáng xóa cứng dữ liệu đã xóa mềm quá 7 ngày ở cả Postgres lẫn Neo4j**,
so that **đồ thị tri thức Neo4j luôn nhất quán cuối (eventual consistency) với Postgres để Story 4.2 (Knowledge Map UI) có dữ liệu thật để vẽ, và hệ thống tự dọn rác theo ARCH-2 mà không phình dữ liệu**.

## Bối cảnh & Phạm vi (đọc trước khi code)

Đây là **story đầu tiên của Epic 4** và là **nền móng 🟢 cốt lõi** cho toàn bộ Bản đồ Tri thức / Gap Detection. **Hiện chưa có bất kỳ hạ tầng Neo4j nào** trong codebase (đã xác minh: không có service trong `docker-compose.yml`, không có package `neo4j` trong `requirements.txt`, không có module `graph_rag/`, không có producer `PAPER_UPSERTED`). Story này dựng toàn bộ đường ống ghi (write path) Postgres→Neo4j từ con số 0, cộng phần Garbage Collection "ride-along".

**Ranh giới (rất quan trọng — chống scope creep):**
- ✅ TRONG phạm vi: Neo4j driver + cấu hình; migration `009` mở rộng `sync_outbox` + thêm `deleted_at`; **producer** sự kiện `PAPER_UPSERTED` khi ingest xong; **consumer** worker dịch event → Cypher MERGE (`Paper`, `Author`, `[:AUTHORED_BY]`); xử lý event xóa (`:Deleted` label); retry/DLQ; lock + heartbeat; GC cron 2h sáng (Postgres + Neo4j).
- ❌ NGOÀI phạm vi (story sau): endpoint đọc đồ thị `GET /api/projects/{id}/graph` và mọi thứ Frontend → **Story 4.2**. Trích xuất ontology học thuật (`Finding`/`Limitation`/`[:CONTRADICTS]`/`[:SUPPORTS]`) → **Story 4.3** (4.3 sẽ ghi event vào `sync_outbox`; story 4.1 chỉ cần **kiến trúc handler mở rộng được** để 4.3 thêm loại event mới mà không phá vỡ). `gap_detection`/Leiden → **Story 4.4** (Leiden đã hoãn Phase 2).
- ❌ NGOÀI phạm vi: cạnh `[:CITES]` **không có nguồn dữ liệu** ở MVP (bảng `papers` không lưu danh sách tham chiếu/references). Vẫn hiện thực **handler Cypher cho `[:CITES]` sẵn sàng + idempotent** nhưng **không có producer** — ghi rõ ở Dev Notes, không cố trích references trong story này.

### 🧭 Nhãn module/role theo task (role-clarity 2026-06-17 — `sprint-change-proposal-2026-06-17-role-matrix.md`)

Story này là **vertical slice xuyên 4 module**. Mỗi task đặt code đúng module của nó để KHÔNG vi phạm §9.6 (không module nào gọi thẳng infra module khác):

| Task | Module (nơi code sống) | Vai trò |
|---|---|---|
| Neo4j driver dùng chung (`neo4j_client.py`) | `[shared]` (Shared Kernel `shared/infra/`) | INFRA |
| Producer `PAPER_UPSERTED` trong `ingest_paper_task` (`worker.py`) | `[ingestion]` | **PRODUCER — retrofit vá nợ Story 2.5** |
| Migration `sync_outbox` + `projects.deleted_at` + soft-delete project | `[workspace]` (chủ ORM `sync_outbox`/`projects`) | SCHEMA |
| Migration `papers.deleted_at` + soft-delete paper | `[ingestion]` (chủ ORM `papers`) | SCHEMA |
| Module mới `modules/graph_rag/` (adapter Cypher + outbox worker + GC) | `[graph_rag]` | **CONSUMER + GC** |

**Lưu ý chống chồng lấn ontology (4.1 ↔ 4.3):** Story 4.1 chỉ tạo **Unique Constraints base** (`Paper.id`, `Author.id`, `Project.id`) và **handler base** (`PAPER_UPSERTED`/`PROJECT_DELETED`/`PAPER_DELETED` + `[:CITES]` sẵn sàng). **Constraints ontology (Finding/Limitation/…) + handler MERGE ontology là của Story 4.3** — 4.1 **KHÔNG** tạo, chỉ dựng **dispatch map mở-rộng-được** để 4.3 đăng ký handler mới mà không sửa worker core (xem AC#12 bullet "Dispatch mở rộng được").

## Acceptance Criteria

### A. Hạ tầng Neo4j (mới hoàn toàn)
1. Thêm service **`neo4j`** vào `docker-compose.yml` (image `neo4j:5-community`), expose `7474` (browser, dev) + `7687` (bolt, internal), volume bền cho data, biến môi trường auth từ `.env`, và **giới hạn RAM theo ARCH-1**: `NEO4J_server_memory_heap_max__size=5G`, `NEO4J_server_memory_pagecache_size=3G` (tổng ≤ 8GB), `mem_limit: 8g`. Healthcheck cho phép backend/worker chờ Neo4j sẵn sàng.
2. Thêm dependency `neo4j>=5.0` (async driver) vào `backend/requirements.txt`. Thêm 3 settings vào `backend/src/shared/infra/settings.py` (hiện CHƯA có `neo4j_*`): `neo4j_uri` (default `bolt://localhost:7687`), `neo4j_username` (default `neo4j`), `neo4j_password` (đọc từ env `NEO4J_URI`/`NEO4J_USERNAME`/`NEO4J_PASSWORD`).
3. Tạo Neo4j driver dùng chung tại `backend/src/shared/infra/neo4j_client.py`: `AsyncGraphDatabase.driver(...)` singleton (mirror pattern `redis_client.py` — `get_redis()` ở [redis_client.py:16-21](backend/src/shared/infra/redis_client.py#L16)), hàm `get_neo4j_driver()` + `close_neo4j_driver()`. Worker `on_startup` khởi tạo driver & **tạo Unique Constraints** (idempotent `CREATE CONSTRAINT IF NOT EXISTS`); `on_shutdown` đóng driver.
4. Tạo các **Unique Constraints base** đảm bảo MERGE idempotent: `Paper.id` UNIQUE, `Author.id` UNIQUE (id = khóa chuẩn hóa tên, xem AC#10), `Project.id` UNIQUE. Mọi node mang property `project_id` để scope đa dự án (chống IDOR ở story đọc 4.2/4.4). **KHÔNG tạo constraints ontology (Finding/Limitation/…) — đó là việc của Story 4.3.**

### B. Mở rộng `sync_outbox` (migration `009`) + Producer sự kiện
5. Tạo Alembic migration `009_extend_sync_outbox_and_soft_delete.py` (down_revision = `"008"` — đã xác minh migration cao nhất hiện tại là `008_create_chat_tables.py`) mở rộng bảng `sync_outbox` thêm: `project_id` (Uuid, nullable, index — phục vụ gom nhóm/khóa theo dự án; **backfill** từ `payload->>'project_id'` cho hàng cũ), `retry_count` (Integer, default 0), `last_error` (Text, nullable), `processed_at` (DateTime tz, nullable), `dead_lettered` (Boolean, default false, index một phần `WHERE dead_lettered = true`). **Giữ nguyên** cột `processed` và index `idx_sync_outbox_unprocessed` hiện có (tạo ở migration `002`). Cập nhật `SyncOutboxORM` ([orm_models.py:36-45](backend/src/modules/workspace/infrastructure/orm_models.py#L36)) khớp.
6. Cùng migration: thêm cột `deleted_at` (DateTime tz, nullable) vào bảng **`projects`** và **`papers`** (mốc thời gian xóa mềm chính xác để GC tính ngưỡng 7 ngày — KHÔNG dùng `updated_at` vì bị reset bởi mọi update). **Đã xác minh:** cả `ProjectORM` (có `is_deleted` tại [orm_models.py:27](backend/src/modules/workspace/infrastructure/orm_models.py#L27)) và `PaperORM` (có `is_deleted` tại [orm_models.py:42](backend/src/modules/ingestion/infrastructure/orm_models.py#L42)) **chỉ có `is_deleted`, chưa có `deleted_at`**. Cập nhật 2 ORM tương ứng.
7. **Cập nhật 2 điểm soft-delete hiện có** để set `deleted_at = now(utc)` (giữ nguyên việc ghi event outbox):
   - `PostgresProjectRepository.soft_delete` ([postgres_repository.py:84-100](backend/src/modules/workspace/infrastructure/postgres_repository.py#L84)) — event `PROJECT_DELETED` đã ghi tại dòng ~96, payload `{"project_id": ..., "user_id": ...}`; thêm set `deleted_at` (đảm bảo `payload` đã có `project_id` — đã có).
   - `delete_paper_soft` ([ingestion/.../postgres_repository.py:169-197](backend/src/modules/ingestion/infrastructure/postgres_repository.py#L169)) — event `PAPER_DELETED` đã ghi tại dòng ~192, payload `{"paper_id": ..., "project_id": ...}`; thêm set `deleted_at`.
8. **Producer `PAPER_UPSERTED`** (vai **`[ingestion]`** — retrofit vá nợ Story 2.5; code đặt trong `worker.py` của module ingestion, KHÔNG phải logic của graph_rag): trong `ingest_paper_task` ([worker.py:248-362](backend/worker.py#L248)), ngay trước `await db.commit()` của nhánh thành công ([worker.py:340-341](backend/worker.py#L340), sau `paper.status = "indexed"`), ghi **transactionally** một `SyncOutboxORM(event_type="PAPER_UPSERTED", project_id=paper.project_id, payload={...})` với payload đủ để MERGE Paper + Authors: `{paper_id, project_id, title, authors: [...], year, doi, arxiv_id, source, url, file_path}`. Cùng một transaction với việc lưu chunks để đảm bảo Outbox Pattern (atomic). **Lưu ý regression:** nhánh "paper đã bị xóa trong lúc ingest" ([worker.py:308-312](backend/worker.py#L308), `if paper.is_deleted:` → publish completed + `return` sớm) phải **KHÔNG** ghi `PAPER_UPSERTED` — producer phải đặt SAU guard này, trong nhánh thành công. Nhánh `except` (status="failed") cũng KHÔNG ghi event.

### C. Consumer Worker (sync outbox → Neo4j)
9. Tạo module mới `backend/src/modules/graph_rag/` theo cấu trúc Hexagonal (ARCH §9.5): `infrastructure/neo4j_adapter.py` (thực thi Cypher), `infrastructure/outbox_worker.py` (vòng lặp quét + lock + dịch event), `application/use_cases.py` (`SyncOutboxUseCase`), `domain/` (entities tối thiểu nếu cần). Đăng ký entrypoint vào `WorkerSettings` của [worker.py:364-375](backend/worker.py#L364).
10. **Vòng quét batch idempotent:** mỗi lần chạy, claim một lô event chưa xử lý bằng `SELECT ... FOR UPDATE SKIP LOCKED` (filter `processed = false AND dead_lettered = false`, `ORDER BY id ASC`, `LIMIT batch_size` mặc định 100). Xử lý theo **thứ tự `id` tăng dần** trong mỗi `project_id`.
11. **Khóa phân tán theo `project_id`** (đảm bảo thứ tự đồng bộ, ARCH §5.3): trước khi xử lý các event của một dự án, lấy Redis lock `graph_sync_lock:{project_id}` (lease ~120s) bằng `SET NX EX`. Nếu không lấy được lock (worker khác đang xử lý dự án đó) → bỏ qua batch dự án đó lần này (không block). **Lock Heartbeat:** một asyncio task nền gia hạn lease mỗi 60s khi batch Neo4j còn chạy. Giải phóng lock bằng **Lua compare-and-delete** (tái dùng `_RELEASE_LOCK_LUA` ở [ingestion/.../use_cases.py:33-36](backend/src/modules/ingestion/application/use_cases.py#L33), pattern acquire/release `_paper_limit_lock` tại [use_cases.py:39-68](backend/src/modules/ingestion/application/use_cases.py#L39)) để tránh xóa nhầm lock của worker khác.
12. **Dịch event → Cypher MERGE** qua `neo4j_adapter`, mỗi loại 1 handler, **idempotent** (MERGE + ON CREATE/ON MATCH SET), scope `project_id`:
    - `PAPER_UPSERTED` → `MERGE (p:Paper {id})` set title/year/doi/arxiv_id/source/url/project_id; với mỗi author: `MERGE (a:Author {id})` (id = tên chuẩn hóa, AC#10) `MERGE (p)-[:AUTHORED_BY]->(a)`. Gắn property `state` cho Paper: `"full_text"` nếu `payload.file_path` có, ngược lại `"metadata_only"` (phục vụ phân biệt node ở Story 4.2 — node toàn văn vs chỉ metadata).
    - `PROJECT_DELETED` → đánh nhãn `:Deleted` (kèm `deleted_at`) cho `Project` và mọi `Paper` thuộc `project_id`. RAG/đọc đồ thị về sau dùng `WHERE NOT p:Deleted`.
    - `PAPER_DELETED` → đánh nhãn `:Deleted` + `deleted_at` cho `Paper {id}` tương ứng.
    - **Dispatch mở rộng được:** map `event_type → handler`; loại event lạ (vd ontology của Story 4.3 chưa hỗ trợ) → **không crash**, log WARN và **để lại event** (không mark processed) + **tăng `retry_count` nhẹ** để cuối cùng vào DLQ nếu mãi không có handler — tránh nghẽn nhưng không mất dữ liệu. (Mục tiêu: 4.3 chỉ cần thêm handler vào map, không sửa worker core.)
    - Handler `[:CITES]` (`(:Paper)-[:CITES]->(:Paper)`) viết sẵn idempotent nhưng **không có producer** ở story này (bảng `papers` không có cột references — đã xác minh; ghi chú scope).
13. **Đánh dấu hoàn tất & xử lý lỗi/DLQ:** event xử lý thành công → `processed = true, processed_at = now()`. Event lỗi → Cypher MERGE idempotent nên retry an toàn, `retry_count += 1`, `last_error = str(e)`; khi `retry_count >= MAX_SYNC_RETRIES` (default 3) → `dead_lettered = true` (đẩy DLQ, không chặn các event sau của dự án). Một event lỗi **không được** làm hỏng cả batch — bọc try/except từng event.

### D. Garbage Collection (ride-along, ARCH-2 — làm sau cùng, không chặn demo)
14. Cronjob **2h sáng** (arq cron, `hour=2, minute=0`) `garbage_collection_task`:
    - **Postgres:** hard-delete `papers` và `projects` có `is_deleted = true AND deleted_at < now() - interval '7 days'`. Xóa paper kéo theo `parent_chunks`/`child_chunks` (cascade FK đã có) + `uploaded_files`; xóa project kéo theo papers thuộc nó. Xóa file vật lý `paper.file_path` nếu tồn tại (PDF cache của Story 2.7). Ngưỡng 7 ngày qua setting `GC_RETENTION_DAYS` (default 7).
    - **Neo4j:** `MATCH (n:Deleted) WHERE n.deleted_at < $threshold DETACH DELETE n` (xóa cứng node đã đánh nhãn quá 7 ngày).
    - Dọn `sync_outbox`: xóa các hàng `processed = true AND processed_at < now() - interval '30 days'` (tránh phình bảng outbox; ngưỡng riêng, không phải 7 ngày).
15. GC phải **an toàn idempotent** và log số lượng đã xóa từng loại. Lỗi một phần (vd Neo4j down) không được làm Postgres rollback đã commit — xử lý 2 store độc lập, log lỗi rõ ràng.

### E. Đăng ký & vận hành
16. `WorkerSettings` ([worker.py:364-375](backend/worker.py#L364) — **đã xác minh hiện CHƯA có `cron_jobs`**, chỉ có `functions=[ingest_paper_task]`, `on_startup`, `on_shutdown`, `max_jobs`, `job_timeout`, `keep_result`, `redis_settings`) bổ sung `cron_jobs = [...]`: (a) job quét sync_outbox chạy thường xuyên (đề xuất mỗi 5s qua `cron(..., second=set(range(0,60,5)))`) và (b) `garbage_collection_task` lúc 2h sáng. Driver Neo4j khởi tạo ở `on_startup` (mở rộng `startup` hiện có — `ctx["session_factory"]` set tại [worker.py:140](backend/worker.py#L140)), đóng ở `on_shutdown` (KHÔNG phá ingestion). `ctx["redis"]` do arq cung cấp (KHÔNG set trong startup).
17. Cập nhật `.env.example` thêm `NEO4J_URI`/`NEO4J_USERNAME`/`NEO4J_PASSWORD` và settings GC/sync mới (`MAX_SYNC_RETRIES`, `GC_RETENTION_DAYS`, `SYNC_OUTBOX_BATCH_SIZE`) với default hợp lý.

### F. Test (bắt buộc — pattern dự án: pytest + pytest-asyncio, mock hạ tầng)
18. Unit test (mock Neo4j async session + Redis `AsyncMock`, fake DB session theo `_FakeSessionFactory` ở [test_worker.py:72-81](tests/unit/ingestion/test_worker.py#L72) — pattern dùng `AsyncMock()` cho cả redis & db):
    - Producer: ingest thành công ghi đúng 1 event `PAPER_UPSERTED` với payload đầy đủ; nhánh paper-đã-xóa KHÔNG ghi event.
    - Consumer: claim batch chỉ lấy `processed=false AND dead_lettered=false`; mark `processed=true` khi thành công; `retry_count` tăng + `last_error` set khi handler raise; vào DLQ sau 3 lần; một event lỗi không làm hỏng các event khác trong batch.
    - Cypher idempotency: gọi handler `PAPER_UPSERTED` 2 lần với cùng payload → adapter phát Cypher dùng MERGE (assert query chứa `MERGE`), không tạo trùng.
    - Lock: không lấy được Redis lock → bỏ qua dự án đó, không xử lý; release dùng compare-and-delete đúng token.
    - Dispatch: event_type lạ → không crash, không mark processed, tăng retry_count.
    - GC: chỉ xóa bản ghi `is_deleted AND deleted_at < now-7d`; bản ghi xóa mềm < 7 ngày KHÔNG bị xóa; Cypher GC dùng `DETACH DELETE` với threshold đúng.
19. Tất cả test mới đặt dưới `tests/unit/graph_rag/` (tạo mới, có `__init__.py`). Không gọi Neo4j/Redis/Postgres thật (mock toàn bộ — dự án không dùng testcontainers).

## Tasks / Subtasks

- [x] **Task 1 — Hạ tầng Neo4j `[shared]`** (AC: 1,2,3,4)
  - [x] Thêm service `neo4j:5-community` vào `docker-compose.yml` với RAM limits ARCH-1 + healthcheck + volume
  - [x] `backend/requirements.txt`: thêm `neo4j>=5.0`
  - [x] `shared/infra/settings.py`: thêm `neo4j_uri/username/password`
  - [x] `shared/infra/neo4j_client.py`: singleton async driver + get/close (mirror `redis_client.py`)
  - [x] Tạo Unique Constraints **base** (Paper.id, Author.id, Project.id) idempotent khi worker startup — KHÔNG tạo ontology constraints
- [x] **Task 2 — Migration 009 + `deleted_at` `[workspace]`+`[ingestion]`** (AC: 5,6,7)
  - [x] Alembic `009_extend_sync_outbox_and_soft_delete.py` (down_revision="008"): thêm cột outbox (project_id, retry_count, last_error, processed_at, dead_lettered) + backfill project_id; thêm `deleted_at` vào projects/papers; giữ index cũ
  - [x] Cập nhật `SyncOutboxORM`, `ProjectORM`, `PaperORM`
  - [x] Sửa `soft_delete` (project, L84-100) + `delete_paper_soft` (paper, L169-197): set `deleted_at`
- [x] **Task 3 — Producer PAPER_UPSERTED `[ingestion]` (retrofit 2.5)** (AC: 8)
  - [x] Ghi event transactionally ở nhánh ingest thành công (`worker.py` L340-341), không ghi ở nhánh paper-đã-xóa (L308-312) hay nhánh failed
  - [x] Test producer
- [x] **Task 4 — Module graph_rag + Consumer worker `[graph_rag]`** (AC: 9,10,11,12,13)
  - [x] Scaffold `modules/graph_rag/` (Hexagonal)
  - [x] `neo4j_adapter.py`: Cypher handlers MERGE (PAPER_UPSERTED, PROJECT_DELETED, PAPER_DELETED, CITES sẵn sàng)
  - [x] `outbox_worker.py`: claim batch SKIP LOCKED + group theo project_id + Redis lock + heartbeat + dispatch map mở-rộng-được + mark/retry/DLQ
  - [x] Test consumer (claim, mark, retry, DLQ, lock, idempotency, dispatch event lạ)
- [x] **Task 5 — Garbage Collection cron `[graph_rag]`** (AC: 14,15)
  - [x] `garbage_collection_task`: Postgres hard-delete >7d + xóa file + Neo4j DETACH DELETE + dọn outbox cũ >30d
  - [x] Test GC ngưỡng
- [x] **Task 6 — Đăng ký WorkerSettings + env** (AC: 16,17)
  - [x] `cron_jobs` (sync mỗi 5s + GC 2h sáng); startup/shutdown driver Neo4j (mở rộng `startup` L136-141)
  - [x] `.env.example` + settings GC/sync mới
- [x] **Task 7 — Chạy migration + lint/test toàn bộ** (AC: 18,19)
  - [x] `alembic upgrade head` chạy sạch; `pytest tests/unit/graph_rag` xanh; không phá test ingestion hiện có

### Review Findings (code review 2026-06-18 — bmad-code-review, 3 lớp: Blind Hunter + Edge Case Hunter + Acceptance Auditor)

**Patch đã áp dụng (8) — tất cả đã sửa trong lần review này:**

- [x] [Review][Patch] Sai key env page cache Neo4j `pagecache__size`→`pagecache_size` → 3G page cache bị Neo4j bỏ qua, vi phạm ngân sách RAM ARCH-1 (AC#1) [docker-compose.yml:34]
- [x] [Review][Patch] Heartbeat so sánh `bytes == str` luôn False (arq redis pool không decode_responses) → lease KHÔNG bao giờ được gia hạn, lock hết hạn giữa batch dài (AC#11) [outbox_worker.py:60-67]
- [x] [Review][Patch] Group `project_id=None` xử lý KHÔNG lock → 2 cron tick chồng lấn xử lý trùng song song (claim SKIP LOCKED đã nhả row-lock trước khi xử lý). Thêm sentinel lock cho mọi group (AC#10/11) [outbox_worker.py:89-121]
- [x] [Review][Patch] GC Neo4j so sánh `DateTime < $threshold(chuỗi ISO)` → Cypher trả null → KHÔNG xóa node `:Deleted` nào, đồ thị phình vĩnh viễn. Sửa thành `< datetime($threshold)` (AC#14) [garbage_collection.py:108-121]
- [x] [Review][Patch] GC rò rỉ file vật lý: paper bị xóa theo cascade khi xóa project (FK ondelete=CASCADE) bị xóa DB row nhưng file PDF còn lại trên đĩa. Mở rộng query unlink cả paper thuộc project hết hạn (AC#14) [garbage_collection.py:52-78]
- [x] [Review][Patch] Producer bỏ sót nhánh no-text: paper chỉ có metadata (không trích được nội dung) bị đánh `indexed` nhưng KHÔNG ghi PAPER_UPSERTED → không bao giờ lên Neo4j (mâu thuẫn `state="metadata_only"`). Thêm producer + race-guard vào nhánh no-text (AC#8/12) [worker.py:283-296]
- [x] [Review][Patch] Author chuẩn hóa ra rỗng vẫn tạo node `Author {id="{project_id}:"}` gom nhầm mọi paper vào 1 tác giả ảo. Thêm guard `if not norm: continue` (AC#10/12) [neo4j_adapter.py:72-78]
- [x] [Review][Patch] Migration 009 không backfill `deleted_at` cho hàng đã xóa mềm TRƯỚC migration (is_deleted=true, deleted_at NULL) → GC dùng `deleted_at < threshold` (NULL→false) KHÔNG bao giờ dọn được chúng. Thêm 2 câu UPDATE backfill (AC#6/14) [009_...py:58-64]

**Defer (2):**

- [x] [Review][Defer] Unknown event_type bị DLQ sau ~15s (MAX_SYNC_RETRIES=3 × cron 5s) — ĐÚNG theo AC#12 nhưng có rủi ro: event forward-compat của Story 4.3 (sinh trước khi handler deploy) bị DLQ rồi mất (chưa có cơ chế replay DLQ). Là quyết định thiết kế của spec → để team cân nhắc nâng MAX_SYNC_RETRIES/giãn cadence cho event lạ, hoặc thêm DLQ-replay khi làm Story 4.3. KHÔNG sửa ngược spec ở review này.
- [x] [Review][Defer] Pre-existing: 35 errors + 1 failed ở `tests/unit/workspace/test_projects_api.py` do test-isolation SQLite (state rò rỉ giữa test). Đã xác minh tái hiện y hệt trên baseline (stash code) — không liên quan story 4.1. Pass khi chạy đơn lẻ.

**Dismissed (4 — nhiễu/false-positive):** `last_error[:2000]` cắt thừa (cột Text vô hạn, vô hại); 2 lần `datetime.now()` trong GC (lệch micro-giây); `.env.example NEO4J_PASSWORD=change-me` (placeholder cố ý); author over-merge first-write-wins tên khác cách viết (đúng thiết kế MVP entity resolution theo spec).

## Dev Notes

### Kiến trúc & nguồn dữ liệu (bắt buộc tuân thủ)
- **Outbox Pattern / Eventual Consistency** — ARCH §5.3: event ghi *transactionally* cùng thay đổi nghiệp vụ; worker quét batch với `FOR UPDATE SKIP LOCKED`; thứ tự đảm bảo qua Redis lock theo `project_id` + Lock Heartbeat; lỗi quá 3 lần → DLQ. [Source: architecture.md#5.3]
- **Nguyên tắc 3 trục (role-clarity)** — Module = nơi code sống; Epic = chủ đề giá trị; Story = lát cắt xuyên-module. Producer `sync_outbox` = `ingestion`; Consumer = `graph_rag`/`simple_rag` (§9.6). Story này xuyên 4 module — xem bảng "Nhãn module/role theo task" ở phần Bối cảnh. [Source: architecture.md#9.6, sprint-change-proposal-2026-06-17-role-matrix.md]
- **Graph Schema Phase 1** — Nodes `Paper`, `Author` (+ `Topic/Method/Dataset/Limitation/Problem/Finding/Community` để Story 4.3+ dùng — **KHÔNG tạo ở 4.1**); Edges `[:AUTHORED_BY]`, `[:CITES]`. MERGE + Unique Constraints → Idempotent Upsert. [Source: architecture.md#5.2]
- **GC (ARCH-2)** — xóa mềm ghi outbox để Neo4j gắn `:Deleted`; RAG query luôn `WHERE NOT p:Deleted`; cron 2h sáng xóa cứng >7 ngày ở **cả** Postgres và Neo4j. [Source: architecture.md#1.3, epics.md ARCH-2]
- **RAM Neo4j ≤ 8GB** (5GB heap + 3GB page cache) — ARCH-1, bắt buộc cấu hình trong docker-compose để tránh OOM trên VM 32GB. [Source: architecture.md#1.3]
- **Hexagonal** — code vào `src/modules/graph_rag/{domain,application,infrastructure}`; module KHÔNG gọi trực tiếp DB/infra của module khác; chỉ đọc `sync_outbox` (bảng dùng chung, do `workspace` module sở hữu ORM). [Source: architecture.md#9.5, §9.6]
- **Naming** — tables số nhiều snake_case; Python snake_case hàm/biến, PascalCase class/Pydantic. Không sửa schema có dữ liệu mà thiếu Alembic migration. [Source: architecture.md#9.1, §9.3]

### Hiện trạng code sẽ ĐỘNG TỚI (đã xác minh trực tiếp — tránh regression)
> Tất cả số dòng dưới đây đã được xác minh bằng cách đọc code hiện tại (2026-06-17), không phải ước lượng.

- **`sync_outbox` hiện tại** ([orm_models.py:36-45](backend/src/modules/workspace/infrastructure/orm_models.py#L36)) chỉ có `id(Integer PK autoincrement), event_type(String100), payload(JSON), processed(Boolean default False), created_at(DateTime tz)`. **Chưa có `project_id`/retry/DLQ/`processed_at`.** Index một phần `idx_sync_outbox_unprocessed (WHERE processed=false)` tạo ở migration `002`. → migration AC#5 bổ sung, **giữ nguyên** cột & index cũ.
- **Chỉ tồn tại 2 producer event** (đã grep toàn repo — **0 match `PAPER_UPSERTED`**): `PROJECT_DELETED` ([postgres_repository.py:96](backend/src/modules/workspace/infrastructure/postgres_repository.py#L96), payload `{project_id, user_id}`) và `PAPER_DELETED` ([ingestion/.../postgres_repository.py:192](backend/src/modules/ingestion/infrastructure/postgres_repository.py#L192), payload `{paper_id, project_id}`). **Không có producer cho Paper upsert** → Neo4j sẽ rỗng vĩnh viễn nếu thiếu AC#8. Đây là lý do AC#8 bắt buộc; thiếu thì milestone demo sau Story 4.2 sập.
- **`ingest_paper_task`** ([worker.py:248-362](backend/worker.py#L248)): nhánh thành công kết ở `paper.status="indexed"` (L340) → `await db.commit()` (L341) → `await publish_completed(...)` (L343). **Race guard** quan trọng: `await db.refresh(paper)` (L308) rồi `if paper.is_deleted:` (L309) → publish completed + `return` sớm (L310-312) — producer AC#8 phải đặt SAU guard này, trước commit thành công. Nhánh `except` set `status="failed"` — KHÔNG ghi event.
- **`WorkerSettings`** ([worker.py:364-375](backend/worker.py#L364)): hiện `functions=[ingest_paper_task]` (L365), `on_startup=startup` (L366), `on_shutdown=shutdown` (L367). **CHƯA có `cron_jobs`** — AC#16 thêm mới.
- **Worker startup** ([worker.py:136-141](backend/worker.py#L136)): `ctx["session_factory"] = async_sessionmaker(engine, expire_on_commit=False)` (L140). `ctx["redis"]` do arq cung cấp (không set ở startup). Consumer dùng `async with ctx["session_factory"]() as db:`.
- **Pattern khóa phân tán Redis** đã có ([ingestion/.../use_cases.py:33-68](backend/src/modules/ingestion/application/use_cases.py#L33)): `_RELEASE_LOCK_LUA` compare-and-delete (L33-36) + `_paper_limit_lock` context manager (L39-68) — key `paper_limit_lock:{project_id}`, token `uuid4`, `redis.set(key, token, nx=True, ex=10)`, release `redis.eval(_RELEASE_LOCK_LUA, 1, key, token)`. **Tái dùng nguyên pattern** cho `graph_sync_lock`, đừng phát minh lại (chỉ đổi key + lease 120s + thêm heartbeat).
- **Redis client**: `get_redis()` singleton ([redis_client.py:16-21](backend/src/shared/infra/redis_client.py#L16)) từ `settings.arq_redis_url`. Worker dùng `ctx["redis"]`. Đảm bảo cùng instance.
- **`papers.authors`** là `ARRAY(Text)` ([orm_models.py:32](backend/src/modules/ingestion/infrastructure/orm_models.py#L32)) — đủ để tạo Author nodes. `papers.file_path` ([orm_models.py:40](backend/src/modules/ingestion/infrastructure/orm_models.py#L40)) dùng cho property `state`. **Không có cột references/citations** → đó là lý do CITES không có producer ở MVP.
- **`PaperORM`/`ProjectORM` có `is_deleted` nhưng CHƯA có `deleted_at`** ([ingestion orm_models.py:42](backend/src/modules/ingestion/infrastructure/orm_models.py#L42), [workspace orm_models.py:27](backend/src/modules/workspace/infrastructure/orm_models.py#L27)) → AC#6 thêm `deleted_at`.
- **Cột khóa chính** dùng tên `id` (cả `papers.id`, `projects.id`), KHÔNG phải `project_id`/`paper_id` ở chính bảng đó — chú ý khi viết query (FK trỏ về thì là `project_id`).
- **Migration cao nhất hiện tại = `008`** (`008_create_chat_tables.py`, revision `"008"`) → migration mới **phải là `009`** với `down_revision="008"`.

### Quyết định kỹ thuật chốt cho story này
- **Author node id (entity resolution MVP):** dùng **tên chuẩn hóa** (`lower(trim(collapse_whitespace(name)))`) làm `Author.id`, scope theo `project_id` (key = `f"{project_id}:{normalized_name}"` để không gộp tác giả trùng tên giữa 2 dự án khác nhau). **Heuristic Jaccard/cosine/ORCID đầy đủ (ARCH §5.2) HOÃN sang Story 4.3** (nơi có ontology + abstract vector) — ghi rõ là MVP resolution. Đừng làm Jaccard ở đây.
- **Cơ chế consumer:** **arq cron mỗi 5s** drain batch (đơn giản, nằm trong hạ tầng arq sẵn có) thay vì dựng process loop riêng. Mỗi lần chạy claim ≤ `SYNC_OUTBOX_BATCH_SIZE` event. Chấp nhận độ trễ đồng bộ ≤ 5s (đủ cho eventual consistency; Story 4.2 sẽ có sync-indicator báo "đang cập nhật").
- **Event lạ (forward-compat cho 4.3):** không hỗ trợ → log WARN + để lại event (không mark processed), tăng `retry_count` để cuối cùng vào DLQ nếu mãi không có handler — tránh nghẽn nhưng không mất dữ liệu. 4.3 chỉ cần đăng ký thêm handler vào dispatch map + tạo constraints ontology của riêng nó.
- **GC độc lập 2 store:** commit Postgres trước, rồi Neo4j; lỗi Neo4j không rollback Postgres (2 nguồn sự thật khác nhau, lần GC sau dọn nốt).

### Project Structure Notes
- Module mới: `backend/src/modules/graph_rag/` (lần đầu xuất hiện — theo khung Hexagonal architecture.md §9.5: `domain/`, `application/use_cases.py`, `infrastructure/neo4j_adapter.py` + `infrastructure/outbox_worker.py`). Chưa cần `presentation/router.py` (đọc đồ thị là Story 4.2).
- Driver dùng chung đặt ở Shared Kernel: `backend/src/shared/infra/neo4j_client.py` (cùng cấp với `redis_client.py`, `database.py`, `settings.py`) — vì cả graph_rag (worker) và sau này graph endpoints (4.2) đều dùng.
- Test: `tests/unit/graph_rag/` (tạo mới, có `__init__.py`).
- **Không** sửa frontend, không thêm endpoint API trong story này.
- **Tuân thủ §9.6:** code producer đặt trong module `ingestion` (`worker.py`); code consumer/GC trong module `graph_rag`; migration cột `sync_outbox`/`projects` thuộc `workspace`, cột `papers` thuộc `ingestion`. Không module nào gọi thẳng infra module khác.

### References
- [Source: architecture.md#5.3] — Eventual Consistency & Sync Manager (SKIP LOCKED, Redis lock theo project_id, Lock Heartbeat, DLQ sau 3 lần, MERGE idempotent).
- [Source: architecture.md#5.2] — Graph Schema (Nodes/Edges Phase 1), Entity Resolution tác giả, Unique Constraints.
- [Source: architecture.md#1.3] — Infrastructure Constraints (RAM Neo4j 8GB) + Cơ chế Garbage Collection (cron 2h sáng, ngưỡng 7 ngày, cả Postgres + Neo4j).
- [Source: architecture.md#9.5, #9.6] — Hexagonal module + Event-Driven Sync boundaries (Producer=ingestion, Consumer=graph_rag/simple_rag).
- [Source: epics.md#Story-4.1] — phạm vi gộp 4.1 (Neo4j Connection + Outbox Worker + Event Sync + **GC gộp vào**); nhãn module/role; ranh giới ontology 4.1(base) ↔ 4.3(ontology).
- [Source: sprint-change-proposal-2026-06-17-gap-detection.md] — bối cảnh gộp 8→5 story, Leiden hoãn Phase 2, 4.1 phải đồng bộ thêm node/edge ontology do 4.3 ghi vào outbox.
- [Source: sprint-change-proposal-2026-06-17-role-matrix.md] — ma trận trách nhiệm 3 tầng; nhãn module/role từng task; producer `PAPER_UPSERTED` = retrofit `[ingestion]`; ranh giới ontology 4.1 ↔ 4.3.
- [Source: backend/worker.py#L248-L375] — `ingest_paper_task` + `WorkerSettings` (điểm chèn producer + cron_jobs).
- [Source: backend/src/modules/ingestion/application/use_cases.py#L33-L68] — pattern Redis lock compare-and-delete để tái dùng.
- [Source: backend/src/modules/workspace/infrastructure/orm_models.py#L36] — `SyncOutboxORM` hiện tại.
- [Source: tests/unit/ingestion/test_worker.py#L72] — pattern `_FakeSessionFactory` + AsyncMock cho test.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context)

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created (regenerated 2026-06-17 với code anchors đã xác minh + nhãn module/role role-clarity).
- Story 4.1 triển khai hoàn tất (2026-06-17): dựng toàn bộ write path Postgres→Neo4j từ zero.
- Task 1: Thêm neo4j:5-community vào docker-compose, neo4j>=5.0 vào requirements, neo4j_uri/username/password vào settings, tạo neo4j_client.py singleton + create_base_constraints (Paper.id/Author.id/Project.id UNIQUE IF NOT EXISTS).
- Task 2: Migration 009 mở rộng sync_outbox (project_id/retry_count/last_error/processed_at/dead_lettered + indexes + backfill). Thêm deleted_at vào projects và papers. Cập nhật 3 ORM, 2 soft_delete thêm set deleted_at + project_id vào outbox event.
- Task 3: Producer PAPER_UPSERTED retrofit trong ingest_paper_task — đặt SAU guard is_deleted, trước commit cuối (atomic outbox pattern). Nhánh is_deleted và nhánh failed KHÔNG ghi event.
- Task 4: Module graph_rag/ theo Hexagonal (domain/application/infrastructure). neo4j_adapter.py: 4 handlers MERGE idempotent (PAPER_UPSERTED→Paper+Author+[:AUTHORED_BY], PROJECT_DELETED/PAPER_DELETED→:Deleted label, CITES sẵn sàng). outbox_worker.py: claim SKIP LOCKED, group by project_id, Redis lock+heartbeat+release Lua, dispatch map mở rộng được, mark/retry/DLQ.
- Task 5: garbage_collection_task: Postgres hard-delete papers >7d (xóa file vật lý) + projects + dọn outbox >30d; Neo4j DETACH DELETE :Deleted >7d. Hai store độc lập.
- Task 6: WorkerSettings.cron_jobs=[sync_outbox_task mỗi 5s, GC 2h sáng]. startup/shutdown mở rộng với Neo4j driver init + create_base_constraints. .env.example thêm MAX_SYNC_RETRIES/GC_RETENTION_DAYS/SYNC_OUTBOX_BATCH_SIZE.
- Task 7: 19/19 tests unit/graph_rag/ xanh; 39/39 ingestion tests xanh; migration 009 syntax OK. Pre-existing SQLite test ordering issue không liên quan đến code thay đổi.

### File List

docker-compose.yml
requirements.txt
backend/src/shared/infra/settings.py
backend/src/shared/infra/neo4j_client.py
backend/alembic/versions/009_extend_sync_outbox_and_soft_delete.py
backend/src/modules/workspace/infrastructure/orm_models.py
backend/src/modules/ingestion/infrastructure/orm_models.py
backend/src/modules/workspace/infrastructure/postgres_repository.py
backend/src/modules/ingestion/infrastructure/postgres_repository.py
backend/worker.py
backend/src/modules/graph_rag/__init__.py
backend/src/modules/graph_rag/domain/__init__.py
backend/src/modules/graph_rag/application/__init__.py
backend/src/modules/graph_rag/application/use_cases.py
backend/src/modules/graph_rag/infrastructure/__init__.py
backend/src/modules/graph_rag/infrastructure/neo4j_adapter.py
backend/src/modules/graph_rag/infrastructure/outbox_worker.py
backend/src/modules/graph_rag/infrastructure/garbage_collection.py
tests/unit/graph_rag/__init__.py
tests/unit/graph_rag/test_producer.py
tests/unit/graph_rag/test_consumer.py
tests/unit/graph_rag/test_gc.py
.env.example

## Change Log

- 2026-06-18: **Correct-course sau review (theo nguyên tắc admin-config của PO):** chuyển `MAX_SYNC_RETRIES` + `GC_RETENTION_DAYS` từ env var → **system_settings** (Admin cấu hình runtime qua `/admin/settings`), mirror pattern `MAX_PAPERS_PER_PROJECT` (story 2.6). Thay đổi: seed 2 key trong migration 009; thêm vào `_NUMERIC_SETTING_KEYS` (router admin, validate int≥1); GC task + consumer đọc qua `get_setting` (fallback hằng số 7/3); bỏ 2 field khỏi `settings.py` + `.env.example`. `SYNC_OUTBOX_BATCH_SIZE` **giữ ở env** (knob hạ tầng RAM/ARCH-1, không cho admin chỉnh để tránh OOM). **Điều chỉnh AC#17 có chủ đích.** Sửa `.env`: `NEO4J_URI` localhost→`neo4j:7687` (app chạy full docker compose). 4 unit test mới; 65/65 graph_rag+ingestion+admin xanh.
- 2026-06-18: **Code review (bmad-code-review):** vá 8 lỗi (3 critical: heartbeat bytes/str, GC Neo4j temporal-vs-string, env key `pagecache__size`; + group None không lock, producer no-text, GC orphan file, author rỗng, migration backfill deleted_at). Xem mục "Review Findings".
- 2026-06-17: Story 4.1 triển khai hoàn tất — dựng toàn bộ write path Postgres→Neo4j từ zero (Neo4j infra, migration 009, producer PAPER_UPSERTED, module graph_rag consumer + GC, WorkerSettings cron_jobs, 19 unit tests xanh). Status → review.
