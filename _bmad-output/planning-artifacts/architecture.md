---
stepsCompleted: [1, 2, 3]
inputDocuments:
  - '_bmad-output/planning-artifacts/prds/prd-C2-App-053-2026-06-11/prd.md'
  - '_bmad-output/planning-artifacts/ux-designs/ux-C2-App-053-2026-06-12/DESIGN.md'
  - '_bmad-output/planning-artifacts/ux-designs/ux-C2-App-053-2026-06-12/EXPERIENCE.md'
  - 'docs/architecture_diagram.md'
  - 'docs/guide/architecture/_index.md'
  - 'docs/guide/architecture/system-design.md'
  - 'docs/prd/plan.md'
workflowType: 'architecture'
project_name: 'C2-App-053'
user_name: 'Dat'
date: '2026-06-14'
---

# Architecture Decision Document

## 1. Project Context & Strategy

### 1.1. Chiến lược Phasing
- **Phase 1 (MVP):** Triển khai Ontology và cấu hình Neo4j + Postgres kép. Hỗ trợ hiển thị Cytoscape.js, tìm kiếm khoảng trống. Mã hóa API Keys nội bộ bằng AES/Fernet.
- **Phase 2 (Mở rộng):** Bổ sung Node `(Concept)` và cạnh `[:REQUIRES]` để vẽ "Cây Khái Niệm" (Concept Tree View), tích hợp thêm Web Search cho Chatbot. Triển khai KMS quản lý khóa API chính thức.

### 1.2. Requirements Overview
**Functional Requirements:**
- **Xác thực & Quản trị:** Đăng nhập/Đăng ký qua JWT lưu trong HttpOnly Cookie. Phân quyền Admin cho tài khoản đăng ký đầu tiên. Cấu hình động các tham số giới hạn lưu trong DB.
- **Quản lý Không gian làm việc:** Workspace-centric. Sidebar trái quản lý CRUD dự án. Trạng thái dự án và chatbot đồng bộ tức thời.
- **Tìm kiếm & Tải tài liệu:** Tìm kiếm song song (arXiv + Semantic Scholar), gộp trùng dựa trên DOI/arXiv ID. Hỗ trợ upload tệp thủ công.
- **AI Agent & Phát hiện khoảng trống:** Trợ lý chatbot RAG + Neo4j/Apache AGE. So sánh chéo bài báo phát hiện mâu thuẫn học thuật.
- **Bản đồ Tri thức:** Sơ đồ tương tác Cytoscape.js vẽ mạng lưới trích dẫn và tác giả.
- **Hỗ trợ viết:** Soạn thảo literature review, quản lý nhiều phiên bản, xuất file ZIP.

**Scale & Complexity:** Hệ thống có độ phức tạp trung bình - cao do tích hợp nhiều công nghệ dữ liệu, xử lý bất đồng bộ, luồng suy luận AI Agent trên LangGraph có tự sửa lỗi trích dẫn.

### 1.3. Infrastructure Constraints
- **Tài nguyên phần cứng:** Giai đoạn khởi chạy đầu tiên (Phase 1) hoạt động trên cấu hình **32GB RAM, 6 vcores**. Phục vụ tối đa **10 người dùng đồng thời**. Dung lượng tối đa 20MB/tệp tải lên. Quản trị viên giám sát tải để nâng cấp lên 48GB hoặc 64GB RAM khi mở rộng.
- **Hiệu năng Database:** RAG latency < 500ms cho DB dưới 100,000 vector. 
- **Cơ chế Dọn dẹp (Garbage Collection):** Xóa mềm khi người dùng xóa dự án. Cronjob định kỳ xóa cứng dữ liệu quá 7 ngày và dọn dẹp file vật lý.

