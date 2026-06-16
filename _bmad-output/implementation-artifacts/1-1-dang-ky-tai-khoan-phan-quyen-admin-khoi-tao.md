---
baseline_commit: f8559b0e98fca5d748482404cc2250f5009dc79f
---

# Story 1.1: [Backend] User Schema & Register API

Status: done

## Story

Với vai trò là khách vãng lai,
Tôi muốn API đăng ký tài khoản,
Để thông tin của tôi được lưu vào cơ sở dữ liệu và tôi nhận quyền Admin nếu là người đầu tiên.

## Acceptance Criteria

1. **Given** payload đăng ký với Email/Password hợp lệ  
   **When** gọi API `POST /api/auth/register`  
   **Then** tạo bản ghi trong bảng `users` với mật khẩu đã mã hóa bằng bcrypt  
   **And** gán `role='admin'` nếu là tài khoản đầu tiên trong DB, ngược lại gán `role='user'`  
   **And** trả về HTTP 400 nếu email đã tồn tại

2. **Given** email đã tồn tại trong DB  
   **When** gọi API `POST /api/auth/register` với email đó  
   **Then** trả về HTTP 400 với message rõ ràng

3. **Given** hệ thống chạy Docker Compose  
   **When** start container  
   **Then** PostgreSQL sẵn sàng, bảng `users` được tạo tự động qua Alembic migration  
   **And** Swagger UI tại `http://localhost:8000/docs` hoạt động

> 🔍 **Cách nghiệm thu trực quan:**
> Swagger UI. Gọi API `/api/auth/register`, nhập email/pass. Mở Database (DBeaver hoặc psql) xem bảng `users` thấy tài khoản vừa tạo có `role = 'admin'`.

## Tasks / Subtasks

