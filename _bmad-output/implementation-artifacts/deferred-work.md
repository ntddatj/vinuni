# Deferred Work

## Deferred from: code review of story 2-6-kiem-soat-gioi-han-so-luong-tai-lieu-admin-dat-ra (2026-06-17)

- **`create_all` (dev path) không seed `system_settings`** — chỉ migration 007 seed (MAX_PAPERS_PER_PROJECT=15, BROAD_QUERY_THRESHOLD=50); đường `Base.metadata.create_all` của lifespan tạo bảng rỗng. Trên DB dev mới, `GET /admin/settings` trả list rỗng → trang Admin hiển thị mặc định 15/50 và chỉ tạo row sau lần Save đầu. Giá trị vẫn áp dụng đúng nhờ fallback trong `get_setting/get_max_papers_limit`; tác động thấp. [backend/main.py:35]
- **Loser của race có thể nhận 503 thay vì 403 (AC#2)** — Redis lock chỉ retry 2 lần với 1 nhịp sleep 0.2s; nếu winner giữ lock >0.2s, loser nhận 503 "Hệ thống đang bận" thay vì 403. ĐÃ QUYẾT ĐỊNH chấp nhận: bảo đảm cốt lõi *không nhân đôi tài liệu* vẫn đúng, 503 là tín hiệu contention retriable; đổi sang blocking-wait để ép 403 thêm độ trễ/nguy cơ thundering-herd không đáng. [backend/src/modules/ingestion/application/use_cases.py:_paper_limit_lock]

## Deferred from: code review of story 2-5-ingestion-bat-dong-bo-qua-worker-arq-stream-tien-trinh-sse (2026-06-17)

- **enqueue sau `db.commit()` không bù trừ khi Redis down** — paper đã commit `pending` nhưng job không được đẩy, exception trả 500; paper kẹt `pending` mãi, frontend không mở SSE. MVP đã tự ghi nhận trong docstring. [backend/src/modules/ingestion/application/use_cases.py:41-45]
- **Paper không có text bị đánh dấu `indexed` im lặng** — download fail + không có abstract → text rỗng → worker set `indexed` + `publish_completed`; UI báo thành công dù không có nội dung tìm kiếm được. Thiếu trạng thái "indexed nhưng rỗng". [backend/worker.py:120-125]
- **`from-search` không giới hạn độ dài input** — title/abstract/authors không bound; abstract là fallback text cho ingestion → client (project owner) có thể post abstract nhiều MB nuôi pipeline embedding (DoS/chi phí). [backend/src/modules/ingestion/presentation/schemas.py AddFromSearchRequestSchema]
- **`get_redis()` singleton race + không dispose** — check-then-set không khóa, hai request cold-start có thể tạo 2 client (rò rỉ client đầu); không có cleanup lúc shutdown. `from_url` lazy nên impact thấp. [backend/src/shared/infra/redis_client.py]
- **`DocumentList` không auto-poll** — hàng `pending`/`processing` chỉ cập nhật khi `refreshTrigger` bị bump bởi SSE completion; tài liệu thêm ở tab/phiên khác hoặc bị onerror sai sẽ kẹt badge `processing` (animation quay mãi). [frontend/src/features/workspace/DocumentList.tsx]

## Deferred from: code review of story 2-2-tim-kiem-bai-bao-hoc-thuat-song-song-voi-xu-ly-loi-degraded-union (2026-06-17)

- **Dedup không bắt trùng chéo nguồn khi định danh rời rạc** — cùng một bài: arXiv chỉ trả `arxiv_id`, Semantic Scholar chỉ trả `DOI` (không có ArXiv externalId) → không có khóa chung nên cả hai lọt qua `_deduplicate`, bài xuất hiện 2 lần. Cần fuzzy/title matching, là tính năng lớn hơn AC #2. [backend/src/modules/search/application/use_cases.py:56-76]
- **arXiv query-grammar injection nhẹ** — user input đưa thẳng vào `search_query=all:{query}`; người dùng có thể chèn cú pháp boolean/field-prefix của arXiv (`ti:`, `OR`, `ANDNOT`) làm đổi ngữ nghĩa truy vấn hoặc tạo query lỗi. Cần escape grammar arXiv. [backend/src/modules/search/infrastructure/arxiv_client.py:21-25]

## Deferred from: code review of story 2-1-quan-ly-api-keys-ca-nhan-ma-hoa-bao-mat (2026-06-16)

- **`update_test_result` no-op âm thầm khi concurrent delete** — nếu credential bị xóa giữa lúc test chạy và ghi kết quả, ORM trả `None`, method return không commit/không lỗi → kết quả test mất, UI hiện trạng thái cũ. Edge race, không chặn MVP. [backend/src/modules/identity/infrastructure/credential_repository.py]
- **`deleteApiKey` endpoint mồ côi — không có UI** — API client `deleteApiKey` và endpoint `DELETE /user/api-keys/{provider}` đã có nhưng ApiKeysPage chỉ render Edit + Test, không có nút xóa. Nằm ngoài AC của story 2.1; cần quyết định có thêm tính năng xóa key ở story sau không. [frontend/src/features/settings/ApiKeysPage.tsx]
- **`mask()` giải mã full plaintext mỗi lần list** — `ListApiKeysUseCase` decrypt toàn bộ key server-side chỉ để hiển thị 4 ký tự cuối, vật chất hóa secret trong RAM ở mọi request GET. Cân nhắc lưu `last4` (không nhạy cảm) tách riêng để tránh decrypt khi list. Đổi thiết kế lưu trữ. [backend/src/modules/identity/application/use_cases.py:138]
- **`TestApiKeyUseCase` hardcode `ChatGoogleGenerativeAI` — không mock được (Dev Notes #8)** — `use_cases.py:167-168` khởi tạo `ChatGoogleGenerativeAI` trực tiếp trong use case nên không unit-test được nếu không có network/thư viện thật. Khớp code mẫu trong spec nên không phải bug runtime; nên refactor inject một LLM client interface để test connection có thể mock. [backend/src/modules/identity/application/use_cases.py:167]

## Deferred from: code review of story 1-5-giao-dien-3-cot-bo-chuyen-doi-ngon-ngu-chu-de (2026-06-16)

- `activeProjectId` đọc từ `?projectId` không validate so với danh sách 10 dự án đã load → URL trỏ project #11+/đã xóa thì tiêu đề cột giữa âm thầm về fallback "Chọn một dự án", không có phản hồi "không tìm thấy". Cần quyết định UX (validate + toast, hay load riêng project đó). [frontend/src/features/dashboard/DashboardPage.tsx:142-148]
- `lang` không lưu localStorage nên reset về 'vi' sau mỗi F5, khác với theme đã persist. AC#7 không yêu cầu persistence nên không chặn story; nên bổ sung `initLang()` + localStorage để nhất quán với theme. [frontend/src/store/languageStore.ts]
- `ProjectsPage` (Story 1.4): ô tìm kiếm không debounce và không hủy request cũ (race condition khi gõ nhanh); xóa item cuối trang để lại trang rỗng không điều hướng được; `new Date(createdAt)` không guard → "Invalid Date" nếu backend trả rỗng. [frontend/src/features/workspace/ProjectsPage.tsx]
- `updateProject` luôn gửi `description: undefined` trong PATCH (có thể ghi đè null mô tả hiện có tùy semantics backend); `addProject` cứng `.slice(0, 10)` truncate khi đã load >10. Thuộc API/store của Story 1.4. [frontend/src/api/projects.ts, frontend/src/store/projectStore.ts]

## Deferred from: code review of story 1-2-dang-nhap-xac-thuc-bang-httponly-cookie (2026-06-16)

- **Login integration tests dùng SQLite trái Dev Notes của spec** — Dev Notes story 1.2 ghi "Không dùng SQLite (intentional decision từ story 1.1)", nhưng test thực tế (`tests/unit/identity/test_login_api.py`) dùng SQLite in-memory. Lý do defer: story 1.1 đã commit `tests/unit/identity/test_register_api.py` dùng **đúng pattern SQLite in-memory y hệt** — đây mới là quy ước thực tế của codebase, ghi chú trong Dev Notes là lỗi thời. Ép test login bỏ SQLite sẽ khiến nó lệch với test register anh em. Việc cần làm sau (nếu muốn): thống nhất chiến lược test ở cấp epic và cập nhật/loại bỏ ghi chú "không dùng SQLite" trong các spec, hoặc chuyển toàn bộ integration test (cả register lẫn login) sang chiến lược khác đồng nhất.

## Deferred from: code review of story 1-3-quy-trinh-onboarding-khoi-tao-du-an-dau-tien (2026-06-16)

- **ProtectedRoute coi mọi lỗi `/me` như chưa xác thực** — `.catch` của `getCurrentUser()` luôn `navigate('/login')` và không `setLoading(false)`, bất kể lỗi là 401, network, hay 500. Lỗi mạng/500 bị đối xử như đăng xuất. Defer vì component unmount khi navigate nên không treo spinner; phân biệt loại lỗi là refinement UX không chặn MVP. [frontend/src/components/ProtectedRoute.tsx:20]

## Deferred from: code review of story 1-4-crud-du-an-nghien-cuu-left-sidebar-dieu-huong (2026-06-16)

- Sidebar click dự án điều hướng `/dashboard?projectId=...` nhưng `DashboardPage` không đọc query param — tương tác "chết" cho tới khi Story 1.5 (layout 3 cột) xử lý. [frontend/src/features/workspace/ProjectSidebar.tsx:72]
- Migration Alembic `002` (JSONB, `gen_random_uuid()`, partial index `WHERE processed = false`) không được test suite chạy qua vì test dùng SQLite tạo bảng từ ORM metadata; `gen_random_uuid()` cần extension pgcrypto trên PostgreSQL < 13. [backend/alembic/versions/002_create_projects_and_sync_outbox_tables.py]
- `addProject` trong Zustand store hardcode `.slice(0, 10)` (liên quan Pitfall #7) — sidebar vẫn hiển thị đúng ≤10 dự án; nên thay bằng hằng số dùng chung hoặc refetch để tránh giả định cứng. [frontend/src/store/projectStore.ts]
- Overlay của CreateProjectModal/DeleteProjectModal vẫn đóng được khi click giữa lúc request đang bay (nút submit đã disable, overlay chưa khóa) — race UX nhỏ. [frontend/src/features/workspace/CreateProjectModal.tsx, DeleteProjectModal.tsx]

## Deferred from: code review of story 1-6-trang-quan-ly-toan-bo-du-an-dang-bang (2026-06-16)

- **Race condition: `loadProjects` không hủy request cũ** — không có AbortController/latest-wins guard; response của lần fetch cũ (đổi search/page/create/delete) có thể resolve sau và đè dữ liệu mới. Defer: là pattern fetch dùng chung toàn app, debounce 300ms đã giảm thiểu phần lớn case gõ tìm kiếm; nên xử lý ở cấp epic (thêm AbortController hoặc request-id chung). [frontend/src/features/workspace/ProjectsPage.tsx]
- **`formatDate` lệch ngày ở timezone âm với chuỗi date-only** — `new Date('2026-06-16')` parse là UTC midnight, `toLocaleDateString` render theo local → user phía tây UTC thấy lệch 1 ngày. Defer: phụ thuộc backend có trả date-only hay full ISO timestamp; hiện `createdAt` là ISO timestamp đầy đủ nên không phát sinh. [frontend/src/features/workspace/ProjectsPage.tsx:13]
- **Tạo dự án mới có thể không hiển thị trên trang hiện tại** — `CreateProjectModal.onSuccess` refetch đúng trang đang xem; dự án mới (tùy sort) có thể rơi sang trang khác và không xuất hiện, không có feedback. Defer: giữ nguyên hành vi cũ, không phải regression của story này. [frontend/src/features/workspace/ProjectsPage.tsx]

## Deferred from: code review of 2-3-goi-y-phan-nganh-mece-cho-chu-de-qua-rong (2026-06-17)

- `detect()` vẫn được gọi khi cả 2 nguồn lỗi / khi threshold cấu hình âm có thể bắn LLM mỗi query. Low impact vì threshold mặc định 50 đã chặn. [broad_query_detector.py:39, use_cases.py:63]
- Heuristic `total == 0 → len(papers)` ở cả ArxivClient và SemanticScholarClient che giấu trường hợp "thiếu field totalResults" vs "zero thật"; total âm không được guard. Một broad query mà nguồn thiếu field total sẽ không bao giờ được flag broad. Phụ thuộc upstream API, ít xảy ra. [arxiv_client.py:105, semantic_scholar_client.py:35]
- Translation key `search.broadQueryHint` đã thêm nhưng không render ở đâu (orphaned key). Cleanup UX — AC#2 chỉ yêu cầu chip, không yêu cầu hint text. [frontend/src/i18n/translations.ts:67]

## Deferred from: code review of story-2.4 (2026-06-17)

- 🟠 MIME spoofing — chỉ validate extension, không kiểm magic bytes (use_cases.py:42-45). Spec cố ý dùng extension; content-sniffing là hardening, rủi ro thấp nhờ graceful fallback.
- 🟠 Orphaned files — uploaded_files ghi disk + commit trước confirm; không TTL/cleanup (use_cases.py:47-61). Liên quan Story 2.5 worker.
- 🟡 Double-confirm tạo duplicate Paper trên cùng file_id, thiếu idempotency (use_cases.py:78-109).
- 🟡 gen_random_uuid() cần Postgres 13+/pgcrypto; migration không CREATE EXTENSION (alembic 004,005). Pattern pre-existing 001-003 — xử lý đồng nhất.
- 🟡 File 0-byte tạo Paper rỗng (use_cases.py:38-67). Tác động thấp.
- 🟡 Backend confirm không clamp year range đầy đủ (use_cases.py:78-109).
