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

> **⚙️ Lưu ý đồng bộ (cập nhật 2026-06-17):** Bảng phân rã story bên dưới đã được **đồng bộ với `_bmad-output/implementation-artifacts/sprint-status.yaml`** — đây là **nguồn sự thật (source of truth)** vì phản ánh đúng những gì đã được triển khai. Trong quá trình thực thi, các story chia nhỏ [Backend]/[Frontend] của bản kế hoạch gốc đã được **gộp thành các story fullstack theo lát cắt dọc (vertical slice)**. Mỗi story dưới đây liệt kê số hiệu thật trong sprint-status, trạng thái hiện tại, và dòng **"Gộp từ kế hoạch cũ"** để truy vết về bản phân rã 38-story ban đầu. **AC chi tiết chính thức của các story đã hoàn thành nằm trong file story tương ứng tại `implementation-artifacts/`** (không lặp lại ở đây để tránh trôi lệch tài liệu).

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
- **FR16 (Document Lifecycle — Delete & Edit Metadata):** Epic 2 - Academic Search & Paper Ingestion Engine

## Ma trận Trách nhiệm 3 Tầng (Module ↔ Epic ↔ Story ↔ FR)

> **Thêm 2026-06-17 (correct-course role-clarity).** Làm rõ ranh giới vai trò sau nhiều lần gộp/tách story. Tham chiếu `sprint-change-proposal-2026-06-17-role-matrix.md`.
>
> **Nguyên tắc 3 trục (chốt):**
> - **Module (architecture.md §9.4)** = *nơi code sống* — bounded context Hexagonal, cố định 7 module (`identity`, `workspace`, `ingestion`, `simple_rag`, `graph_rag`, `orchestrator`, `shared`).
> - **Epic** = *chủ đề giá trị / nhóm FR* — **KHÔNG buộc 1:1 với module**.
> - **Story** = *lát cắt thực thi (vertical slice)* — **được phép xuyên nhiều module**, miễn mỗi *task* khai báo `[module]` của nó và tôn trọng §9.6 (không module nào gọi thẳng infra của module khác).
>
> **Ranh giới bất biến (§9.6):** `ingestion` = **PRODUCER** duy nhất ghi `sync_outbox` (gồm Stage-2 Graph Extraction §6.2); `graph_rag`/`simple_rag` = **CONSUMER** (worker đọc `sync_outbox` → Neo4j / pgvector).

| Module (§9.4) | Vai trò chính | Epic chính | Story | FR / ARCH |
|---|---|---|---|---|
| `identity` | Auth, JWT, users, RBAC | E1 | 1.1✅ 1.2✅ 1.3✅(BE auth) | FR1 |
| `workspace` | Projects, settings động, **chủ ORM `sync_outbox` + bảng `projects`** | E1, E5 | 1.4✅ 1.5✅ 1.6✅; 2.6✅(limits); 5.3(settings) | FR2, FR11, FR12 |
| `ingestion` | **PRODUCER** sync_outbox; pipeline nạp (write-heavy), Stage-1+Stage-2 §6.2 | E2 (+E4) | 2.2–2.5✅ 2.7✅; **4.1·Producer** `PAPER_UPSERTED`; **4.3** Stage-2 extraction | FR3,4,5,16; FR7(extract) |
| `simple_rag` | Vector search read (pgvector), `vector_search` | E3 | 3.6✅ | FR6, NFR3 |
| `graph_rag` | **CONSUMER** sync→Neo4j; `graph_search`/`gap_detection`; GC lifecycle | E4 | **4.1·Infra+Consumer+GC**; 4.2(BE đọc đồ thị); 4.4(GraphRAG Engine) | FR7, FR9, ARCH-2, ARCH-8 |
| `orchestrator` | LangGraph, SSE, Supervisor/RAG/Gap agents, Citation Guardrail | E3 (+E4) | 3.1–3.4✅ 3.6✅; **4.5** tiến hóa Router-Worker | FR6,8,10,15; FR7(chat) |
| `shared` | Shared Kernel: LLMRouter, `neo4j_client`, `redis_client`, settings | cross | 2.1✅(LLMRouter+keys); hạ tầng driver ở 4.1 | ARCH-6 |

> *Frontend (React) được phân mảnh feature-sliced (Auth/Workspace/Chat/Graph) đi kèm phần FE của các story `[BE+FE]` — không phải module backend.*

**Story xuyên-module (đã gắn nhãn task):**
- **4.1** = `[shared]` Neo4j driver + `[ingestion]` producer `PAPER_UPSERTED` (vá nợ 2.5) + `[graph_rag]` consumer worker/GC + `[workspace]` migration `sync_outbox`/`projects` (+`[ingestion]` migration `papers.deleted_at`).
- **4.3** = `[ingestion]` Stage-2 extraction (ghi ontology event) + `[graph_rag]` đăng ký handler MERGE ontology + tạo Unique Constraints ontology vào dispatch map của 4.1.
- **4.5** = `[orchestrator]` tiến hóa graph LangGraph (chạm code Epic 3) + gọi tool `[graph_rag]` (gap_detection/graph_search).

**Chủ sở hữu Ontology (gỡ chồng lấn 4.1 ↔ 4.3):**

