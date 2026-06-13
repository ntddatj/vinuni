---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - "file:///home/agent/github/C2-App-053/_bmad-output/planning-artifacts/prds/prd-C2-App-053-2026-06-11/prd.md"
  - "file:///home/agent/github/C2-App-053/_bmad-output/planning-artifacts/ux-designs/ux-C2-App-053-2026-06-12/DESIGN.md"
  - "file:///home/agent/github/C2-App-053/_bmad-output/planning-artifacts/ux-designs/ux-C2-App-053-2026-06-12/EXPERIENCE.md"
workflowType: 'architecture'
project_name: 'C2-App-053'
user_name: 'Dat'
date: '2026-06-13'
lastStep: 8
status: 'complete'
completedAt: '2026-06-13'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Phân tích Ngữ cảnh Dự án (Project Context Analysis)

### Tổng quan Yêu cầu (Requirements Overview)

**Yêu cầu Chức năng (Functional Requirements):**
Hệ thống bao gồm 15 yêu cầu chức năng cốt lõi (FR-1 đến FR-15) được chia thành các thành phần chính:
1. **Quản lý người dùng & Dự án (FR-1, FR-2):** Đăng ký/đăng nhập, phân quyền tự động tài khoản đầu tiên làm Admin, giao diện lấy dự án làm trung tâm với sự cô lập tuyệt đối dữ liệu.
2. **Tìm kiếm & Nạp tài liệu (FR-3, FR-4, FR-5):** Tìm kiếm đa nguồn (arXiv, Semantic Scholar) hỗ trợ suy giảm chất lượng khi lỗi API (Degraded Union API Toast) và gợi ý từ khóa MECE khi truy vấn quá rộng. Tiến trình nạp tệp bất đồng bộ (FastAPI BackgroundTasks) cập nhật qua SSE. Trích xuất siêu dữ liệu từ tệp PDF/DOCX tự động (AI Suggested Metadata Form).
3. **Phân tích với AI Agent & Đồ thị (FR-6, FR-7, FR-15):** Chat thời gian thực với RAG + Neo4j, tự động tóm tắt trạng thái và cung cấp các nút tương tác nhanh (Quick Reply) định hướng hành động người dùng.
4. **Citation Guardrail (FR-8, FR-10):** Kiểm chứng trích dẫn thô chống trích dẫn ảo, so khớp với DB thực tế. Tự động sửa lỗi (LLM retry) hoặc hạ độ tin cậy dựa trên cấu hình động. Tương tác click/hover xem text chunk gốc của trích dẫn.
5. **Bản đồ Tri thức (FR-9):** Sử dụng Cytoscape.js để vẽ mạng lưới quan hệ trích dẫn và tác giả từ Neo4j, hỗ trợ phân tích và hiển thị khoảng trống tiềm năng hoặc mâu thuẫn học thuật trực quan.
6. **Hỗ trợ soạn thảo (FR-13, FR-14):** Rich editor soạn thảo và quản lý bản thảo, hỗ trợ xuất tệp nén ZIP chứa Markdown và BibTeX.
7. **Cấu hình hệ thống (FR-11, FR-12):** Quản trị viên cấu hình động các tham số lưu trong DB và được áp dụng ngay lập tức mà không cần restart server.

**Yêu cầu Phi chức năng (Non-Functional Requirements):**
- **Hiệu năng:** Độ trễ từ lúc gửi chat đến ký tự đầu tiên stream qua SSE dưới 3 giây. Thời gian truy vấn RAG dưới 500ms đối với cơ sở dữ liệu dưới 100,000 vector nhờ chỉ mục B-Tree (trên project_id) phối hợp HNSW (trên embedding).
- **Quy mô và Tải:** Phục vụ tối đa 50 người dùng hoạt động đồng thời trên cấu hình VM tối thiểu (Xubuntu 6 vcores, 32GB RAM).
- **Lưu trữ:** Giới hạn dung lượng file upload cá nhân tối đa là 20MB. Giới hạn số tài liệu tối đa của mỗi dự án (`MAX_PAPERS_PER_PROJECT`) do Admin cấu hình động (mặc định là 15 tài liệu).
- **Mức độ chính xác:** 100% trích dẫn xuất hiện trong bản thảo sinh bởi Agent phải tương ứng chính xác với tài liệu thực tế của dự án. 100% tiến trình nạp bất đồng bộ phải hiển thị đúng qua SSE.

**Đánh giá Quy mô & Độ phức tạp (Tối ưu hóa theo Nguyên lý đầu tiên):**
- Miền kỹ thuật chính: Full-stack (Python FastAPI backend, Frontend SPA/Vanilla JS, PostgreSQL + pgvector, Neo4j, LangGraph).
- Mức độ phức tạp: **Trung bình - Cao (Medium-High)** nhưng được tinh gọn hóa hạ tầng tối đa.
- Các thành phần kiến trúc và thiết kế tối giản:
  - **API Gateway / Web Server:** FastAPI (chạy Uvicorn).
  - **Auth Service:** JWT lưu trong HttpOnly cookies, phân quyền dựa trên DB.
  - **Project & Document Service:** Sử dụng PostgreSQL cho lưu trữ siêu dữ liệu.
  - **Ingestion Pipeline:** Sử dụng cơ chế `BackgroundTasks` tích hợp sẵn của FastAPI để xử lý ngầm (tải tệp, OCR, nhúng) mà không cần hàng đợi Redis/Celery cồng kềnh.
  - **Vector Database:** pgvector tích hợp trực tiếp trong PostgreSQL, tạo index HNSW phối hợp B-Tree trên `project_id`.
  - **Graph Database:** Neo4j lưu trữ cấu trúc đỉnh (Paper, Author) và cạnh (`:CITES`, `:AUTHORED`). Frontend fetch dữ liệu đồ thị qua một REST API đơn giản của FastAPI thay vì kết nối trực tiếp.
  - **AI Agent Workspace:** LangGraph xây dựng workflow RAG + Citation Verify Node (kiểm chứng trích dẫn thô qua đối khớp DB).
  - **Frontend SPA:** Bố cục 3 cột linh hoạt (Sidebar trái 240px, Center Workspace với horizontal tabs, Right Chat panel co giãn 20-40%). Sử dụng Cytoscape.js hiển thị đồ thị từ API REST JSON và EventSource cho luồng tiến trình SSE.