### 1.4. Cross-Cutting Concerns
- **Đồng bộ Trạng thái Client (State Sync):** Cập nhật tiến trình nạp vào bảng `papers` (`progress_percentage`, `current_step`) và stream qua SSE. F5 trình duyệt sẽ gọi API fetch trạng thái DB trước khi kết nối lại SSE để không mất thanh tiến trình.
- **API Limits & Cơ chế Retry:** Chịu ảnh hưởng bởi rate limit của arXiv/Semantic Scholar và Gemini API. Các tác vụ gọi API bên ngoài được bọc trong bộ điều phối `tenacity` với Exponential Backoff Retry.
- **Định tuyến LLM (LLMRouter Pattern):** Phân phối API Keys riêng biệt cho từng Agent, giúp cô lập lỗi chạm hạn mức (HTTP 429), không ảnh hưởng luồng giao tiếp chat realtime.
- **Tính toàn vẹn trích dẫn (Citation Integrity):** 100% trích dẫn do LLM sinh ra phải được đối chiếu thực tế tới đoạn văn bản gốc trong DB thông qua Citation Guardrail Node.
- **Tải dữ liệu đồ thị (Lazy Rendering):** API giới hạn cứng 150 nodes và 300 edges, trả kèm cờ `has_more` để tránh quá tải trình duyệt và Cytoscape.js.

## 2. Technology Stack & Starter Template

- **Primary Domain:** Web Application.
- **Selected Stack:** FastAPI (Backend) + React 19/Vite 8/TypeScript 6 (Frontend).
- **Rationale:** Tận dụng pre-initialized workspace đã có sẵn LangChain và LangGraph, tối ưu hiệu năng tải tệp và xử lý kết nối SSE thời gian thực. Bỏ qua các phương án Full-stack Next.js kết hợp Python chạy riêng rẽ để giảm thiểu độ phức tạp vận hành.

## 3. Data Architecture & Graph Ontology

Hệ thống sử dụng mô hình Cơ sở dữ liệu Kép (Dual-Database Model) phân tách trách nhiệm rõ ràng:

### 3.1. PostgreSQL + pgvector (Lưu trữ Metadata, Vector & RAG)
Xử lý lưu trữ quan hệ và tìm kiếm nhúng vector (với chỉ mục HNSW trên cột `embedding`). Để tránh penalty khi ghi hàng loạt vector, hệ thống có thể tăng `maintenance_work_mem` hoặc rebuild index sau batch.
* **Bảng `projects`, `papers`, `settings`**: Lưu metadata dự án, tài liệu và cấu hình hệ thống động.
* **Bảng `parent_chunks`, `child_chunks`**: Lưu trữ nội dung văn bản băm nhỏ kèm vector embedding.
* **Bảng `sync_outbox`**: Bảng trung gian lưu tác vụ đồng bộ đồ thị.

### 3.2. Neo4j (Knowledge Graph & Ontology)
Lưu trữ cấu trúc đồ thị phục vụ phát hiện khoảng trống nghiên cứu và hiển thị Cytoscape.js. Tích hợp thuật toán lai Hybrid GraphRAG (Microsoft GraphRAG Communities + LightRAG Dual-Level Retrieval).
* **Phân bổ RAM tối ưu (Phase 1 trên VM 32GB):** Cấp `12G` JVM (8G Heap + 4G Page Cache).
* **Entity Resolution (Hợp nhất tác giả):** Chuẩn hóa chuỗi tên. Gộp node nếu tên trùng khớp và có giao thoa đồng tác giả/chủ đề trên Postgres, ngược lại tạo node độc lập.
* **Graph Schema (Phase 1):**
  * **Nodes:** `Paper`, `Author`, `Topic`, `Method`, `Dataset`, `Limitation`, `Problem`, `Community`.
    * `Finding`: `{id, description, confidence_score: Float}` (Điểm do LLM đánh giá 0.0-1.0).
  * **Edges:** `[:AUTHORED_BY]`, `[:CITES]`, `[:HAS_FINDING]`, v.v.
    * *Tương tác học thuật:* `(:Finding)-[:CONTRADICTS]->(:Finding)`, `(:Finding)-[:SUPPORTS]->(:Finding)`, `(:Paper)-[:HAS_LIMITATION]->(:Limitation)`, `(:Paper)-[:FILLS_GAP]->(:Limitation)`.

