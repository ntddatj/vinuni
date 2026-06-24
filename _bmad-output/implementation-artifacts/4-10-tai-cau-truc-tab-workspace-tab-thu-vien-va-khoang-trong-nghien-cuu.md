---
baseline_commit: 95e0b7459ff63537bab19e69fdc72d89ec91168b
---

# Story 4.10: [BE+FE] Tái cấu trúc Tab Workspace — Tách tab Thư viện + Tab "Khoảng trống Nghiên cứu" (card giàu)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **nhà nghiên cứu đang dùng workspace**,
I want **(1) tab "Thư viện Tài liệu" tách thành 2 tab con rõ ràng (quản lý tài liệu vs. tìm kiếm báo cáo) và (2) một tab lớn riêng "Khoảng trống Nghiên cứu" hiển thị danh sách khoảng trống dạng card giàu (tiêu đề, mô tả, bằng chứng)**,
so that **tôi không bị rối khi gộp tìm-kiếm + quản-lý vào một màn, và giá trị trí tuệ cốt lõi FR7 (gap detection) được phơi bày ngay thay vì bị chôn trong toggle ẩn của Bản đồ Tri thức**.

## Acceptance Criteria

> Thực thi **BE trước → FE sau** (FE cần endpoint để vẽ card). 8 AC: #1–2 backend, #3–7 frontend, #8 regression.

1. **[BE] Use case `gap_detection_detailed(project_id)`** trả về danh sách item cho **cả 3 loại** gap, tái dùng 3 query Cypher của Story 4.4 nhưng **mở rộng `RETURN`**:
   - **CONTRADICTS** → mỗi item kèm **2 đoạn text finding** (`f1.description`, `f2.description`) + **2 paper title** (`p1.title`, `p2.title`).
   - **Unfilled limitation** → mỗi item kèm **`l.description`** + **owner paper title**.
   - **Isolated cluster** → mỗi item kèm **paper title** + **đếm neighbor (= 0)**.
   - Mỗi item có cấu trúc: `{ id, type, reason, title, description, papers: [{paper_id, title}], evidence: {...} }`.
   - Văn xuôi `title`/`description` **template từ entity thật** (description của finding/limitation, title của paper) — **KHÔNG sinh tự do, KHÔNG gọi LLM**.