### Ràng buộc kỹ thuật & Phụ thuộc (Technical Constraints & Dependencies)

- **Cấu hình phần cứng:** Triển khai gọn nhẹ trên máy ảo Xubuntu 6 vcores, 32GB RAM.
- **Nguồn cấp API ngoài:** Phụ thuộc vào API Public của arXiv và Semantic Scholar. Trong trường hợp lỗi API hoặc quá hạn rate-limit, hệ thống áp dụng cơ chế *Degraded Union* (hiển thị Toast cảnh báo nhẹ và trả kết quả từ nguồn khả dụng còn lại).
- **Độc lập và cô lập Workspace:** Không có sự chia sẻ dữ liệu hoặc cộng tác chéo giữa các dự án của người dùng khác nhau ở phiên bản MVP.

### Các vấn đề xuyên suốt được xác định (Cross-Cutting Concerns)

- **Bảo mật và Phân quyền:** Xác thực JWT qua HttpOnly cookie. Phân quyền Admin động cho tài khoản đăng ký đầu tiên để cấu hình hệ thống.
- **Cô lập dữ liệu theo Workspace (Project-based Isolation):** Cô lập bằng logic thông qua khóa ngoại và index `project_id` trên PostgreSQL, pgvector và Neo4j, loại bỏ sự cần thiết của nhiều schema hay database vật lý độc lập.
- **Cơ chế Kiểm định trích dẫn (Citation Guardrail):** Hoạt động như một chốt chặn kiểm duyệt trung gian trên toàn bộ các output văn bản được sinh ra bởi AI Agent.
- **Cấu hình động:** Tham số giới hạn tài liệu và cấu hình AI được lưu trữ động trong DB và được đọc thời gian thực hoặc cache có hiệu lực lập tức.

### Kiểm soát Rủi ro & Phòng ngừa Lỗi (Pre-mortem Mitigation)

1. **Tránh nghẽn Event Loop do Ingestion ngầm:** Tách biệt các tác vụ OCR/nhúng (CPU-bound) chạy trên một `ThreadPoolExecutor` riêng để tránh block main thread của FastAPI. Thiết lập `proxy_buffering off;` và header `X-Accel-Buffering: no` trên Nginx để đảm bảo luồng SSE cập nhật mượt mà, không bị giữ lại ở tầng đệm.
2. **Xử lý bất đồng bộ không đồng nhất (Out-of-Sync) dữ liệu:** Quản trị trạng thái nạp tài liệu theo từng bước chuyển đổi tuyến tính (`PENDING` -> `EXTRACTED` -> `INDEXED_VECTOR` -> `INDEXED_GRAPH` -> `COMPLETED`) trong PostgreSQL. Nếu bất kỳ bước nào thất bại, dọn dẹp các bản ghi dở dang, cập nhật trạng thái `FAILED` kèm mã lỗi và cung cấp tùy chọn "Thử lại (Retry)" để người dùng khôi phục trạng thái nhất quán.
3. **Tránh trễ phản hồi do lặp kiểm định trích dẫn:** Đặt giới hạn cứng `CITATION_RETRY_LIMIT` (tối đa 1 lần LLM tự sửa). Nếu lần thử lại vẫn vượt ngưỡng sai lệch trích dẫn ảo, lập tức chuyển các thẻ lỗi thành `[Nguồn không xác định]` và trả về kết quả stream kèm nhãn **Cảnh báo độ tin cậy thấp (Low-Reliability Warning)** ở đầu khung chat để đảm bảo thời gian phản hồi (NFR <3s).
4. **Tránh vỡ giao diện 3 cột trên màn hình nhỏ:** Định nghĩa breakpoint CSS rõ ràng. Khi chiều rộng màn hình $< 1024\text{px}$, Sidebar trái tự động thu gọn thành Hamburger menu. Khi chiều rộng $< 768\text{px}$, Chatbot Panel phải tự động chuyển thành drawer overlay phủ lên trên thay vì chia cột inline, giải phóng không gian hiển thị cho Cytoscape.js và Editor.

### Nhật ký Quyết định Kiến trúc (ADR) — Giải pháp Cơ sở Dữ liệu Đồ thị

- **Bối cảnh:** Bản đồ Tri thức học thuật yêu cầu hiển thị mối quan hệ trích dẫn và tác giả phức tạp phục vụ cho phân tích khoảng trống nghiên cứu và suy luận đa bước của AI Agent.
- **Quyết định:** Sử dụng giải pháp Hybrid Database bao gồm **PostgreSQL + pgvector** làm nguồn dữ liệu chính cho siêu dữ liệu/RAG, kết hợp với **Neo4j** làm cơ sở dữ liệu đồ thị chuyên biệt để quản lý quan hệ.
- **Đánh đổi & Giải pháp tối ưu tài nguyên trên VM 32GB RAM:**
  - *Mức độ chiếm dụng bộ nhớ:* Neo4j chạy trên JVM có thể ngốn bộ nhớ lớn. Giải pháp phòng ngừa là cấu hình cứng giới hạn RAM của Neo4j trong cấu hình Docker/Server (`dbms.memory.heap.initial_size=512m`, `dbms.memory.heap.max_size=1g`, `dbms.memory.pagecache.size=512m`) giới hạn mức tiêu thụ ở khoảng 1.5 - 2GB RAM.
  - *Độ trễ và Tính nhất quán:* Cập nhật đồ thị Neo4j được thực hiện bất đồng bộ trong background task sau khi dữ liệu PostgreSQL đã được ghi nhận thành công, ngăn việc lỗi đồng bộ đồ thị làm gián đoạn luồng nghiệp vụ chính.

### Tư duy Bậc hai về Giới hạn & Xóa Tài liệu (Second-Order Guardrails)

