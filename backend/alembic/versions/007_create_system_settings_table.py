"""create_system_settings_table

Tạo bảng system_settings để lưu cấu hình hệ thống (admin quản lý).

Revision ID: 007
Revises: 006
Create Date: 2026-06-17

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: str | Sequence[str] | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.bulk_insert(
        sa.table(
            "system_settings",
            sa.column("key", sa.String),
            sa.column("value", sa.Text),
            sa.column("description", sa.Text),
        ),
        [
            {
                "key": "MAX_PAPERS_PER_PROJECT",
                "value": "15",
                "description": "Giới hạn số tài liệu tối đa trong một dự án",
            },
            {
                "key": "BROAD_QUERY_THRESHOLD",
                "value": "50",
                "description": "Ngưỡng kết quả để phát hiện truy vấn rộng",
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("system_settings")
