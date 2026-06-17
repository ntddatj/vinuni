---
title: AI Literature Review Assistant (AI20K-031)
status: final
created: 2026-06-11
updated: 2026-06-12
---

# PRD: AI Literature Review Assistant (AI20K-031)

## 0. Document Purpose
Tài liệu PRD này định nghĩa các yêu cầu sản phẩm cho hệ thống **AI Trợ Lý Tổng Quan Tài Liệu & Phát Hiện Khoảng Trống Nghiên Cứu** (Mã đề: AI20K-031). Tài liệu này làm cơ sở cho các bước thiết kế kiến trúc kỹ thuật (Architecture Design), phân rã công việc (Epics & Stories) và triển khai phát triển tiếp theo. Tài liệu được cấu trúc với các thuật ngữ nhất quán trong phần Thuật ngữ (Glossary), các tính năng nghiệp vụ cụ thể kèm các yêu cầu chức năng (FR) chi tiết, và các giả định được gắn thẻ trực tiếp.

## 1. Vision
Hệ thống **AI Literature Review Assistant** giúp các nhà nghiên cứu khoa học, học viên thạc sĩ và sinh viên thực hiện nghiên cứu khoa học tự động hóa quy trình tìm kiếm, tổng hợp và đánh giá tài liệu từ các nguồn học thuật uy tín (như arXiv và Semantic Scholar) kết hợp với các tài liệu nghiên cứu cá nhân tự tải lên (tệp PDF, DOCX). Thông qua cơ chế tìm kiếm đa nguồn, nạp và phân tích tài liệu PDF/DOCX, phân tích đồ thị tri thức và suy luận đa bước của AI Agent (xây dựng trên LangGraph), hệ thống sẽ giúp người dùng nhanh chóng phát hiện các khoảng trống nghiên cứu (research gaps), các mâu thuẫn học thuật, đồng thời hỗ trợ soạn thảo văn bản tổng quan tài liệu có trích dẫn chính xác, chống hiện tượng ảo ảnh thông tin (hallucination).

### 1.1 Triết lý Thiết kế Hệ thống (Design Philosophy)
Hệ thống được phát triển và vận hành dựa trên 2 trụ cột thiết kế cốt lõi:
* **Dự án (Workspace) làm trung tâm:** Mọi trải nghiệm và ngữ cảnh làm việc của người dùng (từ tài liệu, bản đồ tri thức đến lịch sử chat) đều được cô lập và quản lý nhất quán theo từng Dự án nghiên cứu cụ thể. Người dùng được định hướng tạo dự án ngay từ bước Onboarding để thiết lập không gian cách ly dữ liệu và ngữ cảnh RAG.
* **Chatbot AI là người bạn đồng hành tích hợp (AI Workspace Companion):** Khung chatbot ở cột phải đóng vai trò trợ lý đồng hành chủ động, nhận diện trạng thái dự án để định hướng và cung cấp các nút tương tác nhanh (Quick Reply Buttons). Đồng thời, hệ thống duy trì cơ chế **Định tuyến thao tác song song (Co-existent Redundant Pathways)**: người dùng luôn có thể thực hiện mọi tác vụ cốt lõi qua giao diện đồ họa (GUI) ở trung tâm hoặc ra lệnh tự nhiên qua chatbot, với trạng thái của hai con đường này được đồng bộ hóa tức thời để đảm bảo trải nghiệm liền mạch.


## 2. Target User

### 2.1 Jobs To Be Done
- **Tìm kiếm & Chọn lọc**: Người dùng (nhà nghiên cứu, học viên, sinh viên) cần tìm kiếm nhanh chóng và chính xác các bài báo liên quan đến chủ đề nghiên cứu từ nhiều nguồn học thuật, kết hợp với các tài liệu nghiên cứu cá nhân tự tải lên (PDF, DOCX) mà không mất hàng tuần để tìm và lọc thủ công.
- **Tổng hợp & Phân nhóm**: Người dùng cần tóm tắt và phân nhóm các bài viết theo phương pháp, hướng tiếp cận và kết quả để có cái nhìn tổng quan.
- **Trực quan hóa Bản đồ Tri thức**: Người dùng cần một cái nhìn tổng cảnh trực quan về mạng lưới liên kết trích dẫn và tác giả giữa các bài báo (bài viết nào trích dẫn bài viết nào, các cụm nghiên cứu liên quan...) để dễ dàng theo dõi dòng chảy phát triển của chủ đề nghiên cứu mà không phải tự ghi chép hoặc vẽ tay.
- **Phát hiện Khoảng trống & Mâu thuẫn**: Người dùng cần phát hiện những điểm hạn chế chưa được giải quyết hoặc sự mâu thuẫn thực nghiệm giữa các nghiên cứu đi trước để định vị đóng góp mới của mình.
- **Soạn thảo & Trích dẫn**: Người dùng cần hỗ trợ soạn thảo văn bản Literature Review có trích dẫn nguồn thực tế chính xác (tránh trích dẫn ảo).

