---
stepsCompleted: [1, 2, 3]
inputDocuments:
  - "file:///home/agent/github/C2-App-053/_bmad-output/planning-artifacts/prds/prd-C2-App-053-2026-06-11/prd.md"
  - "file:///home/agent/github/C2-App-053/_bmad-output/planning-artifacts/architecture.md"
  - "file:///home/agent/github/C2-App-053/_bmad-output/planning-artifacts/ux-designs/ux-C2-App-053-2026-06-12/DESIGN.md"
  - "file:///home/agent/github/C2-App-053/_bmad-output/planning-artifacts/ux-designs/ux-C2-App-053-2026-06-12/EXPERIENCE.md"
---

# C2-App-053 - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for C2-App-053, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: Đăng ký, Đăng nhập & Phân quyền Admin khởi tạo
- Đăng ký tài khoản bằng email/mật khẩu, đăng nhập nhận JWT lưu trữ an toàn trong HttpOnly Cookie (Secure, SameSite=Strict).
- Cơ chế phân quyền tự động: Tài khoản đầu tiên đăng ký trên hệ thống nhận quyền Admin (role = 'admin'), các tài khoản đăng ký sau nhận quyền người dùng thường (role = 'user').
- Xử lý lỗi: Nhập sai thông tin đăng nhập trả về mã lỗi HTTP 401.

FR2: Quản lý Dự án Nghiên cứu (CRUD Projects)
- CRUD Dự án Nghiên cứu (Tên dự án, Mô tả ngắn).
- Quy trình lấy Dự án làm trung tâm: Bắt buộc người dùng mới phải tạo dự án đầu tiên (Onboarding gating) trước khi sử dụng các chức năng khác.
- Sidebar điều hướng bên trái chỉ hiển thị tối đa 10 dự án gần đây kèm nút "Xem tất cả" để chuyển hướng sang trang Quản lý toàn bộ dự án tập trung.
- Cô lập dữ liệu và ngữ cảnh hoàn toàn giữa các dự án thông qua `project_id`.
- Ba tab ngang ở cột giữa (Center Workspace) phản ánh các User Journeys chính: "Thư viện Tài liệu", "Bản đồ Tri thức", và "Hỗ trợ viết tổng quan".

FR3: Tìm kiếm bài báo đa nguồn & Xử lý lỗi API (Degraded Union)
- Tìm kiếm bài báo song song từ arXiv và Semantic Scholar (timeout tối đa 10s).
- Degraded Union: Nếu một nguồn lỗi/timeout, hiển thị kết quả từ nguồn còn lại kèm Toast cảnh báo màu vàng nhẹ ở Frontend, không crash giao diện.
- Khử trùng lặp kết quả (deduplication) dựa trên mã DOI hoặc đối khớp Tiêu đề, lưu tạm siêu dữ liệu và tóm tắt vào PostgreSQL cục bộ.
- Broad Query Handling: Nếu số kết quả vượt quá ngưỡng cấu hình `BROAD_QUERY_THRESHOLD` (mặc định 50), LLM gợi ý các sub-fields MECE dưới dạng thẻ nút bấm có thể click trực tiếp để kích hoạt truy vấn mới.

FR4: Ingestion bất đồng bộ & Hiển thị tiến trình chi tiết
- Ingest tài liệu bất đồng bộ sử dụng FastAPI `BackgroundTasks` (tải PDF Open Access, OCR nếu tệp scan, cắt đoạn, nhúng vector pgvector, ánh xạ Neo4j).
- Sử dụng Server-Sent Events (SSE) để đẩy trạng thái tiến trình chi tiết lên Frontend: "Đang tải từ internet..." -> "Đang quét cấu trúc & OCR..." -> "Đang nhúng vector..." -> "Đã nạp thành công".

FR5: Upload tài liệu thủ công & Trích xuất Metadata tự động
- Hỗ trợ tải lên tệp PDF/DOCX cá nhân (tối đa 20MB).
- Backend sử dụng LLM đọc hiểu và tự động trích xuất siêu dữ liệu (Tiêu đề, Tác giả, Năm, Tóm tắt).
- Frontend hiển thị form điền siêu dữ liệu thủ công với các trường do AI đề xuất có nhãn badge `"AI Suggested"`, cho phép người dùng chỉnh sửa/xác nhận trước khi nhúng vector.

FR6: Chat tương tác thời gian thực với AI Agent (RAG)
- Hỏi đáp thời gian thực với AI Agent (RAG kết hợp pgvector và Neo4j), stream phản hồi qua SSE.
- Khung chatbot cột phải có ô nhập chat cố định ở dưới cùng. Lịch sử chat của dự án hiển thị thông qua nút Lịch sử trò chuyện (icon đồng hồ) nằm ngay dưới tiêu đề panel. Bấm vào nút này mở Popover/Drawer hiển thị danh sách các phiên trò chuyện cũ để chuyển đổi.

FR7: Phát hiện Khoảng trống & Mâu thuẫn nghiên cứu
- AI Agent hỗ trợ so sánh chéo, chỉ ra các mâu thuẫn thực nghiệm hoặc điểm hạn chế chưa giải quyết giữa các bài báo trong dự án, hiển thị rõ ràng nguồn trích dẫn.

FR8: Kiểm chứng và xử lý lỗi trích dẫn ảo (Citation Guardrail)
- Citation Verify Node đối chiếu các thẻ trích dẫn thô (dạng `[1]`, `[2]`) với cơ sở dữ liệu thực tế của dự án.
- Tính toán tỷ lệ lỗi trích dẫn ảo. Nếu tỷ lệ <= `CITATION_ERROR_THRESHOLD` (mặc định 30%), tự động lọc bỏ trích dẫn lỗi hoặc thay bằng `[Nguồn không xác định]`.
- Nếu > ngưỡng, LLM tự sửa (retry) tối đa `CITATION_RETRY_LIMIT` (mặc định 2). Nếu vẫn lỗi, trả kết quả kèm nhãn Cảnh báo độ tin cậy thấp nổi bật ở đầu câu trả lời chat.

FR9: Trực quan hóa mạng lưới bài báo & Phát hiện khoảng trống trực quan
- Vẽ bản đồ mạng lưới bài báo (nodes) và quan hệ trích dẫn (`[:CITES]` nét liền xanh Cobalt) hoặc quan hệ tác giả (`[:AUTHORED]` nét đứt tím) từ Neo4j bằng Cytoscape.js.
- Cho phép thu phóng, kéo thả các node, click node mở Thẻ thông tin Node (Node Detail Card) trượt ra từ góc trên bên phải canvas.
- Chế độ "Tìm khoảng trống nghiên cứu": Tự động tô màu viền đỏ nhấp nháy cho bài viết có mâu thuẫn học thuật hoặc viền vàng cho node cô lập/khoảng trống tiềm năng.