| Khía cạnh | Chủ (module) | Story |
|---|---|---|
| Schema base (Paper/Author/Project) + Unique Constraints base | `graph_rag` | **4.1** |
| Schema ontology (Finding/Limitation/Method/Dataset/Topic/Problem + edges CONTRADICTS/SUPPORTS/HAS_LIMITATION/FILLS_GAP) + constraints ontology | `graph_rag` | **4.3** (KHÔNG phải 4.1) |
| Trích xuất & PRODUCE ontology event vào `sync_outbox` | `ingestion` | **4.3** |
| MERGE ontology vào Neo4j (consume) | `graph_rag` handler | **4.3** (đăng ký vào dispatch map khung-mở-rộng của 4.1) |
| Khung dispatch map mở-rộng-được (forward-compat) | `graph_rag` | **4.1** |

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

> **📌 Trạng thái thực thi (đồng bộ từ sprint-status.yaml — 2026-06-17):**
> Epic 1 ✅ done · Epic 2 ⏳ in-progress (2.1–2.6 done, 2.7 backlog) · Epic 3 ⏳ in-progress (3.1–3.5 done, 3.6 ready-for-dev) · Epic 4 ⏳ backlog · Epic 5 ⏳ backlog
> Tổng: **28 story** (đã gộp từ 38 story chia nhỏ của bản kế hoạch gốc; +2 story 2.7/3.6 phát sinh trong thực thi; Epic 4 bổ sung Gap Detection backend rồi **gộp còn 5 story 4.1–4.5** (GC gộp vào 4.1) để giảm số lần vibecode — correct-course + Architect 2026-06-17). AC chính thức của story đã hoàn thành nằm ở file story tương ứng trong `implementation-artifacts/`.

---

## Epic 1: Quản lý Không gian & Nền tảng Xác thực (Workspace & Identity Foundation)

Epic này tập trung vào thiết lập hạ tầng cốt lõi về định danh người dùng và phân quyền, xây dựng giao diện Workspace 3 cột và cơ chế lưu trữ dự án độc lập.

### Story 1.1: [Backend] User Schema & Register API — ✅ done

API đăng ký tài khoản: lưu `users` với mật khẩu bcrypt, tự gán `role='admin'` cho tài khoản đầu tiên, 400 nếu email trùng.

- **Gộp từ kế hoạch cũ:** Story 1.1 (User Schema & Register API).
- **AC chi tiết:** `implementation-artifacts/1-1-dang-ky-tai-khoan-phan-quyen-admin-khoi-tao.md`
- **FRs:** FR1.

### Story 1.2: [Backend] Login API & JWT Session — ✅ done

API đăng nhập cấp JWT qua HttpOnly cookie (`SameSite=Lax`), chặn 401 các route bảo mật khi thiếu cookie.

- **Gộp từ kế hoạch cũ:** Story 1.2 (Login API & JWT Session).
- **AC chi tiết:** `implementation-artifacts/1-2-dang-nhap-xac-thuc-bang-httponly-cookie.md`
- **FRs:** FR1.

### Story 1.3: [Frontend] Auth UI, Onboarding & Khởi tạo Dự án Đầu tiên — ✅ done

Giao diện Đăng ký/Đăng nhập + logic first-admin (hiện nút Bánh răng), và luồng onboarding gating tạo dự án đầu tiên khi chưa có dự án.

- **Gộp từ kế hoạch cũ:** Story 1.3 (Auth UI & First-Admin Logic) + UX-DR4 (New User Onboarding).
- **AC chi tiết:** `implementation-artifacts/1-3-quy-trinh-onboarding-khoi-tao-du-an-dau-tien.md`
- **FRs:** FR1, FR2. UX-DR4.

### Story 1.4: [Fullstack] CRUD Dự án Nghiên cứu & Left Sidebar Điều hướng — ✅ done

API CRUD dự án (soft-delete + ghi `sync_outbox`) cùng Sidebar trái hiển thị tối đa 10 dự án gần nhất và Modal tạo dự án cập nhật tức thời.

- **Gộp từ kế hoạch cũ:** Story 1.4 (Project CRUD APIs) + Story 1.5 (Project Sidebar & Creation Modal).
- **AC chi tiết:** `implementation-artifacts/1-4-crud-du-an-nghien-cuu-left-sidebar-dieu-huong.md`
- **FRs:** FR2.

### Story 1.5: [Frontend] Giao diện 3 Cột, Bộ Chuyển đổi Ngôn ngữ & Chủ đề — ✅ done

Layout Workspace 3 cột (Sidebar / Tab giữa / Chatbot Panel co giãn), bộ chuyển VI|EN và Light/Soft-Dark trên Header.

- **Gộp từ kế hoạch cũ:** UX-DR1 (Three-Column Layout) + UX-DR2 (Language Toggle) + UX-DR3 (Theme Toggle).
- **AC chi tiết:** `implementation-artifacts/1-5-giao-dien-3-cot-bo-chuyen-doi-ngon-ngu-chu-de.md`
- **FRs:** FR2. UX-DR1, UX-DR2, UX-DR3.

### Story 1.6: [Frontend] Trang Quản lý Toàn bộ Dự án Dạng Bảng — ✅ done

Trang quản lý tập trung dạng bảng có tìm kiếm, phân trang, xóa dự án (popup xác nhận).

- **Gộp từ kế hoạch cũ:** Story 1.6 (Centralized Project Management Table) + UX-DR9.
- **AC chi tiết:** `implementation-artifacts/1-6-trang-quan-ly-toan-bo-du-an-dang-bang.md`
- **FRs:** FR2. UX-DR9.

---

## Epic 2: Công cụ Tìm kiếm & Ingestion Tài liệu (Academic Search & Paper Ingestion Engine)

Epic này phát triển công cụ tìm kiếm bài báo khoa học và quản lý quy trình nạp tài liệu tự động và thủ công dưới dạng bất đồng bộ.

