# HSK1: bản nháp bài 2–5

Danh sách từ và bài luyện đã được cập nhật theo yêu cầu ngày 08/11/2026;
xem [bản cập nhật hiện tại](hsk1-content-revision-2026-11-08.md). Phần dưới
ghi lại phạm vi của lần biên soạn ban đầu, trước đợt chỉnh sửa đó.

Biên soạn từ giáo trình có sẵn `docs/HSK1 3.0 Hanu 24.6.26.pdf`; bỏ phần phát âm. Nội dung đọc trong bài được giữ theo hội thoại giáo trình, chuẩn hóa ký tự Hán tương thích và lỗi nhãn bài khóa. Bài 4 hội thoại 1 sửa nhãn người trả lời cuối thành Vương Nhất Tuyết theo bản dịch; bài 5 chuẩn hóa số ngày sang chữ Hán và bỏ dấu câu lặp. Ví dụ, lưu ý và 120 câu luyện được soạn cho web, không sao chép bài tập phát âm.

| Bài | Nội dung | Từ vựng | Ngữ pháp / mẫu câu | Bài khóa | Luyện tập |
| --- | --- | --- | --- | --- | --- |
| 2 | 我叫小丽 · Tôi tên là Tiểu Lệ | 16 | 3 | 4 | 30 câu |
| 3 | 我是越南人 · Tôi là người Việt Nam | 33 | 4 | 3 | 30 câu |
| 4 | 我有两个孩子 · Tôi có hai đứa con | 33 | 5 | 3 | 30 câu |
| 5 | 今天几月几号？ · Hôm nay là ngày mấy tháng mấy? | 32 | 4 | 3 | 30 câu |

Phạm vi bao gồm từ mở rộng hiện ngay trong giáo trình: 没事 ở bài 2; các tên nước và từ giải thích ở bài 3; bảng số ở bài 4; đồ ăn, thức uống minh họa ở bài 5. Tên nhân vật giữ trong bài khóa, không tạo từ mới riêng. Bài 2 diễn giải ba mẫu câu từ phần tổng kết mẫu câu, không gán là một mục ngữ pháp nguyên văn của giáo trình.

Mỗi từ có chữ Hán, pinyin, nghĩa, loại từ, câu ví dụ đủ ba dòng và lưu ý dùng từ khi cần. Không có ghi nguồn trong lưu ý. Hình minh họa chọn theo từ hoặc ngữ cảnh; nhân vật là gấu trúc. Nguồn vẫn lưu trong manifest và trường quản trị, không thêm phần ghi nguồn vào giao diện học viên.

Mỗi bài có 10 câu chọn đáp án, 8 điền từ, 6 nối cặp và 6 sắp xếp câu. Mỗi câu 1 điểm, đạt 24/30 (80%). Những câu sắp xếp có nhiều trật tự tự nhiên được ghi rõ trật tự yêu cầu; câu nối cặp không dùng hai nghĩa giống nhau trong cùng nhóm. Cơ chế phải học hết từ vựng, ngữ pháp và hoàn thành các bài khóa trước khi luyện vẫn dùng luồng hiện có; các lần làm và kết quả vẫn được lưu.

Nhập bằng `backend/scripts/create_hsk1_lessons_02_05_drafts.py`, mặc định chỉ kiểm tra; `--apply` tạo các bản thiếu trong một giao dịch. Không ghi đè bản đã sửa; xung đột số bài hoặc nhập dở dang dừng cả đợt. Các bài và bài luyện đều là DRAFT, chưa hiển thị cho học viên. Đã đối chiếu fingerprint toàn bộ nội dung, bài luyện và lịch sử liên quan Lesson 1 trước/sau đợt nhập, giữ nguyên.

- Bài 2: `6dd3ff5e-4cdd-5f69-a751-a3567d1b2abe`
- Bài 3: `d350b571-582e-59ae-b66c-dbb7c3c77c17`
- Bài 4: `198801d1-89b1-5c0e-8c9d-5b78934ee788`
- Bài 5: `1db6d24e-7328-5544-a1b3-ef06bd006fe3`

Admin bỏ mục Lộ trình riêng khỏi sidebar. Chức năng còn cần để sắp thứ tự bài học và bài kiểm tra chuyển vào **Bài học → Sắp xếp HSK**, URL `/admin/lessons?view=curriculum`. URL cũ chuyển tới đây. Cơ chế hành trình và mở khóa học viên được giữ.
