---
baseline_commit: 56dc266
---

# Story 4.7: [Backend] FILLS_GAP Producer — LLM-judge Limitation↔Paper (mở khóa "limitation chưa giải quyết")

Status: done

## Story

As a **kỹ sư backend của C2-App-053**,
I want **một arq task chạy NGẦM (`fills_gap_task`) — với mỗi Limitation CHƯA được lấp trong một project: tiền lọc ứng viên Paper bằng embedding (cosine ≥ ngưỡng) trên `child_chunks` pgvector, rồi gọi LLM judge (`gemini-2.5-flash`) "Bài X có thực sự giải quyết hạn chế này của bài Y không?"; nếu CÓ → ghi event `FILLS_GAP {filler_paper_id, limitation_id}` vào `sync_outbox` cho handler `handle_fills_gap` (MỚI) MERGE cạnh `(:Paper)-[:FILLS_GAP]->(:Limitation)` vào Neo4j — kèm bảng cache `fills_gap_judgement` để KHÔNG judge lại cặp đã quyết**,
so that **Query 3 của `gap_detection` (limitation chưa giải quyết — Story 4.4) phản ánh khoảng trống THẬT: chỉ Limitation thực sự chưa được paper nào lấp mới bị gắn cờ `has_unfilled_limitation`, thay vì TOÀN BỘ Limitation bị coi là "chưa lấp" vì đồ thị chưa từng có cạnh `[:FILLS_GAP]` nào (query có sẵn ở 4.4 nhưng chưa có producer)**.

## Bối cảnh & Phạm vi

Story này là **[Backend] follow-up** (correct-course 2026-06-18) hiện thực hóa cạnh `[:FILLS_GAP]` đã định nghĩa trong `architecture.md §5.2` ("Tương tác học thuật: `(:Paper)-[:FILLS_GAP]->(:Limitation)`") nhưng **chỉ xuất hiện trong TRUY VẤN** Query 3 của `gap_detection` (Story 4.4) — `NOT EXISTS { MATCH (filler:Paper)-[:FILLS_GAP]->(l) }` — **không nơi nào tạo cạnh này**. Hệ quả: mọi Limitation (gần như mọi paper có 1–5 Limitation do Story 4.3 trích) đều bị coi là "chưa lấp" → mọi Paper bị tô màu gap nhiễu. Đây là **nợ kỹ thuật** được trả nốt sau Story 4.6 (CITES producer — đã `done`).

**Nhãn module/role (theo Ma trận role-clarity `epics.md` §9.6):**
- `[ingestion]` — **PRODUCER duy nhất** ghi `sync_outbox`: task `fills_gap_task` (worker.py = composition root ingestion) + class judge mới `fills_gap_judge.py` (`ingestion/infrastructure/`). Tái dùng `GeminiEmbeddingClient` (ingestion) + pgvector `child_chunks` (Simple RAG retriever pattern).
- `[graph_rag]` — **CONSUMER + READ API**: (a) handler `handle_fills_gap` **MỚI** + đăng ký vào `HANDLER_MAP`; (b) read use-case `list_unfilled_limitations(session, project_id)` **MỚI** (graph_rag SỞ HỮU mọi đọc Neo4j — mirror `gap_detection`). `fills_gap_task` GỌI read use-case này, KHÔNG tự viết Cypher đọc Neo4j từ ingestion.

**Phụ thuộc đã done:** Story 4.1 (`sync_outbox` + `HANDLER_MAP` mở-rộng-được + `outbox_worker` dispatch), Story 4.3 (Limitation nodes + `[:HAS_LIMITATION]` đã tồn tại trong Neo4j; `graph_extract_task` để gắn điểm enqueue), Story 4.4 (`gap_detection` Query 3 — sẽ hưởng lợi, query KHÔNG đổi), Story 3.6/4.6 (pgvector `child_chunks` embeddings + retriever pattern `<=>`).

