"""ORM cho bảng cache fills_gap_judgement (Story 4.7).

Lưu quyết định LLM-judge theo cặp (limitation_id, candidate_paper_id) để tránh re-judge.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.src.shared.infra.database import Base


class FillsGapJudgementORM(Base):
    __tablename__ = "fills_gap_judgement"

    __table_args__ = (
        UniqueConstraint("limitation_id", "candidate_paper_id", name="uq_fills_gap_pair"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        nullable=False,
        index=True,
    )
    limitation_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    candidate_paper_id: Mapped[str] = mapped_column(String, nullable=False)
    fills: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
