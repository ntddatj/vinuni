---
baseline_commit: 498119ff8ae445a7bd8cc65594989130660ddfc9
---
# Story 1.2: Đăng ký, Đăng nhập & Phân quyền Admin khởi tạo (FR-1)

Status: in-progress

## Story

As a người dùng mới hoặc hiện tại,
I want đăng ký tài khoản và đăng nhập vào hệ thống an toàn,
so that tôi có thể truy cập không gian làm việc cá nhân của mình.

## Acceptance Criteria

1. **Given** người dùng chưa xác thực đang ở trang đăng ký/đăng nhập
   **When** người dùng điền Email và Mật khẩu hợp lệ và bấm Đăng ký
   **Then** hệ thống khởi tạo bản ghi trong bảng `users` ở DB PostgreSQL
2. **And** nếu đây là người dùng đầu tiên đăng ký, gán vai trò `admin`, các người dùng sau nhận vai trò `user`
3. **Given** người dùng đã đăng ký thành công
   **When** người dùng đăng nhập bằng Email và Mật khẩu đúng
   **Then** hệ thống cấp mã JWT lưu trong HttpOnly Cookie với cờ `Secure`, `SameSite=Strict` và điều hướng vào hệ thống
4. **And** nếu thông tin đăng nhập sai, hệ thống trả về mã lỗi HTTP 401 và hiển thị Banner lỗi đăng nhập trên Frontend

## Tasks / Subtasks

- [ ] Thiết lập Database & Models ở Backend (AC: 1, 2)
  - [ ] Định nghĩa bảng `users` trong SQLAlchemy/PostgreSQL với các trường: `id`, `email` (unique), `hashed_password`, `role` (mặc định 'user'), `created_at`.
  - [ ] Viết logic kiểm tra: nếu là user đầu tiên được tạo trong hệ thống, gán vai trò `admin`, ngược lại gán vai trò `user`.
- [ ] Xây dựng REST API Auth ở Backend (AC: 1, 2, 3, 4)
  - [ ] Xây dựng hàm băm mật khẩu (bcrypt) và kiểm tra JWT.
  - [ ] Tạo router `/auth` trong `src/api/routes.py` (hoặc module riêng `src/api/auth.py`).
  - [ ] Triển khai endpoint `POST /api/v1/auth/register` để đăng ký.
  - [ ] Triển khai endpoint `POST /api/v1/auth/login` để xác thực, sinh JWT và lưu vào HttpOnly cookie với cờ `Secure`, `SameSite=Strict`.
  - [ ] Triển khai endpoint `POST /api/v1/auth/logout` để xóa cookie JWT.
  - [ ] Triển khai endpoint `GET /api/v1/auth/me` để kiểm tra thông tin user hiện tại.
- [ ] Xây dựng giao diện Đăng ký / Đăng nhập ở Frontend (AC: 1, 3, 4)
  - [ ] Tạo `authContext.tsx` trong thư mục `/frontend/src/context/` để quản lý trạng thái đăng nhập toàn ứng dụng.
  - [ ] Tạo trang Đăng nhập (`Login.tsx`) và Đăng ký (`Register.tsx`) sử dụng phong cách thiết kế của dự án.
  - [ ] Triển khai cơ chế điều hướng bảo mật (Protected Routes) trong React Router để chặn người dùng chưa đăng nhập.
  - [ ] Hiển thị Banner cảnh báo lỗi màu đỏ/cam nổi bật khi nhận mã HTTP 401 từ API đăng nhập.

## Dev Notes

- **Bảo mật:** Không trả mật khẩu hay mã băm mật khẩu qua API. JWT phải được lưu trữ trong HttpOnly Cookie từ phía backend, không lưu ở LocalStorage hay sessionStorage.
- **Quy chuẩn đặt tên:** snake_case cho DB & JSON API; PascalCase cho React Components và Python classes.
- **Kiến trúc:** Sử dụng module `passlib` cho bcrypt và `pyjwt` hoặc `python-jose` cho JWT ở Backend.

### Project Structure Notes

- File backend model: `src/models/schemas.py` hoặc tạo file chuyên biệt `src/models/user.py`.
- File API: `/src/api/routes.py` hoặc tách `/src/api/auth.py`.
- File frontend components: `/frontend/src/components/Auth/Login.tsx`, `/frontend/src/components/Auth/Register.tsx`.
- File frontend context: `/frontend/src/context/authContext.tsx`.

### References

- [Epics breakdown](file:///home/agent/github/C2-App-053/_bmad-output/planning-artifacts/epics.md#Story 1.2: Đăng ký, Đăng nhập & Phân quyền Admin khởi tạo (FR-1))
- [Architecture Document - Xác thực & Bảo mật](file:///home/agent/github/C2-App-053/_bmad-output/planning-artifacts/architecture.md#Xác thực & Bảo mật (Authentication & Security))

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (Medium)

### Debug Log References

### Completion Notes List

### File List