### Story 2.1: [BE+FE] Quản lý API Keys Cá nhân — Mã hóa & Bảo mật — ✅ done

Lưu API Keys người dùng mã hóa Fernet trong Postgres, panel quản lý có masking 4 số cuối + Test Connection (spinner, Connected/Failed). Tiền đề cho mọi lời gọi LLM cá nhân hóa (trích xuất metadata, RAG).

- **Gộp từ kế hoạch cũ:** Story mới phát sinh trong thực thi (chưa có trong bản 38-story gốc). Hiện thực hóa ARCH-6 + UX-DR12.
- **AC chi tiết:** `implementation-artifacts/2-1-quan-ly-api-keys-ca-nhan-ma-hoa-bao-mat.md`
- **FRs:** ARCH-6, UX-DR12.

### Story 2.2: [BE+FE] Tìm kiếm Bài báo Học thuật Song song với Xử lý lỗi Degraded Union — ✅ done

Gọi song song arXiv + Semantic Scholar (timeout 10s, Tenacity retry), khử trùng lặp theo DOI, "degraded union" khi một nguồn lỗi, và UI hiển thị thẻ kết quả.

- **Gộp từ kế hoạch cũ:** Story 2.6 (External Search Clients) + Story 2.7 (Parallel Search & Deduplication API) + phần kết quả của Story 2.8 (Search UI).
- **AC chi tiết:** `implementation-artifacts/2-2-tim-kiem-bai-bao-hoc-thuat-song-song-voi-xu-ly-loi-degraded-union.md`
- **FRs:** FR3, ARCH-5.

### Story 2.3: [BE+FE] Gợi ý phân ngành MECE cho chủ đề quá rộng — ✅ done

Phát hiện truy vấn rộng theo `BROAD_QUERY_THRESHOLD`, sinh các nút gợi ý phân ngành MECE để thu hẹp tìm kiếm.

- **Gộp từ kế hoạch cũ:** Phần broad-query detection của Story 2.8 (Search UI & Broad Query Detection).
- **AC chi tiết:** `implementation-artifacts/2-3-goi-y-phan-nganh-mece-cho-chu-de-qua-rong.md`
- **FRs:** FR3.

### Story 2.4: [BE+FE] Upload tệp PDF/DOCX thủ công – Trích xuất metadata thông minh — ✅ done

Upload PDF/DOCX, đọc 2 trang đầu, LLM trích xuất `{title, authors, abstract, year}`, hiển thị Form "AI Suggested" để người dùng xác nhận/sửa.

- **Gộp từ kế hoạch cũ:** Story 2.1 (Manual Upload & LLM Metadata Extraction) + Story 2.2 (AI Suggested Metadata Form).
- **AC chi tiết:** `implementation-artifacts/2-4-upload-tep-pdf-docx-thu-cong-trich-xuat-metadata-thong-minh.md`
- **FRs:** FR5, NFR2, UX-DR11.

### Story 2.5: [BE+FE] Ingestion Bất Đồng Bộ Qua Worker ARQ – Stream Tiến Trình SSE — ✅ done

Đẩy job nạp tài liệu vào worker ARQ; worker chunk parent-child + sinh embedding (Gemini `text-embedding-004`) lưu vào pgvector (HNSW index); stream tiến trình qua SSE để UI vẽ progress bar.

- **Gộp từ kế hoạch cũ:** Story 2.3 (Background Ingestion Task Foundation) + Story 2.4 (SSE Progress Streaming) + Story 2.5 (Ingestion Progress UI).
- **AC chi tiết:** `implementation-artifacts/2-5-ingestion-bat-dong-bo-qua-worker-arq-stream-tien-trinh-sse.md`
- **FRs:** FR4, NFR3, NFR4, ARCH-5.

### Story 2.6: [BE+FE] Kiểm Soát Giới Hạn Số Lượng Tài Liệu – Admin Đặt Ra — ✅ done

Chặn ingestion (search/upload) khi dự án đạt `MAX_PAPERS_PER_PROJECT` (403 + Redis lock chống vượt giới hạn do đua), UI vô hiệu hóa nút "Thêm" và cảnh báo.

- **Gộp từ kế hoạch cũ:** Story 2.9 (Document Limit Enforcement).
- **AC chi tiết:** `implementation-artifacts/2-6-kiem-soat-gioi-han-so-luong-tai-lieu-admin-dat-ra.md`
- **FRs:** FR11.

### Story 2.7: [BE+FE] Quản lý Tài liệu trong Dự án — Xóa, Sửa Metadata & Cache/Xem PDF Nguồn — ⏳ backlog

Lát cắt dọc quản lý vòng đời tài liệu, gộp 2 năng lực trên cùng thực thể `PaperORM` / cùng tab Thư viện:
1. **Xóa tài liệu**: soft-delete `is_deleted` + ghi `sync_outbox` (Neo4j GC theo ARCH-2) + cascade chunks + **giảm bộ đếm `MAX_PAPERS_PER_PROJECT`** (đồng bộ Redis lock của Story 2.6). Owner scoping chống IDOR.
2. **Sửa metadata**: PATCH `{title, authors, abstract, year}` của tài liệu đã ingest (KHÔNG re-embed).
3. **Cache & xem PDF nguồn**: worker persist PDF Open Access đã tải (`paper.file_path` thay vì bỏ sau khi trích text), endpoint bảo mật `GET /api/projects/{project_id}/papers/{paper_id}/file` (FileResponse, mirror ARCH-9) để xem/tải lại không cần gọi lại arXiv/Scholar; paywalled/tải fail → giữ link ngoài + nhãn "nguồn cần trả phí"; tôn trọng NFR2 (20MB).
4. **UI tab Thư viện**: nút xóa (popup xác nhận) + form sửa metadata + nút "Xem file nguồn".

