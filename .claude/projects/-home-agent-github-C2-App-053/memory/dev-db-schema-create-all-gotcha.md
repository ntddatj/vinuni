---
name: dev-db-schema-create-all-gotcha
description: DB dev tạo schema bằng create_all (không alembic) — story thêm cột vào bảng cũ sẽ vỡ
metadata:
  type: project
---

DB dev (docker compose) tạo schema bằng `Base.metadata.create_all` ở `backend/main.py` (~L42) khi backend startup — **KHÔNG chạy alembic** (bảng `alembic_version` không tồn tại). `create_all` chỉ tạo bảng còn thiếu, **không ALTER bảng đã có**.

**Hệ quả:** bất kỳ story nào thêm cột vào bảng *đã tồn tại* (vd story 4.1: `projects.deleted_at`, `papers.deleted_at`, 5 cột `sync_outbox`) → cột không được áp vào DB live, gây `UndefinedColumnError` khi INSERT/SELECT dù code/ORM đã đúng. Triệu chứng điển hình: "Tạo dự án thất bại" / lỗi 500 với `column "..." does not exist`.

**Cách sửa nhanh (non-destructive, có dữ liệu thật):** áp DDL của migration tương ứng vào Postgres bằng `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, backfill, `CREATE INDEX IF NOT EXISTS`, seed `system_settings` `ON CONFLICT DO NOTHING`. Lệnh: `docker compose exec -T postgres psql -U c2user -d c2db`.

**Đã xử lý lâu dài (2026-06-18):** DB đã `alembic stamp head` (alembic_version=009). `docker-entrypoint.sh` tự chạy `alembic upgrade head` khi start nếu `RUN_MIGRATIONS=1` (đặt cho service **backend** trong docker-compose; gate để tránh race với worker; non-fatal nếu lỗi). → Story sau thêm migration: chỉ cần `docker compose up -d --build backend` là tự áp. create_all vẫn còn trong `main.py` (bootstrap bảng mới trên DB rỗng) — chạy SAU migration nên vô hại. Xem [[runtime-docker-setup]].
