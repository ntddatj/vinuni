import asyncio
from functools import partial
from uuid import uuid4

import bcrypt

from backend.src.modules.identity.application.dtos import RegisterUserDTO, UserResponseDTO
from backend.src.modules.identity.domain.entities import User
from backend.src.modules.identity.domain.exceptions import EmailAlreadyExistsError
from backend.src.modules.identity.domain.repositories import UserRepository


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


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