2. **[BE] Endpoint `GET /api/projects/{project_id}/graph/gaps/detailed`** → `GapDetailResponse { items: GapDetailItem[] }`:
   - JWT bắt buộc (`get_current_user`) + owner scoping qua `_get_project_or_404` (chống IDOR: project của user khác → 404).
   - Neo4j lỗi / down → trả `{ items: [] }` **không raise** (mirror pattern AC#4 của Story 4.4).
   - Endpoint cũ `GET /graph/gaps` **GIỮ NGUYÊN 100%** (gap-mode trên Map vẫn dùng nó).
3. **[FE] Shell 4 tab** trong `CenterWorkspace`, đúng thứ tự `Thư viện Tài liệu › Bản đồ Tri thức › Khoảng trống Nghiên cứu › Hỗ trợ viết tổng quan`, có dấu `›` ngăn cách (pattern Story 3.8 đã có), active đúng, default `library`. Dùng lại pattern `display:none` (không unmount tab khác).
4. **[FE] Tab Thư viện = 2 tab con segmented**, mặc định "Tài liệu trong dự án":
   - **"Tài liệu trong dự án"** = `DocumentList` + nút **"Upload báo cáo offline"** + `IngestionProgress` + cảnh báo giới hạn `MAX_PAPERS`. Xóa/sửa/xem PDF giữ nguyên (Story 2.7).
   - **"Tìm kiếm báo cáo khoa học"** = ô tìm kiếm + kết quả arXiv/Semantic Scholar + nút "Thêm vào dự án" + gợi ý MECE (Story 2.3) + toast degraded-union (Story 2.2); **giữ `searchIdRef`** chống race.
5. **[FE] Counter dùng chung — RỦI RO CHÍNH:** add-from-search ở tab "Tìm kiếm" phải cập nhật **đúng** counter/giới hạn hiển thị ở tab "Tài liệu". State `papers` / `maxPapers` / `isAtLimit` / `processingDocumentIds` / `addingPapers` / `docRefreshTrigger` **nâng lên component cha `LibraryTab`** — **một nguồn sự thật duy nhất**; KHÔNG để mỗi tab con giữ bản sao riêng (sẽ lệch `MAX_PAPERS`). **Viết test riêng cho điểm này.**
6. **[FE] `GapTab` (MỚI)** gọi `fetchGapsDetailed(projectId)`, render danh sách **card giàu nhóm theo 3 reason**:
   - Mỗi card: tiêu đề + mô tả (text thật từ endpoint) + dòng bằng chứng + **badge loại** với **màu khớp Story 4.8** (đỏ `#EF4444` contradiction / cam `#F59E0B` unfilled / xanh `#3B82F6` isolated).
   - **Empty state** khi 0 gap.
   - Nút **"Mở trên Bản đồ Tri thức"** → chuyển `activeTab='graph'` + bật gap-mode + focus node (xem Dev Notes §"Cầu Gap→Map").
   - Nút **"Giải thích khoảng trống này"** → đẩy câu hỏi vào chat (Gap Analyst 4.5) qua bridge `setPendingChatInput` (đã tồn tại).
7. **[FE] FR15 không vỡ:** `activeTab='gaps'` truyền vào `getSuggestions({ activeTab })` không gây lỗi (kiểu `string`, backend hiện không nhánh theo `active_tab` → fallback an toàn sẵn — xác nhận, không cần đổi BE).
8. **[Regression]** Map gap-mode (4.4/4.8) + Node Detail + 3 màu vẫn đúng (coexist 2 view trên cùng dữ liệu); Cytoscape re-fit khi chuyển tab; responsive không vỡ; **i18n VI/EN đủ** cho mọi chuỗi mới.

## Tasks / Subtasks

### Backend (làm trước)

- [x] **Task 1 — Domain + schema cho gap "giàu"** (AC: #1)
  - [x] Thêm dataclass domain trong [entities.py](backend/src/modules/graph_rag/domain/entities.py): `GapDetailItem` (`id`, `type`, `reason`, `title`, `description`, `papers: list`, `evidence: dict`) + `GapDetailContext` (hoặc trả thẳng `list[GapDetailItem]`).
  - [x] Thêm Pydantic trong [schemas.py](backend/src/modules/graph_rag/presentation/schemas.py): `GapPaperRef { paper_id, title }`, `GapDetailItem { id, type, reason, title, description, papers, evidence }`, `GapDetailResponse { items: list[GapDetailItem] }`.
- [x] **Task 2 — Use case `gap_detection_detailed`** (AC: #1)
  - [x] Trong [use_cases.py](backend/src/modules/graph_rag/application/use_cases.py) class `GapDetectionUseCase`, thêm method `async def gap_detection_detailed(self, project_id) -> list[GapDetailItem]`.
  - [x] Viết **3 Cypher mới** cạnh các hằng có sẵn, **mở rộng `RETURN`** (KHÔNG sửa hằng cũ — gap-mode Map vẫn dùng `_CYPHER_CONTRADICTS` / `_CYPHER_ISOLATED` / `_CYPHER_UNFILLED_LIMITATION`):
    - `_CYPHER_CONTRADICTS_DETAILED`: thêm `f1.description AS finding1_text, f2.description AS finding2_text, p1.title AS paper1_title, p2.title AS paper2_title`.
    - `_CYPHER_UNFILLED_LIMITATION_DETAILED`: dựa trên `_CYPHER_UNFILLED_LIMITATION_FULL` (đã có `limitation_id/description/owner_paper_id`) + thêm `p.title AS owner_paper_title`.
    - `_CYPHER_ISOLATED_DETAILED`: thêm `p.title AS paper_title` (giữ `cites_count = 0`).
  - [x] ⚠️ **Property đúng là `.description`** trên Finding/Limitation (KHÔNG phải `.text` — xem Dev Notes). Paper dùng `.title`.
  - [x] Bọc try/except **toàn bộ** (mở session + từng query) → trả `[]` khi sự cố, **không raise** (sao chép cấu trúc `gap_detection` hiện có, dòng 258–298).
  - [x] Dựng `title`/`description` bằng template tất định, ví dụ: contradiction → `title = "Mâu thuẫn giữa <paper1_title> và <paper2_title>"`, `description` ghép 2 finding text; unfilled → `title` từ paper title + `description = l.description`; isolated → `title = "<paper_title> chưa liên kết trích dẫn"`.
- [x] **Task 3 — Endpoint** (AC: #2)
  - [x] Trong [router.py](backend/src/modules/graph_rag/presentation/router.py) thêm `GET /{project_id}/graph/gaps/detailed` → `GapDetailResponse`, mirror `get_graph_gaps`: `_get_project_or_404` + `GapDetectionUseCase(driver).gap_detection_detailed(...)`. **Không đổi** `get_graph_gaps`.
- [x] **Task 4 — Test backend** (AC: #1, #2)
  - [x] Mở rộng [test_gap_detection.py](tests/unit/graph_rag/test_gap_detection.py): `gap_detection_detailed` cho 3 loại (ghép đúng text/title), 0 gap → `[]`, Neo4j down (`_BrokenNeo4jDriver`) → `[]` không raise. Tái dùng fakes `_FakeNeo4jDriver`/`_FakeNeo4jResult` có sẵn (mỗi `run` trả record có key đúng tên cột mới).
  - [x] Mở rộng [test_graph_router.py](tests/unit/graph_rag/test_graph_router.py): endpoint mới — 200 + shape; project của user khác → 404 (IDOR); Neo4j lỗi → `items: []`; `/graph/gaps` cũ vẫn pass.

### Frontend (làm sau khi endpoint xanh)

- [x] **Task 5 — Store + types + api** (AC: #3, #6)
  - [x] [workspaceStore.ts](frontend/src/store/workspaceStore.ts): `TabKey` thêm `'gaps'`; thêm `librarySubTab: 'documents' | 'search'` (default `'documents'`) + `setLibrarySubTab`. (Xem §"Cầu Gap→Map" về field focus.)
  - [x] [types/graph.ts](frontend/src/types/graph.ts): `GapPaperRef`, `GapDetailItem`, `GapDetailResponse` (khớp Pydantic).
  - [x] [api/graph.ts](frontend/src/api/graph.ts): `fetchGapsDetailed(projectId): Promise<GapDetailResponse>` gọi `/api/projects/${projectId}/graph/gaps/detailed`.
- [x] **Task 6 — Shell 4 tab** (AC: #3)
  - [x] [CenterWorkspace.tsx](frontend/src/features/workspace/CenterWorkspace.tsx): thêm nút tab `gaps` **giữa** graph và writing, kèm `<span className={styles.tabSep}>›</span>`; thêm panel `display:flex/none` cho `<GapTab projectId={activeProjectId} />` (panel gap nên dùng layout cuộn dọc như library).
- [x] **Task 7 — Tách LibraryTab thành cha + 2 tab con** (AC: #4, #5)
  - [x] Refactor [LibraryTab.tsx](frontend/src/features/workspace/LibraryTab.tsx): **giữ toàn bộ state dùng chung ở cha** (`papers`, `maxPapers`, `isAtLimit`, `processingDocumentIds`, `addingPapers`, `docRefreshTrigger`, các handler ingestion + `handleAddFromSearch`). Cha render segmented control 2 nút (đọc/ghi `librarySubTab`).
  - [x] Tách 2 child component (cùng file hoặc file riêng): **`DocumentsSubTab`** (DocumentList + nút Upload + IngestionProgress + limitAlert) và **`SearchSubTab`** (searchBar + suggestions + resultList + PaperCard). Truyền props từ cha (đặc biệt `papers`/`isAtLimit`/`onAddFromSearch`/`addingPapers`) — **không tạo state counter mới trong child**.
  - [x] `searchIdRef` đặt ở component chứa search logic; modal upload đọc `isUploadModalOpen` từ store như cũ.
  - [x] CSS: dùng/đặt class segmented control (tham khảo `.subTabBar` trong mockup); thêm vào [LibraryTab.module.css](frontend/src/features/workspace/LibraryTab.module.css).
- [x] **Task 8 — GapTab (MỚI)** (AC: #6)
  - [x] Tạo `frontend/src/features/workspace/GapTab.tsx` + `GapTab.module.css`: fetch khi tab active & có `projectId`; loading/error/empty states; nhóm card theo `reason` với màu Story 4.8; 2 nút mỗi card.
  - [x] Nút "Mở trên Bản đồ Tri thức" + "Giải thích khoảng trống này" — xem §"Cầu Gap→Map" và §"Cầu Gap→Chat".
- [x] **Task 9 — Cầu Gap→Map** (AC: #6, #8)
  - [x] Thêm signal vào `workspaceStore`: `gapFocusRequest: { paperId: string } | null` + `requestGapFocus(paperId)` + `clearGapFocus()`.
  - [x] Nút "Mở trên Bản đồ": `setActiveTab('graph')` + `requestGapFocus(paperId)`.
  - [x] [KnowledgeMapTab.tsx](frontend/src/features/workspace/KnowledgeMapTab.tsx): effect đọc `gapFocusRequest` → khi có & `activeTab==='graph'`: `setGapMode(true)`, và sau khi `gapData` load + node tồn tại → `cy.getElementById(paperId).select()` + `cy.animate({center:{eles}})`; rồi `clearGapFocus()`. (gapMode hiện là local `useState` — KHÔNG chuyển hẳn lên store; chỉ kích hoạt qua signal để tránh vỡ logic toggle/pulsing hiện có.)
- [x] **Task 10 — Cầu Gap→Chat** (AC: #6)
  - [x] Nút "Giải thích khoảng trống này": `setPendingChatInput(<câu hỏi tiếng Việt mô tả gap>)` (bridge sẵn ở [ChatBar.tsx:52-58](frontend/src/features/workspace/ChatBar.tsx#L52-L58) prefill + focus). Câu hỏi nên gồm title gap để Gap Analyst (4.5) trả lời có nguồn.
- [x] **Task 11 — i18n** (AC: #3, #4, #6, #8)
  - [x] [translations.ts](frontend/src/i18n/translations.ts) thêm VI/EN: `tab.gaps`, nhãn 2 tab con (lưu ý `library.documents` đã tồn tại = "Tài liệu trong dự án" — tái dùng), nhãn "Tìm kiếm báo cáo khoa học", "Upload báo cáo offline", và cụm `gapTab.*` (tiêu đề trang, 3 nhãn loại, nhãn bằng chứng, empty state, 2 nút). Tái dùng `graph.legendContradiction/Unfilled/Isolated` nếu hợp.
- [x] **Task 12 — Test frontend** (AC: #3, #4, #5, #6, #8)
  - [x] Cập nhật [CenterWorkspace.test.tsx](frontend/src/features/workspace/__tests__/CenterWorkspace.test.tsx): **4 tab + đúng thứ tự** (test "renders 3 tabs" hiện sẽ FAIL → sửa thành 4).
  - [x] Tách/cập nhật [LibraryTab.test.tsx](frontend/src/features/workspace/__tests__/LibraryTab.test.tsx): 2 tab con render đúng + **test counter dùng chung không lệch** (add-from-search → counter ở tab Tài liệu tăng/đạt giới hạn).
  - [x] Mới `GapTab.test.tsx`: render nhóm 3 loại + empty state + 2 nút bấm gọi đúng store action (mock `fetchGapsDetailed`).
  - [x] Regression [KnowledgeMapTab.test.tsx](frontend/src/features/workspace/__tests__/KnowledgeMapTab.test.tsx): gap-mode vẫn pass.

## Dev Notes

### ⚠️ Cảnh báo quan trọng nhất (đọc trước khi code BE)

- **Property text trên node là `.description`, KHÔNG phải `.text`.** Đã xác minh trong [neo4j_adapter.py](backend/src/modules/graph_rag/infrastructure/neo4j_adapter.py#L199-L230): Finding `MERGE … SET f.description`, Limitation `SET l.description`. Paper dùng `.title`. **Nếu query `.text` sẽ trả `null` → card rỗng.** (Proposal nói "Finding có text" là viết lỏng — dùng `description`.)
- **KHÔNG sửa 3 hằng Cypher cũ** (`_CYPHER_CONTRADICTS`, `_CYPHER_ISOLATED`, `_CYPHER_UNFILLED_LIMITATION`) và **KHÔNG sửa** `gap_detection()` / `get_graph_gaps`. Chúng nuôi gap-mode trên Map (Story 4.4/4.8) — đổi sẽ gây regression AC#8. Tạo hằng `_DETAILED` mới song song.
- **`_CYPHER_UNFILLED_LIMITATION_FULL` đã tồn tại** (dòng 222–229) và đang được `list_unfilled_limitations` (ingestion producer) dùng — **đừng sửa nó**; copy thành biến `_DETAILED` riêng nếu cần thêm `p.title`.

### Hợp đồng dữ liệu `GapDetailItem` (FE & BE phải khớp)

```
GapDetailItem {
  id: string                       // ổn định để React key (vd f1_f2 cho contradiction, limitation_id, paper_id)
  type: 'contradiction' | 'unfilled_limitation' | 'isolated_cluster'
  reason: string                   // alias của type (giữ song song cho rõ; FE map sang màu/nhãn)
  title: string                    // template tất định từ entity thật
  description: string              // template tất định (finding/limitation text)
  papers: { paper_id: string; title: string }[]
  evidence: object                 // vd { finding_count, neighbor_count, paper_count } — số liệu cho dòng "bằng chứng"
}
```
- Màu/nhãn FE map từ `reason`/`type` → **dùng đúng 3 màu Story 4.8**: `has_contradiction`/`contradiction` = `#EF4444` (đỏ), `has_unfilled_limitation`/`unfilled_limitation` = `#F59E0B` (cam), `isolated_cluster` = `#3B82F6` (xanh). Xem [KnowledgeMapTab.tsx:127-150](frontend/src/features/workspace/KnowledgeMapTab.tsx#L127-L150) (class `.gap-contradiction/.gap-unfilled/.gap-isolated`).
- ⚠️ **Mockup gây nhầm:** [layout-tabs-restructure.html](test-data/mockups/layout-tabs-restructure.html) khung 3 hiển thị nhãn "CẤU TRÚC"/"THIẾU BẰNG CHỨNG"/"MÂU THUẪN" với màu khác (amber/indigo/red). Đó chỉ là **flavor minh hoạ**. Dữ liệu thật chỉ có **3 loại từ Cypher** (contradiction/unfilled_limitation/isolated_cluster) → **theo bảng màu/nhãn Story 4.8**, KHÔNG bịa loại "thiếu bằng chứng".

### Pattern hiện trạng cần tuân theo

- **Endpoint mirror:** `get_graph_gaps` ([router.py:76-101](backend/src/modules/graph_rag/presentation/router.py#L76-L101)) là khuôn mẫu: `_get_project_or_404` (JWT + owner) → driver → use case → response. Copy y hệt cho `/gaps/detailed`.
- **Không-raise pattern:** `gap_detection` ([use_cases.py:249-301](backend/src/modules/graph_rag/application/use_cases.py#L249-L301)) bọc cả mở-session lẫn từng query, log warning, trả rỗng. `gap_detection_detailed` phải y vậy.
- **Tab shell + `›`:** [CenterWorkspace.tsx:16-40](frontend/src/features/workspace/CenterWorkspace.tsx#L16-L40) — pattern nút + `tabSep` + `display:none`. Lưu ý panel `graph` có style đặc biệt (`margin:-24px`, flex) để Cytoscape full-bleed; panel `gaps` dùng layout cuộn dọc bình thường như `library`.
- **Bridge Gap→Chat ĐÃ CÓ:** `pendingChatInput` trong [workspaceStore.ts:9](frontend/src/store/workspaceStore.ts#L9) + consumer [ChatBar.tsx:52-58](frontend/src/features/workspace/ChatBar.tsx#L52-L58). Hành vi: **prefill ô chat + focus** (KHÔNG auto-send). Đủ cho nút "Giải thích".
- **FR15 đã an toàn sẵn:** `GetSuggestionsUseCase.execute` ([use_cases.py:240-257](backend/src/modules/orchestrator/application/use_cases.py#L240-L257)) **chỉ nhánh theo `document_count` và `has_draft`**, KHÔNG đọc `active_tab`. Truyền `'gaps'` không gây lỗi. Field schema là `str` ([schemas.py:78](backend/src/modules/orchestrator/presentation/schemas.py#L78)), không phải Enum → không vỡ validation. **Không cần đổi BE cho AC#7** (chỉ xác nhận test ChatBar không lỗi).

### Cầu Gap→Map (phần khó nhất FE)

`gapMode` là `useState` cục bộ trong `KnowledgeMapTab` ([dòng 179](frontend/src/features/workspace/KnowledgeMapTab.tsx#L179)) và logic toggle/pulsing/loadGraph phụ thuộc nó qua refs. **KHÔNG nâng `gapMode` lên store** (sẽ phải refactor nhiều effect → rủi ro regression AC#8). Thay vào đó dùng **signal một chiều**: store giữ `gapFocusRequest`, GapTab set, KnowledgeMapTab tiêu thụ rồi clear. Trong effect tiêu thụ: bật `setGapMode(true)`, chờ `gapData` (đã có effect fetch khi gapMode ON, dòng 357-386) rồi `cy.getElementById(paperId).select()` + center. Vì load graph + gap có độ trễ, nên focus trong một effect phụ thuộc `[gapData, gapFocusRequest, graphNodes]`.

### Refactor state dùng chung LibraryTab (rủi ro chính FE)

Hiện toàn bộ state ở [LibraryTab.tsx:26-36](frontend/src/features/workspace/LibraryTab.tsx#L26-L36). Khi tách 2 tab con: `papers`/`maxPapers`/`isAtLimit`/`addingPapers`/`processingDocumentIds`/`docRefreshTrigger` + `handleAddFromSearch`/`handleIngestion*` **ở lại cha**. `DocumentList` gọi `onPapersLoad={setPapers}` → đây là nguồn sự thật `papers.length` → `isAtLimit`. Khi user ở tab "Tìm kiếm" bấm "Thêm vào dự án", `handleAddFromSearch` (ở cha) chạy → `setDocRefreshTrigger` → DocumentList (ở tab khác, vẫn mounted vì segmented dùng display) refetch → `setPapers` → counter đồng nhất. **Giữ cả 2 child mounted** (display:none) để `searchResult` và `DocumentList` không mất state khi đổi tab con.

### Project Structure Notes

- Backend tuân Clean Architecture sẵn có: domain (`entities.py`) → application (`use_cases.py`) → presentation (`schemas.py`/`router.py`). Endpoint mới nằm trong module `graph_rag`, đúng nguyên tắc 3 trục (mọi đọc Neo4j thuộc `graph_rag`).
- Frontend: feature components trong `frontend/src/features/workspace/`, store zustand trong `frontend/src/store/`, api trong `frontend/src/api/`, types trong `frontend/src/types/`, i18n trong `frontend/src/i18n/translations.ts`. GapTab là component mới cùng thư mục workspace.
- **Không đổi** architecture.md / schema Neo4j / Postgres (xác nhận trong sprint-change-proposal §4: "architecture.md không cần đổi"). Không thêm node/edge mới.
- ⚠️ **Working tree có thay đổi chưa commit** ở một feature khác (chat history CRUD): `ChatBar.tsx`, `api/chat.ts`, `chatStore.ts`, `translations.ts`, `DashboardPage.*`, `ConversationColumn.*`, orchestrator chat-threads. **File của 4.10 (`CenterWorkspace.tsx`, `LibraryTab.tsx`, `workspaceStore.ts`, graph_rag BE, `api/graph.ts`, `types/graph.ts`) KHÔNG nằm trong tập đang sửa** — nhưng `translations.ts` thì CÓ → thêm key cẩn thận, tránh đè block người khác.

### Testing standards summary

- **Backend:** pytest + `pytest.mark.asyncio`. Tái dùng fakes Neo4j trong [test_gap_detection.py](tests/unit/graph_rag/test_gap_detection.py) (`_FakeNeo4jDriver` cấp record theo `run_side_effects` tuần tự; mỗi record là dict — đặt đúng tên cột mới như `finding1_text`, `paper1_title`). Router test mock auth + repo (xem mẫu trong test_graph_router.py).
- **Frontend:** Vitest + Testing Library. Mock store qua `vi.mock('@/store/...')` (xem [CenterWorkspace.test.tsx](frontend/src/features/workspace/__tests__/CenterWorkspace.test.tsx) đầu file), mock api `fetchGapsDetailed`. Test theo role/label tiếng Việt (`getByRole('button', { name: '...' })`).
- Chạy: backend `pytest tests/unit/graph_rag/`, frontend `npm test` trong `frontend/`.

### References

- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-21-tab-restructure-gap-view.md] — nguồn gốc, mọi quyết định chốt (Dat 2026-06-21): card tất định không LLM, 1 story gộp BE trước→FE sau.
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.10] (dòng 526–546) — AC nháp + nhãn module/role + phụ thuộc.
- [Source: _bmad-output/planning-artifacts/epics.md#UX-DR1] (dòng 59) — 4 tab + 2 tab con.
- [Source: test-data/mockups/layout-tabs-restructure.html / .png] — mockup Dat duyệt 2026-06-21 (lưu ý nhãn loại gap là flavor minh hoạ, theo Story 4.8 cho dữ liệu thật).
- [Source: backend/src/modules/graph_rag/application/use_cases.py#GapDetectionUseCase] — Cypher gap + không-raise pattern để mở rộng.
- [Source: backend/src/modules/graph_rag/infrastructure/neo4j_adapter.py#L199-L230] — xác nhận property `.description` của Finding/Limitation.
- [Source: frontend/src/features/workspace/KnowledgeMapTab.tsx#L127-L150] — bảng màu 3 loại gap (Story 4.8) để tái dùng.

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- **ConversationColumn tests fail (setThinkingStatus)**: ChatBar.tsx destructures `setThinkingStatus` từ `useChatStore` nhưng mock trong ConversationColumn.test.tsx không bao gồm nó. Sửa bằng cách thêm `setThinkingStatus: () => {}` và các field còn thiếu (`activeThreadId`, `setStreaming`, `appendChunk`, v.v.) vào mock.
- **ConversationColumn title changed accidentally**: Trong quá trình triển khai, `t('chat.conversationTitle')` bị thay thành `t('chat.title')`. Phát hiện qua test failure, đã revert về `'chat.conversationTitle'`.
- **CenterWorkspace tests crash (Cytoscape)**: KnowledgeMapTab render Cytoscape trong jsdom gây `Error: Could not create canvas of type 2d`. Sửa bằng `vi.mock('../KnowledgeMapTab', ...)`.
- **Multiple element matches**: "Mâu thuẫn"/"Limitation chưa giải quyết"/"Cụm cô lập" xuất hiện cả ở group title lẫn badge trong card → dùng `getAllByText` thay `getByText`.

### Completion Notes List

- Tất cả 8 AC được thực hiện đầy đủ theo thứ tự BE→FE.
- Backend: 3 Cypher DETAILED mới (`_CYPHER_CONTRADICTS_DETAILED`, `_CYPHER_ISOLATED_DETAILED`, `_CYPHER_UNFILLED_LIMITATION_DETAILED`) không sửa hằng cũ — AC#8 regression an toàn.
- Frontend: `workspaceStore` thêm `librarySubTab` + `gapFocusRequest` signal. LibraryTab tách thành cha + `DocumentsSubTab` + `SearchSubTab` với single-source-of-truth cho counter (AC#5). GapTab mới với 3 màu Story 4.8. KnowledgeMapTab tiêu thụ `gapFocusRequest` signal.
- Test: 137 FE tests pass (19 files), 262 BE tests pass (pre-existing 1 fail + 35 errors trong test_projects_api — không phải từ story này, confirmed via git stash).

### File List

**Backend:**
- `backend/src/modules/graph_rag/domain/entities.py` — thêm `GapPaperRef`, `GapDetailItem`
- `backend/src/modules/graph_rag/presentation/schemas.py` — thêm `GapPaperRef`, `GapDetailItem`, `GapDetailResponse`
- `backend/src/modules/graph_rag/application/use_cases.py` — thêm 3 Cypher DETAILED + `gap_detection_detailed()`
- `backend/src/modules/graph_rag/presentation/router.py` — thêm endpoint `GET /{project_id}/graph/gaps/detailed`
- `tests/unit/graph_rag/test_gap_detection.py` — thêm 7 tests cho `gap_detection_detailed`
- `tests/unit/graph_rag/test_graph_router.py` — thêm 5 tests cho `/graph/gaps/detailed` endpoint

**Frontend:**
- `frontend/src/store/workspaceStore.ts` — `TabKey` += `'gaps'`; thêm `librarySubTab`, `gapFocusRequest`, `requestGapFocus`, `clearGapFocus`
- `frontend/src/types/graph.ts` — thêm `GapPaperRef`, `GapDetailItem`, `GapDetailResponse`
- `frontend/src/api/graph.ts` — thêm `fetchGapsDetailed()`
- `frontend/src/features/workspace/CenterWorkspace.tsx` — 4 tab, thêm Gaps tab panel
- `frontend/src/features/workspace/LibraryTab.tsx` — refactor: cha giữ shared state, tách `DocumentsSubTab` + `SearchSubTab`
- `frontend/src/features/workspace/LibraryTab.module.css` — thêm `.subTabBar`, `.subTab`, `.subTabActive`
- `frontend/src/features/workspace/GapTab.tsx` — component mới (gap cards, 3 màu, 2 nút)
- `frontend/src/features/workspace/GapTab.module.css` — styles mới
- `frontend/src/features/workspace/KnowledgeMapTab.tsx` — thêm effect tiêu thụ `gapFocusRequest`
- `frontend/src/features/workspace/ConversationColumn.tsx` — revert accidental key change
- `frontend/src/i18n/translations.ts` — thêm `tab.gaps`, `library.searchSubTab`, `library.uploadOffline`, `gapTab.*`
- `frontend/src/features/workspace/__tests__/CenterWorkspace.test.tsx` — 4 tabs, mock KnowledgeMapTab
- `frontend/src/features/workspace/__tests__/LibraryTab.test.tsx` — segmented control + counter sharing test
- `frontend/src/features/workspace/__tests__/GapTab.test.tsx` — file mới (9 tests)
- `frontend/src/features/workspace/__tests__/KnowledgeMapTab.test.tsx` — update store mock
- `frontend/src/features/workspace/__tests__/ConversationColumn.test.tsx` — update chatStore mock

### Change Log

- 2026-06-22: Story triển khai hoàn chỉnh bởi claude-sonnet-4-6. BE: 3 Cypher DETAILED + use case + endpoint + 12 tests mới. FE: workspaceStore mở rộng, LibraryTab tách 2 sub-tab, GapTab mới, KnowledgeMapTab gap→map bridge, i18n, 4 test files updated/created. 137 FE + 262 BE tests pass. Status → review.
- 2026-06-22: Code review (bmad-code-review, 3 lớp adversarial) + áp 7 patch. Status → done. 140 FE + 73 graph_rag BE tests pass.
- 2026-06-22: UX follow-up (Dat phản hồi tiêu đề card khó hiểu) — tiêu đề card gap viết lại ngắn gọn theo LOẠI (không nhồi tên bài → hết lỗi "Mâu thuẫn giữa X và X" khi mâu thuẫn nội tại cùng 1 bài); phân biệt mâu thuẫn nội tại vs giữa-hai-bài; thêm dòng "Nghiên cứu liên quan" (khử trùng theo paper_id) hiển thị tên bài; prompt "Giải thích" kèm tên bài. Quyết định: giữ template tất định (không gọi LLM runtime — tức thời/miễn phí/ổn định). 141 FE + 74 graph_rag BE tests pass, build xanh.

## Review Findings (2026-06-22)

Code review qua `bmad-code-review` (3 lớp song song: Blind Hunter / Edge Case Hunter / Acceptance Auditor). **Tất cả AC#1–#8 được xác nhận đạt.** Các phát hiện đã được fix ngay trong review (durably authorized "fix hết"):

**Patch — đã fix:**
- [x] [Review][Patch] Gap→Map bridge: node KHÔNG center lần đầu (race giữa graph load và gapData) + rò rỉ `gapFocusRequest` qua các lần mở tab Bản đồ sau — chờ `graphNodes`+`gapData` sẵn sàng rồi mới center & clear [frontend/src/features/workspace/KnowledgeMapTab.tsx:409]
- [x] [Review][Patch] Card "Mâu thuẫn" bị trùng khi cạnh CONTRADICTS đối xứng (f1→f2 & f2→f1) — khử trùng theo cặp finding [backend/src/modules/graph_rag/application/use_cases.py:344]
- [x] [Review][Patch] Dòng "bằng chứng" lộ ID nội bộ (finding/limitation UUID) ra UI — đổi `evidence` sang số liệu (finding_count/paper_count/neighbor_count/filler_count) + nhãn i18n + chặn render giá trị non-scalar [backend …/use_cases.py + frontend …/GapTab.tsx + translations.ts]
- [x] [Review][Patch] Test AC#5 (counter dùng chung — rủi ro chính) chỉ assert `addPaperFromSearch` được gọi, chưa chứng minh non-divergence — tăng cường: add-from-search ở tab Tìm kiếm làm tab Tài liệu đạt giới hạn [frontend …/__tests__/LibraryTab.test.tsx]
- [x] [Review][Patch] Bridge Gap→Map chưa có test (effect lỗi không bị bắt) — thêm 2 test coverage [frontend …/__tests__/KnowledgeMapTab.test.tsx]
- [x] [Review][Patch] LibraryTab.test không reset store zustand giữa các test (dễ vỡ theo thứ tự) — reset trong beforeEach [frontend …/__tests__/LibraryTab.test.tsx]
- [x] [Review][Patch] Prop `papers` thừa truyền vào `DocumentsSubTab` (không dùng) — gỡ bỏ [frontend …/LibraryTab.tsx]

**Defer / Dismiss:**
- [x] [Review][Defer] "Mở trên Bản đồ" chỉ focus `papers[0]` của contradiction — mặc định hợp lý (gap-mode vẫn tô viền cả 2 paper). Không đổi.
- [x] [Review][Defer] Paper `title` NULL → hiện paper id (đã có fallback `or paper_id`, không in "None"). Hiếm gặp vì metadata luôn có title.
- [x] [Review][Dismiss] `translations.ts` lỗi prettier — pre-existing, toàn file, không do story này; build (`tsc -b && vite build`) không enforce eslint.
