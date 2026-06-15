---
name: AcademicPaper
description: Hệ thống thiết kế định hướng tài liệu giấy học thuật sạch sẽ. Mặc định ở chế độ sáng (Light Mode) và hỗ trợ chế độ tối vừa phải (Soft Dark Mode) làm tùy chọn.
status: final
updated: 2026-06-13
colors:
  # Chế độ Sáng (Light Mode - Mặc định)
  surface-base: '#FAF9F6'
  surface-raised: '#FFFFFF'
  ink-primary: '#1E2022'
  ink-secondary: '#64748B'
  accent-blue: '#2563EB'
  accent-violet: '#8B5CF6'
  state-success: '#10B981'
  state-warning: '#F59E0B'
  state-danger: '#EF4444'
  border-hairline: '#E2E8F0'

  # Chế độ Tối Vừa Phải (Soft Dark Mode - Tùy chọn)
  surface-base-dark: '#1F2023'
  surface-raised-dark: '#282A2D'
  ink-primary-dark: '#E4E6EB'
  ink-secondary-dark: '#94A3B8'
  accent-blue-dark: '#60A5FA'
  accent-violet-dark: '#A78BFA'
  state-success-dark: '#34D399'
  state-warning-dark: '#FBBF24'
  state-danger-dark: '#F87171'
  border-hairline-dark: '#383A40'
typography:
  family: 'Inter, system-ui, sans-serif'
  title:
    fontSize: '16px'
    fontWeight: '600'
    lineHeight: '22px'
  body:
    fontSize: '13px'
    fontWeight: '400'
    lineHeight: '18px'
  meta:
    fontSize: '11px'
    fontWeight: '400'
    lineHeight: '14px'
rounded:
  sm: '4px'
  md: '6px'
  lg: '8px'
spacing:
  '1': '4px'
  '2': '8px'
  '3': '12px'
  '4': '16px'
  '5': '24px'
  '6': '32px'
---

# AcademicPaper — Quy chuẩn Thiết kế Giao diện (DESIGN.md)

Hệ thống thiết kế **AcademicPaper** lấy cảm hứng từ cấu trúc trực quan của các bài báo khoa học và công cụ quản lý tài liệu hiện đại. Hệ thống hướng đến sự thoải mái tối đa cho mắt trong thời gian nghiên cứu kéo dài, sử dụng tông màu ấm nhẹ mặc định và tối giản hóa các thành phần màu sắc không liên quan.