FR10: Tương tác với Thẻ trích dẫn (Citation Interaction)
- Người dùng có thể click hoặc hover vào ký hiệu trích dẫn `[1]`, `[2]` trong chat hoặc bản thảo để mở tooltip nổi (Citation Tooltip) hiển thị text chunk gốc đã được render, siêu dữ liệu bài báo, và cung cấp nút mở/tải tệp gốc.

FR11: Cấu hình giới hạn tài liệu trong dự án (Document Limit Configuration)
- Admin cấu hình giới hạn cứng số tài liệu tối đa được phép nạp trong một dự án `MAX_PAPERS_PER_PROJECT` (mặc định 15).
- Khi chạm giới hạn, chặn các hành động tải lên/nạp tiếp theo trên UI và hiển thị thông báo lỗi cảnh báo cứng. Trả về lỗi HTTP 403 ở API.

FR12: Lưu trữ cấu hình động
- Lưu trữ các cấu hình giới hạn động (MAX_PAPERS_PER_PROJECT, BROAD_QUERY_THRESHOLD, CITATION_ERROR_THRESHOLD, CITATION_RETRY_LIMIT) vào Database để Admin chỉnh sửa mà không cần khởi động lại máy chủ.

FR13: Soạn thảo & Quản lý bản thảo tổng quan (Literature Review Drafting & Management)
- Người dùng soạn thảo literature review bằng rich editor ở cột giữa (Tab Hỗ trợ viết tổng quan), lưu trữ nhiều phiên bản bản thảo theo dự án. AI hỗ trợ đề xuất câu chữ và định dạng văn bản trực tiếp.

FR14: Xuất bản thảo và tài liệu trích dẫn
- Cho phép xuất kết quả bản thảo dưới dạng tệp ZIP chứa tệp văn bản Markdown (`.md`) và tệp danh mục trích dẫn định dạng BibTeX/APA (`.bib`).

FR15: Hỗ trợ định hướng người dùng theo trạng thái dự án (Context-Aware User Guiding)
- Khi dự án mới hoặc khi được yêu cầu, Frontend gửi các trạng thái (`active_tab`, `document_count`, `has_draft`) đến AI Agent.
- AI Agent phản hồi lời khuyên kèm các nút hành động gợi ý động (Dynamic Quick Reply Buttons như `[Tải tài liệu lên]`, `[Xem bản đồ tri thức]`, `[Gợi ý dàn ý]`) để tự động chuyển hướng tab tương ứng khi click.

### NonFunctional Requirements

NFR1 (Hiệu năng phản hồi): Độ trễ phản hồi của Chatbot từ khi gửi tin đến khi stream ký tự đầu tiên qua SSE không quá 3 giây.
NFR2 (Hiệu năng truy vấn RAG): Thời gian truy vấn RAG dưới 500ms đối với cơ sở dữ liệu dưới 100,000 vector nhờ kết hợp chỉ mục HNSW trên embeddings và B-Tree trên project_id.
NFR3 (Tải đồng thời): Phục vụ tối đa 50 người dùng hoạt động đồng thời (active sessions) trên cấu hình tối thiểu là máy ảo Xubuntu 6 vcores, 32GB RAM.
NFR4 (Giới hạn dung lượng): Dung lượng tải lên tối đa là 20MB cho mỗi tệp tài liệu cá nhân (PDF/DOCX).
NFR5 (Xử lý nền): Sử dụng FastAPI BackgroundTasks kết hợp với ThreadPoolExecutor riêng để xử lý ngầm (tải tệp, OCR, embedding) mà không làm block main event loop của FastAPI.
NFR6 (Kết nối SSE): Vận hành qua HTTP/2 trên Nginx và tắt buffering (proxy_buffering off; X-Accel-Buffering: no) để tránh nghẽn kết nối SSE (giới hạn 6 kết nối trên HTTP/1.1 của trình duyệt).
NFR7 (Độ chính xác trích dẫn): 100% trích dẫn xuất hiện trong câu trả lời do AI sinh ra phải khớp chính xác với tài liệu thực tế có sẵn trong dự án.
NFR8 (Tính khả dụng tiến trình): 100% tệp nạp bất đồng bộ phải hiển thị đúng trạng thái tiến trình qua SSE (đang tải -> đang OCR -> đang nhúng -> đã nạp) mà không bị mất kết nối.

### Additional Requirements

- Starter Template: Sử dụng Vite + React (TypeScript) khởi tạo tại thư mục `/frontend` bằng lệnh: `npm create vite@latest frontend -- --template react-ts`.
- Quy chuẩn đặt tên đồng bộ (snake_case cho DB & JSON keys API; PascalCase cho React Components, CSS Modules, Python Classes, Neo4j Node Labels; UPPERCASE snake_case cho Neo4j Relationship Labels).
- Cấu hình giới hạn bộ nhớ Neo4j: Giới hạn RAM heap và pagecache tối đa 1.5GB - 2GB trong cấu hình Docker để tối ưu hóa tài nguyên trên máy ảo 32GB RAM.
- Đồng bộ bất đồng bộ Neo4j: Đồng bộ quan hệ Neo4j được chạy bất đồng bộ trong background task sau khi dữ liệu PostgreSQL ghi thành công để không gián đoạn luồng nghiệp vụ chính.
- Cơ chế Xóa mềm & Lưu trữ (Soft Delete & Archiving): Khi xóa tài liệu, chỉ cập nhật trạng thái sang `archived`. Tài liệu archived không tính vào giới hạn MAX_PAPERS_PER_PROJECT, loại khỏi truy vấn RAG chủ động, nhưng giữ siêu dữ liệu và text chunk để hỗ trợ hiển thị trích dẫn cũ. Trên Bản đồ tri thức, các node archived hiển thị màu xám mờ để giữ lịch sử trích dẫn. Hiển thị cảnh báo chuyển sang lưu trữ nếu tài liệu đang được sử dụng làm trích dẫn trong bản thảo hiện tại.
- Định dạng Lỗi Tiêu chuẩn: API trả về lỗi dạng JSON `{ "detail": "Thông điệp lỗi" }` sử dụng chuẩn các mã lỗi HTTP: 400 (Validation), 401 (Auth), 403 (Limit/Admin), 404 (Not Found).
- Ranh giới Component 3 cột độc lập: Sidebar chỉ CRUD dự án, không chứa tab; Center Workspace chứa 3 tab ngang tương ứng 3 User Journeys chính; Chatbot Panel có biên kéo giãn 20-40% và có thể thu gọn hoàn toàn.

### UX Design Requirements

