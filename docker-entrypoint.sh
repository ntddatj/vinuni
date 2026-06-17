#!/bin/sh
set -e

# Khi mount ./data từ host (docker-compose: ./data:/app/data), thư mục thường thuộc
# quyền root trên host → đè lên quyền của image, khiến appuser KHÔNG ghi được
# (PermissionError khi tạo data/uploads lúc upload tài liệu).
#
# Container khởi động như root để sửa quyền volume mount, sau đó hạ quyền xuống
# appuser bằng gosu trước khi chạy app. An toàn và tự phục hồi sau mỗi lần rebuild.
if [ "$(id -u)" = "0" ]; then
  mkdir -p /app/data
  chown -R appuser:appuser /app/data 2>/dev/null || true
  exec gosu appuser "$@"
fi

exec "$@"
