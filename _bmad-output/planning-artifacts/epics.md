---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - '_bmad-output/planning-artifacts/prds/prd-C2-App-053-2026-06-11/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/planning-artifacts/ux-designs/ux-C2-App-053-2026-06-12/EXPERIENCE.md'
  - '_bmad-output/planning-artifacts/ux-designs/ux-C2-App-053-2026-06-12/DESIGN.md'
---

# C2-App-053 - Epic Breakdown

## Overview

Tài liệu này cung cấp bảng phân rã chi tiết các Epic và Story cho C2-App-053, chuyển hóa các yêu cầu từ PRD, thiết kế UX (nếu có) và yêu cầu kiến trúc thành các câu chuyện người dùng (stories) có thể triển khai.

## Requirements Inventory

### Functional Requirements

FR1: Đăng ký, Đăng nhập & Phân quyền Admin khởi tạo (Cấp JWT HttpOnly cookie, tài khoản đầu tiên tự động nhận vai trò admin, hiển thị Admin Settings Gear).
FR2: Quản lý Dự án Nghiên cứu (CRUD dự án, Sidebar hiển thị tối đa 10 dự án gần nhất, chuyển hướng đến trang Quản lý toàn bộ dự án tập trung).
FR3: Tìm kiếm bài báo đa nguồn (Gọi song song arXiv + Semantic Scholar với timeout 10s, khử trùng lặp qua DOI, xử lý tìm kiếm rộng BROAD_QUERY_THRESHOLD gợi ý phân ngành MECE bằng các nút bấm).
FR4: Ingestion bất đồng bộ & Hiển thị tiến trình chi tiết (FastAPI BackgroundTasks, stream trạng thái chi tiết qua SSE, lưu metadata Postgres và chunking parent-child pgvector).
FR5: Upload tài liệu thủ công & Trích xuất Metadata tự động (Upload PDF/DOCX cá nhân, LLM tự động trích xuất metadata và hiển thị Form "AI Suggested" để người dùng chỉnh sửa và xác nhận).
FR6: Chat tương tác thời gian thực với AI Agent (Chatbot cột phải, stream câu trả lời SSE, RAG qua Neo4j/pgvector, xem lại lịch sử chat qua popover Lịch sử trò chuyện).
FR7: Phát hiện Khoảng trống & Mâu thuẫn nghiên cứu (So sánh chéo các tài liệu, chỉ ra mâu thuẫn học thuật CONTRADICTS hoặc hạn chế Limitation, ghi nguồn trích dẫn cụ thể).
FR8: Kiểm chứng và xử lý lỗi trích dẫn ảo (Citation Verify Node trong LangGraph, kiểm định trích dẫn với CITATION_ERROR_THRESHOLD và CITATION_RETRY_LIMIT, thay thế nguồn ảo bằng 'Nguồn không xác định' hoặc gỡ bỏ).
FR9: Trực quan hóa mạng lưới bài báo & Phát hiện khoảng trống trực quan (Bản đồ tri thức Cytoscape.js tương tác, tích hợp chế độ Tìm khoảng trống nghiên cứu highlight đỏ viền mâu thuẫn hoặc vàng viền cô lập).
FR10: Tương tác với Thẻ trích dẫn (Click/hover thẻ trích dẫn hiện Tooltip thông tin metadata và đoạn text gốc từ database, có nút mở tệp gốc/tải xuống).
FR11: Cấu hình giới hạn tài liệu trong dự án (Admin cấu hình MAX_PAPERS_PER_PROJECT, hiển thị cảnh báo đỏ và vô hiệu hóa nạp tài liệu mới khi chạm ngưỡng).
FR12: Lưu trữ cấu hình động (Admin chỉnh sửa các tham số và lưu trực tiếp vào cơ sở dữ liệu Postgres mà không cần restart server).
FR13: Soạn thảo & Quản lý bản thảo tổng quan (Rich editor soạn thảo literature review, quản lý các bản thảo theo dự án, lưu nháp).
FR14: Xuất bản thảo và tài liệu trích dẫn (Bấm nút xuất tải về tệp ZIP chứa file báo cáo Markdown .md và file BibTeX/APA .bib).
FR15: Hỗ trợ định hướng người dùng theo trạng thái dự án (Chatbot tự động phân tích state snapshot: active_tab, document_count, has_draft để sinh gợi ý hành động Dynamic Quick Reply Buttons).

### NonFunctional Requirements

NFR1: Concurrency (Hỗ trợ 10 người dùng hoạt động đồng thời trên cấu hình VM tối thiểu 32GB RAM/6 vcores).
NFR2: Storage Limit (Giới hạn dung lượng tải lên tối đa 20MB cho mỗi tệp tài liệu cá nhân).
NFR3: Database Performance (pgvector HNSW index trên column embedding, phản hồi RAG query < 500ms khi DB dưới 100,000 dòng vector).
NFR4: Background Processing (FastAPI BackgroundTasks cho nạp file ngầm, queue worker arq giới hạn concurrency_limit=2, cấu hình OMP_NUM_THREADS=1, OPENBLAS_NUM_THREADS=1 để chống thrashing).

### Additional Requirements