UX-DR1 (Hệ thống Màu sắc & Chế độ Sáng/Tối): Mặc định hiển thị chế độ sáng (Light Mode, nền giấy ấm `#FAF9F6`, nền nổi `#FFFFFF`, chữ `#1E2022`, màu nhấn xanh cobalt `#2563EB`, tím thạch anh `#8B5CF6`). Hỗ trợ Soft Dark Mode (nền `#1F2023`, nền nổi `#282A2D`, chữ `#E4E6EB`, viền `#383A40`) chuyển đổi qua nút trên Header. Đảm bảo độ tương phản đạt chuẩn WCAG AA/AAA.
UX-DR2 (Kiểu chữ và Reset CSS): Phông chữ chính là `Inter`, các kích thước tiêu đề (16px, weight 600, line-height 22px), thân bài (13px, weight 400, line-height 18px), chú thích (11px, line-height 14px).
UX-DR3 (Bố cục 3 cột co giãn và ẩn/hiện):
  - Cột 1 (Sidebar trái - 240px): CRUD dự án, nút tạo dự án nổi bật, danh sách tối đa 10 dự án (scrollbar dọc mượt mà nếu dài hơn), nút "Xem tất cả" chuyển hướng đến trang Quản lý toàn bộ dự án tập trung.
  - Cột 2 (Center Workspace): Chứa thanh Tab ngang ở trên cùng ("Thư viện Tài liệu", "Bản đồ Tri thức", "Hỗ trợ viết tổng quan") và khu vực nội dung tương ứng bên dưới.
  - Cột 3 (Chatbot Panel): Biên trái có dải kéo giãn rộng 4px (hitbox ẩn 10px), cho phép resize chiều rộng 20-40% màn hình, đúp click để reset về 25%. Nút ẩn/hiện chat thu gọn hoàn toàn chatbot về 0px.
UX-DR4 (Popover Lịch sử Chat & Nút Trò chuyện Mới):
  - Cụm nút ngang hàng ngay dưới tiêu đề Chatbot Panel gồm nút Lịch sử trò chuyện (mở Popover/Drawer hiển thị danh sách các phiên chat cũ trong dự án) và nút Trò chuyện mới. Ô chat input nằm ngay dưới cụm nút này.
UX-DR5 (Thẻ trích dẫn Tooltip): Hover hoặc click thẻ trích dẫn `[1]`, `[2]` mở tooltip nổi bo góc 8px hiển thị đoạn văn bản trích dẫn gốc, siêu dữ liệu bài viết và các nút mở/tải tệp gốc.
UX-DR6 (Cytoscape.js Bản đồ Tri thức):
  - Nền bản đồ `#FAF9F6`. Đỉnh toàn văn (xanh lá `#10B981`), đỉnh siêu dữ liệu (viền đứt cam `#F59E0B`). Đường trích dẫn mũi tên màu xanh `#2563EB`. Đường tác giả màu tím `#8B5CF6`.
  - Node Detail Card: Thẻ thông tin trượt ra từ góc trên bên phải canvas khi click một node.
  - Chế độ Tìm khoảng trống: Nút nổi góc trái đồ thị để bật chế độ đánh dấu khoảng trống/mâu thuẫn (viền đỏ nhấp nháy `#EF4444` cho mâu thuẫn, vàng cho node cô lập/khoảng trống tiềm năng).
UX-DR7 (Onboarding & Guest Landing Page):
  - Landing page cho khách vãng lai: Hero Banner, Interactive Demo Simulator (giả lập 3 cột có dải băng cảnh báo chạy thử màu vàng và node đỏ nhấp nháy gap alert), bảng giá (free/pro).
  - Màn hình Onboarding cho người dùng mới: Split layout (bên trái là form tạo dự án đầu tiên, bên phải là checklist 3 bước và slide/ảnh động hướng dẫn).
UX-DR8 (Dashboard chọn dự án & central management page):
  - User Dashboard: Lưới dự án Responsive (3 cột PC rộng, 2 cột PC vừa/tablet, 1 cột mobile) có hiệu ứng hover thẻ dự án (dịch chuyển `translateY(-2px)` và viền đổi sang xanh Cobalt).
  - Trang Quản lý toàn bộ dự án tập trung: Bảng danh sách dự án đầy đủ có tìm kiếm, phân trang và CRUD.
UX-DR9 (Form điền siêu dữ liệu thủ công & Toast lỗi API):
  - Giao diện điền siêu dữ liệu: Các trường do AI tự trích xuất có nhãn badge `"AI Suggested"` màu thạch anh.
  - Toast lỗi API: Toast màu vàng nhạt viền cam xuất hiện ở góc trên bên phải khi arXiv hoặc Semantic Scholar API lỗi/timeout, tự tắt sau 5s hoặc nút đóng (x).

### FR Coverage Map

FR1: Epic 1 - Đăng ký, Đăng nhập & Phân quyền Admin khởi tạo
FR2: Epic 1 - Quản lý Dự án Nghiên cứu (CRUD, Onboarding gating, sidebar, isolation)
FR3: Epic 2 - Tìm kiếm bài báo đa nguồn, Degraded Union, Broad Query sub-fields
FR4: Epic 2 - Ingestion bất đồng bộ qua FastAPI BackgroundTasks, SSE progress status flow
FR5: Epic 2 - Upload tài liệu thủ công & form AI Suggested Metadata
FR6: Epic 4 - Chat RAG thời gian thực, Drawer lịch sử chat
FR7: Epic 4 - Phát hiện khoảng trống/mâu thuẫn qua chat RAG
FR8: Epic 4 - Citation Guardrail (verify node, error rate threshold, LLM self-correct, low confidence warning)
FR9: Epic 3 - Bản đồ tri thức Cytoscape.js & Neo4j, Gap warnings viền nháy
FR10: Epic 4 - Citation Tooltip hiển thị chunk gốc & metadata
FR11: Epic 1 / Epic 2 - Admin cấu hình giới hạn MAX_PAPERS_PER_PROJECT (cấu hình trong Epic 1, thực thi trong Epic 2)
FR12: Epic 1 - Lưu cấu hình động hệ thống trong DB
FR13: Epic 5 - Soạn thảo & quản lý bản thảo, AI assist
FR14: Epic 5 - Xuất tệp ZIP chứa Markdown (.md) & BibTeX (.bib)
FR15: Epic 4 - AI định hướng người dùng theo trạng thái dự án, Dynamic Quick Reply buttons
Cơ chế Xóa mềm & Lưu trữ: Epic 2 - Giao diện Thư viện & Xóa mềm/Lưu trữ Tài liệu (Soft Delete/Archiving)

## Epic List

### Epic 1: Quản lý Người dùng, Dự án & Cấu hình Hệ thống (Workspace Foundation & Settings)
Thiết lập nền tảng hệ thống cho phép người dùng đăng ký, đăng nhập, khởi tạo và quản lý không gian dự án nghiên cứu độc lập. Đồng thời cung cấp giao diện Cài đặt cho Admin để cấu hình động hệ thống từ Database.
**FRs covered:** FR1, FR2, FR11 (phần cấu hình), FR12

