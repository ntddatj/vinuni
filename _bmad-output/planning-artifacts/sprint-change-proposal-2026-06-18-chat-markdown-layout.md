# Sprint Change Proposal — Render Markdown Chat + Tái cấu trúc Layout Workspace

- **Ngày:** 2026-06-18
- **Người đề xuất:** Dat
- **Workflow:** correct-course (BMad)
- **Mode review:** Batch
- **Phân loại phạm vi:** **Moderate** — thêm **2 story FE (3.7, 3.8)** vào Epic 3. Story 3.7 nhỏ (render markdown trong `MessageContent`); Story 3.8 lớn hơn (tái cấu trúc shell layout toàn app: `DashboardPage`/`CenterWorkspace`/`ChatbotPanel`/header). Không chạm backend, không đổi architecture.

---

## Section 1 — Issue Summary

### Vấn đề
Kiểm thử trực quan câu trả lời chatbot (Trợ lý nghiên cứu) phát hiện **2 vấn đề UX**:

1. **Markdown không được render.** Câu trả lời LLM trả về có `**bold**`, `*`, bullet list, heading, xuống dòng — nhưng hiển thị **dạng thô, viết liền không xuống dòng**, rất khó đọc. Truy nguyên: `frontend/src/components/MessageContent.tsx` chỉ **split text theo `[N]`** để chèn `CitationBadge`, **không xử lý markdown** — phần text còn lại render bằng `<span>` thuần.

2. **Bố cục cột chưa tối ưu cho luồng làm việc "hỏi trợ lý".** Layout hiện tại (`DashboardPage`): `[Sidebar dự án] [CenterWorkspace 3 tab] [ChatbotPanel: header+ô chat+messages, collapse/resize]` — ô chat **bị chôn trong** cột trợ lý bên phải; khi thu hẹp/ẩn cột trợ lý thì **mất luôn ô chat**. Người dùng muốn ô chat luôn truy cập được (tính năng chung toàn project) và đưa khu trò chuyện ra vị trí trung tâm.

### Bằng chứng từ code
| Quan sát | Vị trí |
|---|---|
| `MessageContent` không render markdown, chỉ split `[N]` → `CitationBadge` + `<span>` | `frontend/src/components/MessageContent.tsx` |
| Chưa có lib markdown nào trong `package.json` (không react-markdown/marked/remark) | `frontend/package.json` |
| Ô chat (input) nằm trong `ChatbotPanel`, cùng cột với messages + collapse → ẩn cột là mất ô chat | `frontend/src/features/workspace/ChatbotPanel.tsx` |
| Layout 3 cột flex cứng | `frontend/src/features/dashboard/DashboardPage.tsx` + `.module.css` |

### Hệ quả
- **FR6 (chatbot) trải nghiệm kém:** câu trả lời khó đọc → giảm giá trị tính năng cốt lõi.
- Luồng "hỏi trợ lý" không tiện: ô chat không phải lúc nào cũng hiện.

---

## Section 2 — Impact Analysis

### Epic Impact
- **Epic 3** (chat) `in-progress`: thêm **2 story FE (3.7, 3.8)**. Đây là cải thiện/hoàn thiện FR6 (chatbot UX), không mở lại story đã done.
- **Epic 4 / khác:** không chạm logic. Story 3.8 đổi shell layout → mọi tab (Library/KnowledgeMap/Review) hiển thị trong cột nội dung mới; cần regression test nhẹ để chắc 3 tab + Knowledge Map (Cytoscape resize) vẫn chạy đúng trong khung mới.

### Story Impact
| Story | Ảnh hưởng |
|---|---|
| 3.5 (Thẻ trích dẫn) | **Phải giữ nguyên hành vi:** `CitationBadge` + tooltip tiếp tục hoạt động sau khi bọc markdown (3.7). |
| 3.6 (Real RAG + citation_map) | Không đổi — markdown render trên `msg.content`/`citationMap` đã có. |
| ChatbotPanel (collapse/resize) | **Tái cấu trúc (3.8):** tách ô chat (input) ra **thanh độc lập trên cùng**; collapse/resize chỉ áp cho **vùng messages**, không ẩn ô chat. |