### 2.2 Non-Users (v1)
- Học sinh phổ thông tìm kiếm thông tin bài viết phổ thông hoặc phi học thuật.
- Người dùng cần dịch thuật tài liệu đơn thuần không có nhu cầu phân tích học thuật chuyên sâu.

### 2.3 Key User Journeys
Các User Journeys dưới đây xoay quanh các tác vụ cốt lõi trong một dự án nghiên cứu cụ thể của người dùng.

- **UJ-1: Thư viện tài liệu (Document Library)**
  - **Persona + context:** Minh, học viên cao học ngành Khoa học Máy tính, đang chuẩn bị viết đề cương nghiên cứu về "Tối ưu hóa RAG".
  - **Entry state:** Đã đăng nhập và đang ở giao diện Tab "Thư viện tài liệu" của dự án mới "RAG Optimization".
  - **Path:** Minh tiến hành nạp tài liệu cho dự án bằng 2 cách:
    1. Nhập từ khóa "RAG vector retrieval optimization" để hệ thống truy vấn qua API arXiv & Semantic Scholar, sau đó click chọn 5 bài báo nổi bật.
    2. Kéo thả trực tiếp từ máy tính 2 tệp PDF có phí đã tải về trước đó và 1 tệp nháp nghiên cứu cá nhân (.docx).
  - **Climax:** Hệ thống tự động nạp ngầm: tải PDF Open Access, phân tích cấu trúc tệp tự upload, tạo vector embeddings vào Vector Store và ánh xạ quan hệ vào Graph Database.
  - **Resolution:** Minh thấy danh sách tài liệu trong không gian dự án cập nhật trạng thái sang "Đã nạp" thành công.
  - **Edge case:** Nếu tệp upload bị lỗi định dạng hoặc PDF scan không có lớp text, hệ thống chạy OCR tự động và hiển thị tiến trình/cảnh báo chi tiết trên giao diện thư viện.

- **UJ-2: Bản đồ tri thức (Knowledge Map) & Phát hiện khoảng trống**
  - **Persona + context:** Minh muốn tìm hiểu, hình dung trực quan mạng lưới liên kết học thuật giữa các tài liệu đã nạp trong dự án và phát hiện các khoảng trống nghiên cứu.
  - **Entry state:** Đang ở giao diện dự án "RAG Optimization", Minh chuyển từ Tab "Thư viện tài liệu" sang Tab "Bản đồ tri thức".
  - **Path:** Minh xem sơ đồ mạng lưới trích dẫn tương tác. Anh thực hiện thu phóng, di chuyển các nút bài viết và xem chi tiết thông tin bài báo (tác giả, năm, tóm tắt) bằng cách click vào nút tương ứng. Anh kích hoạt chế độ "Tìm khoảng trống nghiên cứu" trên sơ đồ.
  - **Climax:** Đồ thị tự động làm nổi bật các mối quan hệ trích dẫn và các cụm nghiên cứu. Hệ thống trực quan hóa và chỉ ra các vùng nghi ngờ chứa khoảng trống tri thức hoặc các bài viết có nhận định mâu thuẫn thực nghiệm.
  - **Resolution:** Minh có được cái nhìn tổng quan trực quan về mạng lưới nghiên cứu, phát hiện nhanh các khoảng trống và mâu thuẫn học thuật ngay trên sơ đồ mà không cần đọc thủ công từng bài viết.

- **UJ-3: Hỗ trợ viết tổng quan (Overview Writing Support)**
  - **Persona + context:** Minh cần soạn thảo một đoạn literature review ngắn có trích dẫn nguồn thực tế chính xác và xuất báo cáo.
  - **Entry state:** Đang ở giao diện Tab "Hỗ trợ viết tổng quan".
  - **Path:** Minh yêu cầu chatbot soạn thảo literature review hoặc sử dụng công cụ soạn thảo trực tiếp. Anh kiểm tra các nguồn trích dẫn được đánh số bằng cách di chuột hoặc click vào để xem nhanh đoạn trích gốc từ tài liệu gốc.
  - **Climax:** Hệ thống tự động đối chiếu và xác thực các trích dẫn học thuật với cơ sở dữ liệu tài liệu thực tế trong dự án để loại bỏ trích dẫn sai lệch.
  - **Resolution:** Minh thấy các trích dẫn chính xác, anh bấm nút xuất báo cáo. Hệ thống tải xuống tệp ZIP chứa file báo cáo tổng hợp Markdown (`.md`) và file trích dẫn chuẩn hóa BibTeX/APA (`.bib`).

