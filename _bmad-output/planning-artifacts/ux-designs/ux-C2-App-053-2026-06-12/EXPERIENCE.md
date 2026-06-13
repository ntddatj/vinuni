---
name: AcademicPaper
status: final
sources:
  - file:///home/agent/github/C2-App-053/_bmad-output/planning-artifacts/prds/prd-C2-App-053-2026-06-11/prd.md
updated: 2026-06-13
---

# AcademicPaper — Trải nghiệm Người dùng (EXPERIENCE.md)

Tài liệu này đặc tả cấu trúc tương tác, luồng hành vi, các trạng thái giao diện và các tình huống người dùng (User Journeys) của ứng dụng **AI Literature Review Assistant**, tuân thủ định hướng giao diện sáng mặc định (Light Mode-first) và cấu trúc bố cục ba cột linh hoạt.

* **Tham chiếu trực quan:** 
  - Giao diện làm việc chính (Chat & Sơ đồ): [mockups/academic_paper_dashboard.png](file:///home/agent/github/C2-App-053/_bmad-output/planning-artifacts/ux-designs/ux-C2-App-053-2026-06-12/mockups/academic_paper_dashboard.png)
  - Giao diện Thư viện Tài liệu: [mockups/document_library_view.png](file:///home/agent/github/C2-App-053/_bmad-output/planning-artifacts/ux-designs/ux-C2-App-053-2026-06-12/mockups/document_library_view.png)
  - Quy chuẩn trải nghiệm dạng chữ luôn được ưu tiên áp dụng so với hình ảnh minh họa trong trường hợp có mâu thuẫn.

---

## Foundation

* **Hệ thống thiết kế tham chiếu:** Đồng bộ hoàn toàn với các token thị giác của hệ thống `AcademicPaper` trong [DESIGN.md](file:///home/agent/github/C2-App-053/_bmad-output/planning-artifacts/ux-designs/ux-C2-App-053-2026-06-12/DESIGN.md).
* **Môi trường:** Desktop Web-first (Giao diện web trên máy tính để bàn làm trọng tâm tối ưu hóa cấu trúc 3 cột).
* **Định hướng ngôn ngữ & Bản địa hóa:** Giao diện mặc định hiển thị bằng tiếng Việt (`Vietnamese`). Bộ lọc chuyển đổi ngôn ngữ ở thanh Header cho phép chuyển đổi toàn bộ giao diện nhãn (labels), tiêu đề cột, và thông báo hệ thống sang tiếng Anh (`English`).
* **Chế độ hiển thị:** Chế độ sáng (Light Mode) là mặc định. Người dùng có thể nhấn nút biểu tượng mặt trăng trên Header để chuyển sang Chế độ tối vừa phải (Soft Dark Mode) dạng xám phiến đá dịu mắt.

---

## Information Architecture

Hệ thống được tổ chức theo bố cục **3 cột (Three-Column Layout)** trực quan:

* **Cột trái (Thanh Sidebar điều hướng - Sidebar bên trái):** Chiều rộng cố định 240px. Tập trung **hoàn toàn và duy nhất** vào quản lý dự án (Project Management) và các thao tác CRUD dự án. Không chứa các tab chức năng dự án. Các thành phần bao gồm:
  - Nút "+ Tạo dự án mới" ở trên cùng để khởi tạo một dự án mới (Workspace mới).
  - Danh sách các dự án: Có tiêu đề rõ ràng là **"Danh sách các dự án"**, hiển thị tối đa 10 dự án sử dụng gần nhất. Mỗi dòng dự án hiển thị tên dự án và các nút hành động CRUD nhanh (chỉnh sửa tên, xóa dự án) xuất hiện khi hover. Nếu danh sách quá dài, khu vực này tự động kích hoạt thanh cuộn dọc (scrollbar) mượt mà để cuộn danh sách.
  - Nút "Xem tất cả" ở phía dưới danh sách để chuyển hướng người dùng đến Trang Quản lý toàn bộ dự án tập trung.
* **Cột giữa (Vùng làm việc chính - Center Workspace):** Chiếm toàn bộ không gian làm việc ở giữa. Vùng này chứa hai phần chính:
  - **Thanh Tab chức năng nằm ngang (Horizontal Project Tabs):** Đặt ở mép trên cùng của cột giữa, ngang hàng với tiêu đề Chatbot Panel. Bao gồm 3 tab tương ứng 1-1 với 3 User Journeys: "Thư viện Tài liệu", "Bản đồ Tri thức", và "Hỗ trợ viết tổng quan". Mọi hành động thêm/bớt User Journey phải cập nhật thanh tab ngang này tương ứng.
  - **Không gian hiển thị tab tương ứng:** Nằm dưới thanh tab ngang, hiển thị giao diện động tương ứng với tab được chọn:
    * *Tab 1: Thư viện Tài liệu & Quản lý Nạp* (Mặc định - kéo thả file, tìm kiếm arXiv/Semantic Scholar, hiển thị tiến trình nạp SSE, form điền metadata, danh sách tài liệu dự án).
    * *Tab 2: Bản đồ Tri thức Cytoscape.js* (Hiển thị đồ thị mạng lưới trích dẫn và liên kết tác giả, tích hợp chế độ tìm khoảng trống).
    * *Tab 3: Hỗ trợ viết tổng quan* (Giao diện quản lý bản thảo, hỗ trợ viết literature review và xuất báo cáo).
* **Cột phải (Khung Chatbot AI):** Khung chat với AI Agent trợ lý nghiên cứu hỗ trợ RAG, phân tích khoảng trống nghiên cứu và kiểm định trích dẫn. Khung này có thể co giãn (chiều rộng từ 20% đến 40%) và có thể thu gọn hoàn toàn sang bên phải. Bố cục gồm tiêu đề ở trên cùng. Nằm ngay dưới tiêu đề là cụm nút chức năng gồm nút tròn biểu tượng Lịch sử trò chuyện (Chat History) và nút tròn biểu tượng Trò chuyện mới (New Chat) nằm ngang hàng nhau. Ô nhập liệu chat (Chat Input) nằm ngay dưới cụm nút này. Khu vực hiển thị các đoạn hội thoại (Chat Content) nằm ở phía dưới cùng, tự động cuộn.
* **Top-Right Header Utilities Bar (Thanh Header tiện ích góc trên bên phải):** Nằm ở phía trên cùng góc bên phải (ngang hàng với thanh tab ngang của cột giữa). Chứa cụm phím chức năng hệ thống không phụ thuộc dự án: biểu tượng dấu chấm hỏi (`Trợ giúp`), bánh răng (`Cài đặt Hệ thống` - chỉ hiển thị đối với Admin để chuyển sang Trang Cài đặt Hệ thống dành cho Admin), và biểu tượng thoát (`Đăng xuất`), nằm cạnh bộ chọn ngôn ngữ `VI | EN` và nút chuyển chế độ sáng/tối.

### Các trang bổ sung (Additional Pages)
1. **Trang Cài đặt Hệ thống (Admin System Settings Page):**
   - Chỉ dành cho tài khoản Admin. Khi click bánh răng ở Header, hệ thống chuyển hướng sang trang này.
   - Gồm các tab cấu hình động: "Giới hạn hệ thống", "Trích dẫn & AI", "Quản trị người dùng". Cho phép lưu cấu hình trực tiếp vào cơ sở dữ liệu.
2. **Trang Quản lý toàn bộ dự án tập trung (Centralized Project Management Page):**
   - Click nút "Xem tất cả" ở Sidebar trái để chuyển hướng sang trang này.
   - Hiển thị danh sách dự án đầy đủ dạng bảng với tìm kiếm, phân trang và CRUD.

### Bố cục các Trang chủ (Homepages Layout)
* **Trang chủ Khách (Guest Homepage - Landing Page & Interactive Demo):**
  - Cấu trúc hiển thị toàn trang theo thứ tự cuộn dọc (Scrollable Flow):
    1. *Hero Banner & Value Proposition*: Giới thiệu giá trị cốt lõi của trợ lý nghiên cứu AI, các nút CTA chính ("Trải nghiệm Demo", "Đăng ký ngay").
    2. *Interactive Demo (Khung giả lập tương tác)*: Mô phỏng không gian làm việc thực tế với dữ liệu khoa học giả định, cho phép tìm kiếm thử và phân tích khoảng trống trực quan.
    3. *Case Study & Lợi ích*: Phân tích các trường hợp nghiên cứu thành công và thời gian tối ưu hóa quy trình.
    4. *Bảng giá & Giới hạn gói*: Bảng hiển thị thông tin giới hạn (ví dụ: gói miễn phí cho sinh viên và gói Pro cho nghiên cứu viên chuyên nghiệp).
    5. *Khối đăng ký chuyển đổi cuối trang (Footer CTA Signup)*.
* **Trang chủ Người dùng (User Homepage - Project Selector Dashboard):**
  - Giao diện 1 cột trung tâm hiển thị sau khi đăng nhập thành công (thanh Sidebar trái mặc định thu gọn, ẩn khung Chatbot bên phải).
  - Vùng tiêu đề chào mừng tích hợp thanh tìm kiếm dự án nhanh và nút "+ Tạo dự án mới".
  - Lưới hiển thị các thẻ dự án (Project Cards) hiện có, sắp xếp theo thời gian hoạt động.
* **Màn hình Onboarding tích hợp (New User Onboarding):**
  - Hiển thị khi người dùng đã đăng nhập nhưng chưa có bất kỳ dự án nào. Kết hợp cả 2 khu vực trong cùng 1 màn hình:
    - *Vùng bên trái (Form khởi tạo nhanh)*: Biểu mẫu tạo dự án đầu tiên (Tên dự án, Mô tả ngắn).
    - *Vùng bên phải (Hướng dẫn sử dụng)*: Checklist 3 bước tương tác cùng dải ảnh động/slide giới thiệu nhanh tính năng 3 cột của Workspace.

---

## Voice and Tone

Giữ nguyên giọng văn học thuật, trung thực và trực diện.

### Bộ dịch thuật giao diện tĩnh (Static Translations)

| Khóa giao diện (UI Key) | Nhãn Tiếng Việt (Mặc định) | Nhãn Tiếng Anh (English) |
|---|---|---|
| Menu Tab 1 | Thư viện Tài liệu | Document Library |
| Menu Tab 2 | Bản đồ Tri thức | Knowledge Map |
| Menu Tab 3 | Hỗ trợ viết tổng quan | Overview Writing Support |
| Nút Sidebar | + Tạo dự án mới | + Create Project |
| Tiêu đề danh sách dự án | Danh sách các dự án | Project List |
| Tiêu đề Chat Panel | Trợ lý nghiên cứu | Research Assistant |
| Nút Header Cài đặt | Cài đặt Hệ thống | System Settings |
| Tiêu đề Bản đồ | BẢN ĐỒ TRI THỨC CYTOSCAPE.JS | CYTOSCAPE.JS KNOWLEDGE MAP |
| Chú thích bản đồ | TOÀN VĂN / CHỈ SIÊU DỮ LIỆU | FULL TEXT / METADATA ONLY |
| Nút điều khiển Chat | Ẩn Chat / Hiện Chat | Hide Chat / Show Chat |
| Gợi ý input chat | Bạn cần tôi hỗ trợ gì... | How can I help you... |
| Gợi ý tìm kiếm Demo | Gõ thử "RAG Optimization" | Try searching "RAG Optimization" |
| Tiêu đề Demo | TRÌNH DIỄN GIẢ LẬP TƯƠNG TÁC | INTERACTIVE MOCK DEMO |
| Nhãn Tạo nhanh dự án | Tạo dự án đầu tiên của bạn | Create your first project |
| Tiêu đề Onboarding | Hướng dẫn bắt đầu nhanh | Quick Start Guide |
| Gói Dịch vụ | Gói Sinh viên / Gói Nghiên cứu viên | Student Plan / Researcher Plan |

---

## Component Patterns

### 1. Left Sidebar Navigation (Sidebar bên trái)
* **Thao tác quản lý:** Người dùng click "+ Tạo dự án mới" để chuyển đến màn hình onboarding/tạo dự án mới.
* **CRUD nhanh:** Khi rê chuột qua một dòng dự án, các nút icon sửa/xóa sẽ xuất hiện ở mép phải của dòng. Nhấp xóa sẽ hiển thị một Modal xác nhận trước khi thực hiện để tránh mất dữ liệu ngoài ý muốn.
* **Cuộn danh sách:** Sidebar chỉ hiển thị tối đa 10 dự án gần nhất. Nếu tổng số dự án lớn hơn, khu vực danh sách sẽ tự động kích hoạt thanh cuộn dọc.
* **Trang quản lý:** Click nút "Xem tất cả" dưới danh sách dự án gần đây sẽ điều hướng người dùng đến Trang Quản lý toàn bộ dự án tập trung.

### 2. Horizontal Project Tabs (Thanh Tab chức năng ở giữa)
* **Chuyển đổi màn hình:** Khi nhấp chọn các tab ngang ("Thư viện Tài liệu", "Bản đồ Tri thức", "Hỗ trợ viết tổng quan"), Center Workspace thay đổi nội dung hiển thị tương ứng.
* **Đồng bộ chatbot:** Hành động chuyển tab ngang sẽ tự động cập nhật ngữ cảnh hiển thị và các nút hành động gợi ý động trên Khung Chatbot AI bên phải tức thời.

### 3. Top-Right Header Utilities Bar (Thanh Header tiện ích góc trên bên phải)
* **Admin Gating:** Nút bánh răng `Cài đặt Hệ thống` chỉ hiển thị đối với người dùng có vai trò Admin để chuyển đến trang Cài đặt dành cho Admin.
* **Đăng xuất:** Click Đăng xuất giải phóng HttpOnly JWT cookie và chuyển hướng người dùng về Trang chủ Khách.
* **Chọn ngôn ngữ:** Click `VI | EN` sẽ chuyển đổi toàn bộ nhãn tĩnh trên UI mà không cần tải lại trang. Click icon sáng/tối để chuyển đổi class CSS giao diện.

### 4. Right Resizable & Collapsible Chatbot Panel (Khung Chatbot AI bên phải)
* **Tính năng Kéo giãn (Resizable):** Người dùng có thể rê chuột vào đường viền bên trái của Khung Chatbot (con trỏ chuột sẽ đổi thành dạng `col-resize`) và kéo để thay đổi chiều rộng từ 20% đến 40% màn hình (mặc định 25%). Đúp click vào dải biên kéo giãn để reset về chiều rộng mặc định 25%.
* **Tính năng Ẩn/Hiện (Collapsible):** Nhấp vào nút biểu tượng tin nhắn chat ở Header sẽ thu gọn hoàn toàn Khung Chatbot sang bên phải (chiều rộng về 0) để nhường toàn bộ không gian màn hình cho các tab trung tâm. Nhấp lại nút này để mở ra với kích thước đã kéo trước đó.
* **Cụm nút chức năng:** Nút Lịch sử trò chuyện (đồng hồ) và nút Trò chuyện mới (biểu tượng +) nằm ngang hàng nhau ngay dưới tiêu đề. Click Lịch sử mở Popover danh sách cuộc trò chuyện cũ.
* **Ô nhập tin nhắn (Chat Input):** Nằm ngay phía dưới cụm nút chức năng (bên trên luồng hội thoại).
* **Nút gợi ý động (Dynamic Quick Reply Buttons):** Các nút hành động gợi ý nằm ngay phía dưới ô chat input. Khi click, tự động chuyển tab trung tâm hoặc gửi lệnh tự động.
* **Luồng hội thoại (Chat History / Chat Content):** Nằm ở phía dưới cùng, hiển thị các tin nhắn cuộn từ dưới lên.

### 5. Cytoscape.js Knowledge Map Canvas (Bản đồ tri thức Cytoscape.js ở cột giữa)
* **Tương tác đồ thị:** Cho phép thu phóng, kéo thả tự do các node bài báo trên canvas.
* **Node Detail Card:** Click một node bài báo mở Node Detail Card trượt ra từ góc trên bên phải canvas đồ thị (không đè lên panel chatbot). Thẻ này hiển thị metadata chi tiết và cảnh báo khoảng trống/mâu thuẫn.
* **Chế độ Tìm khoảng trống:** Bật chế độ này qua nút nổi góc trái đồ thị để kích hoạt tô viền nhấp nháy đỏ `{colors.state-danger}` cho các bài viết có mâu thuẫn học thuật hoặc viền vàng cho các node cô lập.

### 6. Overview Writing Support Workspace (Giao diện Hỗ trợ viết tổng quan ở cột giữa)
* **Bản thảo:** Hiển thị danh sách các bản thảo literature review trong dự án. Click bản thảo để hiển thị nội dung trên rich editor.
* **AI Soạn thảo:** Hỗ trợ nhập lệnh AI để sinh/sửa đổi văn bản trực tiếp trong vùng editor.
* **Xuất báo cáo:** Click nút "Xuất báo cáo" ở góc phải để nén và tải xuống tệp ZIP chứa tệp `.md` (Markdown) và tệp `.bib` (BibTeX).

### 7. Interactive Citation Tooltip (Hộp thoại trích dẫn thông minh)
* **Hiển thị nhanh:** Click hoặc hover vào ký hiệu trích dẫn `[1]`, `[2]` trong chat hoặc bản thảo để mở tooltip bo góc `{rounded.lg}`.
* **Nội dung:** Hiển thị đoạn văn bản gốc (text chunk) được AI trích xuất trực tiếp làm bằng chứng, kèm thông tin bài viết gốc và nút mở tệp gốc trong trình duyệt hoặc tải tệp nhanh.

### 8. Interactive Demo Simulator (Khung Demo Giả Lập Tương Tác)
* **Mô phỏng 3 cột:** Khung giả lập hoạt động độc lập trên Landing Page. Cho phép khách gõ từ khóa, click nút gợi ý để mô phỏng tải kết quả tìm kiếm học thuật giả định trong 1.5 giây.
* **Sơ đồ thử nghiệm:** Cho phép click chuyển tab đồ thị Cytoscape demo với 1 node đỏ nhấp nháy chỉ khoảng trống nghiên cứu.

### 9. Centralized Project Management Page (Trang Quản lý toàn bộ dự án tập trung)
* **Quản trị danh sách:** Hiển thị bảng danh sách toàn bộ dự án của người dùng, hỗ trợ tìm kiếm nhanh dự án theo tên/mô tả và phân trang số ở góc dưới bên phải.
* **Thao tác nhanh:** Cung cấp các nút sửa tên dự án và xóa dự án trực tiếp trên bảng dòng dữ liệu.

### 10. Admin System Settings Page (Trang Cài đặt Hệ thống dành cho Admin)
* **Cấu hình động:** Chỉ dành cho Admin. Cho phép nhập/điều chỉnh các tham số hệ thống động (`MAX_PAPERS_PER_PROJECT`, `BROAD_QUERY_THRESHOLD`, `CITATION_ERROR_THRESHOLD`, `CITATION_RETRY_LIMIT`).
* Bấm "Lưu cấu hình" ghi nhận trực tiếp vào Database, áp dụng ngay tức thì mà không cần restart server hay deploy lại code.

### 11. New User Onboarding Section (Màn hình Onboarding tích hợp)
* **Tạo nhanh dự án:** Cột trái hiển thị biểu mẫu tạo dự án đầu tiên của người dùng mới. Nút "Tạo dự án" đổi sang màu xanh Cobalt `{colors.accent-blue}` khi các trường bắt buộc được điền.
* **Hướng dẫn:** Cột phải chứa checklist 3 bước tương tác cùng slide/ảnh động giới thiệu nhanh cách sử dụng.

### 12. Project Selector Grid Dashboard (Thẻ dự án Dashboard)
* Hiển thị danh sách dự án dạng lưới Responsive tự thích ứng theo 3 kích thước màn hình (PC rộng: 3 cột, PC vừa/tablet: 2 cột, Mobile: 1 cột).
* Hover vào thẻ dự án kích hoạt hiệu ứng dịch chuyển nhẹ lên trên (`translateY(-2px)`) và đổi màu viền sang xanh cobalt `{colors.accent-blue}`.

### 13. Pricing Table (Bảng giá dịch vụ)
* Hiển thị bảng so sánh các tính năng và giới hạn giữa gói Sinh viên (Free) và gói Nghiên cứu viên (Pro) trên Landing page. Thẻ Pro được bo viền xanh cobalt `{colors.accent-blue}` và có nhãn nổi bật "PHỔ BIẾN NHẤT".

### 14. SSE Ingestion Progress Flow (Tiến trình nạp tài liệu bất đồng bộ qua SSE)
* SSE đẩy trạng thái tiến trình nạp tài liệu theo thời gian thực (đang tải -> đang OCR -> đang nhúng vector -> hoàn thành). Không sử dụng cơ chế timeout cứng 30 giây của request HTTP thông thường.

### 15. Manual Ingestion Metadata Form (Form điền siêu dữ liệu thủ công)
* Giao diện chỉnh sửa tích hợp hiển thị khi tải lên tệp PDF/DOCX cá nhân. Các trường do AI tự trích xuất có nhãn badge `"AI Suggested"`. Người dùng có thể chỉnh sửa lại thông tin trước khi nhấn nút "Xác nhận".

### 16. Degraded Union API Toast Alert (Thông báo Toast lỗi API)
* Đẩy một thông báo Toast màu vàng nổi bật ở góc trên bên phải màn hình khi một trong hai nguồn API arXiv hoặc Semantic Scholar bị lỗi hoặc quá hạn (Rate limit/Timeout). Chứa nút đóng nhanh (x) hoặc tự biến mất sau 5 giây.

### 17. Broad Query Interactive Buttons (Thẻ gợi ý phân ngành rộng)
* Hiển thị danh sách thẻ nút bấm gợi ý phân ngành phụ do LLM sinh ra dưới thanh tìm kiếm khi kết quả vượt ngưỡng. Nhấp nút sẽ tự động điền từ khóa và kích hoạt tìm kiếm mới.

### 18. Hard Document Limit Error Alert (Cảnh báo lỗi cứng giới hạn tài liệu)
* Khi số tài liệu đạt giới hạn cứng, hệ thống vô hiệu hóa nút nạp tài liệu và hiển thị hộp cảnh báo đỏ viền đậm màu `{colors.state-danger}` với thông điệp: *"Dự án đã đạt giới hạn tài liệu tối đa của hệ thống ({MAX_PAPERS_PER_PROJECT} tài liệu). Vui lòng liên hệ Admin hoặc xóa bớt tài liệu."*

---

## State Patterns

### Trạng thái Khung Chatbot AI:
* `Collapsed` (Đã thu gọn): Khung ẩn hoàn toàn, nút Toggle ở Header ở trạng thái chưa kích hoạt.
* `Expanded` (Đang mở): Khung hiển thị với chiều rộng tùy chỉnh, nút Toggle ở Header đổi màu sang `{colors.accent-blue}`.
* `Resizing` (Đang kéo giãn): Một đường chỉ thị mảnh màu xanh `{colors.accent-blue}` hiển thị dọc biên kéo để người dùng thấy rõ kích thước mới trước khi thả chuột.
* `Chatbot-Thinking` (Đang suy luận): Agent đang chạy RAG hoặc suy luận (hiển thị spinner hoặc 3 chấm nhấp nháy và vô hiệu hóa ô chat input).
* `Chatbot-Error` (Lỗi kết nối): Mất kết nối đến server hoặc timeout (hiển thị banner lỗi màu đỏ dưới chat kèm nút gửi lại).

### Trạng thái Giao diện Homepage & Dashboard:
* `Guest-Landing`: Trạng thái mặc định cho khách vãng lai, hiển thị trang Landing page giới thiệu và bảng giá.
* `Guest-Demoing`: Trạng thái khi khách click tương tác thử trong phần Demo Simulator. Bản đồ Cytoscape và danh sách tài liệu chạy thử chế độ giả lập.
* `User-Dashboard-Empty`: Người dùng đã đăng nhập nhưng chưa có dự án nào, hiển thị màn hình Onboarding kết hợp tạo dự án và tài liệu hướng dẫn.
* `User-Dashboard-Populated`: Người dùng có ít nhất 1 dự án, hiển thị lưới Project Selector Card.

### Trạng thái nạp tài liệu (SSE Ingestion States):
* `Ingesting-Downloading` (Đang tải): SSE gửi sự kiện tải file từ internet hoặc upload tệp.
* `Ingesting-OCR` (Đang quét cấu trúc & OCR): SSE gửi sự kiện chạy OCR cho tài liệu scan.
* `Ingesting-Embedding` (Đang nhúng vector): SSE gửi sự kiện cắt đoạn và nhúng vector.
* `Ingested` (Đã nạp): Hoàn tất nạp tài liệu, danh sách tài liệu cập nhật.

### Trạng thái trích dẫn của Chatbot:
* `Normal` (Bình thường): Các trích dẫn khớp 100% tài liệu thực tế.
* `Citation-Filtered` (Đã sửa lỗi): Tỷ lệ lỗi trích dẫn ảo $\le$ `CITATION_ERROR_THRESHOLD` (mặc định 30%), hệ thống tự động lọc bỏ hoặc thay bằng thẻ `[Nguồn không xác định]`.
* `Low-Reliability` (Độ tin cậy thấp): Tỷ lệ lỗi trích dẫn ảo vượt quá `CITATION_ERROR_THRESHOLD` kể cả sau khi đã thử lại tối đa `CITATION_RETRY_LIMIT` lần. Hiển thị nhãn cảnh báo độ tin cậy thấp màu đỏ/cam nổi bật ở đầu câu trả lời.

### Trạng thái giới hạn tài liệu của dự án:
* `Document-Limit-Reached` (Đạt giới hạn): Số lượng tài liệu trong dự án hiện tại $\ge$ `MAX_PAPERS_PER_PROJECT`. Vô hiệu hóa tính năng nạp tài liệu mới và hiển thị cảnh báo chặn trên UI.

### Trạng thái bề mặt IA bổ sung:
* **Sidebar Navigation:**
  - `Sidebar-Loading`: Đang tải danh sách dự án (hiển thị skeleton).
  - `Sidebar-Scrollable`: Danh sách dự án vượt quá 10, hiển thị thanh cuộn mượt.
* **Center Workspace - Tab 1 (Thư viện tài liệu):**
  - `Search-Results-Empty`: Không tìm thấy bài báo nào khớp từ khóa tìm kiếm.
* **Center Workspace - Tab 2 (Bản đồ tri thức):**
  - `Map-Loading`: Đang tải dữ liệu đồ thị từ Neo4j (hiển thị spinner trên canvas).
  - `Map-Empty`: Dự án chưa có tài liệu nào, bản đồ hiển thị thông điệp hướng dẫn nạp tài liệu.
  - `Node-Focus`: Một node bài viết được click chọn, node đổi sang màu viền xanh lá đậm và trượt Node Detail Card ra.
* **Center Workspace - Tab 3 (Hỗ trợ viết tổng quan):**
  - `Manuscript-Empty`: Dự án chưa có bản thảo nào, hiển thị nút "+ Tạo bản thảo mới".
  - `Manuscript-Saving`: Đang tự động lưu bản thảo (hiển thị nhãn "Đang lưu..." mờ ở góc).
  - `Manuscript-Saved`: Đã lưu thành công (hiển thị nhãn "Đã lưu").
* **Trang Đăng ký & Đăng nhập (Login & Registration Page):**
  - `Auth-Validation-Error`: Các trường nhập liệu email/mật khẩu sai định dạng (hiển thị thông báo đỏ dưới input).
  - `Auth-Failed`: Sai thông tin tài khoản (trả về 401, hiển thị banner lỗi đăng nhập trên cùng).
* **Trang Cài đặt Admin:**
  - `Config-Saving`: Đang lưu cấu hình vào DB (vô hiệu hóa nút Lưu).
  - `Config-Validation-Error`: Giá trị cấu hình nhập số âm hoặc không hợp lệ (hiển thị viền đỏ quanh input và chặn nút Lưu).

---

## Interaction Primitives

* **Thao tác kéo giãn:** Nhấn giữ chuột trái tại biên trái của Khung Chatbot, di chuột sang trái/phải để thay đổi kích thước, thả chuột trái để lưu kích thước.
* **Thao tác chuyển đổi ngôn ngữ:** Click nút `[VI / EN]` ở Header lập tức đổi toàn bộ nhãn giao diện tĩnh sang ngôn ngữ được chọn mà không cần tải lại trang.
* **Thao tác chuyển đổi giao diện:** Click biểu tượng Mặt trăng/Mặt trời ở Header lập tức thay đổi các lớp CSS màu sắc từ Sáng (Light) sang Tối (Soft Dark) và ngược lại.

---

## Accessibility Floor

* **Vùng tương tác:** Đường biên kéo giãn rộng 4px nhưng có vùng nhận diện tương tác chuột (hitbox) ẩn rộng `10px` giúp người dùng dễ dàng rê trúng chuột để kéo giãn.
* **Phím tắt:** Sử dụng `SHIFT + ENTER` để xuống dòng trong ô chat, `ENTER` để gửi tin nhắn.
* **Độ tương phản chữ:** Chữ đen `{colors.ink-primary}` trên nền giấy ấm `{colors.surface-base}` đạt độ tương phản chuẩn WCAG AA, không bị lóa mắt.

---

## Key Flows

### Luồng 1: Minh nạp tài liệu khoa học và phân tích khoảng trống nghiên cứu (UJ-1 & UJ-2)
1. Minh mở ứng dụng, chọn dự án **"Tối ưu hóa RAG"** ở Sidebar bên trái. Cột giữa mặc định mở Tab 1 **Thư viện Tài liệu** (điểm khởi đầu trống rỗng).
2. Minh tiến hành nạp tài liệu thủ công bằng cách kéo thả 1 file PDF scan (không có lớp text). Giao diện lập tức kích hoạt thanh tiến trình nạp SSE.
3. Hệ thống chạy tác vụ bất đồng bộ và trả về tiến trình chi tiết qua SSE: *"Đang tải từ internet..."* -> *"Đang quét cấu trúc & OCR..."* (hiển thị biểu tượng OCR) -> và dừng lại hiển thị **Form điền siêu dữ liệu thủ công**.
4. Các trường thông tin (Tiêu đề, Tác giả, Năm, Tóm tắt) được LLM tự động trích xuất và hiển thị kèm nhãn badge `"AI Suggested"`. Minh chỉnh sửa lại một số ký tự lỗi trong Tiêu đề và bấm **"Xác nhận"**.
5. Hệ thống tiếp tục chạy: *"Đang nhúng vector..."* -> *"Đã nạp thành công"* (màu xanh lá).
6. Minh tiếp tục gõ từ khóa tìm kiếm "RAG vector retrieval optimization" vào thanh tìm kiếm API. API arXiv thành công nhưng API Semantic Scholar bị timeout sau 10 giây. Hệ thống vẫn hiển thị kết quả arXiv và hiện Toast cảnh báo màu vàng nhẹ ở góc phải: *"API Semantic Scholar gặp sự cố, hiển thị kết quả từ nguồn còn lại."*
7. Kết quả trả về vượt ngưỡng `BROAD_QUERY_THRESHOLD` (50), hệ thống tự động sinh ra danh sách thẻ gợi ý phân ngành rộng dưới dạng các nút bấm: `[RAG Retrieval Accuracy]`, `[Vector Index Optimization]`. Minh click vào nút `[Vector Index Optimization]`, hệ thống tự động chạy truy vấn mới cho từ khóa này.
8. Minh thêm bài báo đó vào dự án, sau đó chuyển sang Tab 2 **Bản đồ Tri thức** ở cột giữa để xem sơ đồ mạng lưới Cytoscape.js. Minh bấm chế độ "Tìm khoảng trống nghiên cứu", sơ đồ lập tức làm nổi bật 1 node có viền đỏ nhấp nháy chỉ ra mâu thuẫn thực nghiệm. Minh click node đó để xem Node Detail Card hiển thị chi tiết mâu thuẫn.

### Luồng 2: Minh soạn thảo tổng quan, kiểm định trích dẫn và tương tác Chatbot (UJ-3)
1. Minh chuyển sang Tab 3 **Hỗ trợ viết tổng quan** ở cột giữa để chuẩn bị soạn thảo literature review.
2. Tại cột phải (Khung Chatbot), Minh muốn xem các phiên trò chuyện trước đó của dự án. Anh click vào nút biểu tượng Lịch sử trò chuyện (đồng hồ) nằm dưới tiêu đề panel. Một Popover hiện ra, Minh click chọn phiên chat hôm qua, chatbot tải lại cuộc trò chuyện và tự động đóng popover.
3. Chatbot nhận diện trạng thái dự án của Minh và hiển thị các nút hành động gợi ý động: `[Tải tài liệu lên]`, `[Xem bản đồ tri thức]`, `[Gợi ý dàn ý]`. Minh click nút `[Gợi ý dàn ý]`, chatbot tự động trả về đề xuất dàn ý.
4. Minh gõ yêu cầu vào ô chat: "Soạn thảo một đoạn literature review ngắn về mô hình Hybrid RAG".
5. AI Agent tạo câu trả lời và điền văn bản vào khu vực hỗ trợ viết tổng quan ở cột giữa. Văn bản chứa các trích dẫn học thuật như `[1]` và `[2]`.
6. Tuy nhiên, hệ thống phát hiện 1 trích dẫn không khớp trong cơ sở dữ liệu. Vì tỷ lệ lỗi là 25% ($\le$ `CITATION_ERROR_THRESHOLD` 30%), hệ thống tự động thay trích dẫn lỗi thành `[Nguồn không xác định]` và trả kết quả bình thường.
7. Minh click hoặc di chuột (hover) vào ký hiệu `[1]`. Một hộp thoại nổi `Citation Tooltip` xuất hiện hiển thị thông tin bài viết gốc, đoạn văn bản trích dẫn gốc (text chunk) làm căn cứ, và nút "Tải PDF gốc" để Minh đối chiếu.
8. Minh click nút **"Xuất Báo cáo"** ở góc phải Tab Hỗ trợ viết tổng quan. Hệ thống nén và tải xuống tệp ZIP chứa file `.bib` (BibTeX) và `.md` (Markdown).

### Luồng 3: Quản trị viên điều chỉnh cấu hình hệ thống và kiểm tra giới hạn tài liệu (FR-11 & FR-12)
1. Minh (có tài khoản gán quyền Admin) click vào nút bánh răng `Cài đặt Hệ thống` ở thanh Header góc trên bên phải. Hệ thống chuyển hướng sang **Trang Cài đặt Hệ thống dành cho Admin**.
2. Minh chọn tab "Giới hạn hệ thống". Anh chỉnh sửa giới hạn tài liệu tối đa của dự án `MAX_PAPERS_PER_PROJECT` thành `3` (mặc định là 15) và bấm **"Lưu cấu hình"**. Cấu hình được cập nhật động tức thì vào Database.
3. Minh quay lại không gian làm việc của dự án "Tối ưu hóa RAG" (hiện tại dự án này đang có 3 tài liệu).
4. Hệ thống lập tức nhận diện số tài liệu đã đạt giới hạn 3/3, giao diện chuyển sang trạng thái `Document-Limit-Reached`. Nút tải lên tài liệu và vùng kéo thả file bị vô hiệu hóa (disabled).
5. Để xác định hành vi, Minh cố tình gọi API upload tệp qua console. Hệ thống trả về mã lỗi HTTP 403, và Frontend hiển thị thông báo cảnh báo lỗi cứng: *"Dự án đã đạt giới hạn tài liệu tối đa (3 tài liệu). Vui lòng liên hệ Admin hoặc xóa bớt tài liệu."*
6. Minh quay lại Trang Cài đặt Hệ thống và đổi giới hạn về `15` để tiếp tục làm việc bình thường.

### Luồng 4: Đăng ký, đăng nhập và phân quyền Admin đầu tiên (FR-1)
1. Minh truy cập vào hệ thống lần đầu, được chuyển hướng đến Trang Đăng ký & Đăng nhập.
2. Minh điền email và mật khẩu, nhấn nút Đăng ký.
3. Vì Minh là người dùng đăng ký đầu tiên trên hệ thống, cơ chế phân quyền Admin tự động gán vai trò `admin` cho anh.
4. Hệ thống chuyển hướng anh sang Trang Onboarding do anh chưa có dự án nào. Minh thực hiện điền tên dự án đầu tiên và tạo dự án thành công.
5. Minh đăng xuất ra khỏi hệ thống qua Header Utilities.
6. Minh thử đăng nhập lại với mật khẩu sai, hệ thống trả về mã lỗi HTTP 401 và hiển thị Banner cảnh báo lỗi đăng nhập trên giao diện. Minh điền đúng mật khẩu và đăng nhập thành công. Admin gear icon xuất hiện ở Header vì Minh có quyền Admin.


