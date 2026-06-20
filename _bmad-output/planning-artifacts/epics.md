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
> Tổng: **33 story** (đã gộp từ 38 story chia nhỏ của bản kế hoạch gốc; +2 story 2.7/3.6 phát sinh trong thực thi; Epic 4 bổ sung Gap Detection backend rồi **gộp còn 5 story 4.1–4.5** (GC gộp vào 4.1) để giảm số lần vibecode — correct-course + Architect 2026-06-17; **+3 story follow-up 4.6/4.7/4.8** — CITES/FILLS_GAP producers + tách màu gap, correct-course 2026-06-18, Epic 4 mở lại in-progress; **+2 story FE 3.7/3.8** — render markdown chat + tái cấu trúc layout workspace, correct-course 2026-06-18). AC chính thức của story đã hoàn thành nằm ở file story tương ứng trong `implementation-artifacts/`.

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

### Story 3.7: [Frontend] Render Markdown trong câu trả lời Chatbot (giữ CitationBadge) — ⏳ backlog 🟢

Bọc nội dung câu trả lời chatbot bằng `react-markdown` + `remark-gfm` + `rehype-sanitize` để render đẹp (heading, bullet/numbered list, bold/italic, bảng, xuống dòng), ĐỒNG THỜI giữ nguyên thẻ trích dẫn `[N]` tương tác (`CitationBadge` + tooltip Story 3.5) bằng cách override renderer text/p để chạy logic split `[N]`.

- **Phát sinh:** correct-course 2026-06-18 (câu trả lời hiện markdown thô, viết liền khó đọc).
- **🧭 Nhãn module/role:** `[frontend]` thuần — `components/MessageContent.tsx` (+ `CitationBadge` tái dùng).
- **Phụ thuộc:** Story 3.5 (CitationBadge), Story 3.6 (content + citationMap). KHÔNG phụ thuộc 3.8.
- **FRs:** FR6.

**AC nháp (chi tiết hóa khi create-story):**
1. Thêm `react-markdown` + `remark-gfm` + `rehype-sanitize` vào frontend; sanitize BẮT BUỘC (nội dung LLM sinh).
2. `MessageContent` render markdown của `msg.content`; heading/list/bold/italic/bảng/xuống dòng hiển thị đúng.
3. Thẻ `[N]` trong markdown vẫn render thành `CitationBadge` tương tác (override renderer text/p; tái dùng `CitationBadge` + citationMap ordinal→UUID), kể cả khi `[N]` nằm trong `<p>`/`<li>`/`<td>`.
4. Streaming: markdown render trên chuỗi đang chạy; markdown chưa đóng hiện tạm thô rồi tự đẹp khi token tới — không crash.
5. Không phá link tooltip Story 3.5; không mở lỗ XSS (test thử input markdown độc hại).
6. Tin nhắn user (không có citationMap) vẫn render an toàn.

### Story 3.8: [Frontend] Tái cấu trúc Layout Workspace — Ô chat độc lập trên cùng + đảo cột — ⏳ backlog 🟡

Tái cấu trúc shell layout (`DashboardPage`): hàng trên cùng = brand **"Trợ lý nghiên cứu"** (thay "C2 Research") + nút hệ thống thành MỘT dải liền, tách phần dưới bằng kẻ ngang suốt. Phần dưới: sidebar dự án (trái) | main = **Ô CHAT ĐỘC LẬP trên cùng** (~½ màn, canh giữa, luôn hiện) + thân (cột **"Nội dung trò chuyện" GIỮA**, kéo mở rộng/thu hẹp/ẩn — chỉ ẩn messages, KHÔNG ẩn ô chat; cột nội dung **3 tab PHẢI** có dấu `›` ngăn cách, **GIÃN RỘNG khi cột trò chuyện thu hẹp**). Ô chat tách khỏi `ChatbotPanel` thành component dùng chung toàn project.

- **Phát sinh:** correct-course 2026-06-18. Tham chiếu mockup: `test-data/mockups/layout-chat-top.html`.
- **🧭 Nhãn module/role:** `[frontend]` thuần — `DashboardPage`(+css), `ChatbotPanel` (tách input/messages), `CenterWorkspace` (3 tab + sep), header/brand.
- **Phụ thuộc:** Story 3.6 (chat hoạt động). Nên làm SAU 3.7 để câu trả lời đã đẹp.
- **FRs:** FR6, FR9 (Knowledge Map nằm trong cột nội dung).

