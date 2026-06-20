---
baseline_commit: e2723a4
---

# Story 4.9: [Backend+FE] Sửa cắt text khi parse — kích hoạt References/CITES thật + đưa giới hạn parse vào Admin Setting

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **nhà nghiên cứu dùng C2-App-053**,
I want **các cạnh "Trích dẫn" (CITES) thực sự hiện ra giữa các paper trên Bản đồ Tri thức, thay vì mọi paper đều bị cô lập**,
so that **tôi nhìn đúng mạng lưới trích dẫn của corpus và Query 2 (gap "cụm cô lập", Story 4.4) chỉ cảnh báo những paper thật sự không có kết nối — hiện thực hóa giá trị mà Story 4.6 (CITES Producer) lẽ ra phải mang lại**.

## Bối cảnh & Phạm vi

Story này **vá một lỗ hổng tích hợp** lộ ra sau khi Story 4.6 (CITES Producer) được đánh dấu `done`: Bản đồ Tri thức **không vẽ một cạnh CITES nào**, mọi paper hiện ra như cụm cô lập (tô vàng), dù 6 paper GMO trong project trích dẫn lẫn nhau.

**Nguyên nhân gốc (đã xác minh trên dữ liệu thật `data/papers/`):** danh mục References/Tài liệu tham khảo **không bao giờ tới được LLM**, nên `GraphExtractor` trả `references=[]` → `graph_extract_task` log `"0 references, bỏ qua CITES"` → 0 event CITES → 0 cạnh Neo4j. **Logic Story 4.6 đúng**; defect nằm ở **hai chỗ thắt cổ chai trên đường dẫn text**:

1. **`DocumentParser` cắt PDF còn 2 trang đầu / 4000 ký tự.** References luôn nằm cuối bài (offset thực tế 11k–45k ký tự trên 6 paper khảo sát) → bị cắt sạch bởi mốc 4000.
2. **`GraphExtractor._build_extraction_text` chỉ lấy `head[:30000] + đuôi 8000 ký tự`.** Với paper 134k ký tự, References@37.540: `head` kết thúc @30.000, `tail` bắt đầu @126.387 → mục References rơi vào **khoảng trống giữa head và tail**, vẫn mất kể cả khi đã sửa #1.

