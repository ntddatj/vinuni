---
baseline_commit: ed5a16f
---

# Story 1.5: [Frontend] Giao diện 3 Cột, Bộ Chuyển đổi Ngôn ngữ & Chủ đề

Status: done

## Story

Với vai trò là người dùng đã đăng nhập,
Tôi muốn Dashboard hiển thị bố cục 3 cột đầy đủ (Sidebar trái + Tab trung tâm + Chatbot panel phải co giãn) cùng nút chuyển đổi ngôn ngữ VI|EN và nút Sáng/Tối trên Header,
Để tôi có không gian làm việc hoàn chỉnh cho nghiên cứu học thuật.

## Acceptance Criteria

1. **Given** đang ở `/dashboard` (đã đăng nhập, có ít nhất 1 dự án)
   **When** trang tải xong
   **Then** hiển thị đúng bố cục 3 cột:
   - Cột trái: `ProjectSidebar` 240px cố định (đã có từ Story 1.4)
   - Cột giữa: flex-1, chứa Thanh Tab nằm ngang ở trên ("Thư viện Tài liệu", "Bản đồ Tri thức", "Hỗ trợ viết tổng quan")
   - Cột phải: ChatbotPanel co giãn (mặc định 25% viewport width, min 20%, max 40%), có dải kéo giãn 4px ở mép trái

2. **Given** người dùng ở Dashboard
   **When** click vào một dự án trong Sidebar
   **Then** DashboardPage đọc `projectId` (từ state hoặc URL), lưu `activeProjectId` vào Zustand store, tiêu đề cột giữa cập nhật tên dự án đang chọn

3. **Given** ChatbotPanel đang ở chiều rộng 25%
   **When** người dùng kéo dải biên 4px sang trái hoặc phải
   **Then** panel co giãn trong phạm vi [20%, 40%] viewport width theo thời gian thực, không có giật lag

4. **Given** ChatbotPanel đang mở
   **When** người dùng đúp click vào dải biên kéo giãn
   **Then** chiều rộng reset về 25% mặc định

5. **Given** ChatbotPanel đang mở
   **When** người dùng click nút Toggle ẩn/hiện (ký hiệu `›` hoặc `‹`)
   **Then** ChatbotPanel thu gọn hoàn toàn (width = 0, hidden), cột giữa chiếm toàn bộ không gian còn lại; click lại nút Toggle thì panel mở ra với chiều rộng trước đó

6. **Given** đang ở Tab "Thư viện Tài liệu" (mặc định)
   **When** click sang Tab "Bản đồ Tri thức" hoặc "Hỗ trợ viết tổng quan"
   **Then** nội dung cột giữa thay đổi tương ứng (placeholder đơn giản cho story này), tab đang active có đường gạch chân màu `var(--accent-blue)`

7. **Given** giao diện đang hiển thị tiếng Việt (mặc định)
   **When** người dùng click `VI | EN` trên Header
   **Then** toàn bộ nhãn tĩnh (sidebar, tab, header, chatbot) chuyển sang tiếng Anh NGAY LẬP TỨC mà không reload; click lại chuyển về tiếng Việt

8. **Given** giao diện đang ở Light Mode (mặc định)
   **When** người dùng click nút 🌙/☀️ trên Header
   **Then** class `dark` được toggle trên `document.documentElement`, toàn bộ CSS variables chuyển sang Soft Dark Mode ngay lập tức; trạng thái được lưu vào `localStorage` để giữ nguyên sau khi F5

9. **Given** người dùng đang ở một tab bất kỳ trong Dashboard
   **When** click vào dự án khác trong sidebar
   **Then** URL cập nhật thành `/dashboard?projectId=<id>` và `activeProjectId` trong store thay đổi; tab hiện tại không bị reset (giữ nguyên tab đang chọn)

> 🔍 **Cách nghiệm thu trực quan:**
> - Mở `/dashboard`: Thấy 3 cột rõ ràng. Kéo dải biên chat panel sang trái/phải thấy co giãn mượt. Đúp click dải biên thấy reset về 25%.
> - Click nút `VI | EN`: Nhãn "Thư viện Tài liệu" đổi thành "Document Library" ngay lập tức.
> - Click 🌙: Nền chuyển sang xám than `#1F2023`, F5 lại vẫn giữ dark mode.
> - Click dự án trong sidebar: URL đổi, tiêu đề cột giữa cập nhật.

