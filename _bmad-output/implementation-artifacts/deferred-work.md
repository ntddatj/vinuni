# Deferred Work

## Deferred from: code review of story 1-5-giao-dien-3-cot-bo-chuyen-doi-ngon-ngu-chu-de (2026-06-16)

- `activeProjectId` đọc từ `?projectId` không validate so với danh sách 10 dự án đã load → URL trỏ project #11+/đã xóa thì tiêu đề cột giữa âm thầm về fallback "Chọn một dự án", không có phản hồi "không tìm thấy". Cần quyết định UX (validate + toast, hay load riêng project đó). [frontend/src/features/dashboard/DashboardPage.tsx:142-148]
- `lang` không lưu localStorage nên reset về 'vi' sau mỗi F5, khác với theme đã persist. AC#7 không yêu cầu persistence nên không chặn story; nên bổ sung `initLang()` + localStorage để nhất quán với theme. [frontend/src/store/languageStore.ts]
- `ProjectsPage` (Story 1.4): ô tìm kiếm không debounce và không hủy request cũ (race condition khi gõ nhanh); xóa item cuối trang để lại trang rỗng không điều hướng được; `new Date(createdAt)` không guard → "Invalid Date" nếu backend trả rỗng. [frontend/src/features/workspace/ProjectsPage.tsx]
- `updateProject` luôn gửi `description: undefined` trong PATCH (có thể ghi đè null mô tả hiện có tùy semantics backend); `addProject` cứng `.slice(0, 10)` truncate khi đã load >10. Thuộc API/store của Story 1.4. [frontend/src/api/projects.ts, frontend/src/store/projectStore.ts]

## Deferred from: code review of story 1-2-dang-nhap-xac-thuc-bang-httponly-cookie (2026-06-16)

- **Login integration tests dùng SQLite trái Dev Notes của spec** — Dev Notes story 1.2 ghi "Không dùng SQLite (intentional decision từ story 1.1)", nhưng test thực tế (`tests/unit/identity/test_login_api.py`) dùng SQLite in-memory. Lý do defer: story 1.1 đã commit `tests/unit/identity/test_register_api.py` dùng **đúng pattern SQLite in-memory y hệt** — đây mới là quy ước thực tế của codebase, ghi chú trong Dev Notes là lỗi thời. Ép test login bỏ SQLite sẽ khiến nó lệch với test register anh em. Việc cần làm sau (nếu muốn): thống nhất chiến lược test ở cấp epic và cập nhật/loại bỏ ghi chú "không dùng SQLite" trong các spec, hoặc chuyển toàn bộ integration test (cả register lẫn login) sang chiến lược khác đồng nhất.

## Deferred from: code review of story 1-3-quy-trinh-onboarding-khoi-tao-du-an-dau-tien (2026-06-16)

- **ProtectedRoute coi mọi lỗi `/me` như chưa xác thực** — `.catch` của `getCurrentUser()` luôn `navigate('/login')` và không `setLoading(false)`, bất kể lỗi là 401, network, hay 500. Lỗi mạng/500 bị đối xử như đăng xuất. Defer vì component unmount khi navigate nên không treo spinner; phân biệt loại lỗi là refinement UX không chặn MVP. [frontend/src/components/ProtectedRoute.tsx:20]

## Deferred from: code review of story 1-4-crud-du-an-nghien-cuu-left-sidebar-dieu-huong (2026-06-16)

- Sidebar click dự án điều hướng `/dashboard?projectId=...` nhưng `DashboardPage` không đọc query param — tương tác "chết" cho tới khi Story 1.5 (layout 3 cột) xử lý. [frontend/src/features/workspace/ProjectSidebar.tsx:72]
- Migration Alembic `002` (JSONB, `gen_random_uuid()`, partial index `WHERE processed = false`) không được test suite chạy qua vì test dùng SQLite tạo bảng từ ORM metadata; `gen_random_uuid()` cần extension pgcrypto trên PostgreSQL < 13. [backend/alembic/versions/002_create_projects_and_sync_outbox_tables.py]
- `addProject` trong Zustand store hardcode `.slice(0, 10)` (liên quan Pitfall #7) — sidebar vẫn hiển thị đúng ≤10 dự án; nên thay bằng hằng số dùng chung hoặc refetch để tránh giả định cứng. [frontend/src/store/projectStore.ts]
- Overlay của CreateProjectModal/DeleteProjectModal vẫn đóng được khi click giữa lúc request đang bay (nút submit đã disable, overlay chưa khóa) — race UX nhỏ. [frontend/src/features/workspace/CreateProjectModal.tsx, DeleteProjectModal.tsx]

## Deferred from: code review of story 1-6-trang-quan-ly-toan-bo-du-an-dang-bang (2026-06-16)

- **Race condition: `loadProjects` không hủy request cũ** — không có AbortController/latest-wins guard; response của lần fetch cũ (đổi search/page/create/delete) có thể resolve sau và đè dữ liệu mới. Defer: là pattern fetch dùng chung toàn app, debounce 300ms đã giảm thiểu phần lớn case gõ tìm kiếm; nên xử lý ở cấp epic (thêm AbortController hoặc request-id chung). [frontend/src/features/workspace/ProjectsPage.tsx]
- **`formatDate` lệch ngày ở timezone âm với chuỗi date-only** — `new Date('2026-06-16')` parse là UTC midnight, `toLocaleDateString` render theo local → user phía tây UTC thấy lệch 1 ngày. Defer: phụ thuộc backend có trả date-only hay full ISO timestamp; hiện `createdAt` là ISO timestamp đầy đủ nên không phát sinh. [frontend/src/features/workspace/ProjectsPage.tsx:13]
- **Tạo dự án mới có thể không hiển thị trên trang hiện tại** — `CreateProjectModal.onSuccess` refetch đúng trang đang xem; dự án mới (tùy sort) có thể rơi sang trang khác và không xuất hiện, không có feedback. Defer: giữ nguyên hành vi cũ, không phải regression của story này. [frontend/src/features/workspace/ProjectsPage.tsx]
