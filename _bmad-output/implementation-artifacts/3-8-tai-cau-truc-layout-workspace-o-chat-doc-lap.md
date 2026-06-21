---
baseline_commit: 8478427
---

# Story 3.8: [Frontend] Tái cấu trúc Layout Workspace — Ô chat độc lập trên cùng + đảo cột

Status: done

## Story

Với vai trò là người dùng (nhà nghiên cứu),
Tôi muốn ô chat "Trợ lý nghiên cứu" luôn hiển thị ở vị trí trung tâm trên cùng (không bị chôn trong một cột có thể bị ẩn), còn cột nội dung trò chuyện nằm ở giữa và cột 3 tab (Thư viện / Bản đồ Tri thức / Hỗ trợ viết) nằm bên phải,
Để tôi luôn truy cập được ô hỏi-đáp bất kể đang thu hẹp/ẩn lịch sử trò chuyện, và có không gian rộng hơn cho nội dung khi không cần xem messages.

> **Phạm vi story này** là **pure frontend** — tái cấu trúc shell layout (`DashboardPage`) và tách `ChatbotPanel` thành 2 phần: (a) **ô chat độc lập** (input + Gửi + suggestion pills) ở trên cùng, dùng chung; (b) **cột nội dung trò chuyện** (messages + resize/collapse) ở giữa. **KHÔNG chạm backend, KHÔNG đổi API, KHÔNG đổi architecture.** Luồng gửi tin / SSE / citation giữ nguyên hợp đồng — chỉ di chuyển vị trí render và nơi sở hữu state.

## Acceptance Criteria

1. **AC#1 — Hàng trên cùng: brand "Trợ lý nghiên cứu" + nút hệ thống thành MỘT dải liền [Manual/Visual]**
   **Given** người dùng đã đăng nhập và mở `/dashboard`.
   **When** trang render.
   **Then** hàng trên cùng hiển thị brand **"🔬 Trợ lý nghiên cứu"** (thay "C2 Research") ở góc trái, kèm **badge tên dự án đang chọn** (ẩn khi chưa chọn dự án).
   **And** các nút hệ thống ở bên phải: Cài đặt Hệ thống (chỉ admin) · API Keys · đổi theme (🌙/☀️) · VI|EN · Đăng xuất.
   **And** hàng trên cùng là **MỘT dải liền KHÔNG có vạch dọc** ngăn brand với nút hệ thống.
   **And** phần dưới được tách bằng **một đường kẻ ngang chạy suốt chiều rộng** (border-bottom của dải trên cùng).

2. **AC#2 — Ô chat độc lập luôn hiển thị, ~50% chiều rộng, canh giữa [Manual/Visual]**
   **Given** đang ở `/dashboard`.
   **When** trang render ở mọi trạng thái cột trò chuyện (mở rộng / thu hẹp / ẩn).
   **Then** ngay dưới hàng trên cùng có **ô chat độc lập** gồm input + nút **Gửi** + (nếu có) **suggestion pills**, **rộng ~50% chiều rộng vùng main** (có min hợp lý ≈ 520px), **canh giữa theo chiều ngang**.
   **And** ô chat **LUÔN hiển thị** bất kể cột nội dung trò chuyện đang mở/thu hẹp/ẩn.

3. **AC#3 — Sidebar dự án bên trái giữ nguyên hành vi [Manual/Visual]**
   **Given** đang ở `/dashboard`.
   **When** trang render.
   **Then** sidebar dự án (nút Tạo dự án + danh sách + collapse/expand + rename/delete như cũ) nằm **ngoài cùng bên trái**.
   **And** viền phải của sidebar **chỉ chạy ở phần dưới hàng trên cùng** (không cắt qua dải brand).

4. **AC#4 — Cột "Nội dung trò chuyện" ở GIỮA: thu hẹp/ẩn chỉ ẩn messages [Manual/Visual]**
   **Given** đang ở `/dashboard`, cột nội dung trò chuyện đang hiển thị.
   **When** người dùng kéo resize handle hoặc bấm nút collapse/ẩn.
   **Then** cột "Nội dung trò chuyện" (ở **giữa**) chứa **chỉ vùng messages** (+ header có tiêu đề "Nội dung trò chuyện", nút lịch sử 🕐, nút tạo chat mới ✏️, nút collapse).
   **And** thu hẹp/ẩn cột này **chỉ ẩn vùng messages**, **KHÔNG ẩn ô chat độc lập** ở AC#2.
   **And** resize/collapse giữ đúng hành vi cũ (min/max width hợp lý, double-click reset, toggle mở lại về width trước đó).

5. **AC#5 — Cột nội dung 3 tab Ở BÊN PHẢI, có dấu `›` ngăn cách, giãn rộng khi cột trò chuyện thu hẹp [Manual/Visual]**
   **Given** đang ở `/dashboard`.
   **When** trang render.
   **Then** cột nội dung 3 tab (Thư viện Tài liệu / Bản đồ Tri thức / Hỗ trợ viết tổng quan) nằm **bên phải**; giữa các tab có **dấu `›` ngăn cách**.
   **And** khi cột "Nội dung trò chuyện" **thu hẹp hoặc ẩn**, cột 3 tab **GIÃN RỘNG** chiếm chỗ trống (flex-grow).
   **And** tab active vẫn highlight đúng và chuyển tab vẫn hoạt động.

