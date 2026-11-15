# Khám phá thêm trong từ vựng

Giao diện local đặt khung viết nét bên trái, thông tin từ và ví dụ ở giữa,
ảnh minh họa cùng block khám phá ở bên phải. Loại từ đứng trên nghĩa tiếng Việt.
Màn hình hẹp sắp xếp lại các vùng, giữ luyện viết thu gọn theo hành vi hiện có.
Mọi từ dùng cùng component và khung ảnh vuông theo kích thước màn hình, kể cả
ảnh số, quốc kỳ, gia đình và từ chưa có ảnh. Từ chưa có ảnh giữ khung với nhãn
thông báo, không bỏ cột làm thay đổi bố cục. Nội dung dài được xuống dòng và
tăng chiều cao tự nhiên, không cắt nghĩa, ví dụ hoặc lưu ý để ép bằng chiều cao.

Toàn bộ block khám phá là một button, không có button/link lồng bên trong.
Popup đọc thêm nằm giữa màn hình, có giới hạn chiều rộng/chiều cao, hỗ trợ
Escape, nút đóng, bấm ngoài và trả focus về block đã mở. Nguồn tham khảo thu
gọn; không có câu hỏi, điểm, checkbox hoàn thành hoặc điều kiện mở bài.

Nội dung hiện tại là hai mẫu biên tập có nguồn cho `你` và `饺子` tại
`frontend/src/features/lesson/vocabularyDiscoveries.ts`. Từ chưa có nội dung
không hiện block khám phá. Đây chưa phải nội dung do RAG/LLM tạo hoặc thư viện
được quản trị qua admin; API/DTO và database không đổi. Không dùng phần khám
phá để thay thế ví dụ hoặc lưu ý sử dụng từ.

Chưa triển khai giao diện lưu/duyệt nội dung khám phá. Nếu mở rộng sau này,
cần thiết kế quyền biên soạn, nguồn, duyệt/xuất bản và phạm vi gắn với từ/bài
trước khi thay thế dữ liệu mẫu bằng backend. Không tự gọi provider khi learner
bấm block; phát sinh chi phí AI cần yêu cầu riêng.

Kiểm tra giao diện bằng `frontend/scripts/verify-vocabulary-discovery.mjs`
với API fixture cô lập, không ghi dữ liệu thật; kiểm tra luồng học hiện hữu
bằng `frontend/scripts/verify-vocabulary-pages.mjs`.
