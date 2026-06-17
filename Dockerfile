# ---- Stage 1: Build ----
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- Stage 2: Production ----
FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /install /usr/local

# gosu: hạ quyền từ root xuống appuser trong entrypoint sau khi sửa quyền volume mount
RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m appuser

COPY . .

RUN mkdir -p /app/data \
    && chown -R appuser:appuser /app \
    && chmod +x /app/docker-entrypoint.sh

# KHÔNG dùng `USER appuser` ở đây: container phải khởi động như root để entrypoint
# sửa được quyền của volume ./data (mount đè quyền root từ host), rồi gosu hạ quyền
# xuống appuser. Xem docker-entrypoint.sh.
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
