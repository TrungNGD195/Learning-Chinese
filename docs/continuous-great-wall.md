# Hành trình Trường Thành liên tục

HSK 1 có 15 mốc bài học và bài phát âm ở chân thành; HSK 2 có 10 bài; HSK 3
có 15 bài. Bài kiểm tra định kỳ, khi có trong lộ trình backend, giữ đúng vị trí
và được thêm thành mốc riêng. Không còn chia đoạn 6 bài hoặc chuyển trang đoạn.

Các mốc thiếu trong catalog hiển thị “Sắp có nội dung”, không tạo lesson trong
database và không có đường dẫn vào học. Chỉ mốc thật đã xuất bản, có quyền học
theo trạng thái backend, mới mở lesson/assessment. HSK 2 và 3 tiếp tục được vào
trực tiếp; chỉ HSK 1 giữ điều kiện phát âm. Bộ đếm “Đã hoàn thành X/Y bài” không
tính bài phát âm và kiểm tra định kỳ, không coi bài chưa xuất bản là đã hoàn thành.

Ảnh có lối đi rộng, thành hai bên, các đoạn chân núi/sườn núi/đỉnh núi. Mỗi ảnh
có đường tâm đo riêng. Vị trí con dấu và camera dùng cùng hệ tọa độ ảnh 1024×1536.
Các con dấu được căn theo tâm chính con dấu, không theo tâm cả cụm nhãn chữ.
Khoảng cách được tính theo số mốc, có lề đầu/cuối đủ để căn giữa mốc trên mobile.

Điều chỉnh mật độ: con dấu bản đồ 156px trên desktop, 128px trên mobile;
Khoảng cách hiện tại lấy theo màn hình: 250px giữa tâm con dấu trên desktop,
215px trên mobile, không nhân thêm theo độ phóng cảnh. Phần đường đầu/cuối
còn lần lượt 180/300px trên desktop, 160/260px trên mobile (đã gồm chỗ cho
con dấu và nhãn). Camera chuyển về mốc đầu/cuối trong 96px cuộn cuối để mốc
vẫn nhìn rõ khi không còn đoạn đường trống dài để căn giữa màn hình.
Chiều cao cảnh lấy trực tiếp theo khoảng cách, không làm tròn lên
nguyên tấm ảnh. Mỗi tấm được phân bổ đều trong chiều cao đó; tọa độ đường tâm
và camera cùng đổi về hệ tọa độ ảnh gốc. Bo đứng cạnh con dấu hiện tại để giảm
chiều cao cụm. Vị trí lưu gồm cả chiều cao cảnh để giữ tỷ lệ khi đổi kích thước.

Cuộn trang tự nhiên điều khiển dịch ngang của cảnh theo đường tâm; không chặn
wheel/touch, không xoay/phóng to hoặc ép dừng. Ranh giới ảnh có vùng chuyển camera
mềm. Quỹ đạo camera nội suy cubic giữ dạng, liên tục cả vị trí và tiếp tuyến
qua khúc cua và mối nối ảnh; không đổi tọa độ con dấu. Dịch ngang dùng giảm tốc
theo thời gian (hằng số 80ms), không nảy hoặc ép cuộn dọc. DOM cập nhật transform
bằng requestAnimationFrame và dừng khi đã đến đích, không render React mỗi
frame. Chỉ đọc layout khi có đầu vào mới; lưu vị trí sau khi cuộn nghỉ 180ms
hoặc rời trang. will-change chỉ bật khi camera chuyển động; tab ẩn dừng vòng lặp.
Khôi phục vị trí, focus bàn phím và đổi kích thước định vị ngay để không chờ
camera đuổi theo. ResizeObserver xử lý sidebar/viewport; có phương án resize nếu API không
có. Các ảnh WebP được tải ưu tiên quanh vị trí hiện tại, phần xa tải chậm.

Vị trí được lưu dưới dạng tọa độ cảnh trong sessionStorage theo HSK, giới hạn
tần suất ghi. Không lưu nội dung bài hoặc dữ liệu đăng nhập. Quay về từ lesson
và reload giữ vị trí khi catalog không thay đổi; “Về bài đang học” định vị lại.
Đường dẫn đoạn cũ vẫn mở trang liên tục, không làm biến mất các bài.

Chế độ danh sách luôn khả dụng; người bật prefers-reduced-motion mặc định dùng
danh sách. Các mốc có thể truy cập bằng bàn phím, focus mốc sẽ đưa camera về nó.
Mốc chưa mở có thông tin giải thích, không cấp quyền học bằng frontend.

Kiểm tra: journeyData/wallGeometry unit tests, các luồng học/phát âm/router và
`frontend/scripts/verify-great-wall-production.mjs`. Script browser giả lập API,
không sửa tài khoản hay tiến độ thật, kiểm tra 15/10/15 bài và mọi mốc ở 4 độ rộng,
camera, quay lại lesson, reload, danh sách và catalog trống.