- **Gộp từ kế hoạch cũ:** Phát sinh trong thực thi (correct-course 2026-06-17). Hợp nhất từ 2.7 (Document CRUD) + 2.8 (Cache PDF) do đồng độ gắn kết cao, theo pattern vertical-slice của dự án. Hiện thực hóa FR16 (mới) + hoàn thiện FR4/FR10 đã cam kết (Story 2.5 chỉ tải PDF để trích text rồi bỏ). Tham chiếu `sprint-change-proposal-2026-06-17-document-management.md`.
- **Khuyến nghị thực thi:** làm backend trước (DELETE → PATCH → worker persist → serve endpoint) rồi mới UI; viết test ngay cho điểm nóng giảm counter `MAX_PAPERS` (đua Redis).
- **AC chi tiết:** sẽ tạo qua `bmad-create-story` tại `implementation-artifacts/2-7-quan-ly-tai-lieu-xoa-sua-metadata-cache-xem-pdf.md`.
- **FRs:** FR16 (mới), FR4, FR10, FR11, NFR2. (Tái dùng pattern ARCH-9.)

---

## Epic 3: Trợ lý Chat RAG & Kiểm định Trích dẫn (AI Chatbot, RAG & Citation Guardrail)

Epic này phát triển chatbot AI kết hợp RAG và bộ lọc Citation Guardrail chống trích dẫn ảo.

### Story 3.1: [Backend] Định Tuyến & Quản Lý Phiên Chat với PostgresSaver — ✅ done

Bảng `chat_threads`/`chat_messages`, API tạo thread & lấy lịch sử, tích hợp LangGraph PostgresSaver làm checkpointer phiên chat.

- **Gộp từ kế hoạch cũ:** Story 3.1 (Chat Session DB & Core APIs).
- **AC chi tiết:** `implementation-artifacts/3-1-dinh-tuyen-quan-ly-phien-chat-voi-postgressaver.md`
- **FRs:** FR6.

### Story 3.2: Chat RAG Stream Kết Quả Qua Server-Sent Events (SSE) — ✅ done

Khung LangGraph + (hiện tại) Mock RAG node, gửi tin nhắn nhận `run_id`, stream từng chunk câu trả lời qua SSE; UI khung chat + history sidebar + hiệu ứng typewriter "AI is thinking".

- **Gộp từ kế hoạch cũ:** Story 3.2 (Chat UI Shell & History Sidebar) + Story 3.3 (LangGraph Foundation & Mock RAG) + Story 3.4 (SSE Chat Streaming API).
- **AC chi tiết:** `implementation-artifacts/3-2-chat-rag-stream-ket-qua-qua-server-sent-events-sse.md`
- **FRs:** FR6.
- **⚠️ Ghi chú nợ kỹ thuật:** RAG khởi đầu là **Mock node** (`mock_rag_node`); được thay bằng retriever thật ở **Story 3.6** (pgvector cosine similarity + `citation_map` ordinal→UUID qua SSE).

### Story 3.3: Chatbot Định Hướng Dựa Trên Trạng Thái Dự Án — ✅ done

Phân tích state snapshot (`active_tab`, `document_count`, `has_draft`) sinh gợi ý hành động, hiển thị thành Quick Reply pills điều hướng nhanh.

- **Gộp từ kế hoạch cũ:** Story 3.6 (Context-Aware Suggestion API) + Story 3.7 (Quick Reply Action UI).
- **AC chi tiết:** `implementation-artifacts/3-3-chatbot-dinh-huong-dua-tren-trang-thai-du-an.md`
- **FRs:** FR15.

### Story 3.4: Citation Guardrail Node Chống Trích Dẫn Ảo — ✅ done

Node Guardrail đối chiếu các thẻ `[id]` trong câu trả lời với `valid_citation_ids` của retriever, thay thẻ ảo bằng `[Nguồn không xác định]`; kèm API `GET /api/citations/{chunk_id}` trả `{title, text}`.

- **Gộp từ kế hoạch cũ:** Story 3.8 (Citation Guardrail Node Logic) + Story 3.9 (Citation Detail Fetch API).
- **AC chi tiết:** `implementation-artifacts/3-4-citation-guardrail-node-chong-trich-dan-ao.md`
- **FRs:** FR8, FR10.

### Story 3.5: Giao Diện Tương Tác Thẻ Trích Dẫn — ✅ done

Render `[N]` thành badge `.citation-link` xanh cobalt, hover hiện tooltip (loading → data từ API 3.4 hoặc lỗi gracefully); streaming KHÔNG parse citation.

- **Gộp từ kế hoạch cũ:** Story 3.5 (Typewriter UI & SSE Receiver — phần xác nhận) + Story 3.10 (Interactive Citation Tooltip UI).
- **AC chi tiết:** `implementation-artifacts/3-5-giao-dien-tuong-tac-the-trich-dan.md`
- **FRs:** FR10. UX-DR6.

### Story 3.6: [BE+FE] Real RAG Retriever — pgvector Similarity & Citation Map qua SSE — ⏳ backlog

Thay `mock_rag_node` bằng retriever thật: embed câu hỏi (Gemini `text-embedding-004`), cosine similarity search trên `child_chunks.embedding` (pgvector, scope `project_id`, top-K), sinh câu trả lời có trích dẫn `[N]` bằng LLM (stream token thật qua SSE), trả `valid_citation_ids` (ordinals) cho Citation Guardrail và emit `citation_map` (ordinal→chunk UUID) qua SSE để frontend Story 3.5 hiển thị tooltip thật. Đồng thời sửa lỗi `CitationBadge` đang gửi ordinal vào API `/citations/{uuid}` (422).