### Epic 2: Thư viện Tài liệu & Quy trình Nạp bất đồng bộ (Document Library & Ingestion)
Triển khai luồng tìm kiếm bài báo đa nguồn, tải lên tệp cá nhân và quy trình nạp tài liệu bất đồng bộ (OCR, Embedding RAG, đồng bộ Neo4j) có hiển thị tiến trình SSE chi tiết và form xác nhận siêu dữ liệu do AI gợi ý.
**FRs covered:** FR3, FR4, FR5, FR11 (phần thực thi chặn nạp), Cơ chế Xóa mềm & Lưu trữ (Additional Requirement)

### Epic 3: Đồ thị Bản đồ Tri thức học thuật tương tác (Interactive Knowledge Map)
Dựng mạng lưới đồ thị liên kết trích dẫn và tác giả từ Neo4j bằng Cytoscape.js trong tab "Bản đồ Tri thức", hỗ trợ chế độ xem chi tiết node và đánh dấu các khoảng trống nghiên cứu/mâu thuẫn học thuật trực quan bằng hiệu ứng nhấp nháy.
**FRs covered:** FR9

### Epic 4: Trợ lý AI Chatbot & Kiểm định Trích dẫn (AI Companion & Citation Guardrail)
Phát triển khung chatbot AI RAG (Pgvector + Neo4j) hiển thị lịch sử chat, cung cấp các nút gợi ý định hướng hành động theo trạng thái, tích hợp bộ kiểm định chống trích dẫn ảo (Citation Guardrail) và các tooltip trích dẫn tương tác hiển thị văn bản bằng chứng gốc.
**FRs covered:** FR6, FR7, FR8, FR10, FR15

### Epic 5: Soạn thảo Literature Review & Xuất Bản thảo (Overview Writing & Export)
Triển khai khu vực soạn thảo văn bản trong tab "Hỗ trợ viết tổng quan" với sự trợ giúp viết của AI, quản lý các bản nháp và hỗ trợ xuất tệp ZIP chứa tài liệu Markdown cùng danh mục trích dẫn chuẩn BibTeX.
**FRs covered:** FR13, FR14

## Epic 1: Quản lý Người dùng, Dự án & Cấu hình Hệ thống (Workspace Foundation & Settings)

Thiết lập nền tảng hệ thống cho phép người dùng đăng ký, đăng nhập, khởi tạo và quản lý không gian dự án nghiên cứu độc lập. Đồng thời cung cấp giao diện Cài đặt cho Admin để cấu hình động hệ thống từ Database.

### Story 1.1: Khởi tạo dự án từ Starter Template (Vite + React TS)

As a kỹ sư phát triển,
I want khởi tạo mã nguồn Frontend từ starter template được phê duyệt,
So that tôi có cấu trúc dự án chuẩn và môi trường chạy thử nghiệm sẵn sàng.

**Acceptance Criteria:**

**Given** môi trường phát triển đã sẵn sàng ở thư mục dự án
**When** chạy lệnh khởi tạo `npm create vite@latest frontend -- --template react-ts`
**Then** hệ thống tạo thư mục `/frontend` chứa mã nguồn Vite + React + TypeScript tĩnh
**And** cấu hình ESLint, Prettier và tệp `vite.config.ts` để serve static files
**And** chạy thành công lệnh `npm run dev` để khởi động môi trường phát triển local không lỗi

### Story 1.2: Đăng ký, Đăng nhập & Phân quyền Admin khởi tạo (FR-1)

As a người dùng mới hoặc hiện tại,
I want đăng ký tài khoản và đăng nhập vào hệ thống an toàn,
So that tôi có thể truy cập không gian làm việc cá nhân của mình.

**Acceptance Criteria:**

**Given** người dùng chưa xác thực đang ở trang đăng ký/đăng nhập
**When** người dùng điền Email và Mật khẩu hợp lệ và bấm Đăng ký
**Then** hệ thống khởi tạo bản ghi trong bảng `users` ở DB PostgreSQL
**And** nếu đây là người dùng đầu tiên đăng ký, gán vai trò `admin`, các người dùng sau nhận vai trò `user`
**Given** người dùng đã đăng ký thành công
**When** người dùng đăng nhập bằng Email và Mật khẩu đúng
**Then** hệ thống cấp mã JWT lưu trong HttpOnly Cookie với cờ `Secure`, `SameSite=Strict` và điều hướng vào hệ thống
**And** nếu thông tin đăng nhập sai, hệ thống trả về mã lỗi HTTP 401 và hiển thị Banner lỗi đăng nhập trên Frontend

### Story 1.3: CRUD Dự án Nghiên cứu & Giao diện Sidebar trái (FR-2, UX-DR3, UX-DR1, UX-DR2)

As a nhà nghiên cứu đã đăng nhập,
I want tạo, xem, cập nhật và xóa các dự án nghiên cứu của tôi ngay trên Sidebar,
So that tôi có thể tổ chức và cô lập công việc theo từng chủ đề nghiên cứu.

**Acceptance Criteria:**

**Given** người dùng đã đăng nhập thành công
**Then** người dùng thấy giao diện 3 cột mặc định chế độ Sáng (nền `#FAF9F6`), sử dụng phông chữ `Inter`
**When** người dùng click nút "+ Tạo dự án mới" ở trên cùng Sidebar trái (rộng 240px)
**Then** người dùng điền tên dự án và mô tả ngắn để lưu vào bảng `projects` trong PostgreSQL (cô lập theo `user_id`)
**And** dự án mới hiển thị ngay trong danh sách dự án của Sidebar trái (tối đa hiển thị 10 dự án gần nhất, hỗ trợ scrollbar dọc nếu danh sách dài)
**When** người dùng hover qua một dòng dự án trong Sidebar
**Then** các biểu tượng Chỉnh sửa tên và Xóa dự án xuất hiện ở mép phải
**When** người dùng click nút Xóa dự án
**Then** hệ thống hiển thị Modal xác nhận trước khi xóa dự án trong cơ sở dữ liệu
**When** người dùng click nút Toggle giao diện ở Header
**Then** hệ thống chuyển đổi lập tức giữa Light Mode và Soft Dark Mode (nền `#1F2023`)

### Story 1.4: Màn hình Onboarding và User Dashboard (FR-2, UX-DR7, UX-DR8)

As a nhà nghiên cứu,
I want được hướng dẫn tạo dự án đầu tiên khi mới đăng nhập, hoặc chọn dự án từ bảng điều khiển trực quan,
So that tôi có thể dễ dàng bắt đầu hoặc chuyển đổi công việc.

**Acceptance Criteria:**