- ARCH-1: VM Memory Constraints & Limits (Neo4j max 8GB - 5GB JVM Heap, 3GB Page Cache, arq worker 12GB, Postgres 3GB, Backend 2GB, Redis 1GB. Swap 16GB, vm.swappiness=10).
- ARCH-2: Soft-delete & Garbage Collection (Xóa mềm dự án cập nhật nhãn (:Deleted) trong Neo4j và sync_outbox. Cron job lúc 2h sáng quét xóa cứng dữ liệu đã xóa mềm quá 7 ngày).
- ARCH-3: Ticket-based SSE Auth (Frontend gọi POST /api/sse/ticket lấy ticket một lần, sau đó kết nối SSE qua GET /api/sse/stream?ticket=<ticket> để chống CSRF).
- ARCH-4: Event Catch-up & State Sync (SSE sử dụng ID đơn điệu tăng dần. Khi reconnect, gửi Last-Event-ID để Backend yield lại các sự kiện bị nhỡ).
- ARCH-5: External API Resiliency & Retry (Các cuộc gọi API ngoài bọc trong tenacity với Exponential Backoff Retry).
- ARCH-6: API Key Security (Mã hóa AES/Fernet các API Keys của người dùng trong PostgreSQL, phân lập rate limit qua LLMRouter).
- ARCH-7: Cytoscape.js Lazy Rendering (Giới hạn ban đầu 150 nodes và 300 edges, có API GET /api/projects/{project_id}/graph/nodes/{node_id}/expand mở rộng 1-hop tối đa 20 node mới).
- ARCH-8: Graph Sync Manager Event-driven (Postgres ghi event vào bảng sync_outbox, arq worker dùng SELECT ... FOR UPDATE SKIP LOCKED và Redis lock theo project_id với cơ chế Lock Heartbeat).
- ARCH-9: Secure Media Access (GET /api/projects/{project_id}/images/{image_name} kiểm tra JWT cookie và quyền workspace trước khi FileResponse từ thư mục bảo mật).

### UX Design Requirements

- UX-DR1: Three-Column Layout (Sidebar trái 240px CRUD dự án. Vùng giữa chứa thanh Tab ngang: Thư viện tài liệu, Bản đồ tri thức, Hỗ trợ viết tổng quan. Cột phải là Chatbot Panel co giãn 20-40% bằng cách kéo dải biên 4px, double-click reset về 25%, nút Toggle ẩn/hiện, nút Lịch sử chat popover và nút New Chat).
- UX-DR2: Language Toggle (Chuyển đổi VI | EN trên Header thay đổi static labels lập tức không cần reload).
- UX-DR3: Theme Toggle (Nút Mặt trăng/Mặt trời trên Header chuyển đổi Light Mode và Soft Dark Mode).
- UX-DR4: New User Onboarding (Onboarding gating khi chưa có dự án: form tạo nhanh bên trái, checklist 3 bước kèm ảnh động giới thiệu bên phải).
- UX-DR5: Guest Homepage & Pricing Table (Landing page dạng cuộn dọc có Hero banner, interactive simulator, pricing table gói Student/Researcher).
- UX-DR6: Interactive Citation Tooltip (Click/hover thẻ [1] hiện tooltip bo góc rounded.lg chứa text chunk gốc, thông tin metadata và nút tải PDF).
- UX-DR7: Knowledge Map Canvas Cytoscape.js (Hỗ trợ zoom/pan, Node Detail Card trượt ra góc trên bên phải canvas, chế độ Tìm khoảng trống tô viền nhấp nháy đỏ cho mâu thuẫn học thuật).
- UX-DR8: Interactive Demo Simulator (Mô phỏng 3 cột độc lập trên Landing page: tìm kiếm giả định 1.5s, Cytoscape canvas với node khoảng trống).
- UX-DR9: Centralized Project Management Page (Xem toàn bộ dự án dạng bảng, tìm kiếm, phân trang, CRUD nhanh).
- UX-DR10: Admin System Settings Page (Các trường input điều chỉnh tham số hệ thống động, bấm Lưu cập nhật DB tức thời).
- UX-DR11: manual Ingestion Metadata Form (Form hiển thị sau khi trích xuất tài liệu upload, các trường có badge "AI Suggested", người dùng xác nhận).
- UX-DR12: API Keys Management Panel (Bảng lưu API Key có masking chỉ hiện 4 số cuối, nút Test Connection hiện spinner, trạng thái Connected/Failed).

### FR Coverage Map

- **FR1 (Auth & Admin role):** Epic 1 - Workspace & Identity Foundation
- **FR2 (Workspace CRUD):** Epic 1 - Workspace & Identity Foundation
- **FR3 (Academic Search & Broad Query):** Epic 2 - Academic Search & Paper Ingestion Engine
- **FR4 (Async Ingestion & SSE):** Epic 2 - Academic Search & Paper Ingestion Engine
- **FR5 (Manual Upload & AI Metadata):** Epic 2 - Academic Search & Paper Ingestion Engine
- **FR6 (RAG Chat SSE):** Epic 3 - AI Chatbot, RAG & Citation Guardrail
- **FR7 (Research Gap & Contradiction):** Epic 4 - Knowledge Graph Synchronization & Exploration
- **FR8 (Citation Guardrail):** Epic 3 - AI Chatbot, RAG & Citation Guardrail
- **FR9 (Knowledge Map Cytoscape):** Epic 4 - Knowledge Graph Synchronization & Exploration
- **FR10 (Citation Interaction):** Epic 3 - AI Chatbot, RAG & Citation Guardrail
- **FR11 (Document Limit Admin):** Epic 2 - Academic Search & Paper Ingestion Engine
- **FR12 (Dynamic System Settings):** Epic 5 - Literature Review Workspace & Settings
- **FR13 (Literature Review Drafting):** Epic 5 - Literature Review Workspace & Settings
- **FR14 (Export ZIP):** Epic 5 - Literature Review Workspace & Settings
- **FR15 (Context-Aware Chat Guiding):** Epic 3 - AI Chatbot, RAG & Citation Guardrail

## Epic List

