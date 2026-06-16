import asyncio
import logging
from datetime import datetime, timezone
from functools import partial
from uuid import uuid4

logger = logging.getLogger(__name__)

import bcrypt

from backend.src.modules.identity.application.dtos import LoginResponseDTO, LoginUserDTO, RegisterUserDTO, UserResponseDTO
from backend.src.modules.identity.domain.entities import User, UserCredential
from backend.src.modules.identity.domain.exceptions import (
    CredentialNotFoundError,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
)
from backend.src.modules.identity.domain.repositories import UserCredentialRepository, UserRepository


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        # Mật khẩu > 72 byte hoặc hash lưu trữ không hợp lệ -> coi như sai
        # credential (trả 401 generic) thay vì để vỡ thành HTTP 500.
        return False


class RegisterUserUseCase:
    def __init__(self, user_repository: UserRepository) -> None:
        self._repo = user_repository

    async def execute(self, dto: RegisterUserDTO) -> UserResponseDTO:
        email = dto.email.lower()
        existing = await self._repo.find_by_email(email)
        if existing:
            raise EmailAlreadyExistsError(f"Email {email} đã tồn tại")

        loop = asyncio.get_running_loop()
        hashed = await loop.run_in_executor(None, partial(_hash_password, dto.password))

        user_count = await self._repo.count_all()
        role = "admin" if user_count == 0 else "user"

        user = User(
            id=str(uuid4()),
            email=email,
            hashed_password=hashed,
            role=role,
            is_active=True,
        )
        saved = await self._repo.save(user)

        return UserResponseDTO(
            id=saved.id,
            email=saved.email,
            role=saved.role,
            is_active=saved.is_active,
            created_at=saved.created_at,
            updated_at=saved.updated_at,
        )


class LoginUserUseCase:
    def __init__(self, user_repository: UserRepository) -> None:
        self._repo = user_repository

    async def execute(self, dto: LoginUserDTO) -> LoginResponseDTO:
        from backend.src.shared.infra.jwt_utils import create_access_token

        email = dto.email.lower()
        user = await self._repo.find_by_email(email)

        if not user or not user.is_active:
            raise InvalidCredentialsError("Email hoặc mật khẩu không đúng")

        loop = asyncio.get_running_loop()
        password_valid = await loop.run_in_executor(
            None, partial(_verify_password, dto.password, user.hashed_password)
        )

        if not password_valid:
            raise InvalidCredentialsError("Email hoặc mật khẩu không đúng")

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


class SaveApiKeyUseCase:
    def __init__(self, repo: UserCredentialRepository, encryptor: "FernetEncryptor") -> None:
        self._repo = repo
        self._encryptor = encryptor

    async def execute(self, user_id: str, provider: str, plain_api_key: str) -> UserCredential:
        from backend.src.modules.identity.infrastructure.encryption import FernetEncryptor

        encrypted = self._encryptor.encrypt(plain_api_key)
        existing = await self._repo.find_by_user_and_provider(user_id, provider)
        if existing:
            credential = UserCredential(
                id=existing.id,
                user_id=user_id,
                provider=provider,
                encrypted_api_key=encrypted,
                last_tested_at=None,
                is_valid=None,
                created_at=existing.created_at,
                updated_at=datetime.now(timezone.utc),
            )
        else:
            credential = UserCredential.create(user_id, provider, encrypted)
        return await self._repo.upsert(credential)


class ListApiKeysUseCase:
    def __init__(self, repo: UserCredentialRepository, encryptor: "FernetEncryptor") -> None:
        self._repo = repo
        self._encryptor = encryptor

    async def execute(self, user_id: str) -> list[dict]:
        from backend.src.modules.identity.infrastructure.encryption import FernetEncryptor

        credentials = await self._repo.list_by_user(user_id)
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
        providers_with_key = {r["provider"] for r in result}
        if "gemini" not in providers_with_key:
            result.append({"provider": "gemini", "maskedKey": None, "isValid": None, "lastTestedAt": None})
        return result


class TestApiKeyUseCase:
    def __init__(self, repo: UserCredentialRepository, encryptor: "FernetEncryptor") -> None:
        self._repo = repo
        self._encryptor = encryptor

    async def execute(self, user_id: str, provider: str) -> dict:
        credential = await self._repo.find_by_user_and_provider(user_id, provider)
        if not credential:
            raise CredentialNotFoundError(f"Chưa cấu hình key cho provider: {provider}")

        try:
            plain_key = self._encryptor.decrypt(credential.encrypted_api_key)
        except Exception:
            raise CredentialNotFoundError(f"Không thể giải mã API Key cho provider: {provider}")

        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            # Dùng cùng model với LLMRouter (gemini-1.5-flash đã bị Google ngừng hỗ trợ)
            llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=plain_key)
            response = await asyncio.wait_for(llm.ainvoke("Hello"), timeout=15.0)
            _ = response.content
            await self._repo.update_test_result(credential.id, is_valid=True)
            return {"status": "connected"}
        except asyncio.TimeoutError:
            await self._repo.update_test_result(credential.id, is_valid=False)
            return {"status": "failed", "errorCode": "timeout"}
        except Exception as e:
            # Log chi tiết server-side để chẩn đoán; KHÔNG trả message thô về client
            # (có thể chứa key/URL). Client tự dịch theo errorCode.
            logger.warning("Test connection provider %s thất bại: %s: %s", provider, type(e).__name__, e)
            await self._repo.update_test_result(credential.id, is_valid=False)
            return {"status": "failed", "errorCode": "connection_failed"}


class DeleteApiKeyUseCase:
    def __init__(self, repo: UserCredentialRepository) -> None:
        self._repo = repo

    async def execute(self, user_id: str, provider: str) -> None:
        credential = await self._repo.find_by_user_and_provider(user_id, provider)
        if credential:
            await self._repo.delete(credential.id)


# Forward reference resolution
try:
    from backend.src.modules.identity.infrastructure.encryption import FernetEncryptor
except ImportError:
    pass