### Artifact Conflicts (cần cập nhật)
- `epics.md`: thêm Story 3.7, 3.8 vào Epic 3; cập nhật dòng tổng số story; cập nhật "Khoảng trống đã biết".
- `sprint-status.yaml`: thêm `3-7`, `3-8` = backlog.
- `architecture.md`: **không cần đổi** (UI layer thuần).
- `ux-designs/`: nên cập nhật mockup tham chiếu (đính kèm `test-data/mockups/layout-chat-top.html`).

### Technical Impact
- **Mới (3.7):** thêm dependency `react-markdown` + `remark-gfm` (bảng/list/gạch ngang) + `rehype-sanitize` (**bắt buộc** — nội dung do LLM sinh, chống XSS). Override renderer của `text`/`p` để chạy logic split `[N]` → `CitationBadge` hiện có (tái dùng nguyên `CitationBadge`).
- **Mới (3.8):** tái cấu trúc `DashboardPage` từ "flex 3 cột" → mô hình **hàng trên cùng (brand + nút hệ thống, một dải liền, kẻ ngang suốt) + dưới (sidebar dự án | main(ô chat độc lập trên cùng + thân: cột trò chuyện GIỮA · 3 tab PHẢI))**. State ô chat (input/suggestions) tách khỏi `ChatbotPanel` thành component dùng chung; messages giữ collapse/resize.
- **NFR:** streaming SSE — markdown render trên chuỗi đang chạy (markdown chưa đóng hiện tạm thô rồi tự đẹp khi token kế đến); chấp nhận được.

---

## Section 3 — Recommended Approach

**Direct Adjustment** — thêm 2 story FE độc lập. Tách 3.7 (nhỏ) khỏi 3.8 (lớn) theo nguyên tắc gộp của dự án (cùng mối quan tâm + cùng rủi ro mới gộp).

- **Lý do tách:** 3.7 = render text trong 1 component, rủi ro thấp, giá trị tức thì. 3.8 = đổi khung shell toàn app, rủi ro cao, chạm nhiều file. Gộp sẽ thành PR khổng lồ FE khó review/test.
- **Hướng thay thế đã cân nhắc & loại bỏ:**
  - *Nhét vào Story 4.8 (gap màu):* Loại — khác FR (FR6 chat vs FR9 map), khác màn hình, không liên quan gap.
  - *Gộp 3.7+3.8:* Loại — như trên, trộn 2 mức rủi ro.
- **Quyết định thiết kế đã chốt (Dat 2026-06-18, qua mockup `test-data/mockups/layout-chat-top.html`):**
  - Brand **"Trợ lý nghiên cứu"** thay "C2 Research", nằm góc trái **hàng trên cùng**; hàng trên cùng là **một dải liền** (brand + nút hệ thống), tách phần dưới bằng **một đường kẻ ngang chạy suốt**.
  - **Ô chat độc lập** ngay dưới hàng trên cùng, **rộng ~½ màn hình, canh giữa**, luôn hiển thị (tính năng chung toàn project).
  - **Cột "Nội dung trò chuyện" ở GIỮA**, **cột nội dung 3 tab ở PHẢI**; 3 tab có dấu **`›`** ngăn cách.
  - Cột trò chuyện **kéo mở rộng/thu hẹp/ẩn** như cũ; **thu hẹp/ẩn chỉ ẩn vùng messages, KHÔNG ẩn ô chat**.
  - **Khi thu hẹp/ẩn cột trò chuyện → cột 3 tab GIÃN RỘNG chiếm chỗ trống** (quyết định Dat 2026-06-18).
- **Effort:** 3.7 thấp; 3.8 trung bình-cao (tái cấu trúc layout + di chuyển state ô chat + đảm bảo Cytoscape resize đúng trong khung mới).
- **Rủi ro chính:** (a) tích hợp `CitationBadge` vào trong cây markdown (badge nằm trong `<p>`/`<li>`/`<td>`); (b) Cytoscape (Knowledge Map) cần re-fit khi cột nội dung đổi kích thước lúc collapse; (c) regression layout responsive.

### Khuyến nghị thứ tự thực thi
```
3.7 (markdown — nhỏ, demo ngay) → 3.8 (layout — lớn)
```

---

## Section 4 — Detailed Change Proposals

### 4.A — Story mới (thêm vào `epics.md`, sau Story 3.6)

