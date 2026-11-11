# Biên soạn và duyệt bài học

Trang `/admin/lessons/:lessonId` là nơi biên soạn, xem trước và duyệt cả lý thuyết lẫn bài luyện tập:

- Từ vựng, Ngữ pháp, Bài khóa: giữ các trình biên soạn và bản xem trước hiện có.
- Luyện tập: sửa câu hỏi, đáp án, điểm và thông tin bài luyện ngay trong lesson. Chuyển mục hoặc chuyển giữa các bài luyện đã mở giữ nội dung chưa lưu; rời trang vẫn có cảnh báo.
- Duyệt xuất bản: tổng hợp số mục lý thuyết, số câu, số dạng bài và ngưỡng đạt thực tế. Lưu các thay đổi trước khi xác nhận.

`POST /api/v1/admin/lessons/{lesson_id}/publish-package` chỉ dành cho admin. Lesson phải là DRAFT hoặc PUBLISHED, có ít nhất một bài luyện tập đang hoạt động, mỗi bài đủ 30 câu và ít nhất ba dạng. Lesson và các bài luyện DRAFT/REVIEW được xuất bản trong cùng giao dịch; bài đã lưu trữ không tham gia. Bất kỳ lỗi kiểm tra hoặc ghi dữ liệu nào đều không xuất bản dở dang. Gọi lại an toàn, không đổi ngày xuất bản của nội dung đã xuất bản. Pipeline kiến thức chạy sau commit theo luồng hiện có.

`POST /api/v1/admin/lessons/{lesson_id}/unpublish` chuyển PUBLISHED về DRAFT và ẩn lesson với học viên. Giữ nội dung, trạng thái bài luyện, ngày xuất bản trước, tiến độ học và các lần làm bài. Câu hỏi của bài luyện đã xuất bản vẫn chỉ đọc theo chính sách lưu lịch sử hiện có.

Admin quản lý toàn bộ lý thuyết và luyện tập của lesson trong **Bài học**. Mục **Kiểm tra định kỳ** thay thế mục Luyện tập cũ trên điều hướng và tổng quan; thư viện này chỉ truy vấn `PERIODIC_TEST`, không còn luồng tạo hay lọc luyện tập theo lesson.

Thêm bài luyện và tạo 30 câu bằng AI thực hiện ngay trong mục Luyện tập của lesson, tự lấy phạm vi bài học hiện tại. Bản nháp vừa tạo được mở tại chỗ để sửa, không chuyển sang một trang quản lý khác. Ngưỡng mặc định bài luyện giữ 80%; kiểm tra định kỳ giữ chính sách riêng hiện có.

URL biên soạn cũ của bài luyện thuộc lesson chuyển về `/admin/lessons/:lessonId?section=exercises&exercise=:assessmentId`; liên kết tạo cũ có `lesson` chuyển về lesson và mở phần tạo tương ứng. Bài kiểm tra định kỳ tiếp tục có trình biên soạn riêng. API và dữ liệu bài luyện được giữ nguyên.

Lesson 1 HSK 1 (`d84c81ba-57b3-5132-b15e-dee32ed22bbf`) đã được đưa về DRAFT ngày 2026-11-06 theo yêu cầu. Giữ 13 từ, 1 bài khóa, 30 câu hỏi và tiến độ hiện có. Không tự xuất bản lại sau khi triển khai giao diện.