- **Gộp từ kế hoạch cũ:** Hiện thực hóa phần Real RAG của Story 3.3 gốc (LangGraph + RAG), vốn bị tách thành Mock node ở Story 3.2. Gỡ nợ kỹ thuật ghi ở "Khoảng trống đã biết".
- **Quyết định chốt (correct-course 2026-06-17):** (a) Stream **token thật** từ LLM (`astream`), không giữ giả-stream 50ms; (b) Khi retrieval rỗng → trả câu cố định "Chưa có tài liệu liên quan trong dự án để trích dẫn.", không gọi LLM (chống hallucination).
- **AC chi tiết:** sẽ tạo qua `bmad-create-story` tại `implementation-artifacts/3-6-real-rag-retriever-pgvector-citation-map-sse.md`. Tham chiếu `sprint-change-proposal-2026-06-17.md`.
- **FRs:** FR6, FR10, NFR3.

---

## Epic 4: Bản đồ Tri thức & Phân tích Đồ thị (Knowledge Graph Synchronization & Exploration)

Epic này trực quan hóa và đồng bộ hóa mạng lưới trích dẫn giữa các bài báo sử dụng Neo4j và Cytoscape.js, đồng thời hiện thực hóa hệ con Gap Detection (FR7) đã mô tả trong `architecture.md` (§5.2, §6.2, §7).

> **🏗️ Thứ tự thực thi & ưu tiên (cốt lõi trước, râu ria sau — Winston/Architect, correct-course 2026-06-17):**
> Story đã **gộp còn 5 (đánh số tuần tự 4.1–4.5)** để giảm số lần vibecode mà mỗi story vẫn là một slice gọn (cốt lõi 🟢 → trí tuệ/FR7 🟡).
>
> | Story | Tier | Phụ thuộc |
> |---|---|---|
> | 4.1 Sync Postgres→Neo4j **+ GC** | 🟢 Cốt lõi (+ops ride-along) | — |
> | 4.2 Knowledge Map UI (đọc+vẽ + Node Detail + sync indicator) | 🟢 Cốt lõi | 4.1 |
> | 4.3 Graph Extraction (ontology) | 🟡 Trí tuệ (FR7) | 2.5, 4.1 |
> | 4.4 Gap Detection trên Map (engine + tô viền + bridge→chat) | 🟡 Trí tuệ (FR7) | 4.1, 4.3 |
> | 4.5 Gap Analyst Agent + Supervisor | 🟡 Trí tuệ (FR7) | 3.6, 4.4 |
>
> 🏁 **Milestone sau 4.2:** Knowledge Map tương tác chạy & demo được (FR9 core). · 🏁 **Sau 4.4:** Phát hiện khoảng trống trực quan trên đồ thị (FR7 via map). · 🏁 **Sau 4.5:** FR7 qua chat.
> Tham chiếu: `sprint-change-proposal-2026-06-17-gap-detection.md`. (Gộp 8→5 story, 2026-06-17: [Cytoscape + Node Detail]→4.2; [Engine + tô viền]→4.4; Extraction→4.3; Agent→4.5; **GC gộp vào 4.1**. **Leiden + community summaries → Phase 2**, gap detection MVP dùng Cypher traversal. Sync-indicator + Graph↔Chat bridge nhúng vào AC 4.2/4.4/4.5.)

### Story 4.1: [Backend] Đồng bộ Postgres → Neo4j Event-Driven qua Outbox Worker (+ Garbage Collection) — ⏳ backlog 🟢

Driver Neo4j + Cypher MERGE, worker ARQ quét `sync_outbox` (SELECT ... FOR UPDATE SKIP LOCKED + Redis lock theo project_id) dịch event sang Neo4j. **Kèm Garbage Collection:** cronjob 2h sáng xóa cứng dữ liệu `is_deleted=true` quá 7 ngày khỏi Postgres và Neo4j (DETACH DELETE).

- **Gộp từ kế hoạch cũ:** Story 4.1 (Neo4j Connection & Base Cypher) + Story 4.2 (Outbox Worker Foundation) + Story 4.3 (Event-Driven Graph Sync) + **Story 4.4 (Graph Garbage Collection)**.
- **Lưu ý mở rộng (Architect 2026-06-17):** Ngoài Paper/CITES/Author, worker còn đồng bộ **ontology học thuật** (Finding/Limitation + edges `[:CONTRADICTS]`/`[:SUPPORTS]`/`[:HAS_LIMITATION]`/`[:FILLS_GAP]`) do Story 4.3 ghi vào `sync_outbox`.
- **🔸 GC gộp vào đây (Architect 2026-06-17):** GC dùng chung Neo4j driver + module sync-lifecycle nên gộp tiết kiệm một session. Là phần **"ride-along" không chặn** — làm sau cùng trong story, không ảnh hưởng đường demo (read path). Tôn trọng ARCH-2 (xóa mềm + cron 2h sáng + ngưỡng 7 ngày).
- **🧭 Nhãn module/role (role-clarity 2026-06-17):** Story xuyên 4 module — `[shared]` Neo4j driver (`neo4j_client.py`) · `[ingestion]` **producer** `PAPER_UPSERTED` (**retrofit vá nợ Story 2.5**, code đặt trong `worker.py`) · `[graph_rag]` **consumer** worker + GC · `[workspace]` migration `sync_outbox`/`projects` (+`[ingestion]` migration `papers.deleted_at`). 4.1 tạo **constraints base** (Paper/Author/Project); **constraints + handler MERGE ontology là của Story 4.3**, 4.1 chỉ dựng **dispatch map mở-rộng-được**.
- **FRs:** FR9, ARCH-8, **ARCH-2**.

