---
baseline_commit: be5b938
---

# Story 2.1: [BE+FE] Quản lý API Keys Cá nhân — Mã hóa & Bảo mật

Status: done

## Story

Với vai trò là người dùng đã đăng nhập,
Tôi muốn lưu trữ và quản lý API Key Gemini cá nhân của mình trong tài khoản,
Để hệ thống sử dụng key riêng của tôi cho các tác vụ AI, tách biệt rate limit với người dùng khác.

## Acceptance Criteria

1. **Given** đang ở trang bất kỳ sau khi đăng nhập
   **When** nhìn lên Header
   **Then** thấy nút 🔑 "API Keys" hiển thị cho TẤT CẢ người dùng (không chỉ admin)

2. **Given** click nút 🔑 "API Keys"
   **When** trang `/settings/api-keys` tải
   **Then** hiển thị danh sách provider: **Gemini** với trường API Key được masked dạng `••••••••3a5F` (4 ký tự cuối), trạng thái `Not configured` nếu chưa lưu key

3. **Given** API Key chưa được cấu hình hoặc đang hiển thị masked
   **When** click biểu tượng ✏️ (edit) bên cạnh field
   **Then** field chuyển sang `<input type="password">` có thể nhập key mới; hiện nút "Lưu" và "Huỷ"

4. **Given** đã nhập API Key hợp lệ vào input
   **When** click "Lưu"
   **Then** gọi `PUT /api/user/api-keys/gemini` body `{"apiKey": "..."}`
   **And** Backend mã hóa key bằng AES/Fernet lưu vào bảng `user_credentials`
   **And** UI trở về trạng thái masked hiển thị 4 ký tự cuối của key vừa nhập
   **And** Toast thành công "API Key đã được lưu"

5. **Given** API Key đã được lưu
   **When** click nút "Test Connection"
   **Then** nút hiển thị spinner xoay và nhãn `Testing...` trong khi request chạy
   **And** gọi `POST /api/user/api-keys/gemini/test`
   **And** Backend giải mã key và thực hiện 1 call nhỏ đến Gemini API để kiểm tra tính hợp lệ

6. **Given** test kết nối thành công
   **When** nhận kết quả từ API
   **Then** nút đổi về "Test Connection"; hiển thị badge xanh lá 🟢 **Connected** kèm "Last tested: vừa xong"

7. **Given** test kết nối thất bại (key sai / hết hạn / mạng lỗi)
   **When** nhận kết quả từ API
   **Then** hiển thị badge đỏ 🔴 **Failed** kèm thông báo lỗi ngắn
   **And** Toast lỗi màu đỏ với nội dung lỗi

8. **Given** người dùng đã lưu API Key
   **When** hệ thống cần khởi tạo LLM client ở bất kỳ module nào (ingestion, orchestrator)
   **Then** `LLMRouter.get_llm_client(user_id, model_name)` trả về `ChatGoogleGenerativeAI` dùng key đã giải mã của user
   **And** nếu user CHƯA cấu hình key → fallback về `settings.gemini_api_key` (system key)

9. **Given** đang ở trang `/settings/api-keys`
   **When** click VI|EN trên Header
   **Then** tất cả nhãn tĩnh (tiêu đề, nút, placeholder) đổi ngôn ngữ ngay lập tức

> 🔍 **Cách nghiệm thu trực quan:**
> Swagger UI: gọi `PUT /api/user/api-keys/gemini` với body `{"apiKey":"sk-test-123"}`, sau đó `GET /api/user/api-keys` thấy key trả về masked. Gọi `POST /api/user/api-keys/gemini/test` thấy `{"status":"connected"}` hoặc `{"status":"failed", "error":"..."}`.
> Web UI: Click 🔑 trong header → trang API Keys → click ✏️ → nhập key → Lưu → thấy masked. Click "Test Connection" → spinner → badge Connected/Failed.

---

## Tasks / Subtasks

### BACKEND — Identity Module Extension + Shared LLMRouter

