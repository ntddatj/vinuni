---
baseline_commit: a866f323c6bcea24ab3c0d7cf6985bd7f5f54ad4
---

# Story 1.3: [Frontend] Auth UI, Onboarding & Khởi tạo Dự án Đầu tiên

Status: done

## Story

Với vai trò là khách vãng lai,
Tôi muốn giao diện Đăng ký / Đăng nhập và màn hình Onboarding tích hợp tạo dự án đầu tiên,
Để tôi có thể xác thực vào hệ thống, nhận quyền Admin (nếu có) và bắt đầu nghiên cứu với dự án đầu tiên.

## Acceptance Criteria

1. **Given** trang Đăng nhập `/login`
   **When** nhập sai email/password
   **Then** hiện Toast báo lỗi với message từ backend (401) — ví dụ: "Email hoặc mật khẩu không đúng"

2. **Given** trang Đăng nhập
   **When** nhập đúng credentials và gọi `POST /api/auth/login` thành công
   **Then** lưu thông tin user vào Zustand auth store → kiểm tra số dự án → nếu 0 dự án: redirect sang `/onboarding`; nếu có dự án: redirect sang `/dashboard`

3. **Given** người dùng đã đăng nhập với `role === 'admin'`
   **When** nhìn lên Header của bất kỳ trang bảo mật nào
   **Then** nút Bánh răng ⚙️ "Cài đặt Hệ thống" hiển thị; với user thường, nút này ẩn

4. **Given** người dùng đã đăng nhập nhưng chưa có dự án nào (0 projects)
   **When** truy cập `/onboarding`
   **Then** màn hình split 2 khu vực: trái là Form "Tạo dự án đầu tiên" (tên bắt buộc, mô tả tùy chọn); phải là Checklist 3 bước hướng dẫn tính năng kèm animation giới thiệu

5. **Given** người dùng điền tên dự án hợp lệ và bấm "Tạo dự án"
   **When** gọi `POST /api/projects` thành công
   **Then** redirect sang `/dashboard`

6. **Given** người dùng chưa đăng nhập (không có cookie hoặc cookie hết hạn)
   **When** truy cập bất kỳ route bảo mật nào (`/dashboard`, `/onboarding`)
   **Then** redirect về `/login`

7. **Given** trang Đăng ký `/register`
   **When** nhập email/password hợp lệ và gọi `POST /api/auth/register` thành công
   **Then** tự động gọi `POST /api/auth/login` với cùng credentials → redirect theo logic AC #2

8. **Given** người dùng đã đăng nhập
   **When** refresh trang (F5) bất kỳ route bảo mật
   **Then** `GET /api/auth/me` xác nhận lại session → không bị redirect ra login ngoài ý muốn

## Tasks / Subtasks

- [x] Task 1: Cài đặt packages nền tảng & cấu hình Vite (AC: tất cả)
  - [x] 1.1 Cài packages: `react-router-dom@^7.17.0`, `zustand@^5.0.14`, `axios@^1.9.0`, `sonner@^2.0.0` (toast)
  - [x] 1.2 Cài dev dependencies: `vitest@^3.0.0`, `@testing-library/react@^16.0.0`, `@testing-library/user-event@^14.0.0`, `jsdom@^26.0.0`
  - [x] 1.3 Cập nhật `frontend/vite.config.ts`: thêm `server.proxy` — `/api` → `http://localhost:8000`; thêm `test` config cho vitest (environment: 'jsdom')

- [x] Task 2: Tạo cấu trúc thư mục Frontend theo Architecture (AC: tất cả)
  - [x] 2.1 Tạo `frontend/src/api/` — thư mục chứa Axios instance và API functions
  - [x] 2.2 Tạo `frontend/src/store/` — thư mục Zustand slices
  - [x] 2.3 Tạo `frontend/src/features/auth/` — Auth pages & components
  - [x] 2.4 Tạo `frontend/src/features/onboarding/` — Onboarding page

