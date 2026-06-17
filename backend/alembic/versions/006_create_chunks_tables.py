"""create_chunks_tables

Enable pgvector + tạo parent_chunks / child_chunks tables cho ingestion.

Revision ID: 006
Revises: 005
Create Date: 2026-06-17

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "006"
down_revision: str | Sequence[str] | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Bắt buộc tạo extension trước khi dùng vector type
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "parent_chunks",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("paper_id", sa.Uuid(), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_parent_chunks_paper_id", "parent_chunks", ["paper_id"])
    op.create_index("idx_parent_chunks_project_id", "parent_chunks", ["project_id"])

    op.create_table(
        "child_chunks",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "parent_chunk_id",
            sa.Uuid(),
            sa.ForeignKey("parent_chunks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("paper_id", sa.Uuid(), sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        # embedding: vector(768) — text-embedding-004 của Google tạo vector 768 chiều
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_child_chunks_paper_id", "child_chunks", ["paper_id"])
    op.create_index("idx_child_chunks_project_id", "child_chunks", ["project_id"])
    # HNSW index cho vector search (NFR3: < 500ms)
    op.execute(
        """
        CREATE INDEX idx_child_chunks_embedding_hnsw
        ON child_chunks USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )


def downgrade() -> None:
    op.drop_index("idx_child_chunks_embedding_hnsw", table_name="child_chunks")
    op.drop_index("idx_child_chunks_project_id", table_name="child_chunks")
    op.drop_index("idx_child_chunks_paper_id", table_name="child_chunks")
    op.drop_table("child_chunks")
    op.drop_index("idx_parent_chunks_project_id", table_name="parent_chunks")
    op.drop_index("idx_parent_chunks_paper_id", table_name="parent_chunks")
    op.drop_table("parent_chunks")
