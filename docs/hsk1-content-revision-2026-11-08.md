# Cập nhật nội dung HSK1 bài 2–5

Danh sách do người dùng xác nhận ngày 08/11/2026 thay thế phạm vi từ vựng cũ.
Bài 2 lấy đúng 15 từ đã chỉnh trên bản chạy tại máy, bổ sung thông tin cho 们
và 名字. Bài 1 giữ nguyên.

| Bài | Thẻ từ | Ngữ pháp / mẫu câu | Bài khóa | Luyện tập |
| --- | --- | --- | --- | --- |
| 2 | 15 | 4 | 4 | 30 câu |
| 3 | 30 | 6 | 3 | 30 câu |
| 4 | 42 | 8 | 3 | 30 câu |
| 5 | 31 | 6 | 3 | 30 câu |

中文/汉语, 老公/丈夫, 老婆/妻子 và 日/号 được tách thành thẻ riêng để
phát âm và hiển thị nét viết từng từ. Lưu ý giải thích quan hệ tương đương
và khác biệt khi dùng, không coi dấu gạch chéo là một chữ Hán.

Mỗi từ có pinyin, nghĩa, loại từ, ví dụ cả câu với bản dịch và pinyin. Lưu ý
chỉ ghi khi có thông tin sử dụng cụ thể. Theo yêu cầu bổ sung cùng ngày,
thành viên gia đình dùng minh họa người chibi; các hoạt động khác giữ gấu trúc
và đồ vật. Bốn ông bà có chân dung riêng và nhãn giải thích quan hệ nội/ngoại;
ảnh ngữ cảnh không thay thế định nghĩa của từ. Bổ sung ngữ pháp
về 们; 这/那/哪/谁; 还/太/想; 几/多少; 和/包括; tình trạng hôn nhân; thời gian;
sở thích và ăn uống. Giữ nguyên bài khóa từ giáo trình.

Mỗi đề: 10 câu chọn đáp án, 8 điền từ, 6 nối cặp, 6 sắp xếp câu. Trong đó
24 câu trọng tâm bài hiện tại, 6 câu ôn bài trước, đạt từ 24/30 (80%).
Cơ chế xem hết lý thuyết và lưu mọi lần làm giữ nguyên. Sinh đề từ admin
cũng có thể lấy kiến thức bài trước cùng HSK, không lấy bài sau hoặc bài lưu trữ.

`backend/scripts/revise_hsk1_lessons_02_05.py` áp dụng bản sửa trong một giao dịch,
đối chiếu snapshot trước khi ghi và từ chối nếu bài/đề không còn nháp, nội dung
đã thay đổi hoặc đã có lịch sử học/làm bài. Giữ ID bài, thẻ còn dùng và bài khóa;
không cập nhật bản ghi từ vựng/ngữ pháp dùng chung với bài khác. Snapshot trước
và sau nằm trong thư mục `tmp` bị bỏ qua bởi Git. Không tự xuất bản bài 2–5.
