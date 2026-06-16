---
baseline_commit: 1ed7aea
---

# Story 1.6: [Frontend] Trang Quản lý Toàn bộ Dự án Dạng Bảng

Status: done

## Story

Với vai trò là người dùng đã đăng nhập,
Tôi muốn trang quản lý toàn bộ dự án dạng bảng (tại `/projects`),
Để tôi có thể tìm kiếm, phân trang và xóa dự án khi số lượng dự án lớn.

## Acceptance Criteria

1. **Given** đang ở Dashboard
   **When** click "Xem tất cả →" trong Sidebar trái
   **Then** điều hướng đến `/projects` — trang có Header (logo, VI|EN, theme toggle, settings nếu admin, logout)

2. **Given** đang ở `/projects`
   **When** trang tải xong
   **Then** hiển thị bảng danh sách TẤT CẢ dự án (server-side), phân trang 10 dự án/trang

3. **Given** đang ở `/projects`
   **When** gõ vào ô tìm kiếm
   **Then** sau 300ms debounce, bảng cập nhật đúng kết quả tìm kiếm theo tên; về trang 1

4. **Given** đang ở `/projects` trang > 1, dự án cuối cùng trên trang đó bị xóa
   **When** xác nhận xóa
   **Then** tự động lùi về trang trước (không để lại trang rỗng)

5. **Given** ô "Ngày tạo" có thể nhận giá trị null/rỗng từ backend
   **When** render bảng
   **Then** ngày hợp lệ hiển thị `toLocaleDateString` theo ngôn ngữ hiện tại; giá trị invalid/null hiển thị "—"

6. **Given** đang ở `/projects`
   **When** click VI|EN trên Header
   **Then** tất cả nhãn tĩnh trong bảng (tiêu đề cột, nút, placeholder) đổi ngôn ngữ ngay lập tức

7. **Given** đang ở `/projects`
   **When** click icon 🗑 trên dòng dự án muốn xóa
   **Then** hiện popup `DeleteProjectModal` "Bạn có chắc chắn muốn xóa...?"; bấm OK → dòng biến mất; bấm Hủy → không xóa

> 🔍 **Cách nghiệm thu trực quan:**
> Web UI. Vào `/projects`. Thấy bảng dự án. Gõ từ khóa tìm kiếm — bảng cập nhật. Bấm icon 🗑, hiện popup "Bạn có chắc chắn?". Bấm OK, dòng đó biến mất. Chuyển sang tiếng Anh qua VI|EN, thấy cột đổi sang "Project Name", "Date Created".

## Tasks / Subtasks

### FRONTEND — Sửa lỗi deferred + i18n + tests