### Epic 1: Quản lý Không gian & Nền tảng Xác thực (Workspace & Identity Foundation)
Người dùng có thể đăng ký, đăng nhập và tạo lập các không gian nghiên cứu riêng biệt (Research Workspaces) để phân tách hoàn toàn dữ liệu ngữ cảnh RAG.
**FRs covered:** FR1, FR2.

### Epic 2: Công cụ Tìm kiếm & Ingestion Tài liệu (Academic Search & Paper Ingestion Engine)
Người dùng có thể tìm kiếm bài báo khoa học từ arXiv/Semantic Scholar và tự tải lên tệp PDF/DOCX cá nhân thông qua tiến trình nạp bất đồng bộ stream trạng thái SSE thời gian thực.
**FRs covered:** FR3, FR4, FR5, FR11.

### Epic 3: Trợ lý Chat RAG & Kiểm định Trích dẫn (AI Chatbot, RAG & Citation Guardrail)
Người dùng có thể trò chuyện học thuật với trợ lý RAG stream SSE, xem lịch sử chat và tương tác trực tiếp với các nguồn dẫn chứng thực tế được kiểm chứng để ngăn ngừa trích dẫn ảo.
**FRs covered:** FR6, FR8, FR10, FR15.

### Epic 4: Bản đồ Tri thức & Phân tích Đồ thị (Knowledge Graph Synchronization & Exploration)
Trực quan hóa mạng lưới liên kết trích dẫn/tác giả bằng Cytoscape.js và Neo4j, đồng thời hỗ trợ tìm khoảng trống/mâu thuẫn nghiên cứu nổi bật trên đồ thị.
**FRs covered:** FR7, FR9.

### Epic 5: Soạn thảo Tổng quan & Cấu hình Hệ thống (Literature Review Workspace & Settings)
Người dùng có thể viết literature review có hỗ trợ gợi ý của AI, xuất tệp nén ZIP (Markdown + BibTeX) và Quản trị viên cấu hình các giới hạn tham số động của hệ thống.
**FRs covered:** FR12, FR13, FR14.

---


## Epic 1: Quản lý Không gian & Nền tảng Xác thực (Workspace & Identity Foundation)

Epic này tập trung vào thiết lập hạ tầng cốt lõi về định danh người dùng và phân quyền, xây dựng giao diện Workspace 3 cột và cơ chế lưu trữ dự án độc lập.

### Story 1.1: [Backend] User Schema & Register API

Với vai trò là khách vãng lai,
Tôi muốn API đăng ký tài khoản,
Để thông tin của tôi được lưu vào cơ sở dữ liệu và tôi nhận quyền Admin nếu là người đầu tiên.

**Acceptance Criteria:**

**Given** payload đăng ký với Email/Password hợp lệ.
**When** gọi API `POST /api/auth/register`.
**Then** tạo bản ghi trong bảng `users` với mật khẩu đã mã hóa (bcrypt).
**And** gán `role='admin'` nếu là tài khoản đầu tiên trong DB, ngược lại gán `role='user'`. Trả về lỗi 400 nếu email tồn tại.

> 🔍 **Cách nghiệm thu trực quan:**
> Swagger UI. Gọi API `/api/auth/register`, nhập email/pass. Mở Database xem bảng `users` thấy tài khoản vừa tạo có role `admin`.

### Story 1.2: [Backend] Login API & JWT Session

Với vai trò là người dùng,
Tôi muốn API đăng nhập trả về HttpOnly Cookie,
Để tôi có thể truy cập các đường dẫn (route) bảo mật an toàn.

**Acceptance Criteria:**

**Given** email và mật khẩu đúng.
**When** gọi API `POST /api/auth/login`.
**Then** Backend cấp 1 token JWT chứa `user_id`.
**And** trả về client thông qua header `Set-Cookie` (`HttpOnly`, `SameSite=Lax`).
**And** chặn (401) các request bảo mật nếu không có cookie.

> 🔍 **Cách nghiệm thu trực quan:**
> Swagger UI. Gọi API `/login`. Mở DevTools (F12) -> Application -> Cookies, thấy cookie `access_token` được gán thành công.

### Story 1.3: [Frontend] Auth UI & First-Admin Logic

Với vai trò là khách vãng lai,
Tôi muốn giao diện Đăng ký / Đăng nhập,
Để tôi có thể điền thông tin đăng nhập vào hệ thống.

**Acceptance Criteria:**

**Given** trang Đăng nhập/Đăng ký.
**When** nhập sai mật khẩu, **Then** hiện Toast báo lỗi 401.
**When** nhập đúng, **Then** điều hướng vào Dashboard. Nếu là Admin, hiện biểu tượng Bánh răng (Settings) trên Header.

> 🔍 **Cách nghiệm thu trực quan:**
> Mở Web, điền form đăng nhập. Thấy chuyển trang vào Dashboard và có nút Bánh răng cài đặt góc phải trên cùng.

### Story 1.4: [Backend] Project CRUD APIs

Với vai trò là người dùng,
Tôi muốn các API tạo, đọc, sửa, xóa dự án,
Để tôi có nơi lưu trữ tài liệu tách biệt.

**Acceptance Criteria:**

**Given** request có chứa JWT cookie hợp lệ.
**When** gọi `POST /api/projects` với tên dự án.
**Then** lưu dự án vào DB kèm `user_id`.
**When** gọi `DELETE /api/projects/{id}`.
**Then** cập nhật `is_deleted = true` (soft delete) và ghi sự kiện vào `sync_outbox`.

> 🔍 **Cách nghiệm thu trực quan:**
> Swagger UI. Gọi POST tạo dự án, kiểm tra DB thấy dự án mới được tạo có liên kết đúng với `user_id`.