6. **AC#6 — Gửi tin từ ô chat độc lập route đúng vào luồng chat hiện có [Manual/Functional]**
   **Given** đã chọn dự án, gõ câu hỏi vào ô chat độc lập.
   **When** bấm Gửi (hoặc Enter).
   **Then** tin được gửi đúng luồng hiện có: tạo thread lười nếu cần (Story 3.1) → POST `sendMessage` → mở `EventSource /api/chat/stream` (Story 3.2/3.6) → stream chunk + `citation_map` + `agent_thinking` + `done`.
   **And** message hiển thị trong cột "Nội dung trò chuyện" (optimistic user bubble + streaming bubble + committed assistant message qua `MessageContent` của Story 3.7).
   **And** state input + suggestions **dùng chung**, **không phụ thuộc** cột trò chuyện đang hiển thị hay bị ẩn (gửi được cả khi cột messages đang ẩn).
   **And** Graph→Chat bridge (`pendingChatInput`) vẫn prefill + focus ô chat độc lập (Story 4.4).

7. **AC#7 — Knowledge Map (Cytoscape) re-fit đúng khi cột nội dung đổi kích thước [Manual/Visual]**
   **Given** tab "Bản đồ Tri thức" đang active và có dữ liệu graph.
   **When** người dùng thu hẹp/ẩn/mở lại cột "Nội dung trò chuyện" làm cột nội dung 3 tab đổi kích thước.
   **Then** canvas Cytoscape **resize + fit lại đúng** (không bị trắng canvas, không lệch khung, không vỡ layout 3 tab).
   **And** Node Detail Card và gap mode (tô viền/pulsing) vẫn hiển thị đúng trong khung mới.

8. **AC#8 — Regression: 3 tab + Node Detail + gap mode + responsive [Test/Manual]**
   **Given** layout mới đã áp dụng.
   **When** thao tác qua cả 3 tab và các tính năng Epic 4 (Story 4.2 Node Detail, 4.4 gap mode, 4.8 legend màu).
   **Then** mọi tab + Node Detail + gap mode + legend chạy đúng như trước; layout không vỡ ở chiều rộng màn hình thông thường.
   **And** `npm run build` (`tsc -b && vite build`) sạch, `npm test` pass (các test bị ảnh hưởng đã cập nhật; pre-existing Cytoscape jsdom failures không tính là regression).

---

## Tasks / Subtasks

### Task 1: Cập nhật hàng trên cùng — brand + badge dự án (AC#1)

- [x] 1.1 Trong `frontend/src/components/Header.tsx`: đổi logo từ `C2 Research` sang **"🔬 Trợ lý nghiên cứu"**.
  - Thêm key i18n mới `header.brand` (vi: `🔬 Trợ lý nghiên cứu`, en: `🔬 Research Assistant`) trong `frontend/src/i18n/translations.ts`, hoặc tái dùng `chat.title` đã có (vi: "Trợ lý nghiên cứu") + emoji. **Khuyến nghị:** thêm `header.brand` riêng để không trộn ngữ nghĩa với tiêu đề cột chat.
- [x] 1.2 Thêm **badge tên dự án** cạnh brand: đọc `useProjectStore` → `activeProjectId` + `projects`, tìm `activeProject?.name`. Render `<span className={styles.badge}>{name}</span>` chỉ khi có `activeProject` (Header hiển thị cả ở trang admin/settings nơi không có active project → badge phải tự ẩn).
- [x] 1.3 CSS `Header.module.css`: thêm `.badge` (nền accent, chữ trắng, bo tròn — tham khảo `.badge` trong mockup). Header **đã là** một dải liền có `border-bottom` (đường kẻ ngang suốt) và **không có vạch dọc** → AC#1 phần "một dải liền / kẻ ngang suốt" đã thỏa; chỉ cần đảm bảo brand + badge ở trái, actions ở phải.
- [x] 1.4 (Quyết định layout — xem Dev Notes §"Hàng trên cùng") Giữ `Header` ở `ProtectedRoute` như hiện tại (Approach A — khuyến nghị). KHÔNG di chuyển Header vào `DashboardPage` để tránh ảnh hưởng các route khác.

### Task 2: Tạo component ô chat độc lập dùng chung `ChatBar` (AC#2, #6)

- [x] 2.1 Tạo `frontend/src/features/workspace/ChatBar.tsx` + `ChatBar.module.css`. Component này **sở hữu**:
  - State input: `inputValue` (local `useState`).
  - State suggestions: `suggestions` + effect fetch `getSuggestions` (di chuyển từ `ChatbotPanel`).
  - Logic gửi tin: `handleSend` + tạo thread lười + `EventSource` SSE + xử lý các event (`done`/`citation_map`/`agent_thinking`/`chunk`) + `closeStream` + cleanup on unmount + reset khi đổi project (di chuyển nguyên xi từ `ChatbotPanel`).
  - `citationMapRef`, `eventSourceRef`, `chatInputRef`.
  - Graph→Chat bridge: effect đọc `pendingChatInput` → prefill `inputValue` + focus (di chuyển từ `ChatbotPanel`).
  - `handleSuggestionClick` (đổi tab/mở upload — di chuyển từ `ChatbotPanel`).
