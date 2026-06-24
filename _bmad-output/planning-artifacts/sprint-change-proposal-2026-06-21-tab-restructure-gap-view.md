# Sprint Change Proposal — Tái cấu trúc Tab Workspace: Tách tab Thư viện + Tab "Khoảng trống Nghiên cứu" (card giàu)

- **Ngày:** 2026-06-21
- **Người đề xuất:** Dat
- **Workflow:** correct-course (BMad)
- **Mode review:** Batch
- **Phân loại phạm vi:** **Moderate** — **1 story gộp BE+FE (4.10)**. Backend: thêm **1 endpoint đọc gap "giàu"** ở module `graph_rag` (Cypher tất định, **không LLM**), mở rộng `RETURN` của các query gap đã có. Frontend: tái cấu trúc shell tab `CenterWorkspace` + tách tab Thư viện + tab "Khoảng trống Nghiên cứu". KHÔNG đổi architecture/schema, KHÔNG mở lại story đã done.

---

## Section 1 — Issue Summary

### Vấn đề / Yêu cầu mới
Yêu cầu UX từ Dat (sau khi Epic 4 done), tinh chỉnh điều hướng vùng giữa workspace (`CenterWorkspace` — hiện 3 tab `library › graph › writing`):

1. **Tab "Thư viện Tài liệu" đang gộp 3 chức năng vào một màn** ([LibraryTab.tsx](frontend/src/features/workspace/LibraryTab.tsx)): ô tìm kiếm + nút upload + danh sách tài liệu cuộn chung. Yêu cầu **tách thành 2 tab con**:
   - **"Tài liệu trong dự án"** — danh sách tài liệu (DocumentList) + **nút upload báo cáo offline**.
   - **"Tìm kiếm báo cáo khoa học"** — ô tìm kiếm + kết quả arXiv / Semantic Scholar (+ "Thêm vào dự án").

2. **Khoảng trống nghiên cứu (FR7) hiện chỉ là chế độ ẩn trong Bản đồ Tri thức** (gap-mode toggle Story 4.4/4.8) — khó khám phá. Yêu cầu **thêm tab lớn "Khoảng trống Nghiên cứu"** đặt **giữa "Bản đồ Tri thức" và "Hỗ trợ viết tổng quan"**, hiển thị danh sách khoảng trống **dạng card giàu** (tiêu đề mô tả, đoạn giải thích, số liệu bằng chứng) như mockup khung 3.

