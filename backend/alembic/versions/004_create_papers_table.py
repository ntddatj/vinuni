"""create_papers_table

Revision ID: 004
Revises: 003
Create Date: 2026-06-17

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: str | Sequence[str] | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "papers",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False, server_default=""),
        sa.Column("authors", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("abstract", sa.Text(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(50), nullable=False, server_default="manual"),
        sa.Column("doi", sa.String(200), nullable=True),
        sa.Column("arxiv_id", sa.String(100), nullable=True),
        sa.Column("url", sa.String(2000), nullable=True),
        sa.Column("pdf_url", sa.String(2000), nullable=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_papers_project_id", "papers", ["project_id"])
    op.create_index("idx_papers_user_id", "papers", ["user_id"])
    op.create_index("idx_papers_status", "papers", ["status"])


def downgrade() -> None:
    op.drop_index("idx_papers_status", table_name="papers")
    op.drop_index("idx_papers_user_id", table_name="papers")
    op.drop_index("idx_papers_project_id", table_name="papers")
    op.drop_table("papers")