- [x] Task 3: Tạo Axios HTTP Client (AC: tất cả)
  - [x] 3.1 Tạo `frontend/src/api/client.ts`:
    - Axios instance với `baseURL: ''` (vite proxy handle `/api`)
    - `withCredentials: true` (để gửi HttpOnly cookie tự động)
    - Response interceptor: nếu status 401 → redirect `window.location.href = '/login'`
  - [x] 3.2 Tạo `frontend/src/api/auth.ts` với các functions:
    - `loginUser(email, password): Promise<UserResponse>`
    - `registerUser(email, password): Promise<UserResponse>`
    - `getCurrentUser(): Promise<UserResponse>`
    - `logoutUser(): Promise<void>`
  - [x] 3.3 Tạo `frontend/src/api/projects.ts` với function:
    - `createProject(name, description?): Promise<ProjectResponse>`
    - `listProjects(): Promise<ProjectResponse[]>` (dùng để kiểm tra có dự án hay không)

- [x] Task 4: Tạo TypeScript interfaces (AC: tất cả)
  - [x] 4.1 Tạo `frontend/src/types/auth.ts`:
    ```typescript
    export interface UserResponse {
      id: string;
      email: string;
      role: 'admin' | 'user';
      isActive: boolean;
      createdAt: string;
      updatedAt: string;
    }
    ```
  - [x] 4.2 Tạo `frontend/src/types/project.ts`:
    ```typescript
    export interface ProjectResponse {
      id: string;
      name: string;
      description?: string;
      userId: string;
      createdAt: string;
      updatedAt: string;
    }
    export interface CreateProjectRequest {
      name: string;
      description?: string;
    }
    ```