### Story 1.5: [Frontend] Project Sidebar & Creation Modal

Với vai trò là người dùng,
Tôi muốn thanh Sidebar bên trái hiển thị danh sách dự án,
Để tôi dễ dàng chọn và tạo dự án mới.

**Acceptance Criteria:**

**Given** đang ở màn hình Dashboard.
**When** nhìn sang Sidebar trái.
**Then** thấy danh sách tối đa 10 dự án gần nhất.
**When** bấm nút "Tạo dự án mới", **Then** hiển thị Modal nhập tên dự án. Bấm "Lưu" gọi API 1.4 và Sidebar cập nhật lập tức.

> 🔍 **Cách nghiệm thu trực quan:**
> Bấm "Tạo dự án mới", nhập tên, bấm Lưu. Ngay lập tức Sidebar bên trái xuất hiện dự án mới mà không cần F5 trang.

### Story 1.6: [Frontend] Centralized Project Management Table

Với vai trò là người dùng,
Tôi muốn trang quản lý toàn bộ dự án dạng bảng,
Để tôi có thể tìm kiếm và quản lý số lượng lớn dự án.

**Acceptance Criteria:**

**Given** chọn mục "Tất cả dự án" ở Sidebar.
**When** màn hình hiển thị.
**Then** load bảng danh sách tất cả dự án có phân trang.
**And** có ô tìm kiếm theo tên. Có nút Xóa dự án (hiện popup xác nhận).

> 🔍 **Cách nghiệm thu trực quan:**
> Web UI. Thấy bảng danh sách dự án. Bấm icon Thùng rác, hiện popup "Bạn có chắc chắn?". Bấm OK, dòng đó biến mất.

---

## Epic 2: Công cụ Tìm kiếm & Ingestion Tài liệu (Academic Search & Paper Ingestion Engine)

Epic này phát triển công cụ tìm kiếm bài báo khoa học và quản lý quy trình nạp tài liệu tự động và thủ công dưới dạng bất đồng bộ.

### Story 2.1: [Backend] Manual Upload & LLM Metadata Extraction

Với vai trò là người dùng,
Tôi muốn upload file PDF tự có của tôi,
Để AI tự động trích xuất tiêu đề, tác giả.

**Acceptance Criteria:**

**Given** file PDF tải lên qua `POST /api/documents/upload`.
**When** Backend nhận file.
**Then** lưu file vào ổ cứng/s3. Đọc text 2 trang đầu.
**And** gọi LLM prompt trích xuất JSON `{title, authors, abstract, year}`.
**And** trả về client JSON này.

> 🔍 **Cách nghiệm thu trực quan:**
> Swagger UI. Upload file PDF bất kỳ. Thấy API trả về JSON chứa đúng tên bài báo và tác giả lấy từ trang bìa PDF.

### Story 2.2: [Frontend] AI Suggested Metadata Form

Với vai trò là người dùng,
Tôi muốn xác nhận thông tin AI trích xuất trước khi lưu,
Để tôi có thể sửa nếu AI nhận diện sai.

**Acceptance Criteria:**

**Given** sau khi upload file PDF thành công ở Story 2.1.
**When** Frontend nhận JSON metadata.
**Then** bật Modal Form chứa các trường dữ liệu. Gắn badge "AI Suggested".
**When** người dùng sửa form và bấm "Xác nhận".
**Then** gọi API đưa file vào luồng Ingestion Task (Story 2.3).

> 🔍 **Cách nghiệm thu trực quan:**
> Bấm nút Upload, chọn file. Chờ 2s, bật lên 1 cửa sổ có điền sẵn Tên bài báo. Sửa lại tên theo ý muốn, bấm OK.

### Story 2.3: [Backend] Background Ingestion Task Foundation

Với vai trò là hệ thống,
Tôi muốn một worker queue chạy ngầm để xử lý tài liệu,
Để API không bị block khi xử lý tệp tin nặng.

**Acceptance Criteria:**

**Given** FastAPI nhận lệnh nạp tài liệu.
**When** đẩy job vào queue `arq`.
**Then** API trả về ngay `{"task_id": "123"}`.
**And** Worker ngầm bắt đầu tải metadata (nếu từ tìm kiếm) hoặc sử dụng metadata đã xác nhận, thực hiện chia chunk parent-child và lưu vào `pgvector`.

> 🔍 **Cách nghiệm thu trực quan:**
> Terminal. Xem log của Worker thấy in ra "Processing task 123... Done" trong khi API trả về kết quả lập tức.

### Story 2.4: [Backend] SSE Progress Streaming

Với vai trò là người dùng,
Tôi muốn API stream trạng thái tiến trình nạp tài liệu,
Để giao diện (Frontend) có thể vẽ thanh tiến trình.

**Acceptance Criteria:**

**Given** Worker đang chạy.
**When** Worker cập nhật trạng thái (ví dụ: 10%, 50%, "Đang chia chunk").
**Then** cập nhật trạng thái vào Redis.
**When** Frontend kết nối `GET /api/sse/tasks/{id}`.
**Then** Backend yield các event SSE tuân theo schema cố định sau:
* Event tiến trình:
```json
{
  "event": "progress",
  "task_id": "123",
  "status": "chunking",
  "percent": 50,
  "message": "Đang chia chunk"
}
```
* Event hoàn thành:
```json
{
  "event": "completed",
  "task_id": "123",
  "document_id": "doc_456"
}
```

> 🔍 **Cách nghiệm thu trực quan:**
> Dùng lệnh Terminal: `curl -N http://localhost:8000/api/sse/tasks/123`. Thấy console liên tục in ra các event SSE đúng định dạng JSON như trên cho đến khi hoàn thành.