- **Vấn đề:** Khi chạm giới hạn tài liệu tối đa (`MAX_PAPERS_PER_PROJECT` - mặc định là 15), người dùng sẽ bắt buộc phải xóa tài liệu cũ để thêm tài liệu mới. Việc xóa hoàn toàn (hard-delete) tài liệu sẽ làm đứt gãy các mối quan hệ trích dẫn `[:CITES]` trên đồ thị Neo4j, làm hỏng các liên kết tooltip trích dẫn gốc trong bản thảo cũ và lịch sử chat.
- **Thiết kế phòng ngừa bậc hai:**
  - *Cơ chế Xóa mềm & Lưu trữ (Soft Delete & Archiving):* Khi người dùng thực hiện xóa tài liệu, hệ thống chỉ đổi trạng thái sang `archived`. Tài liệu lưu trữ không được tính vào giới hạn `MAX_PAPERS_PER_PROJECT` và bị loại bỏ khỏi luồng truy vấn RAG chủ động. Tuy nhiên, siêu dữ liệu và các text chunk của nó vẫn được giữ lại trong database để hiển thị trích dẫn cũ. Trên Bản đồ tri thức, các node lưu trữ hiển thị màu xám mờ để giữ tính lịch sử quan hệ trích dẫn.
  - *Cảnh báo ràng buộc:* Trước khi thực hiện, hệ thống đối chiếu xem tài liệu có đang được dùng làm trích dẫn trong bản thảo hiện tại hay không để hiển thị cảnh báo cho người dùng chuyển đổi sang trạng thái Lưu trữ an toàn.

### Đồ thị Hệ thống & Mô thức Vận hành (Graph of Thoughts - System Mapping)

- **Vòng lặp Đối chiếu Trích dẫn (Citation Loopback Pattern):** Phản hồi sinh bởi AI Agent được quét qua Citation Guardrail đối chiếu với cơ sở dữ liệu PostgreSQL trước khi trả về. Để tránh độ trễ, thiết lập chỉ mục Unique kết hợp `(project_id, paper_index)` hoặc `(project_id, doi)` để đảm bảo thời gian đối chiếu là tức thời.
- **Đồng bộ hướng sự kiện phía Client (State-Aware Client-Steering Pattern):** Cột 2 (Center Workspace) và Cột 3 (Right Chat Panel) hoạt động cộng tác dựa trên thông số trạng thái dự án. Client-side state sẽ tự động đính kèm thông tin ngữ cảnh giao diện hiện tại (`active_tab`, `document_count`, `has_draft`) vào payload gửi đến Chatbot để AI Agent trả về Quick Reply điều hướng tương thích mà không cần liên tục query database.
- **Tránh nghẽn kết nối SSE (SSE Multiplexing Constraint):** Trình duyệt giới hạn tối đa 6 luồng kết nối SSE đồng thời đến cùng một domain trên HTTP/1.1. Do đó, toàn bộ ứng dụng sẽ được vận hành qua giao thức **HTTP/2** để tận dụng tính năng Multiplexing (ghép kênh kết nối). Phía Backend FastAPI sẽ đóng luồng SSE tiến trình nạp tệp ngay khi tác vụ hoàn tất để giải phóng connection pool.

## Đánh giá & Lựa chọn Starter Template (Starter Template Evaluation)

### Miền Kỹ thuật Chính (Primary Technology Domain)

Hệ thống được xác định là một **Full-stack Web Application** với sự tách biệt rõ ràng giữa Backend (FastAPI + LangGraph) và Frontend SPA để tối ưu hóa hiệu năng và khả năng mở rộng.

### Các phương án Starter được cân nhắc

- **Next.js:** Phù hợp cho SSR nhưng dư thừa Node.js server overhead do backend đã dùng FastAPI. Dễ gặp lỗi Hydration Mismatch khi dùng Cytoscape.js vẽ đồ thị tương tác.
- **Streamlit:** Phụ thuộc hoàn toàn vào Python, không thể tùy biến giao diện resizable 3 cột và canvas Cytoscape.js nâng cao.
- **Vite React TS:** Tối ưu nhất cho mô hình SPA kết nối FastAPI backend. Tạo ra các file tĩnh gọn nhẹ, dễ serve, biên dịch nhanh và loại bỏ hoàn toàn rủi ro Hydration Mismatch khi thao tác DOM.

### Starter được chọn: Vite + React (TypeScript)

**Lý do lựa chọn:**
- Gọn nhẹ, biên dịch cực nhanh, không gây gánh nặng RAM cho máy ảo 32GB RAM của VM.
- Đầu ra là HTML/JS/CSS tĩnh, dễ dàng phục vụ bởi FastAPI hoặc deploy độc lập lên CDN.
- Hỗ trợ tốt TypeScript để đồng bộ cấu trúc dữ liệu chặt chẽ với Backend.

**Lệnh khởi tạo dự án:**
```bash
npm create vite@latest frontend -- --template react-ts
```

**Các quyết định kiến trúc từ Starter:**
- **Ngôn ngữ:** TypeScript (ESLint + Prettier).
- **Styling:** Vanilla CSS (CSS Modules) để thiết kế giao diện sáng/tối tùy biến cao, không dùng Tailwind CSS theo đúng tiêu chuẩn.
- **Build Tooling:** Vite (cực nhanh).
- **Cơ cấu thư mục đề xuất:**
  - `/frontend/src/components` (Sidebar, ChatPanel, KnowledgeMap, Editor, UI Elements)
  - `/frontend/src/hooks` (useSSE, useChat, useIngest)
  - `/frontend/src/styles` (Màu sắc và typography theo DESIGN.md)

## Các Quyết định Kiến trúc Cốt lõi (Core Architectural Decisions)

### Phân tích Độ ưu tiên Quyết định (Decision Priority Analysis)