* **Tham chiếu trực quan:** 
  - Giao diện làm việc chính (Chat & Sơ đồ): [mockups/academic_paper_dashboard.png](file:///home/agent/github/C2-App-053/_bmad-output/planning-artifacts/ux-designs/ux-C2-App-053-2026-06-12/mockups/academic_paper_dashboard.png)
  - Giao diện Thư viện Tài liệu: [mockups/document_library_view.png](file:///home/agent/github/C2-App-053/_bmad-output/planning-artifacts/ux-designs/ux-C2-App-053-2026-06-12/mockups/document_library_view.png)
  - Quy chuẩn thiết kế dạng chữ luôn được ưu tiên áp dụng so với hình ảnh minh họa trong trường hợp có mâu thuẫn.

---

## Brand & Style

* **Triết lý chủ đạo:** Trực quan hóa tri thức học thuật một cách sạch sẽ, giống như lật mở các trang tài liệu.
* **Chế độ hiển thị:** Mặc định sử dụng Chế độ sáng (Light ## Colors

### 1. Chế độ sáng (Light Mode - Mặc định)
* **Nền cơ sở (`surface-base`):** Sắc trắng ấm của giấy học thuật (`#FAF9F6`), làm dịu mắt người đọc so với nền trắng tinh.
* **Nền nổi (`surface-raised`):** Trắng tinh khiết (`#FFFFFF`) dùng cho thanh Sidebar, các thẻ bài báo, bảng điều khiển và popover.
* **Chữ chính (`ink-primary`):** Màu xám than sẫm (`#1E2022`) mang lại độ sắc nét cao nhưng ít gay gắt hơn màu đen tuyền.
* **Chữ phụ (`ink-secondary`):** Màu xám trung tính (`#64748B`) cho siêu dữ liệu, tóm tắt và chú thích.
* **Nhấn Cobalt (`accent-blue`):** Xanh cobalt học thuật (`#2563EB`), biểu thị hành động chính, nút chọn trạng thái, và liên kết trích dẫn.
* **Nhấn Amethyst (`accent-violet`):** Màu tím hoa thạch anh (`#8B5CF6`), đại diện cho mối liên hệ tác giả.
* **Đường viền (`border-hairline`):** Màu xám nhạt (`#E2E8F0`), phân định ranh giới cột và hộp thoại rõ ràng.

* **Độ tương phản mục tiêu (Light contrast targets):**
  - Tổ hợp chữ chính `ink-primary` trên nền `surface-base` đạt độ tương phản ~15.0:1 (Vượt chuẩn WCAG AAA 7:1).
  - Tổ hợp chữ phụ `ink-secondary` trên nền `surface-base` đạt độ tương phản ~4.6:1 (Vượt chuẩn WCAG AA 4.5:1).
  - Tổ hợp màu nhấn `accent-blue` trên nền `surface-raised` hoặc `surface-base` đạt độ tương phản ~4.8:1 (Vượt chuẩn WCAG AA 4.5:1).

### 2. Chế độ tối vừa phải (Soft Dark Mode)
* **Nền cơ sở tối (`surface-base-dark`):** Màu xám than đá dịu nhẹ (`#1F2023`), giữ độ sáng ở mức vừa phải để không gây hiện tượng bóng ma thị giác khi di chuyển mắt trên màn hình tối.
* **Nền nổi tối (`surface-raised-dark`):** Xám đậm nhẹ (`#282A2D`).
* **Chữ chính tối (`ink-primary-dark`):** Trắng ngà ấm (`#E4E6EB`).
* **Chữ phụ tối (`ink-secondary-dark`):** Xám ghi nhạt (`#94A3B8`).
* **Nhấn Cobalt tối (`accent-blue-dark`):** Màu xanh lam sáng (`#60A5FA`).
* **Nhấn Amethyst tối (`accent-violet-dark`):** Màu tím nhạt (`#A78BFA`).
* **Đường viền tối (`border-hairline-dark`):** Màu xám sẫm (`#383A40`).

* **Độ tương phản mục tiêu (Dark contrast targets):**
  - Tổ hợp chữ chính tối `ink-primary-dark` trên nền `surface-base-dark` đạt độ tương phản ~11.0:1 (Vượt chuẩn WCAG AAA).
  - Tổ hợp chữ phụ tối `ink-secondary-dark` trên nền `surface-base-dark` đạt độ tương phản ~4.8:1 (Vượt chuẩn WCAG AA).
  - Tổ hợp màu nhấn tối `accent-blue-dark` trên nền `surface-base-dark` đạt độ tương phản ~5.1:1 (Vượt chuẩn WCAG AA).

---

## Typography

Phông chữ hệ thống **Inter** là trục xương sống hiển thị văn bản, đảm bảo các bảng dữ liệu siêu dữ liệu và nội dung chat nghiên cứu có mật độ thông tin cao nhưng cực kỳ dễ đọc.

* **Tiêu đề (`title`):** `{typography.title.fontSize}`, độ đậm `{typography.title.fontWeight}`. Dùng cho thanh tiêu đề cột, tên dự án khoa học.
* **Thân bài (`body`):** `{typography.body.fontSize}`. Dùng cho nội dung chat của AI, tóm tắt của bài báo và các đoạn văn bản.
* **Chú thích (`meta`):** `{typography.meta.fontSize}`. Dùng cho thông tin chỉ số năm xuất bản, DOI và chú giải sơ đồ.

---

## Layout & Spacing

Bố cục được xây dựng theo kiến trúc ba cột dọc (Three-Column Layout) từ trái qua phải khi ở trong không gian dự án:
1. **Cột 1 (Sidebar Navigation - Sidebar bên trái):** Chiều rộng cố định 240px. Tập trung **hoàn toàn và duy nhất** vào quản lý dự án (Project Management) và các thao tác CRUD dự án. Không chứa các tab chức năng dự án. Các thành phần bao gồm:
   - Nút "+ Tạo dự án mới" ở trên cùng để khởi tạo một dự án mới (Workspace mới), nền màu `{colors.accent-blue}` và chữ trắng, bo góc `{rounded.md}` (6px).
   - Danh sách các dự án: Có tiêu đề rõ ràng là **"Danh sách các dự án"** (chữ in hoa nhẹ, cỡ `{typography.meta.fontSize}` màu `{colors.ink-secondary}`). Hiển thị tối đa 10 dự án gần nhất dạng danh mục. Mỗi dòng dự án hiển thị tên dự án và các icon CRUD nhanh xuất hiện rõ khi hover. Khu vực danh sách tự động kích hoạt thanh cuộn dọc mượt mà (`overflow-y: auto`) nếu danh sách vượt quá chiều cao hiển thị.
   - Nút "Xem tất cả" ở phía dưới danh sách, chữ màu `{colors.accent-blue}` cỡ `{typography.meta.fontSize}` để chuyển hướng đến Trang Quản lý toàn bộ dự án tập trung.
2. **Cột 2 (Center Workspace - Không gian làm việc ở giữa):** Chiếm toàn bộ không gian còn lại ở giữa. Ở phía trên cùng của cột trung tâm, ngang hàng với tiêu đề của Chatbot Panel, chứa một **Thanh Tab chức năng của dự án** (Horizontal Project Tabs) nằm ngang bao gồm: "Thư viện Tài liệu", "Bản đồ Tri thức", và "Hỗ trợ viết tổng quan". Các tab này tương ứng 1-1 với 3 User Journeys của dự án (thêm/bớt UJ phải thay đổi tab ngang tương ứng). Khi chọn một tab, nội dung workspace tương ứng (danh sách thư viện, bản đồ Cytoscape.js, hay khu vực soạn thảo tổng quan) sẽ hiển thị ở khu vực phía dưới.
3. **Cột 3 (Right Chat Panel - Khung Chatbot bên phải):** Khung Chatbot AI đóng vai trò người bạn đồng hành nghiên cứu. Chiếm tỷ lệ từ 1/4 đến 1/5 màn hình (mặc định 25%), được trang bị dải biên kéo giãn (resizable handle) để điều chỉnh chiều rộng tùy chọn và nút ẩn/hiện (collapsible toggle). Bố cục gồm tiêu đề ở trên cùng. Nằm ngay dưới tiêu đề là cụm nút chức năng gồm nút biểu tượng Lịch sử trò chuyện (Chat History Icon Button) và nút biểu tượng Trò chuyện mới (New Chat Icon Button) nằm ngang hàng nhau. Ô nhập liệu chat (Chat Input) nằm ngay phía dưới cụm nút này. Vùng hiển thị nội dung hội thoại (Chat Content) nằm ở phần còn lại phía dưới, chứa các tin nhắn tự động cuộn.
4. **Thanh Header tiện ích góc trên bên phải (Top-Right Header Utilities Bar):** Nằm ở góc trên cùng bên phải (ngang hàng với thanh tab cột giữa), gom toàn bộ các công cụ hệ thống không phụ thuộc dự án bao gồm: "Trợ giúp" (?), "Cài đặt Hệ thống" (bánh răng - chỉ hiển thị đối với tài khoản có quyền Admin), "Đăng xuất", bộ chọn ngôn ngữ `VI | EN` và nút giao diện sáng/tối.

### Bố cục các Trang bổ sung (Additional Pages Layout)
1. **Trang Đăng ký & Đăng nhập (Login & Registration Page):**
   - Bố cục 1 cột trung tâm tối giản, căn giữa hoàn toàn theo cả chiều ngang và chiều dọc (Flexbox/Grid layout).
   - Container biểu mẫu (Form Card) có chiều rộng cố định 400px, nền màu `{colors.surface-raised}`, bo góc `{rounded.lg}` (8px), viền `{colors.border-hairline}`.
   - Các trường thông tin (Email, Mật khẩu) có nhãn rõ ràng, ô nhập liệu bo góc `{rounded.md}` (6px), viền `{colors.border-hairline}`.
2. **Trang Cài đặt Hệ thống (System Settings Page - Chỉ dành cho Admin):**
   - Bố cục 1 cột trung tâm rộng rãi, hiển thị khi Admin click vào nút bánh răng ở Top-Right Header Utilities Bar.
   - Chứa một **Thanh Tab chức năng cấu hình** (Horizontal Config Tabs) nằm ngang bao gồm: "Giới hạn hệ thống", "Trích dẫn & AI", và "Quản trị người dùng".
   - Khu vực phía dưới hiển thị Form cấu hình chi tiết cho tab được chọn. Các ô nhập liệu có kích thước chuẩn `{spacing.4}` (16px), bo góc `{rounded.md}` (6px), viền `{colors.border-hairline}`.
3. **Trang Quản lý toàn bộ dự án tập trung (Centralized Project Management Page):**
   - Bố cục 1 cột trung tâm rộng rãi, hiển thị khi người dùng click vào nút "Xem tất cả" dưới danh sách dự án ở Sidebar bên trái.
   - Chứa thanh tiêu đề "Quản lý Dự án", thanh tìm kiếm nhanh, nút "+ Tạo dự án mới" ở góc trên bên phải.
   - Bảng danh sách dự án (Project Table) hiển thị tất cả các dự án của tài khoản, hỗ trợ phân trang ở dưới cùng. Mỗi dòng dự án hiển thị đầy đủ thông tin: Tên, Mô tả, Số tài liệu đã nạp, Ngày cập nhật, và các nút CRUD nhanh.

### Bố cục các Trang chủ (Homepages Layout)
1. **Trang chủ Khách (Guest Homepage - Landing Page):**
   - Bố cục 1 cột cuộn dọc duy nhất (Single-Column Scroll layout).
   - Container chính có độ rộng tối đa (`max-width: 1200px`), tự động căn giữa màn hình với khoảng đệm lề `{spacing.5}` (24px) hai bên để hiển thị tốt trên các thiết bị.
   - Khoảng cách dọc (vertical spacing) giữa các khối nội dung lớn là `{spacing.6}` (32px) hoặc `{spacing.5}` (24px) để tạo khoảng thở học thuật.
   - Interactive Demo Simulator: Căn giữa trong container, hiển thị dưới dạng một khung Workspace thu nhỏ (mô phỏng 3 cột) nằm lồng trong dải viền nổi bật.
2. **Trang chủ Người dùng (User Homepage - Project Selector Dashboard):**
   - Bố cục 1 cột trung tâm rộng rãi chiếm toàn bộ chiều ngang trình duyệt. Sidebar trái mặc định thu gọn thành dạng biểu tượng (hoặc ẩn hoàn toàn) và không hiển thị panel chat chatbot bên phải.
   - Header Dashboard nằm ở trên cùng, chứa tiêu đề chào mừng ("Xin chào, {user_name}!"), thanh tìm kiếm dự án nhanh và nút "+ Tạo dự án mới".
   - Lưới danh sách dự án (Project Grid) sử dụng hệ thống responsive:
     * Màn hình máy tính rộng (>1200px): Grid 3 cột.
     * Màn hình máy tính thường và tablet (768px - 1200px): Grid 2 cột.
     * Màn hình di động (<768px): Grid 1 cột.
     * Khoảng cách giữa các cột và hàng trong grid là `{spacing.4}` (16px).
3. **Màn hình Onboarding (Người dùng chưa có dự án):**
   - Bố cục chia hai phần phân tách (Split layout, tỷ lệ 45% bên trái và 55% bên phải).
   - Phần bên trái chứa form tạo nhanh dự án.
   - Phần bên phải chứa checklist hướng dẫn và slide/video minh họa.

---

## Elevation & Depth

* **Sử dụng độ tương phản màu:** Trong Light mode, phần nền cơ sở `{colors.surface-base}` (`#FAF9F6`) bao quanh các thẻ và thanh điều hướng `{colors.surface-raised}` (`#FFFFFF`). Đường viền mảnh `{colors.border-hairline}` (`#E2E8F0`) giúp định hình các đường phân ranh giới.
* **Popover nổi (Citation Tooltip / Chat History Popover):** Sử dụng viền sáng nhẹ và hiệu ứng nâng chiều sâu rất mỏng để làm nổi bật thông tin trích dẫn gốc hoặc danh sách lịch sử so với nền đồ thị hoặc khung chat.

---

## Shapes

AcademicPaper áp dụng các bo góc có bán kính hẹp để giữ giao diện luôn sắc nét và mang tính kỹ thuật:
* Bo góc `{rounded.sm}` (4px) cho các thẻ trích dẫn `[1]`, các thẻ tag phân ngành phụ trợ và badge gợi ý trích xuất.
* Bo góc `{rounded.md}` (6px) cho các nút hành động chính, trường nhập văn bản, các dòng bài báo trong thư viện, các nút gợi ý chat nhanh và hộp cảnh báo.
* Bo góc `{rounded.lg}` (8px) cho hộp thoại chi tiết node đồ thị, popover lịch sử chat và bảng chat chatbot.

---

## Components

### 1. Left Sidebar Navigation (Sidebar bên trái)
* Nền màu `{colors.surface-raised}`, viền phải `{colors.border-hairline}`.
* Chỉ tập trung vào quản lý dự án, bao gồm:
  - **Phần đầu:** Logo "AcademicPaper" cùng tên thương hiệu.
  - **Nút hành động chính:** Nút bấm nổi bật "+ Tạo dự án mới" (nền `{colors.accent-blue}`) để tạo mới dự án.
  - **Danh sách các dự án (Project List):** 
    * Có tiêu đề phân vùng rõ ràng là **"Danh sách các dự án"** (chữ in hoa nhẹ hoặc in đậm mờ, kích thước `{typography.meta.fontSize}`).
    * Danh sách dạng danh mục chứa các dự án của người dùng (ví dụ: "Tối ưu hóa RAG", "Học sâu trong Y tế"). Mỗi dòng dự án hiển thị tên dự án và các biểu tượng CRUD nhanh (chỉnh sửa tên, xóa dự án) xuất hiện rõ khi hover.
    * **Thanh cuộn dọc (Scrollbar):** Nếu danh sách các dự án quá dài vượt quá chiều cao vùng hiển thị, khu vực danh sách này sẽ hiển thị thanh cuộn dọc mượt mà (`overflow-y: auto`) để không làm vỡ bố cục chung của Sidebar.
  - **Nút "Xem tất cả":** Nằm dưới danh sách dự án gần đây để chuyển hướng đến trang Quản lý toàn bộ dự án tập trung.
* Không chứa bất kỳ tab chức năng nào của dự án, và không chứa liên kết cài đặt hay đăng xuất hệ thống.

### 2. Horizontal Project Tabs (Thanh Tab chức năng ở giữa)
* Nằm ở phần trên cùng của Cột trung tâm (Center Workspace), ngang hàng với tiêu đề của Chatbot Panel.
* Chứa các tab ngang: "Thư viện Tài liệu", "Bản đồ Tri thức", và "Hỗ trợ viết tổng quan" (tương ứng 1-1 với các User Journeys).
* Khi một tab được nhấp chọn, đường viền dưới màu `{colors.accent-blue}` sẽ hiển thị, đồng thời tải giao diện tương ứng xuống khu vực bên dưới.

### 3. Top-Right Header Utilities Bar (Thanh Header tiện ích góc trên bên phải)
* Nằm ở góc trên cùng bên phải, nền màu `{colors.surface-raised}`, viền dưới `{colors.border-hairline}`.
* Chứa cụm nút chức năng hệ thống: biểu tượng dấu chấm hỏi (`Trợ giúp`), bánh răng (`Cài đặt Hệ thống` - chỉ hiển thị đối với Admin để chuyển hướng đến trang Cài đặt Hệ thống), và biểu tượng thoát (`Đăng xuất`), nằm liền kề với bộ chọn ngôn ngữ `VI | EN` và nút chuyển chế độ sáng/tối.

### 4. Right Resizable & Collapsible Chatbot Panel (Khung Chatbot AI bên phải)
* Biên trái của khung chat chứa một dải kéo giãn rộng 4px, hiển thị con trỏ dạng `col-resize` khi di chuột qua.
* **Tiêu đề panel:** Logo hoặc dòng chữ "Trợ lý nghiên cứu" ở trên cùng.
* **Cụm nút chức năng trên cùng:** Ngay dưới tiêu đề, chứa nút tròn biểu tượng Lịch sử trò chuyện (Chat History) và nút tròn biểu tượng Trò chuyện mới (New Chat) đặt nằm ngang hàng nhau.
* **Popover Lịch sử trò chuyện:** Khi click vào nút Lịch sử, mở ra popover hiển thị danh sách các cuộc hội thoại cũ trong dự án hiện tại, nền màu `{colors.surface-raised}`, viền `{colors.border-hairline}`, bo góc `{rounded.lg}`.
* **Ô nhập tin nhắn (Chat Input):** Được bố trí ngay phía dưới cụm nút chức năng (nằm trên luồng hội thoại). Ô nhập tin nhắn có bo góc `{rounded.md}` và hiển thị dòng gợi ý mờ (placeholder): **"Bạn cần tôi hỗ trợ gì..."**.
* **Các nút hành động gợi ý động (Dynamic Quick Reply Buttons):** Các nút bấm nhỏ bo góc `{rounded.md}`, viền màu `{colors.border-hairline}`, chữ màu `{colors.ink-primary}` nằm ngay phía dưới ô nhập tin nhắn để người dùng click nhanh.
* **Luồng hội thoại (Chat History / Chat Content):** Nằm ở phía dưới cùng, hiển thị lịch sử đối thoại cuộn từ dưới lên với các tin nhắn AI chứa badge trích dẫn `[1]` màu `{colors.accent-blue}`.
* **Nhãn Cảnh báo độ tin cậy thấp (Low-Reliability Warning Label):** Nhãn cảnh báo màu đỏ/cam nhạt nằm ngang trên đầu câu trả lời của AI nếu phát hiện tỷ lệ trích dẫn ảo vượt ngưỡng. Đi kèm biểu tượng dấu chấm than cảnh báo để người dùng lưu ý.

### 5. Cytoscape.js Knowledge Map Canvas (Bản đồ tri thức Cytoscape.js ở cột giữa)
* Nền bản đồ sử dụng `{colors.surface-base}`.
* **Node Toàn văn:** Điểm tròn xanh lá `{colors.state-success}` viền đậm.
* **Node Chỉ siêu dữ liệu:** Vòng tròn nét đứt viền cam vàng `{colors.state-warning}`.
* **Đường `[:CITES]` (Trích dẫn):** Đường nét liền màu `{colors.accent-blue}` có mũi tên định hướng.
* **Đường `[:AUTHORED]` (Tác giả):** Đường nét đứt màu `{colors.accent-violet}`.
* **Tín hiệu cảnh báo khoảng trống/mâu thuẫn (Gap Warnings):** Viền nhấp nháy hoặc vòng tròn đứt nét xung quanh node/cụm có màu đỏ `{colors.state-danger}` (đại diện cho mâu thuẫn học thuật) hoặc màu vàng `{colors.state-warning}` (đại diện cho cụm bị cô lập/khoảng trống tiềm năng).
* **Thẻ thông tin Node (Node Detail Card):** Thẻ thông tin nhỏ trượt ra từ góc trên bên phải của canvas bản đồ, nền `{colors.surface-raised}`, bo góc `{rounded.lg}`, viền `{colors.border-hairline}`.

### 6. Overview Writing Support Workspace (Giao diện Hỗ trợ viết tổng quan ở cột giữa)
* **Thẻ bản thảo (Manuscript Card):** Nền `{colors.surface-raised}`, bo góc `{rounded.md}`, viền `{colors.border-hairline}`.
* **Khung soạn thảo văn bản (Editor Workspace):** Nền trắng giấy ấm, sử dụng font chữ hệ thống `Inter`, cỡ chữ `{typography.body.fontSize}` với khoảng cách dòng thoáng (line-height `{typography.body.lineHeight}`).
* **Nút xuất bản thảo (Export Button):** Nền xanh cobalt `{colors.accent-blue}`, chữ trắng `{colors.surface-raised}`, bo góc `{rounded.md}` nằm ở góc phải phía trên.

### 7. Interactive Citation Tooltip (Hộp thoại trích dẫn thông minh)
* Hộp thoại nổi nhỏ xuất hiện ngay khi hover hoặc click vào ký hiệu trích dẫn `[1]`, `[2]`.
* Nền màu `{colors.surface-raised}`, viền `{colors.border-hairline}`, bo góc `{rounded.lg}` (8px). Bóng đổ nhẹ để tách lớp.
* Chứa text chunk trích dẫn nguồn (chữ cỡ `{typography.body.fontSize}` màu `{colors.ink-primary}`) và siêu dữ liệu tóm tắt (chữ cỡ `{typography.meta.fontSize}` màu `{colors.ink-secondary}`). Nút mở tệp và tải tệp nhanh có viền `{colors.border-hairline}` và chữ màu `{colors.accent-blue}`.

### 8. Interactive Demo Simulator (Khung Demo Giả Lập Tương Tác)
* Bố cục mô phỏng Workspace 3 cột thực tế nhưng thu nhỏ.
* Nền cơ sở giấy ấm `{colors.surface-base}`.
* **Dải băng cảnh báo chạy thử (Mock Mode Indicator):** Dải băng màu vàng `{colors.state-warning}` chạy dọc ở mép của khung hoặc dải thông báo ở đầu, ghi dòng chữ "BẢN CHẠY THỬ / GIẢ LẬP".
* **Node Đồ thị Đỏ nhấp nháy (Gap Alert Node):** Trên sơ đồ Cytoscape.js demo, node khoảng trống nghiên cứu có màu đỏ `{colors.state-danger}` với hiệu ứng hoạt hình vòng tròn tỏa bóng mờ nhấp nháy xung quanh (`animation: pulse 1.5s infinite`).

### 9. Centralized Project Management Page (Trang Quản lý toàn bộ dự án tập trung)
* Bố cục 1 cột trung tâm rộng rãi, hiển thị khi click nút "Xem tất cả".
* Bảng danh sách dự án (Project Table) có đường viền `{colors.border-hairline}`, nền màu `{colors.surface-raised}`, các dòng có hiệu ứng hover mượt mà.
* Các nút CRUD nhanh ở cột thao tác, thanh tìm kiếm và bộ chọn trạng thái có thiết kế bo góc `{rounded.md}` (6px), viền `{colors.border-hairline}`.

### 10. Admin System Settings Page (Trang Cài đặt Hệ thống dành cho Admin)
* Giao diện gồm thanh Tab cấu hình ngang: "Giới hạn hệ thống", "Trích dẫn & AI", "Quản trị người dùng".
* Các trường cấu hình (nhập số hoặc chọn toggle): Giới hạn tài liệu mỗi dự án (`MAX_PAPERS_PER_PROJECT`), Ngưỡng tìm kiếm rộng (`BROAD_QUERY_THRESHOLD`), Ngưỡng lỗi trích dẫn ảo (`CITATION_ERROR_THRESHOLD`), Số lần thử lại tối đa (`CITATION_RETRY_LIMIT`).
* Nút "Lưu cấu hình" nổi bật với nền màu xanh cobalt `{colors.accent-blue}` và chữ trắng.

### 11. New User Onboarding Section (Màn hình Onboarding tích hợp)
* Thiết kế chia hai phần phân tách (Split Layout, tỷ lệ 45% trái và 55% phải).
* Cột trái: Form tạo nhanh dự án, nền `{colors.surface-raised}`, các trường nhập liệu có bo góc `{rounded.md}` (6px), viền `{colors.border-hairline}`.
* Cột phải: Hướng dẫn nhanh dạng thẻ checklist bo góc `{rounded.md}` (6px), viền `{colors.border-hairline}`.

### 12. Project Selector Grid Dashboard (Thẻ dự án Dashboard)
* Nền màu `{colors.surface-raised}` (Light Mode) hoặc `{colors.surface-raised-dark}` (Soft Dark Mode).
* Bo góc `{rounded.md}` (6px), viền mỏng `{colors.border-hairline}`.
* **Hiệu ứng Hover:** Khi người dùng di chuột qua thẻ, thẻ dịch chuyển nhẹ lên trên (`transform: translateY(-2px)`) kết hợp với hiệu ứng đổ bóng mờ (box-shadow) màu xanh nhạt và viền đổi sang màu nhấn xanh cobalt `{colors.accent-blue}`.
* **Nội dung thẻ:** Tên dự án (chữ đậm cỡ `{typography.title.fontSize}` màu `{colors.ink-primary}`), mô tả dự án (chữ cỡ `{typography.body.fontSize}` màu `{colors.ink-secondary}`), nhãn thông số số tài liệu đã nạp (nền nhạt, bo góc `{rounded.sm}`) và thời gian cập nhật.

### 13. Pricing Table (Bảng giá dịch vụ)
* Hiển thị dạng các cột thẻ cạnh nhau: Thẻ gói Sinh viên (Free) và Thẻ gói Nghiên cứu viên (Pro).
* Thẻ Pro được bao quanh bởi một viền màu xanh cobalt `{colors.accent-blue}` và có thêm nhãn nổi "PHỔ BIẾN NHẤT" ở đỉnh thẻ.
* Nút CTA của thẻ Free dùng màu xám viền (`border`), nút CTA của thẻ Pro dùng màu xanh cobalt `{colors.accent-blue}` làm nền với chữ trắng.

### 14. SSE Ingestion Progress Flow (Tiến trình nạp tài liệu bất đồng bộ qua SSE)
* Thanh tiến trình nằm ngang (progress bar) hiển thị dưới từng dòng tài liệu đang được nạp trong Tab Thư viện Tài liệu.
* Màu nền thanh tiến trình dùng màu xám nhạt, phần hoàn thành chạy màu xanh cobalt `{colors.accent-blue}`.
* Văn bản trạng thái chi tiết hiển thị trực tiếp bên cạnh thanh tiến trình, thay đổi động theo sự kiện SSE: *"Đang tải từ internet..."* -> *"Đang quét cấu trúc & OCR..."* (nếu là PDF scan) -> *"Đang nhúng vector..."* -> *"Đã nạp thành công"*.

### 15. Manual Ingestion Metadata Form (Form điền siêu dữ liệu thủ công)
* Giao diện chỉnh sửa tích hợp hiển thị khi người dùng tải lên tệp PDF/DOCX.
* Các trường thông tin (Tiêu đề, Tác giả, Năm, Tóm tắt) có nhãn badge `"AI Suggested"` màu thạch anh `{colors.accent-violet}` (nền nhạt, chữ đậm) hiển thị rõ ràng bên cạnh để chỉ thị dữ liệu do AI tự trích xuất.
* Các ô nhập liệu có thể chỉnh sửa trực tiếp, bo góc `{rounded.md}`.

### 16. Degraded Union API Toast Alert (Thông báo Toast lỗi API)
* Hộp thông báo Toast nhỏ hiển thị ở góc trên bên phải màn hình khi một trong các nguồn API (arXiv hoặc Semantic Scholar) bị lỗi hoặc quá hạn (Rate limit/Timeout).
* Nền màu vàng nhạt, viền màu cam `{colors.state-warning}`, chữ màu xám than sẫm `{colors.ink-primary}`, bo góc `{rounded.md}`, chứa nút đóng nhanh (x).

### 17. Broad Query Interactive Buttons (Thẻ gợi ý phân ngành rộng)
* Hiển thị dưới dạng một danh sách các thẻ nút bấm nằm ngay dưới ô tìm kiếm của Tab Thư viện Tài liệu khi kết quả trả về vượt ngưỡng cấu hình.
* Các thẻ có viền `{colors.border-hairline}`, bo góc `{rounded.sm}`, nền màu `{colors.surface-raised}`, chữ màu xanh cobalt `{colors.accent-blue}`. Khi hover, đổi màu nền sang `{colors.accent-blue}` nhạt.

### 18. Hard Document Limit Error Alert (Cảnh báo lỗi cứng giới hạn tài liệu)
* Hộp cảnh báo lỗi xuất hiện khi dự án đạt giới hạn tài liệu tối đa và người dùng cố gắng nạp thêm.
* Nền đỏ nhạt, viền đỏ `{colors.state-danger}`, chữ `{colors.state-danger}` đậm, hiển thị rõ ràng thông điệp chặn hành động.

### 19. API Keys Management Panel (Bảng quản lý API Keys cá nhân)
* Hiển thị dạng danh sách thẻ (Card) mờ kính (Glassmorphic) cho từng nhà cung cấp API (Gemini, Semantic Scholar, arXiv).
* Trường nhập hiển thị Key mặc định bị che: `••••••••••••••••3a5F`. Click biểu tượng bút chì để chuyển sang input sửa đổi. Nút "Test Connection" hiển thị spinner xoay tròn khi đang chạy và đổi nhãn thành `Testing...`.
* Trạng thái kết nối hiển thị bằng các nhãn Badge trực quan: xanh lá 🟢 `Connected` và dòng chữ `Last Sync: x mins ago`, hoặc màu xám `Not configured`.
* Ảnh tham chiếu trực quan: [mockups/api_key_management_ui.png](file:///home/agent/github/C2-App-053/_bmad-output/planning-artifacts/ux-designs/ux-C2-App-053-2026-06-12/mockups/api_key_management_ui.png).

### 20. First Admin Onboarding Wizard (Luồng thiết lập nhanh cho Admin đầu tiên)
* Hiển thị banner chào mừng màu tím huyền ảo khi phát hiện hệ thống trống (`users_count == 0`), chỉ dẫn rằng tài khoản đăng ký đầu tiên tự động nhận quyền Admin.
* Biểu mẫu thiết lập nhanh (Setup Wizard) gồm 2 thẻ bước: Nhập API Key hệ thống chung, và Cấu hình các giới hạn mặc định ban đầu.


---

## Do's and Don'ts

### Do
* Mặc định hiển thị giao diện sáng (Light mode). Chỉ kích hoạt chế độ tối (Soft dark mode) khi người dùng chủ động click nút chuyển đổi ngôn ngữ/giao diện ở header.
* Cho phép người dùng kéo giãn chiều rộng khung chat bên phải từ 20% đến 40% màn hình để tối ưu hóa không gian đọc văn bản hoặc xem đồ thị ở giữa.

### Don't
* Không dùng màu đen tuyền `#000000` cho chế độ tối, hãy dùng màu xám dịu `{colors.surface-base-dark}` (`#1F2023`) để bảo vệ mắt.
* Không thiết kế chatbot cố định chiều rộng, điều này gây ức chế khi người dùng cần đọc câu trả lời dài của AI hoặc khi cần không gian rộng cho bản đồ đồ thị ở giữa.


