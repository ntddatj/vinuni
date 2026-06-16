---
baseline_commit: a866f323c6bcea24ab3c0d7cf6985bd7f5f54ad4
---

# Story 1.2: [Backend] Login API & JWT Session

Status: done

## Story

Với vai trò là người dùng,
Tôi muốn API đăng nhập trả về HttpOnly Cookie,
Để tôi có thể truy cập các đường dẫn (route) bảo mật an toàn.

## Acceptance Criteria

1. **Given** email và mật khẩu đúng  
   **When** gọi API `POST /api/auth/login`  
   **Then** Backend cấp 1 token JWT chứa `user_id`  
   **And** trả về client thông qua header `Set-Cookie` (`HttpOnly`, `SameSite=Lax`)  
   **And** response body trả về `UserResponse` (camelCase) với thông tin người dùng

2. **Given** email hoặc mật khẩu sai  
   **When** gọi API `POST /api/auth/login`  
   **Then** trả về HTTP 401 với message rõ ràng  
   **And** KHÔNG tiết lộ email hay mật khẩu nào sai (generic error message)

3. **Given** người dùng chưa đăng nhập (không có cookie)  
   **When** gọi bất kỳ route bảo mật nào (ví dụ: `GET /api/auth/me`)  
   **Then** trả về HTTP 401 Unauthorized

4. **Given** người dùng đã đăng nhập (có cookie hợp lệ)  
   **When** gọi `GET /api/auth/me`  
   **Then** trả về thông tin người dùng hiện tại (`UserResponse`)

5. **Given** người dùng đã đăng nhập  
   **When** gọi `POST /api/auth/logout`  
   **Then** Backend xóa cookie bằng cách set `Set-Cookie: access_token=; Max-Age=0`  
   **And** trả về HTTP 200

> 🔍 **Cách nghiệm thu trực quan:**
> Swagger UI. Gọi API `/api/auth/login`, nhập email/pass đúng. Mở DevTools (F12) → Application → Cookies, thấy cookie `access_token` được gán thành công với flag `HttpOnly`. Gọi `/api/auth/me` thấy trả về thông tin user. Gọi `/api/auth/logout` thấy cookie bị xóa.

## Tasks / Subtasks