- [x] Task 5: Tạo Zustand Auth Store (AC: #2, #3, #6, #8)
  - [x] 5.1 Tạo `frontend/src/store/authStore.ts`:
    ```typescript
    interface AuthState {
      user: UserResponse | null;
      isLoading: boolean;
      setUser: (user: UserResponse | null) => void;
      setLoading: (loading: boolean) => void;
    }
    ```
    - Dùng `create<AuthState>()` từ zustand
    - `user: null` là state ban đầu (chưa biết session)
    - KHÔNG persist vào localStorage — user info luôn lấy từ `/api/auth/me`

- [x] Task 6: Tạo App Router & Protected Route (AC: #6, #8)
  - [x] 6.1 Tạo `frontend/src/components/ProtectedRoute.tsx`:
    - Khi mount: gọi `GET /api/auth/me`, lưu user vào store
    - Nếu 401 → redirect `/login`
    - Trong khi loading: hiển thị spinner (không flash redirect)
  - [x] 6.2 Cập nhật `frontend/src/main.tsx`: wrap với `<BrowserRouter>` (từ react-router-dom)
  - [x] 6.3 Cập nhật `frontend/src/App.tsx`: thiết lập `<Routes>`:
    - `/login` → `<LoginPage>`
    - `/register` → `<RegisterPage>`
    - `/onboarding` → `<ProtectedRoute><OnboardingPage></ProtectedRoute>`
    - `/dashboard` → `<ProtectedRoute><DashboardPage></ProtectedRoute>` (placeholder cho Story 1.5)
    - `/` → redirect `/login`
  - [x] 6.4 Tạo `frontend/src/features/dashboard/DashboardPage.tsx` placeholder: chỉ render `<div>Dashboard (Story 1.5)</div>` — cần thiết để routing không bị lỗi

- [x] Task 7: Tạo trang Login (AC: #1, #2, #3)
  - [x] 7.1 Tạo `frontend/src/features/auth/LoginPage.tsx`:
    - Form: `email` (type="email", required), `password` (type="password", required, minLength=8)
    - Submit: gọi `loginUser(email, password)` → lưu user vào store
    - Thành công: gọi `listProjects()` → nếu `length === 0` → navigate('/onboarding'), else → navigate('/dashboard')
    - Lỗi 401: `toast.error(error.response.data.detail)` — hiển thị message từ backend
    - Loading state: disable button + hiển thị spinner khi đang gọi API
    - Link "Chưa có tài khoản? Đăng ký" → `/register`
  - [x] 7.2 Thêm `<Toaster>` từ sonner vào `App.tsx` (1 lần, toàn app)

- [x] Task 8: Tạo trang Register (AC: #7)
  - [x] 8.1 Tạo `frontend/src/features/auth/RegisterPage.tsx`:
    - Form: `email` (type="email"), `password` (type="password", minLength=8)
    - Validate `password` max 72 ký tự phía client (backend sẽ reject > 72 byte với 422)
    - Submit: gọi `registerUser(email, password)` → nếu thành công: tự động gọi `loginUser(email, password)` → navigate theo logic AC #2
    - Lỗi 400 (email đã tồn tại): hiển thị toast lỗi
    - Link "Đã có tài khoản? Đăng nhập" → `/login`

- [x] Task 9: Tạo Header với Admin Gating (AC: #3)
  - [x] 9.1 Tạo `frontend/src/components/Header.tsx`:
    - Đọc `user` từ `useAuthStore()`
    - Nút ⚙️ "Cài đặt Hệ thống" chỉ render khi `user?.role === 'admin'`
    - Nút 🚪 "Đăng xuất": gọi `logoutUser()` → reset `setUser(null)` → navigate('/login')
    - Toggle ngôn ngữ VI | EN (chỉ render label, logic i18n sẽ ở Story 1.5)
    - Toggle Dark/Light Mode (chỉ toggle class `dark` trên `document.documentElement`)

- [x] Task 10: Tạo trang Onboarding (AC: #4, #5)
  - [x] 10.1 Tạo `frontend/src/features/onboarding/OnboardingPage.tsx`:
    - Layout split 2 cột: trái 50% Form, phải 50% Checklist
    - **Khu vực trái — Form tạo dự án đầu tiên:**
      - Tiêu đề: "Tạo dự án đầu tiên của bạn"
      - Input "Tên dự án" (required)
      - Textarea "Mô tả ngắn" (optional)
      - Button "Tạo dự án" → gọi `createProject(name, description)` → navigate('/dashboard')
    - **Khu vực phải — Checklist hướng dẫn:**
      - Tiêu đề: "Hướng dẫn bắt đầu nhanh"
      - 3 mục checklist có animation fade-in lần lượt:
        1. ✅ "Tạo dự án nghiên cứu đầu tiên"
        2. 📚 "Tìm kiếm và nạp bài báo khoa học"
        3. 🤖 "Chat với AI để phân tích tài liệu"
      - Sử dụng CSS animation `fadeIn` cho từng bước (delay 0ms, 300ms, 600ms)
    - Guard: nếu user có projects (kiểm tra khi mount) → redirect `/dashboard` ngay

- [x] Task 11: Styling theo Design System AcademicPaper (AC: #4)
  - [x] 11.1 Thêm CSS variables vào `frontend/src/index.css`:
    ```css
    :root {
      --surface-base: #FAF9F6;
      --surface-raised: #FFFFFF;
      --ink-primary: #1E2022;
      --ink-secondary: #64748B;
      --accent-blue: #2563EB;
      --state-danger: #EF4444;
      --border-hairline: #E2E8F0;
    }
    .dark {
      --surface-base: #1F2023;
      --surface-raised: #282A2D;
      --ink-primary: #E4E6EB;
      --ink-secondary: #94A3B8;
      --accent-blue: #60A5FA;
      --border-hairline: #383A40;
    }
    ```
  - [x] 11.2 Font family: `Inter, system-ui, sans-serif` — thêm vào `body` trong `index.css`
  - [x] 11.3 Sử dụng CSS Modules (`.module.css`) cho từng component — KHÔNG dùng inline styles hoặc Tailwind (chưa cài)

- [x] Task 12: Viết tests (AC: #1, #2, #6, #7, #8)
  - [x] 12.1 Tạo `frontend/src/features/auth/__tests__/LoginPage.test.tsx`:
    - Mock axios module
    - Test: sai credentials → toast lỗi hiển thị
    - Test: đúng credentials + 0 projects → navigate('/onboarding')
    - Test: đúng credentials + >0 projects → navigate('/dashboard')
  - [x] 12.2 Tạo `frontend/src/features/auth/__tests__/RegisterPage.test.tsx`:
    - Test: register thành công → auto login → navigate
    - Test: email đã tồn tại → toast lỗi
  - [x] 12.3 Tạo `frontend/src/components/__tests__/ProtectedRoute.test.tsx`:
    - Test: không có session (401 từ /me) → redirect /login
    - Test: có session hợp lệ → render children
  - [x] 12.4 Cấu hình `frontend/vitest.config.ts` (hoặc thêm vào `vite.config.ts`):
    ```typescript
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: ['./src/test/setup.ts'],
    }
    ```
  - [x] 12.5 Tạo `frontend/src/test/setup.ts`: import `@testing-library/jest-dom`

## Dev Notes

### ⚠️ CÁC LỖI THƯỜNG GẶP CỦA LLM — PHẢI TRÁNH

1. **KHÔNG dùng localStorage để cache user info** — Security risk. Session state PHẢI được verify qua `/api/auth/me` mỗi lần reload. Zustand store chỉ là in-memory cache.
2. **KHÔNG gọi API với URL tuyệt đối** (e.g. `http://localhost:8000/api/...`) — Vite proxy tự chuyển `/api/...` sang backend. Axios base URL = `''`.
3. **KHÔNG flash redirect khi đang loading** — ProtectedRoute phải hiển thị spinner khi đang fetch `/api/auth/me`, chỉ redirect khi chắc chắn 401.
4. **KHÔNG tự viết toast system** — Dùng `sonner` đã cài. `toast.error()`, `toast.success()`.
5. **KHÔNG import trực tiếp từ `axios`** — Luôn dùng custom Axios instance từ `@/api/client.ts`.
6. **KHÔNG dùng Tailwind** — Chưa được cài trong project. Dùng CSS Modules + CSS variables.
7. **KHÔNG thay đổi `backend/`** — Story này là 100% Frontend.

### Cấu trúc thư mục đầy đủ sau khi hoàn thành

```
frontend/src/
├── api/
│   ├── client.ts          # Axios instance (withCredentials: true)
│   ├── auth.ts            # login, register, me, logout functions
│   └── projects.ts        # createProject, listProjects functions
├── store/
│   └── authStore.ts       # Zustand auth slice
├── types/
│   ├── auth.ts            # UserResponse interface
│   └── project.ts         # ProjectResponse, CreateProjectRequest interfaces
├── components/
│   ├── ProtectedRoute.tsx  # Auth guard + session verification
│   ├── Header.tsx          # Admin gear gating, logout, lang/theme toggle
│   └── __tests__/
│       └── ProtectedRoute.test.tsx
├── features/
│   ├── auth/
│   │   ├── LoginPage.tsx
│   │   ├── RegisterPage.tsx
│   │   └── __tests__/
│   │       ├── LoginPage.test.tsx
│   │       └── RegisterPage.test.tsx
│   ├── onboarding/
│   │   └── OnboardingPage.tsx
│   └── dashboard/
│       └── DashboardPage.tsx  # Placeholder — Story 1.5 sẽ implement
├── test/
│   └── setup.ts
├── App.tsx                # Routes config
├── main.tsx               # BrowserRouter wrap
└── index.css              # CSS variables AcademicPaper design system
```

### API Contracts — Backend đã triển khai (Stories 1.1 & 1.2)

**POST /api/auth/register** (Story 1.1)
```json
Request: { "email": "user@example.com", "password": "securepass123" }
Response 200: UserResponse (camelCase, xem types/auth.ts)
Response 400: { "detail": "Email đã tồn tại" }
Response 422: { "detail": [...] } — validation error (password quá ngắn/dài)
```

**POST /api/auth/login** (Story 1.2)
```json
Request: { "email": "...", "password": "..." }
Response 200: UserResponse + Set-Cookie: access_token=<JWT>; HttpOnly; SameSite=Lax
Response 401: { "detail": "Email hoặc mật khẩu không đúng" }
```

**GET /api/auth/me** (Story 1.2)
```json
Response 200: UserResponse (nếu cookie hợp lệ)
Response 401: { "detail": "Chưa xác thực" } — không có cookie hoặc hết hạn
```

**POST /api/auth/logout** (Story 1.2)
```json
Response 200: { "message": "Đã đăng xuất thành công" } + Set-Cookie: access_token=; Max-Age=0
```

**POST /api/projects** (Story 1.4 — CHƯA có backend, nhưng API client phải sẵn sàng)
```json
Request: { "name": "Tên dự án", "description": "Mô tả" }
Response 200/201: ProjectResponse (camelCase)
```

**GET /api/projects** (Story 1.4 — CHƯA có backend)
```json
Response 200: ProjectResponse[] — dùng để kiểm tra user có dự án chưa
```

> ⚠️ Khi Story 1.3 chạy độc lập (Story 1.4 chưa hoàn thành), các API `/api/projects` sẽ trả về 404. Axios interceptor sẽ không redirect vì không phải 401. Form onboarding sẽ hiện lỗi. Đây là expected behavior — AC #5 sẽ pass đầy đủ sau Story 1.4.

### Axios Client Pattern — Chi tiết

```typescript
// frontend/src/api/client.ts
import axios from 'axios';

const apiClient = axios.create({
  baseURL: '',        // Vite proxy handle /api → localhost:8000
  withCredentials: true, // Gửi HttpOnly cookie tự động
  headers: { 'Content-Type': 'application/json' },
});

// Response interceptor: 401 → redirect login
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      window.location.href = '/login';
    }
    return Promise.reject(error);
  },
);

export default apiClient;
```

> **LƯU Ý QUAN TRỌNG:** `withCredentials: true` là bắt buộc để trình duyệt tự động gửi HttpOnly cookie `access_token` trong mọi request. Thiếu flag này sẽ dẫn đến 401 trên mọi endpoint bảo mật.

### Zustand Auth Store Pattern

```typescript
// frontend/src/store/authStore.ts
import { create } from 'zustand';
import type { UserResponse } from '@/types/auth';

interface AuthState {
  user: UserResponse | null;
  isLoading: boolean;
  setUser: (user: UserResponse | null) => void;
  setLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthState>()((set) => ({
  user: null,
  isLoading: true,  // true ban đầu — ProtectedRoute đang verify
  setUser: (user) => set({ user }),
  setLoading: (isLoading) => set({ isLoading }),
}));
```

### ProtectedRoute Pattern

```typescript
// frontend/src/components/ProtectedRoute.tsx
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { getCurrentUser } from '@/api/auth';

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading, setUser, setLoading } = useAuthStore();
  const navigate = useNavigate();

  useEffect(() => {
    if (user) { setLoading(false); return; }  // đã verify rồi
    getCurrentUser()
      .then((u) => { setUser(u); setLoading(false); })
      .catch(() => { navigate('/login', { replace: true }); });
  }, []);

  if (isLoading) return <div className="spinner" />;  // Chống flash
  return <>{children}</>;
}
```

### Vite Proxy Config (thêm vào `frontend/vite.config.ts`)

```typescript
server: {
  host: true,  // đã có
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
},
```

### Vitest Config (thêm vào `frontend/vite.config.ts`)

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
  },
});
```

### Test Pattern (LoginPage)

```typescript
// vi.mock('axios') hoặc mock @/api/auth
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { LoginPage } from '../LoginPage';
import * as authApi from '@/api/auth';
import * as projectsApi from '@/api/projects';

vi.mock('@/api/auth');
vi.mock('@/api/projects');

it('redirects to onboarding when no projects', async () => {
  vi.mocked(authApi.loginUser).mockResolvedValue({ id: '1', role: 'user', ... });
  vi.mocked(projectsApi.listProjects).mockResolvedValue([]);
  
  const mockNavigate = vi.fn();
  vi.mock('react-router-dom', async () => ({
    ...await vi.importActual('react-router-dom'),
    useNavigate: () => mockNavigate,
  }));

  render(<MemoryRouter><LoginPage /></MemoryRouter>);
  fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'a@b.com' } });
  fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'pass1234' } });
  fireEvent.click(screen.getByRole('button', { name: /đăng nhập/i }));
  
  await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/onboarding'));
});
```

### Design System AcademicPaper — Tóm tắt

| Token | Light Mode | Dark Mode |
|-------|------------|-----------|
| surface-base | `#FAF9F6` (ấm) | `#1F2023` |
| surface-raised | `#FFFFFF` | `#282A2D` |
| ink-primary | `#1E2022` | `#E4E6EB` |
| ink-secondary | `#64748B` | `#94A3B8` |
| accent-blue | `#2563EB` | `#60A5FA` |
| state-danger | `#EF4444` | `#F87171` |
| border-hairline | `#E2E8F0` | `#383A40` |

- Font: `Inter, system-ui, sans-serif` — 13px body, 16px/600 title
- Border radius: sm=4px, md=6px, lg=8px
- Spacing: 4/8/12/16/24/32px

### Onboarding Checklist 3 bước — Nội dung cụ thể

```
Bước 1: ✅ Tạo dự án nghiên cứu đầu tiên
         "Đặt tên cho không gian nghiên cứu của bạn"
         [Delay animation: 0ms]

Bước 2: 📚 Nạp tài liệu khoa học  
         "Tìm kiếm arXiv/Semantic Scholar hoặc upload PDF"
         [Delay animation: 300ms]

Bước 3: 🤖 Chat với AI Agent
         "Phân tích khoảng trống nghiên cứu bằng RAG"
         [Delay animation: 600ms]
```

CSS animation fadeIn cho checklist:
```css
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
.checklistItem {
  animation: fadeInUp 0.4s ease-out both;
}
```

### Phụ thuộc Story & Thứ tự Triển khai

- **Trước Story 1.3:** Stories 1.1 (Register API) + 1.2 (Login API) đã hoàn thành ✅
- **Sau Story 1.3:** Story 1.4 (CRUD dự án + Left Sidebar) sẽ implement `/api/projects` backend
  - Form tạo dự án trong OnboardingPage sẽ bắt đầu hoạt động end-to-end sau Story 1.4
  - AC #5 có thể không pass hoàn toàn cho đến Story 1.4 backend xong