**AC nháp:**
1. Hàng trên cùng: brand "🔬 Trợ lý nghiên cứu" + badge project (góc trái) + nút Cài đặt/API Keys/đổi theme/VI|EN/Đăng xuất (phải) — MỘT dải liền KHÔNG vạch dọc, tách phần dưới bằng 1 đường kẻ ngang chạy suốt.
2. Ô chat độc lập (input + nút Gửi + suggestion pills) ngay dưới hàng trên cùng, rộng ~50% màn (min hợp lý), canh giữa; LUÔN hiển thị bất kể trạng thái cột trò chuyện.
3. Sidebar dự án bên trái (Tạo dự án + danh sách) — viền phải chỉ chạy ở phần dưới hàng trên cùng.
4. Cột "Nội dung trò chuyện" Ở GIỮA: chỉ chứa messages, có resize handle + nút collapse/ẩn (giữ hành vi cũ); thu hẹp/ẩn → chỉ ẩn messages.
5. Cột nội dung 3 tab Ở BÊN PHẢI: tab có dấu `›` ngăn cách; khi cột trò chuyện thu hẹp/ẩn → cột 3 tab GIÃN RỘNG chiếm chỗ trống.
6. Gửi tin từ ô chat độc lập → vẫn route đúng vào luồng chat hiện có (thread/SSE Story 3.1/3.2/3.6); state input dùng chung, không phụ thuộc cột trò chuyện hiển thị hay không.
7. Knowledge Map (Cytoscape) re-fit đúng khi cột nội dung đổi kích thước (collapse cột trò chuyện); không vỡ layout 3 tab.
8. Regression: 3 tab + Node Detail + gap mode (Story 4.2/4.4) chạy đúng trong khung mới; responsive không vỡ.

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
> | 4.6 CITES Producer (mở khóa cụm cô lập) | 🟡 Trí tuệ (FR7) | 4.1, 4.3 |
> | 4.7 FILLS_GAP Producer (LLM-judge, mở khóa unfilled limitation) | 🟡 Trí tuệ (FR7) | 4.1, 4.3 |
> | 4.8 Tách màu 3 loại Gap + Legend | 🟢 FE nhỏ | 4.4 |
>
> 🏁 **Milestone sau 4.2:** Knowledge Map tương tác chạy & demo được (FR9 core). · 🏁 **Sau 4.4:** Phát hiện khoảng trống trực quan trên đồ thị (FR7 via map). · 🏁 **Sau 4.5:** FR7 qua chat. · 🏁 **Sau 4.6+4.7+4.8:** Gap detection phản ánh khoảng trống THẬT (CITES/FILLS_GAP đã sinh) + 3 màu phân biệt rõ.
> **Thứ tự follow-up (correct-course 2026-06-18):** 4.8 (FE, song song được) · 4.6 → 4.7 (ingestion). Tham chiếu: `sprint-change-proposal-2026-06-18-cites-fillsgap-producers.md`.
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

### Story 4.6: [Backend] CITES Producer — Trích references & Khớp Paper (mở khóa "cụm cô lập") — ⏳ backlog 🟡

Bổ sung Stage-2 ingestion (mở rộng Story 4.3): trích danh sách references/trích dẫn từ Markdown đã cấu trúc hóa + metadata, khớp mỗi reference với Paper hiện có trong project (DOI exact → fallback fuzzy title / embedding), rồi ghi sự kiện `CITES {citing_paper_id, cited_paper_id}` vào `sync_outbox` để Story 4.1 MERGE cạnh `[:CITES]` vào Neo4j. Mở khóa Query 2 của `gap_detection` (cụm cô lập) phản ánh thật.

- **Phát sinh:** correct-course 2026-06-18 (kiểm thử Story 4.4 lộ "mọi node vàng"). Hiện thực hóa ARCH §5.2 (`[:CITES]`) + §3.5 (mạng lưới trích dẫn).
- **🧭 Nhãn module/role:** `[ingestion]` producer CITES (mở rộng worker Stage-2 §6.2) · `[graph_rag]` handler `handle_cites` **ĐÃ CÓ** (Story 4.1) — chỉ cần producer.
- **Phụ thuộc:** Story 4.1 (handler + sync), Story 4.3 (Stage-2 worker để gắn vào).
- **FRs:** FR7, FR9. (ARCH §5.2.)
- **⚠️ Follow-up:** giá trị (cạnh CITES thật) chỉ hiện thực hóa sau **Story 4.9** — 4.6 đúng logic nhưng References bị cắt ở tầng parse (`DocumentParser` 2 trang/4000 ký tự) nên LLM trả `references=[]`. Xem `sprint-change-proposal-2026-06-19-cites-references-truncation.md`.

