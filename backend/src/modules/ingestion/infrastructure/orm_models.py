import uuid
from datetime import datetime

from sqlalchemy import ARRAY, BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.src.shared.infra.database import Base


class PaperORM(Base):
    __tablename__ = "papers"

    id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False, server_default="")
    authors: Mapped[list[str]] = mapped_column(ARRAY(Text()), nullable=False, server_default=text("'{}'"))
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, server_default="manual")
    doi: Mapped[str | None] = mapped_column(String(200), nullable=True)
    arxiv_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="pending")
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class UploadedFileORM(Base):
    __tablename__ = "uploaded_files"

    id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("users.id"),
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