- **Sau Story 1.4:** Story 1.5 (3-column Layout) sẽ implement DashboardPage thực sự

### Tóm tắt Packages Cần Cài

```bash
cd frontend

# Runtime
npm install react-router-dom@^7.17.0 zustand@^5.0.14 axios@^1.9.0 sonner@^2.0.0

# Dev / Testing
npm install -D vitest@^3.0.0 @testing-library/react@^16.0.0 @testing-library/user-event@^14.0.0 @testing-library/jest-dom@^6.0.0 jsdom@^26.0.0
```

### Learnings từ Stories 1.1 & 1.2 (áp dụng cho Story 1.3)

1. **Bcrypt password limit 72 bytes** → Frontend PHẢI validate `password.length <= 72` trước khi submit Register (backend trả 422 nếu vượt)
2. **Password min 1 ký tự cho Login** (không phải 8) — backend LoginRequest dùng `Field(min_length=1)` để không chặn valid credentials
3. **Cookie tên là `access_token`** — Frontend không cần tự quản lý token, axios `withCredentials: true` là đủ
4. **Error message từ backend** dạng `{ "detail": "..." }` — luôn dùng `error.response.data.detail` để hiển thị toast
5. **camelCase responses** — Backend đã cấu hình Pydantic alias_generator, mọi field trả về camelCase (`isActive`, `createdAt`)