**AC nháp (chi tiết hóa khi create-story):**
1. Stage-2 trích references (title + DOI + năm nếu có) từ Markdown/metadata; rỗng → bỏ qua an toàn, không lỗi.
2. Khớp reference → Paper trong CÙNG project: ưu tiên DOI exact; fallback so khớp tiêu đề chuẩn hóa (lowercase/bỏ dấu) + ngưỡng tương đồng (vd cosine title ≥ 0.85). Không khớp → bỏ (không tạo Paper ma).
3. Ghi `sync_outbox` event CITES `{citing_paper_id, cited_paper_id}` — idempotent, scope `project_id`; KHÔNG tự-trích-dẫn (citing ≠ cited).
4. Handler `handle_cites` (Story 4.1) MERGE `[:CITES]`; chạy lại không nhân đôi cạnh.
5. Re-ingest / thêm paper mới → cập nhật cạnh CITES tăng dần (forward-compat); nêu rõ giới hạn nếu không backfill toàn bộ.
6. Tôn trọng worker arq (concurrency_limit=2); log số reference khớp/không-khớp để quan sát chất lượng matching.

### Story 4.7: [Backend] FILLS_GAP Producer — LLM-judge Limitation↔Paper (mở khóa "limitation chưa giải quyết") — ⏳ backlog 🟡

Worker bất đồng bộ xác định cạnh `[:FILLS_GAP]`: với mỗi Limitation chưa được lấp trong project, **tiền lọc** ứng viên Paper bằng embedding (cosine ≥ ngưỡng), rồi gọi **LLM judge** (`gemini-1.5-flash`) *"Bài X có giải quyết hạn chế này của bài Y không?"* → nếu CÓ, ghi `sync_outbox` `FILLS_GAP {filler_paper_id, limitation_id}` để Story 4.1 MERGE `(:Paper)-[:FILLS_GAP]->(:Limitation)`. Mở khóa Query 3 của `gap_detection` phản ánh thật. **CHẠY NGẦM (arq/cron) — KHÔNG đồng bộ với nút "Tìm khoảng trống"** (giữ `gap_detection` = Cypher read nhanh).

- **Phát sinh:** correct-course 2026-06-18. Hiện thực hóa ARCH §5.2 (`(:Paper)-[:FILLS_GAP]->(:Limitation)`).
- **Quyết định kiến trúc (Dat 2026-06-18):** Chọn **LLM-judge** (chính xác) thay vì embedding-only; embedding chỉ làm **TIỀN LỌC** để cắt N×M lời gọi.
- **🧭 Nhãn module/role:** `[ingestion]` producer FILLS_GAP (worker ngầm) · `[graph_rag]` handler FILLS_GAP **MỚI** vào dispatch map của 4.1.
- **Phụ thuộc:** Story 4.1 (sync + thêm handler), Story 4.3 (Limitation/Finding ontology đã tồn tại).
- **FRs:** FR7, FR9. (ARCH §5.2.)

**AC nháp:**
1. Worker quét các Limitation trong project chưa có cạnh `[:FILLS_GAP]` (idempotent, không judge lại cặp đã quyết).
2. TIỀN LỌC: với mỗi Limitation, chọn top-K Paper ứng viên có cosine(embedding) ≥ ngưỡng (vd 0.65) — KHÔNG judge toàn bộ N×M.
3. LLM judge (`gemini-1.5-flash`) trên từng cặp (Limitation, Paper ứng viên): trả `{fills: bool, lý do ngắn}`; prompt yêu cầu "chỉ trả CÓ nếu paper thực sự giải quyết/lấp hạn chế này".
4. fills=true → ghi `sync_outbox` FILLS_GAP `{filler_paper_id, limitation_id}`; filler ≠ paper sở hữu limitation đó.
5. Handler FILLS_GAP mới (graph_rag): MATCH Paper + Limitation theo id (scope `project_id`) → MERGE `[:FILLS_GAP]`; idempotent.
6. CHẠY NGẦM (arq concurrency_limit=2 / cron sau ingest). KHÔNG nằm trên đường bấm nút gap. Cache theo `(limitation_id, candidate_paper_id)` tránh gọi lại; LLM qua LLMRouter (user→system fallback), retry/Tenacity khi rate-limit.
7. Ngưỡng thận trọng + log mọi quyết định (judge yes/no + lý do) để chỉnh; empty/ít dữ liệu → an toàn, không bịa cạnh.

