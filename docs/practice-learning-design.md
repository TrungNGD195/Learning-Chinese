# Luyện tập HSK1: nội dung và bố cục

Bộ đề mới nằm trong `backend/content/hsk1/lesson-01-practice.json` đến
`lesson-05-practice.json`. Bộ nhập bài 2–5 dùng cùng nội dung câu hỏi; manifest
bài 1 cũ được giữ để tương thích quy trình nhập và nâng cấp ban đầu.

Mỗi bài có 30 câu, 30 điểm tối đa, ngưỡng đạt 80%:

| Hoạt động | Số câu |
| --- | --- |
| Nghe từ / câu và chọn ý nghĩa | 4 |
| Chọn từ theo hình và gợi ý | 4 |
| Chọn câu / từ theo ngữ cảnh, phân biệt ngữ pháp | 4 |
| Nối từ với nghĩa | 4 |
| Điền từ | 6 |
| Sắp xếp câu | 4 |
| Đọc đoạn ngắn / hội thoại và trả lời | 4 |

10 câu cơ bản, 14 vận dụng, 6 thử thách. Bài 2–5 có 6 câu ôn bài trước;
15 câu trọng tâm ngữ pháp phân bố cả nghe, chọn ngữ cảnh, điền và sắp xếp.
Bài 1 không tự thêm bài kiểm tra ngữ pháp ngoài lý thuyết đã dạy, tập trung
chữ, nghĩa và cách ghép/lời chào đã học. Mức độ là phân loại biên soạn,
chưa được hiệu chỉnh bằng dữ liệu học sinh thực tế.

`config.presentation` chỉ chứa dữ liệu trình bày: kỹ năng, trọng tâm, mức độ,
cờ ôn tập và nội dung nghe/hình/đọc. Khóa đáp án và lời giải không được gửi
trong payload làm bài. Nghe dùng giọng Quan thoại của thiết bị, không tự phát;
có bản chữ thay thế khi thiết bị không hỗ trợ. Đây không phải chấm nói/phát âm.
Hình kèm gợi ý ngữ cảnh, không khẳng định mọi từ trừu tượng có minh họa trực tiếp.

Đáp án lựa chọn, thứ tự mục nối và mảnh câu được xáo trộn ổn định theo lượt làm.
Không đổi ID đáp án hoặc xáo lại sau mỗi lần chọn. Nối cặp tính điểm theo tỷ lệ
cặp đúng; `is_correct` chỉ đúng khi toàn bộ cặp đúng. Lịch sử cũ giữ nguyên điểm
đã ghi nhận. Các dạng khác giữ cách chấm hiện có, bao gồm đáp án điền được chấp nhận.

Lời giải khách quan dùng trường `rubric` hiện có, được lưu vào feedback khi chấm;
không cần migration database. Kết quả hiển thị lựa chọn đã chọn, đáp án đúng,
lý do và bộ lọc câu cần ôn. Admin có thể sửa lời giải và dữ liệu trình bày trong
trang biên soạn. Prompt sinh câu hỏi v3 cũng yêu cầu lời giải tiếng Việt và
phân bổ cả từ vựng lẫn ngữ pháp; tính năng AI trên production vẫn theo cấu hình
triển khai hiện có, không được tự bật bởi thay đổi này.

Giao diện giữ bảng số câu ở bên trái trên desktop; trên màn nhỏ là dải cuộn
ngang. Tiêu đề gọn, không có ảnh bìa lớn; vùng chính dành cho câu hỏi và đáp án.
Màn kết quả tập trung vào phần sửa lỗi. Câu trả lời được giữ trong bộ nhớ khi
chuyển câu; không có cam kết tự lưu khi reload/đóng tab.

Script bảo trì `backend/scripts/update_lesson_practice.py` chỉ thay câu hỏi khi
snapshot còn khớp và đề không có lượt làm. Giữ nguyên lý thuyết, ID và trạng thái
bài/đề; bài 2–5 vẫn nháp. Nếu có lịch sử, toàn bộ giao dịch dừng trước khi ghi;
không xóa hoặc thay nội dung của lượt đang làm.