### Story 4.2: [BE+FE] Knowledge Map UI — Đọc & Vẽ Đồ thị Cytoscape.js + Node Detail Card — ⏳ backlog 🟢

**BE —** endpoint đọc đồ thị từ Neo4j: `GET /api/projects/{project_id}/graph` trả node/edge ban đầu giới hạn **150 nodes / 300 edges** kèm cờ `has_more`; `GET /api/projects/{project_id}/graph/nodes/{node_id}/expand` trả 1-hop lân cận (≤20 thực thể mới). JWT + owner scoping.
**FE —** Canvas Cytoscape.js zoom/pan, lazy rendering, incremental layout (`fcose`/`cola`) khi expand không xáo trộn node cũ; **Node Detail Card** trượt ra góc trên bên phải khi click node (tiêu đề, tác giả, năm, tóm tắt).

- **Gộp:** [4.2 Cytoscape draw] + [4.3 Node Detail Card] cũ — cùng một component canvas → một session liền mạch (gộp 2026-06-17). Truy về kế hoạch 38-story: Story 4.5 (Cytoscape Foundation) + 4.6 (Lazy Expand API) + 4.7 (Interactive Graph UI — Details).
- **🔸 Bổ sung phủ UX (Architect 2026-06-17 — vá lỗ hổng tab Graph):**
  - **(A) Endpoint đọc đồ thị** (ở trên) — trước đây thiếu chủ; đổi nhãn story sang **[BE+FE]** vì FE không có gì để vẽ nếu thiếu nó (ARCH §8.4).
  - **(B) Phân biệt trạng thái node:** node **toàn văn** (đã tải PDF) = xanh lá `state-success` viền đậm; node **chỉ metadata** (paywalled) = vòng tròn nét đứt viền cam `state-warning` (DESIGN §5).
  - **(C) Mạng lưới tác giả:** render node Author + cạnh `[:AUTHORED]` (tím nét đứt `accent-violet`); cạnh `[:CITES]` xanh `accent-blue` có mũi tên. Có thể thêm toggle ẩn/hiện tác giả (UJ-2, DESIGN §5).
  - **(D) Chú giải (Legend):** chú thích nhỏ giải nghĩa màu node/cạnh trên canvas.
  - **(E) Chỉ báo đồng bộ đồ thị (sync indicator):** badge *"Đồ thị đang cập nhật…"* khi còn event `sync_outbox` chưa xử lý cho project (Neo4j *eventual consistency* — đồ thị trễ sau Postgres). Tránh user tưởng mất dữ liệu (đúng triết lý đồng bộ tức thời PRD §1.1).
  - **(F) Cầu nối Graph→Chat:** trên Node Detail Card thêm nút *"Hỏi AI về bài này"* → gửi tin nhắn chat (dùng khung chat Epic 3) hỏi về bài báo đó. Hiện thực hóa Co-existent Redundant Pathways (PRD §1.1).
- **Phụ thuộc:** Story 4.1.
- **FRs:** FR9, ARCH-7, ARCH-9 (owner scoping). UX-DR7.

### Story 4.3: [Backend] Graph Extraction — Trích xuất Ontology Học thuật (Stage-2 Ingestion) — ⏳ backlog 🟡

Hiện thực Giai đoạn 2 pipeline ingest (`gemini-2.5-pro`): từ Markdown đã cấu trúc hóa (GĐ1, Story 2.5), bóc tách Nodes học thuật (Finding`{confidence_score}`, Limitation, Method, Dataset, Topic, Problem) + Edges (`[:HAS_FINDING]`, `[:HAS_LIMITATION]`, `[:CONTRADICTS]`, `[:SUPPORTS]`, `[:FILLS_GAP]`), kèm Author entity resolution. Ghi vào `sync_outbox` để Story 4.1 đẩy sang Neo4j.

- **Gộp từ kế hoạch cũ:** Phát sinh trong thực thi (correct-course 2026-06-17). Hiện thực hóa ARCH §6.2 (GĐ2 Graph Extraction) + §5.2 (Graph Schema).
- **Quyết định kiến trúc (Architect 2026-06-17):** (a) **MỞ RỘNG arq worker của Story 2.5** (module `ingestion`), tái dùng output GĐ1 — KHÔNG dựng worker/pass quét lại tài liệu (chống lãng phí token `gemini-2.5-pro`). (b) **Backfill bắt buộc:** doc đã ingest trước story này thiếu ontology → AC phải có bước re-enqueue extraction cho doc cũ (hoặc chấp nhận chỉ doc mới có graph — ghi rõ). (c) Chốt lại version model khi create-story (doc lệch 1.5 §7 vs 2.5 §6.2).
- **🧭 Nhãn module/role (role-clarity 2026-06-17):** Story xuyên 2 module — `[ingestion]` **Stage-2 Graph Extraction** (mở rộng worker 2.5, là Giai đoạn 2 của pipeline §6.2, đóng vai **PRODUCER** ghi ontology event vào `sync_outbox`) · `[graph_rag]` tạo **Unique Constraints ontology** (Finding/Limitation/…) + **handler MERGE ontology** đăng ký vào dispatch map khung-mở-rộng của 4.1. Epic 4 giữ story này vì *value* = FR7, nhưng phần lớn **code lõi nằm ở module `ingestion`**, không phải `graph_rag`.
- **Phụ thuộc:** Story 2.5 (pipeline + worker arq, đã done), Story 4.1 (sync để hiển thị).
- **FRs:** FR7, FR9. (ARCH §5.2, §6.2.)

