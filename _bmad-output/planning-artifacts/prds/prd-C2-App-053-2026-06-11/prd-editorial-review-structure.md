# Báo cáo Đánh giá Cấu trúc Tài liệu (Editorial Review - Structure)

## Document Summary
- **Purpose:** Xác định các yêu cầu sản phẩm cho hệ thống AI Literature Review Assistant (AI20K-031) làm cơ sở triển khai thiết kế và phát triển.
- **Audience:** Người quản trị dự án, Kiến trúc sư hệ thống, Lập trình viên, Nhân viên kiểm thử (QA).
- **Reader type:** humans
- **Structure model:** Strategic/Context (Pyramid)
- **Current length:** ~3400 từ trên 23 phần/mục lớn nhỏ.

## Recommendations

### 1. CONDENSE / MOVE - Chi tiết giao diện kỹ thuật trong Triết lý Thiết kế (Section 1.1)
**Rationale:** Các chi tiết giao diện cụ thể như "Thanh tab nằm ngang", "Sidebar trái hiển thị 5 dự án gần nhất", "biểu tượng đồng hồ lịch sử" hay thuật ngữ kỹ thuật "Client-side State Management" xuất hiện quá sớm ở phần Tầm nhìn và bị lặp lại ở phần Features.
**Impact:** ~150 từ
**Comprehension note:** Giúp phần Tầm nhìn & Triết lý giữ nguyên tính định hướng cấp cao, không bị quá tải bởi các đặc tả chi tiết giao diện.

### 2. CONDENSE / MERGE - Chi tiết giao diện trong Key User Journeys (Section 2.3)
**Rationale:** Key User Journeys (đặc biệt là UJ-2, UJ-3) đang mô tả quá chi tiết về thư viện UI (Cytoscape.js), loại node, và màu sắc nhấp nháy của node, vốn đã được đặc tả kỹ lưỡng trong phần Features (FR-9).
**Impact:** ~80 từ
**Comprehension note:** Giúp các kịch bản trải nghiệm người dùng tập trung vào hành vi và luồng nghiệp vụ của người dùng thay vì cách thức vẽ đồ thị.

### 3. CONDENSE / MERGE - Tóm tắt MVP Scope (Section 6.1)
**Rationale:** Mục "In Scope" đang lặp lại gần như nguyên văn các yêu cầu chức năng (FR) chi tiết từ phần 4 thay vì chỉ liệt kê danh mục tính năng hoặc tham chiếu ngắn gọn.
**Impact:** ~120 từ
**Comprehension note:** Giúp phần phạm vi MVP cô đọng, người đọc dễ dàng nắm bắt các thành phần được đưa vào MVP trong một lượt quét.

### 4. MOVE - Tách biệt phần NFR cho MVP (Section 7.2)
**Rationale:** Các yêu cầu phi chức năng (NFR) hiện đang bị lồng ghép dưới dạng mục con (7.2) của "7. Success Metrics" (Chỉ số thành công), điều này không hợp lý về mặt phân loại.
**Impact:** ~0 từ (chỉ thay đổi cấu trúc vị trí)
**Comprehension note:** Tách phần NFR thành một chương riêng biệt (`## 8. Non-Functional Requirements (NFR) cho MVP`) giúp cải thiện khả năng tra cứu độc lập.

### 5. MERGE - Câu hỏi mở (Section 8) và Chỉ mục Giả định (Section 9)
**Rationale:** Câu hỏi về Semantic Scholar API Limit và giả định ASSUMPTION-1 được trình bày lặp lại gần như y hệt ở hai mục liền kề nhau.
**Impact:** ~30 từ
**Comprehension note:** Tăng tính cô đọng bằng cách tích hợp trực tiếp giả định vào câu hỏi mở hoặc tham chiếu gọn gàng hơn.

### 6. MERGE - Loại bỏ lặp lại quy tắc ánh xạ Thanh tab ngang
**Rationale:** Quy tắc "ánh xạ 1-1 giữa User Journey và Thanh tab ngang, việc thêm bớt phải cập nhật tương thích" bị lặp lại nguyên văn tới 3 lần (tại các phần 1.1, 2.3 và 4.1.FR-2).
**Impact:** ~50 từ
**Comprehension note:** Loại bỏ các câu lặp lại không cần thiết để văn bản mạch lạc và súc tích hơn.

## Summary
- **Total recommendations:** 6
- **Estimated reduction:** ~430 từ (~12.6% tài liệu)
- **Meets length target:** Không yêu cầu giới hạn cụ thể
- **Comprehension trade-offs:** Không có sự đánh đổi tiêu cực nào; việc cắt giảm và tái cấu trúc hoàn toàn giúp tăng tính rõ ràng và mạch lạc cho tài liệu đối với cả người đọc là con người lẫn LLM.
