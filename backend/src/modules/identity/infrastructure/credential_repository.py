from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.modules.identity.domain.entities import UserCredential
from backend.src.modules.identity.domain.repositories import UserCredentialRepository
from backend.src.modules.identity.infrastructure.orm_models import UserCredentialORM


def _orm_to_entity(orm: UserCredentialORM) -> UserCredential:
    return UserCredential(
        id=orm.id,
        user_id=orm.user_id,
        provider=orm.provider,
        encrypted_api_key=orm.encrypted_api_key,
        last_tested_at=orm.last_tested_at,
        is_valid=orm.is_valid,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
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
            select(UserCredentialORM)
            .where(UserCredentialORM.user_id == user_id)
            .order_by(UserCredentialORM.provider)
        )
        return [_orm_to_entity(r) for r in result.scalars().all()]

    async def upsert(self, credential: UserCredential) -> UserCredential:
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
                    "is_valid": None,
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