### References

- Architecture §4: JWT HttpOnly Cookie, tên cookie `access_token`, `withCredentials` — [architecture.md#4]
- Architecture §2.1: React 19, Vite 8, TypeScript 6, Zustand v5.0.14, React Router v7.17.0 — [architecture.md#2.1]
- Architecture §9.1: Naming conventions — kebab-case files, PascalCase components — [architecture.md#9.1]
- Architecture §9.2: camelCase API responses, `alias_generator=to_camel` — [architecture.md#9.2]
- Architecture §9.4: `frontend/src/api/`, `frontend/src/features/`, `frontend/src/store/` — [architecture.md#9.4]
- UX-DR4: Onboarding gating — form trái + checklist phải — [EXPERIENCE.md#Bố cục các Trang chủ]
- Design System AcademicPaper: color tokens, typography, spacing — [DESIGN.md]
- Story 1.2 Dev Notes: `LoginRequest.password min_length=1`, bcrypt 72-byte limit, cookie name — [1-2-dang-nhap-xac-thuc-bang-httponly-cookie.md]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6 (Dev Story — BMad Method v6.8.0)

### Debug Log References

- ESLint prettier errors: auto-fixed với `eslint --fix` (label nesting trong JSX)
- `useEffect` exhaustive-deps warning: suppressed với inline eslint-disable — intentional mount-only behavior (chạy 1 lần khi component mount để verify session)
- ProtectedRoute test dùng `require()` với alias `@` bị lỗi trong ESM — đổi sang `import { useAuthStore }` trực tiếp

### Completion Notes List

- Task 1-2: Cài đặt 4 runtime packages (react-router-dom, zustand, axios, sonner) + 5 dev packages (vitest, @testing-library/react, user-event, jest-dom, jsdom). Cập nhật vite.config.ts với proxy `/api` → localhost:8000 và vitest config jsdom.
- Task 3-5: Tạo Axios client với `withCredentials: true` và 401 interceptor; API functions cho auth và projects; TypeScript interfaces UserResponse & ProjectResponse; Zustand authStore (in-memory, không persist localStorage).
- Task 6: ProtectedRoute gọi `/api/auth/me` khi mount, hiển thị spinner trong khi loading (tránh flash redirect). App.tsx với full routing. main.tsx wrap BrowserRouter.
- Task 7-9: LoginPage với redirect logic (0 projects → /onboarding, >0 → /dashboard); RegisterPage với validation 72-char limit và auto-login sau register; Header với admin gear gating, dark mode toggle, logout.
- Task 10-11: OnboardingPage split 2 cột (form trái + checklist phải) với CSS fadeInUp animation. index.css viết lại với AcademicPaper design system tokens (light + dark mode).
- Task 12: 8 tests viết và pass (3 LoginPage, 3 RegisterPage, 2 ProtectedRoute). TypeScript check clean. ESLint clean.

### File List

- frontend/package.json (modified — thêm dependencies)
- frontend/vite.config.ts (modified — proxy + vitest config)
- frontend/tsconfig.app.json (modified — thêm vitest/globals type)
- frontend/src/index.css (modified — AcademicPaper design system)
- frontend/src/App.tsx (modified — Routes với BrowserRouter)
- frontend/src/main.tsx (modified — BrowserRouter wrap)
- frontend/src/api/client.ts (new)
- frontend/src/api/auth.ts (new)
- frontend/src/api/projects.ts (new)
- frontend/src/types/auth.ts (new)
- frontend/src/types/project.ts (new)
- frontend/src/store/authStore.ts (new)
- frontend/src/components/ProtectedRoute.tsx (new)
- frontend/src/components/ProtectedRoute.module.css (implicit — spinner in index.css)
- frontend/src/components/Header.tsx (new)
- frontend/src/components/Header.module.css (new)
- frontend/src/components/__tests__/ProtectedRoute.test.tsx (new)
- frontend/src/features/auth/LoginPage.tsx (new)
- frontend/src/features/auth/LoginPage.module.css (new)
- frontend/src/features/auth/RegisterPage.tsx (new)
- frontend/src/features/auth/RegisterPage.module.css (new)
- frontend/src/features/auth/__tests__/LoginPage.test.tsx (new)
- frontend/src/features/auth/__tests__/RegisterPage.test.tsx (new)
- frontend/src/features/onboarding/OnboardingPage.tsx (new)
- frontend/src/features/onboarding/OnboardingPage.module.css (new)
- frontend/src/features/dashboard/DashboardPage.tsx (new)
- frontend/src/test/setup.ts (new)

## Review Findings

### Code Review 2026-06-16 (Blind Hunter + Edge Case Hunter + Acceptance Auditor)

**Tóm tắt:** 4 patch (✅ tất cả đã fix & verify) · 1 defer · 8 dismissed. (Decision về Header đã chốt: mount ngay trong 1.3.) TypeScript clean, 8/8 tests pass sau khi sửa.

#### Patch (sửa được, không cần input)

- [x] [Review][Patch] Header chưa được render trên trang bảo mật (vi phạm AC #3) — ✅ FIXED: mount `<Header />` trong `ProtectedRoute` → Onboarding + Dashboard giờ có Header với admin gating. [frontend/src/components/ProtectedRoute.tsx]
- [x] [Review][Patch] Interceptor 401 hard-reload nuốt toast lỗi đăng nhập/đăng ký (vi phạm AC #1) — ✅ FIXED: loại trừ `/api/auth/login` & `/api/auth/register` khỏi redirect 401 (kiểm tra `error.config.url`). [frontend/src/api/client.ts]
- [x] [Review][Patch] `toast.error` hiển thị `[object Object]` khi backend trả 422 (FastAPI `detail` là array) — ✅ FIXED: thêm helper `getErrorMessage()` chỉ dùng `detail` khi là string. [frontend/src/api/errors.ts] áp dụng tại LoginPage/RegisterPage/OnboardingPage.
- [x] [Review][Patch] Flash nội dung bảo mật do `isLoading` global không reset về `true` (vi phạm anti-pattern #3) — ✅ FIXED: guard render đổi sang `if (isLoading || !user) return spinner` + `setLoading(true)` đầu effect. [frontend/src/components/ProtectedRoute.tsx]

#### Defer (thực nhưng chưa hành động ngay)

- [x] [Review][Defer] `ProtectedRoute` coi mọi lỗi `/me` (network/500) như chưa xác thực và không `setLoading(false)` trong `.catch` [frontend/src/components/ProtectedRoute.tsx:20] — deferred, refinement UX không chặn MVP (component unmount khi navigate)

#### Dismissed (noise / false positive / theo thiết kế)

- Double `listProjects()` (Login/Register + Onboarding mount) — redundancy chấp nhận được, guard có chủ đích.
- Checklist wording lệch AC #4 primary list — dùng bản chi tiết ở Dev Notes (arguably canonical).
- Animation `nth-child(2/3/4)` "off-by-one" — đã verify CHẠY ĐÚNG (h2 là child 1, 3 item là child 2/3/4 → delay 0/300/600ms).
- `baseURL: ''` no-op — có chủ đích (Vite proxy xử lý `/api`), theo spec.
- camelCase types mismatch — backend dùng `alias_generator=to_camel` (learnings), khớp.
- Double-submit window khi `await listProjects` — button `disabled` đã chặn.
- Dark-mode không persist / lang toggle chỉ label — theo thiết kế, i18n hoãn sang Story 1.5.
- Project name whitespace-only không trim — `/api/projects` chưa có (Story 1.4), nicety tối thiểu.

## Change Log

- 2026-06-16: Story 1.3 implementation — Frontend Auth UI, Onboarding & First Project Flow. Tạo toàn bộ frontend layer: Axios client, Zustand store, Router, Login/Register pages, Protected Route, Header với admin gating, Onboarding page split-layout với animation, AcademicPaper design system. 8 tests pass.
