import asyncio
from functools import partial
from uuid import uuid4

import bcrypt

from backend.src.modules.identity.application.dtos import LoginResponseDTO, LoginUserDTO, RegisterUserDTO, UserResponseDTO
from backend.src.modules.identity.domain.entities import User
from backend.src.modules.identity.domain.exceptions import EmailAlreadyExistsError, InvalidCredentialsError
from backend.src.modules.identity.domain.repositories import UserRepository


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
