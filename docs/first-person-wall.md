# Hành trình leo Trường Thành — không gian liên tục ở local

Yêu cầu mới nhất giữ phong cách tranh và Bo, nhưng thay cách di chuyển trên
mặt tranh bằng góc nhìn của người leo theo sau Bo trên một đường ngoằn ngoèo.

`firstPersonRoute.ts` xác định một đường tâm duy nhất trong tọa độ thế giới.
Bậc, hai tường thành, cổng và camera đều dùng đường đó. Một lệnh di chuyển
tương ứng 1,8 đơn vị chiều dài; 6 nhịp tới cổng kế tiếp thay cho 10 nhịp trước
đó. Tốc độ bước thực tế được giữ nguyên; các chiếu nghỉ vẫn trên cùng đường.
Camera nâng dần tầm mắt và quay theo đoạn đường phía trước với góc nhìn cố định
54° ở màn ngang, 64° ở màn dọc. Qua cổng giữ nguyên quãng đường, không lấy phần
dư của tiến trình và không đặt lại cảnh.

`createIllustratedClimbScene.ts` dựng bậc, mặt tường, địa hình và vị trí cây
trong không gian 3D. Cảnh gần đổi phối cảnh nhanh hơn núi xa khi camera tiến
và đổi hướng. Nền núi không chứa đường vẽ sẵn để tránh tạo cảm giác rẽ nhánh.
Vật liệu và cây/cổng dùng lại các tài nguyên minh họa hiện có. Mỗi cây dùng
một mặt ảnh luôn hướng về camera, xoay quanh gốc cố định để tránh lộ cạnh mỏng
của các mặt ảnh cắt nhau; cây vẫn có vị trí và phối cảnh trong thế giới. Bo dùng tám
khung hình hoạt họa trên một mặt ảnh đặt trong thế giới; đây chưa phải nhân
vật 3D có bộ xương chuyển động.

Cổng giữ độ đục đầy đủ trước khi camera qua mặt phẳng cửa. Mây có vị trí trong
không gian, nhẹ hơn và dạt sang hai bên khi tới gần. Theo yêu cầu mới, các cổng
phía trước có bóng mờ từ xa và tăng độ rõ theo khoảng cách, không đợi qua cổng
trước mới được hiện. Cổng gần rõ hoàn toàn trước cửa. Cổng vừa đi qua mờ dần
trong 2,5 đơn vị tiếp theo; không dùng màn mây phủ toàn cảnh cho bước đi thường.
Định vị nhanh và vào bài vẫn dùng chuyển cảnh mây không chữ hiện có.

`ReferenceWallJourney` giữ riêng mục tiêu bước và vị trí camera đang hiển thị.
Tên bài/nút vào bài đổi theo vị trí thực sự đang xem. Quyền học, xuất bản,
điểm và hoàn thành bài vẫn lấy từ API. Đi dạo không ghi tiến độ học tập.
HSK 1 có 15 bài cùng cổng phát âm; HSK 2 có 10 bài, HSK 3 có 15 bài.

Sau cổng cuối HSK 1 và HSK 2 là tháp canh bằng đá, cùng vật liệu của tường,
có cửa vòm tối và bảng tên HSK kế tiếp. Thêm ba bậc sau cổng cuối sẽ đưa Bo
vào cửa: nhân vật khuất trong tháp rồi chuyển cảnh mây không chữ sang đầu
chặng tiếp theo. Hai đoạn đường dành cho tháp nối vị trí thế giới của hai
cấp; camera sang chặng mới nằm phía sau lối ra tháp. Chỉ thực hiện chuyển
cấp khi có HSK kế tiếp trong dữ liệu, không tự tạo HSK 4. Vị trí quay lại được
giữ ngoài cửa tháp để nút Back không gây vòng lặp chuyển trang.

Di chuyển chỉ dùng phím ↑ / ↓, mỗi lần nhấn một bậc. Cuộn chuột, trackpad,
phím trái/phải và giữ phím lặp không làm Bo đi. Khung tên bài giữ liên kết mở
bài, có ký hiệu phím thay cho các nút di chuyển bằng chuột. Đi vào tháp không
ghi điểm hoặc tự đánh dấu hoàn thành bài học.

Vòng vẽ dừng khi đứng yên, ẩn tab hoặc ra khỏi màn hình. Pixel ratio tối đa
1,5; giảm chuyển động chuyển đến vị trí đích mà không chạy camera. Khi không
có WebGL vẫn vào được bài bằng nút tên bài và danh sách toàn lộ trình.

Sidebar cố định theo cửa sổ, không bị kéo theo trang. Phần cảnh dùng phần
chiều cao còn lại sau thanh công cụ, thông báo thật và thanh điều hướng; bỏ
chiều cao tối thiểu gây tràn ở cửa sổ thấp và phần chừa dư ở cuối điện thoại.
Danh sách toàn lộ trình vẫn được cuộn để xem hết bài.

Kiểm chứng tự động: `firstPersonRoute.test.ts` kiểm tra tính liên tục, hướng,
độ cao và quy tắc mây/cổng; `verify-first-person-wall.mjs` ghi video, chuỗi
khung hình và tọa độ camera/cảnh tại desktop, tablet và điện thoại. Bằng chứng
ở `.impeccable/review/first-person-wall/`. Kiểm tra headless không xác nhận
FPS trên GPU của người dùng. Chưa deploy.

`verify-journey-tower.mjs` kiểm tra tháp HSK 1 → 2 → 3, Bo khuất trong cửa,
điểm đến đầu chặng, Back, giảm chuyển động và điều khiển chỉ bằng bàn phím.
Video, ảnh và kết quả ở `tmp/journey-tower/`; dữ liệu học dùng fixture khi
kiểm tra trình duyệt, không thay đổi tài khoản hay tiến độ thật.

Đã kiểm tra lại trên frontend local chính ở cổng 5173 bằng
`node scripts/verify-journey-tower.mjs --reduced-only`; kết quả và ảnh ở
`tmp/journey-tower-primary/`. Lượt chuyển động thường có video ở thư mục
`tmp/journey-tower/`. Trạng thái đến đầu chặng được giữ trong lúc router tải
chậm và chỉ bỏ khi người dùng di chuyển hoặc định vị lại bài; đồng hồ ngắt
chờ không được hủy trạng thái đó sau khi đã giao điều hướng cho router.