```
### Story 3.7: [Frontend] Render Markdown trong câu trả lời Chatbot (giữ CitationBadge) — ⏳ backlog 🟢

Bọc nội dung câu trả lời chatbot bằng react-markdown + remark-gfm + rehype-sanitize để render đẹp
(heading, bullet/numbered list, bold/italic, bảng, xuống dòng), ĐỒNG THỜI giữ nguyên thẻ trích dẫn [N]
tương tác (CitationBadge + tooltip Story 3.5) bằng cách override renderer text/p để chạy logic split [N].

- **Phát sinh:** correct-course 2026-06-18 (câu trả lời hiện markdown thô, viết liền khó đọc).
- **🧭 Nhãn module/role:** [frontend] thuần — components/MessageContent.tsx (+ CitationBadge tái dùng).
- **Phụ thuộc:** Story 3.5 (CitationBadge), Story 3.6 (content + citationMap). KHÔNG phụ thuộc 3.8.
- **FRs:** FR6.

**AC nháp (chi tiết hóa khi create-story):**
1. Thêm react-markdown + remark-gfm + rehype-sanitize vào frontend; sanitize BẮT BUỘC (nội dung LLM sinh).
2. MessageContent render markdown của msg.content; heading/list/bold/italic/bảng/xuống dòng hiển thị đúng.
3. Thẻ [N] trong markdown vẫn render thành CitationBadge tương tác (override renderer text/p; tái dùng CitationBadge + citationMap ordinal→UUID), kể cả khi [N] nằm trong <p>/<li>/<td>.
4. Streaming: markdown render trên chuỗi đang chạy; markdown chưa đóng hiện tạm thô rồi tự đẹp khi token tới — không crash.
5. Không phá link tooltip Story 3.5; không mở lỗ XSS (test thử input markdown độc hại).
6. Tin nhắn user (không có citationMap) vẫn render an toàn.
```

```
### Story 3.8: [Frontend] Tái cấu trúc Layout Workspace — Ô chat độc lập trên cùng + đảo cột — ⏳ backlog 🟡

Tái cấu trúc shell layout (DashboardPage): hàng trên cùng = brand "Trợ lý nghiên cứu" (thay "C2 Research")
+ nút hệ thống thành MỘT dải liền, tách phần dưới bằng kẻ ngang suốt. Phần dưới: sidebar dự án (trái) |
main = Ô CHAT ĐỘC LẬP trên cùng (~½ màn, canh giữa, luôn hiện) + thân (cột "Nội dung trò chuyện" GIỮA,
kéo mở rộng/thu hẹp/ẩn — chỉ ẩn messages, KHÔNG ẩn ô chat; cột nội dung 3 tab PHẢI có dấu › ngăn cách,
GIÃN RỘNG khi cột trò chuyện thu hẹp). Ô chat tách khỏi ChatbotPanel thành component dùng chung toàn project.

- **Phát sinh:** correct-course 2026-06-18. Tham chiếu mockup: test-data/mockups/layout-chat-top.html.
- **🧭 Nhãn module/role:** [frontend] thuần — DashboardPage(+css), ChatbotPanel (tách input/messages), CenterWorkspace (3 tab + sep), header/brand.
- **Phụ thuộc:** Story 3.6 (chat hoạt động). Nên làm SAU 3.7 để câu trả lời đã đẹp.
- **FRs:** FR6, FR9 (Knowledge Map nằm trong cột nội dung).

**AC nháp:**
1. Hàng trên cùng: brand "🔬 Trợ lý nghiên cứu" + badge project (góc trái) + nút Cài đặt/API Keys/đổi theme/VI|EN/Đăng xuất (phải) — MỘT dải liền KHÔNG vạch dọc, tách phần dưới bằng 1 đường kẻ ngang chạy suốt.
2. Ô chat độc lập (input + nút Gửi + suggestion pills) ngay dưới hàng trên cùng, rộng ~50% màn (min hợp lý), canh giữa; LUÔN hiển thị bất kể trạng thái cột trò chuyện.
3. Sidebar dự án bên trái (Tạo dự án + danh sách) — viền phải chỉ chạy ở phần dưới hàng trên cùng.
4. Cột "Nội dung trò chuyện" Ở GIỮA: chỉ chứa messages, có resize handle + nút collapse/ẩn (giữ hành vi cũ); thu hẹp/ẩn → chỉ ẩn messages.
5. Cột nội dung 3 tab Ở BÊN PHẢI: tab có dấu › ngăn cách; khi cột trò chuyện thu hẹp/ẩn → cột 3 tab GIÃN RỘNG chiếm chỗ trống.
6. Gửi tin từ ô chat độc lập → vẫn route đúng vào luồng chat hiện có (thread/SSE Story 3.1/3.2/3.6); state input dùng chung, không phụ thuộc cột trò chuyện hiển thị hay không.
7. Knowledge Map (Cytoscape) re-fit đúng khi cột nội dung đổi kích thước (collapse cột trò chuyện); không vỡ layout 3 tab.
8. Regression: 3 tab + Node Detail + gap mode (Story 4.2/4.4) chạy đúng trong khung mới; responsive không vỡ.
```

