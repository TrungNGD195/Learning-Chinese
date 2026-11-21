# Bộ bản nháp HSK 1–2, ngày 21/11/2026

25 lesson: HSK1 bài 1–15 và HSK2 bài 1–10. Đây là học liệu nháp cần biên tập duyệt, không tự xuất bản.

- Từ vựng HSK1 bài 1–13 và HSK2 bài 1–10: DOCX trong `docs`.
- Từ vựng HSK1 bài 14–15: PDF HSK1 theo yêu cầu bổ sung của PO.
- Bài khóa: trích từ PDF tương ứng, kèm pinyin và bản dịch; các lỗi rõ ràng trong PDF được đối chiếu ngữ cảnh. Ngữ pháp được diễn giải theo các điểm trong giáo trình.
- 649 mục từ/nghĩa; bỏ 34 lượt trùng cả chữ Hán, pinyin và nghĩa, giữ lần xuất hiện đầu. Chỉ chuẩn hóa Unicode, khoảng trắng và kiểu chữ; không gộp tùy tiện các nghĩa khác nhau.
- 72 điểm ngữ pháp, 84 bài khóa. Mỗi lesson có 30 câu, đạt từ 80%, có giải thích; gồm chọn đáp án, điền chữ, nối và sắp xếp câu. Bài sau có thể ôn bài trước. Không có chấm bài tự do bằng AI hoặc chi phí gọi mô hình.
- `source-audit.json`: hash tài liệu nguồn, danh sách lượt trùng đã bỏ, hiệu chỉnh và số lượng mỗi bài. `source_key` và `knowledge_origins` chỉ là metadata biên tập, không truyền vào DTO hiện có.

## Nhập local an toàn

Tại thư mục `backend`, chạy `python -m scripts.import_curriculum_refresh` để kiểm tra offline. `--inspect` đọc database local và trả fingerprint. Muốn nhập cần `--apply --expected-fingerprint <fingerprint> --backup <file-pg_dump>`; chỉ chấp nhận môi trường development và database local `chinese_learning`. Sao lưu thật bằng `pg_dump -Fc`, kiểm tra bằng `pg_restore -l` trước khi nhập. Không đưa backup có dữ liệu người dùng vào Git.

Toàn bộ cập nhật chạy trong một transaction. Giữ ID lesson và các liên kết đã có tiến độ; không xóa tài khoản, lần làm bài hay đáp án cũ. Đề cũ được lưu trữ, đề mới là DRAFT. Chạy lại cùng manifest giữ các chỉnh sửa của admin. Trường hợp cần bỏ học liệu đang có lịch sử mà không ánh xạ được sẽ dừng và rollback.

Admin duyệt ví dụ, pinyin, nghĩa trong ngữ cảnh và đáp án trước khi xuất bản. Đặc biệt, DOCX HSK2 bài 3 ghi `块` trong nhóm nội dung có `快`; bản nháp giữ chữ trong DOCX, cần chủ biên xác nhận ý định trước khi xuất bản.

## Ôn từ vựng

`GET /me/vocabulary-review` chỉ trả các từ trong lesson PUBLISHED có `completed_at` của chính học sinh đang đăng nhập. Hoàn thành lesson vẫn theo cơ chế hiện tại: học đủ lý thuyết và đạt luyện tập. Không cần migration hoặc bảng chép từ riêng. Từ có cùng chữ nhưng khác pinyin/nghĩa là thẻ riêng. Bài nháp hoặc bài đã hủy xuất bản không cung cấp thẻ. Giao diện `/vocabulary-review` có lật thẻ, chuyển thẻ, lọc HSK và phân trang 50 thẻ; không tuyên bố có thuật toán ôn cách quãng.