## 3. Glossary
- **Dự án Nghiên cứu (Research Project/Workspace)** — Không gian làm việc chứa các bài báo, tài liệu và lịch sử chat của một chủ đề nghiên cứu cụ thể.
- **Tài liệu dự án (Project Document/Asset)** — Các tài liệu được đưa vào dự án nghiên cứu, bao gồm bài báo khoa học tải về từ API (PDF) hoặc tệp cá nhân do người dùng tải lên (PDF, DOCX).
- **Bài báo (Paper)** — Tài liệu khoa học có siêu dữ liệu (Metadata) rõ ràng bao gồm Tiêu đề, Tác giả, Năm xuất bản, Tóm tắt, DOI, link PDF và số lượng trích dẫn.
- **Bản đồ Tri thức (Knowledge Map)** — Đồ thị mạng lưới trực quan hiển thị mối quan hệ trích dẫn `[:CITES]` giữa các bài báo và mối quan hệ tác giả `[:AUTHORED]`.
- **Hệ thống RAG (Retrieval-Augmented Generation)** — Cơ chế truy xuất thông tin từ các đoạn văn bản (chunks) được nhúng vector để cung cấp ngữ cảnh cho mô hình ngôn ngữ lớn (LLM).
- **Citation Guardrail (Bộ lọc kiểm định trích dẫn)** — Quy trình kiểm tra tự động đối chiếu các trích dẫn học thuật được sinh ra bởi LLM với cơ sở dữ liệu bài báo thực tế trong dự án nhằm phát hiện và lọc bỏ các trích dẫn giả mạo (hallucinated citations) dựa trên ngưỡng lỗi cấu hình.
- **Quản trị viên (Admin)** — Vai trò của tài khoản đầu tiên được đăng ký trong hệ thống, có đặc quyền truy cập trang cài đặt hệ thống để cấu hình các tham số động của ứng dụng và quản trị người dùng.
- **Tham số hệ thống (System Settings/Configuration)** — Các thiết lập giới hạn kỹ thuật (ví dụ: giới hạn số tài liệu tối đa mỗi dự án, ngưỡng kích hoạt gợi ý MECE, tỷ lệ trích dẫn ảo cho phép, số lần thử lại của AI) được lưu trữ động trong Database và hiển thị trên giao diện của Admin.

## 4. Features

### 4.1 Quản lý Người dùng & Dự án (User & Project Management)
**Description:** Hệ thống quản lý tài khoản nghiên cứu viên và cho phép họ tổ chức công việc theo từng dự án nghiên cứu độc lập.

**Functional Requirements:**
- **FR-1: Đăng ký, Đăng nhập & Phân quyền Admin khởi tạo**
  - Người dùng có thể đăng ký tài khoản bằng email, mật khẩu và đăng nhập vào hệ thống.
  - **Cơ chế phân quyền Admin:** Tài khoản đầu tiên được tạo trong hệ thống sẽ tự động được gán quyền Admin (`role = 'admin'`). Các tài khoản tiếp theo sẽ là tài khoản người dùng thông thường (`role = 'user'`). Tài khoản Admin sẽ có thêm quyền truy cập trang Cài đặt Hệ thống có chứa các tab cấu hình động.
  - *Consequences*: Hệ thống cấp mã JWT lưu trữ an toàn trong HttpOnly Cookie. Nếu sai thông tin đăng nhập, hệ thống trả về mã lỗi HTTP 401.