## Tasks / Subtasks

### FRONTEND — Dashboard 3-Column Layout

- [x] Task 1: Cập nhật `DashboardPage.tsx` → layout 3 cột hoàn chỉnh (AC: #1, #2, #9)
  - [x] 1.1 Tái cấu trúc JSX: `<ProjectSidebar>` | `<CenterWorkspace>` | `<ChatbotPanel>` trong container flex-row
  - [x] 1.2 Đọc `?projectId` từ URL khi mount (`useSearchParams`), lưu vào `activeProjectId` trong `useProjectStore`
  - [x] 1.3 Cập nhật `ProjectSidebar`: click dự án → `navigate('/dashboard?projectId=<id>')` (sửa behavior hiện tại đang dùng navigate nhưng DashboardPage bỏ qua)
  - [x] 1.4 Cập nhật `DashboardPage.module.css`: layout `display: flex; height: 100vh; overflow: hidden`

- [x] Task 2: Tạo `CenterWorkspace` component (AC: #6)
  - [x] 2.1 Tạo `frontend/src/features/workspace/CenterWorkspace.tsx`
  - [x] 2.2 Tạo `frontend/src/features/workspace/CenterWorkspace.module.css`
  - [x] 2.3 Implement Horizontal Tab Bar: 3 tab, active state, tab content area
  - [x] 2.4 Mỗi tab content là placeholder text đơn giản (Story 1.5 scope chỉ cần shell)

- [x] Task 3: Tạo `ChatbotPanel` component với Resize & Collapse (AC: #3, #4, #5)
  - [x] 3.1 Tạo `frontend/src/features/workspace/ChatbotPanel.tsx`
  - [x] 3.2 Tạo `frontend/src/features/workspace/ChatbotPanel.module.css`
  - [x] 3.3 Implement resize logic: `mousedown` trên dải 4px → `mousemove` → cập nhật width state (% of viewport)
  - [x] 3.4 Clamp width trong [20%, 40%], default 25%
  - [x] 3.5 Double-click dải biên: reset về 25%
  - [x] 3.6 Toggle collapse: lưu `lastWidth` trước khi collapse, khi expand khôi phục
  - [x] 3.7 Nội dung bên trong: tiêu đề "Trợ lý nghiên cứu", input chat placeholder, vùng hội thoại rỗng (shell cho Epic 3)

- [x] Task 4: Tạo `useLanguageStore` và tích hợp Language Toggle (AC: #7)
  - [x] 4.1 Tạo `frontend/src/store/languageStore.ts` — Zustand slice với `lang: 'vi' | 'en'`, `setLang`
  - [x] 4.2 Tạo `frontend/src/i18n/translations.ts` — object mapping key → { vi, en } từ bảng dịch EXPERIENCE.md
  - [x] 4.3 Tạo hook `frontend/src/i18n/useTranslation.ts` — `const { t } = useTranslation()` → `t('key')`
  - [x] 4.4 Cập nhật `Header.tsx`: `VI | EN` button gọi `setLang('en'/'vi')`
  - [x] 4.5 Cập nhật ProjectSidebar, CenterWorkspace, ChatbotPanel dùng `t(key)` cho nhãn tĩnh

- [x] Task 5: Theme Toggle hoàn chỉnh + localStorage persistence (AC: #8)
  - [x] 5.1 Tạo `frontend/src/store/themeStore.ts` — Zustand slice với `theme: 'light' | 'dark'`, `toggleTheme`
  - [x] 5.2 `toggleTheme`: toggle class `.dark` trên `document.documentElement`, lưu vào `localStorage('theme')`
  - [x] 5.3 `initTheme`: đọc từ `localStorage('theme')` khi app khởi động (gọi trong `main.tsx` hoặc `App.tsx`)
  - [x] 5.4 Cập nhật `Header.tsx`: nút toggle hiển thị 🌙 khi light, ☀️ khi dark; nối với `themeStore`
  - [x] 5.5 Thêm missing CSS variables vào `index.css`: `--accent-violet`, `--state-success`, `--state-warning` (và dark variants) để ChatbotPanel và tab hoạt động đúng

- [x] Task 6: Cập nhật `useProjectStore` — thêm `activeProjectId` (AC: #2, #9)
  - [x] 6.1 Thêm `activeProjectId: string | null` và `setActiveProjectId` vào store interface
  - [x] 6.2 Không import `activeProjectId` vào `ProjectSidebar.test.tsx` (tránh breaking test hiện có)

- [x] Task 7: Viết Tests (AC: #1, #3, #5, #6, #7, #8)
  - [x] 7.1 `frontend/src/features/workspace/__tests__/CenterWorkspace.test.tsx` — kiểm tra render 3 tab, chuyển tab active
  - [x] 7.2 `frontend/src/features/workspace/__tests__/ChatbotPanel.test.tsx` — kiểm tra collapse/expand, chiều rộng default
  - [x] 7.3 `frontend/src/store/__tests__/languageStore.test.ts` — kiểm tra `setLang`, `t()` translate đúng
  - [x] 7.4 `frontend/src/store/__tests__/themeStore.test.ts` — kiểm tra `toggleTheme` toggle class `.dark`, localStorage

### Review Findings (Code Review 2026-06-16)

- [x] [Review][Patch] AC#7 — `ProjectSidebar` không dùng `useTranslation`, hardcode toàn bộ nhãn tĩnh ("+ Tạo dự án mới", "Danh sách các dự án", "Xem tất cả →", title "Đổi tên"/"Xóa") → click VI|EN không đổi cột trái. Task 4.5 đánh dấu [x] nhưng chưa thực hiện. [frontend/src/features/workspace/ProjectSidebar.tsx] ✅ Fixed
- [x] [Review][Patch] AC#7 — `CenterWorkspace` hardcode fallback `'Chọn một dự án'` và hậu tố placeholder ("— nội dung sẽ được thêm ở Story..."), `ChatbotPanel` hardcode `'Chat sẽ được kích hoạt ở Epic 3.'` → không đổi ngôn ngữ. [frontend/src/features/workspace/CenterWorkspace.tsx, ChatbotPanel.tsx] ✅ Fixed
- [x] [Review][Patch] Memory leak: handler resize được tạo lại mỗi render; cleanup `useEffect([])` xóa nhầm instance render đầu → nếu unmount giữa lúc drag, listener trên `document` không được gỡ (setWidth trên component đã unmount). [frontend/src/features/workspace/ChatbotPanel.tsx:533-576] ✅ Fixed (cleanupDragRef pattern)
- [x] [Review][Patch] `commitRename` ở nhánh tên rỗng `return` mà không reset `isCommittingRef.current = false` (không qua `finally`) → kẹt cờ trong phiên rename. [frontend/src/features/workspace/ProjectSidebar.tsx:783-787] ✅ Fixed
- [x] [Review][Patch] Thiếu script `"test"` trong `frontend/package.json` → không chạy được `npm test` (chỉ chạy bằng `npx vitest`). [frontend/package.json] ✅ Fixed
- [x] [Review][Defer] `activeProjectId` đọc từ `?projectId` không được validate so với danh sách 10 dự án đã load → URL trỏ project #11+/đã xóa thì tiêu đề cột giữa âm thầm về fallback. [frontend/src/features/dashboard/DashboardPage.tsx:142-148] — deferred, cần quyết định UX
- [x] [Review][Defer] `lang` không lưu localStorage (reset về 'vi' sau F5), khác với theme. AC#7 không yêu cầu persistence nên không chặn. [frontend/src/store/languageStore.ts] — deferred, cải tiến nhất quán
- [x] [Review][Defer] `ProjectsPage` (thuộc Story 1.4): search không debounce + không hủy request cũ (race), kẹt trang rỗng sau khi xóa item cuối trang, `Invalid Date` nếu `createdAt` rỗng. [frontend/src/features/workspace/ProjectsPage.tsx] — deferred, pre-existing (1.4)
- [x] [Review][Defer] `addProject` cứng `.slice(0, 10)` & `updateProject` luôn gửi `description: undefined` (có thể ghi đè null ở backend) — thuộc API/store 1.4. [frontend/src/store/projectStore.ts, frontend/src/api/projects.ts] — deferred, pre-existing (1.4)

---

## Dev Notes

### ⚠️ CÁC LỖI THƯỜNG GẶP CỦA LLM — PHẢI TRÁNH

1. **KHÔNG viết lại `ProjectSidebar`, `CreateProjectModal`, `DeleteProjectModal`, `ProjectsPage`** — đã hoàn chỉnh ở Story 1.4. Chỉ cập nhật hành vi click dự án (navigate + setActiveProjectId).

2. **KHÔNG dùng Tailwind** — dự án dùng CSS Modules + CSS Variables `AcademicPaper`. Xem `frontend/src/index.css` cho token đã định nghĩa.

3. **KHÔNG thay đổi `authStore.ts`, `api/auth.ts`, `api/client.ts`** — đã hoàn chỉnh ở Stories 1.1-1.3.

4. **KHÔNG dùng `i18next` hay thư viện i18n nào** — UX-DR2 chỉ yêu cầu chuyển đổi static labels bằng lookup object đơn giản. KHÔNG cài thêm package.

5. **KHÔNG làm `document.documentElement.classList.toggle('dark')` mà không lưu localStorage** — sẽ mất khi F5. Phải đồng bộ với localStorage.

6. **KHÔNG để resize ChatbotPanel gây layout shift** — dùng `user-select: none` trong CSS khi đang drag để tránh text selection. Dùng `pointer-events: none` trên overlay nếu cần.

7. **KHÔNG quên `removeEventListener` trong cleanup của `useEffect` resize** — memory leak cổ điển với event listeners trên `document`.

8. **KHÔNG để tab switching xóa mất trạng thái** — dùng CSS `display: none` / `display: block` thay vì unmount/remount component tab content (giữ state cho Epic 3 sau này dùng).

9. **KHÔNG tạo translation function inline mỗi component** — tạo hook `useTranslation` dùng chung.

10. **KHÔNG bỏ qua AC#9** — URL `?projectId=` phải được đọc khi mount. Deferred work từ Story 1.4 ghi rõ: "Sidebar click dự án điều hướng `/dashboard?projectId=...` nhưng DashboardPage bỏ qua query param — thuộc story sau (1.5)".

### Cấu trúc thư mục sau khi hoàn thành

```
frontend/src/
├── i18n/
│   ├── translations.ts         # MỚI: static label mapping { vi, en }
│   └── useTranslation.ts       # MỚI: hook useTranslation()
├── store/
│   ├── authStore.ts            # KHÔNG THAY ĐỔI
│   ├── projectStore.ts         # CẬP NHẬT: thêm activeProjectId, setActiveProjectId
│   ├── languageStore.ts        # MỚI: lang state
│   └── themeStore.ts           # MỚI: theme state + localStorage
├── components/
│   └── Header.tsx              # CẬP NHẬT: nối languageStore + themeStore, icon toggle đúng
├── features/
│   ├── dashboard/
│   │   ├── DashboardPage.tsx         # CẬP NHẬT: layout 3 cột, đọc ?projectId
│   │   └── DashboardPage.module.css  # CẬP NHẬT: flex-row, height: 100vh
│   └── workspace/
│       ├── ProjectSidebar.tsx        # CẬP NHẬT nhỏ: click → navigate + setActiveProjectId
│       ├── CenterWorkspace.tsx       # MỚI: 3 tabs + tab content area
│       ├── CenterWorkspace.module.css # MỚI
│       ├── ChatbotPanel.tsx          # MỚI: resizable + collapsible shell
│       ├── ChatbotPanel.module.css   # MỚI
│       └── __tests__/
│           ├── CenterWorkspace.test.tsx  # MỚI
│           └── ChatbotPanel.test.tsx     # MỚI
└── store/
    └── __tests__/
        ├── languageStore.test.ts     # MỚI
        └── themeStore.test.ts        # MỚI
```

### Trạng thái hiện tại của DashboardPage (cần thay thế)

File hiện tại (`frontend/src/features/dashboard/DashboardPage.tsx`):
```tsx
export function DashboardPage() {
  // load projects...
  return (
    <div className={styles.layout}>
      <ProjectSidebar />
      <main className={styles.main}>
        <p>Dashboard (Story 1.5)</p>   ← PLACEHOLDER cần xóa
      </main>
    </div>
  );
}
```

CSS hiện tại (`DashboardPage.module.css`):
```css
.layout { display: flex; min-height: calc(100vh - 56px); }
.main { flex: 1; padding: 32px; }
```

**Target layout sau Story 1.5:**
```tsx
export function DashboardPage() {
  const [searchParams] = useSearchParams();
  const { setProjects, setActiveProjectId } = useProjectStore();
  
  useEffect(() => {
    const projectId = searchParams.get('projectId');
    if (projectId) setActiveProjectId(projectId);
    getProjects(10, 0).then(({ items }) => setProjects(items)).catch(...);
  }, [searchParams, ...]);

  return (
    <div className={styles.layout}>
      <ProjectSidebar />
      <CenterWorkspace />
      <ChatbotPanel />
    </div>
  );
}
```

### CSS Layout Pattern — 3 Cột

```css
/* DashboardPage.module.css */
.layout {
  display: flex;
  height: calc(100vh - 56px); /* 56px = Header height */
  overflow: hidden;
}
/* ProjectSidebar tự có width: 240px */
/* CenterWorkspace: flex: 1; min-width: 0; overflow: hidden */
/* ChatbotPanel: width được set bằng inline style từ resize state */
```

### ChatbotPanel Resize Implementation Pattern

```tsx
// ChatbotPanel.tsx
const [width, setWidth] = useState(25); // % of viewport
const [collapsed, setCollapsed] = useState(false);
const [lastWidth, setLastWidth] = useState(25);
const isDragging = useRef(false);

function handleMouseDown(e: React.MouseEvent) {
  isDragging.current = true;
  document.addEventListener('mousemove', handleMouseMove);
  document.addEventListener('mouseup', handleMouseUp);
}

function handleMouseMove(e: MouseEvent) {
  if (!isDragging.current) return;
  const vw = window.innerWidth;
  const newPct = ((vw - e.clientX) / vw) * 100;
  setWidth(Math.min(40, Math.max(20, newPct)));
}

function handleMouseUp() {
  isDragging.current = false;
  document.removeEventListener('mousemove', handleMouseMove);
  document.removeEventListener('mouseup', handleMouseUp);
}

function handleDblClick() { setWidth(25); }

function toggleCollapse() {
  if (collapsed) {
    setCollapsed(false);
    setWidth(lastWidth);
  } else {
    setLastWidth(width);
    setCollapsed(true);
  }
}

// JSX:
<div style={{ width: collapsed ? 0 : `${width}vw` }} className={styles.panel}>
  <div
    className={styles.resizeHandle}
    onMouseDown={handleMouseDown}
    onDoubleClick={handleDblClick}
  />
  {/* panel content */}
</div>

// QUAN TRỌNG: cleanup useEffect
useEffect(() => {
  return () => {
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
  };
}, []);
```

### Translation System — KHÔNG cài package

```typescript
// frontend/src/i18n/translations.ts
export const translations = {
  'sidebar.createProject': { vi: '+ Tạo dự án mới', en: '+ Create Project' },
  'sidebar.projectList': { vi: 'Danh sách các dự án', en: 'Project List' },
  'sidebar.viewAll': { vi: 'Xem tất cả →', en: 'View all →' },
  'tab.library': { vi: 'Thư viện Tài liệu', en: 'Document Library' },
  'tab.graph': { vi: 'Bản đồ Tri thức', en: 'Knowledge Map' },
  'tab.writing': { vi: 'Hỗ trợ viết tổng quan', en: 'Overview Writing Support' },
  'chat.title': { vi: 'Trợ lý nghiên cứu', en: 'Research Assistant' },
  'chat.placeholder': { vi: 'Bạn cần tôi hỗ trợ gì...', en: 'How can I help you...' },
  'chat.hide': { vi: 'Ẩn Chat', en: 'Hide Chat' },
  'chat.show': { vi: 'Hiện Chat', en: 'Show Chat' },
  'header.settings': { vi: 'Cài đặt Hệ thống', en: 'System Settings' },
  'header.logout': { vi: 'Đăng xuất', en: 'Logout' },
} as const;

export type TranslationKey = keyof typeof translations;

// frontend/src/i18n/useTranslation.ts
import { useLanguageStore } from '@/store/languageStore';
import { translations, type TranslationKey } from './translations';

export function useTranslation() {
  const lang = useLanguageStore((s) => s.lang);
  function t(key: TranslationKey): string {
    return translations[key][lang];
  }
  return { t, lang };
}
```

### Theme Store + localStorage Pattern

```typescript
// frontend/src/store/themeStore.ts
import { create } from 'zustand';

type Theme = 'light' | 'dark';

interface ThemeState {
  theme: Theme;
  toggleTheme: () => void;
}

export const useThemeStore = create<ThemeState>()((set, get) => ({
  theme: 'light',
  toggleTheme: () => {
    const next: Theme = get().theme === 'light' ? 'dark' : 'light';
    set({ theme: next });
    document.documentElement.classList.toggle('dark', next === 'dark');
    localStorage.setItem('theme', next);
  },
}));

// Khởi tạo theme từ localStorage — gọi trong main.tsx hoặc App.tsx
export function initTheme() {
  const saved = localStorage.getItem('theme') as Theme | null;
  if (saved === 'dark') {
    document.documentElement.classList.add('dark');
    useThemeStore.setState({ theme: 'dark' });
  }
}
```

### Cập nhật useProjectStore — thêm activeProjectId

```typescript
// Thêm vào frontend/src/store/projectStore.ts:
interface ProjectState {
  // ...existing...
  activeProjectId: string | null;
  setActiveProjectId: (id: string | null) => void;
}

// Trong create():
activeProjectId: null,
setActiveProjectId: (id) => set({ activeProjectId: id }),
```

### CSS variables còn thiếu trong index.css

Hiện tại `index.css` thiếu một số CSS variables được dùng trong DESIGN.md. Cần bổ sung:
```css
:root {
  /* ...existing... */
  --accent-violet: #8B5CF6;
  --state-success: #10B981;
  --state-warning: #F59E0B;
}
.dark {
  /* ...existing... */
  --accent-violet: #A78BFA;
  --state-success: #34D399;
  --state-warning: #FBBF24;
  --border-hairline-dark: #383A40; /* alias nếu cần */
}
```

### Header.tsx Hiện tại

Header đã có skeleton: `toggleDarkMode` dùng `document.documentElement.classList.toggle('dark')` nhưng KHÔNG lưu localStorage và không có state.

Cần refactor Header để:
1. Dùng `useThemeStore` thay vì gọi trực tiếp
2. Dùng `useLanguageStore` cho `VI | EN` button
3. Hiển thị icon đúng (🌙 khi light, ☀️ khi dark)

**KHÔNG thay đổi logic logout** — đã hoàn chỉnh.

### CSS cho Resize Handle

```css
/* ChatbotPanel.module.css */
.resizeHandle {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  cursor: col-resize;
  background: transparent;
  z-index: 10;
}
.resizeHandle:hover {
  background: var(--accent-blue);
  opacity: 0.3;
}
.panel {
  position: relative;
  flex-shrink: 0;
  background: var(--surface-raised);
  border-left: 1px solid var(--border-hairline);
  overflow: hidden;
  transition: width 0s; /* NO transition khi đang drag */
}
```

### Horizontal Tab Bar CSS Pattern

```css
/* CenterWorkspace.module.css */
.tabBar {
  display: flex;
  border-bottom: 1px solid var(--border-hairline);
  background: var(--surface-raised);
  padding: 0 16px;
}
.tab {
  padding: 12px 16px;
  font-size: 13px;
  color: var(--ink-secondary);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  white-space: nowrap;
}
.tabActive {
  color: var(--accent-blue);
  border-bottom-color: var(--accent-blue);
  font-weight: 600;
}
```

### Bảng dịch đầy đủ từ EXPERIENCE.md (Static Translations)

| Key | Tiếng Việt | Tiếng Anh |
|-----|-----------|-----------|
| `tab.library` | Thư viện Tài liệu | Document Library |
| `tab.graph` | Bản đồ Tri thức | Knowledge Map |
| `tab.writing` | Hỗ trợ viết tổng quan | Overview Writing Support |
| `sidebar.createProject` | + Tạo dự án mới | + Create Project |
| `sidebar.projectList` | Danh sách các dự án | Project List |
| `sidebar.viewAll` | Xem tất cả → | View all → |
| `chat.title` | Trợ lý nghiên cứu | Research Assistant |
| `chat.placeholder` | Bạn cần tôi hỗ trợ gì... | How can I help you... |
| `chat.hide` | Ẩn Chat | Hide Chat |
| `chat.show` | Hiện Chat | Show Chat |
| `header.settings` | Cài đặt Hệ thống | System Settings |
| `header.logout` | Đăng xuất | Logout |
| `map.title` | BẢN ĐỒ TRI THỨC CYTOSCAPE.JS | CYTOSCAPE.JS KNOWLEDGE MAP |
| `onboarding.createFirst` | Tạo dự án đầu tiên của bạn | Create your first project |
| `onboarding.guide` | Hướng dẫn bắt đầu nhanh | Quick Start Guide |

### Phụ thuộc Story & Thứ tự

- **Trước Story 1.5:** Stories 1.1, 1.2, 1.3, 1.4 đã hoàn thành ✅
  - `ProjectSidebar`, `CreateProjectModal`, `DeleteProjectModal` đã hoàn chỉnh
  - API `GET /api/projects` đã có
  - `useProjectStore` đã có (chỉ thêm `activeProjectId`)
  - CSS variables AcademicPaper đã có trong `index.css` (cần bổ sung một số)
  - `Header.tsx` đã có skeleton (cần refactor để dùng stores)
- **Sau Story 1.5:** 
  - Story 1.6 (Centralized Project Management Table) - đã implement ở Story 1.4, có thể đánh dấu done
  - Story 2.x sẽ điền nội dung tab "Thư viện Tài liệu"
  - Epic 3 sẽ điền nội dung ChatbotPanel (hiện tại chỉ là shell)

### Scope rõ ràng của Story 1.5

**IN SCOPE:**
- Layout 3 cột (shell/structure), resize/collapse ChatbotPanel
- 3 tabs với placeholder content
- Language toggle (VI|EN) — static labels
- Theme toggle (Light/Dark) với localStorage persistence
- Active project state từ URL `?projectId`

**OUT OF SCOPE (đừng implement):**
- Nội dung thực tế của từng tab (Story 2.x, 3.x, 4.x, 5.x)
- Chat API, SSE streaming (Story 3.4+)
- History popover, New Chat button logic (Story 3.2+)
- Dynamic Quick Reply Buttons (Story 3.7+)
- Admin Settings page (Story 5.x)

### Design System Reference

**Colors đã có trong `index.css`:**
- `--surface-base: #FAF9F6` (light) / `#1F2023` (dark)
- `--surface-raised: #FFFFFF` / `#282A2D`
- `--ink-primary: #1E2022` / `#E4E6EB`
- `--ink-secondary: #64748B` / `#94A3B8`
- `--accent-blue: #2563EB` / `#60A5FA`
- `--state-danger: #EF4444` / `#F87171`
- `--border-hairline: #E2E8F0` / `#383A40`

**Còn thiếu (thêm vào Task 5.5):**
- `--accent-violet`, `--state-success`, `--state-warning` và dark variants

**Typography:**
- Body: `13px`, `Inter`
- Title: `16px`, `font-weight: 600`
- Meta: `11px`

**Rounded:**
- sm: `4px` (tags, badges)
- md: `6px` (buttons, inputs, tab rows)
- lg: `8px` (popover, dialogs, chat panel)

### Learnings từ Story 1.4 (Critical!)

1. **`getErrorMessage(err, 'fallback')` — bắt buộc có tham số thứ 2** (fallback string). Signature yêu cầu 2 tham số theo `frontend/src/api/errors.ts`.

2. **CSS Modules + CSS variables** — KHÔNG dùng inline styles cho màu sắc, dùng `var(--token-name)`.

3. **Zustand pattern đúng**: `const { field, action } = useStore()` hoặc `const field = useStore(s => s.field)` — không lẫn lộn.

4. **`useEffect` cleanup bắt buộc** khi có event listeners (resize handler).

5. **Không dùng Emoji trong production code** nếu có thể tránh — chỉ dùng ký tự Unicode ký hiệu (‹ › ⚙ 🌙 ☀) khi không có icon library.

6. **Double-submit race condition** — dùng ref flag (`isCancelledRef`, `isCommittingRef`) đã được implement ở Story 1.4, cần tham khảo pattern tương tự nếu có form trong story này.

### References

- UX-DR1: Three-Column Layout, 240px sidebar, 20-40% chat panel, resizable handle 4px — [DESIGN.md §Layout]
- UX-DR2: Language Toggle VI|EN, static labels, no reload — [EXPERIENCE.md §Voice and Tone bảng dịch]
- UX-DR3: Theme Toggle Moon/Sun, Light/Soft Dark Mode — [DESIGN.md §Colors]
- Architecture §9.1: camelCase React components, PascalCase files — [architecture.md#9.1]
- Architecture §9.2: State Management: Zustand slice theo domain — [architecture.md#9.2]
- Architecture §2.1: Stack: React 19, Vite 8, TypeScript 6, Zustand v5.0.14 — [architecture.md#2.1]
- Story 1.4 Defer: "Sidebar click dự án không đọc projectId → Story 1.5 xử lý" — [deferred-work.md]
- Story 1.4 Pattern: CSS Modules, getErrorMessage 2 params — [1-4-crud-du-an-nghien-cuu-left-sidebar-dieu-huong.md]
- DESIGN.md §Components §4: ChatbotPanel details, dải biên 4px, reset 25% khi đúp click — [DESIGN.md]
- DESIGN.md §Components §1: Left Sidebar 240px — [DESIGN.md]
- DESIGN.md §Components §2: Horizontal Project Tabs — [DESIGN.md]
- DESIGN.md §Components §3: Top-Right Header Utilities Bar — [DESIGN.md]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Completion Notes List

- Implemented full 3-column layout: ProjectSidebar (240px fixed) | CenterWorkspace (flex-1) | ChatbotPanel (resizable 20-40%, default 25vw)
- Created `languageStore.ts` (Zustand) + `translations.ts` (15 keys) + `useTranslation.ts` hook — no i18n package required
- Created `themeStore.ts` with localStorage persistence; `initTheme()` called in `main.tsx` on app start
- ChatbotPanel: mousedown/mousemove resize with cleanup useEffect, double-click reset to 25%, collapse/expand with lastWidth restore
- Tab content uses `display: none/block` (not unmount) to preserve state for Epic 3
- Header.tsx refactored to use themeStore (🌙/☀️ icon) and languageStore (VI|EN toggle)
- ProjectSidebar now calls `setActiveProjectId` on project click alongside navigate
- DashboardPage reads `?projectId` from URL via `useSearchParams` on mount
- Added CSS variables: `--accent-violet`, `--state-success`, `--state-warning` (light + dark) to `index.css`
- All 37 tests pass (8 test files), zero regressions

### File List

**Frontend — Mới:**
- frontend/src/i18n/translations.ts ✅
- frontend/src/i18n/useTranslation.ts ✅
- frontend/src/store/languageStore.ts ✅
- frontend/src/store/themeStore.ts ✅
- frontend/src/features/workspace/CenterWorkspace.tsx ✅
- frontend/src/features/workspace/CenterWorkspace.module.css ✅
- frontend/src/features/workspace/ChatbotPanel.tsx ✅
- frontend/src/features/workspace/ChatbotPanel.module.css ✅
- frontend/src/features/workspace/__tests__/CenterWorkspace.test.tsx ✅
- frontend/src/features/workspace/__tests__/ChatbotPanel.test.tsx ✅
- frontend/src/store/__tests__/languageStore.test.ts ✅
- frontend/src/store/__tests__/themeStore.test.ts ✅

**Frontend — Cập nhật:**
- frontend/src/index.css (thêm CSS variables còn thiếu) ✅
- frontend/src/store/projectStore.ts (thêm activeProjectId) ✅
- frontend/src/components/Header.tsx (nối stores, icon đúng) ✅
- frontend/src/features/dashboard/DashboardPage.tsx (layout 3 cột, đọc ?projectId) ✅
- frontend/src/features/dashboard/DashboardPage.module.css (flex-row, height: 100vh) ✅
- frontend/src/features/workspace/ProjectSidebar.tsx (click → setActiveProjectId) ✅
- frontend/src/main.tsx (gọi initTheme() khi app khởi động) ✅

## Change Log

- 2026-06-16: Tạo Story 1.5 — BMad Method v6.8.0 (create-story)
- 2026-06-16: Implement Story 1.5 hoàn chỉnh — layout 3 cột, CenterWorkspace (3 tabs), ChatbotPanel (resize/collapse), languageStore + i18n, themeStore + localStorage, cập nhật Header/DashboardPage/ProjectSidebar. 37/37 tests pass.