### Bằng chứng từ code
| Quan sát | Vị trí |
|---|---|
| `LibraryTab` gộp searchBar + uploadButton + searchResults + DocumentList | [LibraryTab.tsx](frontend/src/features/workspace/LibraryTab.tsx) |
| Tab shell cứng 3 tab `library / graph / writing` | [CenterWorkspace.tsx:16-40](frontend/src/features/workspace/CenterWorkspace.tsx#L16-L40) |
| `TabKey = 'library' \| 'graph' \| 'writing'` (chưa có `'gaps'`) | [workspaceStore.ts:3](frontend/src/store/workspaceStore.ts#L3) |
| Gap detection chỉ sống trong gap-mode của Knowledge Map | [KnowledgeMapTab.tsx:179](frontend/src/features/workspace/KnowledgeMapTab.tsx#L179) |
| Backend gap **đã có**: `GET /{project_id}/graph/gaps` + `gap_detection()` Cypher | [router.py:76](backend/src/modules/graph_rag/presentation/router.py#L76), [use_cases.py:249](backend/src/modules/graph_rag/application/use_cases.py#L249) |
| **Đồ thị đã lưu dữ liệu giàu**: `Finding` có text, `Limitation` có `description`, `Paper` có title; query `_CYPHER_CONTRADICTS` trả finding/paper ids, `_CYPHER_UNFILLED_LIMITATION_FULL` trả `limitation_id/description/owner_paper_id` | [use_cases.py:195-228](backend/src/modules/graph_rag/application/use_cases.py#L195-L228) |
| **Nhưng** `GapResponse` hiện thu gọn còn `{paper_id, reason}` + `flagged_edges` → mất prose | [types/graph.ts:39-55](frontend/src/types/graph.ts#L39-L55) |

### Mockup đã chốt
`test-data/mockups/layout-tabs-restructure.html` → `…png` (Dat duyệt 2026-06-21). 3 khung: tab con "Tài liệu", tab con "Tìm kiếm", tab lớn "Khoảng trống Nghiên cứu" (card giàu).

### Hệ quả (nếu không làm)
- Thư viện rối: search + quản lý tài liệu trộn một màn.
- FR7 (giá trị trí tuệ cốt lõi — 5 story 4.3–4.8) bị **chôn** trong toggle của tab Graph; dữ liệu gap giàu (finding/limitation text) đang có trong đồ thị nhưng **không được bề mặt nào hiển thị**.

---

## Section 2 — Impact Analysis

### Epic Impact
- **Epic 4** (`done`, đã nhiều lần mở lại cho follow-up FR7): thêm **Story 4.10 [BE+FE]** — bề mặt mới + endpoint đọc giàu cho FR7/FR9 đã build, đồng thời tái tổ chức UI Epic 2 (FR3/FR5/FR16). Không build logic phát hiện gap mới (tái dùng `gap_detection` Cypher).
- **Epic 2** (`in-progress`): search/upload/document-list **di chuyển/tổ chức lại** vào 2 tab con, KHÔNG đổi hành vi.
- **Epic 5 / khác:** không chạm; tab "Hỗ trợ viết tổng quan" chỉ dịch vị trí sau tab mới.

### Story Impact
| Story | Ảnh hưởng |
|---|---|
| 4.4 (gap_detection + `/graph/gaps`) | **Mở rộng (không phá):** thêm endpoint **mới** `GET /graph/gaps/detailed` đọc giàu (giữ nguyên `/graph/gaps` cũ cho gap-mode trên Map). Tái dùng 3 query Cypher, chỉ **mở rộng `RETURN`** lấy thêm finding text / limitation description / paper title / đếm bằng chứng. |
| 4.8 (3 màu gap trên Map) | Tab mới **tái dùng bảng màu/nhãn 3 loại** (đỏ contradiction / cam unfilled / xanh isolated). Map gap-mode GIỮ NGUYÊN — coexist 2 view trên cùng dữ liệu. |
| 4.5 (Gap Analyst Agent) | Tái dùng cầu Gap→Chat: nút "Giải thích khoảng trống này" trên card gửi câu hỏi vào chat (Gap Analyst trả lời có nguồn). **Văn xuôi card KHÔNG gọi LLM** — chỉ nút giải thích mới gọi chat. |
| 3.3 (Chatbot định hướng FR15) | `getSuggestions({ activeTab })` ([ChatBar.tsx:76](frontend/src/features/workspace/ChatBar.tsx#L76)): `activeTab` thêm giá trị `'gaps'` (kiểu `string` ở [chat.ts:49](frontend/src/api/chat.ts#L49), không vỡ type). Backend suggestion cần xử lý `'gaps'` an toàn (fallback). |
| 2.2/2.3/2.4/2.5/2.6/2.7 | Search/broad-query/upload/ingestion/limit/document-CRUD **di chuyển nguyên trạng** vào 2 tab con. |

### Artifact Conflicts (cần cập nhật)
- `epics.md`: thêm **Story 4.10**; cập nhật dòng tổng số story; cập nhật "Khoảng trống đã biết"; ghi chú UX-DR1 (3→4 tab).
- `sprint-status.yaml`: thêm `4-10-…` = `backlog` (comment follow-up correct-course 2026-06-21).
- `architecture.md`: **không cần đổi** — endpoint mới tuân §5.2/§8.4 (đọc Neo4j, scope `project_id`, owner JWT), không schema/node/edge mới.
- `ux-designs/`: đính kèm mockup `test-data/mockups/layout-tabs-restructure.html`.

### Technical Impact
**Backend (`graph_rag`) — endpoint đọc gap giàu, tất định:**
- Thêm use case `gap_detection_detailed(project_id) -> list[GapDetailItem]` (cạnh `gap_detection` cũ), tái dùng `_CYPHER_CONTRADICTS` / `_CYPHER_UNFILLED_LIMITATION_FULL` / `_CYPHER_ISOLATED`, **mở rộng `RETURN`** lấy: finding text (2 phía mâu thuẫn), limitation `description` + owner paper, paper title, và đếm bằng chứng (vd số neighbor = 0 cho isolated, số paper liên quan).
- Endpoint `GET /api/projects/{project_id}/graph/gaps/detailed` → schema `GapDetailResponse { items: GapDetailItem[] }`. JWT + owner scoping (mirror `/graph/gaps`). Bọc try/except → rỗng khi Neo4j sự cố (giữ pattern AC#4 của 4.4, không raise).
- **Không LLM** trong endpoint này (chi phí 0 token); corpus ≤ `MAX_PAPERS=15` → Cypher rất rẻ.
- `GapDetailItem`: `{ id, type: 'contradiction'|'unfilled_limitation'|'isolated_cluster', reason, title, description, papers: [{paper_id, title}], evidence: {...counts/texts} }`. Văn xuôi `title`/`description` **template từ entity thật** (finding text / limitation description / title), không sinh tự do.

**Frontend:**
- `workspaceStore`: `TabKey` thêm `'gaps'`; thêm `librarySubTab: 'documents' | 'search'` (mặc định `'documents'`).
- **Refactor `LibraryTab`** thành segmented control + 2 child view — **rủi ro chính: state dùng chung** (`papers`/`documentCount`/`isAtLimit`/`MAX_PAPERS`/`processingDocumentIds`/`addingPapers`) phải **nâng lên cha `LibraryTab`**, truyền xuống cả 2 tab con (để add-from-search ở tab "Tìm kiếm" cập nhật đúng counter/giới hạn ở tab "Tài liệu"; KHÔNG để mỗi tab con giữ state riêng → lệch counter `MAX_PAPERS`).
- **`GapTab` (MỚI):** gọi `fetchGapsDetailed(projectId)`, render danh sách card giàu nhóm theo 3 reason (màu/nhãn tái dùng Story 4.8), mỗi card: tiêu đề + mô tả (text thật) + bằng chứng + nút "Mở trên Bản đồ Tri thức" (chuyển `activeTab='graph'` + gap-mode ON + focus) + "Giải thích khoảng trống này" (gửi chat → Gap Analyst 4.5).
- `api/graph.ts` + `types/graph.ts`: thêm `fetchGapsDetailed` + `GapDetailResponse`/`GapDetailItem`.
- i18n: keys `tab.gaps`, nhãn 2 tab con, nút "Upload báo cáo offline", chuỗi `GapTab` (tiêu đề, 3 nhãn loại, nhãn bằng chứng, empty state, 2 nút) — VI/EN.
- **Test:** `CenterWorkspace.test` (4 tab + thứ tự); tách test `LibraryTab` (2 tab con + **counter dùng chung không lệch**); test BE mới cho `gap_detection_detailed` (3 loại, ghép text/title, rỗng an toàn); test `GapTab` (render nhóm + empty + 2 nút).

---

## Section 3 — Recommended Approach

**Option 1 — Direct Adjustment (Hybrid):** **1 story gộp BE+FE (4.10)**, mở rộng backend gap có sẵn + tái cấu trúc shell FE. **Chọn phương án này** (theo lựa chọn của Dat).

- **Văn xuôi card tất định (không LLM)** — lựa chọn của Dat: đồ thị đã lưu finding text + limitation description, nên card giàu dựng được bằng Cypher thuần. **Chi phí 0 token, nhanh, chính xác theo dữ liệu thật.** Văn phong "kỹ thuật" (lấy nguyên văn học thuật) — chấp nhận được; muốn mượt hơn thì bấm "Giải thích khoảng trống này" để Gap Analyst (4.5) diễn giải.
- **1 story gộp** — lựa chọn của Dat: BE chỉ là mở rộng `RETURN` của query có sẵn (nhỏ, rủi ro thấp), gắn liền với FE tab mới → vertical slice gọn, 1 lần vibecode. **Khuyến nghị thực thi nội bộ: BE trước (endpoint + test) → FE sau** (FE cần endpoint để vẽ card).
- **Effort:** Medium · **Risk:** Low–Medium (tập trung ở refactor state dùng chung `LibraryTab` + regression coexistence gap-mode).

**Phương án đã cân nhắc & loại bỏ:**
- *FE-only template theo reason (không backend):* Loại — Dat muốn card giàu như mockup; template-theo-reason quá nghèo (chỉ paper title).
- *Thêm LLM per-gap (Gap Analyst sinh prose):* Loại cho MVP — tốn token; văn xuôi tất định từ entity thật đã đủ giàu. Để dành làm enhancement Phase sau nếu muốn prose mượt tự động.
- *Tách 2–3 story:* Loại — Dat chọn 1 story; BE nhỏ nên gộp hợp lý.
- *Rollback / MVP review:* N/A — không revert, không đổi PRD scope.

---

## Section 4 — Detailed Change Proposals

### 4.1 — Thêm Story 4.10 vào `epics.md` (Epic 4, chèn sau Story 4.9)

> ### Story 4.10: [BE+FE] Tái cấu trúc Tab Workspace — Tách tab Thư viện + Tab "Khoảng trống Nghiên cứu" (card giàu) — ⏳ backlog 🟡
>
> **BE —** endpoint đọc gap "giàu" tất định (không LLM): `gap_detection_detailed(project_id)` tái dùng 3 query Cypher của Story 4.4, mở rộng `RETURN` lấy finding text / limitation description / paper title / đếm bằng chứng; `GET /api/projects/{project_id}/graph/gaps/detailed` → `GapDetailResponse`. JWT + owner scoping, không raise (rỗng khi sự cố). Giữ nguyên `/graph/gaps` cũ cho gap-mode trên Map.
> **FE —** (1) shell **4 tab** `Thư viện › Bản đồ Tri thức › Khoảng trống Nghiên cứu › Hỗ trợ viết tổng quan`; (2) tách tab Thư viện thành 2 tab con segmented ("Tài liệu trong dự án" = DocumentList + Upload báo cáo offline + IngestionProgress + cảnh báo giới hạn; "Tìm kiếm báo cáo khoa học" = ô tìm kiếm + kết quả arXiv/Semantic Scholar + Thêm vào dự án + gợi ý MECE), **state dùng chung nâng lên cha**; (3) `GapTab` render card giàu nhóm theo 3 reason (màu Story 4.8) + nút "Mở trên Bản đồ" / "Giải thích khoảng trống này" (chat).
>
> - **Phát sinh:** correct-course 2026-06-21. Mockup: `test-data/mockups/layout-tabs-restructure.html`.
> - **🧭 Nhãn module/role:** `[graph_rag]` use case `gap_detection_detailed` + endpoint + schema (mở rộng, tái dùng Cypher) · `[frontend]` `CenterWorkspace`(+css), `LibraryTab` (tách 2 child + nâng state), `GapTab` (MỚI), `workspaceStore`, `api/graph.ts`+`types`, i18n.
> - **Phụ thuộc:** Story 4.4 (Cypher gap + `/graph/gaps`), 4.8 (3 màu), 4.2 (graph nodes/title), 4.5 (Gap Analyst cho nút giải thích). Tái dùng FR15 snapshot.
> - **Quyết định chốt (Dat 2026-06-21):** (a) văn xuôi card **tất định từ đồ thị, KHÔNG LLM** (LLM chỉ khi bấm "Giải thích…"); (b) **1 story gộp**, làm **BE trước → FE sau**.
> - **FRs:** FR3, FR5, FR7, FR9, FR16. (UX-DR1 mở rộng 3→4 tab.)
>
> **AC nháp (chi tiết hóa khi create-story):**
> 1. **BE:** `gap_detection_detailed` trả list item cho cả 3 loại; CONTRADICTS kèm **2 finding text + 2 paper title**; unfilled limitation kèm **`description` + owner paper title**; isolated kèm **paper title + đếm neighbor (=0)**. Mỗi item có `type/reason/title/description/papers/evidence`.
> 2. **BE:** endpoint `GET /graph/gaps/detailed` JWT + owner scoping; Neo4j lỗi → `items: []` (không raise); scope `project_id` chống IDOR. `/graph/gaps` cũ **không đổi**.
> 3. **FE shell:** 4 tab đúng thứ tự, có `›` ngăn cách (pattern 3.8), active đúng, default `library`.
> 4. **FE Thư viện:** 2 tab con segmented, mặc định "Tài liệu". Tab "Tài liệu" = DocumentList + Upload offline + IngestionProgress + cảnh báo `MAX_PAPERS`; xóa/sửa/xem PDF giữ nguyên (2.7). Tab "Tìm kiếm" = search + kết quả + Thêm vào dự án + MECE + degraded-union toast; giữ `searchIdRef`.
> 5. **FE counter dùng chung:** add-from-search ở tab "Tìm kiếm" cập nhật counter/giới hạn ở tab "Tài liệu" — **một nguồn sự thật** `papers`/`MAX_PAPERS` ở cha (test riêng điểm này).
> 6. **FE GapTab:** card giàu nhóm theo 3 reason, tiêu đề/mô tả/bằng chứng từ endpoint, màu khớp 4.8, empty state khi 0 gap, nút "Mở trên Bản đồ Tri thức" (graph tab + gap-mode + focus) + "Giải thích khoảng trống này" (chat) chạy đúng.
> 7. **FR15:** `activeTab='gaps'` vào `getSuggestions` không lỗi; fallback an toàn nếu chưa có template gợi ý.
> 8. **Regression:** Map gap-mode (4.4/4.8) + Node Detail + 3 màu vẫn đúng; Cytoscape re-fit khi đổi tab; responsive; i18n VI/EN đủ.

### 4.2 — Cập nhật dòng tổng số story (epics.md, "Trạng thái thực thi")
Thêm: *"+1 story BE+FE 4.10 — tái cấu trúc tab workspace (tách tab Thư viện 2 tab con + tab "Khoảng trống Nghiên cứu" card giàu, endpoint `/graph/gaps/detailed` tất định), correct-course 2026-06-21."*

### 4.3 — Cập nhật "Khoảng trống đã biết" (epics.md)
Thêm: *"UI Tab Restructure + Gap rich view (FR3/5/7/9) — ✅ Đã tạo Story 4.10. Mockup `test-data/mockups/layout-tabs-restructure.html`. Tham chiếu `sprint-change-proposal-2026-06-21-tab-restructure-gap-view.md`."*

### 4.4 — Cập nhật `sprint-status.yaml` (dưới `epic-4`, sau `4-9-…`)
```yaml
  # follow-up correct-course 2026-06-21 (sprint-change-proposal-2026-06-21-tab-restructure-gap-view.md):
  # tái cấu trúc tab workspace: tách tab Thư viện 2 tab con + tab "Khoảng trống Nghiên cứu" card giàu.
  # BE: endpoint /graph/gaps/detailed (Cypher tất định, không LLM). FE: shell 4 tab + GapTab. 1 story gộp, BE trước → FE.
  4-10-tai-cau-truc-tab-workspace-tab-thu-vien-va-khoang-trong-nghien-cuu: backlog
```

### 4.5 — Cập nhật mô tả UX-DR1 (epics.md)
Sửa *"thanh Tab ngang: Thư viện tài liệu, Bản đồ tri thức, Hỗ trợ viết tổng quan"* → **4 tab** (thêm "Khoảng trống Nghiên cứu" giữa Bản đồ và Hỗ trợ viết) + tab Thư viện có 2 tab con.

---

## Section 5 — Implementation Handoff

- **Phân loại phạm vi:** **Moderate** — 1 story BE+FE, tái tổ chức backlog, không đổi architecture/schema.
- **Định tuyến:** **Product Owner / Developer (PO/DEV)** — cập nhật backlog (epics.md + sprint-status) → `bmad-create-story` cho 4.10 → `bmad-dev-story`.
- **Trách nhiệm:**
  - *PO/DEV:* chốt proposal → cập nhật `epics.md` + `sprint-status.yaml` → tạo story 4.10 (chi tiết hóa AC: hợp đồng `GapDetailItem`, khế ước state dùng chung `LibraryTab`).
  - *DEV:* **BE trước** (mở rộng Cypher `RETURN` + endpoint + test 3 loại gap) → **FE sau** (shell + library split + GapTab). Viết test ngay cho **counter `MAX_PAPERS` dùng chung** + regression gap-mode coexistence.
- **Tiêu chí thành công:** 4 tab + 2 tab con + card gap giàu khớp mockup; search/upload/document-list/gap-mode không regress; counter giới hạn đồng nhất; FR15 không vỡ; endpoint không tốn LLM; VI/EN đủ.
- **Không yêu cầu PM/Architect** (không đổi PRD scope/architecture).