### Story 2.5: [Frontend] Ingestion Progress UI

Với vai trò là người dùng,
Tôi muốn thấy thanh tiến trình khi nạp tài liệu,
Để tôi biết hệ thống đang làm gì.

**Acceptance Criteria:**

**Given** người dùng bấm nút "Xác nhận" (từ Form Metadata) hoặc "Thêm vào dự án" (từ Search).
**When** nhận sự kiện SSE từ API 2.4.
**Then** hiển thị Toast hoặc thanh Progress Bar chạy từ 0 đến 100% dựa trên trường `percent` và hiển thị nội dung `message`.
**When** nhận event `completed`, ẩn progress bar và hiển thị thông báo thành công.

> 🔍 **Cách nghiệm thu trực quan:**
> Web UI. Xác nhận form upload, thấy một thanh tải chạy ở góc phải màn hình hiển thị phần trăm và trạng thái, chạy xong 100% thì báo thành công và cập nhật thư viện.

### Story 2.6: [Backend] External Search Clients (arXiv & Semantic Scholar)

Với vai trò là hệ thống,
Tôi muốn tích hợp API tìm kiếm của arXiv và Semantic Scholar,
Để có thể lấy dữ liệu thô từ các nguồn học thuật.

**Acceptance Criteria:**

**Given** từ khóa tìm kiếm.
**When** gọi function adapter.
**Then** HTTP Client gửi request đến arXiv và Semantic Scholar với timeout 10s.
**And** bọc bằng Tenacity (Retry) khi gặp lỗi mạng.

> 🔍 **Cách nghiệm thu trực quan:**
> Chạy script test nhỏ. Nhập từ khóa "LLM", thấy console in ra log trả về danh sách từ arXiv và Semantic Scholar.

### Story 2.7: [Backend] Parallel Search & Deduplication API

Với vai trò là người dùng,
Tôi muốn API tìm kiếm tổng hợp và loại bỏ bài báo trùng lặp,
Để kết quả trả về sạch sẽ và nhanh chóng.

**Acceptance Criteria:**

**Given** từ khóa tìm kiếm.
**When** gọi `GET /api/search?q=keyword`.
**Then** Backend gọi đồng thời (asyncio.gather) cả 2 hàm ở Story 2.6.
**And** khử trùng lặp kết quả dựa trên DOI.
**And** trả về JSON mảng kết quả.

> 🔍 **Cách nghiệm thu trực quan:**
> Swagger UI. Gọi API `/search`, thấy thời gian phản hồi nhanh (< 2s) và trong list kết quả không có 2 bài báo nào trùng DOI.

### Story 2.8: [Frontend] Search UI & Broad Query Detection

Với vai trò là người dùng,
Tôi muốn ô tìm kiếm và giao diện hiển thị kết quả,
Để tôi có thể chọn bài báo cần thêm vào dự án.

**Acceptance Criteria:**

**Given** ô tìm kiếm ở tab Thư viện.
**When** gõ từ khóa "Machine Learning" (truy vấn rất rộng).
**Then** Backend trả về cờ `is_broad_query = true` và danh sách gợi ý phân ngành MECE (ví dụ: "NLP", "Computer Vision").
**And** Frontend hiển thị các nút gợi ý này để người dùng bấm vào thu hẹp tìm kiếm. Hiển thị danh sách thẻ bài báo.

> 🔍 **Cách nghiệm thu trực quan:**
> Web UI. Gõ "AI", bấm tìm. Thấy kết quả hiện ra kèm theo 3-4 nút bấm gợi ý phân ngành nhỏ hơn ở trên cùng.

### Story 2.9: [Backend] Document Limit Enforcement

Với vai trò là Quản trị viên (Admin),
Tôi muốn giới hạn số tài liệu trong 1 dự án theo biến môi trường/cấu hình,
Để máy chủ (server) không bị quá tải.

**Acceptance Criteria:**

**Given** cấu hình `MAX_PAPERS=15`.
**When** dự án đã có 15 tài liệu.
**Then** mọi request Ingestion (Search thêm hoặc Upload thêm) vào dự án này đều trả về HTTP 403.
**And** Frontend vô hiệu hóa nút "Thêm" và hiện cảnh báo giới hạn.

> 🔍 **Cách nghiệm thu trực quan:**
> Chỉnh config `MAX_PAPERS=1`. Thêm 1 bài báo. Cố gắng thêm bài báo thứ 2, thấy hiển thị thông báo lỗi màu đỏ "Đã đạt giới hạn".

---

## Epic 3: Trợ lý Chat RAG & Kiểm định Trích dẫn (AI Chatbot, RAG & Citation Guardrail)

Epic này phát triển chatbot AI kết hợp RAG và bộ lọc Citation Guardrail chống trích dẫn ảo.

### Story 3.1: [Backend] Chat Session DB & Core APIs

Với vai trò là người dùng,
Tôi muốn tạo phiên chat mới và xem lịch sử chat,
Để tôi lưu lại mạch suy nghĩ.

**Acceptance Criteria:**

**Given** DB có bảng `chat_threads` và `chat_messages`.
**When** gọi `POST /api/chat/threads`.
**Then** tạo thread mới cho user.
**When** gọi `GET /api/chat/threads/{id}/messages`.
**Then** trả về danh sách tin nhắn.

> 🔍 **Cách nghiệm thu trực quan:**
> Dùng Swagger UI gọi POST tạo thread, sau đó gọi GET lấy message (list rỗng). Không cần đụng đến UI.

### Story 3.2: [Frontend] Chat UI Shell & History Sidebar

