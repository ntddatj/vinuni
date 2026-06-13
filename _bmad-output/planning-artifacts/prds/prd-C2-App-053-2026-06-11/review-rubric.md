# PRD Quality Review — AI Literature Review Assistant (AI20K-031)

## Overall verdict
Tài liệu PRD đạt mức độ hoàn thiện cao, bám sát các yêu cầu thực tế của đề tài AI20K-031 và tích hợp xuất sắc các phản hồi của người dùng. Các tính năng nghiệp vụ cốt lõi được cấu trúc rõ ràng, có sự liên kết chặt chẽ giữa hành trình người dùng (User Journeys) và yêu cầu chức năng (FRs). Trọng tâm kiểm soát trích dẫn (Citation Guardrail) và cấu hình giới hạn hệ thống để bảo đảm hiệu năng LLM được mô tả rất chi tiết.

## 1. Decision-readiness — adequate
Các quyết định về cấu hình API Key cho Semantic Scholar và việc lựa chọn Apache AGE tích hợp trong PostgreSQL đã được làm rõ và đưa vào dạng cấu hình linh hoạt (System Configuration). Các giả định kỹ thuật được lập chỉ mục rõ ràng.

### Findings
- **low** Cấu hình API Key (§8.1) — Cần làm rõ mức giới hạn rate limit của public API Semantic Scholar khi không có key để người dùng dự liệu. *Fix:* Thêm ghi chú về hạn mức mặc định của public API trong tài liệu Kiến trúc.

## 2. Substance over theater — strong
Hành trình người dùng (UJ-1 và UJ-2) rất thực tế, tập trung trực tiếp vào vai trò nghiên cứu của học viên/sinh viên mà không bị rườm rà. Định nghĩa rõ ràng đối tượng mục tiêu.

### Findings
*Không có phát hiện nào ở mức Nghiêm trọng hoặc Cao.*

## 3. Strategic coherence — strong
Tài liệu thể hiện tính nhất quán chiến lược cao. Sự kết hợp giữa RAG và Graph Database (Apache AGE) phục vụ trực tiếp cho mục tiêu cốt lõi là phát hiện khoảng trống nghiên cứu và dựng bản đồ tri thức trực quan. Các chỉ số đo lường (Success Metrics) như tỷ lệ trích dẫn chính xác (SM-1) phản ánh đúng giá trị cốt lõi của Citation Guardrail.

### Findings
*Không có phát hiện nào ở mức Nghiêm trọng hoặc Cao.*

## 4. Done-ness clarity — strong
Các yêu cầu chức năng (FR) đều có hệ quả (Consequences) mô tả trạng thái đầu ra mong muốn rất chi tiết và có thể kiểm thử được (ví dụ: cấp JWT trong HttpOnly Cookie, hiển thị trạng thái xử lý tài liệu, hoặc kiểm chéo DOI trước khi sinh trích dẫn).

### Findings
- **medium** Kiểm thử OCR (§4.2) — Cần xác định rõ hệ thống sẽ dùng thư viện/dịch vụ OCR nào cho Scanned PDF và giới hạn thời gian xử lý. *Fix:* Bổ sung ghi chú kỹ thuật về việc sử dụng công cụ OCR (ví dụ: Tesseract hoặc LLM-based OCR) trong tài liệu addendum/architecture.

## 5. Scope honesty — strong
Phạm vi MVP (In Scope và Out of Scope) được phân tách rõ ràng. Định nghĩa rõ việc hỗ trợ tệp Word (.docx) và PDF tự upload cục bộ. Các mục tiêu ngoài phạm vi (Non-Goals) như việc không bẻ khóa các trang trả phí được nêu rõ để quản lý kỳ vọng của người đánh giá bài tập.

### Findings
*Không có phát hiện nào ở mức Nghiêm trọng hoặc Cao.*

## 6. Downstream usability — strong
Tài liệu định nghĩa phần Glossary (Thuật ngữ) rất đầy đủ và nhất quán với các yêu cầu kỹ thuật bên dưới. Các thuật ngữ "Tài liệu dự án", "Bản đồ Tri thức", "Hệ thống RAG", "Citation Guardrail" được dùng đồng nhất.

### Findings
*Không có phát hiện nào ở mức Nghiêm trọng hoặc Cao.*

## 7. Shape fit — strong
Tài liệu được điều chỉnh hoàn hảo cho một bài tập lớn trường học có độ quan trọng cao. Nó cân bằng giữa tính hàn lâm khoa học ( literature review, citations, graphs) và tính thực tiễn phát triển phần mềm (JWT auth, limits, system configurations).

### Findings
*Không có phát hiện nào ở mức Nghiêm trọng hoặc Cao.*

## Mechanical notes
- Danh sách hành trình người dùng (UJ-1, UJ-2) có nhân vật đại diện (Minh, học viên cao học) rõ ràng và mang tính ngữ cảnh thực tế.
- Các mã định danh FR (FR-1 đến FR-12) đều liên tục và không bị trùng lặp.