**Vì sao test 4.6 không bắt được:** test mock `GraphExtractor.extract` trả sẵn `references=[...]`, nên cả hai mốc cắt text thật không bao giờ chạy trong test → lỗ hổng tích hợp vô hình. **Story này PHẢI có test tích hợp KHÔNG mock parser/extractor (AC#5).**

**Nhãn module/role (3 trục: module=nơi code / epic=value / story=slice xuyên-module):**
- `[ingestion]` — sửa `DocumentParser` (tham số hóa), bỏ cắt head/đuôi trong `GraphExtractor`, `worker` đọc & áp dụng setting.
- `[admin]` — thêm 2 key số nguyên vào `_NUMERIC_SETTING_KEYS`.
- `[frontend]` — Admin Settings hiển thị + lưu 2 input mới (i18n VI/EN).

**Phụ thuộc (đều `done`):** Story 4.6 (producer CITES — giữ nguyên), Story 4.3 (Stage-2 worker + endpoint backfill), hạ tầng `system_settings` của Story 4.1.

**FRs:** FR7, FR9. **ARCH:** §5.2 (`[:CITES]`), §6.2 (pipeline Stage-1/2), §7 (Dynamic Settings).

**Nguồn chính:** [`sprint-change-proposal-2026-06-19-cites-references-truncation.md`](../planning-artifacts/sprint-change-proposal-2026-06-19-cites-references-truncation.md) — đọc Section 4 (EP-1…EP-9) để biết từng chỉnh sửa chi tiết.

### Quyết định kiến trúc đã chốt (KHÔNG bàn lại)

- **2 setting động** (số nguyên ≥1), giá trị đã duyệt trên dữ liệu thật:

  | Key | Default | Ý nghĩa |
  |---|---|---|
  | `INGEST_MAX_PDF_PAGES` | **50** | Số trang PDF tối đa parse ở worker ingestion (cũ: hardcode 2 / 20) |
  | `INGEST_MAX_EXTRACT_CHARS` | **150000** | Số ký tự text tối đa giữ lại sau parse (cũ: 4000). **Cũng là** cận trên lượng text gửi LLM ở Stage-2 |

  50 / 150.000 phủ toàn bộ corpus hiện tại (cả 6 paper GMO có References @offset ≤45.195 < 150.000).
- **BỎ tham số thứ 3 `INGEST_GRAPH_REF_TAIL_CHARS` và BỎ luôn cơ chế cắt head/đuôi** trong `GraphExtractor` (Quyết định Dat 2026-06-19). Vì `INGEST_MAX_EXTRACT_CHARS` đã chặn tổng text ở Stage-1 → gửi thẳng `full_text` cho LLM thì References luôn lọt, không còn "khoảng trống giữa head và đuôi". Đơn giản hơn, đúng ý "2 tham số vào Admin".
- **KHÔNG cần Alembic migration** — bảng `system_settings` đã tồn tại; default cấp qua `get_setting(..., default=...)`.
- **KHÔNG rollback Story 4.6**, KHÔNG đụng PRD/UX, KHÔNG đổi MVP scope.
- **default tham số parser = giá trị CŨ (2 / 4000)** → đường upload-metadata ([use_cases.py:146](../../backend/src/modules/ingestion/application/use_cases.py#L146), chỉ cần title/abstract đầu bài) giữ nguyên hành vi rẻ; **chỉ worker ingestion mới opt-in** giá trị lớn từ Admin.

## Acceptance Criteria

### A. [ingestion] `DocumentParser` — tham số hóa giới hạn (giữ default cũ)

1. `extract_text(file_path, mime_type, max_pages=2, max_chars=4000)` truyền `max_pages`/`max_chars` xuống `_extract_pdf`/`_extract_docx`.
   - `_extract_pdf` dùng `range(min(max_pages, len(doc)))` + `return text[:max_chars]`.
   - `_extract_docx` dùng `return result.value[:max_chars]`.
   - **Default 2/4000 giữ nguyên hành vi cũ** cho mọi caller chưa truyền tham số (đặc biệt đường upload-metadata).
   - Hằng module `MAX_TEXT_LENGTH = 4000` thay bằng `DEFAULT_MAX_PAGES = 2` / `DEFAULT_MAX_CHARS = 4000` (hoặc default ngay trong signature).

### B. [admin] 2 setting động mới

2. Thêm `"INGEST_MAX_PDF_PAGES"` và `"INGEST_MAX_EXTRACT_CHARS"` vào `_NUMERIC_SETTING_KEYS` ([router.py:24](../../backend/src/modules/admin/presentation/router.py#L24)). Validator hiện có (ép số nguyên ≥1) tự áp dụng — KHÔNG cần code validate riêng. KHÔNG cần migration.

### C. [ingestion] `worker.py` — đọc & áp dụng cả 2 đường PDF

3. `_extract_text(paper, session_factory)` đọc 2 setting **một lần** (từ `system_settings`, fallback default 50/150000 nếu thiếu/sai kiểu) rồi:
   - Đường file local: `DocumentParser().extract_text(paper.file_path, mime_type, max_pages=max_pages, max_chars=max_chars)`.
   - Đường download: `_download_and_persist_pdf(..., max_pages=max_pages, max_chars=max_chars)`.
   - `_download_and_persist_pdf`: thay [worker.py:253](../../backend/worker.py#L253) `range(min(len(doc), 20))` → `range(min(len(doc), max_pages))` và `return text` → `return text[:max_chars]`.
   - Đọc setting bọc `try/except`/guard `int(...)` → giá trị Admin sai kiểu KHÔNG làm hỏng job, lùi về default an toàn.

### D. [ingestion] `GraphExtractor` — bỏ cắt head/đuôi, gửi thẳng full_text

4. **Gỡ toàn bộ** `_build_extraction_text` + các hằng `_EXTRACT_HEAD` / `_REF_TAIL_BUDGET` / `_REF_HEADINGS` ([graph_extractor.py:74-106](../../backend/src/modules/ingestion/infrastructure/graph_extractor.py#L74-L106)). Trong `extract()`, `prompt = GRAPH_EXTRACTION_PROMPT.format(..., text=text)` — truyền thẳng `text` (đã bị `INGEST_MAX_EXTRACT_CHARS` chặn ở Stage-1). KHÔNG còn trimming nội bộ.

### E. Tests — chống tái lỗ hổng (BẮT BUỘC, không mock parser/extractor)

5. **Test tích hợp KHÔNG mock `GraphExtractor`/`DocumentParser`:** fixture nhiều trang có mục References ở offset **>30000** (vượt mốc head cũ).
   - `test_document_parser`: gọi `extract_text(max_pages=50, max_chars=150000)` lấy >2 trang & giữ phần References; **default vẫn 2/4000** (regression).
   - `test_graph_extractor`: `extract` với `text` chứa References @offset ~37000 → prompt gửi LLM (mock ở tầng `ainvoke` để bắt prompt) **chứa nguyên đoạn References** (không bị cắt) → bảo chứng đã bỏ trimming đúng cách.
   - **Integration then chốt:** `graph_extract_task` với `GraphExtractor` **THẬT** (chỉ mock `ainvoke` trả JSON có `references`) + DB có paper candidate khớp title → emit `SyncOutboxORM(event_type="CITES")`. (Lấp đúng lỗ hổng mà test 4.6 để lọt do mock toàn bộ extractor.)

### F. [frontend] Admin Settings hiển thị 2 setting mới

6. `AdminSettingsPage.tsx` thêm 2 input số (theo đúng pattern `MAX_PAPERS_PER_PROJECT` / `BROAD_QUERY_THRESHOLD`): load từ `getAdminSettings()`, default hiển thị **50 / 150000** khi chưa có row, lưu qua `updateAdminSetting(key, value)` trong `handleSave`. Thêm nhãn i18n VI/EN trong `translations.ts`. (`api/admin.ts` đã đủ — generic key/value, KHÔNG đổi.)

### G. Vận hành (tài liệu hóa, không cần code)

7. Ghi chú Completion Notes: sau deploy phải đặt setting (hoặc chấp nhận default) rồi chạy `POST /api/admin/backfill-graph-extraction` (idempotent, Story 4.3) để 6 paper khớp lại trên corpus đầy đủ. Verify: Neo4j `MATCH ()-[r:CITES]->() RETURN count(r)` > 0; node "cụm cô lập" giảm về đúng paper thật sự không nối.

**Lưu ý giới hạn (ghi rõ, chấp nhận MVP):** paper dài hơn `INGEST_MAX_EXTRACT_CHARS` mà References nằm sau mốc cắt vẫn mất reference (Admin nâng được). Ngưỡng khớp `difflib` 0.85 giữ nguyên (defer từ 4.6). Giữ `INGEST_MAX_EXTRACT_CHARS` ~150k–200k để chặn token cost (nay là cận text gửi LLM): 150.000 ký tự ≈ ~38k token << context Gemini 2.5 Pro (~1M+) → an toàn.

## Tasks / Subtasks

- [x] **Task 1 — `DocumentParser` tham số hóa** (AC: #1)
  - [x] Đổi `MAX_TEXT_LENGTH` → `DEFAULT_MAX_PAGES=2` / `DEFAULT_MAX_CHARS=4000`.
  - [x] `extract_text(..., max_pages=DEFAULT_MAX_PAGES, max_chars=DEFAULT_MAX_CHARS)`; truyền xuống `_extract_pdf(file_path, max_pages, max_chars)` & `_extract_docx(file_path, max_chars)`.
  - [x] `_extract_pdf`: `range(min(max_pages, len(doc)))`, `return text[:max_chars]`. `_extract_docx`: `return result.value[:max_chars]`.
- [x] **Task 2 — Admin keys** (AC: #2)
  - [x] Thêm 2 key + comment "Story 4.9" vào `_NUMERIC_SETTING_KEYS` trong [admin/presentation/router.py](../../backend/src/modules/admin/presentation/router.py).
- [x] **Task 3 — `worker.py` đọc & áp dụng setting** (AC: #3)
  - [x] Import `get_setting` từ `backend.src.modules.admin.infrastructure.settings_orm` (KHÔNG nhầm với `get_settings` app-config đã import ở [worker.py:52](../../backend/worker.py#L52)).
  - [x] Trong `_extract_text`: đọc `INGEST_MAX_PDF_PAGES`(50) / `INGEST_MAX_EXTRACT_CHARS`(150000) qua `session_factory`, guard `int()`/try-except → default. **Tái dùng** pattern `_get_int_setting` của [garbage_collection.py:29](../../backend/src/modules/graph_rag/infrastructure/garbage_collection.py#L29) (cùng `(session_factory, key, default)`) thay vì viết lại.
  - [x] Truyền `max_pages`/`max_chars` vào `DocumentParser().extract_text(...)` và `_download_and_persist_pdf(...)`.
  - [x] `_download_and_persist_pdf(pdf_url, paper, session_factory, max_pages, max_chars)`: [worker.py:253](../../backend/worker.py#L253) → `range(min(len(doc), max_pages))`, `return text[:max_chars]`.
- [x] **Task 4 — `GraphExtractor` bỏ trimming** (AC: #4)
  - [x] Xóa `_EXTRACT_HEAD`/`_REF_TAIL_BUDGET`/`_REF_HEADINGS`/`_build_extraction_text` + comment liên quan ([graph_extractor.py:74-106](../../backend/src/modules/ingestion/infrastructure/graph_extractor.py#L74-L106)).
  - [x] `extract()`: `text=text` thẳng vào `.format(...)`.
- [x] **Task 5 — Tests** (AC: #5)
  - [x] `test_document_parser`: fixture PDF/DOCX nhiều trang; (max_pages=50,max_chars=150000) lấy >2 trang & giữ References; default (2/4000) regression.
  - [x] `test_graph_extractor`: `text` có References @~37000, mock `ainvoke`, assert prompt chứa nguyên đoạn References.
  - [x] Integration `graph_extract_task`: GraphExtractor THẬT + mock `ainvoke` trả JSON references + DB candidate khớp → assert `SyncOutboxORM("CITES")` được add. (Mirror `test_graph_extract_task.py`, KHÔNG mock extractor.)
- [x] **Task 6 — Frontend Admin Settings** (AC: #6)
  - [x] `AdminSettingsPage.tsx`: 2 state + 2 input (default '50'/'150000'), load trong `useEffect`, lưu trong `handleSave` (`Promise.all` thêm 2 `updateAdminSetting`).
  - [x] `translations.ts`: 2 cặp nhãn VI/EN (vd `admin.settings.ingestMaxPdfPages`, `admin.settings.ingestMaxExtractChars`).
- [x] **Task 7 — Tài liệu vận hành** (AC: #7)
  - [x] Ghi Completion Notes: đặt setting + `POST /api/admin/backfill-graph-extraction` + verify Neo4j `count(CITES) > 0`.

## Dev Notes

### Kiến trúc & ràng buộc bắt buộc

- **Pipeline 2 Stage (ARCH §6.2) — hiểu đúng để sửa đúng chỗ:**
  - **Stage-1** (`ingest_document_task`): `_extract_text` → `DocumentParser`/`_download_and_persist_pdf` → text → chunking → lưu `ParentChunkORM`. **`INGEST_MAX_EXTRACT_CHARS` chặn text ở ĐÂY.**
  - **Stage-2** (`graph_extract_task`, [worker.py:440](../../backend/worker.py#L440)): build `full_text = "\n\n".join(c.content for c in ParentChunkORM)` ([worker.py:458-467](../../backend/worker.py#L458-L467)) → `GraphExtractor.extract(text=full_text)`. **KHÔNG re-parse PDF.** Vì chunks bắt nguồn từ text đã bị chặn ở Stage-1, `full_text` ≈ ≤`INGEST_MAX_EXTRACT_CHARS` → khi bỏ trimming trong extractor vẫn an toàn token. **Hệ quả: muốn References tới LLM thì PHẢI nâng giới hạn ở Stage-1 (Task 1+3); chỉ sửa extractor là chưa đủ.**
- **Driven adapter thuần:** `DocumentParser` KHÔNG được phụ thuộc DB/setting — composition root (`worker`) inject giới hạn. Giữ đúng Clean Architecture của repo.
- **`graph_extract_task` KHÔNG cần đọc thêm setting nào** — full_text đã bị chặn từ Stage-1.

### 🚨 Regression bắt buộc — đừng phá đường upload-metadata

`DocumentParser.extract_text` còn được gọi ở [ingestion/application/use_cases.py:146](../../backend/src/modules/ingestion/application/use_cases.py#L146) (upload thủ công, chỉ cần title/abstract đầu bài). Caller này **KHÔNG truyền** `max_pages`/`max_chars` → **default 2/4000 PHẢI giữ nguyên** để đường này không bỗng dưng parse 50 trang (tốn thời gian/bộ nhớ vô ích). Test default (AC#5) khóa hành vi này.

### Pattern code tái dùng (KHÔNG reinvent)

- **Đọc int setting:** `_get_int_setting(session_factory, key, default)` đã có sẵn ở [garbage_collection.py:29-43](../../backend/src/modules/graph_rag/infrastructure/garbage_collection.py#L29-L43) — cùng chữ ký, đã guard try/except + log. Cân nhắc import & tái dùng, hoặc copy pattern y hệt vào worker. `get_setting(db, key, default)` async, trả `str | None`.
- **Admin numeric validator:** đã ép `int ≥ 1` cho mọi key trong `_NUMERIC_SETTING_KEYS` ([router.py:79-91](../../backend/src/modules/admin/presentation/router.py#L79-L91)) — thêm key là đủ, KHÔNG viết validate mới.
- **Frontend input number:** copy block `<div className={styles.field}>` của `max-papers` ([AdminSettingsPage.tsx:59-71](../../frontend/src/features/admin/AdminSettingsPage.tsx#L59-L71)); `updateAdminSetting(key, value)` ([api/admin.ts:15](../../frontend/src/api/admin.ts#L15)) đã generic.
- **CITES producer (Story 4.6):** giữ NGUYÊN logic [worker.py:538-...](../../backend/worker.py#L538) (`references` filter + candidate match + `SyncOutboxORM("CITES")`). Story này chỉ làm cho `data.get("references")` **không còn rỗng** — không chạm logic khớp.

### Tham chiếu file UPDATE (đọc kỹ trước khi sửa)

- [document_parser.py](../../backend/src/modules/ingestion/infrastructure/document_parser.py) (37 dòng) — toàn bộ là vùng sửa.
- [graph_extractor.py:72-153](../../backend/src/modules/ingestion/infrastructure/graph_extractor.py#L72-L153) — gỡ block trimming; `extract()` còn lại giữ nguyên graceful-failure (trả `None` không raise) + `setdefault("references", [])`.
- [worker.py:167-262](../../backend/worker.py#L167-L262) (`_extract_text` + `_download_and_persist_pdf`) — thêm tham số, đọc setting. Lưu ý `_download_and_persist_pdf` đã nhận `session_factory` → dùng lại để đọc setting (đừng mở thêm engine).
- [admin/presentation/router.py:24-30](../../backend/src/modules/admin/presentation/router.py#L24-L30).
- [AdminSettingsPage.tsx](../../frontend/src/features/admin/AdminSettingsPage.tsx) + [translations.ts:114-116](../../frontend/src/i18n/translations.ts#L114-L116).

### Learnings từ Story 4.6 (lý do story này tồn tại)

- 4.6 pass review nhưng **không đạt giá trị** vì test **mock `GraphExtractor.extract`** → mốc cắt text thật không bao giờ chạy. **AC#5 của story này cố tình KHÔNG mock parser/extractor** để defect không tái diễn. Nếu bạn thấy mình đang mock `DocumentParser` hoặc `GraphExtractor.extract` trong test tích hợp → SAI hướng.
- 6 paper GMO upload dạng **PDF** (convert từ HTML), lưu `data/papers/`; upload chỉ nhận `.pdf`/`.docx` → nâng giới hạn PDF là đòn bẩy đúng.

### Learnings từ Story 4.1 / 4.3 (hạ tầng đã có)

- `system_settings` + `get_setting`/`upsert_setting` đã có từ 4.1 (`GC_RETENTION_DAYS`, `MAX_SYNC_RETRIES`). Thêm key là **incremental, KHÔNG cần chờ Story 5.3 (Admin Dynamic Settings)**.
- `POST /admin/backfill-graph-extraction` (4.3) idempotent qua `_job_id=f"graph_extract:{paper_id}"` ([router.py:98-133](../../backend/src/modules/admin/presentation/router.py#L98-L133)) — chạy lại an toàn.

### Project Structure Notes

- Backend Clean Architecture (module `ingestion`/`admin`/`graph_rag`): adapter ở `infrastructure/`, composition root là `worker.py`. Thay đổi cô lập theo module, không cross-layer mới.
- Frontend feature-based: `features/admin/`, `api/admin.ts`, `i18n/translations.ts`. Pattern đã có sẵn.
- KHÔNG file mới (trừ fixture test). KHÔNG migration. KHÔNG đổi schema/DB.

### References

- [Source: sprint-change-proposal-2026-06-19-cites-references-truncation.md] — Section 4 EP-1…EP-9 (đề xuất từng chỉnh sửa, đã chốt giá trị 50/150000).
- [Source: epics.md#Story-4.9] (dòng 507-525) — AC nháp + lưu ý giới hạn.
- [Source: architecture.md §7 Dynamic Settings] — 2 setting mới đăng ký quanh `MAX_PAPERS_PER_PROJECT`.
- [Source: architecture.md §5.2 `[:CITES]`, §6.2 pipeline Stage-1/2] — phụ thuộc text parse đủ chứa References.
- [Source: 4-6-cites-producer-trich-references-khop-paper.md] — logic CITES producer giữ nguyên.

## Dev Agent Record

### Agent Model Used
claude-sonnet-4-6

### Debug Log References

### Completion Notes List

**Story 4.9 hoàn thành — 2026-06-21**

**Tóm tắt thay đổi:**
- `DocumentParser.extract_text` được tham số hóa với `max_pages=2`/`max_chars=4000` (default giữ nguyên hành vi cũ, caller upload-metadata không cần thay đổi).
- `worker._extract_text` đọc `INGEST_MAX_PDF_PAGES`(default 50) và `INGEST_MAX_EXTRACT_CHARS`(default 150000) từ Admin Settings qua helper `_get_int_setting`. `_download_and_persist_pdf` cũng nhận 2 tham số mới.
- `GraphExtractor` gỡ toàn bộ `_build_extraction_text` + hằng `_EXTRACT_HEAD`/`_REF_TAIL_BUDGET`/`_REF_HEADINGS` — text được truyền thẳng vào prompt LLM. References không còn rơi vào "khoảng trống giữa head và tail".
- Admin router nhận thêm 2 key `INGEST_MAX_PDF_PAGES` và `INGEST_MAX_EXTRACT_CHARS` vào `_NUMERIC_SETTING_KEYS`.
- Frontend `AdminSettingsPage.tsx` thêm 2 input (default '50'/'150000'), load và lưu qua API admin. `translations.ts` thêm 2 cặp nhãn VI/EN.
- 10 tests mới: 8 trong `test_document_parser.py`, 1 trong `test_graph_extractor.py`, 2 integration tests trong `test_graph_extract_task.py` (GraphExtractor THẬT, chỉ mock ainvoke → bắt được lỗ hổng mà 4.6 để lọt).

**Hướng dẫn vận hành sau deploy:**
1. Đặt setting trong Admin Settings (hoặc chấp nhận default 50/150000).
2. **Re-ingest 6 paper GMO (BẮT BUỘC cho paper đã ingest dưới giới hạn cũ).** Giới hạn mới chỉ áp ở **Stage-1** (parse → chunk → `ParentChunkORM`). Paper đã ingest trước đó có chunk bị cắt ở ~4000 ký tự (References đã mất khỏi chunk). Phải chạy lại Stage-1 để regenerate chunk đầy đủ — hiện cách duy nhất là **xóa rồi upload lại** từng paper (chưa có endpoint re-ingest — xem Review Findings/Defer).
   - ⚠️ `POST /api/admin/backfill-graph-extraction` **CHỈ chạy lại Stage-2** (`graph_extract_task` đọc `ParentChunkORM` đã có) — KHÔNG re-parse PDF, KHÔNG tái tạo chunk. Với paper có chunk đã bị cắt, backfill **vô tác dụng** (References vẫn không nằm trong `full_text`). Backfill chỉ hữu ích cho paper mà chunk ĐÃ chứa References (ingest sau khi đã nâng giới hạn).
3. Verify: Neo4j `MATCH ()-[r:CITES]->() RETURN count(r)` > 0.
4. Confirm: node "cụm cô lập" (tô vàng) giảm về đúng paper thật sự không có kết nối.

**Lưu ý (đã ghi nhận khi review 2026-06-21):** paper upload MỚI (sau khi setting đã nâng) tự động chạy Stage-1 với giới hạn mới → References lọt vào chunk → backfill (hoặc ingest lần đầu) sẽ emit CITES bình thường.

### File List

**Backend:**
- `backend/src/modules/ingestion/infrastructure/document_parser.py` — tham số hóa max_pages/max_chars
- `backend/src/modules/admin/presentation/router.py` — thêm 2 key vào _NUMERIC_SETTING_KEYS
- `backend/worker.py` — import get_setting, thêm _get_int_setting helper, sửa _extract_text + _download_and_persist_pdf
- `backend/src/modules/ingestion/infrastructure/graph_extractor.py` — gỡ _build_extraction_text và trimming constants

**Frontend:**
- `frontend/src/features/admin/AdminSettingsPage.tsx` — thêm 2 input INGEST_MAX_PDF_PAGES/INGEST_MAX_EXTRACT_CHARS
- `frontend/src/i18n/translations.ts` — thêm 2 nhãn i18n VI/EN

**Tests:**
- `tests/unit/ingestion/test_document_parser.py` — file mới, 8 tests
- `tests/unit/ingestion/test_graph_extractor.py` — cập nhật (xoá test _build_extraction_text cũ, thêm 1 test mới)
- `tests/unit/ingestion/test_graph_extract_task.py` — thêm 2 integration tests (GraphExtractor THẬT)

### Change Log

- 2026-06-21: Story 4.9 — Sửa lỗi cắt text parse, tham số hóa DocumentParser, bỏ trimming GraphExtractor, thêm Admin settings INGEST_MAX_PDF_PAGES/INGEST_MAX_EXTRACT_CHARS, cập nhật frontend, thêm 10 tests bảo chứng (không mock parser/extractor trong integration test).

### Review Findings

**Code review 2026-06-21 (bmad-code-review, 3 lớp: Blind / Edge / Acceptance) — reviewer: Dat**

Kết quả: 2 `patch`, 1 `defer`, 4 `dismiss`. Không có `decision-needed` (đã tự chọn phương án tốt nhất theo ủy quyền).

**Patch (đã sửa):**
- [x] [Review][Patch] Completion Notes vận hành SAI/thiếu: `backfill-graph-extraction` chỉ re-enqueue `graph_extract_task` (Stage-2, đọc `ParentChunkORM` đã có). 6 paper GMO đã ingest dưới giới hạn cũ (2 trang/4000 ký tự) có chunk bị cắt → backfill KHÔNG tái tạo chunk → References vẫn thiếu → 0 CITES. PHẢI re-ingest (chạy lại Stage-1) để regenerate chunk với giới hạn mới. [worker.py:469-512 graph_extract_task đọc chunk; admin/presentation/router.py:100-135 backfill] — đã sửa Completion Notes mục "Hướng dẫn vận hành".
- [x] [Review][Patch] Test `test_graph_extract_task_real_extractor_text_with_references_at_offset` không thực sự bảo chứng việc bỏ trimming: mock `ainvoke` trả JSON references CỐ ĐỊNH bất kể nội dung prompt → test vẫn PASS kể cả khi trimming còn → docstring sai. [tests/unit/ingestion/test_graph_extract_task.py] — đã sửa: capture prompt + assert References@offset có mặt trong prompt và len(prompt)>30000.

**Defer (ghi nhận, không sửa trong story này):**
- [x] [Review][Defer] Chưa có endpoint re-ingest (Stage-1) để 1-click reprocess paper đã ingest. Hiện phải xóa + upload lại. Đề xuất follow-up: thêm `POST /admin/reingest` enqueue `ingest_document_task` cho paper `indexed`. [backend/src/modules/admin/presentation/router.py] — deferred, là capability mới ngoài scope 4.9.

**Dismiss (nhiễu / đã xử lý nơi khác):**
- `_get_int_setting` (worker) không clamp ≥1 → admin validator đã ép int≥1 ở đường ghi duy nhất (router.py:81-93); default 50/150000 cũng ≥1. Không thể tới giá trị <1 thực tế.
- Mô tả AC#4 nhắc `_build_extraction_text`/`_EXTRACT_HEAD`/`_REF_TAIL_BUDGET` nhưng baseline thật chỉ có `text[:30000]`; implementation đã bỏ trimming đúng intent (`text=text`). Mô tả spec lỗi thời, code đúng.
- Bỏ cap `[:30000]` → full_text tới ~150000 ký tự gửi LLM mỗi lần Stage-2: story đã ghi rõ & chấp nhận (~38k token << context Gemini 2.5 Pro).
- Magic number 50/150000 lặp ở `_get_int_setting`/`_download_and_persist_pdf` default/frontend default: nit bảo trì, đúng chức năng, mirror pattern gc hiện có.

**Xác nhận PASS:** AC#1 (default 2/4000 giữ nguyên — `use_cases.py:147` không truyền tham số ✓), AC#2 (2 key vào `_NUMERIC_SETTING_KEYS`, validator int≥1 tự áp ✓), AC#3 (`_extract_text` đọc 2 setting 1 lần, guard int/try-except, áp cả 2 đường PDF ✓), AC#4 (bỏ trimming, `text=text` ✓), AC#5 (test không mock parser/extractor; integration GraphExtractor THẬT chỉ mock `ainvoke` → emit CITES ✓), AC#6 (2 input FE default 50/150000, load+save, i18n VI/EN ✓).
