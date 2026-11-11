# Chuỗi leo thành từ các cảnh minh họa — bản lịch sử

**Đã được thay thế.** Người dùng nhận xét bản 2.5D vẫn thiếu cảm giác thật sự
leo lên và đổi góc nhìn. Renderer đang hoạt động được mô tả trong
[first-person-wall.md](first-person-wall.md). Các kiểm chứng và kết luận dưới
đây chỉ áp dụng cho bản cũ, không xác nhận trải nghiệm hiện tại.

Người dùng đã sửa lại yêu cầu: ba ảnh là các mốc hành động của một chuỗi leo
thành, không phải ba ảnh để đổi qua lại. Renderer hiện tại tách Bo, bóng tiếp
xúc và cổng khỏi phần nền; giữ các nút học, sidebar và quyền truy cập từ API.

Ba cảnh tham chiếu được dùng cùng nhau để tạo một tranh nền thống nhất bằng
công cụ imagegen tích hợp. Nền mới có cùng phong cách, chứa bậc thang, chiếu
nghỉ, đoạn cua và khoảng đặt cổng trong một phối cảnh. Runtime chỉ dùng một
tranh với phép chiếu camera; không còn hòa ảnh hay optical flow làm tường/cây
bị chồng nét. Những file nguồn tham chiếu cũ được giữ nguyên.

Bo dùng atlas tám khung đi lên/đi xuống và atlas mới tám tư thế quay từ phía
sau; không đổi sang dáng nhìn chính diện chỉ tay. Pha chân phụ thuộc quãng
đường, dừng thì giữ chân đã đặt xuống. Bóng bám gốc chân; Bo đặt chân cố định
khi quay người, sau đó bước qua khúc cua. Camera theo
độ cao, độ phóng đại và hướng của chuỗi; các mốc trong tranh dịch theo phép chiếu.
Cổng và chữ trên biển tách riêng; cổng hiện dần khi đến gần cuối đoạn đường.

Một lần bấm phím/mũi tên hoặc một nấc chuột đặt mục tiêu đi một bậc. Nhiều
lệnh liên tiếp vẫn chạy qua các khung trung gian. Định vị bài đang học và đổi
đoạn đặt lại vị trí dưới mây che, không chạy lùi lộ ra ngoài. Chuyển HSK bắt
đầu lại ở chân đoạn kế tiếp; không sửa điểm, tiến độ hay quyền mở bài.

Đây là chuỗi minh họa 2.5D, không phải thế giới 3D
được mô hình hóa đầy đủ hoặc phim quay thực. Thử nghiệm mesh chiều sâu đầu
tiên bị kéo giãn và optical flow bị chồng nét đã được bỏ. Hình động không còn là đối tượng
kiểm tra pixel-identical với ảnh tĩnh. Các tài liệu/capture reference-journey
trước đó chỉ ghi lại bản tĩnh đã bị người dùng bác bỏ về cách diễn giải.

Một canvas WebGL, shader chiếu cảnh và sprite; pixel ratio tối đa 1.5. Vòng vẽ
dừng khi đứng yên, ẩn tab hoặc ra khỏi vùng nhìn. Giảm chuyển động chuyển ngay
đến vị trí mới. Nếu WebGL không có, nền tĩnh và nút vào bài/toàn lộ trình vẫn
hoạt động. Không khẳng định FPS phần cứng từ trình duyệt kiểm tra headless.

Kiểm tra: `verify-illustrated-climb.mjs` ghi video và dữ liệu khung trung gian
ở desktop/mobile, kiểm tra nhịp chân, camera, trạng thái đứng yên, giảm chuyển
động, quay lại từ bài học và các số bài 15/10/15. Bằng chứng ở
`.impeccable/review/illustrated-climb/`. Chưa deploy.

Reviewer đã xác nhận các điểm sửa về cảnh liền mạch, tư thế quay người, khung
nhân vật và cổng trên điện thoại. Kết luận `ship` chỉ áp dụng cho các điểm đã
chấm và lỗi cắt nhân vật ở khúc cua; xem `REVIEW.md` trong thư mục bằng chứng.

Tài nguyên cuối ở `frontend/public/academy/great-wall/climb-motion-v2/`:
`master.webp` (1774×887), `bo-turn.webp` (1024×640), `provenance.json`.
PNG gốc ở `assets/plates/continuous-climb-master-v2.png` và
`assets/plates/bo-rear-turn-v2.png`; prompt chính xác ở hai file `.prompt.txt`
cùng tên. Công cụ tạo ảnh: built-in `image_gen.imagegen`.
`prepare-climb-motion-v2.py` chỉ đổi định dạng, chia ô, dùng một tỷ lệ chung và
căn gốc bàn chân; giữ alpha nguyên sinh, không tô lại hoặc xóa nền.