Với vai trò là người dùng,
Tôi muốn giao diện khung chat và danh sách lịch sử,
Để tôi thao tác được với các phiên trò chuyện cũ.

**Acceptance Criteria:**

**Given** trang thư viện/dashboard.
**When** bấm biểu tượng Lịch sử.
**Then** Popover mở ra hiển thị list threads lấy từ API 3.1.
**When** bấm vào 1 thread, **Then** load tin nhắn ra khu vực chat chính.

> 🔍 **Cách nghiệm thu trực quan:**
> Trình duyệt. Bấm biểu tượng Lịch sử. Thấy danh sách. Bấm vào tên, màn hình chính thay đổi (có thể rỗng nếu chưa chat).

### Story 3.3: [Backend] LangGraph Foundation & Mock RAG

Với vai trò là hệ thống,
Tôi muốn bộ khung LangGraph khởi tạo,
Để các tính năng RAG phức tạp có nền móng chạy thử.

**Acceptance Criteria:**

**Given** Endpoint `POST /api/chat/invoke` (chưa phải SSE).
**When** gửi câu hỏi.
**Then** Backend chạy LangGraph Node. Thay vì gọi Vector DB, dùng Dummy Retriever trả về chuỗi text fix cứng.
**And** trả về câu trả lời JSON đầy đủ ngay lập tức.

> 🔍 **Cách nghiệm thu trực quan:**
> Swagger UI. Gọi API `/invoke` với tin nhắn bất kỳ. Nhận về JSON có chữ "Đây là câu trả lời mock từ hệ thống".

### Story 3.4: [Backend] SSE Chat Streaming API

Với vai trò là người dùng,
Tôi muốn gửi tin nhắn và nhận câu trả lời dưới dạng luồng sự kiện,
Để tôi không phải chờ quá lâu cho câu trả lời dài.

**Acceptance Criteria:**

**Given** tin nhắn của người dùng trong một thread.
**When** gọi `POST /api/chat/threads/{thread_id}/messages` với Body `{ "message": "..." }`.
**Then** lưu tin nhắn vào database, khởi tạo luồng xử lý RAG và trả về JSON `{"run_id": "run_xxx"}` ngay lập tức.
**When** Frontend kết nối `GET /api/chat/stream?run_id=run_xxx`.
**Then** Backend kết nối SSE để yield từng ký tự câu trả lời sinh ra (giả lập hoặc thực tế qua RAG Graph) bằng `Server-Sent Events` mỗi 50ms.

> 🔍 **Cách nghiệm thu trực quan:**
> Swagger UI gọi POST gửi tin nhắn nhận `run_id`. Dùng Terminal: `curl -N http://localhost:8000/api/chat/stream?run_id=run_xxx`. Thấy console liên tục in ra từng dòng `data: {"chunk": "..."}`.

### Story 3.5: [Frontend] Typewriter UI & SSE Receiver

Với vai trò là người dùng,
Tôi muốn thấy chữ gõ ra từ từ trên giao diện,
Để tôi biết AI đang gõ phản hồi.

**Acceptance Criteria:**

**Given** người dùng gửi tin nhắn trên UI.
**When** gọi API POST gửi tin nhắn và nhận được `run_id`.
**Then** thiết lập kết nối `GET /api/chat/stream?run_id=...`.
**And** hiển thị icon "AI is thinking..." cho đến khi nhận được chunk đầu tiên.
**And** chữ xuất hiện dần dần thành hiệu ứng Typewriter. Cập nhật thanh cuộn tự động (auto-scroll).

> 🔍 **Cách nghiệm thu trực quan:**
> Mở Web, gõ tin nhắn, thấy icon xoay xoay rồi chữ hiện dần từng từ mượt mà, cuộn xuống dần nếu dài.

### Story 3.6: [Backend] Context-Aware Suggestion API

Với vai trò là người dùng,
Tôi muốn AI gợi ý hành động tiếp theo,
Để tôi không bị bối rối.

**Acceptance Criteria:**

**Given** payload `{"active_tab": "library", "document_count": 0}`.
**When** gọi `POST /api/chat/suggestions`.
**Then** LLM Adapter (mock) sinh mảng 3 chuỗi text (ví dụ: `["Upload file PDF", "Search paper", "Help"]`).

> 🔍 **Cách nghiệm thu trực quan:**
> Swagger UI. Truyền JSON `document_count=0`. Xem mảng trả về có đúng gợi ý yêu cầu tải lên tài liệu không.

### Story 3.7: [Frontend] Quick Reply Action UI

Với vai trò là người dùng,
Tôi muốn bấm nút gợi ý dưới khung chat để điều hướng nhanh,
Để tôi đỡ phải tìm nút thủ công.

**Acceptance Criteria:**

**Given** mảng text gợi ý từ API 3.6.
**When** UI hiển thị thành các nút pill/chip.
**When** click vào nút `"Upload file PDF"`.
**Then** Frontend điều hướng sang tab Library và mở sẵn Modal Upload.

> 🔍 **Cách nghiệm thu trực quan:**
> Trên Web, thấy 3 nút bấm dưới ô chat. Bấm 1 nút, hệ thống tự động chuyển sang tab Library và hiển thị Modal tương ứng.

### Story 3.8: [Backend] Citation Guardrail Node Logic

Với vai trò là hệ thống,
Tôi muốn một node chạy Python Regex để kiểm duyệt số trích dẫn,
Để chống trích dẫn ảo (hallucination).

**Acceptance Criteria:**