### Story 4.4: [BE+FE] Gap Detection trên Bản đồ — GraphRAG Engine & Tô viền Khoảng trống — ⏳ backlog 🟡

**BE — GraphRAG Engine (Module 1)** trên Neo4j: `gap_detection(project_id)->GapContext` (cụm node cô lập + `[:CONTRADICTS]` + Limitation chưa `[:FILLS_GAP]`, kết hợp tín hiệu RAG), `graph_search(entities, project_id)->GraphContext`; endpoint `GET /api/projects/{project_id}/graph/gaps`.
**FE —** chế độ "Tìm khoảng trống nghiên cứu" tô viền đỏ nhấp nháy (`[:CONTRADICTS]`) / vàng (cụm cô lập) trên canvas Cytoscape, dựa trên endpoint trên.

- **Gộp:** [4.5 GraphRAG Engine] + [4.6 tô viền gap] cũ — vertical slice BE endpoint + đúng FE tiêu thụ, test end-to-end ngay (gộp 2026-06-17). Hiện thực hóa ARCH §5.2 (Module 1 API) + phần gap-highlight của Story 4.7 gốc (38-story).
- **🔸 Phạm vi MVP (Architect, cập nhật 2026-06-17):** Gap detection cốt lõi chạy bằng **Cypher traversal** (cụm cô lập, CONTRADICTS, Limitation chưa FILLS_GAP) — đủ cho FR7. **Leiden community detection + Hierarchical Community Summaries + `community_summary_search` chuyển sang Phase 2** (xem cuối tài liệu) vì là enhancement GraphRAG, phức tạp hơn mức cần cho MVP. `graph_search` (Cypher neighborhood) GIỮ ở MVP để phục vụ Story 4.5.
- **Lưu ý kiến trúc:** Quy mô đồ thị chặn trên bởi `MAX_PAPERS_PER_PROJECT=15` → Cypher traversal rất rẻ. Cypher scope `project_id` chống IDOR.
- **🔸 Cầu nối Gap→Chat (Architect 2026-06-17):** click viền cảnh báo (node/cụm) → nút *"Giải thích khoảng trống này"* mở chat với câu hỏi tương ứng → Gap Analyst Agent (Story 4.5) trả lời có nguồn. Nếu 4.5 chưa xong, fallback gửi câu hỏi vào chat RAG thường.
- **Phụ thuộc:** Story 4.1 (Neo4j có dữ liệu), Story 4.3 (ontology).
- **FRs:** FR7, FR9. UX-DR7. (ARCH §5.2.)

### Story 4.5: [BE+FE] Gap Analyst Agent & Supervisor Routing trong LangGraph — ⏳ backlog 🟡

Tiến hóa orchestrator (sau Story 3.6) từ single RAG node sang topology Router-Worker (ARCH §7.1): Supervisor định tuyến → Research&RAG Agent hoặc Gap Analyst Agent. Gap Analyst Agent gọi `gap_detection_tool` + `graph_search_tool` (Story 4.4), sinh câu trả lời mâu thuẫn/hạn chế **chỉ rõ nguồn `[N]`** (FR7) qua Citation Guardrail (Story 3.4). Research&RAG Agent bổ sung `graph_search` vào fusion context (ARCH §7.4).

- **Gộp từ kế hoạch cũ:** Phát sinh trong thực thi (correct-course 2026-06-17). Hiện thực hóa ARCH §7.1, §7.2, §7.4.
- **Quyết định kiến trúc (Architect 2026-06-17):** Cân nhắc **router nhẹ/lazy** — RAG là nhánh mặc định, chỉ rẽ Gap Analyst khi intent "khoảng trống/mâu thuẫn" rõ ràng, để **giữ SM-3 (first-chunk < 3s)** không bị thêm 1 hop LLM phân loại đầy đủ. Tích hợp nặng nhất Epic 4 → để cuối nhóm trí tuệ.
- **🔸 Cầu nối Gap→Chat (Architect 2026-06-17):** Gap Analyst Agent là backend cho nút *"Giải thích khoảng trống này"* (Story 4.4) và *"Hỏi AI về bài này"* (Story 4.2) — đảm bảo trả lời gap qua chat có nguồn `[N]`.
- **🧭 Nhãn module/role (role-clarity 2026-06-17):** Code lõi thuộc module **`[orchestrator]`** (graph LangGraph, §9.7) — **tiến hóa code đã build ở Epic 3** (3.2/3.6): single RAG node → topology Router-Worker. **Cross-epic touch hợp lệ** nhưng **KHÔNG được regress AC Epic 3 + SM-3 (first-chunk < 3s)**; RAG vẫn là **nhánh mặc định**, Gap Analyst là worker **thêm vào**. Gọi tool sang `[graph_rag]` (gap_detection/graph_search của 4.4) qua Port — không truy cập thẳng Neo4j (§9.6).
- **Phụ thuộc:** Story 3.6 (real RAG node + SSE protocol), Story 4.4 (gap_detection/graph_search tools).
- **FRs:** FR6, FR7. (ARCH §7.)

> **ℹ️ Garbage Collection (ARCH-2)** đã **gộp vào Story 4.1** (cùng module sync/Neo4j-lifecycle) — xem Story 4.1.

---

## Epic 5: Soạn thảo Tổng quan & Cấu hình Hệ thống (Literature Review Workspace & Settings)

