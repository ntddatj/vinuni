---
name: tuning-vars-admin-settings
description: PO nguyên tắc — biến tuning/policy phải vào admin system_settings, không để env var
metadata:
  type: feedback
---

Đạt (PO) yêu cầu: các **biến tuning/chính sách nghiệp vụ** phải được đưa vào **admin System Settings** (bảng `system_settings`, API `/admin/settings`) để admin cấu hình runtime — KHÔNG hardcode thành env var.

**Why:** tiện cấu hình không cần redeploy; nhất quán với pattern `MAX_PAPERS_PER_PROJECT`/`BROAD_QUERY_THRESHOLD` (story 2.6).

**How to apply:**
- Cơ chế có sẵn: `SystemSettingORM` + `get_setting`/`upsert_setting` (`backend/src/modules/admin/infrastructure/settings_orm.py`); seed default trong migration (mirror `007_create_system_settings_table.py`); thêm key vào `_NUMERIC_SETTING_KEYS` trong `admin/presentation/router.py` (validate int≥1); code đọc qua `get_setting(db, KEY, default)` với fallback hằng số.
- **Ngoại lệ:** knob hạ tầng thuần (RAM/throughput, vd `SYNC_OUTBOX_BATCH_SIZE`) GIỮ ở env — không cho admin chỉnh để tránh OOM/ARCH-1.
- Tiền lệ đã làm (story 4.1, 2026-06-18): `GC_RETENTION_DAYS` + `MAX_SYNC_RETRIES` chuyển từ env → system_settings.