**Given** người dùng mới đăng nhập và chưa có bất kỳ dự án nào trong DB
**Then** hệ thống hiển thị màn hình Onboarding với giao diện chia đôi (45% form tạo dự án nhanh bên trái, 55% checklist 3 bước và hướng dẫn dạng slide/ảnh động bên phải)
**Given** người dùng đã đăng nhập và có ít nhất một dự án trong DB
**When** người dùng truy cập trang chủ hệ thống
**Then** hệ thống hiển thị trang User Dashboard dạng lưới Responsive (3 cột trên PC rộng, 2 cột trên PC vừa/tablet, 1 cột trên mobile) gồm các thẻ dự án
**When** người dùng di chuột qua một thẻ dự án trên Dashboard
**Then** thẻ dịch chuyển nhẹ lên trên (`transform: translateY(-2px)`) và đổi viền sang màu xanh Cobalt

### Story 1.5: Trang Quản lý Dự án Tập trung (FR-2, UX-DR8)

As a nhà nghiên cứu có nhiều dự án,
I want quản lý toàn bộ danh sách dự án ở một trang tập trung có phân trang và tìm kiếm,
So that tôi có thể dễ dàng tìm và quản lý các dự án cũ đã ẩn khỏi Sidebar.

**Acceptance Criteria:**

**Given** người dùng click nút "Xem tất cả" dưới danh sách dự án ở Sidebar
**Then** hệ thống điều hướng đến trang Quản lý dự án tập trung
**And** hiển thị bảng danh sách toàn bộ dự án với các thông tin (Tên, Mô tả, Số tài liệu, Ngày cập nhật, Thao tác CRUD)
**When** người dùng gõ từ khóa vào thanh tìm kiếm nhanh của bảng
**Then** danh sách dự án tự động lọc tương ứng
**And** bảng hỗ trợ phân trang số ở góc dưới bên phải

### Story 1.6: Lưu trữ Cấu hình Động & Giao diện Cài đặt Admin (FR-11, FR-12, UX-DR10)

As an Admin hệ thống,
I want điều chỉnh các tham số cấu hình động và lưu trữ chúng vào Database thông qua giao diện cài đặt chuyên biệt,
So that tôi có thể tùy chỉnh các giới hạn kỹ thuật của hệ thống mà không cần restart server.

**Acceptance Criteria:**

**Given** người dùng thông thường (`role = 'user'`)
**Then** họ không thấy biểu tượng bánh răng "Cài đặt Hệ thống" trên Header và bị chặn HTTP 403 khi gọi API cấu hình cài đặt
**Given** người dùng Admin (`role = 'admin'`)
**When** họ click vào biểu tượng bánh răng cài đặt ở Header
**Then** hệ thống điều hướng đến trang Cài đặt Admin có chứa các tab cấu hình dọc/ngang (Giới hạn hệ thống, Trích dẫn & AI, Quản trị người dùng)
**When** Admin chỉnh sửa các tham số (MAX_PAPERS_PER_PROJECT, BROAD_QUERY_THRESHOLD, CITATION_ERROR_THRESHOLD, CITATION_RETRY_LIMIT) and click "Lưu cấu hình"
**Then** hệ thống ghi nhận các giá trị mới vào bảng `system_configurations` trong PostgreSQL
**And** các thay đổi này được áp dụng động tức thời trên toàn hệ thống mà không cần restart server

## Epic 2: Thư viện Tài liệu & Quy trình Nạp bất đồng bộ (Document Library & Ingestion)

Triển khai luồng tìm kiếm bài báo đa nguồn, tải lên tệp cá nhân và quy trình nạp tài liệu bất đồng bộ (OCR, Embedding RAG, đồng bộ Neo4j) có hiển thị tiến trình SSE chi tiết và form xác nhận siêu dữ liệu do AI gợi ý.

### Story 2.1: Tìm kiếm bài báo đa nguồn (arXiv & Semantic Scholar) & Gợi ý từ khóa rộng (FR-3, UX-DR16, UX-DR17)

As a nhà nghiên cứu ở tab Thư viện Tài liệu,
I want tìm kiếm tài liệu học thuật theo từ khóa từ các nguồn arXiv và Semantic Scholar đồng thời,
So that tôi có thể tìm thấy các tài liệu liên quan mà không sợ bị gián đoạn do lỗi API ngoài và có thêm gợi ý khi tìm khóa quá rộng.

**Acceptance Criteria:**

**Given** người dùng đang ở Tab Thư viện Tài liệu (Cột giữa)
**When** người dùng nhập từ khóa tìm kiếm và nhấn Enter
**Then** hệ thống gọi song song API arXiv và Semantic Scholar (timeout tối đa 10s)
**And** kết quả được khử trùng lặp theo DOI hoặc Tiêu đề, sau đó hiển thị danh sách bài báo trên Frontend
**Given** một trong hai API bị lỗi hoặc timeout
**Then** hệ thống vẫn trả về kết quả của API thành công còn lại
**And** Frontend hiển thị Toast cảnh báo màu vàng nhạt viền cam góc trên bên phải (tự tắt sau 5 giây hoặc click đóng) ghi rõ lỗi từ nguồn nào
**Given** tổng số kết quả tìm thấy lớn hơn `BROAD_QUERY_THRESHOLD` (mặc định 50)
**Then** hệ thống gọi LLM sinh danh sách gợi ý phân ngành (sub-fields) dạng MECE
**And** Frontend hiển thị các thẻ gợi ý dạng nút bấm có thể click dưới thanh tìm kiếm. Bấm vào nút sẽ tự động điền query mới và chạy tìm kiếm

### Story 2.2: Nạp bài báo bất đồng bộ & Hiển thị tiến trình chi tiết qua SSE (FR-4, NFR5, NFR8, UX-DR14)

As a nhà nghiên cứu ở tab Thư viện Tài liệu,
I want thêm bài báo từ kết quả tìm kiếm vào dự án và theo dõi tiến trình xử lý ngầm của hệ thống,
So that tôi biết tài liệu được xử lý đến đâu mà không phải chờ đợi trong trạng thái đơ trình duyệt.

**Acceptance Criteria:**

**Given** người dùng đang ở Tab Thư viện Tài liệu của dự án có danh sách kết quả tìm kiếm bài báo
**When** người dùng nhấn nút "Thêm vào dự án" trên một dòng kết quả tìm kiếm
**Then** hệ thống lưu siêu dữ liệu bài báo vào PostgreSQL
**And** kích hoạt FastAPI `BackgroundTasks` chạy trên một `ThreadPoolExecutor` riêng để: tải tệp PDF Open Access ngầm, thực hiện OCR (nếu là PDF scan), cắt đoạn văn bản (chunking), tạo embedding pgvector (có index HNSW phối hợp B-Tree), và đồng bộ bất đồng bộ quan hệ trích dẫn sang Neo4j
**And** hệ thống thiết lập kết nối Server-Sent Events (SSE) để đẩy trạng thái tiến trình xử lý chi tiết từ Backend lên Frontend
**Then** Frontend hiển thị thanh tiến trình nằm ngang màu xanh Cobalt dưới dòng tài liệu tương ứng
**And** nhãn văn bản trạng thái hiển thị động theo sự kiện SSE nhận được: `"Đang tải từ internet..."` -> `"Đang quét cấu trúc & OCR..."` -> `"Đang nhúng vector..."` -> `"Đã nạp thành công"`