### Story 4.8: [Frontend] Tách màu 3 loại Gap + Chú giải Gap có điều kiện — ⏳ backlog 🟢

Trên Knowledge Map (Story 4.2/4.4), tách màu node theo `reason` để phân biệt rõ 3 loại khoảng trống: **đỏ** = mâu thuẫn (`has_contradiction`), **cam** = limitation chưa giải quyết (`has_unfilled_limitation`), **xanh** = cụm cô lập (`isolated_cluster`). Bổ sung mục chú giải gap vào GraphLegend, chỉ hiển thị khi gap mode ON.

- **Phát sinh:** correct-course 2026-06-18 (gộp 2 reason vào 1 màu vàng gây nhầm — quyết định MVP "Option A" của Story 4.4 nay nâng cấp).
- **🧭 Nhãn module/role:** `[frontend]` thuần — KnowledgeMapTab `CY_STYLE` + GraphLegend.
- **Phụ thuộc:** Story 4.4 (gap mode + `reason` đã có trong response). KHÔNG phụ thuộc 4.6/4.7 (làm trước được ngay).
- **FRs:** FR9.

**AC nháp:**
1. Map `reason` → 3 class: `has_contradiction` → `gap-contradiction` (đỏ #EF4444, giữ); `has_unfilled_limitation` → `gap-unfilled` (cam #F59E0B, MỚI); `isolated_cluster` → `gap-isolated` (xanh #3B82F6, đổi nghĩa: chỉ còn cô lập).
2. Thêm selector `node.gap-unfilled` vào `CY_STYLE`; animation pulsing áp cho cả 3 class.
3. Dedup priority giữ nguyên (contradiction > unfilled > isolated) — màu hiển thị theo reason ưu tiên.
4. GraphLegend: thêm 3 dòng chú giải gap (đỏ/cam/xanh ↔ tên loại), CHỈ render khi `gapMode = true`; tắt gap mode → ẩn.
5. NodeDetailCard "Giải thích khoảng trống này": prefill khác nhau theo 3 reason (đã có ở 4.4, kiểm tra map đủ 3 nhánh).
6. Toggle OFF → removeClass cả 3 + removeStyle `border-width` (giữ fix review 4.4, không sót inline style).

### Story 4.9: [Backend+FE] Sửa cắt text khi parse — kích hoạt References/CITES thật + giới hạn parse vào Admin Setting — ⏳ backlog 🟡

Vá lỗ hổng tích hợp lộ sau Story 4.6: `DocumentParser` cắt PDF còn 2 trang/4000 ký tự → mục References (offset thực tế 11k–45k ký tự) không bao giờ tới LLM → `GraphExtractor` trả `references=[]` → `graph_extract_task` log "0 references, bỏ qua CITES" → 0 cạnh CITES. Nâng giới hạn parse (cấu hình động qua Admin) và bỏ cơ chế cắt head/đuôi trong `GraphExtractor` (gửi thẳng full_text đã bị `INGEST_MAX_EXTRACT_CHARS` chặn).

- **Phát sinh:** correct-course 2026-06-19 (`sprint-change-proposal-2026-06-19-cites-references-truncation.md`). Hiện thực hóa giá trị Story 4.6 (marked done nhưng CITES rỗng). Lỗ hổng lọt review 4.6 vì test mock `GraphExtractor` → không chạy mốc cắt text thật.
- **🧭 Nhãn module/role:** `[ingestion]` sửa `DocumentParser` + `GraphExtractor` + `worker` · `[admin]` thêm 2 key setting động · `[frontend]` Admin Settings hiển thị 2 input.
- **Phụ thuộc:** Story 4.6 (producer CITES), Story 4.3 (Stage-2 worker + backfill endpoint), hạ tầng `system_settings` (Story 4.1).
- **FRs:** FR7, FR9. (ARCH §5.2, §8.4.)

**AC nháp (chi tiết hóa khi create-story):**
1. `DocumentParser.extract_text` nhận `max_pages`/`max_chars` (default 2/4000 — giữ hành vi cũ cho đường upload-metadata); `_extract_pdf` dùng `range(min(max_pages, len(doc)))` + `text[:max_chars]`; `_extract_docx` dùng `text[:max_chars]`.
2. 2 setting động mới (số nguyên ≥1) vào `_NUMERIC_SETTING_KEYS`: `INGEST_MAX_PDF_PAGES`=50, `INGEST_MAX_EXTRACT_CHARS`=150000 — đọc qua `get_setting(..., default=...)`, sửa được trong Admin Settings. KHÔNG cần Alembic migration.
3. `worker._extract_text` + `_download_and_persist_pdf` đọc 2 setting và áp dụng (thay `min(2,..)`/`min(20,..)`/`MAX_TEXT_LENGTH` hardcode).
4. `GraphExtractor`: bỏ `_build_extraction_text` + hằng `_EXTRACT_HEAD`/`_REF_TAIL_BUDGET`/`_REF_HEADINGS`; `extract` truyền thẳng `text` (đã bị `INGEST_MAX_EXTRACT_CHARS` chặn) vào prompt.
5. **Test tích hợp KHÔNG mock `GraphExtractor`/`DocumentParser`**: fixture nhiều trang có References ở offset >30000 → `references` được trích, `graph_extract_task` add `SyncOutboxORM("CITES")`. (Lấp đúng lỗ hổng để defect lọt.)
6. Frontend Admin Settings hiển thị + lưu 2 setting mới (i18n VI/EN), default hiển thị 50/150000.
7. Vận hành: ghi chú chạy lại `POST /admin/backfill-graph-extraction` (idempotent) sau khi đặt giá trị → 6 paper khớp lại trên corpus đầy đủ.
- **Lưu ý giới hạn:** paper dài hơn `INGEST_MAX_EXTRACT_CHARS` mà References sau mốc cắt vẫn mất reference (Admin nâng được). Ngưỡng `difflib` 0.85 giữ nguyên (defer từ 4.6). Giữ `INGEST_MAX_EXTRACT_CHARS` ~150k–200k để chặn token cost (nay là cận text gửi LLM).

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
- **CITES & FILLS_GAP Producers (FR7) — kích hoạt thật Gap Detection:** ✅ **Đã tạo Story 4.6 (CITES producer), 4.7 (FILLS_GAP LLM-judge), 4.8 (tách màu 3 loại gap)** (correct-course 2026-06-18). Trước đó Story 4.4 chạy `gap_detection` nhưng `[:CITES]` và `[:FILLS_GAP]` (đã có trong ARCH §5.2) **chưa có producer** → mọi Paper bị cờ cô lập + unfilled (nhiễu), và 2 loại gap dùng chung 1 màu vàng gây nhầm. Xem `sprint-change-proposal-2026-06-18-cites-fillsgap-producers.md`. Liên quan FR7, FR9.
- **UX Chatbot (FR6) — Markdown render + Layout workspace:** ✅ **Đã tạo Story 3.7 (render markdown câu trả lời, giữ CitationBadge) + 3.8 (tái cấu trúc layout: brand "Trợ lý nghiên cứu" + ô chat độc lập trên cùng + cột trò chuyện ở giữa, 3 tab bên phải có `›` ngăn cách)** (correct-course 2026-06-18). Trước đó câu trả lời hiện markdown thô khó đọc + ô chat bị chôn trong cột trợ lý (ẩn cột là mất ô chat). Mockup: `test-data/mockups/layout-chat-top.html`. Xem `sprint-change-proposal-2026-06-18-chat-markdown-layout.md`. Liên quan FR6, FR9.

---

## Hoãn sang Phase 2 (Deferred — ngoài phạm vi MVP)

> Ghi nhận để không mất dấu; sẽ tạo story khi mở Phase 2.

- **Leiden Community Detection + Hierarchical Community Summaries + `community_summary_search` (GraphRAG Communities):** Hoãn từ Story 4.4 sang **Phase 2** (quyết định Dat + Architect, 2026-06-17) vì phức tạp hơn mức cần cho MVP. Gap detection MVP (Story 4.4) đã đủ FR7 bằng **Cypher traversal** (cụm cô lập + CONTRADICTS + Limitation chưa FILLS_GAP). Khi mở Phase 2: thêm worker ngầm chạy Leiden gom Community + `gemini-1.5-flash` tóm tắt phân cấp, lưu ngược Neo4j, và API `community_summary_search` cho GraphRAG dual-level retrieval. Tham chiếu ARCH §5.2 (Graph Indexing).