### 3.3. Tính nhất quán CSDL (Eventual Consistency & Sync Manager)
Đảm bảo đồng bộ dữ liệu an toàn từ Postgres sang Neo4j:
* Khi Postgres thay đổi dữ liệu, một sự kiện được ghi transactionally vào bảng `sync_outbox`.
* Background Worker chạy ngầm sẽ gom nhóm các sự kiện theo `project_id` và quét tuần tự theo `created_at` để đẩy sang Neo4j, đảm bảo Order Guarantee (không gãy đồ thị).
* Nếu lỗi kết nối, tác vụ sẽ retry bằng `tenacity` hoặc xử lý lại sau khi restart (Eventual Consistency).

## 4. Ingestion & RAG Strategy

### 4.1. Nạp tài liệu bất đồng bộ & Quản lý Tài nguyên
* Xử lý bất đồng bộ qua FastAPI `BackgroundTasks`. 
* **Kiểm đếm Concurrency trên Postgres:** Khống chế giới hạn nạp toàn hệ thống qua `CONCURRENT_INGESTION_LIMIT` và giới hạn cho cá nhân qua `MAX_CONCURRENT_PER_USER`. Nếu vượt ngưỡng, API trì hoãn tác vụ vào hàng đợi `pending` để tránh sập hệ thống hoặc 1 người chiếm dụng toàn bộ slot.

### 4.2. Two-Stage Ingestion Pipeline
* **Giai đoạn 1: Document Parsing (Sử dụng Docling)**
  * Chốt dùng **Docling (IBM)** cho Phase 1 vì tối ưu tốt trên CPU. 
  * Tự động phân tích layout, giữ cấu trúc phân cấp, bảng biểu và **crop hình ảnh/biểu đồ** lưu vào `/static/images/` cực chuẩn xác. Xuất ra Raw Markdown.
* **Giai đoạn 2: Semantic Proofreading & Extraction (Gemini 2.5 Pro / 3.1 Flash-Lite)**
  * Tận dụng Context Window 1M-2M tokens gửi nguyên file Markdown.
  * *Proofreading:* Sửa lỗi chính tả OCR, phục hồi dấu tiếng Việt bị vỡ từ Giai đoạn 1.
  * *Hybrid Structured Extraction:* Ưu tiên lấy Metadata từ API/Form, LLM chỉ làm giàu thêm. LLM bóc tách sâu cấu trúc đồ thị (Nodes/Edges) nạp vào Neo4j.
* **Xử lý lỗi LLM:** Việc tách bạch giúp nếu Gemini timeout/rate limit, hệ thống chỉ retry Giai đoạn 2 mà không cần chạy lại tác vụ Docling nặng nề.

### 4.3. Chunking & Global-Local Context
* **Parent-Child Chunking:** Cắt theo thẻ Heading lớn lưu vào `parent_chunks`. Cắt nhỏ đoạn văn chi tiết vào `child_chunks` để nhúng vector.
* **Khử trùng lặp (Deduplicate) & Global Context:** Dùng SQL JOIN để không nạp trùng lặp Parent Chunk. Tóm tắt (Abstract) được chèn làm Global Context ở đầu Prompt để tránh hiệu ứng "Lost in the middle".

### 4.4. Hoạt động của Citation Guardrail Node
Trong LangGraph, Node kiểm chứng trích dẫn tự động bảo vệ tính chính xác:
1. Trích xuất thẻ tham chiếu từ văn bản sinh ra bởi LLM.
2. Kiểm tra ánh xạ tới danh sách tài liệu RAG Context.
3. **Auto-Correction Loop:** Nếu sai, truy vấn vector trên `child_chunks` tìm nguồn gốc. Vòng lặp khống chế tối đa bởi `CITATION_RETRY_LIMIT` (mặc định 2).
4. Nếu độ tương tự > `CITATION_ERROR_THRESHOLD`, sửa thẻ. Nếu thất bại sau số lần thử, đánh dấu `[Cảnh báo: Không xác minh được nguồn]`.