- **FR-2: Quản lý Dự án Nghiên cứu**
  - Người dùng có thể Tạo, Đọc, Cập nhật, Xóa (CRUD) các Dự án. Mỗi dự án có tên và mô tả chủ đề.
  - **Quy trình hoạt động lấy Dự án làm trung tâm:**
    - Người dùng mới bắt buộc phải tạo dự án đầu tiên (Onboarding gating) trước khi sử dụng các chức năng phân tích hoặc nạp tài liệu.
    - Thanh điều hướng bên trái (Sidebar) chỉ hiển thị danh sách tối đa 10 dự án được sử dụng gần nhất, kèm một nút "Xem tất cả" để chuyển hướng đến trang Quản lý toàn bộ dự án tập trung nhằm tránh quá tải giao diện.
    - Trạng thái các tài liệu và luồng chat được phân tách hoàn toàn theo dự án qua `project_id`. Mọi thao tác trên đồ thị hoặc thư viện ở cột giữa đều được đồng bộ hóa tức thời với Chatbot đồng hành ở cột phải bằng cơ chế quản lý trạng thái phía client (Client-side State Management).
    - **Ánh xạ 1-1 với Thanh tab ngang:** Để duy trì sự nhất quán, các Tab chức năng ở cột giữa (Thư viện tài liệu, Bản đồ tri thức, Hỗ trợ viết tổng quan) phản ánh trực tiếp các User Journeys chính của dự án.

### 4.2 Tìm kiếm Học thuật & Nạp tài liệu (Academic Search & Ingest)
**Description:** Tra cứu bài báo từ các nguồn học thuật và nạp nội dung PDF vào cơ sở dữ liệu để chuẩn bị cho phân tích RAG và đồ thị.

**Functional Requirements:**
- **FR-3: Tìm kiếm bài báo đa nguồn (Tính năng con thuộc Tab Thư viện tài liệu)**
  - Người dùng thực hiện tìm kiếm bài báo trực tiếp từ ô tìm kiếm trong Tab Thư viện tài liệu hoặc thông qua câu lệnh chat với AI Agent.
  - **Cơ chế tìm kiếm và Xử lý lỗi API (Degraded Union):**
    - Hệ thống gọi song song API của arXiv và Semantic Scholar với thời hạn Timeout tối đa là 10 giây. Nếu một trong hai API bị lỗi hoặc quá hạn (Rate limit/Timeout), hệ thống vẫn trả về danh sách kết quả của API thành công còn lại kèm theo một cờ cảnh báo nguồn lỗi. Frontend sẽ hiển thị thông báo Toast cảnh báo nhẹ cho người dùng biết dữ liệu từ nguồn đó tạm thời không khả dụng, tránh crash giao diện.
    - Hệ thống khử trùng lặp (deduplication) dựa trên mã **DOI** hoặc đối khớp Tiêu đề, sau đó lưu tạm siêu dữ liệu và tóm tắt của các bài viết được người dùng thêm vào dự án vào PostgreSQL cục bộ.
  - *Consequences*: 
    - **Xử lý chủ đề quá rộng (Broad Query Handling):** Khi số lượng kết quả trả về từ API vượt quá ngưỡng cấu hình `BROAD_QUERY_THRESHOLD` (Admin cấu hình, mặc định là 50), hệ thống sẽ gọi LLM phân tích từ khóa chính để tự động sinh ra **danh sách các gợi ý phân ngành (sub-fields) mang tính bao phủ toàn bộ phạm vi (exhaustive/MECE)** dưới dạng các **thẻ nút bấm có thể click trực tiếp (interactive buttons)**. Khi click, hệ thống tự động chạy một truy vấn tìm kiếm mới.
    - Trả về danh sách bài báo gồm: tiêu đề, tác giả, năm xuất bản, tóm tắt, số trích dẫn, DOI, link PDF gốc (nếu có) kèm tổng số lượng kết quả tìm thấy.
- **FR-4: Ingestion bất đồng bộ & Hiển thị tiến trình chi tiết**
  - Khi người dùng chọn thêm một bài báo vào dự án hoặc tải lên tệp:
    - Hệ thống luôn lưu trữ siêu dữ liệu và tóm tắt (nếu có) vào PostgreSQL để hiển thị trong dự án và dựng Bản đồ Tri thức.
    - Kích hoạt tác vụ bất đồng bộ (FastAPI `BackgroundTasks`) để tải PDF ngầm (đối với Open Access), thực hiện OCR (nếu là PDF scan), cắt đoạn văn bản (chunking) và nhúng vector.
  - *Consequences*: 
    - Bỏ giới hạn thời gian nạp 30 giây cứng nhắc. Thay vào đó, hệ thống sử dụng Server-Sent Events (SSE) để đẩy trạng thái tiến trình xử lý chi tiết lên Frontend.
    - Người dùng có thể theo dõi tiến trình trực quan trên giao diện: *"Đang tải từ internet..."* -> *"Đang quét cấu trúc & OCR..."* (nếu là PDF scan) -> *"Đang nhúng vector..."* -> *"Đã nạp thành công"*.
    - Đối với tài liệu Open Access tải tự động, hệ thống LƯU TRỮ tệp PDF đã tải vào kho lưu trữ bảo mật phía server (`paper.file_path`) để phục vụ xem/tải lại sau này mà KHÔNG cần gọi lại API arXiv/Semantic Scholar. Tệp gốc được phục vụ qua endpoint bảo mật (xác thực JWT + quyền dự án, theo pattern Secure Media Access ARCH-9). Link có phí (paywalled/không tải được) giữ nguyên liên kết ngoài kèm nhãn *"nguồn cần trả phí"* (nhất quán Non-Goals — không tích hợp Sci-Hub).