### Story 2.5: Giao diện Thư viện & Xóa mềm/Lưu trữ Tài liệu (Soft Delete/Archiving)

As a nhà nghiên cứu,
I want thực hiện xóa mềm (chuyển sang lưu trữ) các tài liệu trong dự án,
So that tôi có thể quản lý số lượng tài liệu trong giới hạn của dự án mà không làm mất lịch sử trích dẫn của các bản thảo cũ.

**Acceptance Criteria:**

**Given** người dùng đang ở Tab Thư viện tài liệu của dự án có danh sách các tài liệu đã nạp
**When** người dùng click nút Xóa tài liệu
**Then** hệ thống đối chiếu xem tài liệu có đang được sử dụng làm trích dẫn trong bản thảo hiện tại hay không
**And** nếu tài liệu đang được trích dẫn, hệ thống hiển thị cảnh báo yêu cầu người dùng xác nhận chuyển sang trạng thái lưu trữ an toàn (Archived)
**When** người dùng xác nhận xóa/lưu trữ tài liệu
**Then** Backend cập nhật trạng thái tài liệu sang `archived` trong PostgreSQL
**And** tài liệu archived được giải phóng khỏi giới hạn tối đa `MAX_PAPERS_PER_PROJECT` và loại khỏi các truy vấn RAG chủ động
**And** siêu dữ liệu và các text chunk của tài liệu vẫn được lưu trữ để hỗ trợ trích dẫn cũ hiển thị trong Citation Tooltip
**And** trên Bản đồ Tri thức, node tương ứng của tài liệu chuyển sang hiển thị màu xám mờ để giữ tính lịch sử quan hệ trích dẫn

### Story 2.3: Upload tài liệu cá nhân & Form siêu dữ liệu gợi ý của AI (FR-5, NFR4, UX-DR9, UX-DR15)

As a nhà nghiên cứu ở tab Thư viện Tài liệu,
I want upload tệp PDF/DOCX cá nhân của tôi lên và để AI tự động trích xuất thông tin,
So that tôi có thể kiểm chứng và điền nhanh siêu dữ liệu thay vì nhập tay hoàn toàn.

**Acceptance Criteria:**

**Given** khu vực kéo thả tệp trong tab Thư viện tài liệu
**When** người dùng kéo thả tệp PDF/DOCX cá nhân
**Then** hệ thống kiểm tra dung lượng tệp. Nếu lớn hơn 20MB, chặn tải lên và hiển thị thông báo lỗi
**And** nếu tệp <= 20MB, hệ thống chạy BackgroundTasks để đọc tệp thô, gọi LLM tự động đọc hiểu trích xuất siêu dữ liệu (Tiêu đề, Tác giả, Năm, Tóm tắt)
**When** tiến trình trích xuất hoàn tất
**Then** hệ thống hiển thị Form điền siêu dữ liệu thủ công trên Frontend
**And** các trường thông tin được điền sẵn dữ liệu do AI trích xuất kèm nhãn badge `"AI Suggested"` màu thạch anh bên cạnh
**When** người dùng chỉnh sửa (nếu cần) và bấm nút "Xác nhận"
**Then** hệ thống lưu chính thức thông tin vào PostgreSQL, thực hiện nhúng vector và cập nhật trạng thái đã nạp

### Story 2.4: Kiểm soát Giới hạn Tài liệu trong dự án (FR-11, UX-DR18)

As a nhà nghiên cứu đang làm việc trong dự án,
I want hệ thống cảnh báo và chặn tôi khi dự án đạt giới hạn tài liệu tối đa của hệ thống,
So that tôi không nạp quá giới hạn tài nguyên được cấp và biết khi nào cần xóa bớt tài liệu cũ.

**Acceptance Criteria:**

**Given** số lượng tài liệu hiện có trong dự án >= `MAX_PAPERS_PER_PROJECT` (mặc định 15, do Admin cấu hình)
**Then** hệ thống vô hiệu hóa (disabled) nút nạp tài liệu và khu vực kéo thả file trong tab Thư viện tài liệu
**And** Frontend hiển thị hộp cảnh báo lỗi cứng màu đỏ viền đậm màu `state-danger` ghi: "Dự án đã đạt giới hạn tài liệu tối đa của hệ thống ({MAX_PAPERS_PER_PROJECT} tài liệu). Vui lòng liên hệ Admin hoặc xóa bớt tài liệu."
**When** người dùng cố tình gọi API tải lên/thêm bài báo qua các công cụ ngoài
**Then** API trả về mã lỗi HTTP 403 Forbidden kèm chi tiết lỗi chặn

## Epic 3: Đồ thị Bản đồ Tri thức học thuật tương tác (Interactive Knowledge Map)

Dựng mạng lưới đồ thị liên kết trích dẫn và tác giả từ Neo4j bằng Cytoscape.js trong tab "Bản đồ Tri thức", hỗ trợ chế độ xem chi tiết node và đánh dấu các khoảng trống nghiên cứu/mâu thuẫn học thuật trực quan bằng hiệu ứng nhấp nháy.

### Story 3.1: Trực quan hóa mạng lưới bài viết bằng Cytoscape.js & Neo4j (FR-9, UX-DR6)

As a nhà nghiên cứu ở tab Bản đồ Tri thức,
I want xem sơ đồ mạng lưới trích dẫn và tác giả của các tài liệu trong dự án dưới dạng đồ thị trực quan,
So that tôi có thể dễ dàng thu phóng, di chuyển các nút để theo dõi mối liên kết học thuật.

**Acceptance Criteria:**

**Given** người dùng chọn Tab 2 "Bản đồ Tri thức" (Cột giữa)
**When** tab được mở, Frontend gọi API `/api/v1/projects/{id}/graph` của Backend
**Then** Backend truy vấn Neo4j lấy danh sách các đỉnh (Paper, Author) và cạnh (`:CITES`, `:AUTHORED`) thuộc dự án hiện tại và trả về JSON
**Then** Frontend render đồ thị bằng thư viện Cytoscape.js trên nền giấy ấm `#FAF9F6`
**And** đỉnh bài viết toàn văn hiển thị màu xanh lá `#10B981` viền đậm, đỉnh chỉ có siêu dữ liệu hiển thị vòng tròn nét đứt viền cam `#F59E0B`
**And** đường trích dẫn `:CITES` hiển thị nét liền màu xanh Cobalt `#2563EB` có mũi tên định hướng, đường tác giả `:AUTHORED` hiển thị nét đứt màu tím `#8B5CF6`
**When** người dùng thực hiện thao tác zoom, kéo thả (drag) các node
**Then** canvas Cytoscape phản hồi mượt mà không crash
**When** người dùng click vào một node bài viết
**Then** Thẻ thông tin Node (Node Detail Card) trượt ra từ góc trên bên phải của canvas hiển thị siêu dữ liệu (Tiêu đề, Tác giả, Năm, DOI, Tóm tắt)