- [x] Task 1: Thêm translation keys cho `ProjectsPage` vào `translations.ts` (AC: #6)
  - [x] 1.1 Thêm 11 keys mới vào `frontend/src/i18n/translations.ts` (xem Dev Notes § Translation Keys)
  - [x] 1.2 `TranslationKey` type tự cập nhật do `as const` — không cần sửa thêm

- [x] Task 2: Refactor `ProjectsPage.tsx` — i18n + debounce + bugfixes (AC: #2–#7)
  - [x] 2.1 Import `useTranslation` hook, dùng `t()` cho tất cả nhãn tĩnh (tên cột, nút, placeholder, empty states)
  - [x] 2.2 Thêm `debouncedSearch` state: `useEffect` với `setTimeout(300ms)` + cleanup `clearTimeout` — KHÔNG dùng thư viện ngoài
  - [x] 2.3 Tách `loadProjects` effect: trigger bởi `[page, debouncedSearch]` thay vì `[page, searchQuery]`
  - [x] 2.4 Thêm `handleDeleteSuccess`: nếu `projects.length - 1 === 0 && page > 0` → `setPage(p => p - 1)`, ngược lại `loadProjects(page, debouncedSearch)` — truyền làm `onSuccess` cho `DeleteProjectModal`
  - [x] 2.5 Thêm `formatDate()` helper (xem Dev Notes § formatDate) — guard `null/undefined/NaN`
  - [x] 2.6 Đổi nút text "Xóa" → icon 🗑 (Unicode U+1F5D1, không cần icon library)
  - [x] 2.7 Format ngày dùng `lang` từ `useTranslation`: `lang === 'vi' ? 'vi-VN' : 'en-US'`

- [x] Task 3: Viết tests `ProjectsPage.test.tsx` (AC: #2, #3, #4, #7)
  - [x] 3.1 Tạo `frontend/src/features/workspace/__tests__/ProjectsPage.test.tsx`
  - [x] 3.2 Test: render bảng với danh sách mock projects (kiểm tra tên cột, dữ liệu hàng)
  - [x] 3.3 Test: ô tìm kiếm gõ text → loading state → refetch (dùng fake timers vi.useFakeTimers để test debounce)
  - [x] 3.4 Test: click 🗑 → `DeleteProjectModal` xuất hiện với đúng tên dự án
  - [x] 3.5 Test: `Invalid Date` guard — truyền `createdAt: ''` → hiển thị "—"
  - [x] 3.6 Test: pagination render đúng khi `total > PAGE_SIZE`

---

## Dev Notes

### ⚠️ LỖI THƯỜNG GẶP CỦA LLM — PHẢI TRÁNH

1. **KHÔNG viết lại `DeleteProjectModal`, `CreateProjectModal`, `ProjectSidebar`** — đã hoàn chỉnh, chỉ sửa `ProjectsPage.tsx`.

2. **KHÔNG dùng Tailwind** — dự án dùng CSS Modules + CSS Variables `AcademicPaper`. Không thêm class Tailwind.

3. **KHÔNG cài thêm debounce library (lodash.debounce, use-debounce, v.v.)** — implement bằng `useEffect` + `setTimeout` thuần. Pattern đã được dùng ở nhiều story trước.

4. **KHÔNG dùng `i18next` hay thư viện i18n nào** — dùng hook `useTranslation()` từ `frontend/src/i18n/useTranslation.ts` đã có sẵn.

5. **KHÔNG import emoji từ thư viện** — dùng Unicode trực tiếp trong JSX: `🗑` hoặc `{'\u{1F5D1}'}`.

6. **KHÔNG thay đổi `getProjects` API shape** — API đã trả về `{items: ProjectResponse[], total: number}` từ Story 1.4. Xem `frontend/src/api/projects.ts`.

7. **KHÔNG quên `getErrorMessage(err, 'fallback string')`** — hàm này yêu cầu BẮT BUỘC tham số thứ 2. Thiếu sẽ lỗi TypeScript TS2554. Xem pattern ở code hiện tại.

8. **KHÔNG dùng emoji trong tên biến/hàm** — chỉ dùng trong JSX content.

9. **KHÔNG đặt debounce effect vào cùng `useEffect` với `loadProjects`** — phải tách ra 2 effect riêng biệt.

10. **KHÔNG gọi `loadProjects` trực tiếp trong `handleDeleteSuccess`** — phải `setPage(p => p - 1)` khi trang rỗng (sẽ trigger effect `[page, debouncedSearch]` tự động reload).

### Translation Keys Cần Thêm vào `translations.ts`

Thêm 11 keys sau vào object `translations` trong `frontend/src/i18n/translations.ts`:

```typescript
'projects.title': { vi: 'Quản lý Dự án', en: 'Project Management' },
'projects.createButton': { vi: '+ Tạo dự án mới', en: '+ New Project' },
'projects.searchPlaceholder': { vi: 'Tìm kiếm theo tên dự án...', en: 'Search by project name...' },
'projects.colName': { vi: 'Tên dự án', en: 'Project Name' },
'projects.colDesc': { vi: 'Mô tả', en: 'Description' },
'projects.colDate': { vi: 'Ngày tạo', en: 'Date Created' },
'projects.colAction': { vi: 'Hành động', en: 'Action' },
'projects.empty': { vi: 'Chưa có dự án nào. Hãy tạo dự án đầu tiên!', en: 'No projects yet. Create your first one!' },
'projects.noResults': { vi: 'Không tìm thấy dự án nào.', en: 'No projects found.' },
'projects.loading': { vi: 'Đang tải...', en: 'Loading...' },
'projects.pagePrev': { vi: '← Trước', en: '← Prev' },
'projects.pageNext': { vi: 'Tiếp →', en: 'Next →' },
```

### Debounce Pattern — Không cài thư viện

```tsx
// ProjectsPage.tsx — thay thế searchQuery effect hiện tại
const [searchQuery, setSearchQuery] = useState('');
const [debouncedSearch, setDebouncedSearch] = useState('');

// Effect 1: debounce
useEffect(() => {
  const timer = setTimeout(() => setDebouncedSearch(searchQuery), 300);
  return () => clearTimeout(timer);
}, [searchQuery]);

// Effect 2: load data — trigger bởi page VÀ debouncedSearch
useEffect(() => {
  loadProjects(page, debouncedSearch);
}, [page, debouncedSearch, loadProjects]);

function handleSearch(e: React.ChangeEvent<HTMLInputElement>) {
  setSearchQuery(e.target.value);
  setPage(0); // reset về trang 1 ngay lập tức (không cần đợi debounce)
}
```

### formatDate Helper — Guard Invalid Date

```tsx
// Thêm bên trong component hoặc bên ngoài file
function formatDate(dateStr: string | null | undefined, locale: string): string {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return '—';
  return d.toLocaleDateString(locale);
}

// Dùng trong JSX:
<td>{formatDate(project.createdAt, lang === 'vi' ? 'vi-VN' : 'en-US')}</td>
```

### handleDeleteSuccess — Tránh Trang Rỗng

```tsx
const handleDeleteSuccess = useCallback(() => {
  // Nếu xóa item cuối cùng trên trang > 0 → lùi trang
  if (projects.length === 1 && page > 0) {
    setPage((p) => p - 1); // effect [page, debouncedSearch] sẽ tự reload
  } else {
    loadProjects(page, debouncedSearch);
  }
}, [projects.length, page, debouncedSearch, loadProjects]);
```

### Toàn bộ ProjectsPage.tsx sau khi refactor

```tsx
import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { getProjects } from '@/api/projects';
import { getErrorMessage } from '@/api/errors';
import { useTranslation } from '@/i18n/useTranslation';
import type { ProjectResponse } from '@/types/project';
import { CreateProjectModal } from './CreateProjectModal';
import { DeleteProjectModal } from './DeleteProjectModal';
import styles from './ProjectsPage.module.css';

const PAGE_SIZE = 10;

function formatDate(dateStr: string | null | undefined, locale: string): string {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return '—';
  return d.toLocaleDateString(locale);
}

export function ProjectsPage() {
  const { t, lang } = useTranslation();
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [page, setPage] = useState(0);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);

  const loadProjects = useCallback(async (currentPage: number, search: string) => {
    setIsLoading(true);
    try {
      const { items, total: t } = await getProjects(PAGE_SIZE, currentPage * PAGE_SIZE, search || undefined);
      setProjects(items);
      setTotal(t);
    } catch (err) {
      toast.error(getErrorMessage(err, 'Không thể tải danh sách dự án'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Debounce: delay search 300ms
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Load khi page hoặc debouncedSearch thay đổi
  useEffect(() => {
    loadProjects(page, debouncedSearch);
  }, [page, debouncedSearch, loadProjects]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  function handleSearch(e: React.ChangeEvent<HTMLInputElement>) {
    setSearchQuery(e.target.value);
    setPage(0);
  }

  const handleDeleteSuccess = useCallback(() => {
    if (projects.length === 1 && page > 0) {
      setPage((p) => p - 1);
    } else {
      loadProjects(page, debouncedSearch);
    }
  }, [projects.length, page, debouncedSearch, loadProjects]);

  const locale = lang === 'vi' ? 'vi-VN' : 'en-US';

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>{t('projects.title')}</h1>
        <button className={styles.createButton} onClick={() => setShowCreateModal(true)}>
          {t('projects.createButton')}
        </button>
      </div>

      <input
        className={styles.searchInput}
        type="search"
        placeholder={t('projects.searchPlaceholder')}
        value={searchQuery}
        onChange={handleSearch}
      />

      {isLoading ? (
        <div className={styles.empty}>{t('projects.loading')}</div>
      ) : projects.length === 0 ? (
        <div className={styles.empty}>
          {searchQuery ? t('projects.noResults') : t('projects.empty')}
        </div>
      ) : (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>{t('projects.colName')}</th>
              <th>{t('projects.colDesc')}</th>
              <th>{t('projects.colDate')}</th>
              <th>{t('projects.colAction')}</th>
            </tr>
          </thead>
          <tbody>
            {projects.map((project) => (
              <tr key={project.id}>
                <td>{project.name}</td>
                <td>{project.description ?? '—'}</td>
                <td>{formatDate(project.createdAt, locale)}</td>
                <td>
                  <button
                    className={styles.deleteBtn}
                    onClick={() => setDeleteTarget({ id: project.id, name: project.name })}
                    title={t('sidebar.delete')}
                  >
                    🗑
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {totalPages > 1 && (
        <div className={styles.pagination}>
          <button
            className={styles.pageBtn}
            disabled={page === 0}
            onClick={() => setPage((p) => p - 1)}
          >
            {t('projects.pagePrev')}
          </button>
          <span className={styles.pageInfo}>
            {page + 1} / {totalPages}
          </span>
          <button
            className={styles.pageBtn}
            disabled={page >= totalPages - 1}
            onClick={() => setPage((p) => p + 1)}
          >
            {t('projects.pageNext')}
          </button>
        </div>
      )}

      {showCreateModal && (
        <CreateProjectModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => loadProjects(page, debouncedSearch)}
        />
      )}
      {deleteTarget && (
        <DeleteProjectModal
          projectId={deleteTarget.id}
          projectName={deleteTarget.name}
          onClose={() => setDeleteTarget(null)}
          onSuccess={handleDeleteSuccess}
        />
      )}
    </div>
  );
}
```

### CSS Hiện Có — Không Cần Sửa

`ProjectsPage.module.css` đã có đủ styles. Nút `deleteBtn` sẽ hiển thị icon 🗑 tốt với style hiện tại. Không cần thêm class mới.

Trường hợp muốn icon to hơn, có thể thêm `font-size: 1rem` vào `.deleteBtn` — nhưng không bắt buộc.

### Cấu Trúc File

```
frontend/src/
├── i18n/
│   ├── translations.ts         # CẬP NHẬT: thêm 12 keys 'projects.*'
│   └── useTranslation.ts       # KHÔNG THAY ĐỔI
├── features/
│   └── workspace/
│       ├── ProjectsPage.tsx    # CẬP NHẬT: i18n + debounce + bugfixes
│       ├── ProjectsPage.module.css  # KHÔNG THAY ĐỔI (hoặc minor)
│       └── __tests__/
│           └── ProjectsPage.test.tsx  # MỚI
```

**Files KHÔNG được chỉnh sửa:**
- `App.tsx` — route `/projects` đã đúng
- `ProtectedRoute.tsx` — đã render `<Header />` tự động
- `DeleteProjectModal.tsx`, `CreateProjectModal.tsx`
- `frontend/src/api/projects.ts`
- `frontend/src/store/projectStore.ts`

### Pattern Test File — Tham khảo Story 1.4

```tsx
// frontend/src/features/workspace/__tests__/ProjectsPage.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { ProjectsPage } from '../ProjectsPage';
import * as projectsApi from '@/api/projects';

vi.mock('@/api/projects');

const mockProjects = [
  { id: '1', name: 'Dự án Alpha', description: 'Mô tả A', createdAt: '2026-01-15T00:00:00Z' },
  { id: '2', name: 'Dự án Beta', description: null, createdAt: '' },
];

function renderPage() {
  return render(
    <MemoryRouter>
      <ProjectsPage />
    </MemoryRouter>
  );
}

describe('ProjectsPage', () => {
  beforeEach(() => {
    vi.mocked(projectsApi.getProjects).mockResolvedValue({ items: mockProjects, total: 2 });
  });

  it('hiển thị bảng với dữ liệu', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('Dự án Alpha')).toBeInTheDocument());
    expect(screen.getByText('Dự án Beta')).toBeInTheDocument();
  });

  it('createdAt rỗng hiển thị —', async () => {
    renderPage();
    await waitFor(() => screen.getByText('Dự án Beta'));
    const cells = screen.getAllByText('—');
    expect(cells.length).toBeGreaterThan(0); // description null + createdAt rỗng
  });

  it('click icon xóa mở DeleteProjectModal', async () => {
    renderPage();
    await waitFor(() => screen.getByText('Dự án Alpha'));
    const trashBtns = screen.getAllByTitle('Xóa');
    fireEvent.click(trashBtns[0]);
    expect(screen.getByText(/Dự án Alpha/)).toBeInTheDocument(); // trong modal
  });

  it('debounce: search gọi API sau 300ms', async () => {
    vi.useFakeTimers();
    renderPage();
    await waitFor(() => screen.getByText('Dự án Alpha'));
    const input = screen.getByRole('searchbox');
    fireEvent.change(input, { target: { value: 'Alpha' } });
    // chưa gọi lại ngay
    expect(vi.mocked(projectsApi.getProjects)).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(300);
    await waitFor(() =>
      expect(vi.mocked(projectsApi.getProjects)).toHaveBeenCalledWith(10, 0, 'Alpha')
    );
    vi.useRealTimers();
  });
});
```

**Lưu ý test:** Mock `@/api/projects` không phải `@/store/projectStore`. `ProjectsPage` gọi API trực tiếp qua `getProjects()`, không qua Zustand store.

### Phụ Thuộc Story & Context

**Trước Story 1.6:** Stories 1.1–1.5 đã hoàn thành ✅
- `ProjectsPage.tsx` + `ProjectsPage.module.css` đã có (Story 1.4)
- `DeleteProjectModal`, `CreateProjectModal` đã có (Story 1.4)
- `useTranslation` hook + `translations.ts` đã có (Story 1.5)
- Route `/projects` + `ProtectedRoute` với `Header` đã có (Story 1.4)
- Sidebar "Xem tất cả →" đã navigate đến `/projects` (Story 1.4+1.5)

**Deferred bugs được fix ở Story 1.6** (từ `deferred-work.md`):
- `ProjectsPage` search không debounce → race condition ✅ fix Task 2.2–2.3
- Xóa item cuối trang → trang rỗng ✅ fix Task 2.4
- `Invalid Date` nếu `createdAt` rỗng ✅ fix Task 2.5

**Sau Story 1.6:** Epic 2 bắt đầu (tab Thư viện Tài liệu)

### Learnings từ Stories Trước

1. **`getErrorMessage(err, 'fallback string')`** — bắt buộc có tham số thứ 2. Thiếu → lỗi TS2554.

2. **CSS Modules + CSS Variables** — KHÔNG dùng inline styles cho màu sắc.

3. **Zustand pattern**: `const { field, action } = useStore()` — không import store rồi gọi `.getState()` inline.

4. **`useCallback` cho loadProjects** — đã có pattern đúng trong code hiện tại, giữ nguyên.

5. **Mock trong Vitest**: mock module-level (`vi.mock('@/api/projects')`), không mock từng function.

6. **`MemoryRouter` bắt buộc trong test** vì `ProjectsPage` dùng hook router (qua `Header` nếu render, nhưng test chỉ render `ProjectsPage` thôi, vẫn cần nếu component có `Link`/`useNavigate` transitively).

7. **Không dùng `act()` thủ công** với RTL — `waitFor()` tự xử lý async.

### API Reference — getProjects

```typescript
// frontend/src/api/projects.ts (đã có, không sửa)
export async function getProjects(
  limit: number,
  offset: number,
  search?: string
): Promise<{ items: ProjectResponse[]; total: number }> { ... }
```

### Type Reference — ProjectResponse

```typescript
// frontend/src/types/project.ts (đã có, không sửa)
export interface ProjectResponse {
  id: string;
  name: string;
  description: string | null;
  createdAt: string;
  updatedAt: string;
}
```

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Completion Notes List

- Thêm 12 translation keys `projects.*` vào `translations.ts` (11 keys + `projects.pageNext` do đếm lại)
- Refactor `ProjectsPage.tsx`: thêm `useTranslation`, tách 2 useEffect (debounce + load), `formatDate()` helper, `handleDeleteSuccess` callback, icon 🗑 thay text "Xóa", format ngày theo locale
- Tạo 7 test cases trong `ProjectsPage.test.tsx`: bảng, tiêu đề cột, invalid date, modal xóa, debounce với fake timers, phân trang hiện/ẩn
- Tất cả 44 tests pass, không regression

### File List

**Cập nhật:**
- frontend/src/i18n/translations.ts
- frontend/src/features/workspace/ProjectsPage.tsx

**Mới:**
- frontend/src/features/workspace/__tests__/ProjectsPage.test.tsx

### Review Findings

_Code review 2026-06-16 (Blind Hunter + Edge Case Hunter + Acceptance Auditor). 4 patch, 3 defer, ~10 dismissed as noise._

- [x] [Review][Patch] Empty-state chọn thông điệp theo `searchQuery` trong khi dữ liệu hiển thị theo `debouncedSearch` — lệch trong cửa sổ 300ms (gõ/xóa từ khóa hiện sai "Không tìm thấy" vs "Chưa có dự án"). Sửa: dùng `debouncedSearch` ở ternary empty-state. [frontend/src/features/workspace/ProjectsPage.tsx:93]
- [x] [Review][Patch] Thiếu test cho AC#4 (xóa item cuối ở trang > 1 → tự lùi trang). Spec yêu cầu rõ test cover AC#4 nhưng không test nào chạm `handleDeleteSuccess` với `page > 0`. [frontend/src/features/workspace/__tests__/ProjectsPage.test.tsx]
- [x] [Review][Patch] Thiếu assertion cho AC#3 phần "về trang 1" — debounce có test nhưng không kiểm tra reset page khi đang ở trang > 1. [frontend/src/features/workspace/__tests__/ProjectsPage.test.tsx]
- [x] [Review][Patch] Nút xóa đổi từ chữ "Xóa" sang emoji 🗑 chỉ dựa vào `title` — thiếu `aria-label`, regression a11y (screen reader đọc không nhất quán). [frontend/src/features/workspace/ProjectsPage.tsx:115]
- [x] [Review][Defer] Race condition: `loadProjects` không hủy request cũ (không AbortController/latest-wins) — response cũ có thể đè dữ liệu mới. Pre-existing, là pattern toàn app, debounce đã giảm thiểu phần lớn. [frontend/src/features/workspace/ProjectsPage.tsx]
- [x] [Review][Defer] `formatDate` với chuỗi date-only (`'2026-06-16'`) bị lệch ngày 1 đơn vị ở timezone âm (parse UTC midnight rồi render local). Phụ thuộc format backend trả về; pre-existing. [frontend/src/features/workspace/ProjectsPage.tsx:13]
- [x] [Review][Defer] `CreateProjectModal.onSuccess` refetch trang hiện tại — dự án mới tạo có thể rơi vào trang khác và không hiện, không feedback. Pre-existing (giữ nguyên hành vi cũ). [frontend/src/features/workspace/ProjectsPage.tsx]

## Change Log

- 2026-06-16: Tạo Story 1.6 — BMad Method v6.8.0 (create-story). Phần lớn logic đã implement ở Story 1.4; story này fix 3 deferred bugs + thêm i18n + viết tests.
- 2026-06-16: Implement xong — thêm i18n keys, refactor ProjectsPage (debounce, formatDate, handleDeleteSuccess, icon 🗑), tạo 7 tests. Status → review.
- 2026-06-16: Code review (adversarial 3-layer) — 4 patch + 3 defer findings, ~10 dismissed.