- **FR-5: Upload tài liệu thủ công & Trích xuất Metadata tự động**
  - Người dùng có thể tự upload tệp PDF/DOCX của riêng họ lên dự án.
  - **Quy trình xử lý tệp tải lên (PDF/DOCX):** Khi tệp được tải lên, Backend sẽ đưa nội dung thô lên LLM để tự động đọc hiểu và trích xuất các siêu dữ liệu (Tiêu đề, Tác giả, Năm, Tóm tắt). Sau đó, Frontend hiển thị một Form điền siêu dữ liệu với các trường do AI tự trích xuất có gắn nhãn *"AI Suggested"*. Người dùng có thể trực tiếp sửa đổi, điền thêm các thông tin còn thiếu và bấm nút *"Xác nhận"* để chính thức nạp tài liệu vào dự án và chạy nhúng vector.
- **FR-16: Quản lý vòng đời Tài liệu trong Dự án (Document Lifecycle Management)**
  - Người dùng có thể Xóa một tài liệu khỏi dự án và Chỉnh sửa siêu dữ liệu (Tiêu đề, Tác giả, Năm, Tóm tắt) của một tài liệu ĐÃ được nạp.
  - *Consequences*:
    - Xóa tài liệu dùng cơ chế xóa mềm (`is_deleted`), ghi sự kiện vào `sync_outbox` để đồng bộ gỡ node khỏi Neo4j (theo ARCH-2 GC), cascade xóa các chunk vector, và GIẢI PHÓNG 1 suất trong giới hạn `MAX_PAPERS_PER_PROJECT` (FR-11).
    - Chỉnh sửa metadata chỉ cập nhật thông tin hiển thị/đồ thị, KHÔNG nhúng lại vector.
    - Mọi thao tác kiểm tra quyền sở hữu dự án (owner scoping) chống truy cập trái phép.

### 4.3 Phân tích với AI Agent & Phát hiện Khoảng trống (Agentic Analysis & Gap Detection)
**Description:** AI Agent sử dụng LangGraph để trả lời câu hỏi của người dùng dựa trên tài liệu trong dự án, phát hiện các khoảng trống nghiên cứu và mâu thuẫn.

**Functional Requirements:**
- **FR-6: Chat tương tác thời gian thực với AI Agent**
  - Người dùng có thể gửi tin nhắn chat trong dự án để hỏi về nội dung các bài báo đã nạp.
  - *Consequences*: 
    - AI Agent sử dụng RAG kết hợp với Graph Database (Neo4j) để truy xuất thông tin chính xác và stream câu trả lời (SSE) về giao diện.
    - **Cấu trúc nút lịch sử chat và ô chat:** Khung chatbot ở cột phải chứa ô nhập chat (Chat Input) nằm cố định ở dưới cùng. Thay vì dùng tab nhỏ gây tốn diện tích, lịch sử trò chuyện được hiển thị thông qua một nút bấm (biểu tượng lịch sử trò chuyện) nằm ngay dưới tiêu đề "Trợ lý nghiên cứu" và ở trên vùng hiển thị chat. Khi người dùng bấm vào nút này, một danh sách các phiên trò chuyện cũ trong dự án hiện tại sẽ hiển thị dưới dạng popover/drawer để người dùng lựa chọn chuyển đổi.
- **FR-7: Phát hiện Khoảng trống & Mâu thuẫn nghiên cứu**
  - AI Agent cung cấp tính năng phân tích so sánh chéo, chỉ ra các mâu thuẫn thực nghiệm hoặc các điểm hạn chế chưa giải quyết giữa các bài báo trong dự án.
  - *Consequences*: Câu trả lời phải chỉ rõ nguồn của từng nhận định so sánh (ví dụ: "Phương pháp của bài báo [1] đạt độ chính xác 90% nhưng độ trễ cao, mâu thuẫn với nhận định tối ưu hóa của bài báo [2]").