**Given** câu trả lời chứa các thẻ trích dẫn dạng `[id]` sinh ra bởi LLM.
**When** đi qua node Guardrail.
**Then** hệ thống kiểm chứng danh sách các ID trích dẫn xuất hiện trong câu trả lời đối chiếu với danh sách các chunk ID thực tế được trả về bởi bộ truy vấn (retriever) cho câu hỏi đó (`valid_citation_ids = list of chunk IDs returned by retriever for the current answer`).
**And** nếu bất kỳ thẻ trích dẫn `[id]` nào không nằm trong danh sách `valid_citation_ids`, thay thế thẻ đó bằng `[Nguồn không xác định]` hoặc gỡ bỏ.
**Example**: LLM sinh `"Apple is red [1] và blue [99]"` nhưng `valid_citation_ids` chỉ có `[1]`. Node Guardrail biến đổi kết quả thành `"Apple is red [1] và blue [Nguồn không xác định]"`.

> 🔍 **Cách nghiệm thu trực quan:**
> Chạy script test hoặc Swagger. Truyền text chứa `[99]` và giả lập `valid_citation_ids=[1]`. Thấy API trả về text đã bị che thành chữ cảnh báo mà không cần giao diện phức tạp.

### Story 3.9: [Backend] Citation Detail Fetch API

Với vai trò là hệ thống,
Tôi muốn API trả về nguyên văn đoạn text gốc của trích dẫn,
Để giao diện (Frontend) có cái để hiển thị.

**Acceptance Criteria:**

**Given** `id=1`.
**When** gọi `GET /api/citations/1`.
**Then** truy vấn CSDL lấy bản ghi chunk ID=1.
**And** trả về JSON `{ "title": "Paper A", "text": "Apple color is red..." }`.

> 🔍 **Cách nghiệm thu trực quan:**
> Gọi API qua Swagger. Truyền ID 1. Nhận về JSON đoạn văn bản.

### Story 3.10: [Frontend] Interactive Citation Tooltip UI

Với vai trò là người dùng,
Tôi muốn rê chuột vào số `[1]` để xem trích dẫn,
Để không làm gián đoạn mạch đọc.

**Acceptance Criteria:**

**Given** đoạn chat hiện số `[1]` là một thẻ HTML có class `.citation-link`.
**When** người dùng hover chuột vào.
**Then** Frontend gọi API 3.9 và bật popover nhỏ nổi lên chứa dòng chữ "Apple color is red".

> 🔍 **Cách nghiệm thu trực quan:**
> Web UI. Rê chuột vào thẻ màu xanh `[1]`. Một tooltip đen hiện lên chứa 2 dòng chữ. Di chuột ra ngoài thì tooltip biến mất.

---

## Epic 4: Bản đồ Tri thức & Phân tích Đồ thị (Knowledge Graph Synchronization & Exploration)

Epic này trực quan hóa và đồng bộ hóa mạng lưới trích dẫn giữa các bài báo sử dụng Neo4j và Cytoscape.js.

### Story 4.1: [Backend] Neo4j Connection & Base Cypher

Với vai trò là hệ thống,
Tôi muốn tạo driver kết nối Neo4j,
Để tôi có thể chạy thử các lệnh Cypher MERGE.

**Acceptance Criteria:**

**Given** thông tin kết nối Neo4j.
**When** Backend start lên.
**Then** tạo Neo4j Driver pool.
**And** cung cấp API giả lập `POST /api/neo4j/test` để test chạy lệnh Cypher tạo Node tĩnh.

> 🔍 **Cách nghiệm thu trực quan:**
> Swagger UI. Gọi API `/neo4j/test`. Sau đó mở trình duyệt Neo4j Browser (localhost:7474), xem có Node nào vừa sinh ra không.

### Story 4.2: [Backend] Outbox Worker Foundation

Với vai trò là hệ thống,
Tôi muốn một worker lắng nghe hàng đợi outbox và dùng Redis Lock,
Để tôi có bộ khung an toàn để chạy tiến trình đồng bộ.

**Acceptance Criteria:**

**Given** Worker Arq đang chạy.
**When** nhận trigger.
**Then** lấy Lock trên Redis. Print log "Lock acquired".
**And** thả Lock sau khi xong.

> 🔍 **Cách nghiệm thu trực quan:**
> Terminal. Trigger worker 2 lần liên tục. Thấy worker 1 báo "Lock acquired", worker 2 báo "Locked, skip".

### Story 4.3: [Backend] Event-Driven Graph Sync

Với vai trò là hệ thống,
Tôi muốn nối worker 4.2 với Cypher 4.1,
Để dữ liệu đẩy từ Postgres sang Neo4j thật sự.

**Acceptance Criteria:**

**Given** một record `sync_outbox` xuất hiện trong Postgres.
**When** Worker quét được.
**Then** dịch dữ liệu đó sang lệnh MERGE và lưu thành công vào Neo4j.

> 🔍 **Cách nghiệm thu trực quan:**
> Insert 1 dòng thủ công vào bảng `sync_outbox` trong DBeaver. Vài giây sau mở Neo4j xem node có tự mọc lên không.

### Story 4.4: [Backend] Graph Garbage Collection

Với vai trò là hệ thống,
Tôi muốn cronjob dọn rác,
Để dữ liệu không phình to.

**Acceptance Criteria:**

**Given** tài liệu đã bị xóa mềm `is_deleted=true` quá 7 ngày.
**When** Cronjob chạy lúc 2h sáng.
**Then** xóa hẳn khỏi Postgres và Neo4j.

> 🔍 **Cách nghiệm thu trực quan:**
> Sửa data thành ngày xóa là 1 tháng trước. Chạy thủ công Cronjob. Reload DBeaver thấy data biến mất.

