import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.src.shared.infra.database import Base


class ProjectORM(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SyncOutboxORM(Base):
    __tablename__ = "sync_outbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)  # ORM uses generic JSON for SQLite compat; migration creates JSONB on Postgres
    processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    project_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True, index=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dead_lettered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