- [x] 2.2 UI `ChatBar`: hàng input (input + nút Gửi) rộng **~50% vùng main, min ≈ 520px, canh giữa**; hàng pills canh giữa bên dưới. Tham khảo `.chatbar`/`.inputrow`/`.pills` trong mockup `test-data/mockups/layout-chat-top.html`. Có `border-bottom` để tách với phần thân bên dưới.
- [x] 2.3 Ghi/đọc state qua `useChatStore` (đọc `isStreaming` để disable input/nút khi đang stream) + `useProjectStore` (`activeProjectId`) + `useWorkspaceStore` (`activeTab`, `documentCount`, `setActiveTab`, `setUploadModalOpen`, `pendingChatInput`, `setPendingChatInput`).
- [x] 2.4 **Lift `thinkingStatus` vào `chatStore`** (xem Task 4) vì `ChatBar` set nó trong SSE còn cột messages (Task 3) đọc nó để hiển thị trạng thái "đang suy nghĩ".

### Task 3: Tách cột "Nội dung trò chuyện" `ConversationColumn` (AC#4, #6)

- [x] 3.1 Tạo `frontend/src/features/workspace/ConversationColumn.tsx` + `ConversationColumn.module.css` (đổi tên/tái cấu trúc từ `ChatbotPanel`). Component này **sở hữu**:
  - State layout: `width`, `collapsed`, `lastWidth` + `handleMouseDown`/`onMouseMove`/`onMouseUp` (resize), `handleDblClick` (reset), `toggleCollapse`.
  - State `showHistory` + `handleNewChat`.
  - Render: header cột ("Nội dung trò chuyện" + 🕐 history + ✏️ new chat + nút collapse), vùng messages (đọc `messages`, `streamingContent`, `isStreaming`, `isLoadingMessages`, `thinkingStatus` từ `chatStore`), `messagesEndRef` auto-scroll, `ChatHistoryPopover`.
  - Render committed assistant qua `<MessageContent>` (giữ nguyên Story 3.7), streaming bubble plain-text + cursor (giữ nguyên Story 3.7 AC#4).
- [x] 3.2 **Sửa hướng resize**: cột nay ở GIỮA (không còn dock phải). Resize handle đặt ở **mép phải** cột; kéo phải → rộng ra. Tính `width` theo khoảng cách từ mép trái vùng body (sau sidebar) tới con trỏ, **không** dùng công thức `(vw - clientX)/vw` của panel dock-phải cũ. Đề xuất: đo bằng `getBoundingClientRect()` của container body hoặc dùng `clientX - bodyRect.left`. Giữ clamp min/max hợp lý (px hoặc %).
- [x] 3.3 **Collapse**: khi `collapsed` → cột width 0 / `display:none` phần messages; cột 3 tab (Task 5) tự giãn rộng nhờ `flex:1`. Nút toggle mở lại đặt ở vị trí hợp lý giữa cột trò chuyện và cột 3 tab (không còn `position:fixed` ở mép phải màn hình như cũ — cân nhắc đặt trong header cột hoặc ở ranh giới 2 cột).
- [x] 3.4 **Bỏ phần input/suggestions** khỏi component này (đã chuyển sang `ChatBar`). Component này KHÔNG còn `inputValue`, `handleSend`, `getSuggestions`, `pendingChatInput`.

### Task 4: Lift `thinkingStatus` vào `chatStore` (AC#6)

- [x] 4.1 Thêm `thinkingStatus: string | null` + `setThinkingStatus` vào `frontend/src/store/chatStore.ts` (thêm vào `INIT` để `reset()` xóa luôn).
- [x] 4.2 `ChatBar` gọi `setThinkingStatus` trong SSE (agent_thinking → set; chunk/done → clear). `ConversationColumn` đọc `thinkingStatus` để render dòng "đang suy nghĩ" (`t('chat.thinking.*')`).
- [x] 4.3 Đảm bảo reset khi đổi project: `ChatBar` gọi `reset()` (đã xóa `thinkingStatus` qua INIT) + `closeStream` + clear `citationMapRef` (giữ logic cũ từ `ChatbotPanel` effect `[activeProjectId]`).

### Task 5: Tái cấu trúc `DashboardPage` + `CenterWorkspace` (AC#2–#5)

- [x] 5.1 Viết lại `frontend/src/features/dashboard/DashboardPage.tsx` theo cấu trúc mới (xem Dev Notes §"Cấu trúc DOM mục tiêu"):
  ```tsx
  <div className={styles.layout}>           {/* flex row, height: calc(100vh - 56px) */}
    <ProjectSidebar />                        {/* trái */}
    <div className={styles.main}>             {/* flex column, flex:1, min-width:0 */}
      <ChatBar />                             {/* trên cùng, border-bottom */}
      <div className={styles.body}>           {/* flex row, flex:1, min-height:0 */}
        <ConversationColumn />                {/* giữa: messages + resize/collapse */}
        <CenterWorkspace />                   {/* phải: 3 tab, flex:1 */}
      </div>
    </div>
  </div>
  ```
- [x] 5.2 Cập nhật `DashboardPage.module.css`: thêm `.main` (flex column, flex:1, min-width:0) và `.body` (flex row, flex:1, min-height:0). Giữ `.layout` height `calc(100vh - 56px)` (Header 56px vẫn ở trên).
- [x] 5.3 `CenterWorkspace.tsx`: thêm **dấu `›` ngăn cách** giữa 3 tab (span `.tabSep` giữa các button tab). Đảm bảo `.workspace` có `flex:1` + `border-left` để giãn rộng khi cột trò chuyện thu hẹp/ẩn. (Hiện đã có `flex:1; min-width:0` — xác nhận giữ.)
- [x] 5.4 Thêm key i18n `chat.conversationTitle` (vi: `Nội dung trò chuyện`, en: `Conversation`) cho header cột trò chuyện. CenterWorkspace `›` là ký tự tĩnh, không cần i18n.

### Task 6: Cytoscape re-fit khi cột nội dung đổi kích thước (AC#7)

- [x] 6.1 Cơ chế hiện tại trong `KnowledgeMapTab.tsx` (effect dòng ~438) chỉ `cy.resize()`+`cy.fit()` khi `activeTab` hoặc `graphNodes` đổi — **KHÔNG** fire khi cột trò chuyện collapse/resize (chỉ đổi width container). Cần thêm trigger.
- [x] 6.2 **Cách khuyến nghị (robust):** gắn `ResizeObserver` lên `containerRef` (canvas wrapper) trong `KnowledgeMapTab`; khi kích thước đổi và `activeTab === 'graph'` → `cy.resize()` + (nếu có elements) `cy.fit(undefined, 30)`. Debounce nhẹ (rAF) để tránh gọi liên tục khi đang kéo resize. Nhớ `disconnect()` khi unmount.
  - *Phương án thay thế (đơn giản hơn, kém mượt):* nâng trạng thái collapse/width cột trò chuyện ra `workspaceStore` và thêm vào deps của effect resize. Loại trừ vì rò state layout ra store toàn cục + không bắt được kéo-mượt. ResizeObserver tự chứa hơn.
- [x] 6.3 Verify: chuyển sang tab Bản đồ → thu hẹp/ẩn/mở lại cột trò chuyện → canvas fit đúng, không trắng.

### Task 7: Cập nhật tests (AC#8)

- [x] 7.1 `ChatbotPanel.test.tsx` hiện test width `25vw`/collapse/title "Trợ lý nghiên cứu"/resize handle trên `<ChatbotPanel>`. Sau refactor `ChatbotPanel` không còn → **tách thành 2 test mới**: `ConversationColumn.test.tsx` (collapse/resize/title "Nội dung trò chuyện", render messages) và `ChatBar.test.tsx` (render input + Gửi + suggestions; gửi gọi đúng API — mock `@/api/chat`). Xóa/thay `ChatbotPanel.test.tsx`.
- [x] 7.2 Cập nhật test mock cho store `chatStore` mới có `thinkingStatus`/`setThinkingStatus` nếu test nào assert.
- [x] 7.3 Cân nhắc thêm 1 test nhỏ cho `CenterWorkspace` xác nhận có dấu `›` (separator) giữa 3 tab — hoặc để manual nếu test Cytoscape jsdom đang flaky (xem Dev Notes). → Để manual (CenterWorkspace.test.tsx flaky vì Cytoscape jsdom).
- [x] 7.4 Chạy `npm test` (pass, trừ pre-existing Cytoscape jsdom failures đã biết) + `npm run build` (`tsc -b && vite build`) sạch.

### Task 8: Kiểm tra thủ công cuối (AC#1–#8)

- [ ] 8.1 Mở `/dashboard`: brand "🔬 Trợ lý nghiên cứu" + badge dự án; nút hệ thống bên phải; kẻ ngang suốt.
- [ ] 8.2 Ô chat độc lập ~50% canh giữa, luôn hiện. Gõ + Gửi → message vào cột giữa, stream chạy, `[N]` badge tương tác (Story 3.5/3.7), markdown đẹp.
- [ ] 8.3 Thu hẹp/ẩn cột trò chuyện → chỉ ẩn messages, ô chat vẫn còn; cột 3 tab giãn rộng. Gửi tin khi cột messages đang ẩn vẫn route đúng.
- [ ] 8.4 Tab Bản đồ Tri thức: thu hẹp/ẩn/mở lại cột trò chuyện → Cytoscape fit đúng; Node Detail + gap mode + legend OK. Dấu `›` giữa tab hiển thị.
- [ ] 8.5 Graph→Chat bridge (gap mode → gửi vào chat) prefill ô chat độc lập + focus.

*(Manual verification by Dat)*

---

## Dev Notes

### Tổng quan thay đổi

Story này là **pure frontend, tái cấu trúc shell layout** — rủi ro trung bình-cao vì chạm khung toàn `/dashboard` và **tách `ChatbotPanel` thành 2 component**. Không chạm backend, không đổi API/architecture. Mấu chốt: state chat **đã được tách qua `chatStore`** (messages/streaming/citation đều trong store) nên `ChatBar` (gửi) và `ConversationColumn` (hiển thị) có thể tách độc lập mà vẫn đồng bộ qua store. Chỉ còn `thinkingStatus` là local → cần lift vào store (Task 4).

| File | Action |
|------|--------|
| `frontend/src/components/Header.tsx` | UPDATE — brand "Trợ lý nghiên cứu" + badge dự án |
| `frontend/src/components/Header.module.css` | UPDATE — `.badge` |
| `frontend/src/features/dashboard/DashboardPage.tsx` | UPDATE — cấu trúc mới (sidebar | main(ChatBar + body(Conversation + CenterWorkspace))) |
| `frontend/src/features/dashboard/DashboardPage.module.css` | UPDATE — `.main`, `.body` |
| `frontend/src/features/workspace/ChatBar.tsx` | **NEW** — ô chat độc lập (input + Gửi + suggestions + send/SSE logic) |
| `frontend/src/features/workspace/ChatBar.module.css` | **NEW** |
| `frontend/src/features/workspace/ConversationColumn.tsx` | **NEW** (refactor từ `ChatbotPanel`) — messages + resize/collapse |
| `frontend/src/features/workspace/ConversationColumn.module.css` | **NEW** (chuyển từ `ChatbotPanel.module.css`) |
| `frontend/src/features/workspace/ChatbotPanel.tsx` + `.module.css` | **DELETE** (sau khi tách) |
| `frontend/src/features/workspace/CenterWorkspace.tsx` | UPDATE — dấu `›` giữa 3 tab |
| `frontend/src/store/chatStore.ts` | UPDATE — thêm `thinkingStatus`/`setThinkingStatus` |
| `frontend/src/features/workspace/KnowledgeMapTab.tsx` | UPDATE — ResizeObserver re-fit (AC#7) |
| `frontend/src/i18n/translations.ts` | UPDATE — `header.brand`, `chat.conversationTitle` |
| `frontend/src/features/workspace/__tests__/ChatbotPanel.test.tsx` | REPLACE → `ConversationColumn.test.tsx` + `ChatBar.test.tsx` |

**Không chạm:** `CitationBadge.tsx`, `MessageContent.tsx` (Story 3.7 giữ nguyên), `ChatHistoryPopover.tsx`, `ProjectSidebar.tsx` (giữ nguyên — chỉ là cột trái), toàn bộ backend, `api/chat.ts`.

### Cấu trúc DOM hiện tại (trước khi sửa)

`DashboardPage` (dòng 25-31) hiện là flex 3 cột phẳng:
```tsx
<div className={styles.layout}>   {/* display:flex; height: calc(100vh - 56px) */}
  <ProjectSidebar />              {/* trái */}
  <CenterWorkspace />            {/* giữa: 3 tab, flex:1 */}
  <ChatbotPanel />              {/* phải: dock phải, header+input+suggestions+messages, collapse/resize theo vw */}
</div>
```
- `Header` (56px) render **bên ngoài** `DashboardPage`, trong `ProtectedRoute` (`src/components/ProtectedRoute.tsx` dòng 31-35: `<><Header />{children}</>`) → áp cho **mọi route protected** (admin/settings/api-keys cũng có Header). Vì vậy `.layout` cao `calc(100vh - 56px)`.
- `ChatbotPanel` dock phải: width tính `((vw - clientX)/vw)*100` (dòng 144), toggle `position:fixed` mép phải (CSS `.toggleBtn`). **Tất cả** (header chat + input + suggestions + messages) nằm trong một panel → ẩn panel là mất ô chat (đúng vấn đề cần sửa).

### Cấu trúc DOM mục tiêu (sau khi sửa)

```tsx
<div className={styles.layout}>             {/* flex row, height: calc(100vh - 56px) */}
  <ProjectSidebar />                          {/* trái — giữ nguyên */}
  <div className={styles.main}>               {/* flex column, flex:1, min-width:0 */}
    <ChatBar />                               {/* trên cùng: input+Gửi+pills, ~50% canh giữa, border-bottom, LUÔN hiện */}
    <div className={styles.body}>             {/* flex row, flex:1, min-height:0 */}
      <ConversationColumn />                  {/* giữa: header cột + messages, resize handle mép phải, collapse → width 0 */}
      <CenterWorkspace />                     {/* phải: 3 tab (có ›), flex:1 → giãn khi cột giữa thu hẹp */}
    </div>
  </div>
</div>
```
Đối chiếu mockup `test-data/mockups/layout-chat-top.html`: `.topbar`(brand+header) → `.below`(`.sidebar` + `.main`(`.chatbar` + `.body`(`.assistant` + `.content`))). Lưu ý mockup gộp brand vào `.topbar` rộng = sidebar; ở app ta giữ `Header` toàn cục (Approach A) nên brand không cần canh đúng 220px — chấp nhận khác biệt cosmetic nhỏ này (xem §Hàng trên cùng).

### Hàng trên cùng — quyết định thiết kế (đã chốt trong story này)

`Header` đang render toàn cục trong `ProtectedRoute` cho mọi route protected. Có 2 hướng:
- **Approach A (KHUYẾN NGHỊ, đã chọn):** Giữ `Header` ở `ProtectedRoute`; chỉ đổi brand + thêm badge dự án. Header **đã là** dải liền có `border-bottom` (kẻ ngang suốt) và không có vạch dọc → thỏa AC#1 về mặt chức năng. **Không** cố canh brand đúng 220px như mockup (cosmetic). Rủi ro thấp, không đụng route khác.
- **Approach B (loại):** Chuyển top-strip vào `DashboardPage` để brand canh đúng width sidebar → phải gỡ `Header` khỏi `ProtectedRoute` cho route dashboard, ảnh hưởng admin/settings, rủi ro cao. Không tương xứng giá trị cosmetic.

> Nếu sau review Dat muốn brand canh chính xác theo cột sidebar (fidelity tuyệt đối với mockup), nâng cấp theo Approach B trong story follow-up — không nằm trong scope 3.8.

### Tách state: ai sở hữu gì

| State | Trước (ChatbotPanel) | Sau |
|---|---|---|
| `inputValue` | local | `ChatBar` local |
| `suggestions` + fetch | local + effect | `ChatBar` |
| `handleSend` + SSE + `eventSourceRef` + `citationMapRef` | local | `ChatBar` |
| `pendingChatInput` prefill/focus | local effect | `ChatBar` |
| `handleSuggestionClick` | local | `ChatBar` |
| `width`/`collapsed`/`lastWidth` + resize/collapse | local | `ConversationColumn` local |
| `showHistory` + `handleNewChat` | local | `ConversationColumn` local |
| `messages`/`streamingContent`/`isStreaming`/`isLoadingMessages` | chatStore (đã) | chatStore — `ConversationColumn` đọc |
| `thinkingStatus` | **local (vấn đề)** | **chatStore** (Task 4): `ChatBar` set, `ConversationColumn` đọc |

**Vì sao tách được sạch:** luồng gửi tin ghi vào `chatStore` (`addOptimisticUserMessage`, `beginStreaming`, `appendChunk`, `commitStreamingMessage`, `setStreaming`); cột messages chỉ đọc store. Hai component không cần truyền props cho nhau — đồng bộ qua store. Chỉ `thinkingStatus` còn local nên phải lift.

### Resize cột giữa — lưu ý công thức

Panel cũ dock phải nên dùng `(vw - clientX)/vw`. Cột mới ở GIỮA (sau sidebar), resize handle ở **mép phải** cột → width tăng khi kéo phải. Dùng `clientX - bodyRect.left` (với `bodyRect` = `getBoundingClientRect()` của `.body`) thay vì công thức vw cũ. Clamp min/max hợp lý. Double-click reset về default. Toggle collapse: lưu `lastWidth`, set width 0; mở lại trả về `lastWidth`. Cột 3 tab `flex:1` tự chiếm chỗ trống khi cột giữa width nhỏ/0 (AC#5).

### Cytoscape re-fit (AC#7) — vì sao cần thêm

`KnowledgeMapTab` init Cytoscape một lần (effect deps `[]`); effect re-fit hiện tại (dòng 438-444) deps `[activeTab, graphNodes]` → chỉ fit khi đổi tab hoặc data đổi. Khi cột trò chuyện collapse/resize, **chỉ width container `.canvas` đổi** → Cytoscape giữ kích thước cũ → canvas có thể trắng/lệch. Thêm `ResizeObserver` trên `containerRef` để gọi `cy.resize()` + `cy.fit()` khi container đổi kích thước (debounce bằng `requestAnimationFrame`), chỉ khi `activeTab==='graph'` và có elements. Nhớ `observer.disconnect()` khi cleanup. Đây là cách tự-chứa, không cần rò state layout ra store toàn cục.

### Streaming + markdown (giữ nguyên Story 3.7)

`ConversationColumn` render messages **y hệt** `ChatbotPanel` cũ: committed assistant → `<MessageContent content={msg.content} citationMap={msg.citationMap} />` (Story 3.7, markdown + CitationBadge); streaming bubble → plain text + cursor `▋` (Story 3.7 AC#4 — KHÔNG đổi); user message → text thuần (KHÔNG qua MessageContent). Không chạm `MessageContent.tsx`/`CitationBadge.tsx`.

### Test note — Cytoscape jsdom pre-existing failures

Story 3.7 ghi nhận: 4 failures trong `CenterWorkspace.test.tsx`/Knowledge Map là **pre-existing** (Cytoscape canvas không chạy trong jsdom), không phải regression. Khi chạy `npm test`, xác nhận failures còn lại đúng là pre-existing (git stash so sánh nếu nghi ngờ), đừng coi là lỗi của story này. Test mới (`ChatBar`, `ConversationColumn`) nên mock `@/api/chat` và các store để tránh phụ thuộc network/Cytoscape.

### Translations cần thêm

- `header.brand`: vi `🔬 Trợ lý nghiên cứu` / en `🔬 Research Assistant`.
- `chat.conversationTitle`: vi `Nội dung trò chuyện` / en `Conversation`.
- Tái dùng: `chat.placeholder`, `chat.sendBtn`, `chat.inputDisabled`, `chat.hide`, `chat.show`, `chat.historyBtn`, `chat.newChatBtn`, `chat.noProject`, `chat.thinking*`, `tab.*`, `header.*` (đã có).

### Thứ tự implement đề xuất

1. `chatStore`: thêm `thinkingStatus` (Task 4) — nền tảng cho tách component.
2. `ChatBar.tsx` (Task 2) — di chuyển input/suggestions/send/SSE.
3. `ConversationColumn.tsx` (Task 3) — di chuyển messages/resize/collapse; sửa công thức resize.
4. `DashboardPage` + CSS + `CenterWorkspace` `›` (Task 5).
5. `Header` brand + badge (Task 1).
6. `KnowledgeMapTab` ResizeObserver (Task 6).
7. Xóa `ChatbotPanel.*`; cập nhật tests (Task 7); build + manual (Task 8).

### References

- [Source: sprint-change-proposal-2026-06-18-chat-markdown-layout.md — Section 2, 3, 4.A] — Quyết định layout đã chốt (brand, ô chat độc lập ½ màn canh giữa, cột trò chuyện giữa, 3 tab phải có `›`, giãn rộng khi thu hẹp), rủi ro (CitationBadge/Cytoscape/responsive), nhướng đã loại.
- [Source: epics.md Story 3.8 (dòng 351-368)] — Story statement, 8 AC nháp, FRs (FR6, FR9), phụ thuộc Story 3.6, nhãn module.
- [Source: test-data/mockups/layout-chat-top.html] — Mockup thiết kế của record: cấu trúc `.topbar`/`.below`/`.main`/`.chatbar`/`.body`/`.assistant`/`.content`, kích thước (chat ~50% min 520px, sidebar 220px), dấu `›` tab-sep, res-handle mép phải cột trợ lý, ghi chú "thu hẹp chỉ ẩn messages".
- [Source: frontend/src/features/dashboard/DashboardPage.tsx + .module.css] — Cấu trúc 3 cột hiện tại cần viết lại; `.layout` height `calc(100vh - 56px)`.
- [Source: frontend/src/features/workspace/ChatbotPanel.tsx] — Nguồn để tách: input (327-351), suggestions (353-366), messages (368-400), send/SSE (193-266), resize/collapse (135-180), pendingChatInput bridge (71-76), reset on project (63-68), thinkingStatus local (23, 252, 255).
- [Source: frontend/src/features/workspace/ChatbotPanel.module.css] — Style nguồn cho `ConversationColumn`/`ChatBar` (resizeHandle, toggleBtn, messages, bubble, input, suggestions...).
- [Source: frontend/src/store/chatStore.ts] — Store đã chứa messages/streaming/citation; cần thêm `thinkingStatus` vào INIT/actions.
- [Source: frontend/src/features/workspace/CenterWorkspace.tsx + .module.css] — 3 tab (library/graph/writing); thêm `›`; `.workspace` flex:1 (giãn khi cột giữa thu hẹp). KnowledgeMapTab nhúng ở tab graph (margin:-24px).
- [Source: frontend/src/features/workspace/KnowledgeMapTab.tsx:438-444] — Effect re-fit hiện tại (deps activeTab/graphNodes); cần thêm ResizeObserver cho AC#7. Init cy effect deps [] (253-291).
- [Source: frontend/src/components/Header.tsx + .module.css + ProtectedRoute.tsx:31-35] — Header toàn cục; đổi brand + badge; quyết định giữ ở ProtectedRoute (Approach A).
- [Source: frontend/src/store/projectStore.ts] — `activeProjectId`, `projects` → badge tên dự án.
- [Source: frontend/src/features/workspace/__tests__/ChatbotPanel.test.tsx] — Test cũ (width 25vw/collapse/title/resize) cần thay bằng test cho 2 component mới.
- [Source: implementation-artifacts/3-7-render-markdown-cau-tra-loi-chatbot.md] — Story trước: MessageContent markdown giữ nguyên; ghi chú pre-existing Cytoscape jsdom test failures.
- [Source: frontend/src/i18n/translations.ts] — Key i18n hiện có (chat.*, tab.*, header.*); thêm `header.brand`, `chat.conversationTitle`.

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- ResizeObserver chưa có trong jsdom → thêm polyfill vào `src/test/setup.ts`.
- ConversationColumn và ChatBar dùng `useChatStore()` không selector → mock trả object trực tiếp, không dùng `selector({...})`.

### Completion Notes List

- Task 4: Thêm `thinkingStatus: string | null` + `setThinkingStatus` vào chatStore INIT và actions — reset() tự xóa.
- Task 2: Tạo `ChatBar.tsx` — sở hữu toàn bộ input/suggestions/send/SSE/pendingChatInput logic. UI: input+Gửi 50% width, min 520px, canh giữa, border-bottom.
- Task 3: Tạo `ConversationColumn.tsx` — sở hữu resize (handle mép phải, công thức `clientX - columnLeft`)/collapse/messages. Nút collapse trong header cột; expand button khi collapsed.
- Task 5: Viết lại `DashboardPage` theo cấu trúc mới (sidebar | main(ChatBar + body(ConversationColumn + CenterWorkspace))). Thêm `.main` + `.body` CSS. Thêm `›` separator + `.tabSep` vào CenterWorkspace.
- Task 1: Header brand → `t('header.brand')` = "🔬 Trợ lý nghiên cứu". Badge dự án tự ẩn khi không có activeProject. Thêm `.brand` + `.badge` CSS.
- Task 6: ResizeObserver trên `containerRef` trong KnowledgeMapTab — debounce rAF, chỉ re-fit khi `activeTab==='graph'`.
- Task 7: Xóa `ChatbotPanel.test.tsx`. Tạo `ConversationColumn.test.tsx` (5 tests) và `ChatBar.test.tsx` (4 tests). Thêm `ResizeObserver` polyfill vào `setup.ts`.
- Build: `tsc -b && vite build` sạch. `npm test`: 120 pass, 4 fail đều là pre-existing Cytoscape jsdom failures (CenterWorkspace.test.tsx).

### File List

- `frontend/src/store/chatStore.ts` — UPDATE: thêm `thinkingStatus`/`setThinkingStatus`
- `frontend/src/i18n/translations.ts` — UPDATE: thêm `header.brand`, `chat.conversationTitle`
- `frontend/src/features/workspace/ChatBar.tsx` — NEW
- `frontend/src/features/workspace/ChatBar.module.css` — NEW
- `frontend/src/features/workspace/ConversationColumn.tsx` — NEW
- `frontend/src/features/workspace/ConversationColumn.module.css` — NEW
- `frontend/src/features/workspace/ChatbotPanel.tsx` — DELETE
- `frontend/src/features/workspace/ChatbotPanel.module.css` — DELETE
- `frontend/src/features/dashboard/DashboardPage.tsx` — UPDATE
- `frontend/src/features/dashboard/DashboardPage.module.css` — UPDATE
- `frontend/src/features/workspace/CenterWorkspace.tsx` — UPDATE: thêm `›` separators
- `frontend/src/features/workspace/CenterWorkspace.module.css` — UPDATE: thêm `.tabSep`
- `frontend/src/components/Header.tsx` — UPDATE: brand + badge
- `frontend/src/components/Header.module.css` — UPDATE: thêm `.brand`, `.badge`
- `frontend/src/features/workspace/KnowledgeMapTab.tsx` — UPDATE: ResizeObserver effect
- `frontend/src/test/setup.ts` — UPDATE: ResizeObserver polyfill
- `frontend/src/features/workspace/__tests__/ChatbotPanel.test.tsx` — DELETE
- `frontend/src/features/workspace/__tests__/ConversationColumn.test.tsx` — NEW
- `frontend/src/features/workspace/__tests__/ChatBar.test.tsx` — NEW

### Change Log

- 2026-06-21: Tạo story 3.8 — Tái cấu trúc Layout Workspace (ô chat độc lập trên cùng + đảo cột: trò chuyện giữa, 3 tab phải). Phân tích đầy đủ sprint-change-proposal-2026-06-18-chat-markdown-layout.md, mockup layout-chat-top.html, code DashboardPage/ChatbotPanel/CenterWorkspace/Header/KnowledgeMapTab/ProtectedRoute, chatStore/workspaceStore/projectStore, story 3.7 learnings. (create-story agent: claude-opus-4-8)
- 2026-06-21: Implement story 3.8 — tách ChatbotPanel thành ChatBar + ConversationColumn, tái cấu trúc DashboardPage, cập nhật Header, ResizeObserver KnowledgeMapTab. Build sạch, 120/124 tests pass (4 pre-existing Cytoscape jsdom failures). (dev agent: claude-sonnet-4-6)

---

## Review Findings

*Code review 2026-06-21 (bmad-code-review, 3 lớp: Blind Hunter / Edge Case Hunter / Acceptance Auditor). Tất cả patch đã được áp dụng & build/test lại sạch.*

### Patches đã sửa

- [x] [Review][Patch] **(Blocker)** Cột trò chuyện khi thu gọn không mở lại được — nút mở (`.expandBtn`, position:absolute) nằm trong cột `width:0` + `overflow:hidden` nên bị cắt mất, collapse thành "một chiều". Fix: `.columnCollapsed { overflow: visible }` [ConversationColumn.module.css:13]
- [x] [Review][Patch] **(High)** Gửi tin khi cột đang thu gọn → không thấy gì (messages + streaming bị ẩn), trông như lỗi. Fix: tự mở lại cột khi `isStreaming` bật [ConversationColumn.tsx]
- [x] [Review][Patch] **(Medium)** `handleNewChat` lúc đang stream gây rò chunk của câu trả lời cũ vào thread mới (EventSource thuộc ChatBar, cột này không đóng được). Fix: guard `isStreaming` + disable nút ✏️ khi stream [ConversationColumn.tsx]
- [x] [Review][Patch] **(Medium)** `thinkingStatus` (đã lift lên store) không được xóa giữa các lần stream / khi stream lỗi → có thể hiện trạng thái cũ. Fix: clear trong `beginStreaming` + trong `es.onerror` [chatStore.ts:63, ChatBar.tsx]
- [x] [Review][Patch] **(Low)** `bodyRef` tạo ra nhưng không bao giờ đọc (comment còn mô tả sai). Fix: xóa [ConversationColumn.tsx]
- [x] [Review][Patch] **(Low)** Clamp resize chỉ theo px tuyệt đối (220–640) → trên màn hẹp có thể bóp nghẹt cột 3 tab. Fix: clamp thêm theo `window.innerWidth`, chừa ≥320px cho CenterWorkspace [ConversationColumn.tsx]
- [x] [Review][Patch] **(Low)** Auto-scroll không re-fire khi mở lại cột. Fix: thêm `collapsed` vào deps [ConversationColumn.tsx]
- [x] [Review][Patch] **(Medium, test gap)** AC#6 (gửi route đúng API) chưa có test thực sự — test cũ chỉ kiểm tra trạng thái disabled. Fix: thêm 2 test cho ChatBar (gửi gọi `sendMessage`; tạo thread lười khi chưa có thread) dùng EventSource giả [ChatBar.test.tsx]

### Deferred

- [x] [Review][Defer] **(Low)** Race "đổi project khi POST sendMessage đang bay" — đã tồn tại nguyên xi trong `ChatbotPanel` cũ, không phải do story 3.8 gây ra. Hoãn xử lý (cần AbortController cho POST) [ChatBar.tsx]

### ⚠️ Lệch phạm vi (cần Dat quyết)

- **`ProjectSidebar.tsx` + `ProjectSidebar.module.css` bị sửa lớn (collapse/expand, avatar, localStorage) và thêm 2 key i18n `sidebar.collapse` / `sidebar.expand`** — story 3.8 ghi rõ "KHÔNG chạm ProjectSidebar (giữ nguyên)" và File List chỉ thêm 2 key `header.brand` + `chat.conversationTitle`. Phần này nằm ngoài phạm vi 3.8, không được review/sửa trong vòng này. Cần xác nhận story nào sở hữu thay đổi này (có vẻ là một feature sidebar-collapse riêng đang lẫn trong working tree cùng story 3.7).

### Đã bỏ qua (noise)

- Nút collapse/expand tái dùng title `chat.hide`/`chat.show` ("Ẩn/Hiện Chat") — a11y label hơi lệch ngữ nghĩa nhưng chấp nhận được, và test đang phụ thuộc vào title này.
- Badge dự án ẩn theo state store thay vì theo route — AC#1 nguyên văn (ẩn khi chưa chọn dự án) vẫn thỏa.

### Kết quả build/test sau khi sửa

- `npm run build` (`tsc -b && vite build`): **sạch**.
- `npm test`: **122 pass / 4 fail** — 4 fail đều là pre-existing Cytoscape jsdom (`CenterWorkspace.test.tsx`), không phải regression.