- **FR-15: Hỗ trợ định hướng người dùng theo trạng thái dự án (Context-Aware User Guiding)**
  - Hệ thống cho phép AI Chatbot tự động cảm nhận trạng thái hiện tại của dự án để chủ động hướng dẫn và đề xuất hành động tiếp theo cho người dùng (đặc biệt là người dùng mới).
  - *Consequences*:
    - **Tóm tắt Trạng thái Dự án (Project State Snapshot):** Khi người dùng đặt câu hỏi gợi ý hành động (như "Tôi cần làm gì tiếp theo?") hoặc dự án mới tạo hoàn toàn trống, Frontend sẽ gửi kèm các thông số trạng thái gọn nhẹ gồm: tab hiện tại (`active_tab`), số lượng tài liệu (`document_count`), và trạng thái bản thảo (`has_draft`).
    - **Nút hành động động (Dynamic Quick Reply Buttons):** AI Agent sẽ trả về câu trả lời định hướng kèm một danh mục hành động gợi ý dưới dạng các thẻ nút bấm có thể click (ví dụ: `[Tải tài liệu lên]`, `[Xem bản đồ tri thức]`, `[Gợi ý dàn ý]`). Khi người dùng bấm vào các nút gợi ý này, Frontend sẽ tự động điều hướng sang tab chức năng tương ứng mà không bắt người dùng tự thực hiện thủ công.

### 4.4 Citation Guardrail (Bộ lọc chống trích dẫn ảo)
**Description:** Đảm bảo tất cả các trích dẫn học thuật trong câu trả lời hoặc bản thảo do AI sinh ra đều là có thật và tương ứng với tài liệu thực tế trong dự án.

**Functional Requirements:**
- **FR-8: Kiểm chứng và xử lý lỗi trích dẫn ảo**
  - Trước khi trả kết quả cho người dùng, hệ thống chạy một *Citation Verify Node* để quét tất cả các thẻ trích dẫn thô (dạng `[1]`, `[2]`, `[ID]`) và đối chiếu với cơ sở dữ liệu thực tế của dự án.
  - **Luồng xử lý lỗi và Cấu hình Admin:**
    - Tính toán tỷ lệ lỗi trích dẫn = (Số trích dẫn không khớp / Tổng số trích dẫn).
    - Nếu tỷ lệ lỗi $\le$ `CITATION_ERROR_THRESHOLD` (do Admin cấu hình, mặc định 30%): Hệ thống tự động lọc bỏ thẻ trích dẫn lỗi hoặc thay bằng thẻ `[Nguồn không xác định]` và trả kết quả cho người dùng.
    - Nếu tỷ lệ lỗi > `CITATION_ERROR_THRESHOLD`: Hệ thống kích hoạt quy trình tự sửa của LLM với số lần thử lại tối đa là `CITATION_RETRY_LIMIT` (do Admin cấu hình, mặc định 2 lần). Nếu sau khi thử lại mà tỷ lệ lỗi vẫn vượt ngưỡng, hệ thống trả về kết quả kèm nhãn cảnh báo độ tin cậy thấp nổi bật ở đầu câu trả lời.
- **FR-10: Tương tác với Thẻ trích dẫn (Citation Interaction)**
  - Người dùng có thể nhấp (click) hoặc di chuột (hover) vào các ký hiệu trích dẫn (ví dụ: `[1]`, `[2]`) trong câu trả lời của AI hoặc trong bản thảo literature review.
  - *Consequences*: 
    - Hệ thống hiển thị giao diện xem nhanh (tooltip/popup hoặc sidebar) chứa thông tin siêu dữ liệu bài báo (Tiêu đề, Tác giả, Năm, DOI) và **đoạn văn bản gốc đã được render** (text chunk thực tế trong database) dùng làm căn cứ trích dẫn.
    - Cung cấp nút liên kết để tải xuống tệp gốc (PDF/DOCX) hoặc mở tệp gốc trực tiếp trên trình duyệt để đối chiếu.

### 4.5 Bản đồ Tri thức tương tác (Interactive Knowledge Map UI)
**Description:** Hiển thị mạng lưới trích dẫn giữa các tài liệu giúp người dùng có góc nhìn trực quan về mối liên kết học thuật qua đồ thị trực quan dựng trên Neo4j.

