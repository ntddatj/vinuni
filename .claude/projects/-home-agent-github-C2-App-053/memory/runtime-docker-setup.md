---
name: runtime-docker-setup
description: How the app runs (docker-compose) and how to apply backend code changes
metadata:
  type: project
---

App chạy qua docker-compose: services `backend` (8000), `worker`, `postgres` (pgvector, 5432), `redis` (6379). Frontend dev chạy ngoài compose ở `5173`, proxy `/api` → `http://localhost:8000` (frontend/vite.config.ts).

Backend image **build từ code** (chỉ mount `./data`), KHÔNG mount source. Nên sau khi sửa code backend phải rebuild, không phải chỉ restart:
`docker compose up -d --build backend`

Kiểm tra nhanh: `docker ps` (xem `Restarting` = crash loop), `docker logs c2-app-053-backend-1 --tail 50`, `curl http://localhost:8000/health`.

DB creds (.env): c2user/c2pass/c2db. Admin user: nguyentiendat1990@gmail.com (role=admin). Auth qua cookie httponly `access_token`; login endpoint `POST /api/auth/login`.

Tooling local: dùng `.venv/bin/pytest` và `.venv/bin/ruff` (không phải `venv/`). Frontend: `npx tsc --noEmit`, `npx eslint`.
