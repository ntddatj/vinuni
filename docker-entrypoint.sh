#!/bin/sh
set -e

# Khi mount ./data từ host (docker-compose: ./data:/app/data), thư mục thường thuộc
# quyền root trên host → đè lên quyền của image, khiến appuser KHÔNG ghi được
# (PermissionError khi tạo data/uploads lúc upload tài liệu).
#
# Container khởi động như root để sửa quyền volume mount, sau đó hạ quyền xuống
# appuser bằng gosu trước khi chạy app. An toàn và tự phục hồi sau mỗi lần rebuild.
#
# Tự áp Alembic migration khi khởi động — CHỈ service đặt RUN_MIGRATIONS=1 (thường là backend)
# để tránh race giữa backend & worker (cùng DB). Non-fatal: lỗi chỉ in cảnh báo, vẫn start để
# không brick stack dev. Lý do cần: dev tạo schema bằng create_all (KHÔNG ALTER bảng đã tồn tại)
# → migration thêm cột vào bảng cũ phải chạy qua alembic, nếu không sẽ UndefinedColumnError.
run_migrations() {
  if [ "$RUN_MIGRATIONS" = "1" ]; then
    echo "[entrypoint] alembic upgrade head..."
    ( cd /app/backend && alembic upgrade head ) \
      || echo "[entrypoint] WARNING: alembic upgrade head thất bại — schema có thể chưa đồng bộ"
  fi
}

if [ "$(id -u)" = "0" ]; then
  mkdir -p /app/data
  chown -R appuser:appuser /app/data 2>/dev/null || true
  if [ "$RUN_MIGRATIONS" = "1" ]; then
    echo "[entrypoint] alembic upgrade head..."
    gosu appuser sh -c 'cd /app/backend && alembic upgrade head' \
      || echo "[entrypoint] WARNING: alembic upgrade head thất bại — schema có thể chưa đồng bộ"
  fi
  exec gosu appuser "$@"
fi

run_migrations
exec "$@"