### Story 3.2: Chế độ Tìm khoảng trống & Cảnh báo trực quan trên sơ đồ (FR-9, UX-DR6)

As a nhà nghiên cứu ở tab Bản đồ Tri thức,
I want kích hoạt chế độ phát hiện khoảng trống nghiên cứu và mâu thuẫn trực tiếp trên sơ đồ đồ thị,
So that tôi có thể phát hiện nhanh bằng mắt các vùng nghi ngờ chứa khoảng trống tri thức hoặc mâu thuẫn thực nghiệm.

**Acceptance Criteria:**

**Given** người dùng đang xem Bản đồ tri thức
**When** người dùng click nút nổi "Tìm khoảng trống nghiên cứu" ở góc trái bản đồ
**Then** hệ thống chạy thuật toán phân tích đồ thị Neo4j kết hợp RAG để xác định các node/vùng nghi vấn (mâu thuẫn học thuật hoặc cụm cô lập)
**Then** trên sơ đồ, các node có mâu thuẫn học thuật hiển thị viền đỏ nhấp nháy tỏa bóng mờ (`animation: pulse 1.5s infinite` hoặc tương đương) và các node cô lập/khoảng trống hiển thị viền vàng nhạt
**When** người dùng click vào node có cảnh báo
**Then** Node Detail Card trượt ra hiển thị rõ chi tiết cảnh báo (ví dụ: "Mâu thuẫn thực nghiệm về độ chính xác với tài liệu [X]" hoặc "Bài viết bị cô lập, chưa có nghiên cứu trích dẫn liên quan")

## Epic 4: Trợ lý AI Chatbot & Kiểm định Trích dẫn (AI Companion & Citation Guardrail)

Phát triển khung chatbot AI RAG (Pgvector + Neo4j) hiển thị lịch sử chat, cung cấp các nút gợi ý định hướng hành động theo trạng thái, tích hợp bộ kiểm định chống trích dẫn ảo (Citation Guardrail) và các tooltip trích dẫn tương tác hiển thị văn bản bằng chứng gốc.

### Story 4.1: Khung giao diện Chatbot AI co giãn & ẩn/hiện (UX-DR3, UX-DR4)

As a nhà nghiên cứu,
I want co giãn hoặc thu gọn khung chatbot bên phải tùy ý, và chuyển đổi lịch sử các phiên chat nhanh chóng,
So that tôi có thể mở rộng không gian cho sơ đồ đồ thị ở giữa hoặc xem lại các cuộc hội thoại cũ.

**Acceptance Criteria:**

**Given** khung Chatbot ở Cột 3 (rộng mặc định 25% màn hình)
**When** người dùng rê chuột vào biên trái của khung Chatbot (con trỏ đổi thành `col-resize`)
**Then** người dùng có thể kéo để thay đổi chiều rộng từ 20% đến 40% màn hình, thả chuột để lưu kích thước. Đúp click biên kéo reset về 25%
**When** người dùng click nút ẩn chat ở Header
**Then** khung Chatbot thu gọn hoàn toàn về bên phải (rộng 0px). Click lại nút này để khôi phục kích thước cũ
**When** người dùng click nút Lịch sử trò chuyện (icon đồng hồ) nằm ngang hàng với nút Trò chuyện mới (+) ở đầu panel
**Then** hệ thống mở Popover hiển thị danh sách các phiên trò chuyện cũ trong dự án hiện tại. Click một phiên để tải lại cuộc trò chuyện và đóng popover

### Story 4.2: Chat RAG thời gian thực qua LangGraph & pgvector (FR-6, NFR1, NFR2)

As a nhà nghiên cứu ở khung chat,
I want đặt câu hỏi và nhận câu trả lời stream thời gian thực từ AI dựa trên tài liệu đã nạp,
So that tôi có thể tra cứu thông tin nhanh chóng với độ trễ tối thiểu.

**Acceptance Criteria:**

**Given** người dùng nhập câu hỏi vào ô Chat Input cố định dưới cùng cột phải và nhấn Enter
**Then** ô chat chuyển sang disabled, hiển thị trạng thái "Chatbot-Thinking" (hiển thị 3 dấu chấm nhấp nháy)
**And** hệ thống gọi API POST `/api/v1/chat` gửi kèm câu hỏi và lịch sử trò chuyện
**Then** Backend chạy đồ thị suy luận LangGraph, truy xuất ngữ cảnh pgvector và stream văn bản trả lời thô (`text/plain`) qua kênh SSE
**And** thời gian phản hồi từ lúc gửi đến lúc bắt đầu stream ký tự đầu tiên <= 3 giây
**Then** Frontend render tin nhắn cập nhật thời gian thực, tự động cuộn xuống dưới cùng

### Story 4.3: Citation Guardrail & Tooltip trích dẫn gốc (FR-8, FR-10, NFR7, UX-DR5)

As a nhà nghiên cứu,
I want tất cả trích dẫn học thuật trong câu trả lời của AI phải được kiểm chứng với nguồn thực tế, và xem được đoạn văn bản gốc làm căn cứ,
So that tôi hoàn toàn tin tưởng vào câu trả lời của AI và loại bỏ được hiện tượng trích dẫn giả mạo.

**Acceptance Criteria:**

**Given** câu trả lời thô của LLM chứa các thẻ trích dẫn dạng `[1]`, `[2]`
**When** qua bước *Citation Verify Node* ở Backend
**Then** hệ thống đối chiếu siêu dữ liệu và ID trích dẫn với cơ sở dữ liệu dự án qua index `(project_id, paper_index)`
**And** nếu phát hiện trích dẫn sai lệch vượt quá tỷ lệ lỗi cấu hình `CITATION_ERROR_THRESHOLD` (mặc định 30%), kích hoạt LLM tự sửa tối đa 2 lần
**And** nếu sửa lỗi thất bại, tự động đổi các thẻ lỗi thành `[Nguồn không xác định]` và trả về cờ cảnh báo độ tin cậy thấp `low_reliability: true`
**When** Frontend nhận được chunk cuối chứa JSON thông tin trích dẫn
**Then** nếu có cờ `low_reliability: true`, hiển thị nhãn Cảnh báo độ tin cậy thấp màu đỏ/cam nhạt nổi bật kèm biểu tượng dấu chấm than ở đầu khung chat
**When** người dùng click hoặc hover vào thẻ trích dẫn `[1]`, `[2]` trong câu trả lời
**Then** một hộp thoại nổi `Citation Tooltip` xuất hiện hiển thị tiêu đề, tác giả, năm của bài viết, đoạn văn bản trích dẫn gốc (text chunk thực tế) và cung cấp nút mở tệp PDF/DOCX gốc trong trình duyệt để đối chiếu

