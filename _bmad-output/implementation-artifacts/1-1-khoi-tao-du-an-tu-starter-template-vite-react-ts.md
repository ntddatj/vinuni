---
baseline_commit: 498119ff8ae445a7bd8cc65594989130660ddfc9
---
# Story 1.1: Khởi tạo dự án từ Starter Template (Vite + React TS)

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a kỹ sư phát triển,
I want khởi tạo mã nguồn Frontend từ starter template được phê duyệt,
so that tôi có cấu trúc dự án chuẩn và môi trường chạy thử nghiệm sẵn sàng.

## Acceptance Criteria

1. **Given** môi trường phát triển đã sẵn sàng ở thư mục dự án
   **When** chạy lệnh khởi tạo `npm create vite@latest frontend -- --template react-ts`
   **Then** hệ thống tạo thư mục `/frontend` chứa mã nguồn Vite + React + TypeScript tĩnh
2. **And** cấu hình ESLint, Prettier và tệp `vite.config.ts` để serve static files
3. **And** chạy thành công lệnh `npm run dev` để khởi động môi trường phát triển local không lỗi

## Tasks / Subtasks

- [x] Khởi tạo dự án Vite React TS (AC: 1)
  - [x] Chạy lệnh `npm create vite@latest frontend -- --template react-ts` (hoặc qua npx) ở chế độ tự động chấp nhận để tạo thư mục `/frontend`.
  - [x] Cài đặt các package mặc định bằng `npm install`.
- [x] Cài đặt và cấu hình ESLint và Prettier (AC: 2)
  - [x] Cài đặt Prettier và các plugin ESLint cần thiết (`eslint-config-prettier`, `eslint-plugin-prettier`).
  - [x] Tạo file `.prettierrc` cấu hình các quy chuẩn định dạng (ví dụ: singleQuote: true, tabWidth: 2, semi: true).
  - [x] Cấu hình ESLint để kiểm tra mã nguồn TypeScript và tích hợp với Prettier.
- [x] Thiết lập cấu hình Vite (AC: 2)
  - [x] Kiểm tra và tối ưu hóa file `vite.config.ts` để serve static files và hỗ trợ aliases nếu cần thiết.
- [x] Chạy thử nghiệm và xác minh (AC: 3)
  - [x] Thực hiện lệnh `npm run dev` để khởi động Vite dev server local (port 5173).
  - [x] Đảm bảo ứng dụng React TS chạy không lỗi trên console trình duyệt và console terminal.

## Dev Notes

- **Kiến trúc & Công nghệ:** Dự án sử dụng Vite + React + TypeScript. Không sử dụng Tailwind CSS (sử dụng CSS Modules/Vanilla CSS cho mọi component sau này).
- **Cấu trúc Thư mục Frontend:** Tất cả mã nguồn sau này phải tuân thủ cấu trúc:
  - `/frontend/src/components` (Sidebar, ChatPanel, KnowledgeMap, Editor, UI Elements)
  - `/frontend/src/hooks` (useSSE, useChat, useIngest)
  - `/frontend/src/styles` (Màu sắc và typography theo DESIGN.md)
  - `/frontend/src/context` (Trạng thái dự án)
- **Tầng Production:** Sau này, frontend sẽ được build tĩnh qua `npm run build` và backend FastAPI sẽ serve các file tĩnh từ `/frontend/dist`.

### Project Structure Notes

- Thư mục frontend được tạo tại `{project-root}/frontend`.
- Không sử dụng Tailwind CSS theo đúng tiêu chuẩn thiết kế của dự án (trừ khi có yêu cầu cụ thể khác của User).

### References

- [Epics breakdown](file:///home/agent/github/C2-App-053/_bmad-output/planning-artifacts/epics.md#Story 1.1: Khởi tạo dự án từ Starter Template (Vite + React TS))
- [Architecture Document - Frontend SPA](file:///home/agent/github/C2-App-053/_bmad-output/planning-artifacts/architecture.md#Kiến trúc Frontend (Frontend Architecture))

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (Medium)

### Debug Log References

### Completion Notes List

- Khởi tạo thành công dự án frontend bằng Vite (React + TypeScript).
- Đã cấu hình tích hợp ESLint và Prettier thành công. Đã định dạng và sửa toàn bộ lỗi linting.
- Cấu hình path alias `@/` ánh xạ tới thư mục `src` cho cả Vite (`vite.config.ts`) và TypeScript (`tsconfig.app.json`).
- Đã kiểm tra chạy dev server thành công bằng `npm run dev` ở cổng 5173.
- Viết bộ test kiểm tra cấu trúc thư mục frontend (`tests/test_frontend_init.py`) và tích hợp thành công vào pytest suite chạy 100% pass.

### File List

- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/vite.config.ts`
- `frontend/tsconfig.json`
- `frontend/tsconfig.app.json`
- `frontend/tsconfig.node.json`
- `frontend/eslint.config.js`
- `frontend/.prettierrc`
- `frontend/index.html`
- `frontend/src/App.tsx`
- `frontend/src/main.tsx`
- `frontend/src/vite-env.d.ts`
- `tests/test_frontend_init.py`
- `pytest.ini`