**Quyết định Cực kỳ Quan trọng (Critical Decisions - Bắt buộc triển khai sớm):**
- **Cơ sở dữ liệu Hybrid:** PostgreSQL + pgvector (siêu dữ liệu & RAG vector) + Neo4j (đồ thị liên kết mạng lưới). Cần cài đặt cấu hình Neo4j giới hạn RAM trước khi dựng API.
- **SSE & Giao thức truyền tải:** Vận hành qua HTTP/2 trên Nginx và tắt buffering (`proxy_buffering off;`) để đảm bảo truyền tải SSE ổn định cho cả chat stream và tiến trình nạp tệp.

**Quyết định Quan trọng (Important Decisions - Định hình cấu trúc ứng dụng):**
- **Quản lý Trạng thái phía Client:** Sử dụng React Context API kết hợp client-side state để lưu trữ thông tin dự án hiện tại, đồng bộ tức thời giữa các Tab ở cột giữa và Chatbot ở cột phải.
- **Xác thực & Bảo mật:** Dùng JWT lưu trong HttpOnly, Secure Cookie để chống tấn công XSS/CSRF.

**Quyết định Hoãn lại (Deferred Decisions - Thực hiện sau MVP):**
- **Chia sẻ dự án (Collaboration):** Tính năng cộng tác đa người dùng thời gian thực (real-time collaboration) được hoãn lại sau MVP.
- **Tích hợp API có phí:** Các nguồn học thuật có phí (Sci-Hub/IEEE Xplore) được hoãn để tối ưu hóa phạm vi MVP.

---

### Kiến trúc Dữ liệu (Data Architecture)

- **Cơ sở dữ liệu Quan hệ & Vector:** **PostgreSQL (v16+)** kết hợp extension **pgvector (v0.7+)**. Lưu trữ thông tin người dùng, dự án, siêu dữ liệu tài liệu, lịch sử chat và các vector chunk phục vụ RAG.
  - *Thư viện kết nối:* `SQLAlchemy==2.0.38` và `asyncpg==0.29.0` (chạy async hoàn toàn cho các request).
  - *Chỉ mục:* Sử dụng index HNSW kết hợp B-Tree trên `project_id` để tối ưu hóa truy vấn vector dưới 500ms.
- **Cơ sở dữ liệu Đồ thị:** **Neo4j (v5.x)** để lưu trữ các quan hệ mạng lưới học thuật.
  - *Thư viện kết nối:* `neo4j==6.2.0` (Python driver chính thức).
  - *Cấu hình tối ưu:* Giới hạn RAM heap và pagecache tối đa 1.5GB - 2GB trong tệp cấu hình Docker/Server để tránh làm nghẽn VM 32GB RAM.
- **Quản lý Migration:** **Alembic==1.18.4** để quản lý lịch sử schema PostgreSQL.

### Xác thực & Bảo mật (Authentication & Security)

- **Cơ chế xác thực:** Sử dụng mã **JWT** được cấp phát sau khi đăng nhập thành công. JWT được lưu trữ an toàn trong **HttpOnly Cookie** với cờ `Secure`, `SameSite=Strict`.
- **Phân quyền (Authorization):** Mô hình RBAC (Role-Based Access Control) động:
  - Tài khoản đăng ký đầu tiên có vai trò `admin`, được phép truy cập trang Cài đặt Hệ thống.
  - Các tài khoản tiếp theo có vai trò `user`, bị giới hạn bởi cấu hình động của Admin (ví dụ: giới hạn số file `MAX_PAPERS_PER_PROJECT`).
  - Mọi API truy cập tài nguyên đều phải validate quyền sở hữu thông qua `user_id` and `project_id` được giải mã từ JWT.
- **Security Middleware:** FastAPI CORS Middleware cấu hình danh sách domain Frontend cụ thể. Sử dụng thư viện `passlib==1.7.4` với thuật toán bcrypt để băm mật khẩu trước khi lưu DB.

### API & Giao thức Truyền thông (API & Communication Patterns)

- **Thiết kế API:** Sử dụng mô hình **RESTful API** chuẩn cho các thao tác CRUD dự án, tài liệu và cấu hình Admin.
- **Giao thức Streaming (SSE):** 
  - FastAPI `StreamingResponse` (dùng python generators) để stream nội dung câu trả lời của Chatbot từ LangGraph.
  - FastAPI `BackgroundTasks` đẩy các cập nhật trạng thái nạp tài liệu bất đồng bộ qua kênh SSE riêng biệt `/api/v1/projects/{id}/ingest/progress`.
- **Tài liệu hóa API:** Tích hợp Swagger UI (`/docs`) có sẵn của FastAPI.

### Kiến trúc Frontend (Frontend Architecture)

- **Framework & Build Tool:** **Vite + React (TypeScript) v5.x** tạo SPA tĩnh.
- **Quản lý State:** Sử dụng **React Context API** tích hợp sẵn. Do mỗi phiên làm việc được cô lập theo dự án và các hành động khá trực tiếp, Context API là giải pháp sạch sẽ và đủ dùng cho MVP, không cần cài đặt Redux.
- **Thư viện Vẽ đồ thị:** **Cytoscape.js==3.33.3** để dựng Bản đồ Tri thức tương tác, kết hợp với các helper tự động hóa CSS hoạt hình nhấp nháy cho khoảng trống đỏ.
- **Rich Editor:** Dùng thư viện editor nhẹ như **Lexical** hoặc **Slate.js** phục vụ cho Tab Hỗ trợ viết tổng quan.
- **Cơ cấu CSS:** Sử dụng **CSS Modules (Vanilla CSS)** theo đúng thiết kế DESIGN.md để đạt hiệu năng tải tốt nhất và độ linh hoạt cao, hỗ trợ chuyển đổi class sáng/tối dễ dàng qua biến CSS Variables.

### Hạ tầng & Triển khai (Infrastructure & Deployment)

- **Môi trường:** Máy chủ Linux (Xubuntu 6 vcores, 32GB RAM).
- **Container hóa:** Sử dụng **Docker Compose** để chạy 3 container:
  1. `web-backend`: FastAPI application + Uvicorn.
  2. `db-postgres`: PostgreSQL + pgvector.
  3. `db-neo4j`: Neo4j Community Edition.