### Story 4.5: [Frontend] Cytoscape.js Foundation

Với vai trò là người dùng,
Tôi muốn xem màn hình vẽ đồ thị cơ bản,
Để tôi có không gian trực quan.

**Acceptance Criteria:**

**Given** truy cập tab Bản đồ.
**When** component render.
**Then** vẽ 1 đồ thị mock tĩnh có 3 node và 2 edge bằng Cytoscape. Có thể zoom/kéo thả.

> 🔍 **Cách nghiệm thu trực quan:**
> Mở Web, vào tab Bản đồ. Thấy 3 nút tròn (nodes) nối với nhau. Rê chuột kéo thả để di chuyển các nút tròn dễ dàng.

### Story 4.6: [Backend] Lazy Graph Expand API

Với vai trò là người dùng,
Tôi muốn API lấy node lân cận,
Để tôi có thể xem các trích dẫn của 1 nút (node).

**Acceptance Criteria:**

**Given** ID node.
**When** gọi `GET /api/graph/expand/{id}`.
**Then** truy vấn Neo4j lấy 1-hop trả về JSON chuẩn cytoscape.

> 🔍 **Cách nghiệm thu trực quan:**
> Gọi API qua Swagger. Nhận về danh sách JSON Nodes, Edges.

### Story 4.7: [Frontend] Interactive Graph UI (Expand & Details)

Với vai trò là người dùng,
Tôi muốn tương tác đồ thị thật,
Để tôi khám phá được mạng lưới.

**Acceptance Criteria:**

**Given** đồ thị đang hiển thị.
**When** double-click vào node.
**Then** gọi API 4.6, vẽ thêm node lân cận.
**When** bật nút highlight.
**Then** tô viền đỏ cho node mâu thuẫn.

> 🔍 **Cách nghiệm thu trực quan:**
> Trên Web. Nhấp đúp chuột trái vào 1 nút tròn (node), thấy nó hiển thị thêm các nút con liên kết.

---

## Epic 5: Soạn thảo Tổng quan & Cấu hình Hệ thống (Overview Writing & Settings)

Epic này phát triển không gian soạn thảo nháp, xuất báo cáo và trang cấu hình hệ thống dành cho Admin.

### Story 5.1: [Backend] Draft Versioning API

Với vai trò là người dùng,
Tôi muốn API CRUD bản nháp,
Để bản nháp của tôi được lưu vào cơ sở dữ liệu.

**Acceptance Criteria:**

**Given** text bản nháp.
**When** gọi `POST /api/drafts`.
**Then** lưu vào DB `drafts`.

> 🔍 **Cách nghiệm thu trực quan:**
> Swagger UI. Gọi POST. Kiểm tra DB thấy text.

### Story 5.2: [Frontend] Rich Text Editor Foundation

Với vai trò là người dùng,
Tôi muốn bộ soạn thảo chữ,
Để tôi gõ được văn bản in đậm, in nghiêng.

**Acceptance Criteria:**

**Given** trang Soạn thảo.
**When** mở trang.
**Then** render trình soạn thảo (Tiptap/Quill). Gõ chữ được.

> 🔍 **Cách nghiệm thu trực quan:**
> Mở web, gõ chữ, bôi đen, bấm Ctrl+B thấy chữ in đậm.

### Story 5.3: [Frontend] Auto-save & History UI

Với vai trò là người dùng,
Tôi muốn hệ thống tự lưu mỗi 10s,
Để tôi không sợ mất dữ liệu.

**Acceptance Criteria:**

**Given** đang gõ text.
**When** dừng tay 10s.
**Then** tự động gọi API 5.1 lưu. Chữ "Đã lưu" nhấp nháy góc phải.

> 🔍 **Cách nghiệm thu trực quan:**
> Web UI. Gõ xong ngừng gõ chữ/thao tác trong 10 giây, nhìn góc phải thấy dòng chữ trạng thái "Đang lưu..." hiện lên.

### Story 5.4: [Backend] ZIP Export API

Với vai trò là người dùng,
Tôi muốn API xuất file,
Để tôi tải được tệp tin về máy.

**Acceptance Criteria:**

**Given** ID bản nháp.
**When** gọi `GET /api/drafts/{id}/export`.
**Then** Backend gom text + bib, nén thành `export.zip`, trả về dạng File Stream.

> 🔍 **Cách nghiệm thu trực quan:**
> Swagger UI. Gọi GET. Trình duyệt tự tải 1 file `export.zip` về, mở ra xem có 2 file bên trong không.

### Story 5.5: [Frontend] Export Button

Với vai trò là người dùng,
Tôi muốn bấm nút để tải,
Để không cần gọi API.

**Acceptance Criteria:**

**Given** góc trái màn hình soạn thảo.
**When** bấm "Xuất file".
**Then** tự động gọi API 5.4 và tải ZIP về.

> 🔍 **Cách nghiệm thu trực quan:**
> Bấm nút trên giao diện, trình duyệt hiển thị thanh download tải file.

### Story 5.6: [FE+BE] Admin Settings Management

Với vai trò là Quản trị viên (Admin),
Tôi muốn thay đổi cấu hình giới hạn,
Để hệ thống linh hoạt.

**Acceptance Criteria:**

**Given** trang Settings.
**When** sửa ô `MAX_PAPERS` = 10, bấm Lưu.
**Then** gọi API PATCH `/api/settings` lưu DB. User thường sửa sẽ báo 403.

> 🔍 **Cách nghiệm thu trực quan:**
> Đăng nhập Admin, đổi số 15 thành 10 trên UI. Mở cửa sổ ẩn danh đăng nhập User thường thì không thấy menu đó.