**Functional Requirements:**
- **FR-9: Trực quan hóa mạng lưới bài báo & Phát hiện khoảng trống trực quan**
  - Người dùng có thể xem một bản đồ mạng lưới tương tác hiển thị các bài báo dưới dạng các đỉnh (nodes) và quan hệ trích dẫn dưới dạng các cạnh (edges) kết nối.
  - **Tích hợp phát hiện khoảng trống nghiên cứu (Gap Detection Integration):**
    - Hệ thống truy vấn quan hệ từ Neo4j để vẽ đồ thị bằng Cytoscape.js. Khi bật chế độ "Tìm khoảng trống nghiên cứu", hệ thống sẽ phân tích cấu trúc đồ thị trích dẫn (ví dụ: các cụm node bị cô lập, thiếu liên kết trích dẫn) kết hợp với nội dung RAG để tự động đánh dấu (highlight/đổi màu sắc) các vùng nghi vấn chứa khoảng trống tri thức hoặc mâu thuẫn thực nghiệm.
  - *Consequences*: Cho phép thu phóng (zoom), kéo thả và click vào từng nút bài báo để xem nhanh siêu dữ liệu (metadata) tương ứng, và xem các cảnh báo khoảng trống được đính kèm trực tiếp tại các vùng/cạnh trên bản đồ.

### 4.6 Hỗ trợ viết tổng quan tài liệu (Overview Writing Support)
**Description:** Cung cấp công cụ và tính năng hỗ trợ người dùng soạn thảo literature review từ các tài liệu trong dự án, đồng thời quản lý bản thảo và xuất kết quả nghiên cứu.

**Functional Requirements:**
- **FR-13: Soạn thảo & Quản lý bản thảo tổng quan (Literature Review Drafting & Management)**
  - Người dùng có thể soạn thảo trực tiếp hoặc yêu cầu AI Agent hỗ trợ viết các đoạn tổng quan tài liệu. Các bản thảo được lưu trữ theo từng dự án.
  - *Consequences*: Người dùng có thể chỉnh sửa, lưu nháp nhiều phiên bản của bản thảo. AI Agent hỗ trợ đề xuất câu chữ, định dạng văn bản trực tiếp trong vùng soạn thảo.
- **FR-14: Xuất bản thảo và tài liệu trích dẫn (Exporting Manuscript & Citations)**
  - Người dùng có thể xuất bản thảo và toàn bộ danh mục tài liệu trích dẫn ra máy tính cá nhân.
  - *Consequences*: Hệ thống đóng gói kết quả xuất dưới dạng tệp nén ZIP chứa file văn bản Markdown (`.md`) và file trích dẫn chuẩn hóa định dạng BibTeX/APA (`.bib`) của toàn bộ các tài liệu được tham chiếu.

### 4.7 Cấu hình Hệ thống (System Configuration)
**Description:** Cho phép người quản trị (Admin) cấu hình và tùy chỉnh các giới hạn kỹ thuật để phù hợp với năng lực xử lý của mô hình LLM và tối ưu chi phí API.

**Functional Requirements:**
- **FR-11: Cấu hình giới hạn tài liệu trong dự án (Document Limit Configuration)**
  - Người dùng có vai trò Quản trị viên (Admin) có thể thiết lập giới hạn cứng số lượng tài liệu tối đa được phép nạp trong một dự án (`MAX_PAPERS_PER_PROJECT`).
  - *Consequences*: 
    - Giới hạn mặc định là 15 tài liệu. Khi dự án đạt giới hạn này, người dùng thông thường không thể thêm tài liệu mới; hệ thống hiển thị thông báo lỗi cứng trên UI và chặn các hành động tải lên/nạp tiếp theo.
- **FR-12: Lưu trữ cấu hình động**
  - Các tham số cấu hình hệ thống (như số tài liệu tối đa, kích thước file upload tối đa) phải được lưu trữ trong Database (hoặc file cấu hình hệ thống động) để Admin có thể thay đổi thông qua API/UI mà không cần restart server hay deploy lại code.

## 5. Non-Goals (Explicit)
- Hệ thống không tự động bẻ khóa các trang tải bài báo có phí (không tích hợp Sci-Hub). Chỉ hỗ trợ tự động tải các tài liệu Open Access (arXiv, Semantic Scholar Open Access). Các tài liệu có phí yêu cầu người dùng upload thủ công.
- Hệ thống không thay thế hoàn toàn nhà nghiên cứu viết bài báo khoa học từ đầu đến cuối mà chỉ đóng vai trò hỗ trợ soạn thảo và tổng hợp thông tin.

## 6. MVP Scope