Epic này phát triển không gian soạn thảo nháp, xuất báo cáo và trang cấu hình hệ thống dành cho Admin.

### Story 5.1: [BE+FE] Soạn thảo Literature Review & Quản lý Bản thảo — ⏳ backlog

Rich editor (Tiptap/Quill), API CRUD bản nháp, auto-save mỗi 10s + chỉ báo trạng thái "Đã lưu".

- **Gộp từ kế hoạch cũ:** Story 5.1 (Draft Versioning API) + Story 5.2 (Rich Text Editor Foundation) + Story 5.3 (Auto-save & History UI).
- **FRs:** FR13.

### Story 5.2: [BE+FE] Đóng gói & Xuất Bản thảo chuẩn Markdown + BibTeX — ⏳ backlog

API gom text + bib nén `export.zip` (Markdown .md + BibTeX .bib) trả File Stream, kèm nút "Xuất file" tải về.

- **Gộp từ kế hoạch cũ:** Story 5.4 (ZIP Export API) + Story 5.5 (Export Button).
- **FRs:** FR14.

### Story 5.3: [BE+FE] Cài đặt Hệ thống Động của Admin – Lưu Cơ sở Dữ liệu — ⏳ backlog

Trang Admin Settings chỉnh tham số động (`MAX_PAPERS_PER_PROJECT`, `BROAD_QUERY_THRESHOLD`, `MAX_UPLOAD_SIZE_MB`...), PATCH lưu Postgres không restart; user thường nhận 403.

- **Gộp từ kế hoạch cũ:** Story 5.6 (Admin Settings Management).
- **Bổ sung (correct-course 2026-06-17):** Đưa `MAX_UPLOAD_SIZE_MB` vào danh sách key động — hiện đang là biến môi trường tĩnh `max_upload_size_mb=20` ([settings.py:65](backend/src/shared/infra/settings.py#L65)), chưa nằm trong `system_settings`. Hoàn thiện FR12 (PRD đã hứa "kích thước file upload tối đa" là setting động). Mặc định giữ 20MB (NFR2); Admin tự nâng tay sau khi story xong.
- **FRs:** FR12. UX-DR10.

### Story 5.4: [Frontend] Trang Landing Page Vãng lai & Bản Demo Mô phỏng — ⏳ backlog

Landing page cuộn dọc: Hero banner, interactive demo simulator 3 cột, pricing table gói Student/Researcher.

- **Gộp từ kế hoạch cũ:** Story mới phát sinh trong thực thi (chưa có trong bản 38-story gốc). Hiện thực hóa UX-DR5 + UX-DR8.
- **FRs:** UX-DR5, UX-DR8.

---

## Khoảng trống đã biết (Known Gaps — chưa có story)

> Ghi nhận trong lúc đồng bộ tài liệu (2026-06-17) để phục vụ việc tạo story mới.

- **Real RAG Retrieval Node (thay `mock_rag_node`):** ✅ **Đã tạo Story 3.6** (correct-course 2026-06-17) để hiện thực hóa — pgvector cosine similarity trên `child_chunks.embedding`, trả `valid_citation_ids` (ordinals) cho Citation Guardrail, và emit `citation_map` (ordinal→chunk UUID) qua SSE cho tooltip. Đồng thời sửa lỗi 422 do `CitationBadge` gửi ordinal thay vì UUID vào `/api/citations/{uuid}`. Xem Epic 3 — Story 3.6 và `sprint-change-proposal-2026-06-17.md`. Liên quan FR6, FR10, NFR3.

- **Gap Detection Backend (FR7) — Graph Extraction / GraphRAG Engine / Gap Analyst Agent:** ✅ **Đã tạo Story 4.3 (Graph Extraction), 4.4 (GraphRAG Engine + tô viền gap), 4.5 (Gap Analyst Agent)** (correct-course + Architect review 2026-06-17, sau gộp 8→6 story) để hiện thực hóa hệ con ontology học thuật (Finding/Limitation + edges CONTRADICTS/SUPPORTS/HAS_LIMITATION/FILLS_GAP), `gap_detection`/`graph_search` (Cypher traversal; Leiden communities → Phase 2), và agent phân tích khoảng trống qua chat. Trước đó Epic 4 chỉ phủ FR9 (vẽ), thiếu toàn bộ phần *sinh* dữ liệu khoảng trống mà `architecture.md` (§5.2, §6.2, §7) đã mô tả. Knowledge Map UI (Cytoscape + Node Detail) gộp thành Story 4.2. Xem Epic 4 và `sprint-change-proposal-2026-06-17-gap-detection.md`. Liên quan FR7, FR9.

---

## Hoãn sang Phase 2 (Deferred — ngoài phạm vi MVP)

> Ghi nhận để không mất dấu; sẽ tạo story khi mở Phase 2.

- **Leiden Community Detection + Hierarchical Community Summaries + `community_summary_search` (GraphRAG Communities):** Hoãn từ Story 4.4 sang **Phase 2** (quyết định Dat + Architect, 2026-06-17) vì phức tạp hơn mức cần cho MVP. Gap detection MVP (Story 4.4) đã đủ FR7 bằng **Cypher traversal** (cụm cô lập + CONTRADICTS + Limitation chưa FILLS_GAP). Khi mở Phase 2: thêm worker ngầm chạy Leiden gom Community + `gemini-1.5-flash` tóm tắt phân cấp, lưu ngược Neo4j, và API `community_summary_search` cho GraphRAG dual-level retrieval. Tham chiếu ARCH §5.2 (Graph Indexing).
