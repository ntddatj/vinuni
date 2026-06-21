"""create_fills_gap_judgement_table

Bảng cache quyết định LLM-judge cho cặp (limitation_id, candidate_paper_id).
Tránh re-judge khi fills_gap_task chạy lại (Story 4.7).

Revision ID: 010
Revises: 009
Create Date: 2026-06-21

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "010"
down_revision: str | Sequence[str] | None = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fills_gap_judgement",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("limitation_id", sa.String(), nullable=False),
        sa.Column("candidate_paper_id", sa.String(), nullable=False),
        sa.Column("fills", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("limitation_id", "candidate_paper_id", name="uq_fills_gap_pair"),
    )
    op.create_index("idx_fills_gap_project_id", "fills_gap_judgement", ["project_id"])
    op.create_index("idx_fills_gap_limitation_id", "fills_gap_judgement", ["limitation_id"])


def downgrade() -> None:
    op.drop_index("idx_fills_gap_limitation_id", table_name="fills_gap_judgement")
    op.drop_index("idx_fills_gap_project_id", table_name="fills_gap_judgement")
    op.drop_table("fills_gap_judgement")