- [x] Task 1: Mở rộng Domain Layer — thêm `find_by_id` vào `UserRepository` (AC: #3, #4)
  - [x] 1.1 Thêm method `find_by_id(user_id: str) -> User | None` vào abstract class `UserRepository` tại `backend/src/modules/identity/domain/repositories.py`
  - [x] 1.2 Implement `find_by_id` trong `PostgresUserRepository` tại `backend/src/modules/identity/infrastructure/postgres_repository.py`

- [x] Task 2: Thêm DTO và Exception cho Login (AC: #1, #2)
  - [x] 2.1 Thêm `LoginUserDTO` vào `backend/src/modules/identity/application/dtos.py`
  - [x] 2.2 Thêm `InvalidCredentialsError` vào `backend/src/modules/identity/domain/exceptions.py`

- [x] Task 3: Xây dựng Application Layer — `LoginUserUseCase` (AC: #1, #2)
  - [x] 3.1 Tạo `LoginUserUseCase` trong `backend/src/modules/identity/application/use_cases.py` (thêm vào file hiện có):
    - Tìm user theo email (normalize lowercase)
    - Kiểm tra user tồn tại và `is_active=True`
    - Verify bcrypt password bất đồng bộ qua `loop.run_in_executor`
    - Sinh JWT token chứa `sub: user_id`, `role: role`, `exp: now + JWT_EXPIRE_HOURS`
    - Trả về `LoginResponseDTO` (chứa user info + token string)

- [x] Task 4: Xây dựng JWT Utility (AC: #1, #3, #4)
  - [x] 4.1 Tạo `backend/src/shared/infra/jwt_utils.py`:
    - `create_access_token(user_id: str, role: str) -> str` — ký JWT bằng `settings.secret_key`, algo `HS256`
    - `decode_access_token(token: str) -> dict` — giải mã JWT, raise `InvalidTokenError` nếu hết hạn hoặc sai chữ ký

- [x] Task 5: Xây dựng FastAPI Dependency — `get_current_user` (AC: #3, #4)
  - [x] 5.1 Tạo `backend/src/modules/identity/infrastructure/auth_dependencies.py`:
    - Dependency `get_current_user(request: Request, repo: UserRepository = Depends(get_user_repository)) -> User`:
      - Đọc cookie `access_token` từ `request.cookies`
      - Gọi `decode_access_token`, lấy `user_id`
      - Gọi `repo.find_by_id(user_id)`, nếu không có → raise `HTTPException(401)`
      - Kiểm tra `user.is_active`, nếu False → raise `HTTPException(403)`
      - Trả về `User` domain entity

- [x] Task 6: Mở rộng Presentation Layer — thêm schemas Login/Logout (AC: #1, #2, #5)
  - [x] 6.1 Thêm `LoginRequest` vào `backend/src/modules/identity/presentation/schemas.py` (thêm vào file hiện có):
    - `email: EmailStr`, `password: str = Field(min_length=8)`
  - [x] 6.2 Thêm `LoginResponse` kế thừa `UserResponse` hoặc tái dùng `UserResponse`

- [x] Task 7: Thêm endpoints vào Router (AC: #1, #2, #3, #4, #5)
  - [x] 7.1 Thêm `POST /auth/login` vào `backend/src/modules/identity/presentation/router.py`:
    - Gọi `LoginUserUseCase`
    - Tạo `Response` object, gọi `response.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=settings.jwt_expire_hours * 3600)`
    - Trả về `UserResponse`
  - [x] 7.2 Thêm `GET /auth/me` vào router:
    - Inject `current_user: User = Depends(get_current_user)`
    - Trả về `UserResponse.model_validate(current_user, from_attributes=True)`
  - [x] 7.3 Thêm `POST /auth/logout` vào router:
    - Tạo `Response` object, gọi `response.delete_cookie("access_token")`
    - Trả về `{"message": "Đã đăng xuất thành công"}`

- [x] Task 8: Đăng ký error handler cho `InvalidCredentialsError` (AC: #2)
  - [x] 8.1 Thêm handler cho `InvalidCredentialsError` vào `backend/src/shared/api/error_handlers.py` — trả về HTTP 401

- [x] Task 9: Viết tests (AC: #1, #2, #3, #4, #5)
  - [x] 9.1 Unit test `LoginUserUseCase`: email sai → 401, password sai → 401, user inactive → 401, đúng → trả về DTO
  - [x] 9.2 Unit test `get_current_user` dependency: không có cookie → 401, token hết hạn → 401, user không tồn tại → 401, hợp lệ → trả về User
  - [x] 9.3 Integration test `/api/auth/login`: đúng → có cookie + 200, sai → 401
  - [x] 9.4 Integration test `/api/auth/me`: không có cookie → 401, có cookie hợp lệ → trả về user info
  - [x] 9.5 Integration test `/api/auth/logout`: sau logout cookie bị xóa

### Review Findings

- [x] [Review][Patch] Missing `get_current_user` dependency unit tests — đã thêm `tests/unit/identity/test_auth_dependency.py` (7 test: no-cookie/garbage/expired/missing-sub/not-found → 401, inactive → 403, valid → User). [CR 2026-06-16]
- [x] [Review][Defer] Login integration tests dùng SQLite trái Dev Notes — **deferred, không sửa**: story 1.1 đã commit `test_register_api.py` dùng đúng pattern SQLite in-memory; quy ước thực tế của codebase LÀ SQLite, ghi chú "không dùng SQLite" trong Dev Notes là lỗi thời. [tests/unit/identity/test_login_api.py:15]
- [x] [Review][Patch] Cookie security assertions không kiểm `HttpOnly`/`SameSite=Lax`/`Max-Age=0` — đã bổ sung assertion đọc header Set-Cookie trong `test_login_sets_httponly_cookie` và `test_logout_clears_cookie`. [CR 2026-06-16]
- [x] [Review][Patch] Malformed bcrypt hash → 500 — đã guard `try/except ValueError` trong `_verify_password` (trả False → 401 generic). [backend/src/modules/identity/application/use_cases.py:17]
- [x] [Review][Patch] JWT decode chấp nhận token thiếu `exp`/`sub` — đã thêm `options={"require": ["exp","sub"]}`. [backend/src/shared/infra/jwt_utils.py:20]
- [x] [Review][Patch] JWT `sub` chưa validate trước khi query repo — đã thêm kiểm tra `isinstance(user_id, str)` (không ép UUID-format vì token đã được verify chữ ký và query đã tham số hóa). [backend/src/modules/identity/infrastructure/auth_dependencies.py:31]

#### Review Findings — Adversarial 3-layer (2026-06-16)

Review độc lập (Blind Hunter + Edge Case Hunter + Acceptance Auditor) **xác nhận 6 finding ở trên là thật**. Bổ sung:

- [x] [Review][Patch] Bỏ `min_length` khỏi `LoginRequest.password` — đã đổi thành `Field(min_length=1)`; thêm test `test_login_short_password_reaches_auth_not_422`. [CR 2026-06-16] [backend/src/modules/identity/presentation/schemas.py]
- [x] [Review][Patch] Mật khẩu > 72 byte gây `bcrypt.ValueError` → 500 — đã guard `_verify_password` (login → 401) và thêm `field_validator` giới hạn 72 byte cho `RegisterRequest` (register → 422); thêm test `test_login_long_password_returns_401_not_500`. [CR 2026-06-16] [backend/src/modules/identity/presentation/schemas.py]



### ⚠️ FILES PHẢI ĐỌC TRƯỚC KHI CODE

**Files CẦN CẬP NHẬT (UPDATE — đọc kỹ trước khi chỉnh sửa):**
- `backend/src/modules/identity/domain/repositories.py` — thêm `find_by_id` abstract method
- `backend/src/modules/identity/infrastructure/postgres_repository.py` — implement `find_by_id`
- `backend/src/modules/identity/application/dtos.py` — thêm `LoginUserDTO`, `LoginResponseDTO`
- `backend/src/modules/identity/application/use_cases.py` — thêm `LoginUserUseCase`
- `backend/src/modules/identity/domain/exceptions.py` — thêm `InvalidCredentialsError`
- `backend/src/modules/identity/presentation/schemas.py` — thêm `LoginRequest`
- `backend/src/modules/identity/presentation/router.py` — thêm 3 endpoints mới
- `backend/src/shared/api/error_handlers.py` — thêm handler `InvalidCredentialsError`

**Files TẠO MỚI:**
- `backend/src/shared/infra/jwt_utils.py`
- `backend/src/modules/identity/infrastructure/auth_dependencies.py`
- `tests/unit/identity/test_login_use_case.py`
- `tests/unit/identity/test_auth_dependency.py`

### Trạng thái Code Hiện tại (Story 1.1 đã xây dựng)

Story 1.1 đã hoàn thành và tạo nên nền tảng Hexagonal Architecture. Dev agent CẦN HIỂU cấu trúc hiện tại trước khi thêm code:

**`UserRepository` (abstract) — hiện có:**
```python
# backend/src/modules/identity/domain/repositories.py
class UserRepository(ABC):
    async def find_by_email(self, email: str) -> User | None: ...
    async def count_all(self) -> int: ...
    async def save(self, user: User) -> User: ...
```
→ Story 1.2 THÊM `find_by_id(user_id: str) -> User | None`

**`User` entity — hiện có (KHÔNG được thay đổi):**
```python
# backend/src/modules/identity/domain/entities.py
@dataclass
class User:
    id: str  # UUID dạng string (as_uuid=False)
    email: str
    hashed_password: str
    role: str  # 'admin' hoặc 'user'
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
```

**`UserORM` — hiện có:**
- Bảng `users`, primary key UUID `as_uuid=False` → `Mapped[str]`
- Phải dùng `select(UserORM).where(UserORM.id == user_id)` để query by ID

**`RegisterUserUseCase` — hiện có, KHÔNG được sửa:**
- Dùng `loop.run_in_executor` để hash password async (giải pháp đã được review)
- Pattern này PHẢI được tái sử dụng cho `verify_password` trong `LoginUserUseCase`

### API Endpoint Spec

```
POST /api/auth/login
Content-Type: application/json

Request Body:
{
  "email": "user@example.com",
  "password": "securepassword123"
}

Response 200 OK:
Set-Cookie: access_token=<JWT>; HttpOnly; SameSite=Lax; Path=/; Max-Age=86400
Body: {
  "id": "uuid",
  "email": "user@example.com",
  "role": "admin",
  "isActive": true,
  "createdAt": "2026-01-01T00:00:00Z",
  "updatedAt": "2026-01-01T00:00:00Z"
}

Response 401 (sai credentials):
{
  "detail": "Email hoặc mật khẩu không đúng"
}

---
GET /api/auth/me
Cookie: access_token=<JWT>

Response 200 OK: (UserResponse — camelCase)
{
  "id": "uuid",
  "email": "user@example.com",
  "role": "admin",
  "isActive": true,
  "createdAt": "...",
  "updatedAt": "..."
}

Response 401 (không có cookie hoặc cookie hết hạn):
{
  "detail": "Chưa xác thực"
}

---
POST /api/auth/logout
Cookie: access_token=<JWT>

Response 200 OK:
Set-Cookie: access_token=; Max-Age=0; Path=/
Body: {"message": "Đã đăng xuất thành công"}
```

### JWT Utility — Chi tiết Triển khai

```python
# backend/src/shared/infra/jwt_utils.py
import jwt  # PyJWT >= 2.10.0
from datetime import UTC, datetime, timedelta
from backend.src.shared.infra.settings import get_settings

settings = get_settings()

def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.now(UTC) + timedelta(hours=settings.jwt_expire_hours)
    payload = {
        "sub": user_id,   # subject = user_id (string UUID)
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)

def decode_access_token(token: str) -> dict:
    """Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError nếu invalid."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
```

### LoginUserUseCase — Chi tiết Triển khai

```python
# Thêm vào backend/src/modules/identity/application/use_cases.py
import bcrypt

def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

class LoginUserUseCase:
    def __init__(self, user_repository: UserRepository) -> None:
        self._repo = user_repository

    async def execute(self, dto: LoginUserDTO) -> LoginResponseDTO:
        email = dto.email.lower()
        user = await self._repo.find_by_email(email)
        
        # QUAN TRỌNG: Không tiết lộ email nào sai (generic error)
        if not user or not user.is_active:
            raise InvalidCredentialsError("Email hoặc mật khẩu không đúng")
        
        loop = asyncio.get_running_loop()
        password_valid = await loop.run_in_executor(
            None, partial(_verify_password, dto.password, user.hashed_password)
        )
        
        if not password_valid:
            raise InvalidCredentialsError("Email hoặc mật khẩu không đúng")
        
        from backend.src.shared.infra.jwt_utils import create_access_token
        token = create_access_token(user.id, user.role)
        
        return LoginResponseDTO(
            id=user.id,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
            access_token=token,
        )
```

### get_current_user Dependency — Chi tiết

```python
# backend/src/modules/identity/infrastructure/auth_dependencies.py
import jwt
from fastapi import Depends, HTTPException, Request, status
from backend.src.shared.infra.jwt_utils import decode_access_token
from backend.src.modules.identity.domain.entities import User
from backend.src.modules.identity.domain.repositories import UserRepository
from backend.src.modules.identity.infrastructure.dependencies import get_user_repository

async def get_current_user(
    request: Request,
    repo: UserRepository = Depends(get_user_repository),
) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Chưa xác thực")
    
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Phiên đăng nhập đã hết hạn")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token không hợp lệ")
    
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token không hợp lệ")
    
    user = await repo.find_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Người dùng không tồn tại")
    
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị vô hiệu hóa")
    
    return user
```

### Router Endpoints — Chi tiết Set-Cookie

```python
# Trong backend/src/modules/identity/presentation/router.py — THÊM VÀO (không xóa register)
from fastapi import Response

@router.post("/auth/login", response_model=UserResponse)
async def login(
    request: LoginRequest,
    response: Response,  # FastAPI inject Response object để set cookie
    repo: UserRepository = Depends(get_user_repository),
) -> UserResponse:
    try:
        use_case = LoginUserUseCase(repo)
        result = await use_case.execute(LoginUserDTO(email=request.email, password=request.password))
        response.set_cookie(
            key="access_token",
            value=result.access_token,
            httponly=True,
            samesite="lax",
            max_age=settings.jwt_expire_hours * 3600,
            path="/",
        )
        return UserResponse.model_validate(result, from_attributes=True)
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user, from_attributes=True)

@router.post("/auth/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie(key="access_token", path="/")
    return {"message": "Đã đăng xuất thành công"}
```

**LƯU Ý:** Để import `settings` trong router, thêm:
```python
from backend.src.shared.infra.settings import get_settings
settings = get_settings()
```

### Error Handler — Thêm vào error_handlers.py

```python
# Thêm vào backend/src/shared/api/error_handlers.py
from backend.src.modules.identity.domain.exceptions import InvalidCredentialsError

# Trong hàm register_error_handlers(app):
@app.exception_handler(InvalidCredentialsError)
async def invalid_credentials_handler(request: Request, exc: InvalidCredentialsError):
    return JSONResponse(status_code=401, content={"detail": str(exc)})
```

### find_by_id trong PostgresUserRepository

```python
# Thêm vào class PostgresUserRepository
async def find_by_id(self, user_id: str) -> User | None:
    result = await self._session.execute(select(UserORM).where(UserORM.id == user_id))
    orm = result.scalar_one_or_none()
    return self._to_domain(orm) if orm else None
```

### Bảo mật Cookie — Môi trường Dev vs Production

- **Dev (SameSite=Lax, không Secure):** Hoạt động đúng khi Vite proxy `/api` về FastAPI — không bị CORS block
- **Production:** Thêm `secure=True` nếu chạy HTTPS. Hiện tại story 1.2 **KHÔNG CẦN** `secure=True` cho môi trường dev local
- Cookie `access_token` được đọc bởi `request.cookies.get("access_token")` — không cần Bearer header
- Tên cookie cố định: `access_token` (trùng với spec architecture mục 4)

### DTOs Mới Cần Thêm

```python
# Thêm vào backend/src/modules/identity/application/dtos.py
@dataclass
class LoginUserDTO:
    email: str
    password: str

@dataclass
class LoginResponseDTO:
    id: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    access_token: str  # JWT string — chỉ dùng nội bộ để set cookie, KHÔNG expose ra JSON
```

**LƯU Ý:** `LoginResponseDTO` có trường `access_token` nhưng `UserResponse` (Pydantic) KHÔNG có trường này. Cookie được set qua `response.set_cookie()` — không nằm trong response body.

### Chiến lược Test

**Pattern test từ story 1.1 (đã xác nhận hoạt động):**
- Unit tests: Dùng `MagicMock` / `AsyncMock` cho `UserRepository`
- Integration tests: Dùng `TestClient` với minimal `test_app` **không có lifespan** (tránh connect DB thật)
- `AsyncSession` mock: `AsyncMock(spec=AsyncSession)`
- Không dùng SQLite (intentional decision từ story 1.1)

**Unit test LoginUserUseCase:**
```python
# tests/unit/identity/test_login_use_case.py
import pytest
from unittest.mock import AsyncMock, patch
from backend.src.modules.identity.application.use_cases import LoginUserUseCase
from backend.src.modules.identity.application.dtos import LoginUserDTO
from backend.src.modules.identity.domain.entities import User
from backend.src.modules.identity.domain.exceptions import InvalidCredentialsError

@pytest.mark.asyncio
async def test_login_wrong_email():
    repo = AsyncMock()
    repo.find_by_email.return_value = None
    use_case = LoginUserUseCase(repo)
    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(LoginUserDTO(email="noone@x.com", password="password123"))
```

### Phòng tránh Timing Attack

Khi user không tồn tại, **KHÔNG được** trả về lỗi ngay lập tức mà không check password — điều này tạo timing side-channel. Tuy nhiên, với scale hiện tại (10 users), đây là acceptable trade-off. Implementation đơn giản (check user → nếu không có, raise luôn) là OK.

### Alembic Migration

**Story 1.2 KHÔNG cần tạo Alembic migration mới** — không thêm cột hay bảng mới vào DB. Bảng `users` từ story 1.1 đã đủ field.

### Dependency Tree

```
POST /api/auth/login
  → LoginRequest (Pydantic schema)
  → LoginUserUseCase
    → UserRepository.find_by_email (đã có)
    → bcrypt.checkpw via run_in_executor (reuse pattern từ story 1.1)
    → create_access_token (jwt_utils mới)
  → response.set_cookie (httponly=True, samesite='lax')
  → UserResponse (Pydantic schema đã có)

GET /api/auth/me
  → get_current_user dependency (mới)
    → request.cookies['access_token']
    → decode_access_token (jwt_utils mới)
    → UserRepository.find_by_id (mới)
  → UserResponse

POST /api/auth/logout
  → response.delete_cookie
  → {"message": "..."}
```

### Hexagonal Architecture — Dependency Flow

```
Presentation (router.py) → Application (LoginUserUseCase) → Domain (UserRepository interface)
Infrastructure (PostgresUserRepository, jwt_utils) → Domain
Presentation → Infrastructure qua Depends() — KHÔNG import trực tiếp
```

- `router.py` inject `LoginUserUseCase` qua constructor, không biết `PostgresUserRepository`
- `jwt_utils.py` ở `shared/infra/` — được dùng bởi cả `use_cases.py` (tạo token) và `auth_dependencies.py` (decode token)
- `auth_dependencies.py` ở `infrastructure/` là Adapter, chịu trách nhiệm đọc cookie và xác thực

### Settings Hiện Có (Sử dụng ngay, không thêm mới)

```python
# backend/src/shared/infra/settings.py — đã có đủ
secret_key: str = "change-me"        # JWT signing key
jwt_algorithm: str = "HS256"         # JWT algorithm
jwt_expire_hours: int = 24            # Thời hạn token
```

### References

- Architecture mục 4: JWT HttpOnly Cookie, SameSite=Lax, tên cookie `access_token`
- Architecture mục 9.3: Enforcement — dùng Pydantic alias_generator camelCase
- Story 1.1 Dev Notes: Pattern `run_in_executor` cho bcrypt (phải tái dùng cho `checkpw`)
- Story 1.1 Review: `router.py` inject qua `Depends`, không import trực tiếp Repository
- `UserResponse` schema đã có camelCase — tái dụng, không tạo mới

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6 (Dev Story — BMad Method v6.8.0)

### Debug Log References

- Không có debug đặc biệt — toàn bộ 37 tests pass lần đầu tiên

### Completion Notes List

- Implement `POST /api/auth/login`: bcrypt verify async qua `run_in_executor`, JWT tạo qua `jwt_utils`, set HttpOnly cookie SameSite=Lax
- Implement `GET /api/auth/me`: đọc cookie → decode JWT → `find_by_id` → trả UserResponse camelCase
- Implement `POST /api/auth/logout`: xóa cookie qua `response.delete_cookie`
- Tạo `jwt_utils.py` tại shared/infra: `create_access_token` và `decode_access_token`
- Tạo `auth_dependencies.py`: `get_current_user` FastAPI Dependency xử lý 3 loại lỗi (no cookie, expired, invalid)
- Mở rộng `UserRepository` abstract interface: thêm `find_by_id`
- 37 tests pass (14 mới + 23 cũ), 0 regressions
- JWT payload chứa `sub` (user_id) và `role` — test xác nhận payload hợp lệ
- Error message "Email hoặc mật khẩu không đúng" là generic — không tiết lộ email hay password nào sai
- `access_token` KHÔNG expose trong response body (chỉ qua Set-Cookie header)

### Change Log

- 2026-06-16: Implement Story 1.2 — Login API & JWT HttpOnly Cookie Session. Tạo mới 4 files, cập nhật 8 files.

### File List

**Tạo mới:**
- `backend/src/shared/infra/jwt_utils.py`
- `backend/src/modules/identity/infrastructure/auth_dependencies.py`
- `tests/unit/identity/test_login_use_case.py`
- `tests/unit/identity/test_login_api.py`
- `tests/unit/identity/test_auth_dependency.py` — thêm trong code review 2026-06-16

**Cập nhật:**
- `backend/src/modules/identity/domain/repositories.py` — thêm `find_by_id` abstract method
- `backend/src/modules/identity/domain/exceptions.py` — thêm `InvalidCredentialsError`
- `backend/src/modules/identity/application/dtos.py` — thêm `LoginUserDTO`, `LoginResponseDTO`
- `backend/src/modules/identity/application/use_cases.py` — thêm `LoginUserUseCase`, `_verify_password`
- `backend/src/modules/identity/infrastructure/postgres_repository.py` — implement `find_by_id`
- `backend/src/modules/identity/presentation/schemas.py` — thêm `LoginRequest`
- `backend/src/modules/identity/presentation/router.py` — thêm 3 endpoints (login, me, logout)
- `backend/src/shared/api/error_handlers.py` — thêm handler `InvalidCredentialsError`
- `tests/unit/identity/test_register_use_case.py` — thêm `find_by_id` vào InMemoryUserRepository (bắt buộc do thêm abstract method)