- **Reverse Proxy & Web Server:** **Nginx** làm reverse proxy đứng trước, hỗ trợ **HTTP/2** để cho phép ghép kênh kết nối SSE không giới hạn. Cấu hình `proxy_buffering off;` cho các endpoint API `/api/v1/chat/stream` và `/api/v1/projects/*/ingest/progress`.
- **Quản lý Log:** Ghi log hệ thống qua thư viện `logging` của Python ra file và console để Docker daemon thu thập.

## Các Mô thức Triển khai & Quy tắc Nhất quán (Implementation Patterns & Consistency Rules)

### 1. Quy tắc Đặt tên (Naming Patterns)

**Quy tắc Cơ sở Dữ liệu (Database Naming):**
- **PostgreSQL:**
  - Tên bảng (Tables): Viết thường, dạng số nhiều, phân tách bằng dấu gạch dưới (snake_case). Ví dụ: `users`, `projects`, `project_documents`, `system_configurations`.
  - Tên cột (Columns): snake_case. Ví dụ: `project_id`, `created_at`.
  - Khóa ngoại (Foreign Keys): `<table_name_singular>_id`. Ví dụ: `project_id` tham chiếu đến bảng `projects`.
- **Neo4j:**
  - Nhãn đỉnh (Node Labels): Viết hoa chữ cái đầu, dạng số ít (PascalCase). Ví dụ: `:Paper`, `:Author`.
  - Nhãn cạnh (Relationship Labels): Viết hoa toàn bộ, phân tách bằng dấu gạch dưới (UPPERCASE). Ví dụ: `[:CITES]`, `[:AUTHORED]`.

**Quy tắc API (API Naming):**
- **Đường dẫn REST API:** Dạng số nhiều, snake_case. Ví dụ: `/api/v1/projects/{project_id}/documents`.
- **Tham số truy vấn (Query Params):** snake_case. Ví dụ: `/api/v1/projects?page_size=10`.
- **Định dạng JSON (JSON Keys):** Thống nhất dùng **snake_case** cho cả Request và Response để đồng bộ tự nhiên với Python. Không dùng camelCase cho các khóa JSON trao đổi qua API.

**Quy tắc Đặt tên Code:**
- **Backend (Python):**
  - Tệp và thư mục: snake_case (Ví dụ: `routes.py`, `citation_verify.py`).
  - Hàm và biến: snake_case (Ví dụ: `get_project_by_id`, `user_id`).
  - Lớp (Classes): PascalCase (Ví dụ: `CitationVerifyNode`).
- **Frontend (React/TypeScript):**
  - Component UI (Tên class & tên tệp): PascalCase (Ví dụ: `SidebarNav.tsx`, `KnowledgeMapCanvas.tsx`).
  - CSS Modules (Tên tệp): PascalCase (Ví dụ: `SidebarNav.module.css`).
  - Hooks, helpers, contexts (Tên hàm & tên tệp): camelCase (Ví dụ: `useSSE.ts`, `projectContext.tsx`).

---

### 2. Quy tắc Cấu trúc Dự án (Structure Patterns)

