# Deferred Work

## Deferred from: code review of story 1-2-dang-nhap-xac-thuc-bang-httponly-cookie (2026-06-16)

- **Login integration tests dùng SQLite trái Dev Notes của spec** — Dev Notes story 1.2 ghi "Không dùng SQLite (intentional decision từ story 1.1)", nhưng test thực tế (`tests/unit/identity/test_login_api.py`) dùng SQLite in-memory. Lý do defer: story 1.1 đã commit `tests/unit/identity/test_register_api.py` dùng **đúng pattern SQLite in-memory y hệt** — đây mới là quy ước thực tế của codebase, ghi chú trong Dev Notes là lỗi thời. Ép test login bỏ SQLite sẽ khiến nó lệch với test register anh em. Việc cần làm sau (nếu muốn): thống nhất chiến lược test ở cấp epic và cập nhật/loại bỏ ghi chú "không dùng SQLite" trong các spec, hoặc chuyển toàn bộ integration test (cả register lẫn login) sang chiến lược khác đồng nhất.

## Deferred from: code review of story 1-3-quy-trinh-onboarding-khoi-tao-du-an-dau-tien (2026-06-16)

- **ProtectedRoute coi mọi lỗi `/me` như chưa xác thực** — `.catch` của `getCurrentUser()` luôn `navigate('/login')` và không `setLoading(false)`, bất kể lỗi là 401, network, hay 500. Lỗi mạng/500 bị đối xử như đăng xuất. Defer vì component unmount khi navigate nên không treo spinner; phân biệt loại lỗi là refinement UX không chặn MVP. [frontend/src/components/ProtectedRoute.tsx:20]
