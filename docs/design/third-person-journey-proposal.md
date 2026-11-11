# Đề xuất hành trình góc nhìn thứ ba cùng Bo

Trạng thái: đã được người dùng duyệt và triển khai. Chi tiết hành vi thực tế,
tài sản và kiểm chứng ở `docs/third-person-great-wall.md`. Người dùng đã
chọn cuộn để Bo đi, kết hợp bấm cổng để đến nhanh. Storyboard minh họa phương án
mây: `.impeccable/proposals/third-person-bo/storyboard-v1.png`; đây là tranh ý
tưởng, không phải ảnh chụp một tính năng hoạt động. Trang bài học trong khung 4
chỉ minh họa khoảnh khắc chuyển cảnh, không phải đề xuất thay toàn bộ layout lesson.

## Bố cục và cảnh

Camera ở sau và cao hơn vai Bo, hơi chếch để nhận ra sừng, bờm, túi và đuôi.
Bo chiếm khoảng 18–22% chiều cao cảnh, nằm trong một phần ba dưới màn hình.
Camera nhìn ra một cổng chính và 1–2 cổng xa trên đường uốn qua sườn núi. Góc
quay nhỏ, không rung theo bước chân hoặc tự xoay để khoe cảnh.

Biển tên bài nằm trên hoành phi; khoảng giữa cổng mở để nhân vật đi qua. Khi
đến gần mới hiện rõ tên/trạng thái bài. Cổng hiện tại có ánh đèn ấm; cổng đã
xong có dấu hoàn thành; cổng khóa/chưa xuất bản có ký hiệu rõ, không tạo quyền
học mới. Người dùng vẫn xem được lộ trình dự kiến.

Không gian chuyển nhẹ qua chân thành có thông, khúc cua qua thung lũng và đỉnh
thành có chòi canh. Mây xa trôi chậm, một ít cành thông và đèn lồng chuyển động
theo gió. Không bật đồng thời nhiều hiệu ứng quanh nhân vật và chữ bài học.
Trúc/Bút xuất hiện ở vài điểm nghỉ, chỉ có lời nhắc khi người dùng chủ động bấm.

## Chuyển động nhân vật

| Trạng thái | Chuyển động đề xuất |
|---|---|
| Đứng chờ | Thở nhẹ, chớp mắt thưa, đuôi thả lỏng; không nhún nảy liên tục. |
| Bắt đầu đi | Chuyển trọng tâm, nghiêng thân nhẹ rồi bước; tăng tốc khoảng 150–200ms. |
| Đang đi | Chân đặt trên mặt đá, tay/bờm/túi/đuôi đi theo nhịp; vòng bước đồng bộ quãng đường. |
| Ngừng cuộn | Giảm nhịp và đặt chân xuống trong khoảng 200–300ms, không trượt thân trên đường. |
| Vào cua | Thân và đầu hướng theo đường; đuôi theo sau một nhịp. Camera vào cua chậm và ổn định. |
| Quay lại | Bo quay người đi về phía bài cũ; camera lùi theo, giữ hướng cảnh để tránh xoay toàn màn hình 180 độ. |
| Đến cổng | Bo dừng lệch nhẹ khỏi lối giữa, ngoái lại và đưa tay mời. |
| Hoàn thành bài | Bo quay về cổng, mừng ngắn; trạng thái hoàn thành chỉ cập nhật từ backend. |

Cuộn chỉ di chuyển, không tự vào bài. Một lần bấm cổng bài khả dụng thực hiện
chuỗi đi tới cổng và vào bài. Khi chọn bài xa, dùng chuyển vị trí bằng mây ngắn,
không bắt người dùng xem nhân vật chạy hết lộ trình. Tổng quan cho phép chọn bài
nhanh. HSK 1/2/3 giữ số bài 15/10/15, phát âm và kiểm tra thật như hiện tại.

## Hai phương án chuyển cảnh

A — Mây qua cổng (đề xuất): cổng phản hồi ánh sáng, Bo bước qua ngưỡng, mây màu
ivory từ cạnh thành/khung cổng phủ một nhịp rồi tách ra để lộ lesson. Camera chỉ
tiến gần nhẹ. Tổng mục tiêu khoảng 0.8–1 giây, rút còn 0.5–0.7 giây khi ôn bài.
Khi quay lại lộ trình dùng mây đảo chiều, Bo đứng tại cổng vừa học.

B — Cuộn thư mở bài: Bo lấy cuộn thư từ túi trước cổng, mở ra; mặt giấy mở rộng
thành vùng nội dung lesson. Khoảng 0.6–0.8 giây, ít che cảnh hơn, sắc thái học
thuật rõ hơn nhưng cảm giác bước qua không gian nhẹ hơn phương án A.

Nội dung được tải trước khi đến gần cổng, chỉ đọc dữ liệu hợp lệ, không ghi tiến
độ. Nếu dữ liệu chưa sẵn sàng, hiển thị trạng thái tải rõ; không lặp bước chân
hoặc mây vô hạn. Bấm liên tiếp không xếp hàng các hoạt cảnh. Giảm chuyển động
dùng đổi cảnh/mờ ngắn; tổng quan luôn có để bỏ qua cảnh di chuyển.

## Hình ảnh và tính khả thi

Bo hiện tại là bộ ảnh tĩnh nhiều tư thế; cần bộ nhân vật chuyển động mới, gồm
góc sau, sau lệch trái/phải, chính diện và các trạng thái ở bảng trên. Ưu tiên
model 3D có rig, bề mặt vẽ và hình khối mềm giữ đúng nhận diện; phương án nhẹ hơn
là hoạt ảnh 2.5D đa hướng được vẽ đủ chu kỳ. Không coi việc dịch chuyển cả PNG
là một chu kỳ đi bộ.

Cần thêm hình cho cổng mở/trạng thái đèn, mây có nền trong suốt, chi tiết cây/
đèn lồng và lớp núi có chiều sâu. Phải kiểm tra chuyển động và chất lượng của Bo
trong một đoạn đường ngắn trước khi phủ toàn bộ lộ trình.

Storyboard được tạo bằng công cụ tích hợp `image_gen`, tham chiếu trực tiếp bộ
nhân vật hiện tại và ảnh chụp hành trình hiện tại. Prompt đầy đủ:
`.impeccable/proposals/third-person-bo/storyboard-v1.prompt.txt`.
