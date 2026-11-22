# Hanfolio — đề thi thử HSK 3.0

Ba bộ câu hỏi tự biên soạn, phiên bản 2026-11-22. Chỉ mô phỏng bài thi viết trên máy tính; không có HSKK/phần nói. Không sao chép hoặc phân phối lại đề, tranh hay bản ghi chính thức.

| Cấp độ | Nghe | Đọc | Viết | Tổng | Thời gian làm bài và kiểm tra đáp án nghe |
|---|---:|---:|---:|---:|---:|
| HSK 1 | 20 | 20 | 0 | 40 | 12 + 3 + 20 = 35 phút |
| HSK 2 | 25 | 25 | 10 | 60 | 17 + 3 + 25 + 10 = 55 phút |
| HSK 3 | 30 | 30 | 10 | 70 | 23 + 5 + 30 + 20 = 78 phút |

Không cộng 5 phút khai thông tin cá nhân vào đồng hồ. Đối chiếu cấu trúc ngày 2026-11-22 từ CTI: [HSK 1](https://www.chinesetest.cn/HSK/1), [HSK 2](https://www.chinesetest.cn/HSK/2), [HSK 3](https://www.chinesetest.cn/HSK/3) và gói đề mẫu HSK 3.0 được liên kết trên các trang này.

## Các điều chỉnh có chủ đích cho web

- Câu hỏi, các phương án và tranh được trình bày từng câu; nhóm ghép hình/chọn lời đáp dùng các lựa chọn ngay tại câu. Giữ số phần và số câu; không mô phỏng nguyên trang giấy hoặc phát một bản thu liên tục.
- Phần nghe dùng giọng Mandarin của trình duyệt đã được sử dụng trong bài học. Không gọi TTS trả phí. Chất lượng phụ thuộc giọng được cài trên thiết bị. Nút nghe có tối đa hai lượt trong màn câu hỏi; đây là hỗ trợ thi thử, không phải hệ thống chống gian lận/phòng thi được giám sát.
- HSK 1–2 có pinyin hỗ trợ; HSK 3 không có pinyin ở nghe/đọc. Giữ gợi âm bắt buộc tại 5 câu viết chữ HSK 3 theo quyết định của PO.
- HSK 2 có phần chọn thành phần chữ và điền chữ theo gợi âm. Giao diện nhập chữ Hán thay cho viết tay.
- Năm câu viết câu theo tranh của HSK 3: đáp án mẫu, tiêu chí, và tự đánh giá 0 / 0,5 / 1. Kết quả luôn ghi rõ có phần tự chấm; trước khi tự đánh giá xong chỉ có khoảng điểm và chưa kết luận đạt.
- Mỗi kỹ năng quy đổi tuyến tính về 100 điểm; đạt ngưỡng tham khảo 60% tổng. Đây không phải cách chuẩn hóa điểm/chứng chỉ chính thức. Ngưỡng bài luyện tập trong lesson vẫn 80%.

## Lưu trữ và bảo mật

`hsk_exam_attempts` lưu riêng từng lượt, snapshot bộ đề (chứa đáp án, chỉ backend đọc), đáp án đã chọn, thứ tự đã đảo, hạn giờ từng phần, kết quả và phần tự chấm. Không dùng lượt thi để khóa cấp độ hoặc thay tiến độ học hiện tại.

Bài thi chỉ mở khi tất cả lesson của HSK tương ứng đã có `completed_at` từ luồng hoàn thành lý thuyết và đạt luyện tập. Kiểm tra cả trên giao diện và backend, gồm tạo/tiếp tục lượt và thao tác với lượt đang làm. HSK 1/2/3 phải có đủ 15/10/15 bài đã xuất bản trong giáo trình; thiếu bài hoặc bài còn nháp không được mở sớm. Các bài thêm đã xuất bản trong giáo trình cũng phải hoàn thành. Kết quả các lượt đã nộp vẫn được giữ và xem lại. Không bắt học HSK khác để mở bài thi của cấp độ này.

Seed đảo gồm UUID tài khoản và UUID lượt làm. Giữ ranh giới kỹ năng/phần; đảo câu độc lập trong mỗi phần và đảo phương án bằng ID ổn định. Tải lại tiếp tục cùng đề. Cập nhật JSON chỉ ảnh hưởng lượt mới.

API chỉ trả câu của phần đang mở, không trả đáp án/giải thích trước khi nộp. Chỉ chủ lượt thi có quyền đọc/ghi. Hết giờ được tính trên server, kể cả khi đóng tab hoặc mất mạng. Đóng phần là thao tác idempotent theo chỉ số phần; không quay lại sửa phần đã đóng. Câu bỏ trống = 0.

Phản hồi lesson dùng `practice_responses`: lưu lần trả lời đầu của mỗi câu trong lượt làm, rồi trả đáp án câu đó; không có phản hồi tức thì cho periodic test hoặc bài thi HSK. Nộp bài không được thay các câu đã kiểm tra thành đáp án khác để nâng điểm. Các bảng kết quả và progress cũ được giữ nguyên.

## Bảo trì

JSON là học liệu dùng lúc chạy. `scripts/build_hsk_mock_exams.py` là nguồn biên soạn và tạo lại pinyin khi cần (cần `pypinyin` ở môi trường biên soạn, không phải dependency runtime). Không tạo câu hỏi hoặc gọi LLM khi học sinh mở đề. Đổi nội dung sẽ tạo hash phiên bản mới; snapshot lượt cũ không đổi.