### Story 4.4: Phân tích Khoảng trống qua Chat & Gợi ý định hướng theo trạng thái (FR-7, FR-15, UX-DR12)

As a nhà nghiên cứu,
I want AI Agent đề xuất các hành động tiếp theo dựa trên trạng thái dự án của tôi và trả lời so sánh đối chiếu sâu,
So that tôi biết mình cần làm gì tiếp theo trong dự án một cách tự nhiên.

**Acceptance Criteria:**

**Given** người dùng đang ở giao diện dự án và đang mở khung Chatbot AI bên phải
**When** người dùng hỏi về khoảng trống nghiên cứu hoặc mâu thuẫn học thuật
**Then** AI Agent truy vấn Neo4j và pgvector để làm nổi bật các mối quan hệ trích dẫn và trả về câu trả lời chỉ rõ nguồn trích dẫn đối lập
**Given** dự án mới bắt đầu hoặc khi người dùng yêu cầu hướng dẫn hành động
**When** Frontend tự động gửi thông số giao diện hiện tại (`active_tab`, `document_count`, `has_draft`) đến Backend
**Then** AI Agent trả về câu trả lời định hướng kèm danh mục Quick Reply dưới dạng thẻ nút bấm có thể click (ví dụ: `[Tải tài liệu lên]`, `[Xem bản đồ tri thức]`, `[Gợi ý dàn ý]`) dưới ô nhập chat
**When** người dùng bấm nút gợi ý hành động
**Then** Frontend tự động điều hướng sang tab tương ứng (ví dụ: bấm `[Xem bản đồ tri thức]` chuyển sang tab Bản đồ tri thức)

## Epic 5: Soạn thảo Literature Review & Xuất Bản thảo (Overview Writing & Export)

Triển khai khu vực soạn thảo văn bản trong tab "Hỗ trợ viết tổng quan" với sự trợ giúp viết của AI, quản lý các bản nháp và hỗ trợ xuất tệp ZIP chứa tài liệu Markdown cùng danh mục trích dẫn chuẩn BibTeX. Đồng thời hoàn thiện trang chủ khách vãng lai và bảng giá dịch vụ để người dùng đăng ký trải nghiệm.

### Story 5.1: Giao diện Soạn thảo & Quản lý bản thảo (FR-13, UX-DR12)

As a nhà nghiên cứu ở tab Hỗ trợ viết tổng quan,
I want tạo và quản lý các bản nháp literature review của dự án và soạn thảo trực tiếp trên rich editor,
So that tôi có thể ghi chép và cấu trúc bài nghiên cứu của mình.

**Acceptance Criteria:**

**Given** người dùng chọn Tab 3 "Hỗ trợ viết tổng quan" (Cột giữa)
**Then** hệ thống hiển thị danh sách các bản nháp dưới dạng các Thẻ bản thảo (Manuscript Card) bo góc 6px và nút "+ Tạo bản thảo mới"
**When** người dùng click một bản thảo hoặc nút tạo mới
**Then** mở Khung soạn thảo văn bản (Editor Workspace) sử dụng Lexical/Slate.js, font Inter 13px, line-height 18px trên nền giấy ấm
**When** người dùng chỉnh sửa nội dung văn bản
**Then** hệ thống kích hoạt tự động lưu (autosave) và ghi nhận bản nháp vào PostgreSQL (bảng `manuscripts`)
**And** hiển thị nhãn trạng thái "Đang lưu..." mờ ở góc editor, đổi thành "Đã lưu" khi hoàn tất ghi nhận

### Story 5.2: Trợ lý AI hỗ trợ viết & Xuất bản thảo tệp ZIP (FR-13, FR-14, UX-DR12)

As a nhà nghiên cứu,
I want AI hỗ trợ sửa đổi/viết tiếp văn bản ngay trong editor và xuất báo cáo kèm danh mục trích dẫn ra máy tính,
So that tôi có thể nhanh chóng hoàn thành bản thảo và tải về đầy đủ file tài liệu trích dẫn học thuật.

**Acceptance Criteria:**

**Given** người dùng đang mở một bản thảo trong Khung soạn thảo văn bản (Editor Workspace) ở Tab Hỗ trợ viết tổng quan
**When** người dùng bôi đen một đoạn văn bản trong editor hoặc nhập lệnh AI (ví dụ: "Viết tiếp đoạn này")
**Then** hệ thống gọi API tích hợp AI Agent để chỉnh sửa hoặc viết tiếp văn bản trực tiếp trong vùng soạn thảo
**Given** bản thảo đang có nội dung chứa các trích dẫn tài liệu
**When** người dùng click nút "Xuất báo cáo" (màu xanh Cobalt chữ trắng, bo góc 6px) ở góc phải trên editor
**Then** Backend thực hiện đối chiếu các tài liệu được tham chiếu trong bản thảo, đóng gói thành tệp ZIP và tải xuống máy người dùng
**And** tệp ZIP chứa: tệp văn bản Markdown (`.md`) và tệp danh mục trích dẫn định dạng BibTeX/APA (`.bib`) của toàn bộ các tài liệu được tham chiếu trong bản thảo

### Story 5.3: Trang chủ Khách vãng lai (Guest Landing Page) & Khung giả lập Demo (UX-DR7, UX-DR13)

As an khách vãng lai chưa đăng nhập,
I want xem trang giới thiệu sản phẩm và trải nghiệm một bản demo mô phỏng tương tác của ứng dụng,
So that tôi hiểu giá trị của sản phẩm và quyết định đăng ký tài khoản.

**Acceptance Criteria:**

**Given** người dùng chưa đăng nhập truy cập vào địa chỉ gốc `/` của hệ thống
**Then** hệ thống hiển thị trang Landing Page gồm: Hero Banner giới thiệu tính năng, nút CTA hướng đến trang đăng ký/đăng nhập
**And** hiển thị Interactive Demo Simulator (khung giả lập 3 cột thu nhỏ hoạt động độc lập với dữ liệu giả định, có dải băng cảnh báo màu vàng "BẢN CHẠY THỬ / GIẢ LẬP" và sơ đồ Cytoscape demo có 1 node đỏ nhấp nháy gap alert tỏa bóng)
**And** hiển thị Bảng giá dịch vụ (Pricing Table) so sánh tính năng gói Sinh viên (Free) và gói Nghiên cứu viên (Pro) có viền xanh Cobalt nổi bật và nhãn "PHỔ BIẾN NHẤT" trên gói Pro