- [x] Task 1: Cập nhật Settings — thêm Gemini & Fernet config (AC: #8)
  - [x] 1.1 Thêm `gemini_api_key: str = ""` và `fernet_secret_key: str = ""` vào `Settings` class trong `backend/src/shared/infra/settings.py`
  - [x] 1.2 Bổ sung validator cho `fernet_secret_key`: cảnh báo log nếu rỗng trong development (KHÔNG raise ValueError — để test không bị chặn)

- [x] Task 2: Alembic migration — bảng `user_credentials` (AC: #4)
  - [x] 2.1 Tạo `backend/alembic/versions/003_create_user_credentials_table.py` theo pattern của `002_...` (xem Dev Notes § Migration Template)
  - [x] 2.2 Tạo bảng `user_credentials` với các cột: `id UUID PK`, `user_id UUID FK→users`, `provider VARCHAR(50)`, `encrypted_api_key TEXT`, `last_tested_at TIMESTAMPTZ`, `is_valid BOOLEAN`, `created_at TIMESTAMPTZ`, `updated_at TIMESTAMPTZ`; UNIQUE(`user_id`, `provider`); index `idx_user_credentials_user_id`

- [x] Task 3: Identity module — Domain layer (AC: #4, #8)
  - [x] 3.1 Thêm dataclass `UserCredential` vào `backend/src/modules/identity/domain/entities.py` (xem Dev Notes § Domain Entity)
  - [x] 3.2 Thêm `UserCredentialRepository` abstract class vào `backend/src/modules/identity/domain/repositories.py` (xem Dev Notes § Repository Interface)
  - [x] 3.3 Thêm `CredentialNotFoundError` vào `backend/src/modules/identity/domain/exceptions.py`

- [x] Task 4: Identity module — Application layer (AC: #4, #5, #6, #7, #8)
  - [x] 4.1 Thêm DTOs: `SaveApiKeyDTO`, `TestApiKeyDTO` vào `backend/src/modules/identity/application/dtos.py`
  - [x] 4.2 Thêm use cases: `SaveApiKeyUseCase`, `ListApiKeysUseCase`, `TestApiKeyUseCase`, `DeleteApiKeyUseCase` vào `backend/src/modules/identity/application/use_cases.py` (xem Dev Notes § Use Cases)

- [x] Task 5: Identity module — Infrastructure layer (AC: #4)
  - [x] 5.1 Thêm `UserCredentialORM` vào `backend/src/modules/identity/infrastructure/orm_models.py` (xem Dev Notes § ORM Model)
  - [x] 5.2 Tạo `backend/src/modules/identity/infrastructure/credential_repository.py` implement `UserCredentialRepository` (xem Dev Notes § Repository Implementation)
  - [x] 5.3 Thêm `get_credential_repository` dependency function vào `backend/src/modules/identity/infrastructure/dependencies.py`
  - [x] 5.4 Tạo `backend/src/modules/identity/infrastructure/encryption.py` với class `FernetEncryptor` (xem Dev Notes § Encryption)

- [x] Task 6: Identity module — Presentation layer (AC: #2, #3, #4, #5, #6, #7)
  - [x] 6.1 Thêm schemas vào `backend/src/modules/identity/presentation/schemas.py`: `SaveApiKeyRequest`, `ApiKeyResponse`, `ApiKeyTestResponse`
  - [x] 6.2 Thêm 4 routes vào `backend/src/modules/identity/presentation/router.py`: `GET /user/api-keys`, `PUT /user/api-keys/{provider}`, `DELETE /user/api-keys/{provider}`, `POST /user/api-keys/{provider}/test` (xem Dev Notes § API Endpoints)
  - [x] 6.3 Import `UserCredentialORM` vào `backend/main.py` để Base.metadata nhận biết bảng mới (xem Dev Notes § main.py Import)

- [x] Task 7: Shared — LLMRouter (AC: #8)
  - [x] 7.1 Tạo `backend/src/shared/infra/llm/__init__.py` (trống)
  - [x] 7.2 Tạo `backend/src/shared/infra/llm/router.py` với class `LLMRouter` (xem Dev Notes § LLMRouter)

### FRONTEND — API Keys Management Panel

- [x] Task 8: Types & API client (AC: #2, #4, #5, #6, #7)
  - [x] 8.1 Tạo `frontend/src/types/userCredential.ts` với interface `ApiKeyStatus` (xem Dev Notes § Frontend Types)
  - [x] 8.2 Tạo `frontend/src/api/userCredentials.ts` với 4 functions: `getApiKeys()`, `saveApiKey()`, `deleteApiKey()`, `testApiKey()` (xem Dev Notes § Frontend API Client)

- [x] Task 9: ApiKeysPage component (AC: #2–#9)
  - [x] 9.1 Tạo `frontend/src/features/settings/ApiKeysPage.tsx` (xem Dev Notes § ApiKeysPage Component)
  - [x] 9.2 Tạo `frontend/src/features/settings/ApiKeysPage.module.css` với styles theo AcademicPaper design system
  - [x] 9.3 Đảm bảo field edit dùng `<input type="password">` để browser không log key

- [x] Task 10: Cập nhật routing & Header (AC: #1, #9)
  - [x] 10.1 Thêm route `/settings/api-keys` vào `frontend/src/App.tsx` (bọc trong `ProtectedRoute`)
  - [x] 10.2 Thêm nút 🔑 vào `frontend/src/components/Header.tsx` điều hướng `/settings/api-keys` — hiển thị cho TẤT CẢ users (không check `role === 'admin'`)
  - [x] 10.3 Thêm `header.apiKeys` translation key vào `frontend/src/i18n/translations.ts` (style giống `iconButton`)

- [x] Task 11: i18n — Translation keys (AC: #9)
  - [x] 11.1 Thêm các translation keys vào `frontend/src/i18n/translations.ts` (xem Dev Notes § Translation Keys)

- [x] Task 12: Tests (AC: #2, #4, #5, #6, #7)
  - [x] 12.1 Tạo `frontend/src/features/settings/__tests__/ApiKeysPage.test.tsx` với test cases (xem Dev Notes § Test Cases)

---

## Dev Notes

### ⚠️ LỖI THƯỜNG GẶP CỦA LLM — PHẢI TRÁNH

1. **KHÔNG dùng Tailwind** — dự án dùng CSS Modules + CSS Variables `AcademicPaper`. Dùng `styles.className` từ `.module.css`.

2. **KHÔNG import emoji từ thư viện** — dùng Unicode trực tiếp: `🔑`, `✏️`, `🟢`, `🔴`.

3. **KHÔNG dùng `i18next` hay thư viện i18n nào** — dùng hook `useTranslation()` từ `frontend/src/i18n/useTranslation.ts`.

4. **KHÔNG quên tham số thứ 2 của `getErrorMessage(err, 'fallback')`** — thiếu sẽ lỗi `TS2554`.

5. **KHÔNG commit `FERNET_SECRET_KEY` hay `GEMINI_API_KEY` vào code** — chỉ đọc từ `.env` qua `Settings`.

6. **KHÔNG gọi `Fernet(key)` với key là string thường** — Fernet key phải là URL-safe base64 32 bytes. Sinh bằng `Fernet.generate_key()`. Lưu vào `.env` dưới dạng base64 string.

7. **KHÔNG bỏ qua việc import `UserCredentialORM` vào `main.py`** — SQLAlchemy chỉ biết model nếu được import trước khi `Base.metadata.create_all`. Pattern: `from backend.src.modules.identity.infrastructure.orm_models import UserORM, UserCredentialORM  # noqa: F401`.

8. **KHÔNG gọi API Gemini trong test** — `TestApiKeyUseCase` phải có thể nhận mock LLM client; đừng hardcode `ChatGoogleGenerativeAI` trong use case.

9. **KHÔNG để `fernet_secret_key` rỗng trong production** — nhưng KHÔNG raise error trong dev (sẽ chặn unit tests). Chỉ log warning.

10. **KHÔNG thêm `onClick` cho nút gear ⚙️ hiện tại** — đó là admin settings button khác. Tạo nút 🔑 riêng cho API Keys của user.

---

### § Migration Template — `003_create_user_credentials_table.py`

```python
"""create_user_credentials_table

Revision ID: 003
Revises: 002
Create Date: 2026-06-16

"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: str | Sequence[str] | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_credentials",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("encrypted_api_key", sa.Text(), nullable=False),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_valid", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "provider", name="uq_user_credentials_user_provider"),
    )
    op.create_index("idx_user_credentials_user_id", "user_credentials", ["user_id"])


def downgrade() -> None:
    op.drop_index("idx_user_credentials_user_id", table_name="user_credentials")
    op.drop_table("user_credentials")
```

---

### § Domain Entity — `UserCredential`

Thêm vào `backend/src/modules/identity/domain/entities.py`:

```python
@dataclass
class UserCredential:
    id: str
    user_id: str
    provider: str           # 'gemini'
    encrypted_api_key: str  # AES/Fernet encrypted, KHÔNG bao giờ trả về plain text ra ngoài
    last_tested_at: datetime | None
    is_valid: bool | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(cls, user_id: str, provider: str, encrypted_api_key: str) -> "UserCredential":
        now = datetime.now(timezone.utc)
        return cls(
            id=str(uuid.uuid4()),
            user_id=user_id,
            provider=provider,
            encrypted_api_key=encrypted_api_key,
            last_tested_at=None,
            is_valid=None,
            created_at=now,
            updated_at=now,
        )
```

---

### § Repository Interface

Thêm vào `backend/src/modules/identity/domain/repositories.py`:

```python
class UserCredentialRepository(ABC):
    @abstractmethod
    async def find_by_user_and_provider(self, user_id: str, provider: str) -> UserCredential | None: ...

    @abstractmethod
    async def list_by_user(self, user_id: str) -> list[UserCredential]: ...

    @abstractmethod
    async def upsert(self, credential: UserCredential) -> UserCredential: ...

    @abstractmethod
    async def update_test_result(self, credential_id: str, is_valid: bool) -> None: ...

    @abstractmethod
    async def delete(self, credential_id: str) -> None: ...
```

---

### § Encryption — `FernetEncryptor`

Tạo `backend/src/modules/identity/infrastructure/encryption.py`:

```python
from cryptography.fernet import Fernet, InvalidToken
from backend.src.shared.infra.settings import get_settings


class FernetEncryptor:
    def __init__(self) -> None:
        settings = get_settings()
        key = settings.fernet_secret_key
        if not key:
            # Dev/test fallback: sinh key ephemeral — KHÔNG an toàn cho production
            import logging
            logging.getLogger(__name__).warning(
                "FERNET_SECRET_KEY chưa được cấu hình. Dùng ephemeral key cho dev/test."
            )
            key = Fernet.generate_key().decode()
        self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode()).decode()

    @staticmethod
    def mask(plaintext: str) -> str:
        """Hiển thị 4 ký tự cuối, che phần còn lại bằng ••"""
        if len(plaintext) <= 4:
            return "••••"
        return "••••••••" + plaintext[-4:]
```

---

### § ORM Model — `UserCredentialORM`

Thêm vào `backend/src/modules/identity/infrastructure/orm_models.py`:

```python
class UserCredentialORM(Base):
    __tablename__ = "user_credentials"

    id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()),
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    encrypted_api_key: Mapped[str] = mapped_column(Text, nullable=False)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_user_credentials_user_provider"),
    )
```

Import cần thêm: `from sqlalchemy import UniqueConstraint`

---

### § Repository Implementation — `credential_repository.py`

```python
# backend/src/modules/identity/infrastructure/credential_repository.py
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from backend.src.modules.identity.domain.entities import UserCredential
from backend.src.modules.identity.domain.repositories import UserCredentialRepository
from backend.src.modules.identity.infrastructure.orm_models import UserCredentialORM


def _orm_to_entity(orm: UserCredentialORM) -> UserCredential:
    return UserCredential(
        id=orm.id, user_id=orm.user_id, provider=orm.provider,
        encrypted_api_key=orm.encrypted_api_key,
        last_tested_at=orm.last_tested_at, is_valid=orm.is_valid,
        created_at=orm.created_at, updated_at=orm.updated_at,
    )


class PostgresUserCredentialRepository(UserCredentialRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def find_by_user_and_provider(self, user_id: str, provider: str) -> UserCredential | None:
        result = await self._db.execute(
            select(UserCredentialORM).where(
                UserCredentialORM.user_id == user_id,
                UserCredentialORM.provider == provider,
            )
        )
        orm = result.scalar_one_or_none()
        return _orm_to_entity(orm) if orm else None

    async def list_by_user(self, user_id: str) -> list[UserCredential]:
        result = await self._db.execute(
            select(UserCredentialORM).where(UserCredentialORM.user_id == user_id)
            .order_by(UserCredentialORM.provider)
        )
        return [_orm_to_entity(r) for r in result.scalars().all()]

    async def upsert(self, credential: UserCredential) -> UserCredential:
        # Dùng PostgreSQL ON CONFLICT DO UPDATE để upsert
        stmt = (
            pg_insert(UserCredentialORM)
            .values(
                id=credential.id,
                user_id=credential.user_id,
                provider=credential.provider,
                encrypted_api_key=credential.encrypted_api_key,
                last_tested_at=credential.last_tested_at,
                is_valid=credential.is_valid,
                created_at=credential.created_at,
                updated_at=credential.updated_at,
            )
            .on_conflict_do_update(
                constraint="uq_user_credentials_user_provider",
                set_={
                    "encrypted_api_key": credential.encrypted_api_key,
                    "updated_at": datetime.now(timezone.utc),
                    "is_valid": None,         # reset validity khi đổi key
                    "last_tested_at": None,
                },
            )
            .returning(UserCredentialORM)
        )
        result = await self._db.execute(stmt)
        await self._db.commit()
        orm = result.scalar_one()
        return _orm_to_entity(orm)

    async def update_test_result(self, credential_id: str, is_valid: bool) -> None:
        result = await self._db.execute(
            select(UserCredentialORM).where(UserCredentialORM.id == credential_id)
        )
        orm = result.scalar_one_or_none()
        if orm:
            orm.is_valid = is_valid
            orm.last_tested_at = datetime.now(timezone.utc)
            orm.updated_at = datetime.now(timezone.utc)
            await self._db.commit()

    async def delete(self, credential_id: str) -> None:
        result = await self._db.execute(
            select(UserCredentialORM).where(UserCredentialORM.id == credential_id)
        )
        orm = result.scalar_one_or_none()
        if orm:
            await self._db.delete(orm)
            await self._db.commit()
```

**Lưu ý quan trọng**: `pg_insert` dùng PostgreSQL-specific `INSERT ... ON CONFLICT`. Trong test dùng SQLite in-memory sẽ fail. Giải pháp cho test: mock repository (không test hàm upsert trực tiếp với SQLite), hoặc dùng `find + save/update` thay thế khi cần chạy test.

---

### § Use Cases

Thêm vào `backend/src/modules/identity/application/use_cases.py`:

```python
class SaveApiKeyUseCase:
    def __init__(self, repo: UserCredentialRepository, encryptor: FernetEncryptor) -> None:
        self._repo = repo
        self._encryptor = encryptor

    async def execute(self, user_id: str, provider: str, plain_api_key: str) -> UserCredential:
        encrypted = self._encryptor.encrypt(plain_api_key)
        existing = await self._repo.find_by_user_and_provider(user_id, provider)
        if existing:
            credential = UserCredential(
                id=existing.id, user_id=user_id, provider=provider,
                encrypted_api_key=encrypted,
                last_tested_at=None, is_valid=None,
                created_at=existing.created_at,
                updated_at=datetime.now(timezone.utc),
            )
        else:
            credential = UserCredential.create(user_id, provider, encrypted)
        return await self._repo.upsert(credential)


class ListApiKeysUseCase:
    def __init__(self, repo: UserCredentialRepository, encryptor: FernetEncryptor) -> None:
        self._repo = repo
        self._encryptor = encryptor

    async def execute(self, user_id: str) -> list[dict]:
        credentials = await self._repo.list_by_user(user_id)
        # KHÔNG trả về decrypted key — chỉ trả masked + metadata
        result = []
        for c in credentials:
            try:
                plain = self._encryptor.decrypt(c.encrypted_api_key)
                masked = FernetEncryptor.mask(plain)
            except Exception:
                masked = "••••••••[lỗi giải mã]"
            result.append({
                "provider": c.provider,
                "maskedKey": masked,
                "isValid": c.is_valid,
                "lastTestedAt": c.last_tested_at,
            })
        # Luôn trả về entry cho Gemini dù user chưa lưu
        providers_with_key = {r["provider"] for r in result}
        if "gemini" not in providers_with_key:
            result.append({"provider": "gemini", "maskedKey": None, "isValid": None, "lastTestedAt": None})
        return result


class TestApiKeyUseCase:
    def __init__(self, repo: UserCredentialRepository, encryptor: FernetEncryptor) -> None:
        self._repo = repo
        self._encryptor = encryptor

    async def execute(self, user_id: str, provider: str) -> dict:
        credential = await self._repo.find_by_user_and_provider(user_id, provider)
        if not credential:
            raise CredentialNotFoundError(f"Chưa cấu hình key cho provider: {provider}")

        plain_key = self._encryptor.decrypt(credential.encrypted_api_key)

        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=plain_key)
            # Gọi nhỏ nhất có thể để validate key
            response = await llm.ainvoke("Hello")
            _ = response.content  # chỉ verify không raise exception
            await self._repo.update_test_result(credential.id, is_valid=True)
            return {"status": "connected"}
        except Exception as e:
            await self._repo.update_test_result(credential.id, is_valid=False)
            return {"status": "failed", "error": str(e)[:200]}
```

---

### § API Endpoints — `router.py`

Thêm vào `backend/src/modules/identity/presentation/router.py`:

```python
# GET /api/user/api-keys — list tất cả keys (masked) của user hiện tại
@router.get("/user/api-keys")
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    repo: UserCredentialRepository = Depends(get_credential_repository),
) -> list[dict]:
    encryptor = FernetEncryptor()
    use_case = ListApiKeysUseCase(repo, encryptor)
    return await use_case.execute(current_user.id)


# PUT /api/user/api-keys/{provider} — lưu/cập nhật key cho provider
@router.put("/user/api-keys/{provider}", status_code=200)
async def save_api_key(
    provider: str,
    request: SaveApiKeyRequest,
    current_user: User = Depends(get_current_user),
    repo: UserCredentialRepository = Depends(get_credential_repository),
) -> dict:
    if provider not in {"gemini"}:
        raise HTTPException(status_code=400, detail=f"Provider không hợp lệ: {provider}")
    encryptor = FernetEncryptor()
    use_case = SaveApiKeyUseCase(repo, encryptor)
    await use_case.execute(current_user.id, provider, request.api_key)
    return {"message": "API Key đã được lưu thành công"}


# DELETE /api/user/api-keys/{provider}
@router.delete("/user/api-keys/{provider}", status_code=204)
async def delete_api_key(
    provider: str,
    current_user: User = Depends(get_current_user),
    repo: UserCredentialRepository = Depends(get_credential_repository),
) -> None:
    credential = await repo.find_by_user_and_provider(current_user.id, provider)
    if credential:
        await repo.delete(credential.id)


# POST /api/user/api-keys/{provider}/test — test connection
@router.post("/user/api-keys/{provider}/test")
async def test_api_key(
    provider: str,
    current_user: User = Depends(get_current_user),
    repo: UserCredentialRepository = Depends(get_credential_repository),
) -> dict:
    encryptor = FernetEncryptor()
    use_case = TestApiKeyUseCase(repo, encryptor)
    try:
        return await use_case.execute(current_user.id, provider)
    except CredentialNotFoundError:
        raise HTTPException(status_code=404, detail=f"Chưa cấu hình API Key cho {provider}")
```

**Schemas cần thêm vào `schemas.py`:**
```python
class SaveApiKeyRequest(BaseModel):
    api_key: str = Field(alias="apiKey", min_length=1)
    model_config = ConfigDict(populate_by_name=True)
```

---

### § main.py Import

Thêm dòng này vào `backend/main.py` (bên dưới dòng import `ProjectORM`):

```python
from backend.src.modules.identity.infrastructure.orm_models import UserORM, UserCredentialORM  # noqa: F401
```

Đồng thời import credential router nếu tách riêng, hoặc routes mới đã nằm trong `identity_router` thì không cần thêm.

---

### § LLMRouter — `src/shared/infra/llm/router.py`

```python
# backend/src/shared/infra/llm/router.py
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.shared.infra.settings import get_settings

logger = logging.getLogger(__name__)


class LLMRouter:
    """
    Định tuyến LLM client với API Key:
    1. Ưu tiên dùng API Key riêng của user (giải mã từ DB)
    2. Fallback về System API Key trong settings nếu user chưa cấu hình
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_llm_client(self, user_id: str, model_name: str = "gemini-2.5-flash"):
        """Trả về ChatGoogleGenerativeAI được cấu hình với API Key phù hợp."""
        from langchain_google_genai import ChatGoogleGenerativeAI
        from backend.src.modules.identity.infrastructure.credential_repository import PostgresUserCredentialRepository
        from backend.src.modules.identity.infrastructure.encryption import FernetEncryptor

        api_key = await self._resolve_api_key(user_id)
        return ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key)

    async def _resolve_api_key(self, user_id: str) -> str:
        from backend.src.modules.identity.infrastructure.credential_repository import PostgresUserCredentialRepository
        from backend.src.modules.identity.infrastructure.encryption import FernetEncryptor

        repo = PostgresUserCredentialRepository(self._db)
        credential = await repo.find_by_user_and_provider(user_id, "gemini")

        if credential:
            try:
                encryptor = FernetEncryptor()
                return encryptor.decrypt(credential.encrypted_api_key)
            except Exception:
                logger.warning("Không thể giải mã API Key của user %s, fallback system key", user_id)

        settings = get_settings()
        if not settings.gemini_api_key:
            raise RuntimeError(
                "Không có API Key Gemini: user chưa cấu hình và GEMINI_API_KEY system chưa được thiết lập"
            )
        return settings.gemini_api_key
```

**Cách dùng trong các module khác (ví dụ ingestion):**
```python
from backend.src.shared.infra.llm.router import LLMRouter

llm_router = LLMRouter(db_session)
llm = await llm_router.get_llm_client(user_id=current_user.id, model_name="gemini-2.5-flash")
response = await llm.ainvoke(prompt)
```

---

### § Frontend Types — `userCredential.ts`

```typescript
// frontend/src/types/userCredential.ts
export interface ApiKeyStatus {
  provider: 'gemini';
  maskedKey: string | null;   // null = chưa cấu hình
  isValid: boolean | null;    // null = chưa test
  lastTestedAt: string | null;
}

export interface SaveApiKeyPayload {
  apiKey: string;
}

export interface TestApiKeyResult {
  status: 'connected' | 'failed';
  error?: string;
}
```

---

### § Frontend API Client — `userCredentials.ts`

```typescript
// frontend/src/api/userCredentials.ts
import { apiClient } from './client';
import type { ApiKeyStatus, SaveApiKeyPayload, TestApiKeyResult } from '@/types/userCredential';

export async function getApiKeys(): Promise<ApiKeyStatus[]> {
  const res = await apiClient.get<ApiKeyStatus[]>('/user/api-keys');
  return res.data;
}

export async function saveApiKey(provider: string, payload: SaveApiKeyPayload): Promise<void> {
  await apiClient.put(`/user/api-keys/${provider}`, payload);
}

export async function deleteApiKey(provider: string): Promise<void> {
  await apiClient.delete(`/user/api-keys/${provider}`);
}

export async function testApiKey(provider: string): Promise<TestApiKeyResult> {
  const res = await apiClient.post<TestApiKeyResult>(`/user/api-keys/${provider}/test`);
  return res.data;
}
```

**Lưu ý**: `apiClient` đã được cấu hình với `withCredentials: true` và base URL `/api` trong `frontend/src/api/client.ts`. Không tạo lại.

---

### § ApiKeysPage Component

```tsx
// frontend/src/features/settings/ApiKeysPage.tsx
import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { getApiKeys, saveApiKey, testApiKey } from '@/api/userCredentials';
import { getErrorMessage } from '@/api/errors';
import { useTranslation } from '@/i18n/useTranslation';
import type { ApiKeyStatus } from '@/types/userCredential';
import styles from './ApiKeysPage.module.css';

const PROVIDERS = [{ key: 'gemini', label: 'Gemini (Google AI)' }] as const;

export function ApiKeysPage() {
  const { t } = useTranslation();
  const [apiKeys, setApiKeys] = useState<ApiKeyStatus[]>([]);
  const [editingProvider, setEditingProvider] = useState<string | null>(null);
  const [inputValue, setInputValue] = useState('');
  const [isTesting, setIsTesting] = useState<Record<string, boolean>>({});
  const [isLoading, setIsLoading] = useState(true);

  const loadApiKeys = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await getApiKeys();
      setApiKeys(data);
    } catch (err) {
      toast.error(getErrorMessage(err, t('apiKeys.loadError')));
    } finally {
      setIsLoading(false);
    }
  }, [t]);

  useEffect(() => {
    loadApiKeys();
  }, [loadApiKeys]);

  async function handleSave(provider: string) {
    if (!inputValue.trim()) return;
    try {
      await saveApiKey(provider, { apiKey: inputValue.trim() });
      toast.success(t('apiKeys.saveSuccess'));
      setEditingProvider(null);
      setInputValue('');
      await loadApiKeys();
    } catch (err) {
      toast.error(getErrorMessage(err, t('apiKeys.saveError')));
    }
  }

  async function handleTest(provider: string) {
    setIsTesting((prev) => ({ ...prev, [provider]: true }));
    try {
      const result = await testApiKey(provider);
      if (result.status === 'connected') {
        toast.success(t('apiKeys.testSuccess'));
      } else {
        toast.error(`${t('apiKeys.testFailed')}: ${result.error ?? ''}`);
      }
      await loadApiKeys();
    } catch (err) {
      toast.error(getErrorMessage(err, t('apiKeys.testError')));
    } finally {
      setIsTesting((prev) => ({ ...prev, [provider]: false }));
    }
  }

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>{t('apiKeys.title')}</h1>
      <p className={styles.subtitle}>{t('apiKeys.subtitle')}</p>

      {isLoading ? (
        <div className={styles.loading}>{t('apiKeys.loading')}</div>
      ) : (
        <div className={styles.providerList}>
          {PROVIDERS.map(({ key: provider, label }) => {
            const status = apiKeys.find((k) => k.provider === provider);
            const isEditing = editingProvider === provider;
            const testing = isTesting[provider] ?? false;

            return (
              <div key={provider} className={styles.providerCard}>
                <div className={styles.cardHeader}>
                  <span className={styles.providerName}>{label}</span>
                  <span className={styles.statusBadge} data-valid={status?.isValid}>
                    {status?.isValid === true
                      ? '🟢 Connected'
                      : status?.isValid === false
                      ? '🔴 Failed'
                      : '⚪ Not configured'}
                  </span>
                </div>

                {isEditing ? (
                  <div className={styles.editRow}>
                    <input
                      type="password"
                      className={styles.keyInput}
                      placeholder={t('apiKeys.inputPlaceholder')}
                      value={inputValue}
                      onChange={(e) => setInputValue(e.target.value)}
                      autoFocus
                    />
                    <button className={styles.saveBtn} onClick={() => handleSave(provider)}>
                      {t('apiKeys.save')}
                    </button>
                    <button
                      className={styles.cancelBtn}
                      onClick={() => {
                        setEditingProvider(null);
                        setInputValue('');
                      }}
                    >
                      {t('apiKeys.cancel')}
                    </button>
                  </div>
                ) : (
                  <div className={styles.displayRow}>
                    <span className={styles.maskedKey}>
                      {status?.maskedKey ?? t('apiKeys.notSet')}
                    </span>
                    <button
                      className={styles.editBtn}
                      onClick={() => setEditingProvider(provider)}
                      aria-label={t('apiKeys.editAriaLabel')}
                    >
                      ✏️
                    </button>
                  </div>
                )}

                {status?.maskedKey && !isEditing && (
                  <button
                    className={styles.testBtn}
                    onClick={() => handleTest(provider)}
                    disabled={testing}
                    aria-label={t('apiKeys.testAriaLabel')}
                  >
                    {testing ? `⏳ ${t('apiKeys.testing')}` : t('apiKeys.testConnection')}
                  </button>
                )}

                {status?.lastTestedAt && (
                  <span className={styles.lastTested}>
                    {t('apiKeys.lastTested')}: {new Date(status.lastTestedAt).toLocaleTimeString()}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
```

---

### § Translation Keys

Thêm vào `frontend/src/i18n/translations.ts`:

```typescript
// Header
'header.apiKeys': { vi: '🔑 API Keys', en: '🔑 API Keys' },

// ApiKeysPage
'apiKeys.title': { vi: 'Quản lý API Keys', en: 'API Keys Management' },
'apiKeys.subtitle': { vi: 'Cấu hình API Key cá nhân để sử dụng model AI của riêng bạn.', en: 'Configure personal API keys to use your own AI models.' },
'apiKeys.loading': { vi: 'Đang tải...', en: 'Loading...' },
'apiKeys.loadError': { vi: 'Không thể tải danh sách API Keys', en: 'Failed to load API keys' },
'apiKeys.notSet': { vi: 'Chưa cấu hình', en: 'Not configured' },
'apiKeys.inputPlaceholder': { vi: 'Nhập API Key mới...', en: 'Enter new API key...' },
'apiKeys.save': { vi: 'Lưu', en: 'Save' },
'apiKeys.cancel': { vi: 'Huỷ', en: 'Cancel' },
'apiKeys.saveSuccess': { vi: 'API Key đã được lưu', en: 'API key saved successfully' },
'apiKeys.saveError': { vi: 'Không thể lưu API Key', en: 'Failed to save API key' },
'apiKeys.testConnection': { vi: 'Test Connection', en: 'Test Connection' },
'apiKeys.testing': { vi: 'Testing...', en: 'Testing...' },
'apiKeys.testSuccess': { vi: 'Kết nối thành công!', en: 'Connection successful!' },
'apiKeys.testFailed': { vi: 'Kết nối thất bại', en: 'Connection failed' },
'apiKeys.testError': { vi: 'Lỗi khi test kết nối', en: 'Error testing connection' },
'apiKeys.lastTested': { vi: 'Kiểm tra lần cuối', en: 'Last tested' },
'apiKeys.editAriaLabel': { vi: 'Sửa API Key', en: 'Edit API key' },
'apiKeys.testAriaLabel': { vi: 'Kiểm tra kết nối', en: 'Test connection' },
```

---

### § Test Cases — `ApiKeysPage.test.tsx`

```tsx
// frontend/src/features/settings/__tests__/ApiKeysPage.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { ApiKeysPage } from '../ApiKeysPage';
import * as credApi from '@/api/userCredentials';

vi.mock('@/api/userCredentials');

function renderPage() {
  return render(<MemoryRouter><ApiKeysPage /></MemoryRouter>);
}

describe('ApiKeysPage', () => {
  beforeEach(() => {
    vi.mocked(credApi.getApiKeys).mockResolvedValue([
      { provider: 'gemini', maskedKey: '••••••••a1b2', isValid: true, lastTestedAt: null },
    ]);
  });

  it('hiển thị provider Gemini với masked key', async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText('Gemini (Google AI)')).toBeInTheDocument());
    expect(screen.getByText('••••••••a1b2')).toBeInTheDocument();
  });

  it('click ✏️ hiển thị input nhập key', async () => {
    renderPage();
    await waitFor(() => screen.getByText('••••••••a1b2'));
    fireEvent.click(screen.getByRole('button', { name: /sửa api key/i }));
    expect(screen.getByPlaceholderText(/nhập api key mới/i)).toBeInTheDocument();
  });

  it('click Huỷ ẩn input', async () => {
    renderPage();
    await waitFor(() => screen.getByText('••••••••a1b2'));
    fireEvent.click(screen.getByRole('button', { name: /sửa api key/i }));
    fireEvent.click(screen.getByText('Huỷ'));
    expect(screen.queryByPlaceholderText(/nhập api key mới/i)).not.toBeInTheDocument();
  });

  it('lưu key gọi saveApiKey và reload', async () => {
    vi.mocked(credApi.saveApiKey).mockResolvedValue(undefined);
    renderPage();
    await waitFor(() => screen.getByText('••••••••a1b2'));
    fireEvent.click(screen.getByRole('button', { name: /sửa api key/i }));
    const input = screen.getByPlaceholderText(/nhập api key mới/i);
    fireEvent.change(input, { target: { value: 'new-key-xyz' } });
    fireEvent.click(screen.getByText('Lưu'));
    await waitFor(() =>
      expect(vi.mocked(credApi.saveApiKey)).toHaveBeenCalledWith('gemini', { apiKey: 'new-key-xyz' })
    );
  });

  it('Test Connection hiển thị Testing... trong khi chờ', async () => {
    vi.mocked(credApi.testApiKey).mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({ status: 'connected' }), 100))
    );
    renderPage();
    await waitFor(() => screen.getByText('Test Connection'));
    fireEvent.click(screen.getByText('Test Connection'));
    expect(screen.getByText(/testing/i)).toBeInTheDocument();
  });

  it('chưa cấu hình key hiển thị Not configured', async () => {
    vi.mocked(credApi.getApiKeys).mockResolvedValue([
      { provider: 'gemini', maskedKey: null, isValid: null, lastTestedAt: null },
    ]);
    renderPage();
    await waitFor(() => expect(screen.getByText('Chưa cấu hình')).toBeInTheDocument());
    expect(screen.queryByText('Test Connection')).not.toBeInTheDocument();
  });
});
```

---

### § Cấu trúc File — Tổng quan

```
backend/
├── alembic/versions/
│   └── 003_create_user_credentials_table.py     # MỚI
├── src/
│   ├── shared/infra/
│   │   ├── settings.py                          # CẬP NHẬT: +gemini_api_key, +fernet_secret_key
│   │   └── llm/
│   │       ├── __init__.py                      # MỚI
│   │       └── router.py                        # MỚI: LLMRouter
│   └── modules/identity/
│       ├── domain/
│       │   ├── entities.py                      # CẬP NHẬT: +UserCredential
│       │   ├── repositories.py                  # CẬP NHẬT: +UserCredentialRepository
│       │   └── exceptions.py                    # CẬP NHẬT: +CredentialNotFoundError
│       ├── application/
│       │   ├── dtos.py                          # CẬP NHẬT: +SaveApiKeyDTO, +TestApiKeyDTO
│       │   └── use_cases.py                     # CẬP NHẬT: +3 use cases
│       ├── infrastructure/
│       │   ├── orm_models.py                    # CẬP NHẬT: +UserCredentialORM
│       │   ├── credential_repository.py         # MỚI
│       │   ├── encryption.py                    # MỚI: FernetEncryptor
│       │   └── dependencies.py                  # CẬP NHẬT: +get_credential_repository
│       └── presentation/
│           ├── router.py                        # CẬP NHẬT: +4 routes
│           └── schemas.py                       # CẬP NHẬT: +SaveApiKeyRequest

frontend/
├── src/
│   ├── types/
│   │   └── userCredential.ts                    # MỚI
│   ├── api/
│   │   └── userCredentials.ts                   # MỚI
│   ├── i18n/
│   │   └── translations.ts                      # CẬP NHẬT: +17 keys
│   ├── components/
│   │   └── Header.tsx                           # CẬP NHẬT: +nút 🔑 API Keys
│   ├── features/settings/
│   │   ├── ApiKeysPage.tsx                      # MỚI
│   │   ├── ApiKeysPage.module.css               # MỚI
│   │   └── __tests__/
│   │       └── ApiKeysPage.test.tsx             # MỚI
│   └── App.tsx                                  # CẬP NHẬT: +route /settings/api-keys
```

**Files KHÔNG được chỉnh sửa** (trừ khi có lý do bắt buộc):
- `frontend/src/api/client.ts` — Axios client đã đúng
- `frontend/src/components/ProtectedRoute.tsx` — routing guard đã đúng
- `backend/src/shared/infra/database.py` — database setup đã đúng
- `backend/src/modules/identity/infrastructure/auth_dependencies.py` — JWT auth đã đúng
- `backend/alembic/versions/001_*.py`, `002_*.py` — đừng sửa migrations cũ

---

### § Phụ Thuộc & Dependencies cần cài

Kiểm tra `backend/pyproject.toml` hoặc `requirements.txt`:
- `cryptography` — thư viện AES/Fernet (xác nhận đã có hoặc thêm vào)
- `langchain-google-genai` — LangChain adapter cho Gemini (xác nhận đã có)
- Nếu chưa có: thêm vào requirements và chạy `pip install`

---

### § Learnings từ Stories Trước (Epic 1)

1. **`getErrorMessage(err, 'fallback string')`** — BẮT BUỘC tham số thứ 2.

2. **CSS Modules + CSS Variables AcademicPaper** — không dùng inline style cho màu sắc; dùng `var(--surface-raised)`, `var(--accent-blue)`, v.v.

3. **Zustand pattern**: Tách slice riêng nếu cần global state; `ApiKeysPage` có thể dùng local state đơn giản (không cần Zustand store riêng).

4. **Mock trong Vitest**: `vi.mock('@/api/userCredentials')` tại module level, không mock từng function riêng lẻ.

5. **`MemoryRouter` bắt buộc** khi render component có `Link`/`useNavigate`.

6. **Không dùng `act()` thủ công** với RTL — `waitFor()` tự xử lý async.

7. **Pydantic camelCase**: Backend dùng `alias_generator=to_camel` → Frontend nhận `maskedKey`, `isValid`, `lastTestedAt` (camelCase). Đảm bảo TypeScript interface khớp với JSON response.

8. **`onConflict` với SQLite** — `pg_insert().on_conflict_do_update()` không chạy với SQLite. Tests backend cho `upsert` nên mock repository.

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Completion Notes List

- ✅ Task 1: Cập nhật Settings — thêm `gemini_api_key` và `fernet_secret_key` với validator warning (không raise lỗi trong dev)
- ✅ Task 2: Migration 003 — tạo bảng `user_credentials` với UUID PK, FK→users, UNIQUE constraint, index
- ✅ Task 3: Domain layer — `UserCredential` dataclass, `UserCredentialRepository` ABC, `CredentialNotFoundError`
- ✅ Task 4: Application layer — DTOs (`SaveApiKeyDTO`, `TestApiKeyDTO`) + 4 use cases (`Save`, `List`, `Test`, `Delete`)
- ✅ Task 5: Infrastructure — `UserCredentialORM`, `PostgresUserCredentialRepository` (pg_insert upsert), `FernetEncryptor`, `get_credential_repository` dependency
- ✅ Task 6: Presentation — `SaveApiKeyRequest` schema, 4 routes (GET/PUT/DELETE/POST), import `UserCredentialORM` vào `main.py`
- ✅ Task 7: `LLMRouter` — ưu tiên user key, fallback về system key
- ✅ Task 8: Frontend types (`ApiKeyStatus`, `SaveApiKeyPayload`, `TestApiKeyResult`) + API client 4 functions
- ✅ Task 9: `ApiKeysPage.tsx` + CSS Modules theo AcademicPaper design system, input type="password"
- ✅ Task 10: Route `/settings/api-keys` trong App.tsx, nút 🔑 trong Header (mọi user)
- ✅ Task 11: 18 translation keys (vi/en) cho header.apiKeys và apiKeys.*
- ✅ Task 12: 6 test cases pass 100%
- ✅ Fix bug: `useTranslation` trả `t` không stable → gây infinite re-fetch. Fix bằng `useCallback([lang])`
- ✅ Backend: 41/41 tests pass. Frontend: 52/52 tests pass, không regression

### File List

- `backend/src/shared/infra/settings.py` (cập nhật: +gemini_api_key, +fernet_secret_key)
- `backend/alembic/versions/003_create_user_credentials_table.py` (mới)
- `backend/src/modules/identity/domain/entities.py` (cập nhật: +UserCredential)
- `backend/src/modules/identity/domain/repositories.py` (cập nhật: +UserCredentialRepository)
- `backend/src/modules/identity/domain/exceptions.py` (cập nhật: +CredentialNotFoundError)
- `backend/src/modules/identity/application/dtos.py` (cập nhật: +SaveApiKeyDTO, +TestApiKeyDTO)
- `backend/src/modules/identity/application/use_cases.py` (cập nhật: +4 use cases)
- `backend/src/modules/identity/infrastructure/orm_models.py` (cập nhật: +UserCredentialORM)
- `backend/src/modules/identity/infrastructure/credential_repository.py` (mới)
- `backend/src/modules/identity/infrastructure/encryption.py` (mới)
- `backend/src/modules/identity/infrastructure/dependencies.py` (cập nhật: +get_credential_repository)
- `backend/src/modules/identity/presentation/schemas.py` (cập nhật: +SaveApiKeyRequest)
- `backend/src/modules/identity/presentation/router.py` (cập nhật: +4 routes)
- `backend/main.py` (cập nhật: import UserCredentialORM)
- `backend/src/shared/infra/llm/__init__.py` (mới)
- `backend/src/shared/infra/llm/router.py` (mới: LLMRouter)
- `frontend/src/types/userCredential.ts` (mới)
- `frontend/src/api/userCredentials.ts` (mới)
- `frontend/src/features/settings/ApiKeysPage.tsx` (mới)
- `frontend/src/features/settings/ApiKeysPage.module.css` (mới)
- `frontend/src/features/settings/__tests__/ApiKeysPage.test.tsx` (mới)
- `frontend/src/App.tsx` (cập nhật: +route /settings/api-keys)
- `frontend/src/components/Header.tsx` (cập nhật: +nút 🔑 API Keys)
- `frontend/src/i18n/translations.ts` (cập nhật: +18 translation keys)
- `frontend/src/i18n/useTranslation.ts` (fix: memoize t với useCallback)

### Review Findings

_Code review 2026-06-16 (bmad-code-review: Blind Hunter + Edge Case Hunter + Acceptance Auditor). 4 decision-needed, 9 patch, 3 defer, 6 dismissed._

**Decision resolved (default — 2026-06-16):** #1→Patch (raise ở prod), #2→Patch (raise khi decrypt fail), #3→Defer (giữ runtime, refactor test sau), #4→Patch (làm đúng spec).

- [x] [Review][Decision→Patch] Ephemeral Fernet key không hard-fail ở production — sẽ raise khi `app_env=production` & key rỗng (mirror `secret_key_must_not_be_default`). Xem patch bên dưới.
- [x] [Review][Decision→Patch] LLMRouter fallback system key khi giải mã thất bại — sẽ raise thay vì fallback âm thầm. Xem patch bên dưới.
- [x] [Review][Decision→Defer] `TestApiKeyUseCase` hardcode `ChatGoogleGenerativeAI` — giữ hiện trạng runtime (khớp code mẫu spec); refactor inject client để test sau. Ghi deferred-work.
- [x] [Review][Decision→Patch] Lệch spec UI AC6/AC7 — sẽ làm đúng wording. Xem patch bên dưới.

**Patch (sửa được, không cần quyết định):**

- [x] [Review][Patch] Hard-fail ở production khi `FERNET_SECRET_KEY` rỗng — thêm raise trong validator giống `secret_key_must_not_be_default` [backend/src/shared/infra/settings.py:49]
- [x] [Review][Patch] LLMRouter raise rõ ràng khi decrypt fail thay vì fallback system key âm thầm (tránh cross-tenant billing) [backend/src/shared/infra/llm/router.py:38]
- [x] [Review][Patch] AC6 hiển thị "vừa xong"/relative time + AC7 thông báo lỗi inline cạnh badge Failed (lưu error string, không chỉ toast) [frontend/src/features/settings/ApiKeysPage.tsx]

- [x] [Review][Patch] Test connection: `decrypt()` nằm NGOÀI try → InvalidToken (key xoay/ciphertext hỏng) leo thẳng thành HTTP 500 [backend/src/modules/identity/application/use_cases.py:164]
- [x] [Review][Patch] Rò rỉ exception thô `str(e)[:200]` về client + render thẳng trong toast — lỗi SDK có thể chứa key/URL/header; cần log nội bộ, trả message generic [backend/src/modules/identity/application/use_cases.py:175]
- [x] [Review][Patch] `llm.ainvoke("Hello")` không có timeout — Gemini treo sẽ giữ worker/DB session vô hạn (vector cạn pool) [backend/src/modules/identity/application/use_cases.py:169]
- [x] [Review][Patch] `SaveApiKeyRequest.api_key` chỉ `min_length=1`, không strip/không max_length — key toàn khoảng trắng hoặc khổng lồ qua được; client non-browser bypass trim của FE [backend/src/modules/identity/presentation/schemas.py:52]
- [x] [Review][Patch] DELETE & POST `.../test` thiếu allowlist provider mà PUT đã có — provider tuỳ ý chảy thẳng vào DB query [backend/src/modules/identity/presentation/router.py:110,121]
- [x] [Review][Patch] Lệch tên index: ORM `index=True` (→ `ix_user_credentials_user_id`) vs migration tạo `idx_user_credentials_user_id` — schema test (create_all) lệch schema prod (alembic) [backend/src/modules/identity/infrastructure/orm_models.py:44]
- [x] [Review][Patch] FE: Save với input rỗng/khoảng trắng `return` âm thầm, không toast/feedback [frontend/src/features/settings/ApiKeysPage.tsx]
- [x] [Review][Patch] FE: nút Save không disable khi đang gửi → double-click bắn 2 PUT/duplicate upsert [frontend/src/features/settings/ApiKeysPage.tsx]
- [x] [Review][Patch] FE: `lastTestedAt` dùng `toLocaleTimeString()` mất ngày + render `Invalid Date` nếu chuỗi hỏng, cần guard `isNaN` [frontend/src/features/settings/ApiKeysPage.tsx]

**Defer (đã ghi vào deferred-work.md):**

- [x] [Review][Defer] `update_test_result` no-op âm thầm khi row bị xóa giữa test và ghi kết quả (concurrent delete) — kết quả test mất, UI hiện trạng thái cũ [backend/src/modules/identity/infrastructure/credential_repository.py] — deferred, edge race
- [x] [Review][Defer] `deleteApiKey` API client + endpoint DELETE tồn tại nhưng KHÔNG có nút xóa trên UI — endpoint mồ côi, user không xóa được key (ngoài AC) [frontend/src/features/settings/ApiKeysPage.tsx] — deferred, ngoài AC
- [x] [Review][Defer] `mask()` giải mã full plaintext server-side mỗi lần list chỉ để lấy 4 ký tự cuối — vật chất hóa secret trong RAM mỗi request; cân nhắc lưu last4 riêng [backend/src/modules/identity/application/use_cases.py:138] — deferred, đổi thiết kế

## Change Log

- 2026-06-16: Tạo Story 2.1 — BMad Method v6.8.0 (create-story). Story về quản lý API Keys cá nhân với mã hóa AES/Fernet + LLMRouter foundation.
- 2026-06-16: Triển khai Story 2.1 — claude-sonnet-4-6. 24 files tạo/cập nhật, 41 BE tests + 52 FE tests pass.