### 6.1 In Scope
Tất cả các tính năng và yêu cầu chức năng (FR-1 đến FR-15) được mô tả trong phần [4. Features](file:///home/agent/github/C2-App-053/_bmad-output/planning-artifacts/prds/prd-C2-App-053-2026-06-11/prd.md#L72) đều nằm trong phạm vi phát triển của phiên bản MVP. Cụ thể bao gồm:
- **Quản lý người dùng & dự án** (Đăng nhập/Đăng ký, Phân quyền Admin, CRUD dự án).
- **Thư viện tài liệu** (Tìm kiếm API arXiv/Semantic Scholar, Tải tài liệu tự động/Thủ công, Trích xuất siêu dữ liệu tự động cho tệp upload PDF/DOCX).
- **Phân tích với AI Agent** (Chat RAG qua Neo4j/pgvector, Hướng dẫn tương tác chủ động, Phát hiện khoảng trống/mâu thuẫn).
- **Citation Guardrail** (Bộ kiểm tra và sửa lỗi trích dẫn ảo, Giao diện tương tác thẻ trích dẫn).
- **Bản đồ tri thức** (Vẽ đồ thị liên kết trích dẫn và tích hợp phân tích khoảng trống).
- **Hỗ trợ viết tổng quan** (Soạn thảo văn bản, quản lý bản thảo và xuất tệp ZIP gồm Markdown & BibTeX).
- **Cấu hình hệ thống** (Cấu hình giới hạn động của Admin được lưu trữ trong DB).

### 6.2 Out of Scope for MVP
- Tính năng chia sẻ dự án giữa nhiều người dùng và cộng tác thời gian thực (real-time collaboration).
- Tích hợp thêm các thư viện tìm kiếm học thuật có phí khác như IEEE Xplore, Scopus (sẽ xem xét ở v2).
- Tự động gợi ý bài báo mới hàng tuần dựa trên hồ sơ người dùng.

## 7. Success Metrics

**Primary**
- **SM-1: Tỷ lệ trích dẫn chính xác (Citation Accuracy)**: 100% trích dẫn xuất hiện trong bản thảo được sinh ra bởi Agent phải khớp chính xác với DOI và siêu dữ liệu thực tế của các bài báo có sẵn trong dự án. Validates FR-8.
- **SM-2: Tính khả dụng của tiến trình (Ingestion Progress Availability)**: 100% tệp nạp bất đồng bộ phải hiển thị đúng trạng thái tiến trình (đang tải, đang OCR, đang nhúng, đã nạp) thông qua SSE mà không bị mất kết nối.

**Secondary**
- **SM-3: Độ trễ phản hồi của Agent (First Chunk Latency)**: Thời gian từ khi gửi tin nhắn chat đến khi nhận được ký tự đầu tiên dạng stream (SSE) không quá 3 giây. Validates FR-6.

**Counter-metrics (không tối ưu hóa bằng mọi giá)**
- **SM-C1: Số lượng bài báo nạp vào dự án**: Việc tối ưu hóa số lượng bài báo không được làm giảm hiệu năng truy xuất RAG hoặc tăng tỷ lệ trích dẫn sai lệch (hallucination).

## 8. Non-Functional Requirements (NFR) cho MVP
Hệ thống được thiết kế để triển khai chạy ổn định trên cấu hình tối thiểu là máy ảo **Xubuntu 6 vcores, 32GB RAM**:
- **Concurrency**: Đảm bảo phục vụ tối đa 10 người dùng hoạt động đồng thời (active sessions) mà không gây treo hệ thống.
- **Storage Limit**: Dung lượng tải lên tối đa là 20MB cho mỗi tệp tài liệu cá nhân (PDF/DOCX).
- **Database Performance**: pgvector sử dụng chỉ mục B-Tree trên trường `project_id` kết hợp với chỉ mục HNSW trên trường `embedding` để đảm bảo thời gian truy vấn RAG dưới 500ms khi quy mô cơ sở dữ liệu dưới 100,000 dòng vector.
- **Background Processing**: Sử dụng FastAPI `BackgroundTasks` để tải tệp và chạy OCR bất đồng bộ, giải phóng thread chính của Server để phục vụ các request thông thường.

## 9. Open Questions & Assumptions
- **Giới hạn API Semantic Scholar (Semantic Scholar API Limit):** 
  - *Câu hỏi:* Có cần đăng ký tài khoản Semantic Scholar API để lấy API Key nâng hạn mức hay không, hay chỉ sử dụng public API endpoint với giới hạn rate limit thấp?
  - *Giả định/Hướng xử lý [ASSUMPTION-1]:* Giai đoạn MVP sẽ sử dụng public API endpoint của Semantic Scholar và arXiv, đồng thời hỗ trợ cấu hình truyền API Key cá nhân qua biến môi trường (`.env`) nếu người dùng cần nâng hạn mức.
