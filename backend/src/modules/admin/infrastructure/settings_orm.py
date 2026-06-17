from datetime import datetime

from sqlalchemy import DateTime, String, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from backend.src.shared.infra.database import Base


class SystemSettingORM(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


async def get_setting(db: AsyncSession, key: str, default: str | None = None) -> str | None:
    result = await db.execute(select(SystemSettingORM).where(SystemSettingORM.key == key))
    row = result.scalar_one_or_none()
    return row.value if row else default


async def list_settings(db: AsyncSession) -> list[SystemSettingORM]:
    result = await db.execute(select(SystemSettingORM).order_by(SystemSettingORM.key))
    return list(result.scalars().all())


async def upsert_setting(db: AsyncSession, key: str, value: str) -> SystemSettingORM:
    result = await db.execute(select(SystemSettingORM).where(SystemSettingORM.key == key))
    row = result.scalar_one_or_none()
    if row:
        row.value = value
    else:
        row = SystemSettingORM(key=key, value=value)
        db.add(row)
    await db.flush()
    return row
