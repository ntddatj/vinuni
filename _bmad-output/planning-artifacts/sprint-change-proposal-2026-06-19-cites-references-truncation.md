# Sprint Change Proposal — CITES rỗng do cắt text khi parse (Story 4.6 follow-up)

- **Ngày:** 2026-06-19
- **Người soạn:** Dat (qua Correct Course)
- **Phát sinh từ:** kiểm thử thủ công sau khi Story 4.6 (CITES Producer) = `done` — project "GMO", 6 paper `test-data/gmo-bt-maize`
- **Phân loại phạm vi:** **Moderate** (1 story mới `4.9`, xuyên `ingestion` + `admin` + Frontend Admin + tests; KHÔNG đổi schema DB)
- **Mode:** Batch

---

## Section 1 — Issue Summary (Tóm tắt vấn đề)

Sau khi Story 4.6 done, Bản đồ Tri thức **không vẽ một cạnh "Trích dẫn" (CITES) nào** giữa các paper, dù 6 paper trong project trích dẫn lẫn nhau. Mỗi paper hiện ra như một cụm cô lập (chỉ có tác giả + ontology), tất cả bị tô vàng "cụm cô lập" — đúng triệu chứng mà Story 4.6 lẽ ra phải khắc phục.

**Nguyên nhân gốc (đã xác minh trên dữ liệu thật):** Danh mục References/Tài liệu tham khảo **không bao giờ tới được LLM**, nên `GraphExtractor` trả `references=[]` → `graph_extract_task` log `"0 references, bỏ qua CITES"` → 0 event CITES → 0 cạnh trong Neo4j. Logic Story 4.6 đúng; lỗi nằm ở **hai chỗ thắt cổ chai trên đường dẫn text** mà unit test của 4.6 không phát hiện được vì đã **mock `GraphExtractor`**.

### Bằng chứng

**Thắt cổ chai #1 — `DocumentParser` cắt PDF còn 2 trang đầu / 4000 ký tự.**
[document_parser.py:5](backend/src/modules/ingestion/infrastructure/document_parser.py#L5) (`MAX_TEXT_LENGTH = 4000`), [document_parser.py:25](backend/src/modules/ingestion/infrastructure/document_parser.py#L25) (`range(min(2, len(doc)))`). References luôn nằm cuối bài. Quét các PDF đã lưu của user (`data/papers/`):

| total chars | References heading tại offset | lọt vào 4000 ký tự đầu? |
|---|---|---|
| 91.694 | 37.390 | ❌ |
| 80.242 | 45.195 | ❌ |
| 134.387 | 37.540 | ❌ |
| 63.089 | 39.944 | ❌ |
| 44.496 | 28.690 | ❌ |
| 362.510 | 11.787 | ❌ |

→ Gần như mọi paper có mục References ở offset **11k–45k ký tự**, bị cắt sạch bởi mốc 4000.

**Thắt cổ chai #2 — `GraphExtractor` chỉ lấy `head[:30000] + đuôi 8000 ký tự cuối`.**
[graph_extractor.py:88-106](backend/src/modules/ingestion/infrastructure/graph_extractor.py#L88-L106): `_REF_TAIL_BUDGET = 8000`, `tail_start = max(head, len(text) - ref_budget)`. Với paper 134k ký tự, References@37.540: `head` kết thúc ở 30.000, `tail` bắt đầu ở `134.387 - 8.000 = 126.387` → mục References rơi vào **khoảng trống giữa head và tail** → vẫn bị cắt **kể cả khi đã sửa #1**. Cơ chế đuôi cố định không bám theo vị trí thật của mục References.

**Vì sao test 4.6 không bắt được:** tests mock `GraphExtractor.extract` trả sẵn `references=[...]`, nên cả hai mốc cắt text thật (DocumentParser + `_build_extraction_text`) đều không bao giờ chạy trong test → lỗ hổng tích hợp vô hình.

### Bối cảnh đã xác minh

- 6 paper GMO được upload dạng **PDF** (đã convert từ HTML), lưu tại `data/papers/`. → nâng giới hạn PDF là đúng đòn bẩy.
- Upload chỉ nhận `.pdf`/`.docx` ([use_cases.py:84](backend/src/modules/ingestion/application/use_cases.py#L84), [UploadModal.tsx:102](frontend/src/features/workspace/UploadModal.tsx#L102)). Không liên quan HTML — loại trừ giả thuyết "file HTML không parse được".
- Title các paper khớp nhau tốt theo từ khóa → khi references tới được matcher, `difflib` 0.85 nhiều khả năng khớp.

---

## Section 2 — Impact Analysis (Phân tích tác động)

### Epic Impact
- **Epic 4** (Bản đồ Tri thức & Gap Detection): Story 4.6 marked `done` nhưng **không đạt mục tiêu giá trị** (CITES vẫn rỗng) → Query 2 `gap_detection` (cụm cô lập, Story 4.4) vẫn báo nhiễu "mọi node vàng". Cần story sửa lỗi tích hợp **4.9**.
- **Epic 5**: Story 5.3 (Admin Dynamic Settings) liên quan khái niệm, nhưng hạ tầng `system_settings` đã tồn tại (Story 4.1 thêm `GC_RETENTION_DAYS`/`MAX_SYNC_RETRIES`) → thêm key mới là **incremental**, KHÔNG cần chờ 5.3.

### Story Impact
- **Story 4.6** (`done`): logic giữ nguyên, KHÔNG rollback. Defect nằm ở các thành phần upstream (parse) mà 4.6 không chạm tới.
- **Story 4.9 (MỚI):** "Sửa cắt text khi parse + đưa giới hạn parse vào Admin Setting để CITES hoạt động thật".
- **Story 4.7** (FILLS_GAP, backlog) **hưởng lợi gián tiếp:** cùng đường dẫn text — limitation/finding của paper dài cũng đang bị cắt; sửa 4.9 cải thiện chất lượng ontology cho cả 4.7.

### Artifact Conflicts
- `epics.md` — thêm Story 4.9 vào Epic 4; ghi chú dưới Story 4.6 rằng giá trị thực hiện hóa ở 4.9.
- `architecture.md §7` (Dynamic Settings, quanh dòng 335) — bổ sung 2 setting động mới; ghi chú Stage-1 parse không còn hardcode 2 trang/4000 ký tự.
- KHÔNG đụng PRD, UX.

### Technical Impact
- `ingestion/infrastructure/document_parser.py` — tham số hóa giới hạn trang/ký tự.
- `worker.py` — `_extract_text` + `_download_and_persist_pdf` đọc setting & truyền giới hạn.
- `ingestion/infrastructure/graph_extractor.py` — **bỏ cơ chế cắt head/đuôi** (`_build_extraction_text`); gửi thẳng `full_text` (đã bị `INGEST_MAX_EXTRACT_CHARS` chặn) cho LLM.
- `admin/presentation/router.py` — thêm **2 key** vào `_NUMERIC_SETTING_KEYS`.
- Frontend `features/admin/AdminSettingsPage.tsx` + `api/admin.ts` + i18n — hiển thị **2 input** mới.
- **KHÔNG cần Alembic migration** (bảng `system_settings` đã có; default qua `get_setting(..., default=...)`).
- **Chi phí:** `INGEST_MAX_EXTRACT_CHARS` giờ gánh 2 vai (lượng text chunking/embedding **và** lượng text gửi LLM). Default 150.000 ký tự ≈ ~38k token < context Gemini 2.5 Pro (~1M+) → an toàn; chi phí token tăng vừa phải (corpus ≤15, chấp nhận). **Giữ giá trị này ở mức hợp lý (~150k–200k)** để chặn cost — nếu Admin nâng rất cao, mỗi lần extract sẽ tốn token tương ứng.
- **Vận hành:** sau deploy phải chạy lại `POST /admin/backfill-graph-extraction` (Story 4.3, idempotent) để 6 paper khớp lại trên corpus đầy đủ (forward-compat AC#7).

---

## Section 3 — Recommended Approach (Hướng tiếp cận đề xuất)

**Direct Adjustment** — tạo Story 4.9 vá tích hợp, KHÔNG rollback 4.6, KHÔNG đổi MVP scope.

**2 setting động mới (Admin, kiểu số nguyên dương), đã chốt giá trị duyệt:**

| Key | Default | Ý nghĩa |
|---|---|---|
| `INGEST_MAX_PDF_PAGES` | **50** | Số trang PDF tối đa parse (cũ: 2) |
| `INGEST_MAX_EXTRACT_CHARS` | **150000** | Số ký tự text tối đa giữ lại sau parse (cũ: 4000). Cũng là cận trên lượng text gửi LLM. |

Giá trị 50 / 150.000 phủ toàn bộ paper hiện tại — kiểm chứng trên dữ liệu thật: cả 6 paper GMO có mục References ở offset ≤45.195, nằm trọn trong 150.000 ký tự đầu → References luôn tới được LLM.

**Quyết định 2026-06-19 (Dat):** BỎ tham số thứ 3 `INGEST_GRAPH_REF_TAIL_CHARS` và **bỏ luôn cơ chế cắt head/đuôi** trong `GraphExtractor`. Lý do: `INGEST_MAX_EXTRACT_CHARS` đã chặn tổng text; gửi thẳng `full_text` cho LLM thì References luôn lọt (không còn "khoảng trống giữa head và đuôi"). Đơn giản hơn, đúng ý "2 tham số vào Admin". Đánh đổi đã chấp nhận: `INGEST_MAX_EXTRACT_CHARS` gánh thêm vai "lượng token gửi LLM" → giữ ở mức hợp lý.

**Ước lượng:** ~0.5–1 ngày (1 story, không migration). **Rủi ro:** thấp (tham số có default lùi về hành vi cũ; thay đổi cô lập theo module).

---

## Section 4 — Detailed Change Proposals (Đề xuất chỉnh sửa chi tiết)

> Quy ước: tham số `max_pages`/`max_chars` để **default = giá trị cũ (2 / 4000)** nên đường upload-metadata ([use_cases.py:146](backend/src/modules/ingestion/application/use_cases.py#L146) — chỉ cần title/abstract ở đầu bài) giữ nguyên hành vi rẻ; chỉ **worker ingestion** mới opt-in giá trị lớn từ Admin Setting.

### EP-1 — `epics.md`: thêm Story 4.9 (Epic 4, sau Story 4.8)

```markdown
### Story 4.9: [Backend+FE] Sửa cắt text khi parse — kích hoạt References/CITES thật + giới hạn parse vào Admin Setting — ⏳ backlog 🟡

Vá lỗ hổng tích hợp lộ sau Story 4.6: `DocumentParser` cắt PDF còn 2 trang/4000 ký tự → mục References (offset 11k–45k) không bao giờ tới LLM → `references=[]` → 0 cạnh CITES. Nâng giới hạn parse (cấu hình động qua Admin) và bỏ cơ chế cắt head/đuôi trong `GraphExtractor` (gửi thẳng full_text đã bị `INGEST_MAX_EXTRACT_CHARS` chặn).

- **Phát sinh:** correct-course 2026-06-19 (`sprint-change-proposal-2026-06-19-cites-references-truncation.md`). Hiện thực hóa giá trị Story 4.6 (vốn marked done nhưng CITES rỗng).
- **🧭 Nhãn module/role:** `[ingestion]` sửa `DocumentParser` + `GraphExtractor` + `worker` · `[admin]` thêm 2 key setting động · `[frontend]` Admin Settings hiển thị 2 input.
- **Phụ thuộc:** Story 4.6 (producer CITES), Story 4.3 (Stage-2 worker + backfill endpoint), hạ tầng `system_settings` (Story 4.1).

**Acceptance Criteria:**
1. `DocumentParser.extract_text` nhận `max_pages`/`max_chars` (default 2/4000 — giữ hành vi cũ); `_extract_pdf` dùng `range(min(max_pages, len(doc)))` + `text[:max_chars]`; `_extract_docx` dùng `text[:max_chars]`.
2. 2 setting động mới (số nguyên ≥1): `INGEST_MAX_PDF_PAGES`=50, `INGEST_MAX_EXTRACT_CHARS`=150000 — đọc qua `get_setting(..., default=...)`, sửa được trong Admin Settings.
3. `worker._extract_text` + `_download_and_persist_pdf` đọc 2 setting và áp dụng (thay `min(2,..)`/`min(20,..)`/`MAX_TEXT_LENGTH` hardcode).
4. `GraphExtractor`: **bỏ `_build_extraction_text` + hằng `_EXTRACT_HEAD`/`_REF_TAIL_BUDGET`/`_REF_HEADINGS`**; `extract` truyền thẳng `text` (đã bị `INGEST_MAX_EXTRACT_CHARS` chặn ở DocumentParser) vào prompt. References nằm trong full_text → LLM trích được.
5. Test tích hợp KHÔNG mock `GraphExtractor`/`DocumentParser`: PDF/text fixture nhiều trang có mục References ở offset >30000 → `references` được trích, `graph_extract_task` add `SyncOutboxORM("CITES")`. (Lấp đúng lỗ hổng đã để defect lọt.)
6. Frontend Admin Settings hiển thị + lưu được 2 setting mới (i18n VI/EN).
7. Tài liệu: ghi chú vận hành chạy lại `POST /admin/backfill-graph-extraction` sau khi đặt giá trị.

**Lưu ý giới hạn (ghi rõ):** paper dài hơn `INGEST_MAX_EXTRACT_CHARS` mà References nằm sau mốc cắt vẫn mất reference (chấp nhận MVP; Admin nâng được). Ngưỡng khớp `difflib` 0.85 giữ nguyên (defer từ 4.6).
```

Đồng thời thêm 1 dòng dưới **Story 4.6** trong `epics.md`:
```markdown
- **⚠️ Follow-up:** giá trị (cạnh CITES thật) chỉ hiện thực hóa sau **Story 4.9** — 4.6 đúng logic nhưng references bị cắt ở tầng parse (xem sprint-change-proposal-2026-06-19).
```

### EP-2 — `architecture.md §7` (Dynamic Settings, quanh dòng 335)

```markdown
OLD:
    * `MAX_PAPERS_PER_PROJECT` (integer, mặc định: `15`): Giới hạn số tài liệu tối đa của mỗi dự án.

NEW:
    * `MAX_PAPERS_PER_PROJECT` (integer, mặc định: `15`): Giới hạn số tài liệu tối đa của mỗi dự án.
    * `INGEST_MAX_PDF_PAGES` (integer, mặc định: `50`): Số trang PDF tối đa được parse ở Stage-1 (chunking/ontology). Nâng từ 2 để mục References (cuối bài) lọt vào, kích hoạt cạnh CITES.
    * `INGEST_MAX_EXTRACT_CHARS` (integer, mặc định: `150000`): Số ký tự tối đa giữ lại sau parse (nâng từ 4000). Đồng thời là cận trên lượng text gửi LLM ở Stage-2.
```
Rationale: §5.2 (`[:CITES]`) và §6.2 (pipeline Stage-1/2) phụ thuộc text parse đủ chứa References.

### EP-3 — `admin/presentation/router.py` ([_NUMERIC_SETTING_KEYS](backend/src/modules/admin/presentation/router.py#L24))

```python
OLD:
_NUMERIC_SETTING_KEYS = {
    "MAX_PAPERS_PER_PROJECT",
    "BROAD_QUERY_THRESHOLD",
    "GC_RETENTION_DAYS",
    "MAX_SYNC_RETRIES",
}

NEW:
_NUMERIC_SETTING_KEYS = {
    "MAX_PAPERS_PER_PROJECT",
    "BROAD_QUERY_THRESHOLD",
    "GC_RETENTION_DAYS",
    "MAX_SYNC_RETRIES",
    "INGEST_MAX_PDF_PAGES",        # Story 4.9: số trang PDF tối đa parse
    "INGEST_MAX_EXTRACT_CHARS",    # Story 4.9: số ký tự tối đa sau parse (cũng là cận text gửi LLM)
}
```
(Validator hiện có đã ép số nguyên ≥1 — phù hợp cả 2.)

### EP-4 — `document_parser.py`: tham số hóa giới hạn

```python
OLD:
MAX_TEXT_LENGTH = 4000
...
    def extract_text(self, file_path: str, mime_type: str) -> str:
        ...
    def _extract_pdf(self, file_path: str) -> str:
        ...
            for page_num in range(min(2, len(doc))):
                text += doc[page_num].get_text()
        ...
        return text[:MAX_TEXT_LENGTH]
    def _extract_docx(self, file_path: str) -> str:
        ...
        return result.value[:MAX_TEXT_LENGTH]

NEW:
DEFAULT_MAX_PAGES = 2        # giữ default cũ; worker opt-in giá trị Admin
DEFAULT_MAX_CHARS = 4000
...
    def extract_text(self, file_path, mime_type,
                     max_pages: int = DEFAULT_MAX_PAGES,
                     max_chars: int = DEFAULT_MAX_CHARS) -> str:
        # ...truyền max_pages/max_chars xuống _extract_pdf/_extract_docx...
    def _extract_pdf(self, file_path, max_pages, max_chars) -> str:
        ...
            for page_num in range(min(max_pages, len(doc))):
                text += doc[page_num].get_text()
        ...
        return text[:max_chars]
    def _extract_docx(self, file_path, max_chars) -> str:
        ...
        return result.value[:max_chars]
```
Rationale: parser thuần (driven adapter), không phụ thuộc DB — composition root inject giới hạn.

### EP-5 — `worker.py`: đọc setting & áp dụng cả 2 đường PDF

```python
# _extract_text(paper, session_factory): đọc setting một lần (mở session từ session_factory),
#   max_pages = int(get_setting(db, "INGEST_MAX_PDF_PAGES", "50"))
#   max_chars = int(get_setting(db, "INGEST_MAX_EXTRACT_CHARS", "150000"))
# rồi:
#   DocumentParser().extract_text(paper.file_path, mime_type, max_pages=max_pages, max_chars=max_chars)
#   _download_and_persist_pdf(..., max_pages=max_pages, max_chars=max_chars)

OLD ([worker.py:253](backend/worker.py#L253)):
                text = "".join(doc[i].get_text() for i in range(min(len(doc), 20)))
            ...
            return text
NEW:
                text = "".join(doc[i].get_text() for i in range(min(len(doc), max_pages)))
            ...
            return text[:max_chars]
```
Guard `int(...)` bọc try/except → default an toàn nếu giá trị Admin sai kiểu. `graph_extract_task` KHÔNG cần đọc thêm setting nào (full_text đã bị `INGEST_MAX_EXTRACT_CHARS` chặn từ Stage-1).

### EP-6 — `graph_extractor.py`: bỏ cắt head/đuôi, gửi thẳng full_text

```python
OLD (gỡ toàn bộ):
    _EXTRACT_HEAD = 30000
    _REF_TAIL_BUDGET = 8000
    _REF_HEADINGS = (...)
    def _build_extraction_text(text, head=..., ref_budget=...):  # toàn bộ hàm
        ...
    # trong extract():
    prompt = GRAPH_EXTRACTION_PROMPT.format(..., text=_build_extraction_text(text))

NEW:
    # trong extract(): truyền thẳng text (DocumentParser đã chặn ở INGEST_MAX_EXTRACT_CHARS)
    prompt = GRAPH_EXTRACTION_PROMPT.format(..., text=text)
```
Rationale: full_text đã bị `INGEST_MAX_EXTRACT_CHARS` (mặc định 150k) chặn → vừa với context Gemini 2.5 Pro; References luôn nằm trong đó nên không cần cắt head/đuôi hay anchor heading. Bỏ hẳn nguồn gây "khoảng trống giữa head và đuôi" của bottleneck #2.

### EP-7 — Frontend Admin Settings

- [api/admin.ts](frontend/src/api/admin.ts): không đổi cấu trúc (generic key/value PUT đã sẵn).
- [AdminSettingsPage.tsx](frontend/src/features/admin/AdminSettingsPage.tsx): thêm `settings.find(s => s.key === 'INGEST_MAX_PDF_PAGES')` v.v., render 2 input số (theo đúng pattern `MAX_PAPERS_PER_PROJECT`/`BROAD_QUERY_THRESHOLD`), gọi `updateAdminSetting` khi lưu, có default hiển thị 50/150000 khi chưa có row.
- `i18n/translations.ts`: thêm nhãn VI/EN cho 2 setting (vd "Số trang PDF tối đa khi phân tích", "Số ký tự tối đa khi phân tích").

### EP-8 — Tests (chống tái lỗ hổng)

- `test_document_parser`: PDF/DOCX fixture → `extract_text(max_pages=50, max_chars=150000)` lấy > 2 trang; default vẫn 2/4000.
- `test_graph_extractor_passes_full_text`: `extract` với `text` chứa mục References ở offset ~37000 (< max_chars) → prompt gửi LLM (`ainvoke` được mock để bắt prompt) **chứa nguyên đoạn References** (không bị cắt). Bảo chứng đã bỏ trimming đúng cách.
- **Integration (then chốt):** `graph_extract_task` với `GraphExtractor` THẬT (LLM mock ở tầng `ainvoke` trả JSON có references) + DB candidate → emit `CITES`. Tránh lặp lỗi 4.6 (mock toàn bộ extractor).

### EP-9 — Vận hành (sau deploy)

1. Admin Settings: đặt `INGEST_MAX_PDF_PAGES=50`, `INGEST_MAX_EXTRACT_CHARS=150000` (hoặc chấp nhận default).
2. `POST /api/admin/backfill-graph-extraction` → re-enqueue toàn bộ paper indexed (idempotent).
3. Knowledge Map → reload: kỳ vọng cạnh xanh "Trích dẫn" xuất hiện, các paper hết cô lập (hết vàng cụm cô lập).
4. Kiểm tra Neo4j: `MATCH ()-[r:CITES]->() RETURN count(r)` → > 0.

---

## Section 5 — Implementation Handoff

- **Phân loại:** **Moderate** — không replan, không đổi PRD/UX; 1 story mới xuyên `ingestion`/`admin`/FE + tests.
- **Bàn giao:** PO/DEV.
  1. Cập nhật `epics.md` (EP-1) + `architecture.md` (EP-2).
  2. `bmad-create-story` cho **Story 4.9** (context-fill từ proposal này), rồi `bmad-dev-story` để code EP-3…EP-8.
  3. Sau merge: thực thi EP-9 (đặt setting + backfill + verify).
- **Success criteria:** Knowledge Map của project GMO hiển thị cạnh CITES giữa các paper; `count(CITES) > 0` trên Neo4j; số node "cụm cô lập" giảm về đúng paper thật sự không nối; test tích hợp EP-8 pass (không mock extractor).
