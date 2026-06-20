---
baseline_commit: e2723a4
---

# Story 4.6: [Backend] CITES Producer — Trích references & Khớp Paper (mở khóa "cụm cô lập")

Status: done

## Story

As a **kỹ sư backend của C2-App-053**,
I want **mở rộng Stage-2 ingestion (`graph_extract_task` + `GraphExtractor`) để trích danh sách references/trích dẫn của mỗi paper, khớp từng reference với Paper đã có trong CÙNG project (DOI exact → fuzzy title chuẩn hóa), rồi ghi sự kiện `CITES {citing_paper_id, cited_paper_id}` vào `sync_outbox` cho handler `handle_cites` (Story 4.1, ĐÃ CÓ) MERGE cạnh `[:CITES]` vào Neo4j**,
so that **Query 2 của `gap_detection` (cụm cô lập — Story 4.4) phản ánh khoảng trống THẬT: chỉ paper thực sự không nối với ai mới bị gắn cờ cô lập, thay vì TOÀN BỘ paper bị tô vàng vì đồ thị chưa từng có cạnh `[:CITES]` nào (handler có sẵn nhưng chưa có producer)**.

## Bối cảnh & Phạm vi

Story này là **[Backend] follow-up** (correct-course 2026-06-18) hiện thực hóa cạnh `[:CITES]` đã định nghĩa trong `architecture.md §5.2` nhưng chưa có producer. Đây là **nợ kỹ thuật**: comment trong [neo4j_adapter.py:128-132](backend/src/modules/graph_rag/infrastructure/neo4j_adapter.py#L128-L132) ghi rõ *"handler sẵn sàng nhưng chưa có producer ở MVP… Bảng papers không lưu danh sách references"*. Story này trả nợ đó.

**Nhãn module/role:**
- `[ingestion]` — **PRODUCER**: mở rộng `GraphExtractor.extract` (trích thêm `references`) + `graph_extract_task` (khớp reference→Paper + ghi event `CITES`). Tái dùng module mới `reference_matcher.py` (logic khớp thuần Python, dễ test).
- `[graph_rag]` — **CONSUMER**: handler `handle_cites` **ĐÃ TỒN TẠI và ĐÃ đăng ký** trong `HANDLER_MAP` (Story 4.1). **KHÔNG cần viết handler mới.** Chỉ cập nhật docstring lỗi thời.

**Phụ thuộc đã done:** Story 4.1 (handler `handle_cites` + `HANDLER_MAP` + outbox_worker dispatch), Story 4.3 (Stage-2 `graph_extract_task` + `GraphExtractor` để gắn vào), Story 4.4 (`gap_detection` Query 2 cụm cô lập — sẽ hưởng lợi).

**Ranh giới:**
- ✅ TRONG phạm vi: trích `references` trong `GraphExtractor` (cùng 1 lời gọi LLM, KHÔNG thêm call) · thuật toán khớp reference→Paper (DOI exact → fuzzy title `difflib` ≥ 0.85) trong `reference_matcher.py` · ghi event `CITES` trong `graph_extract_task` (idempotent, no self-cite) · cập nhật docstring `handle_cites` · unit tests.
- ❌ NGOÀI phạm vi: `FILLS_GAP` producer (Story 4.7) · tách màu gap FE (Story 4.8) · sửa logic `gap_detection`/`graph_search` (Story 4.4 — chỉ "đổ dữ liệu thật" vào, query không đổi) · tạo handler mới · sửa Alembic/schema DB (KHÔNG cột mới) · backfill toàn-corpus cho paper-cũ-cite-paper-mới (incremental, xem AC#7) · embedding-based title match (dùng `difflib` thuần, xem Quyết định #3).

### Quyết định kiến trúc đã chốt

1. **MỘT lời gọi LLM** — mở rộng `GRAPH_EXTRACTION_PROMPT` hiện có để trả thêm mảng `references`, KHÔNG thêm LLM call thứ 2 (chống lãng phí token `gemini-2.5-pro`). `references` được trích cùng lúc với ontology từ `text[:30000]`.
2. **Giới hạn truncation (chấp nhận, ghi rõ):** references thường nằm CUỐI bài; với bài > 30000 chars phần references có thể bị cắt → một số reference không trích được. MVP chấp nhận (đa số nội dung đã ingest là abstract + phần đầu; corpus nhỏ `MAX_PAPERS_PER_PROJECT=15`). Mitigation nhẹ: nếu `full_text` chứa heading references → đảm bảo đưa slice đó vào (xem AC#2). KHÔNG dựng pipeline parse PDF riêng.
3. **Khớp title bằng `difflib.SequenceMatcher` (stdlib), KHÔNG embedding.** Lý do: candidate ≤ 15 paper/project → brute-force O(refs×papers) cực rẻ; tránh thêm lời gọi `text-embedding-004` (chi phí + độ phức tạp). Ngưỡng `ratio ≥ 0.85` trên title đã chuẩn hóa. AC#3 cho phép cosine nhưng **chốt `difflib`** cho MVP — đơn giản, deterministic, test offline được.
4. **Matching deterministic ở Python** (`reference_matcher.py`), KHÔNG nhờ LLM khớp (LLM chỉ trích references thô). Tách bạch: LLM = trích, Python = khớp → test độc lập, không tốn token cho matching.
5. **Producer ghi event trong CÙNG `graph_extract_task`**, cùng transaction với `ONTOLOGY_EXTRACTED` (1 commit). Mỗi cạnh khớp = 1 `SyncOutboxORM(event_type="CITES")`.
6. **Idempotent toàn tuyến:** re-run task (backfill) re-emit `CITES` events → handler MERGE không nhân đôi cạnh (nhất quán hành vi `ONTOLOGY_EXTRACTED`). Outbox có thể có event trùng — chấp nhận như các event khác.
7. **Chỉ query candidate papers KHI có references** (`references` rỗng → KHÔNG chạy query DB thứ 3). Giữ no-op an toàn VÀ tránh phá test 4.3 hiện có (xem §Regression bắt buộc).

## Acceptance Criteria

### A. [ingestion] Trích references trong `GraphExtractor`

1. Mở rộng `GRAPH_EXTRACTION_PROMPT` ([graph_extractor.py:18-66](backend/src/modules/ingestion/infrastructure/graph_extractor.py#L18)) thêm mảng `references` vào JSON schema + rule:
   ```json
   "references": [
     {"title": "Cited paper title", "doi": "10.xxxx/yyyy", "year": 2020}
   ]
   ```
   - Rule: *"references: extract the list of works CITED by this paper from its References/Bibliography section. Each: title (required), doi (if present, else null/omit), year (if present). Empty array [] if no reference section found. Do NOT invent references."*
   - `doi`/`year` optional; `title` bắt buộc — reference thiếu title → bỏ (xem AC#3).

2. `GraphExtractor.extract` trả dict có thêm key `references` (list). Điều chỉnh kiểm tra "có nội dung":
   - Hiện tại `has_entity = any(data.get(k) for k in _ENTITY_KEYS)` → trả `None` nếu rỗng. **Mở rộng:** paper chỉ có `references` (không ontology) vẫn hợp lệ. Đưa `references` vào điều kiện non-empty HOẶC giữ `references` sống sót khi có ontology. **Tối thiểu:** khi `extract` trả dict, `references` (nếu LLM trả) phải nằm trong dict đó. Nếu muốn paper references-only vẫn produce CITES → thêm điều kiện `or data.get("references")`.
   - Nếu LLM không trả `references` → mặc định `[]` (graceful, không KeyError).

3. (Trong worker, dùng `reference_matcher`) Mỗi reference được CHUẨN HÓA + VALIDATE: bỏ reference không có `title` (str non-empty sau strip). `doi`/`year` để nguyên cho matcher.

### B. [ingestion] Module khớp `reference_matcher.py`

4. Tạo `backend/src/modules/ingestion/infrastructure/reference_matcher.py` — hàm thuần (không I/O, không async), dễ unit test:
   - `normalize_title(s: str) -> str`: lowercase → `unicodedata.normalize("NFKD")` bỏ dấu → bỏ ký tự không phải `[a-z0-9 ]` → gộp khoảng trắng. (Trả "" nếu input rỗng.)
   - `normalize_doi(s: str | None) -> str | None`: lowercase, strip, bỏ tiền tố `https://doi.org/` / `http://dx.doi.org/` / `doi:`. Trả `None` nếu rỗng.
   - `match_reference(ref: dict, candidates: list[dict]) -> str | None`: `candidates` là list `{"id", "title", "doi"}` của các Paper khác trong project. Thứ tự khớp:
     1. **DOI exact:** nếu `normalize_doi(ref.doi)` non-empty và bằng `normalize_doi(cand.doi)` của một candidate → trả `cand.id`.
     2. **Fuzzy title:** chọn candidate có `difflib.SequenceMatcher(None, normalize_title(ref.title), normalize_title(cand.title)).ratio()` cao nhất; nếu `ratio ≥ 0.85` → trả `cand.id`. (Normalized-title bằng nhau ⇒ ratio = 1.0, tự bao gồm.)
     3. Không thỏa → trả `None` (KHÔNG tạo Paper ma).
   - Ngưỡng `TITLE_MATCH_THRESHOLD = 0.85` là hằng module-level (dễ chỉnh).

### C. [ingestion] Producer event `CITES` trong `graph_extract_task`

5. Mở rộng `graph_extract_task` ([worker.py:439-537](backend/worker.py#L439)) — SAU khi build/commit `ONTOLOGY_EXTRACTED` (hoặc trong cùng khối, cùng 1 `db.commit()`):
   - Lấy `references = data.get("references") or []`; lọc bỏ ref thiếu `title`.
   - **Nếu `references` rỗng → BỎ QUA hoàn toàn** (không query DB candidate, không ghi event). Log `info` "0 references".
   - Nếu có references: query candidate papers CÙNG project, KHÁC chính nó, chưa xóa:
     ```python
     cand_result = await db.execute(
         select(PaperORM.id, PaperORM.title, PaperORM.doi)
         .where(
             PaperORM.project_id == paper.project_id,
             PaperORM.id != paper_id,
             PaperORM.is_deleted == False,  # noqa: E712
         )
     )
     candidates = [{"id": r.id, "title": r.title, "doi": r.doi} for r in cand_result.all()]
     ```
   - Với mỗi reference: `cited_id = match_reference(ref, candidates)`. Bỏ qua nếu `None` hoặc `cited_id == paper_id` (no self-cite). Gom `matched: set[str]` (dedup nhiều reference khớp cùng 1 paper).

6. Mỗi `cited_id` trong `matched` → `db.add(SyncOutboxORM(event_type="CITES", project_id=paper.project_id, payload={"citing_paper_id": paper_id, "cited_paper_id": cited_id}))`. Commit cùng transaction với `ONTOLOGY_EXTRACTED` (một `await db.commit()`).
   - Log `info`: số reference trích được / số khớp / số không khớp (quan sát chất lượng matching). VD: `"graph_extract_task: paper %s — %d references, %d matched CITES"`.

7. **Forward-compat / giới hạn backfill (ghi rõ trong log/notes):** task chỉ khớp references của paper ĐANG xử lý với papers ĐÃ TỒN TẠI lúc đó. Paper cũ trích dẫn paper mới-thêm-sau sẽ KHÔNG tự cập nhật cạnh. Cách lấp: admin chạy lại `POST /api/admin/backfill-graph-extraction` (Story 4.3, ĐÃ CÓ — re-enqueue `graph_extract_task` cho mọi paper indexed) → references được khớp lại trên tập papers đầy đủ. Idempotent nên an toàn. **KHÔNG cần viết backfill mới.**

### D. [graph_rag] Handler `handle_cites` — chỉ cập nhật docstring (KHÔNG đổi logic)

8. `handle_cites` ([neo4j_adapter.py:128-145](backend/src/modules/graph_rag/infrastructure/neo4j_adapter.py#L128)) ĐÃ MERGE `[:CITES]` idempotent và ĐÃ ở `HANDLER_MAP["CITES"]`. **KHÔNG sửa logic Cypher.** Chỉ cập nhật docstring lỗi thời (dòng 129-132 ghi "chưa có producer ở MVP") → ghi rằng producer hiện ở Story 4.6 (`graph_extract_task`). Giữ guard `if not citing_id or not cited_id` hiện có.

### E. Tests

9. `tests/unit/ingestion/test_reference_matcher.py` (module thuần — phủ kỹ):
   - `test_normalize_title_strips_diacritics_punct_case`: "Đánh Giá: Mô-hình AI!" → "danh gia mohinh ai" (hoặc tương đương ổn định) — assert lowercase, không dấu, không ký tự đặc biệt.
   - `test_normalize_doi_strips_prefix`: "https://doi.org/10.1/AbC" → "10.1/abc"; `None`/"" → `None`.
   - `test_match_by_doi_exact`: ref.doi khớp candidate.doi (khác hoa thường/tiền tố) → trả đúng id.
   - `test_match_by_fuzzy_title_above_threshold`: title gần giống (ratio ≥ 0.85) → khớp; title khác hẳn → `None`.
   - `test_match_returns_none_when_no_candidate`: candidates rỗng → `None`.
   - `test_match_prefers_doi_over_title`: DOI khớp candidate A nhưng title gần candidate B → trả A.
   - `test_match_ignores_missing_title_or_doi`: ref không title → matcher xử lý an toàn (hàm worker lọc trước; matcher với title rỗng → `None`).

10. `tests/unit/ingestion/test_graph_extract_task.py` (MỞ RỘNG file hiện có — xem §Regression):
    - `test_graph_extract_task_emits_cites_on_match`: paper indexed; `GraphExtractor.extract` mock trả dict có `references=[{title: "X"}]`; candidate paper trong DB có title "X" → `SyncOutboxORM(event_type="CITES")` được `db.add` với payload đúng `{citing_paper_id, cited_paper_id}`.
    - `test_graph_extract_task_no_cites_when_no_references`: extract trả dict KHÔNG có `references` (hoặc `[]`) → KHÔNG query candidate, KHÔNG add CITES event (chỉ ONTOLOGY_EXTRACTED).
    - `test_graph_extract_task_skips_self_cite`: reference khớp về CHÍNH paper đang xử lý → không add CITES.
    - `test_graph_extract_task_skips_unmatched_reference`: reference không khớp candidate nào → không add CITES (không tạo paper ma).
    - (Giữ nguyên 3 test cũ pass: skip deleted/non-indexed, write ontology event.)

11. (Tùy chọn, nếu chưa có) bổ sung `tests/unit/graph_rag/test_consumer.py` hoặc test handler: `test_handle_cites_merges_edge` — mock session, payload `{citing_paper_id, cited_paper_id}` → query chứa "MERGE" + "CITES". (Nếu Story 4.1 đã có test này thì BỎ QUA — kiểm tra trước, không trùng.)

## Tasks / Subtasks

- [x] **Task 1 — [ingestion] Trích references trong GraphExtractor** (AC: 1,2,3)
  - [x] Thêm `references` vào `GRAPH_EXTRACTION_PROMPT` (schema + rule "do NOT invent")
  - [x] `extract()` trả dict gồm `references` (mặc định `[]` nếu LLM bỏ sót); điều chỉnh điều kiện non-empty cho paper references-only (AC#2)
  - [x] (Không thêm LLM call mới — cùng 1 `ainvoke`)

- [x] **Task 2 — [ingestion] Module `reference_matcher.py`** (AC: 4)
  - [x] `normalize_title`, `normalize_doi`, `match_reference` + hằng `TITLE_MATCH_THRESHOLD=0.85`
  - [x] Dùng `unicodedata` + `difflib` (stdlib, KHÔNG thêm dependency)
  - [x] Unit tests `tests/unit/ingestion/test_reference_matcher.py` (AC: 9)

- [x] **Task 3 — [ingestion] Producer CITES trong graph_extract_task** (AC: 5,6,7)
  - [x] Sau ontology: lọc references có title; rỗng → bỏ qua (không query thứ 3)
  - [x] Query candidate papers (project scope, ≠ self, chưa xóa) — CHỈ khi có references
  - [x] `match_reference` từng ref → gom `matched` set; bỏ self-cite
  - [x] `db.add(SyncOutboxORM("CITES", ...))` cho mỗi match; 1 commit chung; log matched/unmatched
  - [x] MỞ RỘNG `tests/unit/ingestion/test_graph_extract_task.py` (AC: 10) — sửa `_make_db` để cấp result thứ 3 (candidates)

- [x] **Task 4 — [graph_rag] Cập nhật docstring handle_cites** (AC: 8)
  - [x] Sửa docstring dòng 129-132 (producer nay ở Story 4.6); KHÔNG đổi Cypher/guard
  - [x] Kiểm tra test handler CITES đã có chưa (AC: 11) — chỉ thêm nếu thiếu

## Dev Notes

### Kiến trúc & ràng buộc bắt buộc

- **Hexagonal §9.5/§9.6:** `GraphExtractor` + `reference_matcher` ở `ingestion/infrastructure/` (driven adapter / pure logic). Orchestrate ở `graph_extract_task` (`worker.py` = composition root ingestion, được phép gọi infra + ghi `SyncOutboxORM`). `graph_rag` CONSUME qua `HANDLER_MAP`. **KHÔNG** gọi `neo4j_adapter` từ ingestion; **KHÔNG** sửa `HANDLER_MAP` từ `worker.py`.
- **Role-clarity (epics.md §Ma trận):** `ingestion` = **PRODUCER** duy nhất ghi `sync_outbox`; `graph_rag` = **CONSUMER**. Story 4.6 đúng nguyên tắc: producer đặt ở ingestion, handler đã ở graph_rag.
- **IDOR/scope:** query candidate papers PHẢI lọc `project_id == paper.project_id`. Handler Cypher `MATCH (a:Paper {id}), (b:Paper {id})` đã scope theo id paper trong project (id là UUID toàn cục, an toàn).
- **Không dependency mới:** chỉ `unicodedata` + `difflib` (stdlib). KHÔNG thêm lib fuzzy (rapidfuzz/thefuzz).

### 🚨 Regression bắt buộc — `test_graph_extract_task.py` `_make_db`

`_make_db` hiện dùng `db.execute = AsyncMock(side_effect=[paper_result, chunk_result])` — **đúng 2 lần execute**. Story 4.6 thêm execute THỨ 3 (query candidates) **khi có references**.
- Các test cũ mock `extract` trả ontology KHÔNG có `references` → nhánh "references rỗng" → KHÔNG execute lần 3 → **3 test cũ vẫn pass nếu code skip query khi references rỗng** (chính là AC#7/Quyết định #7 — lý do chốt thiết kế này).
- Test MỚI có references → phải mở rộng `_make_db` cấp `side_effect=[paper_result, chunk_result, cand_result]`. Cập nhật helper để nhận `candidates` optional.
- **Xác minh:** chạy `pytest tests/unit/ingestion/test_graph_extract_task.py` thấy 3 test cũ + test mới đều pass.

### Pattern code tái dùng

- **Mở rộng prompt + parse:** `extract()` đã có `_parse_json` (strip code fence + fallback cắt `{...}`) → `references` tự được parse cùng dict. Không cần parser riêng.
- **Ghi outbox:** mẫu ở `graph_extract_task` ([worker.py:517-535](backend/worker.py#L517)) — `SyncOutboxORM(event_type=..., project_id=..., payload={...})` rồi `db.add` + `db.commit`. Import `SyncOutboxORM` đã có sẵn ([worker.py:43](backend/worker.py#L43)).
- **Query papers (id+title+doi):** dùng `select(PaperORM.id, PaperORM.title, PaperORM.doi)` (chỉ cột cần, mirror tối ưu select-id của review 4.3). `PaperORM` đã import trong `worker.py`.
- **Test handler Cypher:** mẫu `test_consumer.py` — `session.run = AsyncMock(side_effect=lambda q,**k: queries.append(q))`, assert `any("MERGE" in q)`.
- **Test task:** `_FakeSessionFactory` + `_make_paper` + `_make_db` đã có trong [test_graph_extract_task.py:10-57](tests/unit/ingestion/test_graph_extract_task.py#L10). `ctx = {"session_factory": ..., "redis": AsyncMock()}`. Mock `GraphExtractor` qua `patch("backend.worker.GraphExtractor")`, set `MockExtractor.return_value.extract = AsyncMock(return_value={...})`.

### PaperORM (nguồn dữ liệu khớp)

[orm_models.py:10-49](backend/src/modules/ingestion/infrastructure/orm_models.py#L10): `id` (UUID str), `title` (String500, non-null), `doi` (String200, nullable), `project_id`, `is_deleted`, `status`. Candidate = paper bất kỳ trong project (kể cả `metadata_only` / `indexed`) trừ chính nó và đã-xóa. Reference khớp theo title/doi của các paper này.

### Mẫu reference_matcher (tham khảo)

```python
import difflib
import re
import unicodedata

TITLE_MATCH_THRESHOLD = 0.85
_DOI_PREFIXES = ("https://doi.org/", "http://dx.doi.org/", "https://dx.doi.org/", "doi:")

def normalize_title(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def normalize_doi(s: str | None) -> str | None:
    if not s:
        return None
    s = s.strip().lower()
    for p in _DOI_PREFIXES:
        if s.startswith(p):
            s = s[len(p):]
    return s or None

def match_reference(ref: dict, candidates: list[dict]) -> str | None:
    ref_doi = normalize_doi(ref.get("doi"))
    if ref_doi:
        for c in candidates:
            if normalize_doi(c.get("doi")) == ref_doi:
                return c["id"]
    ref_title = normalize_title(ref.get("title", ""))
    if not ref_title:
        return None
    best_id, best_ratio = None, 0.0
    for c in candidates:
        r = difflib.SequenceMatcher(None, ref_title, normalize_title(c.get("title", ""))).ratio()
        if r > best_ratio:
            best_id, best_ratio = c["id"], r
    return best_id if best_ratio >= TITLE_MATCH_THRESHOLD else None
```

### Learnings từ Story 4.3 (áp dụng vào 4.6)

- **`enqueue`/commit sau lỗi:** Story 4.3 bọc `_enqueue_graph_extract` best-effort để lỗi enqueue không lật paper `indexed`→`failed`. Story 4.6 chỉ THÊM `db.add` trước cùng `commit` đã có — nếu lỡ lỗi commit, cả ontology lẫn CITES rớt cùng nhau (atomic), backfill tự lành. KHÔNG cần try/except riêng cho CITES.
- **Guard `.get()` cho payload từ LLM:** handler 4.3 từng KeyError khi thiếu `id`. Với 4.6, lọc reference thiếu `title` Ở PRODUCER (worker) trước khi matching → handler `CITES` chỉ nhận `{citing_paper_id, cited_paper_id}` do code mình kiểm soát (không phải raw LLM) → an toàn.
- **JSON fence/prose:** `_parse_json` đã xử lý; `references` hưởng lợi sẵn.
- **Self-loop:** 4.3 guard `new_from == new_to`. 4.6 tương tự guard `cited_id == paper_id` (no self-cite).
- **Pre-existing failures:** `tests/unit/identity/*` + `test_projects_api.py` có lỗi SQLite ARRAY/isolation — KHÔNG liên quan, KHÔNG debug.

### Learnings từ Story 4.1 (handler + outbox đã có)

- `handle_cites` MERGE `(a:Paper)-[:CITES]->(b:Paper)` idempotent, đã ở `HANDLER_MAP["CITES"]` ([neo4j_adapter.py:328-332](backend/src/modules/graph_rag/infrastructure/neo4j_adapter.py#L328)).
- `outbox_worker` dispatch theo `HANDLER_MAP.get(event_type)` ([outbox_worker.py:169](backend/src/modules/graph_rag/infrastructure/outbox_worker.py#L169)); event lạ → WARN + retry. Vì `CITES` ĐÃ có handler, event sẽ được xử lý ngay (không DLQ).
- Thứ tự outbox theo `id.asc()`: `PAPER_UPSERTED` (tạo node Paper) luôn sync TRƯỚC `CITES` của paper sau → `MATCH (a),(b)` tìm thấy cả 2 node. Nếu cited paper chưa kịp sync, MERGE không tạo cạnh (MATCH rỗng) — nhưng backfill/run-sau tự lành. Ghi rõ là chấp nhận được.

### Project Structure Notes

**Files MỚI:**
```
backend/src/modules/ingestion/infrastructure/reference_matcher.py   # normalize/match thuần Python
tests/unit/ingestion/test_reference_matcher.py                       # AC: 9
```

**Files CẬP NHẬT:**
```
backend/src/modules/ingestion/infrastructure/graph_extractor.py   # +references vào prompt + dict (AC:1,2)
backend/worker.py                                                  # graph_extract_task: +query candidates +emit CITES (AC:5,6,7)
backend/src/modules/graph_rag/infrastructure/neo4j_adapter.py     # CHỈ docstring handle_cites (AC:8)
tests/unit/ingestion/test_graph_extract_task.py                   # mở rộng _make_db + test CITES (AC:10)
```

**KHÔNG SỬA:** logic Cypher `handle_cites` · `HANDLER_MAP` (CITES đã có) · `outbox_worker.py` · Alembic/schema (không cột mới) · `gap_detection`/`graph_search` (Story 4.4 — query không đổi) · admin backfill endpoint (Story 4.3 đã re-enqueue được) · FE · `ingest_paper_task` (điểm enqueue 4.3 không đổi).

### References

- [Source: architecture.md §5.2] — Graph Schema Phase 1: Edge `[:CITES]` (mạng lưới trích dẫn) giữa Paper nodes
- [Source: architecture.md §3.5 / line 34] — "Bản đồ Tri thức: vẽ mạng lưới trích dẫn và tác giả"
- [Source: sprint-change-proposal-2026-06-18-cites-fillsgap-producers.md §1,§4.A] — Vấn đề "mọi node vàng" + AC nháp Story 4.6 (handler có, producer không); thứ tự 4.8→4.6→4.7
- [Source: epics.md §Story 4.6] — Phạm vi CITES producer, phụ thuộc 4.1/4.3, FR7/FR9
- [Source: backend/src/modules/graph_rag/infrastructure/neo4j_adapter.py:128-145] — `handle_cites` (đã MERGE idempotent, docstring "chưa có producer" cần cập nhật)
- [Source: backend/src/modules/graph_rag/infrastructure/neo4j_adapter.py:328-332] — `HANDLER_MAP["CITES"]` đã đăng ký
- [Source: backend/worker.py:439-537] — `graph_extract_task` Stage-2: điểm chèn producer CITES (sau ONTOLOGY_EXTRACTED, cùng commit)
- [Source: backend/src/modules/ingestion/infrastructure/graph_extractor.py:18-113] — `GRAPH_EXTRACTION_PROMPT` + `extract()` để thêm `references`; `_parse_json` tái dùng
- [Source: backend/src/modules/ingestion/infrastructure/orm_models.py:10-49] — `PaperORM` (id/title/doi/project_id/is_deleted) — nguồn candidate matching
- [Source: tests/unit/ingestion/test_graph_extract_task.py:10-70] — `_FakeSessionFactory`/`_make_db`/`_make_paper` (mở rộng cho execute thứ 3)
- [Source: tests/unit/graph_rag/test_consumer.py] — pattern test Cypher handler (mock `session.run`)
- [Source: 4-3-graph-extraction-trich-xuat-ontology-hoc-thuat.md] — Stage-2 design, learnings (enqueue best-effort, guard `.get()`, self-loop, JSON fence)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed — comprehensive developer guide created (2026-06-18)
- Task 1: Mở rộng GRAPH_EXTRACTION_PROMPT thêm schema `references` + rule "do NOT invent references". `extract()` đã setdefault `references=[]` + điều kiện non-empty bao gồm `or bool(data.get("references"))`.
- Task 2: Tạo `reference_matcher.py` với `normalize_title`, `normalize_doi`, `match_reference` (difflib+unicodedata stdlib). 17 unit tests pass.
- Task 3: Mở rộng `graph_extract_task` — sau ONTOLOGY_EXTRACTED: lọc refs có title, query candidates (project-scoped), match từng ref, gom `matched` set (dedup + no-self-cite), `db.add(SyncOutboxORM("CITES", ...))` cho từng match, commit 1 lần. Log matched/unmatched. Refactor `_make_db` helper cấp execute thứ 3 optional. 5 test CITES mới pass, 5 test cũ vẫn pass.
- Task 4: Cập nhật docstring `handle_cites` (không còn ghi "chưa có producer"). Thêm `test_handle_cites_merges_edge` + `test_handle_cites_skips_when_missing_ids` vào `test_consumer.py`. 14 tests pass.
- Toàn bộ 127 tests ingestion + graph_rag pass, không regression.

### File List

- backend/src/modules/ingestion/infrastructure/graph_extractor.py (modified)
- backend/src/modules/ingestion/infrastructure/reference_matcher.py (new)
- backend/worker.py (modified)
- backend/src/modules/graph_rag/infrastructure/neo4j_adapter.py (modified — docstring only)
- tests/unit/ingestion/test_reference_matcher.py (new)
- tests/unit/ingestion/test_graph_extract_task.py (modified)
- tests/unit/graph_rag/test_consumer.py (modified)
- _bmad-output/implementation-artifacts/sprint-status.yaml (modified)
- _bmad-output/implementation-artifacts/4-6-cites-producer-trich-references-khop-paper.md (modified)

### Change Log

- 2026-06-18: Triển khai CITES producer — trích references trong GraphExtractor, module reference_matcher (DOI exact + fuzzy title difflib), producer event CITES trong graph_extract_task, cập nhật docstring handle_cites, tests đầy đủ (127 pass).

### Review Findings

**Code review 2026-06-18** (3 lớp đối kháng: Blind Hunter + Edge Case Hunter + Acceptance Auditor). Kết quả: 1 patch (Critical) đã sửa, 1 defer, phần còn lại by-design/noise. Acceptance Auditor xác nhận **toàn bộ AC#1–11 PASS** và 7 quyết định kiến trúc + ràng buộc hexagonal/role-clarity được tuân thủ.

- [x] [Review][Patch] Crash khi LLM trả `references` có `title: null` hoặc entry không phải dict [backend/worker.py:539] — `r.get("title", "").strip()` ném `AttributeError` (None/str không có `.strip`/`.get`), cuốn theo cả commit `ONTOLOGY_EXTRACTED` (không try/except). **Đã sửa:** lọc `isinstance(r, dict) and (r.get("title") or "").strip()` + test `test_graph_extract_task_tolerates_malformed_references`. Cả 3 lớp đều flag (Critical).
- [x] [Review][Defer] Fuzzy title `difflib` 0.85 dễ false-positive với title ngắn/chung [backend/src/modules/ingestion/infrastructure/reference_matcher.py:416] — title chuẩn hóa ngắn ("conclusion", một năm) có thể khớp nhầm → cạnh CITES sai, che lấp gap thật. **Defer:** thuật toán + ngưỡng 0.85 do AC#4/Quyết định #3 CHỐT cho MVP (corpus ≤15 paper, title bibliography thường đầy đủ); thêm guard độ dài = lệch spec. Xem lại Phase 2 nếu quan sát thấy cạnh sai.

**Dismissed (by-design / đã ghi rõ trong Dev Notes, hoặc unreachable):**
- CITES rớt im lặng khi Paper node chưa kịp sync sang Neo4j → đã ghi "chấp nhận được, backfill tự lành" (Dev Notes §Learnings 4.1).
- Cạnh CITES xuyên project → `id` là UUID toàn cục, an toàn (Dev Notes §IDOR).
- Guard `cited_id == paper_id` là dead code (query đã lọc `id != paper_id`) → vô hại, giữ lại làm defensive.
- Log `unmatched` đếm gộp self-cite/dedup → chỉ sai số quan sát, không sai hành vi.
- `match_reference` `c["id"]` KeyError nếu candidate thiếu `id` → producer luôn cấp `id`, unreachable.
- Nondeterminism khi 2 paper trùng DOI/title (first-wins) → edge case hiếm, corpus nhỏ.