**Cấu trúc Backend (FastAPI):**
- `src/main.py`: Điểm khởi chạy FastAPI.
- `src/config.py`: Cấu hình hệ thống (Pydantic Settings).
- `src/api/`: Các tệp định nghĩa route API.
- `src/models/`: SQLAlchemy entities và Pydantic schemas.
- `src/services/`: Logic nghiệp vụ (Ingestion, OCR, LLM service).
- `src/agents/`: Luồng xử lý AI Agent (LangGraph, nodes, state).
- Thư mục kiểm thử: **tests/** nằm ở thư mục gốc, phân cấp tương ứng với `src/`. Ví dụ: `tests/api/test_routes.py`.

**Cấu trúc Frontend (Vite + React):**
Tất cả mã nguồn frontend nằm trong thư mục `/frontend/src/`:
- `/components/`: Các UI components tái sử dụng (Layout, Sidebar, ChatPanel, Canvas, Editor).
- `/hooks/`: Các custom hooks (xử lý SSE, chat logic).
- `/context/`: Quản lý state chung của ứng dụng (Active Project Context, Auth Context).
- `/styles/`: Định nghĩa design tokens (biến CSS cho Light/Dark mode, Global reset) theo DESIGN.md.
- `/utils/`: Các hàm bổ trợ thuần túy (format date, export file ZIP).

---

### 3. Quy tắc Định dạng Dữ liệu (Format Patterns)

**Định dạng API Response thành công:**
Hệ thống trả về trực tiếp dữ liệu dạng JSON Object hoặc Array mà không cần bọc qua envelope `{ data: ... }` trừ trường hợp phân trang.
- Định dạng phân trang: `{ "items": [...], "total": 100, "page": 1, "page_size": 10 }`

**Định dạng API Error:**
Thống nhất sử dụng cấu trúc lỗi tiêu chuẩn của FastAPI:
```json
{
  "detail": "Thông điệp mô tả lỗi chi tiết dành cho người dùng"
}
```
Mã lỗi HTTP được sử dụng nghiêm ngặt:
- `400 Bad Request`: Lỗi validation đầu vào.
- `401 Unauthorized`: Sai thông tin đăng nhập hoặc JWT hết hạn.
- `403 Forbidden`: Người dùng thường cố truy cập trang Admin hoặc vượt giới hạn tài liệu của dự án.
- `404 Not Found`: Dự án hoặc tài liệu không tồn tại.

**Định dạng Dữ liệu Trao đổi qua SSE:**
- **Luồng nạp tài liệu (SSE Ingest):**
  ```json
  {
    "status": "ingesting_downloading" | "ingesting_ocr" | "ingesting_embedding" | "ingested" | "failed",
    "progress": 50,
    "message": "Đang quét cấu trúc & OCR...",
    "document_id": "uuid-string-here"
  }
  ```
- **Luồng Chat Stream:**
  - Stream các chunk chữ thô (`text/plain`) để hiển thị tốc độ cao.
  - Chunk cuối cùng chứa metadata trích dẫn dạng JSON:
    ```json
    {
      "finish_reason": "stop",
      "citations": [
        { "index": 1, "title": "...", "doi": "...", "text_chunk": "..." }
      ],
      "low_reliability": false
    }
    ```

---

### 4. Quy tắc Xử lý Quy trình (Process Patterns)

- **Xử lý trạng thái tải (Loading States):** 
  - Mọi nút bấm kích hoạt API phải chuyển sang trạng thái disabled và hiển thị spinner/indicator.
  - Vùng canvas đồ thị hiển thị Skeleton mờ trong khi fetch dữ liệu từ Neo4j.
- **Xử lý lỗi phía Client (Error Boundaries):** 
  - Đóng gói các khu vực nhạy cảm dễ crash (như Cytoscape.js canvas và Rich Text Editor) trong các lớp `ErrorBoundary` của React để đảm bảo nếu đồ thị lỗi, khung chat và sidebar vẫn hoạt động bình thường, không gây trắng màn hình.
- **Xử lý trích dẫn ảo (Citation Guardrail Workflow):** 
  - Agent Node luôn thực hiện: Trích xuất các trích dẫn $\rightarrow$ Đối chiếu ID với PostgreSQL $\rightarrow$ Tính tỷ lệ lỗi.
  - Nếu sửa lỗi thất bại sau 1 lần, tự động chuyển thẻ lỗi thành `[Nguồn không xác định]` và đính kèm cờ `low_reliability: true` để Frontend hiển thị cảnh báo đỏ trên UI.

## Cấu trúc Dự án & Ranh giới Kiến trúc (Project Structure & Boundaries)

### Cấu trúc Thư mục Toàn diện (Complete Project Directory Structure)

```
C2-App-053/
├── .env                  # Cấu hình môi trường local (chứa API Keys, DB URI)
├── .env.example          # Tệp mẫu cấu hình môi trường
├── Dockerfile            # Dockerfile build multi-stage cho ứng dụng
├── docker-compose.yml    # Docker Compose chạy PostgreSQL, Neo4j, Backend FastAPI
├── requirements.txt      # Các thư viện Python Backend
├── ruff.toml             # Quy tắc linting ruff cho Backend
├── src/                  # Mã nguồn Backend (Python FastAPI)
│   ├── main.py           # Điểm khởi chạy ứng dụng FastAPI và middleware
│   ├── config.py         # Cấu hình ứng dụng qua Pydantic Settings
│   ├── api/              # Tầng định nghĩa REST API
│   │   ├── __init__.py
│   │   └── routes.py     # Định tuyến API (CRUD dự án, tài liệu, cấu hình Admin)
│   ├── models/           # Cấu trúc dữ liệu và thực thể DB
│   │   ├── __init__.py
│   │   └── schemas.py    # Pydantic schemas và SQLAlchemy ORM models
│   ├── services/         # Tầng logic nghiệp vụ
│   │   ├── __init__.py
│   │   ├── llm.py        # Giao tiếp với OpenAI/Semantic Scholar
│   │   ├── ingestion.py  # Xử lý BackgroundTasks nạp tài liệu & OCR
│   │   └── guardrail.py  # Node xử lý và kiểm định trích dẫn ảo
│   └── agents/           # Luồng AI Agent (LangGraph)
│       ├── __init__.py
│       ├── state.py      # Định nghĩa AgentState
│       ├── graph.py      # Định nghĩa đồ thị LangGraph (Nodes & Edges)
│       ├── nodes/        # Các Node của LangGraph (retrieval, cite verify)
│       │   ├── __init__.py
│       │   └── example_node.py
│       └── tools/        # Các công cụ bổ trợ cho Agent (Cypher queries)
│           ├── __init__.py
│           └── example_tool.py
├── frontend/             # Mã nguồn Frontend (React SPA + Vite)
│   ├── package.json      # Dependencies frontend (react, cytoscape, lexical)
│   ├── tsconfig.json     # Cấu hình TypeScript
│   ├── vite.config.ts    # Cấu hình Vite dev server và build static
│   ├── index.html        # Trang chính SPA
│   ├── src/
│   │   ├── main.tsx      # Entrypoint React
│   │   ├── App.tsx       # Bố cục chính 3 cột
│   │   ├── context/      # Quản lý State chung phía Client
│   │   │   ├── authContext.tsx
│   │   │   └── projectContext.tsx
│   │   ├── hooks/        # Hooks tương tác API và SSE
│   │   │   ├── useSSE.ts
│   │   │   └── useChat.ts
│   │   ├── styles/       # Hệ thống CSS biến sáng/tối
│   │   │   ├── variables.css
│   │   │   └── global.css
│   │   └── components/   # Các Component giao diện tái sử dụng
│   │       ├── Layout.tsx
│   │       ├── Sidebar/   # Quản lý và danh sách dự án (Cột 1)
│   │       │   ├── ProjectList.tsx
│   │       │   └── ProjectList.module.css
│   │       ├── CenterWorkspace/ # Tab ngang (Cột 2)
│   │       │   ├── DocumentLibrary.tsx
│   │       │   ├── KnowledgeMap.tsx
│   │       │   ├── OverviewSupport.tsx
│   │       │   └── CenterWorkspace.module.css
│   │       ├── ChatbotPanel/ # Trợ lý chat và nút gợi ý (Cột 3)
│   │       │   ├── Chatbox.tsx
│   │       │   ├── QuickReplies.tsx
│   │       │   └── ChatbotPanel.module.css
│   │       └── Common/    # Hộp thoại nổi và Toast
│   │           ├── CitationTooltip.tsx
│   │           ├── SettingsModal.tsx
│   │           └── ToastAlert.tsx
├── tests/                # Bộ kiểm thử (Backend)
│   ├── conftest.py       # Cấu hình Pytest fixtures (DB connection, app mock)
│   ├── test_api/         # API Tests
│   │   ├── __init__.py
│   │   └── test_routes.py
│   └── test_agents/      # Agent / Graph Tests
│       ├── __init__.py
│       └── test_graph.py
```

### Ranh giới Kiến trúc (Architectural Boundaries)

#### API Boundaries (Ranh giới API)
- **REST Endpoints:** Backend FastAPI mở các cổng dịch vụ công khai tại `/api/v1`. Mọi trao đổi dữ liệu (ngoại trừ luồng SSE) đều sử dụng giao thức HTTP REST với cấu trúc JSON.
- **SSE Stream Endpoints:** Kênh `/api/v1/projects/{id}/ingest/progress` và `/api/v1/chat/stream` là luồng đẩy dữ liệu một chiều từ Server sang Client, giữ kết nối mở ngắn hạn.
- **Ranh giới CORS:** Chỉ cho phép tên miền Frontend (cấu hình trong `.env`) truy cập API.

#### Component Boundaries (Ranh giới Component)
- **Cấu trúc 3 cột độc lập:**
  - *Cột 1 (Sidebar):* Chỉ thao tác với danh sách dự án và tạo dự án mới. Không giao tiếp trực tiếp với nội dung bên trong Tab trung tâm.
  - *Cột 2 (Center Workspace):* Chứa 3 tab độc lập giao diện. Tương tác bên trong tab (ví dụ: click node trên Cytoscape) chỉ ảnh hưởng tới Node Detail Card cục bộ.
  - *Cột 3 (Chatbot Panel):* Nhận dữ liệu trạng thái từ Context để hiển thị Quick Replies, không can thiệp trực tiếp vào cấu trúc DOM của cột giữa.

#### Service Boundaries (Ranh giới Dịch vụ Backend)
- **Ingestion Service:** Chịu trách nhiệm tải file, OCR, sinh metadata, tính toán vector embedding và đồng bộ sang Neo4j. Chạy bất đồng bộ qua `BackgroundTasks`.
- **LLM Agent Service (LangGraph):** Độc lập với API, chỉ nhận đầu vào là câu hỏi và lịch sử hội thoại từ API Router, thực thi đồ thị suy luận và trả về kết quả cho Router stream về Client.

#### Data Boundaries (Ranh giới Dữ liệu)
- **PostgreSQL/pgvector:** Nguồn chân lý duy nhất (Source of Truth) cho siêu dữ liệu tài liệu, tài khoản, dự án và cấu hình.
- **Neo4j:** Đồ thị quan hệ học thuật thứ cấp phục vụ Bản đồ Tri thức và suy luận. Mọi thay đổi trên Neo4j phải bắt nguồn từ các cập nhật của Ingestion Service từ PostgreSQL.

---

### Ánh xạ Yêu cầu vào Cấu trúc (Requirements to Structure Mapping)

#### Tính năng & Epic:
- **Đăng nhập & Phân quyền Admin (FR-1, FR-11, FR-12):**
  - Backend API: `src/api/routes.py` (endpoints `/auth/login`, `/admin/settings`).
  - Models: `src/models/schemas.py` (Bảng `User`, `SystemConfiguration`).
  - Frontend UI: `/frontend/src/components/Common/SettingsModal.tsx`.
- **Quản lý Dự án & Workspace (FR-2):**
  - Backend API: `/api/v1/projects` CRUD.
  - Frontend UI: `/frontend/src/components/Sidebar/` và `/frontend/src/context/projectContext.tsx`.
- **Nạp tài liệu & Trích xuất siêu dữ liệu (FR-3, FR-4, FR-5, FR-11):**
  - Backend API: `/api/v1/projects/{id}/documents/upload` và SSE progress.
  - Backend Logic: `src/services/ingestion.py`.
  - Frontend UI: `/frontend/src/components/CenterWorkspace/DocumentLibrary.tsx`.
- **Chat Agent & Định hướng người dùng (FR-6, FR-7, FR-15):**
  - Backend Agent: `src/agents/graph.py` và `src/agents/nodes/`.
  - Frontend UI: `/frontend/src/components/ChatbotPanel/`.
- **Citation Guardrail & Tooltip (FR-8, FR-10):**
  - Backend logic: `src/services/guardrail.py` (Citation Verify Node).
  - Frontend UI: `/frontend/src/components/Common/CitationTooltip.tsx`.
- **Bản đồ Tri thức (FR-9):**
  - Backend API: `/api/v1/projects/{id}/graph`.
  - Frontend UI: `/frontend/src/components/CenterWorkspace/KnowledgeMap.tsx` (Cytoscape.js canvas).
- **Hỗ trợ Soạn thảo & Xuất bản thảo (FR-13, FR-14):**
  - Backend API: `/api/v1/projects/{id}/manuscript` CRUD và `/export` ZIP.
  - Frontend UI: `/frontend/src/components/CenterWorkspace/OverviewSupport.tsx`.

---

### Tích hợp Quy trình Phát triển & Triển khai (Development Workflow Integration)

- **Cấu hình môi trường:** `.env` lưu trữ các biến `DATABASE_URL`, `NEO4J_URI`, `OPENAI_API_KEY`, `CORS_ORIGINS`, `MAX_PAPERS_PER_PROJECT`.
- **Chạy môi trường phát triển (Development):**
  - Backend: `uvicorn src.main:app --reload --port 8000`
  - Frontend: `npm run dev` (Vite chạy tại `http://localhost:5173`)
- **Quy trình Build & Đóng gói (Production):**
  1. Frontend được build qua lệnh `npm run build` xuất các tệp tĩnh vào `/frontend/dist`.
  2. Dockerfile multi-stage copy `/frontend/dist` vào container backend, FastAPI serve thư mục này làm static files tại đường dẫn gốc `/`.

## Đánh giá & Kiểm định Kiến trúc (Architecture Validation Results)

### Kiểm định Tính nhất quán (Coherence Validation) ✅

- **Tương thích của Quyết định Công nghệ (Decision Compatibility):** Tất cả các lựa chọn công nghệ (PostgreSQL 16, pgvector 0.7, Neo4j 5.x, FastAPI 0.136.3, LangGraph 1.2.0, Vite React TS 5.x, Cytoscape.js 3.33.3) hoàn toàn tương thích và không có xung đột phiên bản.
- **Nhất quán của Quy tắc (Pattern Consistency):** Quy tắc đặt tên đồng bộ snake_case từ cơ sở dữ liệu đến các khóa trao đổi JSON API. Các quy tắc PascalCase được áp dụng đúng chuẩn cho cả class Python và React Component.
- **Đồng bộ Cấu trúc (Structure Alignment):** Cấu trúc thư mục phân tách rõ rệt giữa Frontend SPA và Backend API giúp giữ các ranh giới kiến trúc rõ ràng, phục vụ tốt cho việc deploy độc lập.

### Kiểm định Độ phủ Yêu cầu (Requirements Coverage Validation) ✅

- **Độ phủ Yêu cầu Chức năng (FR Coverage):** Tất cả 15 yêu cầu chức năng (FR-1 đến FR-15) được lập bản đồ chi tiết tới các tệp tin và module tương ứng. Không có yêu cầu nào bị bỏ sót.
- **Độ phủ Yêu cầu Phi chức năng (NFR Coverage):**
  - *Hiệu năng:* Đảm bảo bằng chỉ mục HNSW trên pgvector và chạy ngầm BackgroundTasks cho OCR.
  - *Kết nối:* Đảm bảo bằng ghép kênh HTTP/2 trên Nginx cho SSE.
  - *Bảo mật:* Bảo vệ bằng JWT trong HttpOnly, Secure Cookie và phân quyền RBAC.

### Kiểm định Độ sẵn sàng Triển khai (Implementation Readiness Validation) ✅

- **Độ đầy đủ của Quyết định:** Các quyết định kỹ thuật cốt lõi kèm phiên bản thư viện đã được xác thực qua web search và ghi nhận chi tiết.
- **Độ đầy đủ của Cấu trúc:** Bản đồ phân cấp thư mục chi tiết bao quát toàn bộ tệp tin cần thiết cho cả backend và frontend.
- **Độ đầy đủ của Mô thức:** Đã thiết lập các mô thức xử lý lỗi, trạng thái tải và kiểm định trích dẫn ảo chi tiết để định hướng thống nhất cho các AI Agent.

### Kết quả Phân tích Khoảng trống (Gap Analysis Results)

- **Khoảng trống Cực kỳ Quan trọng (Critical Gaps):** Không có (Tất cả hạ tầng và logic cốt lõi đã được định hình đầy đủ).
- **Khoảng trống Quan trọng (Important Gaps):** Việc lựa chọn thư viện Rich Editor (Lexical hay Slate.js) cho phần bản soạn thảo tổng quan tài liệu có thể tùy chỉnh thêm trong giai đoạn đầu phát triển frontend.
- **Khoảng trống Khuyên dùng (Nice-to-Have Gaps):** Cài đặt thêm tầng Cache (Redis) cho API học thuật để tránh bị dính Rate Limit khi mở rộng quy mô sau này.

### Danh sách Kiểm tra Độ hoàn thiện (Architecture Completeness Checklist)

**Phân tích Yêu cầu:**
- [x] Ngữ cảnh dự án được phân tích sâu sắc.
- [x] Quy mô và độ phức tạp được đánh giá đầy đủ.
- [x] Ràng buộc kỹ thuật được xác định rõ ràng.
- [x] Vấn đề xuyên suốt được lập bản đồ chi tiết.

**Quyết định Kiến trúc:**
- [x] Quyết định quan trọng kèm phiên bản được tài liệu hóa.
- [x] Tech stack được chỉ định rõ rệt.
- [x] Mô thức tích hợp được định nghĩa cụ thể.
- [x] Các yếu tố hiệu năng được giải quyết triệt để.

**Mô thức Triển khai:**
- [x] Quy chuẩn đặt tên được thiết lập rõ ràng.
- [x] Quy tắc cấu trúc dự án được định nghĩa cụ thể.
- [x] Định dạng trao đổi dữ liệu được chỉ rõ.
- [x] Luồng xử lý lỗi và quy trình được tài liệu hóa.

**Cấu trúc Dự án:**
- [x] Bản đồ thư mục dự án được định hình chi tiết.
- [x] Ranh giới giữa các component được thiết lập vững chắc.
- [x] Các điểm tích hợp được ánh xạ đầy đủ.
- [x] Ánh xạ yêu cầu chức năng vào thư mục hoàn tất.

### Đánh giá Độ sẵn sàng Kiến trúc (Architecture Readiness Assessment)

- **Trạng thái chung:** **SẴN SÀNG TRIỂN KHAI (READY FOR IMPLEMENTATION)** (Tất cả 16/16 đầu mục kiểm tra đã hoàn thành, không có khoảng trống chí tử).
- **Độ tự tin (Confidence Level):** **Cao (High)**.
- **Thế mạnh chính:** Hạ tầng tối giản hóa tài nguyên tối đa (FastAPI Native SSE & BackgroundTasks), kiến trúc dữ liệu đồ thị hybrid có ranh giới rõ ràng, và cơ chế an toàn Citation Guardrail được thiết kế chặt chẽ.
- **Định hướng phát triển tiếp theo:** Tối ưu hóa caching API và tích hợp CI/CD.

### Bàn giao Triển khai (Implementation Handoff)

**Hướng dẫn dành cho AI Agent:**
1. Tuân thủ nghiêm ngặt tech stack và phiên bản đã ghi nhận.
2. Tuân thủ tuyệt đối quy tắc đặt tên (snake_case cho DB & JSON, PascalCase cho React components).
3. Đảm bảo cấu hình HTTP/2 và tắt buffering trên Nginx Proxy cho luồng SSE.

**Đầu mục ưu tiên triển khai đầu tiên:**
Khởi tạo dự án Frontend React SPA bằng Vite tại thư mục gốc:
```bash
npm create vite@latest frontend -- --template react-ts
```
