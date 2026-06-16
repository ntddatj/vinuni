from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.modules.identity.domain.entities import User
from backend.src.modules.identity.domain.exceptions import EmailAlreadyExistsError
from backend.src.modules.identity.domain.repositories import UserRepository
from backend.src.modules.identity.infrastructure.orm_models import UserORM


class PostgresUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(UserORM).where(UserORM.email == email))
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def find_by_id(self, user_id: str) -> User | None:
        result = await self._session.execute(select(UserORM).where(UserORM.id == user_id))
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def count_all(self) -> int:
        result = await self._session.execute(select(func.count()).select_from(UserORM))
        return result.scalar_one()

    async def save(self, user: User) -> User:
        orm = UserORM(
            id=user.id,
            email=user.email,
            hashed_password=user.hashed_password,
            role=user.role,
            is_active=user.is_active,
        )
        self._session.add(orm)
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            raise EmailAlreadyExistsError(f"Email {user.email} đã tồn tại")
        await self._session.refresh(orm)
        return self._to_domain(orm)

    @staticmethod
    def _to_domain(orm: UserORM) -> User:
        return User(
            id=orm.id,
            email=orm.email,
            hashed_password=orm.hashed_password,
            role=orm.role,
            is_active=orm.is_active,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )
