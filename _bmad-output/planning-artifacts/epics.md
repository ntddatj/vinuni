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

This document provides the complete epic and story breakdown for C2-App-053, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

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

NFR1: Concurrency (Hỗ trợ 50 người dùng hoạt động đồng thời trên cấu hình VM tối thiểu 32GB RAM/6 vcores).
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

### Story 1.1: Đăng ký tài khoản & Phân quyền Admin khởi tạo (User Registration & Initial Admin Assignment)

As a khách vãng lai,
I want đăng ký tài khoản mới bằng Email và Mật khẩu,
So that tôi có thể đăng nhập vào hệ thống và tự động nhận quyền Admin nếu là tài khoản đăng ký đầu tiên.

**Acceptance Criteria:**

**Given** người dùng đang ở giao diện đăng ký tài khoản và nhập email chưa tồn tại cùng mật khẩu hợp lệ (tối thiểu 8 ký tự).
**When** nhấn nút "Đăng ký".
**Then** hệ thống mã hóa mật khẩu bằng `bcrypt` và lưu trữ tài khoản vào bảng `users` trong PostgreSQL.
**And** chuyển hướng người dùng vào giao diện Dashboard.

**Given** bảng `users` trong cơ sở dữ liệu hoàn toàn trống (chưa có tài khoản nào).
**When** người dùng đầu tiên đăng ký tài khoản thành công.
**Then** hệ thống tự động gán vai trò của họ là `role = 'admin'`.
**And** các tài khoản đăng ký sau đó nhận vai trò mặc định là `role = 'user'`.

**Given** email `researcher@example.com` đã tồn tại trong database.
**When** người dùng cố gắng đăng ký tài khoản mới với email này.
**Then** Backend trả về lỗi `HTTP 400 Bad Request`.
**And** Frontend hiển thị thông báo cảnh báo email đã được sử dụng.

### Story 1.2: Đăng nhập & Xác thực bằng HttpOnly Cookie (User Login & JWT HttpOnly Cookie Session)

As a người dùng đã đăng ký,
I want đăng nhập bằng Email và Mật khẩu chính xác,
So that hệ thống cấp mã JWT lưu trong HttpOnly Cookie để duy trì phiên làm việc an toàn.

**Acceptance Criteria:**

**Given** người dùng nhập đúng Email và Mật khẩu của tài khoản đã đăng ký.
**When** nhấn nút "Đăng nhập".
**Then** Backend tạo mã JWT (payload chứa user_id và role) và trả về qua set-cookie header.
**And** cookie được cấu hình với thuộc tính `HttpOnly`, `SameSite=Lax`, tên `access_token` có thời hạn 24 giờ.
**And** Frontend chuyển hướng người dùng vào giao diện Dashboard và hiển thị gear cài đặt hệ thống ở Header nếu người dùng có quyền Admin.

**Given** người dùng nhập sai mật khẩu hoặc email chưa đăng ký.
**When** nhấn nút "Đăng nhập".
**Then** Backend trả về mã lỗi `HTTP 401 Unauthorized`.
**And** Frontend hiển thị Banner thông báo lỗi đăng nhập màu đỏ trên giao diện.

**Given** người dùng đang ở giao diện Dashboard.
**When** click nút "Đăng xuất" ở Header.
**Then** Backend xóa cookie `access_token` trên trình duyệt.
**And** Frontend điều hướng người dùng về Landing Page của khách vãng lai.

### Story 1.3: Quy trình Onboarding & Khởi tạo dự án đầu tiên (Onboarding & First Project Gating)

As a người dùng mới chưa có dự án nào,
I want hệ thống hiển thị màn hình Onboarding khóa (gating) yêu cầu tạo dự án đầu tiên kèm xem hướng dẫn,
So that tôi được định hướng bắt đầu dự án mà không bị bối rối bởi giao diện trống.

**Acceptance Criteria:**

**Given** người dùng đăng nhập thành công và hệ thống kiểm tra số lượng dự án của người dùng bằng 0.
**When** người dùng truy cập trang chủ Workspace.
**Then** hệ thống hiển thị màn hình Onboarding bao phủ toàn bộ vùng làm việc.
**And** hiển thị biểu mẫu tạo dự án nhanh bên trái và checklist hướng dẫn sử dụng cùng slide giới thiệu bên phải.

**Given** người dùng điền đầy đủ Tên dự án và Mô tả ngắn hợp lệ.
**When** click nút "Tạo dự án" (đã đổi sang màu xanh Cobalt).
**Then** hệ thống tạo dự án mới trong PostgreSQL liên kết với `user_id`.
**And** chuyển hướng người dùng vào giao diện làm việc 3 cột đầy đủ của dự án vừa tạo.

### Story 1.4: CRUD Dự án nghiên cứu & Left Sidebar điều hướng (Workspace Management & Sidebar CRUD)

As a người dùng đang hoạt động,
I want tạo mới, chỉnh sửa tên và xóa dự án trực tiếp trên Sidebar trái hoặc trang quản lý tập trung,
So that tôi có thể dễ dàng tổ chức các không gian nghiên cứu riêng biệt.

**Acceptance Criteria:**

**Given** người dùng có danh sách nhiều dự án đã tạo.
**When** hiển thị Sidebar bên trái.
**Then** hiển thị tối đa 10 dự án được sử dụng gần nhất.
**And** hiển thị thanh cuộn dọc (scrollbar) mượt mà khi danh sách Sidebar vượt màn hình.
**And** hiển thị nút "Xem tất cả" dưới danh sách dự án.

**Given** người dùng di chuột (hover) qua một dòng dự án trên Sidebar.
**When** click vào biểu tượng Sửa (edit) hoặc Xóa (delete).
**Then** hành động sửa cho phép đổi tên dự án inline.
**And** hành động xóa mở Modal xác nhận và cập nhật trạng thái xóa mềm (Soft-Delete) sang bảng `sync_outbox`.

**Given** người dùng click nút "Xem tất cả" dưới Sidebar.
**When** chuyển sang Trang Quản lý toàn bộ dự án tập trung.
**Then** hiển thị danh sách dự án đầy đủ dạng bảng, hỗ trợ tìm kiếm theo tên/mô tả và phân trang số ở góc dưới bên phải.

### Story 1.5: Giao diện 3 Cột & Bộ chuyển đổi ngôn ngữ/chủ đề (Three-Column Layout & Global Utilities)

As a người dùng hệ thống,
I want làm việc trên bố cục 3 cột đồng bộ, có thể ẩn chatbot, đổi ngôn ngữ VI/EN hoặc Light/Dark theme,
So that tôi có trải nghiệm làm việc tối ưu và cá nhân hóa.

**Acceptance Criteria:**

**Given** Khung Chatbot AI bên phải đang hiển thị ở chiều rộng mặc định 25%.
**When** kéo dải biên 4px (hitbox 10px) hoặc click nút Toggle ẩn chat ở Header.
**Then** chiều rộng khung chat thay đổi tương ứng từ 20-40%, hoặc thu gọn về 0.
**And** double-click vào đường biên resets chiều rộng về 25% mặc định.

**Given** người dùng click nút chuyển đổi ngôn ngữ `VI | EN` ở Header.
**When** chọn chuyển đổi.
**Then** toàn bộ nhãn tĩnh trên UI (tab ngang, nút sidebar, menu cài đặt) được dịch tức thời mà không cần reload trang.

**Given** người dùng click biểu tượng mặt trăng/mặt trời trên Header.
**When** thay đổi chủ đề.
**Then** hệ thống chuyển đổi class CSS từ Light Mode sang Soft Dark Mode (màu xám phiến đá dịu mắt) và ngược lại.

**Given** bài báo chứa biểu đồ/hình ảnh lưu trong thư mục `/app/data/images/`.
**When** Frontend truy cập URL `GET /api/projects/{project_id}/images/{image_name}`.
**Then** Backend kiểm chứng access_token cookie và quyền sở hữu dự án (`project_id`) trước khi trả về FileResponse.

---

### Chiến lược Kiểm thử cho Epic 1 (Epic 1 Testing Strategy)

Do Epic 1 hoàn toàn bao gồm các thành phần nội bộ (PostgreSQL, JWT Cookie, REST API), chúng ta sẽ chuẩn bị các kịch bản test như sau:
1. **Mock Database Session:** Sử dụng `pytest` fixtures để khởi tạo và rollback database PostgreSQL sau mỗi test case, đảm bảo độc lập dữ liệu.
2. **FastAPI Integration Tests:** Viết các test case tích hợp gọi endpoint `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/projects` sử dụng `httpx.AsyncClient` để xác thực:
   - Cơ chế cấp cookie HttpOnly `access_token` sau khi đăng nhập.
   - Cơ chế gán quyền admin cho user đầu tiên.
   - Việc phân tách dữ liệu dự án (user A không thể truy cập dự án của user B).
3. **Mocking Client Cookies:** Trong `pytest`, sử dụng `cookies` dict để gửi JWT cookie hợp lệ và không hợp lệ để kiểm chứng các endpoint yêu cầu xác thực hoạt động đúng.

---

## Epic 2: Công cụ Tìm kiếm & Ingestion Tài liệu (Academic Search & Paper Ingestion Engine)

Epic này phát triển công cụ tìm kiếm bài báo khoa học và quản lý quy trình nạp tài liệu tự động và thủ công dưới dạng bất đồng bộ.

### Story 2.1: Quản lý API Keys cá nhân & Mã hóa bảo mật (Personal API Keys Management)

As a người dùng,
I want thêm, sửa, xóa và kiểm tra kết nối API Key cá nhân của Gemini/Semantic Scholar,
So that tôi có thể nâng hạn mức gọi API và lưu trữ chúng an toàn bằng mã hóa AES/Fernet trong database.

**Acceptance Criteria:**

**Given** người dùng ở tab API Keys trong Cài đặt cá nhân.
**When** người dùng nhập Gemini API Key và bấm "Test Connection".
**Then** hệ thống gọi thử API Gemini để kiểm tra tính hợp lệ, hiển thị spinner `Testing...` và badge 🟢 `Connected` hoặc 🔴 `Failed` tùy thuộc kết quả.
**When** người dùng bấm "Lưu".
**Then** Backend mã hóa API Key bằng khóa đối xứng `AES/Fernet` trước khi lưu vào PostgreSQL.
**And** hiển thị key dạng mask trên UI, chỉ lộ 4 ký tự cuối (ví dụ: `••••••••••••••••3a5F`).

### Story 2.2: Tìm kiếm bài báo học thuật song song với xử lý lỗi Degraded Union (Academic Search with API Failover)

As a người dùng,
I want nhập từ khóa tìm kiếm và hệ thống gọi song song arXiv + Semantic Scholar (timeout 10s),
So that tôi nhận được danh sách bài báo không trùng lặp và vẫn xem được kết quả từ nguồn còn lại kèm Toast cảnh báo nếu một bên gặp sự cố.

**Acceptance Criteria:**

**Given** người dùng ở tab Thư viện tài liệu của dự án.
**When** người dùng nhập từ khóa "RAG optimization" và bấm Tìm kiếm.
**Then** Backend gửi yêu cầu tìm kiếm song song đến arXiv API và Semantic Scholar API.
**And** khử trùng lặp các bài báo dựa trên DOI hoặc đối khớp tiêu đề.
**And** hiển thị danh sách kết quả chứa siêu dữ liệu (tiêu đề, tác giả, năm, tóm tắt, trích dẫn, link PDF).
**Given** API Semantic Scholar bị lỗi hoặc quá hạn 10s nhưng arXiv thành công.
**When** thực hiện tìm kiếm.
**Then** Backend vẫn trả về kết quả thành công từ arXiv kèm cờ `warnings: ["semantic_scholar_timeout"]`.
**And** Frontend hiển thị Toast cảnh báo màu vàng ở góc phải: *"API Semantic Scholar gặp sự cố, hiển thị kết quả từ nguồn còn lại."* mà không bị sập hay trắng màn hình.

### Story 2.3: Gợi ý phân ngành MECE cho chủ đề quá rộng (Broad Query handling with Sub-field buttons)

As a người dùng,
I want hệ thống tự gợi ý các thẻ phân ngành nhỏ khi truy vấn quá rộng (vượt `BROAD_QUERY_THRESHOLD`),
So that tôi có thể dễ dàng bấm nút để thu hẹp phạm vi tìm kiếm.

**Acceptance Criteria:**

**Given** Admin cấu hình `BROAD_QUERY_THRESHOLD = 50`.
**When** người dùng tìm kiếm từ khóa rộng nhận về 65 kết quả từ API.
**Then** Backend gọi LLM phân tích từ khóa chính để sinh ra danh sách phân ngành nhỏ mang tính MECE (bao phủ toàn bộ phạm vi).
**And** trả về danh sách gợi ý dưới dạng các thẻ nút bấm có thể click dưới thanh tìm kiếm (ví dụ: `[RAG Retrieval Accuracy]`, `[Vector Index Optimization]`).
**When** người dùng click vào một nút gợi ý.
**Then** hệ thống tự động điền từ khóa đó vào ô tìm kiếm và kích hoạt một lượt truy vấn mới.

### Story 2.4: Upload tệp PDF/DOCX thủ công & Trích xuất Metadata thông minh (Manual Upload & AI Suggested Metadata)

As a người dùng,
I want tải lên tệp PDF/DOCX và AI tự trích xuất siêu dữ liệu điền vào biểu mẫu chỉnh sửa,
So that tôi có thể xác nhận lại siêu dữ liệu tài liệu trước khi nạp chính thức vào dự án.

**Acceptance Criteria:**

**Given** người dùng kéo thả tệp PDF/DOCX cá nhân vào vùng tải lên.
**When** tệp được tải lên Backend (giới hạn dung lượng < 20MB).
**Then** Backend chạy parse văn bản thô và gửi lên LLM để trích xuất Metadata.
**And** hiển thị form Metadata trên UI với các trường (Tiêu đề, Tác giả, Năm, Tóm tắt) được điền sẵn kèm nhãn badge `"AI Suggested"`.
**When** người dùng chỉnh sửa các trường này và click "Xác nhận".
**Then** hệ thống chính thức lưu Metadata đã xác thực vào PostgreSQL và khởi chạy quy trình nhúng vector.

### Story 2.5: Ingestion bất đồng bộ qua Worker arq & Stream tiến trình SSE (Async Ingestion & SSE Progress Stream)

As a người dùng,
I want hệ thống chạy nạp tài liệu ngầm (tải PDF, OCR nếu scan, chunking parent-child, lưu vector pgvector) và cập nhật tiến trình liên tục qua SSE,
So that tôi theo dõi được tiến trình xử lý chi tiết và tiếp tục làm việc khác mà không bị chặn UI.

**Acceptance Criteria:**

**Given** người dùng xác nhận nạp tài liệu vào dự án.
**When** Backend tiếp nhận yêu cầu.
**Then** Backend tạo một Background Task bất đồng bộ (arq worker) để xử lý nạp tài liệu:
  - Tải tệp PDF về local (nếu là link open access).
  - Sử dụng PyMuPDF / Docling để phân tách cấu trúc PDF/DOCX.
  - Sử dụng mô hình `text-embedding-004` nhúng Child Chunks (cỡ 500 ký tự, overlap 100) và lưu vào pgvector.
**And** Backend thiết lập kết nối SSE gửi các cập nhật trạng thái chi tiết theo thời gian thực về Frontend: `"Đang tải..."` -> `"Đang quét cấu trúc & OCR..."` -> `"Đang nhúng vector..."` -> `"Đã nạp thành công"`.
**And** Frontend cập nhật thanh tiến trình tương ứng của tài liệu trên danh sách Thư viện.

### Story 2.6: Kiểm soát Giới hạn số lượng tài liệu Admin đặt ra (Workspace Document limit)

As a người dùng,
I want hệ thống chặn nạp tài liệu và hiển thị cảnh báo đỏ khi số lượng tài liệu đạt giới hạn `MAX_PAPERS_PER_PROJECT` của Admin,
So that tài nguyên lưu trữ của hệ thống được kiểm soát và tránh vượt quá khả năng xử lý của dự án.

**Acceptance Criteria:**

**Given** Admin cấu hình giới hạn cứng dự án là `MAX_PAPERS_PER_PROJECT = 3`.
**When** dự án của người dùng đã có 3 tài liệu nạp thành công.
**Then** Frontend vô hiệu hóa (disable) nút nạp tài liệu mới và hiển thị banner cảnh báo màu đỏ: *"Dự án đã đạt giới hạn tài liệu tối đa của hệ thống (3 tài liệu)..."*
**When** người dùng cố tình gọi API upload tệp bằng cách gửi request thủ công.
**Then** Backend kiểm tra số lượng qua khóa phân tán Redis hoặc Optimistic Lock trên Postgres và từ chối xử lý, trả về mã lỗi `HTTP 403 Forbidden`.

---

### Chiến lược Kiểm thử & Giả lập cho Epic 2 (Epic 2 Testing & Mocking Strategy)

Để kiểm thử tự động cho Epic 2 mà không phụ thuộc vào kết nối mạng, chúng ta sẽ chuẩn bị các kịch bản test như sau:
1. **Mocking External Search HTTP APIs:**
   - Sử dụng thư viện `respx` hoặc `pytest-mock` để intercept các request HTTP gửi đến các endpoint của arXiv và Semantic Scholar.
   - Thiết lập các fixture trả về kết quả JSON học thuật giả định (mock search response) để test tính năng khử trùng lặp và hiển thị dữ liệu.
   - **Test Failover:** Thiết lập mock Semantic Scholar ném ra lỗi Timeout (HTTP 504) hoặc Rate Limit (HTTP 429), và verify Backend vẫn trả về kết quả của arXiv kèm mảng `warnings: ["semantic_scholar_timeout"]`.
2. **Mocking Gemini API (Metadata Extraction & Broad Query):**
   - Mock lời gọi đến SDK của Gemini để trích xuất Metadata và sinh MECE sub-fields. 
   - Fixture sẽ nhận dữ liệu text thô và trả về trực tiếp một JSON mock chứa: `{ "title": "Mock Title", "authors": ["Author A"], "abstract": "...", "year": 2026 }` hoặc danh sách `{ "suggested_sub_fields": ["Subfield A", "Subfield B"] }`.
3. **Integration Test cho Arq Worker & pgvector:**
   - Khởi chạy một test Redis server (`redislite` hoặc Redis Docker test container) để điều phối hàng đợi arq.
   - Viết test đẩy task nạp tài liệu với file PDF giả lập (mock file stream).
   - Verify worker arq chạy bình thường (concurrency = 2), thực hiện cắt chunk parent-child đúng thuật toán (Parent: 1000-3000 ký tự theo heading, Child: 500 ký tự, 100 overlap).
   - Kiểm tra DB PostgreSQL sau khi chạy verify các bản ghi chunk đã có vector và truy vấn tìm kiếm vector cosine distance trả về đúng dữ liệu.

---

## Epic 3: Trợ lý Chat RAG & Kiểm định Trích dẫn (AI Chatbot, RAG & Citation Guardrail)

Epic này phát triển chatbot AI kết hợp RAG và bộ lọc Citation Guardrail chống trích dẫn ảo.

### Story 3.1: Định tuyến & Quản lý phiên chat với PostgresSaver (Chat Session Management with PostgresSaver Checkpointer)

As a người dùng,
I want xem lịch sử các phiên chat cũ và khởi tạo phiên chat mới trong dự án hiện tại,
So that tôi có thể tiếp tục mạch suy nghĩ cũ được lưu trữ an toàn bằng checkpointer PostgresSaver.

**Acceptance Criteria:**

**Given** người dùng click nút tròn biểu tượng Lịch sử trò chuyện (đồng hồ) ở cột phải.
**When** popover mở ra.
**Then** hiển thị danh sách các phiên trò chuyện (threads) của dự án hiện tại từ cơ sở dữ liệu.
**When** người dùng click chọn một phiên chat cũ.
**Then** Backend load lại các trạng thái checkpoints trước đó từ PostgresSaver để phục hồi lịch sử hội thoại của LangGraph.
**And** hiển thị toàn bộ nội dung tin nhắn cũ lên khuông chat và đóng popover.
**When** người dùng click nút Trò chuyện mới (+).
**Then** hệ thống tạo một `thread_id` mới trong PostgreSQL và reset khung chat về trạng thái trống.

### Story 3.2: Chat RAG stream kết quả qua Server-Sent Events (SSE) (SSE Streaming RAG Chat)

As a người dùng,
I want gửi tin nhắn hỏi về tài liệu và chatbot trả lời dưới dạng stream ký tự SSE,
So that tôi có thể đọc phản hồi ngay lập tức với độ trễ thấp mà không cần chờ toàn bộ câu trả lời được sinh xong.

**Acceptance Criteria:**

**Given** người dùng đã đăng nhập và kết nối SSE qua ticket hợp lệ `GET /api/sse/stream?ticket=<ticket>`.
**When** nhập câu hỏi và nhấn `ENTER` (hoặc bấm nút gửi).
**Then** Backend chạy đồ thị LangGraph (Supervisor Agent điều phối RAG Agent gọi `vector_search_tool` để lấy text chunks).
**And** stream câu trả lời về Frontend theo thời gian thực (SSE events).
**And** Frontend hiển thị câu chữ dạng máy đánh chữ (typewriter) với độ trễ ký tự đầu tiên (First Chunk Latency) < 3 giây.
**And** hiển thị trạng thái suy nghĩ của Agent (`agent_thinking`) trước khi bắt đầu trả lời.

### Story 3.3: Chatbot định hướng dựa trên trạng thái dự án (Context-Aware User Guiding)

As a người dùng (đặc biệt là người mới),
I want chatbot tự cảm nhận trạng thái dự án để chủ động gợi ý các nút Quick Reply động,
So that tôi biết cần làm gì tiếp theo và điều hướng nhanh chỉ bằng một click.

**Acceptance Criteria:**

**Given** Frontend gửi kèm payload `ui_context` chứa: tab hiện tại (`active_tab`), số tài liệu (`document_count`), trạng thái bản thảo (`has_draft`).
**When** người dùng đặt câu hỏi gợi ý hành động hoặc dự án mới tạo hoàn toàn trống.
**Then** LLM phân tích `ui_context` và trả về danh sách các `suggested_actions` gợi ý hành động thích hợp.
**And** Frontend hiển thị các gợi ý đó dưới dạng thẻ nút bấm Quick Reply động ở dưới ô nhập chat (ví dụ: `[Tải tài liệu lên]`, `[Xem bản đồ tri thức]`, `[Gợi ý dàn ý]`).
**When** người dùng click vào nút gợi ý.
**Then** Frontend tự động chuyển hướng màn hình sang tab tương ứng mà không cần người dùng thao tác thủ công.

### Story 3.4: Citation Guardrail Node chống trích dẫn ảo (Citation Guardrail Node & Auto-Correction)

As a người dùng,
I want các trích dẫn học thuật (dạng `[1]`, `[2]`) do AI sinh ra phải được đối chiếu và sửa lỗi tự động nếu là trích dẫn ảo,
So that tôi có được nguồn tài liệu thực tế tin cậy tuyệt đối và không bị lỗi hallucination của LLM.

**Acceptance Criteria:**

**Given** Admin cấu hình `CITATION_ERROR_THRESHOLD = 30%` và `CITATION_RETRY_LIMIT = 2`.
**When** LLM hoàn tất sinh câu trả lời thô có chứa các thẻ trích dẫn.
**Then** hệ thống chuyển luồng qua *Citation Verify Node* (chạy code Python thuần sử dụng Regex) đối chiếu danh sách các thẻ trích dẫn với các Chunk dữ liệu thực tế đã truy xuất từ Postgres.
**And** tính toán tỷ lệ lỗi trích dẫn ảo:
  - **Nếu tỷ lệ lỗi $\le$ 30%:** Hệ thống tự động thay thế thẻ trích dẫn lỗi thành `[Nguồn không xác định]` hoặc loại bỏ nó ngay lập tức (không gọi lại LLM) và trả kết quả.
  - **Nếu tỷ lệ lỗi > 30%:** Hệ thống kích hoạt quy trình tự sửa của LLM tối đa 2 lần. Nếu vẫn vượt ngưỡng, trả câu trả lời kèm banner cảnh báo độ tin cậy thấp ở trên đầu.

### Story 3.5: Giao diện tương tác thẻ trích dẫn (Interactive Citation Tooltip)

As a người dùng,
I want di chuột hoặc click vào thẻ trích dẫn `[1]` trong chat hoặc bản thảo để xem thông tin bài báo và đoạn text gốc trích dẫn,
So that tôi có thể đối chiếu nội dung trực tiếp mà không cần mở file thủ công.

**Acceptance Criteria:**

**Given** câu trả lời hiển thị thẻ trích dẫn `[1]`.
**When** người dùng hover hoặc click vào thẻ trích dẫn `[1]`.
**Then** Frontend hiển thị giao diện xem nhanh (tooltip bo góc rounded.lg).
**And** gọi API `GET /api/citations/{citation_id}` để fetch thông tin: Tên bài viết, tác giả, năm, DOI và đoạn văn bản gốc (`text_chunk`) dùng làm căn cứ trích dẫn.
**And** cung cấp nút liên kết tải xuống tệp PDF hoặc mở URL bài báo gốc trong trình duyệt.

---

### Chiến dịch Kiểm thử & Giả lập cho Epic 3 (Epic 3 Testing & Mocking Strategy)

Do Epic 3 kết hợp luồng logic đa Agent trong LangGraph và stream SSE, chúng ta thiết lập chiến lược mock như sau:
1. **Mocking Simple RAG & GraphRAG Tools:**
   - Trong quá trình test Agent, chúng ta mock các công cụ `vector_search_tool` và `graph_search_tool` bằng `unittest.mock`. Các tool mock này sẽ trả về dữ liệu chunk thô giả lập dưới dạng list object thay vì thực sự kết nối DB Postgres/Neo4j, giúp cô lập hành vi suy luận của Agent.
2. **Mocking LLM Generation Stream:**
   - Giả lập phản hồi của Gemini API dạng stream (yield text từng phần) có chứa các thẻ trích dẫn hợp lệ và không hợp lệ (ví dụ: sinh thẻ trích dẫn `[9]` mặc dù chỉ có 2 chunks dữ liệu được nạp vào context).
   - Kiểm chứng xem `Citation Verify Node` có chạy đúng thuật toán phân tích Regex và sửa lỗi thành `[Nguồn không xác định]` hoặc kích hoạt LLM retry tự sửa lỗi khi tỷ lệ lỗi vượt ngưỡng hay không.
3. **Test Ticket-based SSE Authentication & Last-Event-ID:**
   - Viết test case tích hợp:
     - Truy cập stream SSE trực tiếp không có ticket -> Trả về lỗi `HTTP 401 Unauthorized`.
     - POST `ticket` -> Trả về token một lần.
     - Gửi request SSE kèm ticket -> Kết nối thành công.
     - Giả lập mất mạng (ngắt kết nối), kết nối lại và gửi header `Last-Event-ID` -> Backend phải yield lại các message bị nhỡ nằm trong cache buffer.

---

## Epic 4: Bản đồ Tri thức & Phân tích Đồ thị (Knowledge Graph Synchronization & Exploration)

Epic này trực quan hóa và đồng bộ hóa mạng lưới trích dẫn giữa các bài báo sử dụng Neo4j và Cytoscape.js.

### Story 4.1: Đồng bộ Postgres sang Neo4j Event-driven qua outbox worker (Graph Event-Driven Sync Manager)

As a hệ thống,
I want lắng nghe các thay đổi trong Postgres để ghi sự kiện vào `sync_outbox`, sau đó background worker chạy cypher MERGE để đồng bộ sang Neo4j,
So that dữ liệu đồ thị tri thức luôn nhất quán với cơ sở dữ liệu quan hệ Postgres.

**Acceptance Criteria:**

**Given** người dùng thêm hoặc cập nhật tài liệu trong dự án.
**When** giao dịch ghi vào Postgres thành công.
**Then** hệ thống ghi một sự kiện tương ứng vào bảng `sync_outbox` trong cùng một transaction.
**When** background worker arq quét bảng `sync_outbox`.
**Then** sử dụng truy vấn `SELECT ... FOR UPDATE SKIP LOCKED` để lấy các sự kiện chưa xử lý và lock theo `project_id` trên Redis.
**And** chạy các câu lệnh Cypher MERGE để đồng bộ thông tin (Paper, Author, CITES) sang Neo4j an toàn, tránh deadlock.

### Story 4.2: Cơ chế Xóa mềm & Dọn dẹp Garbage Collection (Workspace Soft-Delete & GC)

As a hệ thống,
I want khi người dùng xóa tài liệu/dự án thì chỉ cập nhật trạng thái xóa mềm trong cơ sở dữ liệu và gán nhãn Deleted trong Neo4j, sau đó cron job ban đêm quét xóa cứng dữ liệu cũ quá 7 ngày,
So that dữ liệu thừa được dọn dẹp sạch sẽ mà không làm crash các truy vấn đang chạy hoặc các phiên làm việc hiện tại.

**Acceptance Criteria:**

**Given** người dùng thực hiện xóa dự án hoặc bài báo.
**When** Backend nhận yêu cầu xóa.
**Then** hệ thống cập nhật trạng thái xóa mềm trong Postgres và ghi sự kiện cập nhật vào `sync_outbox`.
**And** Worker đồng bộ cập nhật nhãn `(:Deleted)` cho các nodes tương ứng trong Neo4j.
**And** các truy vấn RAG và đồ thị luôn tự động bỏ qua các nodes có nhãn `(:Deleted)` thông qua mệnh đề `WHERE NOT p:Deleted`.
**When** cron job chạy định kỳ lúc 2h sáng.
**Then** hệ thống quét và xóa vĩnh viễn (hard-delete) tất cả các dữ liệu đã bị xóa mềm quá 7 ngày ở cả Postgres và Neo4j.

### Story 4.3: Vẽ đồ thị Cytoscape.js & Tải động (Lazy Graph Rendering & Expand API)

As a người dùng,
I want xem bản đồ trích dẫn bài báo dạng đồ thị Cytoscape.js giới hạn tối đa 150 nodes/300 edges ban đầu và có thể click expand 1-hop lân cận,
So that trình duyệt không bị treo khi dự án lớn và tôi có thể chủ động khám phá đồ thị một cách mượt mà.

**Acceptance Criteria:**

**Given** người dùng chuyển sang Tab Bản đồ Tri thức.
**When** đồ thị được tải.
**Then** API Backend giới hạn kết quả trả về ban đầu tối đa 150 nodes và 300 edges, kèm theo cờ `hasMore = true` nếu vượt quá giới hạn.
**And** Frontend vẽ đồ thị Cytoscape.js hỗ trợ zoom, pan và kéo thả tự do các nodes.
**When** người dùng double click vào một node bài báo.
**Then** Frontend gọi API `GET /api/projects/{project_id}/graph/nodes/{node_id}/expand` lấy các node và cạnh lân cận trong vòng 1-hop của node được chọn (giới hạn 20 thực thể mới).
**And** thêm các nodes mới vào Cytoscape viewport bằng incremental layout (bố cục gia tăng) mà không làm xáo trộn vị trí của các node cũ đang hiển thị.

### Story 4.4: Node Detail Card & Tích hợp Phát hiện Khoảng trống trực quan (Node Details & Gap Highlight)

As a người dùng,
I want click vào một node bài báo để mở slide-card xem metadata và bật chế độ "Tìm khoảng trống nghiên cứu" để highlight các node mâu thuẫn thực nghiệm,
So that tôi nhanh chóng nhận biết các khoảng trống học thuật trực tiếp trên sơ đồ mạng lưới.

**Acceptance Criteria:**

**Given** người dùng click vào một node bài báo trên canvas đồ thị.
**When** node được chọn.
**Then** node đổi màu viền sang xanh lá đậm.
**And** một slide-card Node Detail Card trượt ra từ góc trên bên phải canvas đồ thị, hiển thị các thông tin metadata (Title, Authors, Abstract, Year) mà không đè lên panel chatbot bên phải.
**When** người dùng bật nút nổi "Tìm khoảng trống nghiên cứu" ở góc trái đồ thị.
**Then** hệ thống tô viền nhấp nháy đỏ cho các node bài báo có nhận định mâu thuẫn thực nghiệm (`(:Finding)-[:CONTRADICTS]->(:Finding)`) và viền vàng cho các node trích dẫn cô lập (không liên kết trích dẫn).

---

### Chiến lược Kiểm thử & Giả lập cho Epic 4 (Epic 4 Testing & Mocking Strategy)

Để kiểm thử tự động phần đồ thị và đồng bộ dữ liệu:
1. **Mocking Neo4j Driver (Graph Database Mocking):**
   - Trong quá trình test API, chúng ta mock hoàn toàn Neo4j Driver (`neo4j.AsyncDriver`) trả về danh sách mock records chứa thông tin node và relationship giả định, giúp kiểm thử API `/expand` và `/graph` mà không cần chạy instance Neo4j thật.
2. **Test Outbox Sync Concurrency & Lock:**
   - Viết test case tích hợp cho worker đồng bộ:
     - Tạo 2 tiến trình worker đồng thời gọi xử lý cùng một `project_id`.
     - Xác thực cơ chế phân tán dùng Redis lock và `SELECT ... FOR UPDATE SKIP LOCKED` đảm bảo chỉ có 1 worker được xử lý đồng bộ đồ thị cho dự án đó tại một thời điểm.
     - Test luồng Lock Heartbeat: Giả lập tác vụ đồng bộ chạy lâu hơn thời gian timeout của lock, kiểm tra xem luồng phụ có tự động gia hạn thời gian sống của lock trong Redis hay không.
3. **Cytoscape.js Frontend Rendering Mock:**
   - Viết component test cho frontend: giả lập dữ liệu JSON đồ thị có cờ `hasMore = true`, verify Cytoscape vẽ đúng số node.
   - Giả lập double-click vào node, mock kết quả trả về từ API `/expand` và verify các node mới được vẽ thêm vào viewport mà không bị mất đi các node cũ.

---

## Epic 5: Soạn thảo Tổng quan & Cấu hình Hệ thống (Overview Writing & Settings)

Epic này phát triển không gian soạn thảo nháp, xuất báo cáo và trang cấu hình hệ thống dành cho Admin.

### Story 5.1: Soạn thảo Literature Review & Quản lý bản thảo (Literature Review Drafting & Version Saving)

As a người dùng,
I want soạn thảo văn bản tổng quan tài liệu trong rich text editor, lưu nháp tự động và phục hồi các phiên bản cũ,
So that tôi có thể quản lý chặt chẽ nội dung tài liệu tổng quan mà không sợ mất dữ liệu.

**Acceptance Criteria:**

**Given** người dùng chọn tab Hỗ trợ viết tổng quan trong dự án.
**When** người dùng bắt đầu viết nháp nội dung Literature Review.
**Then** hệ thống tự động lưu nháp sau mỗi 10 giây (với chỉ báo `"Đang lưu..."` và `"Đã lưu"` ở góc màn hình) và lưu trữ lịch sử phiên bản vào PostgreSQL.
**When** người dùng xem danh sách bản thảo và click chọn khôi phục một phiên bản cũ.
**Then** hệ thống ghi đè nội dung editor bằng nội dung của phiên bản được chọn.

### Story 5.2: Đóng gói và Xuất bản thảo chuẩn Markdown & BibTeX (ZIP Exporting)

As a người dùng,
I want xuất bản thảo và toàn bộ danh mục tài liệu trích dẫn thành tệp ZIP chứa Markdown `.md` và BibTeX/APA `.bib`,
So that tôi có thể tải xuống sử dụng ngay cho các công cụ viết bài báo (LaTeX, Overleaf, Word).

**Acceptance Criteria:**

**Given** người dùng có bản thảo đã hoàn thành có chứa các thẻ trích dẫn.
**When** người dùng click nút "Xuất báo cáo".
**Then** Backend thu thập nội dung bản thảo và metadata các bài báo có trong dự án.
**And** chuyển đổi danh mục trích dẫn sang chuẩn format BibTeX `.bib`.
**And** nén cả 2 tệp (Markdown `.md` và BibTeX `.bib`) thành một tệp nén ZIP.
**And** trả về stream tải tệp ZIP về máy tính của người dùng.

### Story 5.3: Cài đặt hệ thống động của Admin lưu cơ sở dữ liệu (Dynamic System Settings via Admin Panel)

As an Admin,
I want điều chỉnh cấu hình giới hạn hệ thống động qua UI cài đặt dành cho Admin (lưu vào database Postgres),
So that tôi có thể tối ưu hóa và quản trị tài nguyên server mà không cần restart hay deploy lại server.

**Acceptance Criteria:**

**Given** người dùng có vai trò là Admin.
**When** nhấp biểu tượng bánh răng ở Header để vào Trang Cài đặt Hệ thống và cập nhật các tham số (ví dụ: đổi `MAX_PAPERS_PER_PROJECT` từ 15 thành 5).
**Then** Backend lưu trữ các tham số cấu hình động này vào bảng `settings` trong PostgreSQL.
**And** áp dụng cấu hình mới ngay lập tức.
**When** người dùng thường (`role = 'user'`) cố tình truy cập trang Cài đặt hoặc gửi request thay đổi cấu hình.
**Then** Backend trả về mã lỗi `HTTP 403 Forbidden` và chặn chỉnh sửa.

### Story 5.4: Trang Landing Page vãng lai & Bản demo mô phỏng (Guest Landing Page & Mock Simulator)

As a khách vãng lai,
I want xem trang giới thiệu Landing page có bảng so sánh giá và tương tác thử với Khung Demo Giả lập,
So that tôi hiểu được tính năng của ứng dụng trước khi quyết định đăng ký tài khoản.

**Acceptance Criteria:**

**Given** khách vãng lai chưa đăng nhập truy cập vào trang chủ.
**When** xem trang Landing page.
**Then** hiển thị đầy đủ giao diện cuộn dọc gồm Hero banner giới thiệu, Bảng giá (gói Sinh viên free và Nghiên cứu viên Pro nổi bật viền cobalt).
**When** khách nhập từ khóa bất kỳ vào ô tìm kiếm trong Khung Demo Giả lập và click Tìm thử.
**Then** Khung demo mô phỏng tìm kiếm bài báo trong 1.5s (hiển thị loading spinner).
**And** render ra một đồ thị trích dẫn Cytoscape demo đơn giản có 1 node đỏ nhấp nháy tượng trưng cho khoảng trống nghiên cứu để khách tương tác thử.

---

### Chiến dịch Kiểm thử & Giả lập cho Epic 5 (Epic 5 Testing & Mocking Strategy)

Để kiểm thử tự động các chức năng soạn thảo, xuất ZIP và phân quyền cài đặt Admin:
1. **Mocking Export ZIP Payload:**
   - Viết unit test cho API `/export`. Thiết lập mock database trả về dữ liệu bản thảo và tài liệu mẫu.
   - Sử dụng thư viện `zipfile` của Python trong test script để đọc trực tiếp dữ liệu nhị phân trả về, verify tệp ZIP chứa đúng 2 file `.md` và `.bib` với format BibTeX hợp lệ.
2. **Settings Boundary Validation Tests:**
   - Viết các test case kiểm chứng phân quyền của Admin: gửi request thay đổi cài đặt bằng token của user thường -> Đảm bảo trả về lỗi `HTTP 403 Forbidden`.
   - Kiểm thử validate đầu vào cài đặt: gửi các giá trị âm hoặc không hợp lệ (như tỷ lệ trích dẫn lỗi âm) -> Đảm bảo Backend trả về lỗi validation `HTTP 422 Unprocessable Entity`.
3. **Frontend Localization & Theme Swap Mock:**
   - Viết component test cho Header: giả lập click `VI | EN` hoặc nút sáng tối, verify các phần tử DOM thay đổi nhãn ngôn ngữ và class CSS theme tức thời mà không phát sinh thêm bất kỳ lượt reload trang nào.
