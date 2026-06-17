"""extend_sync_outbox_and_soft_delete

Mở rộng bảng sync_outbox: thêm project_id, retry_count, last_error, processed_at, dead_lettered.
Thêm deleted_at vào projects và papers (mốc xóa mềm chính xác cho GC 7 ngày).

Revision ID: 009
Revises: 008
Create Date: 2026-06-17

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: str | Sequence[str] | None = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- sync_outbox: thêm cột mới ---
    op.add_column("sync_outbox", sa.Column("project_id", sa.UUID(), nullable=True))
    op.add_column("sync_outbox", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("sync_outbox", sa.Column("last_error", sa.Text(), nullable=True))
    op.add_column("sync_outbox", sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("sync_outbox", sa.Column("dead_lettered", sa.Boolean(), nullable=False, server_default="false"))

    # Backfill project_id từ payload->>'project_id' cho hàng cũ
    op.execute(
        "UPDATE sync_outbox SET project_id = (payload->>'project_id')::uuid "
        "WHERE project_id IS NULL AND payload->>'project_id' IS NOT NULL"
    )

    # Index cho project_id và dead_lettered
    op.create_index("idx_sync_outbox_project_id", "sync_outbox", ["project_id"])
    op.create_index(
        "idx_sync_outbox_dead_lettered",
        "sync_outbox",
        ["dead_lettered"],
        postgresql_where=sa.text("dead_lettered = true"),
    )
    # Index đã xử lý + thời điểm (cho GC dọn outbox cũ)
    op.create_index(
        "idx_sync_outbox_processed_at",
        "sync_outbox",
        ["processed_at"],
        postgresql_where=sa.text("processed = true"),
    )

    # --- projects: thêm deleted_at ---
    op.add_column("projects", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    # --- papers: thêm deleted_at ---
    op.add_column("papers", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    # Backfill deleted_at cho hàng đã xóa mềm TRƯỚC migration này (is_deleted=true, deleted_at NULL).
    # Nếu không, GC dùng `deleted_at < threshold` (NULL → false) sẽ KHÔNG bao giờ dọn được chúng.
    # Dùng now() (thay vì updated_at — bị reset bởi mọi update) → cấp lại cửa sổ retention từ thời điểm migrate.
    op.execute("UPDATE projects SET deleted_at = now() WHERE is_deleted = true AND deleted_at IS NULL")
    op.execute("UPDATE papers SET deleted_at = now() WHERE is_deleted = true AND deleted_at IS NULL")

    # --- Seed cấu hình tuning vào system_settings (Admin chỉnh runtime, không để env) ---
    # Mirror pattern MAX_PAPERS_PER_PROJECT (migration 007). Code đọc qua get_setting + fallback.
    op.bulk_insert(
        sa.table(
            "system_settings",
            sa.column("key", sa.String),
            sa.column("value", sa.Text),
            sa.column("description", sa.Text),
        ),
        [
            {
                "key": "GC_RETENTION_DAYS",
                "value": "7",
                "description": "Số ngày giữ dữ liệu đã xóa mềm trước khi Garbage Collection xóa cứng vĩnh viễn (Postgres + Neo4j)",
            },
            {
                "key": "MAX_SYNC_RETRIES",
                "value": "3",
                "description": "Số lần retry đồng bộ Postgres→Neo4j khi lỗi, trước khi đẩy event vào DLQ",
            },
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM system_settings WHERE key IN ('GC_RETENTION_DAYS', 'MAX_SYNC_RETRIES')")
    op.drop_index("idx_sync_outbox_processed_at", table_name="sync_outbox")
    op.drop_index("idx_sync_outbox_dead_lettered", table_name="sync_outbox")
    op.drop_index("idx_sync_outbox_project_id", table_name="sync_outbox")
    op.drop_column("sync_outbox", "dead_lettered")
    op.drop_column("sync_outbox", "processed_at")
    op.drop_column("sync_outbox", "last_error")
    op.drop_column("sync_outbox", "retry_count")
    op.drop_column("sync_outbox", "project_id")
    op.drop_column("projects", "deleted_at")
    op.drop_column("papers", "deleted_at")