**Ranh giới:**
- ✅ TRONG phạm vi: `fills_gap_task` arq (project-scoped) · enqueue ngầm từ `graph_extract_task` (`_defer_by` để chờ ONTOLOGY_EXTRACTED sync) + đăng ký `WorkerSettings.functions` · class `FillsGapJudge` (LLM judge `gemini-2.5-flash`) · tiền-lọc embedding qua pgvector `child_chunks` · bảng cache `fills_gap_judgement` (Alembic migration 010) · read use-case `list_unfilled_limitations` (graph_rag) · handler `handle_fills_gap` + `HANDLER_MAP["FILLS_GAP"]` · admin endpoint backfill · unit tests.
- ❌ NGOÀI phạm vi: sửa logic `gap_detection`/Query 3 (Story 4.4 — chỉ "đổ dữ liệu thật") · tách màu FE 3 loại gap (Story 4.8 — đã `done`) · CITES (Story 4.6 — đã `done`) · Leiden community (Phase 2) · embedding lại toàn corpus / cột embedding mới cho Limitation/Paper (dùng `child_chunks` sẵn có) · gọi LLM-judge ĐỒNG BỘ trên nút "Tìm khoảng trống" (BỊ CẤM — xem Quyết định #1) · sửa `outbox_worker.py` (dispatch đã mở-rộng-được).

### Quyết định kiến trúc đã chốt

1. **CHẠY NGẦM, KHÔNG đồng bộ với nút gap.** `gap_detection` (Story 4.4) PHẢI giữ nguyên = Cypher read nhanh. LLM-judge N×M tốn vài chục giây/dự án → BẮT BUỘC chạy trong arq worker. (Proposal §3: phá triết lý "gap_detection = Cypher read nhanh" là điều cấm.)
2. **Tiền lọc embedding TRƯỚC LLM (cắt N×M → N×K).** Với mỗi Limitation, embed `description` rồi cosine-search `child_chunks` pgvector → chỉ lấy top-K Paper ứng viên có độ tương đồng ≥ ngưỡng. KHÔNG judge mọi cặp. Tái dùng đúng pattern retriever `real_rag_node` (`embedding.op("<=>")` = cosine distance). Tránh thêm cột/bảng embedding mới — `child_chunks.embedding` (Vector 768) đã có.
3. **Cache quyết định trong Postgres (`fills_gap_judgement`).** Idempotency của LLM: một Limitation "chưa có cạnh FILLS_GAP" có thể là *chưa-judge* HOẶC *đã-judge-âm*. Không cache → mỗi lần ingest re-judge toàn bộ → tốn token lặp lại. Cache theo `(limitation_id, candidate_paper_id)` (cả yes lẫn no) → bỏ qua cặp đã quyết. (Proposal AC#6 bắt buộc.) → **1 bảng mới + Alembic migration 010**.
4. **Ngưỡng là HẰNG MODULE-LEVEL, không admin-setting.** Mirror `TITLE_MATCH_THRESHOLD=0.85` của Story 4.6 (`reference_matcher.py`): `FILLS_GAP_SIM_THRESHOLD=0.65` (cosine similarity) + `FILLS_GAP_TOP_K_CANDIDATES=5` đặt trong module judge. KHÔNG thêm vào `_NUMERIC_SETTING_KEYS` (các key đó là **int**, ngưỡng là **float** — tránh phức tạp; quan sát log để chỉnh — Proposal AC#7).
5. **Đọc Limitation từ Neo4j QUA graph_rag read use-case, KHÔNG query Neo4j trực tiếp từ ingestion.** Thêm `list_unfilled_limitations(session, project_id)` vào `graph_rag/application/use_cases.py` (cạnh `GapDetectionUseCase`). `fills_gap_task` gọi nó qua `ctx["neo4j_driver"].session()`. Tôn trọng "graph_rag sở hữu mọi đọc Neo4j".
6. **Model judge = `gemini-2.5-flash`** (flash tier rẻ nhất trong codebase; default của `get_llm_client`). Proposal nêu `gemini-1.5-flash` vì chi phí — codebase dùng họ 2.5; chọn flash để rẻ. Qua `LLMRouter` (user key → system fallback). Bọc retry Tenacity cho rate-limit (pattern `arxiv_client.py`).
7. **Trigger = enqueue ngầm từ `graph_extract_task` (incremental, project-scoped) + admin backfill.** Sau khi `graph_extract_task` commit ONTOLOGY_EXTRACTED, best-effort enqueue `fills_gap_task(project_id)` với `_job_id=f"fills_gap:{project_id}"` (arq tự khử trùng) và `_defer_by≈60s` (chờ event ONTOLOGY_EXTRACTED được `sync_outbox_task` sync sang Neo4j — eventual consistency). KHÔNG cron quét-mọi-project mỗi tick (nặng). Re-run an toàn nhờ cache + MERGE idempotent.
8. **Eventual consistency chấp nhận được.** Limitation node chỉ tồn tại sau khi ONTOLOGY_EXTRACTED sync (cron 5s). `fills_gap_task` deferred ~60s + idempotent + re-trigger mỗi ingest → cuối cùng mọi Limitation được judge. Project ít dữ liệu → `list_unfilled_limitations` trả rỗng → no-op an toàn.

## Acceptance Criteria

### A. [graph_rag] Read use-case `list_unfilled_limitations`

1. Thêm vào `backend/src/modules/graph_rag/application/use_cases.py` (cạnh `GapDetectionUseCase`, dòng ~234) hàm/coroutine đọc Neo4j trả về các Limitation CHƯA được lấp trong project:
   - Chữ ký: `async def list_unfilled_limitations(session, project_id: str) -> list[dict]` (nhận Neo4j `AsyncSession` như các use-case đọc khác trong file).
   - Cypher (mirror Query 3 của `gap_detection` nhưng trả thêm `description` + owner paper):
     ```cypher
     MATCH (p:Paper {project_id: $pid})-[:HAS_LIMITATION]->(l:Limitation {project_id: $pid})
     WHERE NOT p:Deleted
       AND NOT EXISTS {
         MATCH (filler:Paper {project_id: $pid})-[:FILLS_GAP]->(l) WHERE NOT filler:Deleted
       }
     RETURN DISTINCT l.id AS limitation_id, l.description AS description, p.id AS owner_paper_id
     ```
   - Trả `[{"limitation_id", "description", "owner_paper_id"}]`. Bọc try/except → lỗi Neo4j trả `[]` + `logger.warning` (nhất quán `gap_detection`). Bỏ qua record `description` rỗng/None (không judge được).

### B. [ingestion] Class `FillsGapJudge` (LLM judge)

2. Tạo `backend/src/modules/ingestion/infrastructure/fills_gap_judge.py` — class `FillsGapJudge` mirror `GraphExtractor`:
   - `__init__(self, user_id: str, db: AsyncSession)` — inject cho `LLMRouter`.
   - `async def judge(self, limitation_desc: str, owner_title: str, candidate_title: str, candidate_text: str) -> dict | None` — gọi LLM, trả `{"fills": bool, "reason": str}` hoặc `None` nếu lỗi/JSON sai (KHÔNG raise).
   - Dùng `LLMRouter(self._db).get_llm_client(self._user_id, model_name="gemini-2.5-flash")` + `.ainvoke(prompt)`. Tái dùng `_coerce_to_text` + `_parse_json` (strip code-fence + fallback cắt `{...}`) — copy/ tái dùng pattern từ `graph_extractor.py` (KHÔNG thêm dependency).
   - Prompt (xem Dev Notes §Prompt judge): bảo thủ — *"chỉ trả fills=true nếu candidate paper THỰC SỰ giải quyết/lấp hạn chế này, không phải chỉ liên quan chủ đề"*.
   - `candidate_text` giới hạn `[:4000]` chars (đủ ngữ cảnh, rẻ).
   - JSON sai / `fills` không phải bool → coi như `None` (an toàn, không bịa cạnh).

3. Hằng module-level trong `fills_gap_judge.py` (hoặc module task): `FILLS_GAP_SIM_THRESHOLD = 0.65` (cosine similarity), `FILLS_GAP_TOP_K_CANDIDATES = 5`, `FILLS_GAP_JUDGE_MODEL = "gemini-2.5-flash"`, `CANDIDATE_TEXT_LIMIT = 4000`. Dễ chỉnh.

### C. [ingestion] Bảng cache `fills_gap_judgement` + Alembic migration

4. Tạo ORM `FillsGapJudgementORM` trong `backend/src/modules/ingestion/infrastructure/` (file mới `fills_gap_orm.py` HOẶC thêm vào `orm_models.py` ingestion — dev chọn nhất quán, mặc định file mới):
   - Cột: `id` (int autoincrement PK), `project_id` (Uuid as_uuid=False, indexed), `limitation_id` (String, indexed), `candidate_paper_id` (String), `fills` (Boolean), `reason` (Text, nullable), `created_at` (DateTime tz, server_default now()).
   - **Unique constraint** `(limitation_id, candidate_paper_id)` (1 quyết định/cặp). Index trên `(project_id)` để quét/xóa theo project.

5. Alembic migration `backend/alembic/versions/010_create_fills_gap_judgement_table.py`:
   - `upgrade()`: `op.create_table("fills_gap_judgement", ...)` đúng cột AC#4 + UniqueConstraint + index. `down_revision = "009"` (migration mới nhất hiện tại là `009_extend_sync_outbox_and_soft_delete`). `revision = "010"`.
   - `downgrade()`: `op.drop_table("fills_gap_judgement")`.
   - Mirror style migration hiện có (xem `006_create_chunks_tables.py` / `009_*`).

### D. [ingestion] Task `fills_gap_task` + tiền lọc embedding + producer event

6. Tạo `async def fills_gap_task(ctx, project_id: str) -> None` trong `backend/worker.py`:
   - Lấy `session_factory = ctx["session_factory"]` (Postgres) + `neo4j_driver = ctx["neo4j_driver"]`.
   - **Bước 1 — đọc Limitation chưa lấp:** `async with neo4j_driver.session() as ns:` → `limitations = await list_unfilled_limitations(ns, project_id)`. Rỗng → `logger.info("fills_gap_task: project %s — 0 unfilled limitations", project_id)` + return.
   - **Bước 2 — với mỗi limitation:**
     - Embed `description` qua `GeminiEmbeddingClient(user_id, db).embed_batch([description])[0]`. (`user_id` lấy từ owner paper — xem Dev Notes §user_id.) Vector toàn 0.0 (degraded) → bỏ qua limitation đó (log).
     - **Tiền lọc pgvector** (mirror `real_rag_node`): query `child_chunks` cùng `project_id`, `embedding IS NOT NULL`, `paper_id != owner_paper_id`, lấy candidate paper theo cosine distance nhỏ nhất, giữ candidate có `similarity ≥ FILLS_GAP_SIM_THRESHOLD` (tức `distance ≤ 1 - threshold`), tối đa `FILLS_GAP_TOP_K_CANDIDATES` paper distinct. (Cosine distance qua `embedding.op("<=>")(literal(vec, Vector(768)))`.)
     - Với mỗi `candidate_paper_id`:
       - **Skip nếu đã cache:** SELECT `fills_gap_judgement` theo `(limitation_id, candidate_paper_id)` — tồn tại → bỏ qua (không gọi LLM lại).
       - Lấy ngữ cảnh candidate: `candidate_title` + `candidate_text` (= abstract + join vài `ParentChunkORM` của candidate, `[:CANDIDATE_TEXT_LIMIT]`).
       - Gọi `FillsGapJudge(user_id, db).judge(description, owner_title, candidate_title, candidate_text)`. `None` → bỏ qua (KHÔNG cache, retry lần sau).
       - Ghi cache: `db.add(FillsGapJudgementORM(project_id, limitation_id, candidate_paper_id, fills=result["fills"], reason=result.get("reason")))`.
       - Nếu `fills is True` **và** `candidate_paper_id != owner_paper_id`: `db.add(SyncOutboxORM(event_type="FILLS_GAP", project_id=project_id, payload={"filler_paper_id": candidate_paper_id, "limitation_id": limitation_id, "project_id": project_id}))`.
   - Commit theo lô an toàn (xem Dev Notes §commit). Log tổng: số limitation quét / số cặp judge / số FILLS_GAP phát sinh / số cache-hit.

7. Đăng ký `fills_gap_task` vào `WorkerSettings.functions` (thêm vào list hiện tại `[ingest_paper_task, graph_extract_task]`).

8. **Enqueue ngầm từ `graph_extract_task`:** thêm helper best-effort `_enqueue_fills_gap(redis, project_id)` (mirror `_enqueue_graph_extract`, worker.py:445) và gọi SAU `await db.commit()` cuối `graph_extract_task` (dòng ~613):
   - `await redis.enqueue_job("fills_gap_task", paper.project_id, _job_id=f"fills_gap:{paper.project_id}", _defer_by=timedelta(seconds=60))` — `_job_id` cố định theo project (arq khử trùng), `_defer_by` chờ ONTOLOGY_EXTRACTED sync. Bọc try/except: lỗi enqueue KHÔNG làm fail `graph_extract_task`.
   - **Lưu ý:** `graph_extract_task` chỉ có `ctx["session_factory"]` hiện tại — xác nhận có `ctx["redis"]` (arq luôn cấp `ctx["redis"]`); dùng `ctx["redis"]` để enqueue.

### E. [graph_rag] Handler `handle_fills_gap` + HANDLER_MAP

9. Thêm `async def handle_fills_gap(session: AsyncSession, payload: dict) -> None` vào `backend/src/modules/graph_rag/infrastructure/neo4j_adapter.py` (mirror `handle_cites`):
   - `filler_id = payload.get("filler_paper_id")`, `limitation_id = payload.get("limitation_id")`, `project_id = payload.get("project_id")`. Thiếu `filler_id`/`limitation_id` → `logger.warning` + return (guard như `handle_cites`).
   - Cypher (scope `project_id` chống IDOR, MATCH không MERGE node để tránh tạo node rác):
     ```cypher
     MATCH (p:Paper {id: $filler_id}), (l:Limitation {id: $limitation_id})
     WHERE p.project_id = $project_id AND l.project_id = $project_id
     MERGE (p)-[:FILLS_GAP]->(l)
     ```
   - Idempotent (MERGE); chạy lại không nhân đôi cạnh. Nếu `project_id` thiếu trong payload (forward-compat) → bỏ điều kiện scope hoặc skip an toàn (dev chốt: ưu tiên scope khi có).

10. Đăng ký `HANDLER_MAP["FILLS_GAP"] = handle_fills_gap` (cuối `neo4j_adapter.py`, KHÔNG xóa entry cũ). `outbox_worker` dispatch tự nhận (event có handler → không DLQ).

### F. Admin backfill + Tests

11. Thêm endpoint `POST /api/admin/backfill-fills-gap` vào `backend/src/modules/admin/presentation/router.py` (mirror `backfill-graph-extraction` của Story 4.3):
    - Requires `current_user.role == "admin"`.
    - Lấy danh sách `project_id` distinct của papers `status="indexed"`, `is_deleted=False` (chỉ cột cần — `select(PaperORM.project_id).distinct()`).
    - Enqueue `fills_gap_task` cho từng project (`_job_id=f"fills_gap:{pid}"` idempotent; KHÔNG `_defer_by` ở backfill — chạy ngay).
    - Response `{"enqueued": N, "message": "Đã đưa N project vào hàng đợi phân tích FILLS_GAP"}`. Chạy OK khi N=0.

12. `tests/unit/ingestion/test_fills_gap_judge.py` (class judge):
    - `test_judge_returns_dict_on_valid_json`: mock LLM trả `{"fills": true, "reason": "..."}` → trả dict.
    - `test_judge_returns_none_on_invalid_json`: LLM trả `"not json"` → `None`.
    - `test_judge_returns_none_on_llm_exception`: LLM raise → `None`.
    - `test_judge_returns_none_when_fills_not_bool`: `{"fills": "maybe"}` → `None`.
    - `test_judge_strips_code_fence`: LLM bọc ```` ```json ```` → parse đúng.

13. `tests/unit/graph_rag/test_consumer.py` (MỞ RỘNG — handler + HANDLER_MAP):
    - `test_handle_fills_gap_merges_edge`: mock `session.run`, payload đủ → query chứa `"MERGE"` + `"FILLS_GAP"`.
    - `test_handle_fills_gap_skips_when_missing_ids`: payload thiếu `filler_paper_id` → KHÔNG gọi `session.run`.
    - `test_fills_gap_in_handler_map`: `assert "FILLS_GAP" in HANDLER_MAP`.

14. `tests/unit/ingestion/test_fills_gap_task.py` (task — mock LLM + embedding + Neo4j read):
    - `test_fills_gap_task_emits_event_on_fill`: 1 unfilled limitation; embedding mock; 1 candidate qua tiền lọc; judge mock `{"fills": true}` → `SyncOutboxORM(event_type="FILLS_GAP")` được `db.add` + bản ghi cache.
    - `test_fills_gap_task_no_event_when_not_fill`: judge `{"fills": false}` → KHÔNG add FILLS_GAP event, NHƯNG cache vẫn ghi (tránh re-judge).
    - `test_fills_gap_task_skips_cached_pair`: cặp đã có trong `fills_gap_judgement` → KHÔNG gọi judge.
    - `test_fills_gap_task_noop_when_no_unfilled`: `list_unfilled_limitations` trả `[]` → KHÔNG embed, KHÔNG judge, KHÔNG add event.
    - `test_fills_gap_task_skips_self_fill`: candidate == owner_paper_id → KHÔNG add event.
    - `test_graph_extract_task_enqueues_fills_gap`: (mở rộng `test_graph_extract_task.py`) sau commit → `ctx["redis"].enqueue_job` được gọi với `"fills_gap_task"` + đúng project_id. (Best-effort: lỗi enqueue không làm fail task.)

## Tasks / Subtasks

- [x] **Task 1 — [graph_rag] read use-case `list_unfilled_limitations`** (AC: 1)
  - [x] Thêm hàm vào `use_cases.py` (Cypher trả limitation_id/description/owner_paper_id; try/except → `[]`)
  - [x] Skip description rỗng/None

- [x] **Task 2 — [ingestion] `FillsGapJudge` + hằng module** (AC: 2,3)
  - [x] Tạo `fills_gap_judge.py` (class judge + `_parse_json`/`_coerce_to_text` tái dùng; `gemini-2.5-flash`)
  - [x] Hằng `FILLS_GAP_SIM_THRESHOLD=0.65`, `TOP_K=5`, model, `CANDIDATE_TEXT_LIMIT=4000`
  - [x] Unit tests `test_fills_gap_judge.py` (AC: 12)

- [x] **Task 3 — [ingestion] Bảng cache + migration 010** (AC: 4,5)
  - [x] ORM `FillsGapJudgementORM` (unique `(limitation_id, candidate_paper_id)`)
  - [x] Alembic `010_create_fills_gap_judgement_table.py` (`down_revision="009"`)

- [x] **Task 4 — [ingestion] `fills_gap_task` (tiền lọc + judge + producer)** (AC: 6,7,8)
  - [x] Hàm `fills_gap_task(ctx, project_id)`: đọc limitations (Neo4j) → embed → pgvector tiền lọc → cache-check → judge → cache-write → emit `FILLS_GAP`
  - [x] Tiền lọc `child_chunks` qua `embedding.op("<=>")` (mirror `real_rag_node`), ngưỡng + top-K, loại owner paper
  - [x] Guard self-fill, commit theo lô, log đầy đủ
  - [x] Đăng ký `WorkerSettings.functions`
  - [x] Helper `_enqueue_fills_gap` + gọi cuối `graph_extract_task` (`_defer_by=60s`, best-effort)
  - [x] Unit tests `test_fills_gap_task.py` + mở rộng `test_graph_extract_task.py` (AC: 14)

- [x] **Task 5 — [graph_rag] handler `handle_fills_gap` + HANDLER_MAP** (AC: 9,10)
  - [x] Handler MERGE `[:FILLS_GAP]` (scope project_id, guard missing ids)
  - [x] `HANDLER_MAP["FILLS_GAP"] = handle_fills_gap`
  - [x] Tests trong `test_consumer.py` (AC: 13)

- [x] **Task 6 — [admin] backfill endpoint** (AC: 11)
  - [x] `POST /api/admin/backfill-fills-gap` (admin role, distinct project_id, enqueue mỗi project)

## Dev Notes

### Kiến trúc & ràng buộc bắt buộc

- **Hexagonal §9.5/§9.6:** `FillsGapJudge` + `FillsGapJudgementORM` ở `ingestion/infrastructure/` (driven adapter / persistence). Orchestrate ở `fills_gap_task` (`worker.py` = composition root ingestion — được phép gọi infra ingestion + đọc graph_rag read use-case + ghi `SyncOutboxORM`). `handle_fills_gap` + `list_unfilled_limitations` ở `graph_rag` (CONSUMER + sở hữu mọi Neo4j read/write). **KHÔNG** viết Cypher đọc Limitation trực tiếp trong `worker.py`; **KHÔNG** sửa `HANDLER_MAP` từ `worker.py`.
- **Role-clarity (`epics.md` §Ma trận):** `ingestion` = PRODUCER duy nhất ghi `sync_outbox`; `graph_rag` = CONSUMER + read API (`gap_detection`/`graph_search`/`list_unfilled_limitations`). Story 4.7 đúng nguyên tắc: producer ở ingestion, handler + read ở graph_rag.
- **NFR4 (RAM/concurrency):** worker `max_jobs=2` (worker.py:621). `fills_gap_task` chạy trong cùng worker → tôn trọng giới hạn. Tiền-lọc embedding (Quyết định #2) + cache (Quyết định #3) là cơ chế cắt chi phí N×M BẮT BUỘC. Corpus nhỏ (`MAX_PAPERS_PER_PROJECT=15`) → N×K nhỏ.
- **IDOR/scope:** tiền-lọc `child_chunks` PHẢI `project_id == project_id`; `list_unfilled_limitations` scope `project_id` trên cả Paper & Limitation; handler MERGE scope `project_id`. (Id Neo4j là UUID toàn cục nhưng vẫn thêm guard project_id cho an toàn — mirror ontology handler 4.3.)
- **Không dependency mới:** dùng `GeminiEmbeddingClient` (có sẵn), `pgvector`/`sqlalchemy` (có), `tenacity` (đã dùng `arxiv_client.py`), `langchain_google_genai` qua `LLMRouter`. KHÔNG thêm lib.

### 🚨 Eventual consistency & idempotency (đọc kỹ)

- **Limitation node chỉ có SAU khi ONTOLOGY_EXTRACTED sync** (`sync_outbox_task` cron 5s). `graph_extract_task` enqueue `fills_gap_task` với `_defer_by=60s` để chờ. Nếu vẫn chưa sync → `list_unfilled_limitations` trả ít/rỗng → no-op; lần ingest sau hoặc admin backfill bù. **Chấp nhận (Quyết định #8).**
- **3 tầng idempotent:** (a) `_job_id=f"fills_gap:{project_id}"` → arq không chạy trùng job/project; (b) `fills_gap_judgement` unique `(limitation_id, candidate_paper_id)` → không judge lại + không INSERT trùng (dùng `INSERT ... ON CONFLICT DO NOTHING` hoặc check-then-add; ưu tiên check-SELECT trước add để đơn giản test); (c) handler MERGE `[:FILLS_GAP]` → không nhân đôi cạnh.
- **Thứ tự outbox (`id.asc()`):** `PAPER_UPSERTED`/`ONTOLOGY_EXTRACTED` (id thấp hơn) luôn sync trước `FILLS_GAP`. Nếu Limitation/Paper chưa kịp sync khi `FILLS_GAP` xử lý → `MATCH` rỗng → MERGE không tạo cạnh; re-run/backfill tự lành. Ghi rõ là chấp nhận được (mirror learnings CITES 4.6).

### §commit — chiến lược commit trong `fills_gap_task`

- Mở 1 `async with session_factory() as db:` cho toàn task. `db.add` cache row + FILLS_GAP event, **commit định kỳ** (vd sau mỗi limitation, hoặc mỗi batch ~20 add) để tránh transaction quá lớn + giải phóng nếu task bị kill giữa chừng (đã commit phần trước → cache giữ, không re-judge). KHÔNG để toàn task trong 1 commit cuối (rủi ro mất hết khi timeout 600s). Cache + MERGE idempotent khiến commit-một-phần an toàn.

### §user_id — LLM/embedding cần user_id

- `GeminiEmbeddingClient` và `LLMRouter` cần `user_id` (resolve API key user→system). `fills_gap_task` nhận `project_id`, KHÔNG có user trực tiếp. Lấy `user_id` từ owner paper của limitation: query `PaperORM.user_id` theo `owner_paper_id` (mỗi limitation có owner). Hoặc lấy user_id của project owner. **Chốt:** dùng `paper.user_id` của owner paper (đã có cột — `graph_extract_task` dùng `paper.user_id` y hệt, worker.py:505). Nếu nhiều owner khác user → mỗi limitation tự dùng user của owner mình (LLMRouter fallback system key nếu user không có key).

### §Prompt judge (tham khảo)

```python
FILLS_GAP_JUDGE_PROMPT = """You are an academic reviewer. Decide if a CANDIDATE paper genuinely
RESOLVES or FILLS a specific LIMITATION stated by another (SOURCE) paper.

SOURCE paper title: {owner_title}
LIMITATION to evaluate: {limitation_desc}

CANDIDATE paper title: {candidate_title}
CANDIDATE paper content (may be truncated):
{candidate_text}

Answer ONLY with a JSON object (no markdown):
{{"fills": true_or_false, "reason": "one short sentence"}}

Rules:
- fills=true ONLY if the candidate paper directly addresses/solves/overcomes THIS limitation
  (e.g. provides the missing method, larger dataset, or resolves the stated gap).
- Mere topical similarity, citing the same domain, or partial relevance => fills=false.
- Be conservative: when unsure, fills=false.
- JSON only."""
```

### Pattern code tái dùng (xác minh trước khi code)

- **Tiền-lọc pgvector** — mirror `orchestrator/application/graph.py` `real_rag_node` (vector_search):
  ```python
  from pgvector.sqlalchemy import Vector
  from sqlalchemy import literal, select
  from backend.src.modules.ingestion.infrastructure.chunk_orm_models import ChildChunkORM
  query_vec = literal(limitation_embedding, Vector(768))
  stmt = (
      select(ChildChunkORM.paper_id, ChildChunkORM.embedding.op("<=>")(query_vec).label("dist"))
      .where(ChildChunkORM.project_id == project_id)
      .where(ChildChunkORM.embedding.is_not(None))
      .where(ChildChunkORM.paper_id != owner_paper_id)
      .order_by("dist")
      .limit(FILLS_GAP_TOP_K_CANDIDATES * 4)  # lấy dư rồi distinct + ngưỡng ở Python
  )
  # → gom distinct paper_id theo dist nhỏ nhất, giữ những paper có (1 - dist) >= FILLS_GAP_SIM_THRESHOLD,
  #   cắt còn TOP_K. (pgvector "<=>" = cosine distance; similarity = 1 - distance.)
  ```
  (`TOP_K=5`, threshold so trên similarity. Có thể distinct bằng `GROUP BY paper_id, MIN(dist)` ở SQL nếu muốn gọn.)
- **LLMRouter + parse JSON** — mirror `graph_extractor.py` (`_coerce_to_text`, `_parse_json` strip fence + fallback `{...}`) và `metadata_extractor.py`. Copy 2 helper hoặc tách shared util.
- **Embedding** — `GeminiEmbeddingClient(user_id, db).embed_batch([text])` trả `list[list[float]]`; vector toàn 0.0 = degraded (bỏ qua).
- **Ghi outbox** — `SyncOutboxORM(event_type=..., project_id=..., payload={...})` + `db.add` (worker.py:547,597 làm mẫu). `SyncOutboxORM` đã import sẵn worker.py.
- **Enqueue arq** — `_enqueue_graph_extract` (worker.py:445) làm mẫu best-effort; `ctx["redis"].enqueue_job(..., _job_id=..., _defer_by=timedelta(...))`. `timedelta` từ `datetime` (kiểm tra import).
- **Test handler Cypher** — `test_consumer.py`: `session.run = AsyncMock(side_effect=lambda q,**k: queries.append(q))`, assert `any("MERGE" in q)`. Mẫu sẵn cho CITES/ontology.
- **Test task** — `tests/unit/ingestion/test_graph_extract_task.py`: `_FakeSessionFactory` + `_make_db` (mock `db.execute` side_effect theo thứ tự query). Mock `FillsGapJudge`/`GeminiEmbeddingClient`/`list_unfilled_limitations` qua `patch("backend.worker....")`. Mock `ctx["neo4j_driver"].session()`.
- **Backfill admin** — `router.py` `POST /admin/backfill-graph-extraction` (Story 4.3) làm mẫu chính xác (admin check + select-id-only + enqueue loop + response).

### Hiện trạng code sẽ ĐỘNG TỚI (xác minh kỹ)

- **`backend/worker.py`**: `WorkerSettings.functions` (dòng 618) → thêm `fills_gap_task`. Cuối `graph_extract_task` (sau `await db.commit()` dòng 613) → gọi `_enqueue_fills_gap`. Thêm hàm `fills_gap_task` + `_enqueue_fills_gap`. Import: `FillsGapJudge`, `FillsGapJudgementORM`, `GeminiEmbeddingClient` (kiểm tra đã import chưa — `ingest_paper_task` dùng nó), `ChildChunkORM`, `list_unfilled_limitations`, `timedelta`, `literal`, `Vector`.
- **`backend/src/modules/graph_rag/application/use_cases.py`**: thêm `list_unfilled_limitations` cạnh `GapDetectionUseCase` (dòng ~234). Tái dùng hằng Cypher `_CYPHER_UNFILLED_LIMITATION` (dòng ~213) làm cơ sở — nhưng trả thêm cột.
- **`backend/src/modules/graph_rag/infrastructure/neo4j_adapter.py`**: thêm `handle_fills_gap` + `HANDLER_MAP["FILLS_GAP"]` (dict dòng ~349, hiện 5 entry: PAPER_UPSERTED/PROJECT_DELETED/PAPER_DELETED/CITES/ONTOLOGY_EXTRACTED). KHÔNG sửa handler cũ.
- **`backend/src/modules/admin/presentation/router.py`**: thêm `POST /admin/backfill-fills-gap` (mirror backfill-graph-extraction). KHÔNG đụng `_NUMERIC_SETTING_KEYS`.
- **`backend/alembic/versions/`**: thêm `010_create_fills_gap_judgement_table.py` (`down_revision="009"`).

### Learnings từ Story 4.6 (CITES producer — sibling, áp dụng trực tiếp)

- **LLM output untrusted:** lọc entry không phải dict / field None TRƯỚC khi `.strip()`/`.get()` (4.6 review Critical: `None.strip()` cuốn theo cả commit). `FillsGapJudge.judge` phải guard `result` không phải dict / `fills` không bool → trả `None`.
- **Producer ghi outbox cùng `db.commit`** với cache row; commit-một-phần an toàn nhờ idempotent (xem §commit).
- **No self-cite ↔ no self-fill:** 4.6 guard `cited_id == paper_id`; 4.7 guard `candidate_paper_id == owner_paper_id`.
- **Query candidate chỉ khi cần:** 4.6 skip query thứ 3 khi references rỗng (giữ test cũ pass). 4.7: skip embed/judge khi `list_unfilled_limitations` rỗng (no-op, không gọi LLM/embedding tốn phí).
- **Pre-existing failures:** `tests/unit/identity/*` + `test_projects_api.py` lỗi SQLite ARRAY/isolation — KHÔNG liên quan, KHÔNG debug.

### Learnings từ Story 4.3 / 4.1

- **`graph_extract_task` text gathering:** join `ParentChunkORM` order by `chunk_index`, fallback `paper.abstract`. Tái dùng cho `candidate_text` (worker.py:486-496 làm mẫu).
- **Handler guard `.get()`:** 4.3 review — KeyError khi payload thiếu id đầu độc outbox→DLQ. `handle_fills_gap` dùng `.get()` + return khi thiếu.
- **Outbox forward-compat:** `outbox_worker.py` guard "event lạ" tăng retry. Vì `FILLS_GAP` ĐÃ có handler khi deploy → xử lý ngay, không DLQ.
- **LLM graceful failure:** 4.3 — LLM fail/JSON sai → log + return `None`, KHÔNG fail task. `FillsGapJudge` y hệt.

### Project Structure Notes

**Files MỚI:**
```
backend/src/modules/ingestion/infrastructure/fills_gap_judge.py     # FillsGapJudge (LLM gemini-2.5-flash) + hằng ngưỡng
backend/src/modules/ingestion/infrastructure/fills_gap_orm.py       # FillsGapJudgementORM (cache)
backend/alembic/versions/010_create_fills_gap_judgement_table.py    # migration cache table
tests/unit/ingestion/test_fills_gap_judge.py                        # AC: 12
tests/unit/ingestion/test_fills_gap_task.py                         # AC: 14
```

**Files CẬP NHẬT:**
```
backend/worker.py                                                   # +fills_gap_task +_enqueue_fills_gap +WorkerSettings.functions +enqueue cuối graph_extract_task
backend/src/modules/graph_rag/application/use_cases.py             # +list_unfilled_limitations
backend/src/modules/graph_rag/infrastructure/neo4j_adapter.py     # +handle_fills_gap +HANDLER_MAP["FILLS_GAP"]
backend/src/modules/admin/presentation/router.py                  # +POST /admin/backfill-fills-gap
tests/unit/graph_rag/test_consumer.py                             # +test handle_fills_gap + HANDLER_MAP
tests/unit/ingestion/test_graph_extract_task.py                   # +test enqueue fills_gap
```

**KHÔNG SỬA:** `gap_detection`/Query 3 (Story 4.4 — query không đổi) · `outbox_worker.py` (dispatch mở-rộng-được) · handler cũ (`handle_cites`/`handle_ontology_extracted`/...) · `reference_matcher.py` (4.6) · `_NUMERIC_SETTING_KEYS` · FE · `ingest_paper_task` (ngoài việc graph_extract_task đã enqueue) · cột embedding mới (dùng `child_chunks`).

### References

- [Source: architecture.md §5.2] — Graph Schema Phase 1: Edge `(:Paper)-[:FILLS_GAP]->(:Limitation)` (Tương tác học thuật)
- [Source: sprint-change-proposal-2026-06-18-cites-fillsgap-producers.md §4.A (Story 4.7), §2 Technical/NFR, §3] — AC nháp FILLS_GAP, quyết định LLM-judge + tiền lọc embedding + cache + chạy ngầm; thứ tự 4.8→4.6→4.7
- [Source: epics.md §Story 4.7] — Phạm vi FILLS_GAP producer, phụ thuộc 4.1/4.3, FR7/FR9, "CHẠY NGẦM không đồng bộ nút gap"
- [Source: 4-6-cites-producer-trich-references-khop-paper.md] — Sibling producer pattern (outbox emit trong worker, handler đã có, no-self, idempotent, LLM-untrusted guard, threshold module-const)
- [Source: 4-3-graph-extraction-trich-xuat-ontology-hoc-thuat.md] — Stage-2 `graph_extract_task`, GraphExtractor LLM pattern, ontology MERGE, backfill endpoint, Limitation node
- [Source: backend/worker.py:445-457] — `_enqueue_graph_extract` best-effort enqueue (mẫu `_enqueue_fills_gap`)
- [Source: backend/worker.py:469-614] — `graph_extract_task` (text gathering, outbox emit, điểm enqueue cuối dòng 613)
- [Source: backend/worker.py:617-634] — `WorkerSettings` (functions, max_jobs=2, cron_jobs, ctx["neo4j_driver"] qua startup:175)
- [Source: backend/src/modules/graph_rag/application/use_cases.py:213-220,234-286] — `_CYPHER_UNFILLED_LIMITATION` Query 3 + `GapDetectionUseCase` (mẫu `list_unfilled_limitations`)
- [Source: backend/src/modules/graph_rag/infrastructure/neo4j_adapter.py:148-166,349-355] — `handle_cites` (mẫu `handle_fills_gap`) + `HANDLER_MAP`
- [Source: backend/src/modules/orchestrator/application/graph.py:131-174] — `real_rag_node` vector_search pgvector `<=>` (mẫu tiền-lọc embedding)
- [Source: backend/src/modules/ingestion/infrastructure/embedding_client.py:9,19-44] — `GeminiEmbeddingClient.embed_batch`, EMBEDDING_DIM=768, degraded zero-vector
- [Source: backend/src/modules/ingestion/infrastructure/chunk_orm_models.py:41-73] — `ChildChunkORM.embedding` Vector(768) (nguồn tiền-lọc)
- [Source: backend/src/shared/infra/llm/router.py:10-50] — `LLMRouter.get_llm_client(user_id, model_name)` user→system fallback
- [Source: backend/src/modules/workspace/infrastructure/orm_models.py:37-52] — `SyncOutboxORM` (event_type/project_id/payload/processed/retry/dead_lettered)
- [Source: backend/src/modules/admin/presentation/router.py] — `POST /admin/backfill-graph-extraction` (mẫu backfill-fills-gap)
- [Source: backend/alembic/versions/009_extend_sync_outbox_and_soft_delete.py] — migration mới nhất (down_revision cho 010)
- [Source: backend/src/modules/ingestion/infrastructure/graph_extractor.py:18-113] — `_parse_json`/`_coerce_to_text` (tái dùng cho FillsGapJudge)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed — comprehensive developer guide created (2026-06-21)
- Task 1: Thêm `list_unfilled_limitations` vào `graph_rag/application/use_cases.py` + Cypher `_CYPHER_UNFILLED_LIMITATION_FULL` trả limitation_id/description/owner_paper_id. Skip description rỗng. (2026-06-21)
- Task 2: Tạo `fills_gap_judge.py` — class `FillsGapJudge` với LLM judge `gemini-2.5-flash`, hằng ngưỡng module-level, `_parse_json`/`_coerce_to_text` pattern. 5 unit tests pass. (2026-06-21)
- Task 3: Tạo `fills_gap_orm.py` — `FillsGapJudgementORM` unique `(limitation_id, candidate_paper_id)`. Alembic migration `010_create_fills_gap_judgement_table.py` với `down_revision="009"`. (2026-06-21)
- Task 4: Tạo `fills_gap_task` trong `worker.py` — đọc Limitation từ Neo4j qua `list_unfilled_limitations`, embed qua `GeminiEmbeddingClient`, tiền lọc pgvector `<=>`, cache-check, judge, cache-write, emit FILLS_GAP. Thêm `_enqueue_fills_gap` best-effort + enqueue cuối `graph_extract_task`. Đăng ký `WorkerSettings.functions`. 5+1 unit tests pass. (2026-06-21)
- Task 5: Thêm `handle_fills_gap` vào `neo4j_adapter.py` — MERGE `[:FILLS_GAP]` scoped project_id, guard missing ids. Đăng ký `HANDLER_MAP["FILLS_GAP"]`. 3 unit tests pass. (2026-06-21)
- Task 6: Thêm `POST /admin/backfill-fills-gap` vào `admin/router.py` — mirror `backfill-graph-extraction`, distinct project_id, idempotent job_id. (2026-06-21)
- Toàn bộ 223 unit tests pass (không regression).

### File List

**Files mới:**
- backend/src/modules/ingestion/infrastructure/fills_gap_judge.py
- backend/src/modules/ingestion/infrastructure/fills_gap_orm.py
- backend/alembic/versions/010_create_fills_gap_judgement_table.py
- tests/unit/ingestion/test_fills_gap_judge.py
- tests/unit/ingestion/test_fills_gap_task.py

**Files cập nhật:**
- backend/worker.py
- backend/src/modules/graph_rag/application/use_cases.py
- backend/src/modules/graph_rag/infrastructure/neo4j_adapter.py
- backend/src/modules/admin/presentation/router.py
- tests/unit/graph_rag/test_consumer.py
- tests/unit/ingestion/test_graph_extract_task.py

### Change Log

- 2026-06-21: Story 4.7 triển khai — FILLS_GAP producer hoàn chỉnh: LLM judge + tiền lọc embedding + cache + handler Neo4j + admin backfill. 223 unit tests pass.

### Review Findings

**Code review 2026-06-21 (bmad-code-review — Blind Hunter + Edge Case Hunter + Acceptance Auditor).** 5 patch / 0 decision-needed / 0 defer / ~10 dismissed. Tất cả patch đã áp dụng & 42/42 test liên quan pass (244 pass toàn suite; chỉ còn lỗi SQLite ARRAY/isolation tiền-tồn ở identity/test_projects_api — KHÔNG liên quan, đã xác nhận pass khi chạy độc lập).

- [x] [Review][Patch] Concurrency: per-limitation `commit()` không bắt `IntegrityError` → khi 2 run song song (enqueue `_defer_by` vs admin backfill, `max_jobs=2`) cùng judge một cặp `uq_fills_gap_pair` thì commit raise, đầu độc session (`PendingRollbackError`) cuốn theo toàn bộ limitation còn lại của task [backend/worker.py:789] — FIX: bọc `try/except IntegrityError` → `rollback()` + continue (idempotent, run kia đã ghi cache+event).
- [x] [Review][Patch] LLM `reason` untrusted có thể là dict/list/int → ghi thẳng vào cột Text `fills_gap_judgement.reason` gây `DataError` lúc commit [fills_gap_judge.py:81] — FIX: ép `reason` về str an toàn (None→"", non-str→`str()`) trong `FillsGapJudge.judge`.
- [x] [Review][Patch] Regression test: `test_graph_extract_task_real_extractor_emits_cites` (CITES 4.6) bị xóa 4 assertion (payload `citing/cited_paper_id` + `commit.assert_awaited_once`) [tests/unit/ingestion/test_graph_extract_task.py:432] — FIX: khôi phục đủ 4 assertion (graph_extract_task vẫn commit đúng 1 lần).
- [x] [Review][Patch] Candidate lookup không lọc `is_deleted` (khác CITES producer 4.6) → có thể emit FILLS_GAP cho paper đã soft-delete nếu chunk sống sót [backend/worker.py:738] — FIX: thêm `PaperORM.is_deleted == False` (row None → skip).
- [x] [Review][Patch] Hiệu năng: dựng `candidate_text` ghép TOÀN BỘ ParentChunk rồi mới cắt `[:4000]` trong judge — lãng phí với mỗi cặp limitation×candidate [backend/worker.py:752] — FIX: tích lũy chunk, dừng sớm khi đạt `CANDIDATE_TEXT_LIMIT`.

**Dismissed (đã xác minh là false-positive / đúng thiết kế):** paper-id "type mismatch" (Neo4j `id` = Postgres `paper_id` đều là str-UUID, guard self-fill đúng) · `literal(vec, Vector(768))` (đúng pattern `real_rag_node`) · `redis.aclose()` (giống hệt `backfill-graph-extraction` sẵn có) · `handle_fills_gap` fallback bỏ scope khi thiếu `project_id` (Quyết định #9 cho phép — producer luôn gửi `project_id`) · `list_unfilled_limitations` nuốt lỗi Neo4j → `[]` (AC#1 bắt buộc, mirror `gap_detection`) · UUID-vs-str enqueue (job_id stringify giống nhau, vô hại).

---

**Phát hiện khi TEST THỦ CÔNG runtime (2026-06-21, sau review tĩnh).** Chạy thật end-to-end qua arq worker lộ ra bug mà cả 3 lớp review tĩnh + unit test đều không bắt được (unit test mock `db.execute`):

- [x] [Review][Patch][🔴 Runtime] `fills_gap_task` tiền-lọc pgvector: đưa `embedding.op("<=>")(query_vec)` vào **SELECT** (`.label("dist")`) khiến SQLAlchemy suy kiểu trả về = **Vector** (kế thừa cột) → bộ giải mã Vector subscript giá trị float Postgres trả về → `TypeError: 'float' object is not subscriptable` → task fail, 0 cạnh [backend/worker.py:708] — FIX: `op("<=>", return_type=Float)`. *Dòng này TRƯỚC ĐÓ không bao giờ chạy* vì mọi embedding bị degraded (xem mục hạ tầng) → bị skip ở guard `all(v==0.0)` trước khi tới query. `real_rag_node` không vướng vì chỉ dùng `<=>` trong ORDER BY (không SELECT). **Khoảng trống test:** chỉ integration test với pgvector thật mới bắt được — unit test hiện mock DB nên không phát hiện.

- [x] [Infra][ngoài phạm vi 4.7, nhưng là blocker] Model embedding `text-embedding-004` bị Google gỡ (404 NOT_FOUND) → **toàn bộ 2345 `child_chunks` là zero-vector** → tiền-lọc FILLS_GAP (và RAG chat) vô hiệu. Đã đổi sang `gemini-embedding-001` ở `output_dimensionality=768` (giữ schema `Vector(768)`, cosine `<=>` bất biến độ lớn nên không cần re-normalize) [embedding_client.py] + re-embed lại toàn corpus 2345 chunk. Đã verify model chạy với key hiện tại.

**Kết quả verify cuối:** 58 cặp judge (22 fills=true / 36 false) → 22 event `FILLS_GAP` (processed=t, 0 DLQ) → **22 cạnh `(:Paper)-[:FILLS_GAP]->(:Limitation)` trong Neo4j**, ngữ nghĩa hợp lý, 0 job lỗi. Idempotent 3 tầng + commit-một-phần hoạt động đúng.