### 4.B — Cập nhật dòng trạng thái tổng (`epics.md` dòng ~155)

```
OLD: Tổng: **31 story** (... +3 story follow-up 4.6/4.7/4.8 ...).
NEW: Tổng: **33 story** (... +3 story follow-up 4.6/4.7/4.8 ...; **+2 story FE 3.7/3.8** — render markdown chat + tái cấu trúc layout workspace, correct-course 2026-06-18).
```

### 4.C — `sprint-status.yaml` (khối epic-3, trước `epic-3-retrospective`)

```
OLD:
  3-6-real-rag-retriever-pgvector-citation-map-sse: done
  epic-3-retrospective: optional
NEW:
  3-6-real-rag-retriever-pgvector-citation-map-sse: done
  # follow-up correct-course 2026-06-18: UX chatbot (markdown render + tái cấu trúc layout). Thứ tự 3-7 → 3-8.
  3-7-render-markdown-cau-tra-loi-chatbot: backlog
  3-8-tai-cau-truc-layout-workspace-o-chat-doc-lap: backlog
  epic-3-retrospective: optional
```

### 4.D — Cập nhật "Khoảng trống đã biết" (`epics.md` cuối file)

```
Thêm mục:
- **UX Chatbot (FR6) — Markdown render + Layout workspace:** ✅ Đã tạo Story 3.7 (render markdown câu
  trả lời, giữ CitationBadge) + 3.8 (tái cấu trúc layout: brand "Trợ lý nghiên cứu" + ô chat độc lập trên
  cùng + cột trò chuyện ở giữa, 3 tab bên phải có › ngăn cách) (correct-course 2026-06-18). Trước đó câu
  trả lời hiện markdown thô khó đọc + ô chat bị chôn trong cột trợ lý (ẩn cột là mất ô chat). Mockup:
  test-data/mockups/layout-chat-top.html. Xem sprint-change-proposal-2026-06-18-chat-markdown-layout.md.
```

---

## Section 5 — Implementation Handoff

- **Phân loại:** **Moderate** — 2 story FE; 3.8 đổi shell layout toàn app (cần regression nhẹ mọi tab + Cytoscape).
- **Người nhận:**
  - **UX Designer (Sally)** (tùy chọn) — đối chiếu mockup `test-data/mockups/layout-chat-top.html`, cập nhật `ux-designs/` nếu cần.
  - **Developer (Amelia)** — chạy `bmad-create-story` theo thứ tự **3.7 → 3.8**.
- **Bước kế tiếp:**
  1. Áp các sửa đổi 4.A–4.D vào `epics.md` + `sprint-status.yaml`.
  2. `bmad-create-story` sinh file story chi tiết tại `implementation-artifacts/3-7-...md`, `3-8-...md`.
  3. `bmad-dev-story` triển khai: 3.7 (markdown, demo nhanh) → 3.8 (layout).
- **Success criteria:**
  - 3.7: câu trả lời chatbot hiển thị markdown đẹp (heading/list/bold/bảng/xuống dòng); thẻ `[N]` vẫn tương tác; không XSS.
  - 3.8: brand "Trợ lý nghiên cứu" + ô chat độc lập trên cùng (½ màn, canh giữa, luôn hiện); cột trò chuyện ở giữa thu hẹp chỉ ẩn messages; 3 tab bên phải có `›`, giãn rộng khi cột trò chuyện thu hẹp; mọi tab + Cytoscape + gap mode chạy đúng.

---

## Phụ lục — Tóm tắt 2 story mới

| Story | Loại | Vai trò | Phụ thuộc | FRs |
|---|---|---|---|---|
| 3.7 | Frontend | Render markdown câu trả lời chatbot (giữ CitationBadge) | 3.5, 3.6 | FR6 |
| 3.8 | Frontend | Tái cấu trúc layout: ô chat độc lập trên cùng + đảo cột (trò chuyện giữa, 3 tab phải) | 3.6 | FR6, FR9 |
