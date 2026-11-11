# Hành trình Trường Thành cùng Bo

> Bản local hiện hành đã chuyển sang cảnh minh hoạ 2.5D theo ảnh người dùng
> chỉ định; xem `docs/painted-great-wall.md`. Các mô tả 3D và triển khai cũ
> bên dưới là ghi nhận lịch sử, không phải renderer hiện tại.

Phần mở rộng đường bậc đá và địa hình leo núi hiện được thực hiện riêng ở
local, chưa deploy; xem `docs/uphill-great-wall.md`. Ghi nhận triển khai ở cuối
tài liệu này thuộc bản góc nhìn thứ ba trước phần mở rộng đó.

Phần mở rộng này thực hiện hướng đã duyệt trong
`docs/design/third-person-journey-proposal.md` và storyboard
`.impeccable/proposals/third-person-bo/storyboard-v1.png`; hợp đồng bề mặt ở
`.impeccable/surfaces/third-person-great-wall.md`. Bo dùng atlas hoạt ảnh 2.5D
nhiều hướng có alpha gốc, đặt theo phép chiếu trên đường 3D. Đây là phương án
nhẹ đã chọn, không phải nhân vật 3D có bộ xương. Bài học tiếp tục dùng bố cục
đọc hiện có.

## Đi cùng Bo và chọn bài

Trang mặc định mở cảnh đi bộ. Cuộn trang tự nhiên thay đổi vị trí trên đường;
không chặn wheel hoặc touch. Với ánh xạ hiện tại, cuộn lên tiến về cổng kế
tiếp, cuộn xuống quay lại. Mỗi cổng cách nhau 235px cuộn, hoặc 205px khi vùng
cảnh hẹp hơn 700px. Camera đuổi theo vị trí đích bằng giảm chấn thời gian
105ms; camera, bảng tên HTML, bóng chân và Bo dùng cùng tiến độ đường.

`boMotion.ts` tăng pha bước theo quãng đường thực tế, giới hạn tốc độ đổi pha
khi có bước nhảy vị trí. Hai atlas 4×2 cung cấp tám frame mỗi chiều: tiến lên
dùng góc nhìn từ sau, quay lại dùng góc nhìn từ trước. Khi ngừng di chuyển,
Bo chuyển sang tư thế nhìn lại hoặc chỉ đường và thở nhẹ; chân không tiếp tục
đạp tại chỗ. Một chuyển dịch nhỏ sang bên để lộ lối đi diễn ra lúc nghỉ.
Trở về sau khi dữ liệu bài vừa học chuyển thành hoàn thành có thể hiển thị
tư thế vui mừng ngắn; đây chỉ là phản hồi hình ảnh, không ghi hoàn thành.
Trúc/Bút xuất hiện ở các bài có số chia hết cho năm, với nút mở lời nhắc học.

Mỗi cổng có hai trụ, mái cong, đèn lồng và lối giữa để trống. Bảng tên được
nằm trọn giữa mái và xà cổng, gồm hai dòng số bài và tên bài; trạng thái nằm
trong bảng điều hướng phía dưới để lối giữa mở rõ trên cả điện thoại. Cổng hiện tại dùng cinnabar, cổng hoàn
thành dùng jade; trạng thái cũng có chữ và biểu tượng. Cổng xa giản lược tên
và trạng thái; các cổng còn được chiếu trong cảnh vẫn là liên kết/nút HTML.
Focus bàn phím đưa camera tới cổng ngay, giữ liên kết có tên đầy đủ.

Một lần bấm liên kết cổng gần bắt đầu bước vào cổng rồi phủ mây ivory và mở
bài. “Gần” nghĩa là cách tiến độ hiện tại không quá 1,1 cổng trong chế độ đi
bộ. Chọn cổng xa hoặc một bài trong tổng quan dùng chuyển mây nhanh, tránh
phải xem Bo chạy hết đường. Nút trước/sau, “Về bài đang học” và nút định vị
trên thẻ tổng quan chỉ đưa người học tới vị trí tương ứng. “Xem toàn bộ lộ
trình” đổi sang danh sách thẻ; người học có thể chọn bài trực tiếp tại đây.

## Dữ liệu và trạng thái học

HSK 1/2/3 giữ số bài dự kiến 15/10/15. HSK 1 có thêm cổng phát âm đầu đường;
kiểm tra thật giữ thứ tự `order_index` từ backend. Vì vậy số cổng trong bảng
điều hướng có thể lớn hơn số bài. Bộ đếm hoàn thành chỉ tính bài học. Điều
kiện hoàn thành phát âm áp dụng cho HSK 1; HSK 2/3 giữ đường vào trực tiếp.

Bài còn thiếu có mốc “Sắp có nội dung”, không tạo bản ghi hay đường dẫn giả.
Bài thật chỉ có liên kết khi đã xuất bản, cấp độ cho phép và trạng thái bài
khác `LOCKED`. Mốc khóa/đang chuẩn bị dùng nút `aria-disabled` có lời giải
thích. Hướng dẫn giữ quy tắc hoàn thành bài trước và đạt từ 80% luyện tập;
backend tiếp tục quyết định quyền học và tiến độ.

Khi dừng gần bài, trỏ chuột hoặc focus cổng, ứng dụng có thể nạp trước dữ
liệu bài và tiến độ qua các query đọc hiện có. Cache bài dùng `staleTime`
30 giây, tiến độ 10 giây. Chỉ đường dẫn `/lessons/:id` có bước nạp trước
này; phát âm và kiểm tra giữ đường vào riêng. Không đánh dấu đã xem, hoàn
thành, mở khóa hay sửa nội dung trong bước đi bộ, nạp trước hoặc chuyển mây.

## Chuyển mây, gián đoạn và quay lại

`JourneyCloudProvider` bọc toàn bộ `LearnerLayout`, nên màn mây tồn tại qua
đổi route. Chuyến đi thường bắt đầu phủ ở 280ms và chuẩn bị điều hướng ở
660ms; lối nhanh từ xa phủ ngay và bắt đầu điều hướng ở 240ms. Việc chờ
prefetch được giới hạn thêm 1.100ms, lỗi nạp trước không chặn việc vào bài.
Sau điều hướng có 100ms chờ trước khi vén mây; lớp vén kéo dài 340ms. Nền
ivory CSS bảo đảm vẫn có lớp phủ nếu ảnh mây không tải được.

Provider nhận một chuyến tại một thời điểm. Escape hủy các timer, đổi mã
thế hệ để bỏ qua kết quả đang chờ, gọi callback dừng bước vào cổng và trả màn
mây về trạng thái nghỉ. Đổi tổng quan hoặc bấm “Về bài đang học” cũng gọi
hủy. Nếu route chuyển sang nơi khác ngoài đích dự kiến, provider hủy chuyến
đang chờ để callback cũ không đưa người học quay về bài đã bỏ qua. Watchdog
hủy timer, đổi mã thế hệ và gọi callback dừng bước trước khi vén mây nếu
chuyến còn bận sau mốc điều hướng cộng 1.800ms. Kết quả promise cũ không thể
lên lịch chuyển tiếp sau đó; thao tác điều hướng đã giao cho router vẫn do
router quản lý.

Ctrl/Cmd/Shift/Alt-click và thao tác chuột khác nút chính giữ hành vi liên
kết gốc. Trong chế độ giảm chuyển động, liên kết mở bài dùng điều hướng gốc.
Nút quay lại trong `LessonHeader` vẫn trỏ `/pronunciation`, dùng chuyển mây
quay lại cho click thường và giữ modifier-click. Khi route trở từ
`/lessons/…` hoặc `/assessments/…` về `/pronunciation` hoặc `/hsk/:level`, kể
cả Back của trình duyệt, provider có màn phủ rồi vén ngắn 180ms nếu không
có chuyến đang chạy. Bộ xử lý này không thay đổi lịch sử trình duyệt hay
nội dung bài học.

Vị trí đích được lưu theo tab tại `bo-forward-wall-v1-hsk-{level}`, kèm chuỗi
ID cổng. Chỉ khôi phục khi danh sách ID khớp, rồi giới hạn vào miền hợp lệ.
Lưu sau 200ms nghỉ cuộn, khi ẩn/rời trang và khi tháo cảnh. Storage không khả
dụng không chặn học. Đây là vị trí trình bày, tách khỏi tiến độ học backend.

## Đồ họa, giảm chuyển động và dọn tài nguyên

Three.js tải động khi dùng cảnh; đường và tường là geometry dải, kiến trúc
cổng dùng geometry dùng chung và `InstancedMesh`. WebGL2 dùng ánh sáng và
sương, pixel ratio tối đa 1,5, không có shadow map hay hậu kỳ thời gian thực.
Chỉ khoảng cổng gần được hiển thị, kiến trúc xa tan dần. Ảnh núi và mist là
lớp trang trí; canvas, Bo và bóng chân không mang nội dung đọc màn hình.

Thiếu WebGL2, lỗi khởi tạo hoặc mất graphics context chuyển sang tổng quan,
hiện lời hướng dẫn và khóa nút quay lại cảnh. Texture đá lỗi vẫn có vật liệu
đá màu ấm. Atlas Bo lỗi dùng `Companion` tư thế hướng dẫn hiện có; trạng thái
bài và liên kết vẫn dùng được.

`prefers-reduced-motion` mặc định mở tổng quan; bật trong lúc xem cũng đưa
về tổng quan. Nếu chủ động mở lại cảnh, camera định vị ngay và Bo không chạy
chu kỳ bước. CSS tắt thở, vui mừng, mist và hiệu ứng vào bài; chuyển mây quay
lại dùng các mốc ngắn và fade 80ms. Các trạng thái học không phụ thuộc vào
chuyển động.

Vòng `requestAnimationFrame` chỉ chạy khi có thay đổi, camera đang tới đích
hoặc đang bước vào cổng. Tab ẩn dừng frame và tạm dừng hoạt ảnh CSS. Đổi chế
độ hoặc tháo component hủy frame, timer, `ResizeObserver`, listener cuộn,
resize, visibility và context loss. Scene giải phóng geometry, material,
texture, instanced mesh, renderer rồi đóng context; texture tải xong sau khi
tháo cũng được giải phóng. Provider hủy timer và vô hiệu hóa callback cũ khi
tháo khỏi cây giao diện.

## Tài sản và nguồn gốc

Tất cả đường dẫn sau nằm trong `frontend/public/academy/great-wall/` và được
phục vụ dưới `/academy/great-wall/`:

| Tệp | Vai trò |
| --- | --- |
| `bo-walk-away-v1.webp` | Tám frame đi tới, góc nhìn sau; 1024×640, ô 256×320. |
| `bo-walk-toward-v1.webp` | Tám frame quay lại, góc nhìn trước; cùng lưới. |
| `bo-journey-poses-v1.webp` | Bốn tư thế nghỉ, mời đi và vui mừng; 1024×320. |
| `journey-cloud-v1.webp` | Mây ivory có alpha dùng cho hai cánh màn chuyển. |
| `forward-mountains-v1.webp`, `forward-stone-v1.webp` | Nền núi và texture kiến trúc được giữ từ cảnh trước. |
| `mountain-mist-v1.webp` | Lớp mist trang trí của cảnh. |

`bo-journey-provenance-v1.json` ghi prompt chính xác, PNG gốc, lần thử và lựa
chọn nguồn. `bo-journey-metrics-v1.json` ghi kích thước, lưới, bounds alpha,
điểm neo chân, sai khác frame và hash atlas. Prompt riêng nằm trong
`away-journey-v1.prompt.txt`, `toward-journey-v1.prompt.txt`,
`toward_retry-journey-v1.prompt.txt`, `poses-journey-v1.prompt.txt` và
`cloud-journey-v1.prompt.txt`; prompt chọn cũng được nhúng trong XMP WebP.

Nhân vật và mây được tạo bằng công cụ tích hợp `image_gen` với
`transparent_background: true`. Công cụ phát triển
`frontend/scripts/normalize-bo-journey-v1.py` dùng Pillow
để chia ô, resize đẳng hướng chung cho mỗi atlas, căn root/đường chân và xuất
WebP lossless. Script giữ alpha gốc, không key màu, vẽ lại nhân vật hay nội
suy frame. Hình dáng, tư thế và chất lượng chu kỳ thuộc nguồn ảnh model;
code chịu trách nhiệm pha bước, hướng, neo chân, phép chiếu và thời điểm
chuyển trạng thái. Provenance giữ ghi chú về các pha chân gần giống nhau và
một số wisps mây chạm biên ảnh gốc; không biến chúng thành quy tắc mỹ thuật.

## Ranh giới thiết kế và mã nguồn

Giữ `DESIGN.md` hiện có: jade/pine/cinnabar/ivory, Noto Sans/SC, cảnh vẽ tay
và mặt đọc bài phẳng. Đá vàng, atlas bước chân và màn mây thuộc bề mặt hành
trình này, không tạo token toàn cục mới.

Mã chính: `ForwardWallJourney.tsx`, `createForwardWallScene.ts`,
`forwardGeometry.ts`, `boMotion.ts`, `JourneyCloudTransition.tsx` và
`journeyCloudContext.ts` trong `frontend/src/features/journey/`, cùng
`journeyData.ts` và `GreatWallJourneyPage.tsx`. Kiểu nằm ở
`frontend/src/styles/forward-great-wall.css`; provider nằm trong
`frontend/src/app/layouts/LearnerLayout.tsx`, liên kết quay lại nằm trong
`frontend/src/features/lesson/LessonHeader.tsx`.

## Kiểm chứng và triển khai

Ngày 09/11/2026: bản `learn-chinese-6qmfp3hik-mcbo1.vercel.app` đã qua bộ
kiểm tra trình duyệt 30 ảnh chụp ở 1440/1024/390/320px và được promote lên
`https://learn-chinese-mcbo1.vercel.app`. Alias `learn-chinese-pied-three.vercel.app`
cùng phục vụ bundle `index-Bt5s2sjs.js`; ảnh Bo, mây và dữ liệu nét chữ trả HTTP 200.
Bản Docker frontend tại `http://127.0.0.1:5173` cũng đã được build lại.

Báo cáo ở `.impeccable/review/third-person-great-wall/verification.json`:
không có lỗi trình duyệt, API ngoài dự kiến hoặc thao tác ghi tiến độ. Dữ liệu
API trong lượt này là fixture có kiểm soát; kiểm tra không xác nhận nội dung
curriculum production hay tốc độ khung hình trên thiết bị thật. Bố cục sau khi
sửa biển cổng được duyệt lại trên cả bốn kích thước, disposition: ship.

Kiểm tra hồi quy cuối: 146/146 tests qua trong 9 file liên quan hành trình,
route, bài học và phát âm; TypeScript build và lint phạm vi thay đổi qua.
Lượt test trước đó có một timeout ở trang phát âm khi kiểm tra trình duyệt
đang chạy; file đó và toàn bộ lượt cuối đều đã chạy lại thành công.