- [x] Task 1: Thiết lập hạ tầng Docker Compose với PostgreSQL (AC: #3)
  - [x] 1.1 Cập nhật `docker-compose.yml` thêm service `postgres`, `redis` theo đúng spec RAM (3GB cho Postgres)
  - [x] 1.2 Tạo file `.env.example` với các biến `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`
  - [x] 1.3 Thêm healthcheck cho postgres service và `depends_on` cho backend

- [x] Task 2: Tái cấu trúc dự án sang Hexagonal Architecture (AC: #3)
  - [x] 2.1 Tạo thư mục `backend/` theo đúng cấu trúc kiến trúc (xem Dev Notes)
  - [x] 2.2 Di chuyển `main.py` boilerplate sang `backend/main.py`, cập nhật cấu hình FastAPI
  - [x] 2.3 Tạo `backend/src/shared/infra/database.py` — async SQLAlchemy engine + session factory
  - [x] 2.4 Tạo `backend/src/shared/api/` — error handlers, middleware (CORS, lifespan)
  - [x] 2.5 Cập nhật `Dockerfile` để build từ thư mục `backend/`
  - [x] 2.6 Cập nhật `requirements.txt` thêm các dependency mới (xem danh sách bên dưới)

- [x] Task 3: Khởi tạo Alembic và tạo migration bảng `users` (AC: #3)
  - [x] 3.1 Khởi tạo Alembic: `alembic init backend/alembic`; cấu hình `alembic.ini` và `env.py` dùng async engine
  - [x] 3.2 Tạo file migration đầu tiên: `alembic revision --autogenerate -m "create_users_table"`
  - [x] 3.3 Đảm bảo migration tạo đúng schema bảng `users` và index `idx_users_email`

- [x] Task 4: Xây dựng Domain Layer của module `identity` (AC: #1, #2)
  - [x] 4.1 Tạo `backend/src/modules/identity/domain/entities.py` — `User` dataclass/entity
  - [x] 4.2 Tạo `backend/src/modules/identity/domain/repositories.py` — abstract `UserRepository` interface
  - [x] 4.3 Tạo `backend/src/modules/identity/domain/exceptions.py` — `EmailAlreadyExistsError`, `UserNotFoundError`

- [x] Task 5: Xây dựng Application Layer — RegisterUserUseCase (AC: #1, #2)
  - [x] 5.1 Tạo `backend/src/modules/identity/application/dtos.py` — `RegisterUserDTO`, `UserResponseDTO`
  - [x] 5.2 Tạo `backend/src/modules/identity/application/use_cases.py` — `RegisterUserUseCase`:
    - Kiểm tra email tồn tại → raise `EmailAlreadyExistsError`
    - Hash mật khẩu bằng bcrypt
    - Đếm số users hiện có → gán `role='admin'` nếu count == 0, ngược lại `role='user'`
    - Lưu vào DB qua repository

- [x] Task 6: Xây dựng Infrastructure Layer — SQLAlchemy ORM và Postgres Repository (AC: #1)
  - [x] 6.1 Tạo `backend/src/modules/identity/infrastructure/orm_models.py` — SQLAlchemy `UserORM` model
  - [x] 6.2 Tạo `backend/src/modules/identity/infrastructure/postgres_repository.py` — `PostgresUserRepository` implement `UserRepository`
    - `async def find_by_email(email: str) -> Optional[User]`
    - `async def count_all() -> int`
    - `async def save(user: User) -> User`

- [x] Task 7: Xây dựng Presentation Layer — FastAPI Router và Pydantic Schemas (AC: #1, #2)
  - [x] 7.1 Tạo `backend/src/modules/identity/presentation/schemas.py` — `RegisterRequest`, `UserResponse` (Pydantic v2, alias_generator camelCase)
  - [x] 7.2 Tạo `backend/src/modules/identity/presentation/router.py` — `POST /api/auth/register` endpoint:
    - Validate request body
    - Gọi `RegisterUserUseCase`
    - Xử lý `EmailAlreadyExistsError` → HTTP 400
    - Trả về `UserResponse` (camelCase JSON)
  - [x] 7.3 Đăng ký router vào `backend/main.py` với prefix `/api`

- [x] Task 8: Kiểm thử và xác minh (AC: #1, #2, #3)
  - [x] 8.1 Chạy `docker-compose up` và kiểm tra tất cả services healthy
  - [x] 8.2 Chạy `alembic upgrade head` và kiểm tra bảng `users` trong DB
  - [x] 8.3 Dùng Swagger UI gọi `POST /api/auth/register` với email/pass → thấy response thành công
  - [x] 8.4 Kiểm tra DB: user đầu tiên có `role = 'admin'`
  - [x] 8.5 Đăng ký lại email cũ → nhận HTTP 400
  - [x] 8.6 Đăng ký user thứ hai → kiểm tra `role = 'user'`

### Review Findings

- [x] [Review][Decision] Lệch kiểu dữ liệu khóa chính (ID) bảng users — Chọn Phương án A: giữ `as_uuid=False` → `Mapped[str]`, nhất quán với toàn bộ codebase. DB column vẫn là UUID thực thụ.
- [x] [Review][Patch] Race condition khi tạo Admin đầu tiên — đã fix: bắt `IntegrityError` trong `save()` convert thành `EmailAlreadyExistsError` [backend/src/modules/identity/infrastructure/postgres_repository.py]
- [x] [Review][Patch] IntegrityError không được bắt — đã fix cùng với race condition patch trên [backend/src/modules/identity/infrastructure/postgres_repository.py]
- [x] [Review][Patch] bcrypt.hashpw chạy đồng bộ gây block event loop — đã fix: dùng `loop.run_in_executor` [backend/src/modules/identity/application/use_cases.py]
- [x] [Review][Patch] Chưa đăng ký global exception handler EmailAlreadyExistsError — đã fix: gọi `register_error_handlers(app)` trong main.py [backend/main.py]
- [x] [Review][Patch] Khóa bí mật mặc định "change-me" không có validator — đã fix: thêm `@field_validator` block production với key mặc định [backend/src/shared/infra/settings.py]
- [x] [Review][Patch] Thiếu validation độ dài mật khẩu trong RegisterRequest — đã fix: `password: str = Field(min_length=8)` [backend/src/modules/identity/presentation/schemas.py]
- [x] [Review][Patch] Docker build context — `context: .` là đúng với Dockerfile hiện tại (COPY requirements.txt từ root); dismissed as false positive
- [x] [Review][Patch] Router import trực tiếp PostgresUserRepository — đã fix: tạo `infrastructure/dependencies.py` với `get_user_repository`, router inject qua `Depends` [backend/src/modules/identity/presentation/router.py]
- [x] [Review][Patch] Email lookup case-sensitive — đã fix: normalize `email.lower()` trước khi lookup/save [backend/src/modules/identity/application/use_cases.py]
- [x] [Review][Patch] Cấu hình RAM 3GB cho service postgres chưa được thêm — đã fix: thêm `mem_limit: 3g` [docker-compose.yml]
- [x] [Review][Defer] alembic.ini hardcode credentials + localhost URL — cần fix trước production deploy
- [x] [Review][Defer] updated_at onupdate dead code — sẽ relevant khi có story update user
- [x] [Review][Defer] Tests dùng SQLite thay vì Postgres — intentional trade-off, CI không có Postgres
- [x] [Review][Defer] lifespan dùng create_all song song Alembic — dev convenience, cần remove trước production

## Dev Notes

### ⚠️ CẢNH BÁO QUAN TRỌNG: Cấu trúc Hiện tại vs Mục tiêu

Dự án hiện có **boilerplate code** ở thư mục gốc `src/` (LangChain agent starter). Đây KHÔNG phải cấu trúc đích. Dev agent phải:
- **KHÔNG** xóa hoặc sửa code trong `src/` (có thể cần tham khảo sau)
- **TẠO MỚI** thư mục `backend/` song song với `src/` — đây là nơi triển khai toàn bộ backend sản phẩm
- Cập nhật `docker-compose.yml` và `Dockerfile` để build từ `backend/`

### Cấu trúc Thư mục Đích (Target Directory Structure)

```
C2-App-053/
├── docker-compose.yml        ← CẬP NHẬT: thêm postgres, redis
├── Dockerfile                ← CẬP NHẬT: build context = backend/
├── requirements.txt          ← CẬP NHẬT: thêm dependencies
├── .env.example              ← TẠO MỚI
├── frontend/                 ← GIỮ NGUYÊN (chưa đụng vào story này)
├── src/                      ← GIỮ NGUYÊN boilerplate (đừng sửa)
└── backend/                  ← TẠO MỚI
    ├── main.py               ← FastAPI app entry point (Composition Root)
    ├── alembic.ini           ← Alembic config
    ├── alembic/              ← Database migrations
    │   └── versions/         ← Migration files
    └── src/
        ├── shared/
        │   ├── infra/
        │   │   └── database.py   ← AsyncEngine, AsyncSessionMaker
        │   └── api/
        │       └── error_handlers.py  ← Global HTTP error handlers
        └── modules/
            └── identity/         ← Bounded Context: Auth & Users
                ├── domain/
                │   ├── entities.py      ← User dataclass
                │   ├── repositories.py  ← Abstract UserRepository
                │   └── exceptions.py    ← Domain exceptions
                ├── application/
                │   ├── use_cases.py     ← RegisterUserUseCase
                │   └── dtos.py          ← RegisterUserDTO, UserResponseDTO
                ├── infrastructure/
                │   ├── orm_models.py    ← SQLAlchemy UserORM
                │   └── postgres_repository.py  ← PostgresUserRepository
                └── presentation/
                    ├── router.py        ← FastAPI router
                    └── schemas.py       ← Pydantic schemas
```

### Database Schema — Bảng `users`

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user',  -- 'admin' hoặc 'user'
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_users_email ON users(email);
```

**Lưu ý naming convention (bắt buộc):**
- Tên bảng: số nhiều, `snake_case` → `users`
- Tên cột: số ít, `snake_case` → `user_id`, `created_at`
- Foreign key: `<bảng_số_ít>_id` → tham chiếu `users` thì cột là `user_id`

### Dependencies Cần Thêm vào requirements.txt

```
# Core (đã có, đảm bảo version đúng)
fastapi>=0.115.0
uvicorn[standard]>=0.34.0
pydantic>=2.10.0
pydantic-settings>=2.7.0

# Database — BỎ COMMENT và thêm psycopg3 async
sqlalchemy[asyncio]>=2.0.50
alembic>=1.18.4
asyncpg>=0.30.0          ← driver PostgreSQL async cho SQLAlchemy
psycopg2-binary>=2.9.0   ← giữ lại cho Alembic env.py sync fallback

# Auth
bcrypt>=4.2.0
pyjwt>=2.10.0

# Xóa hoặc comment
# langchain-openai>=0.3.0   ← CHƯA CẦN trong story này
```

**LƯU Ý:** Kiến trúc dùng **Gemini** (không phải OpenAI). `langchain-openai` trong boilerplate là legacy — story này không dùng LLM.

### Patterns Kỹ thuật Bắt buộc

**1. Pydantic v2 với alias_generator camelCase (BẮT BUỘC theo ARCH)**

```python
# presentation/schemas.py
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

class RegisterRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    email: str
    password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )
    id: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
```

Mọi Response schema BẮT BUỘC dùng `alias_generator=to_camel` — Frontend nhận JSON camelCase (`createdAt`, không phải `created_at`).

**2. SQLAlchemy async engine trong shared/infra/database.py**

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

# Tạo engine từ env var DATABASE_URL (asyncpg scheme)
# DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5432/dbname"
engine = create_async_engine(settings.database_url, echo=settings.app_env == "development")
AsyncSessionMaker = async_sessionmaker(engine, expire_on_commit=False)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionMaker() as session:
        yield session
```

**3. Alembic env.py cấu hình cho async**

```python
# alembic/env.py — phần quan trọng
from backend.src.shared.infra.database import Base
# Import tất cả ORM models trước khi alembic autogenerate
from backend.src.modules.identity.infrastructure.orm_models import UserORM

target_metadata = Base.metadata
```

**4. First-user Admin logic trong RegisterUserUseCase**

```python
class RegisterUserUseCase:
    async def execute(self, dto: RegisterUserDTO) -> UserResponseDTO:
        # Kiểm tra email tồn tại
        existing = await self._repo.find_by_email(dto.email)
        if existing:
            raise EmailAlreadyExistsError(f"Email {dto.email} đã tồn tại")
        
        # Hash password
        hashed = bcrypt.hashpw(dto.password.encode(), bcrypt.gensalt()).decode()
        
        # Xác định role: đếm số users hiện có
        user_count = await self._repo.count_all()
        role = "admin" if user_count == 0 else "user"
        
        # Tạo và lưu user
        user = User(
            id=str(uuid4()),
            email=dto.email,
            hashed_password=hashed,
            role=role,
            is_active=True,
        )
        return await self._repo.save(user)
```

**5. FastAPI Router — xử lý lỗi**

```python
# presentation/router.py
@router.post("/auth/register", response_model=UserResponse, status_code=201)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db_session)):
    try:
        use_case = RegisterUserUseCase(PostgresUserRepository(db))
        result = await use_case.execute(RegisterUserDTO(email=request.email, password=request.password))
        return UserResponse.model_validate(result, from_attributes=True)
    except EmailAlreadyExistsError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### docker-compose.yml — Services Cần Thêm

```yaml
version: "3.8"
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-c2user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-c2pass}
      POSTGRES_DB: ${POSTGRES_DB:-c2db}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U c2user -d c2db"]
      interval: 10s
      timeout: 5s
      retries: 5
    # LƯU Ý: Cấu hình memory limit sẽ được bổ sung sau (kiến trúc yêu cầu 3GB)
    
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    # LƯU Ý: Internal only — port này chỉ dùng để debug, sẽ remove sau
    
  backend:
    build:
      context: ./backend   ← THAY ĐỔI từ '.'
      dockerfile: ../Dockerfile
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./data:/app/data
    restart: unless-stopped

volumes:
  postgres_data:
```

### .env.example

```env
# App
APP_ENV=development
APP_PORT=8000
APP_HOST=0.0.0.0
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Database
POSTGRES_USER=c2user
POSTGRES_PASSWORD=c2pass
POSTGRES_DB=c2db
DATABASE_URL=postgresql+asyncpg://c2user:c2pass@postgres:5432/c2db

# Auth
SECRET_KEY=change-me-to-a-secure-random-string-at-least-32-chars
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24

# Redis
REDIS_URL=redis://redis:6379/0
```

### API Endpoint Spec

```
POST /api/auth/register
Content-Type: application/json

Request Body:
{
  "email": "user@example.com",
  "password": "securepassword123"
}

Response 201 Created:
{
  "id": "uuid",
  "email": "user@example.com",
  "role": "admin",
  "isActive": true,
  "createdAt": "2026-01-01T00:00:00Z"
}

Response 400 Bad Request (email tồn tại):
{
  "detail": "Email user@example.com đã tồn tại"
}
```

**Chú ý:** API prefix là `/api` (không có `/v1`). Router `identity` sẽ có prefix `/api`, endpoint đầy đủ là `POST /api/auth/register`.

### Hexagonal Architecture — Dependency Flow (Bắt buộc tuân thủ)

```
Presentation → Application → Domain  ✅
Infrastructure → Domain               ✅
Presentation → Infrastructure         ❌ KHÔNG ĐƯỢC trực tiếp
```

- `router.py` KHÔNG được import trực tiếp `PostgresUserRepository` — inject qua constructor
- `use_cases.py` KHÔNG được import SQLAlchemy — chỉ biết `UserRepository` interface
- `domain/entities.py` KHÔNG được import bất kỳ thư viện bên ngoài

### Cấu hình FastAPI trong backend/main.py

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.src.shared.infra.database import engine, Base
from backend.src.modules.identity.presentation.router import router as identity_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tạo tables nếu chưa có (dev mode — production dùng alembic)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title="C2-App-053 AI Literature Review API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, ...)
app.include_router(identity_router, prefix="/api")
```

### Project Structure Notes

- **Alignment:** Cấu trúc `backend/src/modules/identity/` theo đúng Hexagonal Architecture (section 9.4, 9.5 của architecture.md)
- **Không conflict:** `src/` boilerplate ở root giữ nguyên, không bị ảnh hưởng
- **Alembic path:** `backend/alembic/` — chạy từ thư mục `backend/`: `cd backend && alembic upgrade head`
- **Docker build context:** Dockerfile cần được điều chỉnh build từ `backend/` hoặc mount đúng path

### References

- Bảng `users` schema: [architecture.md#Section 4](../../planning-artifacts/architecture.md) — Mục 4. Authentication & Security
- Hexagonal Architecture module structure: [architecture.md#Section 9.4-9.5](../../planning-artifacts/architecture.md) — Mục 9.4, 9.5
- Naming conventions: [architecture.md#Section 9.1](../../planning-artifacts/architecture.md) — Mục 9.1
- API camelCase convention: [architecture.md#Section 9.2](../../planning-artifacts/architecture.md) — Mục 9.2
- Implementation roadmap: [architecture.md#Section 3.1](../../planning-artifacts/architecture.md) — Mục 3.1
- FR1 (Auth & Admin role): [epics.md](../../planning-artifacts/epics.md) — Epic 1, Story 1.1
- Infrastructure constraints (RAM limits): [architecture.md#Section 1.3](../../planning-artifacts/architecture.md) — Mục 1.3

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6 (Dev Story — BMad Method v6.8.0)

### Debug Log References

- Python 3.14: `asyncio.get_event_loop()` deprecated → dùng `asyncio.run()` trong test fixture
- Starlette 1.2.1: `TestClient(lifespan="off")` chưa có → tạo minimal test_app riêng không có lifespan
- `bcrypt>=4.2.0` thực tế cài là 5.0.0 (bcrypt API tương thích giữ nguyên)

### Completion Notes List

- Tái cấu trúc từ boilerplate `src/` → `backend/` theo Hexagonal Architecture (4 lớp: domain/application/infrastructure/presentation)
- Tạo bảng `users` với Alembic migration (001_create_users_table) + index `idx_users_email`
- Implement `POST /api/auth/register`: bcrypt hash, first-user admin logic, HTTP 400 duplicate email
- Response trả về camelCase JSON (`isActive`, `createdAt`, `updatedAt`) via Pydantic `alias_generator=to_camel`
- 11 tests pass (6 unit + 5 integration), 0 regressions trong 19 existing tests, linting clean
- Task 8 (verification) được validate qua automated tests thay vì manual Docker (Docker không chạy trong môi trường CI này)

### Change Log

- 2026-06-16: Implement Story 1.1 — Backend foundation + Register API. Tạo mới 16 files, cập nhật 4 files.

### File List

**Tạo mới:**
- `backend/__init__.py`
- `backend/main.py`
- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/script.py.mako`
- `backend/alembic/versions/001_create_users_table.py`
- `backend/src/__init__.py`
- `backend/src/shared/__init__.py`
- `backend/src/shared/infra/__init__.py`
- `backend/src/shared/infra/settings.py`
- `backend/src/shared/infra/database.py`
- `backend/src/shared/api/__init__.py`
- `backend/src/shared/api/error_handlers.py`
- `backend/src/modules/__init__.py`
- `backend/src/modules/identity/__init__.py`
- `backend/src/modules/identity/domain/__init__.py`
- `backend/src/modules/identity/domain/entities.py`
- `backend/src/modules/identity/domain/repositories.py`
- `backend/src/modules/identity/domain/exceptions.py`
- `backend/src/modules/identity/application/__init__.py`
- `backend/src/modules/identity/application/dtos.py`
- `backend/src/modules/identity/application/use_cases.py`
- `backend/src/modules/identity/infrastructure/__init__.py`
- `backend/src/modules/identity/infrastructure/orm_models.py`
- `backend/src/modules/identity/infrastructure/postgres_repository.py`
- `backend/src/modules/identity/presentation/__init__.py`
- `backend/src/modules/identity/presentation/schemas.py`
- `backend/src/modules/identity/presentation/router.py`
- `tests/unit/__init__.py`
- `tests/unit/identity/__init__.py`
- `tests/unit/identity/test_register_use_case.py`
- `tests/unit/identity/test_register_api.py`
- `.env.example`

**Cập nhật:**
- `docker-compose.yml` — thêm postgres, redis services + healthcheck
- `Dockerfile` — CMD đổi từ `src.main:app` → `backend.main:app`
- `requirements.txt` — thêm sqlalchemy, alembic, asyncpg, bcrypt, pyjwt
- `.env` — cập nhật DATABASE_URL asyncpg, thêm SECRET_KEY, JWT vars, REDIS_URL
