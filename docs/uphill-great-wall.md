# Bo leo Trường Thành — bản local

> Ghi nhận lịch sử: bản khối 3D này đã bị người dùng yêu cầu dựng lại theo
> ảnh minh hoạ đã duyệt. Triển khai local hiện hành được mô tả tại
> `docs/painted-great-wall.md`; các kết quả duyệt bên dưới thuộc bản cũ.

Người dùng đã duyệt bản nháp
`.impeccable/proposals/uphill-bo-v1/uphill-bo-v1.png` và yêu cầu sửa ở local
trước, chưa deploy. Hợp đồng bề mặt nằm tại
`.impeccable/surfaces/uphill-bo.md`. Đây là phần mở rộng của hành trình góc
nhìn thứ ba, giữ giao diện học tập và nhận diện học viện hiện có.

## Đường leo và chiếu nghỉ

Đường 3D uốn qua lại theo sườn núi. Khoảng cách trong `forwardGeometry.ts`
là độ dài cung ngang, nên vào cua không tự làm Bo tăng hoặc giảm tốc theo
độ lệch ngang. Hướng tiếp tuyến thay đổi liên tục theo chu kỳ bốn khoảng cổng,
với biên độ khoảng 64°. Đây là đường uốn chữ S, không phải các góc quay 180°.

Mỗi cổng cách nhau 42 đơn vị cảnh và cao hơn cổng trước 9 đơn vị. Mặt đường
giữa hai tâm cổng gồm chiếu nghỉ bằng phẳng dài tổng cộng 18 đơn vị và một
đợt 32 bậc đá trên quãng ngang 24 đơn vị. Mỗi mặt bậc sâu 0,75 đơn vị, cao
0,28125 đơn vị; độ dốc trung bình của đợt bậc khoảng 20,6°. Các số này là
đơn vị hình học của cảnh, không phải thông số của một địa điểm thật.

Mặt bậc và cổ bậc là các mặt hình học riêng, có gờ đá tại mép bậc. Lối đi
rộng 16 đơn vị; hai lan can và các răng thành theo pháp tuyến của đường.
Cổng nằm giữa chiếu nghỉ, xoay cùng tiếp tuyến địa phương, giữ khoảng thông
ở giữa. Biển HTML lấy vị trí, tỉ lệ và góc xoay từ phép chiếu 3D; mặt sau
hoặc mặt quá nghiêng không hiện nhãn đọc ngược. Cổng vẫn dùng tên, trạng thái
và đường dẫn bài thật.

Khi Bo đi qua, kiến trúc cổng và biển HTML cùng mờ theo một khoảng quãng
đường: bắt đầu khi Bo vượt tâm cổng 2 đơn vị và hết khi vượt 7 đơn vị. Phần
3D dùng uniform quãng đường cùng thuộc tính khoảng cách từng instance;
phần HTML dùng cùng hàm smoothstep. Cổng đã khuất hoàn toàn được loại khỏi
nhóm instance đang hiển thị, tránh biển biến mất trước phần mái hoặc cột.

Sườn đá liên tục nằm dưới chân tường, mở rộng và hạ xuống thung lũng để
không còn cảm giác đường thành lơ lửng. Chòi canh nhỏ xuất hiện cạnh một số
chiếu nghỉ, không đặt giữa lối đi. Phần đường sau cổng cuối được giới hạn
còn 11 đơn vị để có khoảng bước qua cổng mà không kéo dài đoạn trống.

## Bo và camera

Bo vẫn dùng bộ atlas 2.5D hiện có: tám frame đi tới, tám frame quay lại và
các tư thế nghỉ. Nhân vật được chiếu trên mặt đường 3D; điểm chân lấy cao
độ bậc thật. Pha bước tăng theo quãng đường, nay dùng hằng số khoảng cổng
42 đơn vị; tốc độ đổi pha vẫn có giới hạn khi cuộn nhanh.

`forwardCameraFrame` đặt camera theo Bo, thay vì đặt trên một điểm đường
cách xa phía sau. Hướng đuổi lấy từ đoạn đường giữa điểm cách Bo 10 đơn vị
về sau và 14 đơn vị về trước. Camera lùi 22 đơn vị theo hướng này, lệch bên
1,8 đơn vị và nhìn tới điểm cách Bo 14 đơn vị phía trước; nhờ vậy Bo không
trôi khỏi khung hình khi đường rẽ vào phía trong khúc cua.

Cao độ camera dùng trung bình không gian của hồ sơ dốc liên tục tại vị trí
Bo và hai điểm cách 3 đơn vị trước/sau, rồi cộng 9,8 đơn vị; điểm nhìn cộng
3 đơn vị vào cùng hồ sơ đó. Vì thế camera không nhảy theo từng cổ bậc.
Tiến độ camera vẫn giảm chấn thời gian 105ms; không thêm rung theo chân hay
tự xoay 180° khi người học quay lại. Nền núi dịch nhẹ theo hướng đường, với
độ lệch giới hạn theo chiều rộng viewport để không lộ mép ảnh ở điện thoại.

Thời gian giữa hai frame camera được giới hạn ở 250ms để camera vẫn tiến
tới đích khi render chậm; bộ tính nhịp chân Bo tiếp tục giới hạn ở 64ms để
không tăng pha bước đột ngột. Timer chuyển sang tư thế nghỉ chỉ được đặt
khi tiến độ hiện tại đã bằng đích, tránh chèn tư thế đứng trong lúc camera
còn đang đuổi theo thao tác cuộn.

## Đồ họa và tải render

Khi `WEBGL_debug_renderer_info` cho biết renderer là SwiftShader, llvmpipe
hoặc software, cảnh 3D dùng pixel ratio 0,4 trong lúc di chuyển và 0,85 khi
đứng yên. Chữ HTML, các nút và atlas Bo vẫn hiển thị bằng CSS ở độ phân giải
gốc; phần giảm độ phân giải chỉ áp dụng cho drawing buffer của cảnh 3D.
Renderer phần cứng giữ pixel ratio tối đa 1,5 như trước. Nếu không có thông
tin renderer để nhận diện software, ứng dụng dùng cấu hình mặc định đó.

Các vật liệu có fade bật `forceSinglePass`, tránh render lặp mặt trước/sau
đối với vật liệu hai mặt. Đây là cấu hình giảm công việc render, không phải
bằng chứng đạt một tốc độ khung hình cụ thể trên thiết bị thật.

## Các thao tác giữ nguyên

Cuộn lên tiến tới cổng tiếp theo, cuộn xuống quay lại; ứng dụng không chặn
wheel hay touch. Mỗi cổng vẫn tương ứng 235px cuộn, hoặc 205px khi vùng cảnh
hẹp hơn 700px. Nút trước/sau và “Về bài đang học” định vị theo bài; “Xem toàn
bộ lộ trình” mở danh sách để chọn nhanh. Vị trí được lưu theo tab và danh
sách ID cổng như trước.

Chọn cổng gần giữ bước qua cổng và màn mây trước khi mở bài. Chọn bài xa
dùng chuyển mây ngắn; Escape, Back và khôi phục khi reload tiếp tục theo cơ
chế của `JourneyCloudProvider`. Nạp trước bài chỉ đọc dữ liệu. Bài khóa hoặc
đang chuẩn bị vẫn hiển thị giải thích thay vì tạo quyền truy cập.

`prefers-reduced-motion` mặc định dùng tổng quan; mất WebGL2/context hoặc lỗi
khởi tạo cũng chuyển sang tổng quan. Hỏng texture đá vẫn có vật liệu màu
cơ bản; bộ fallback nhân vật hiện có vẫn được giữ. Tab ẩn dừng vòng render,
và các geometry, material, texture cùng renderer được giải phóng khi rời cảnh.

Không sửa backend, xuất bản bài, điều kiện mở bài, điểm đạt 80% hoặc tiến độ
học. HSK 1/2/3 vẫn có 15/10/15 bài dự kiến; HSK 1 thêm phát âm và các kỳ kiểm
tra thật tiếp tục theo dữ liệu backend. Bản mở rộng này chưa được deploy.

## Hình ảnh và mã nguồn

Ảnh nền núi, đá thành, mây và các atlas Bo được giữ từ bản trước. Tài sản mới
là `frontend/public/academy/great-wall/uphill-rock-v1.webp`: texture vách đá
vẽ tay, RGB không alpha, 1024×1024, 267800 byte. Texture lặp trên mesh sườn
núi, ánh sáng và phối cảnh do cảnh 3D tạo. `uphill-rock-v1.prompt.txt` giữ
prompt chính xác; `uphill-rock-v1.provenance.json` ghi ảnh gốc, tham chiếu,
chuyển đổi và hash. Prompt cũng được nhúng trong metadata WebP. Việc lặp
texture do model tạo, không có cam kết nối mép hoàn hảo bằng toán học.

Mã chính nằm trong `frontend/src/features/journey/`: `forwardGeometry.ts`,
`createForwardWallScene.ts`, `ForwardWallJourney.tsx` và `boMotion.ts`.
CSS hiện có ở `frontend/src/styles/forward-great-wall.css` tiếp tục định
nghĩa biển bài, thanh điều hướng, nhân vật và chuyển mây.

## Kiểm chứng

Lượt kiểm tra hồi quy mã cuối tại `tmp/uphill-final-checks.log` đã đạt
152/152 tests trong 10 file. Các kiểm tra hình học xác nhận độ dài cung
ngang gần như không đổi, hướng cua liên tục, chiều
rộng lối đi, cao độ từng chiếu nghỉ và chuỗi bậc không giảm độ cao. Bốn kiểm
tra phép chiếu camera mới bao phủ bốn chiều rộng, các vị trí nguyên và phân
số trên toàn đường, giới hạn Bo và biển cổng trong khung hình. Typecheck và
lint của mã cuối cũng đã đạt.

Lượt kiểm tra trình duyệt đầy đủ đã đạt trên `http://127.0.0.1:5173`, với
34 ảnh chụp và mẫu chuyển động ở 1440/1024/390/320px. Báo cáo
`.impeccable/review/uphill-bo/verification.json` ghi nhận không có lỗi trình
duyệt, API ngoài dự kiến hoặc thao tác ghi dữ liệu; log hoàn tất ở
`tmp/uphill-browser-complete.log`. Runner
`frontend/scripts/verify-forward-wall.mjs` dùng fixture API có kiểm soát trên
ứng dụng local, không xác nhận nội dung curriculum thật hay tốc độ khung
hình trên thiết bị thật.

Lượt đầu ở 1440px đã qua đủ 16 cổng, chuyển động, mở bài và quay lại; bước
reload của harness sau đó bị timeout khi chờ sự kiện `load` trong môi trường
thiếu tài nguyên. Runner đã đổi sang chờ `DOMContentLoaded` cùng các điều
kiện sẵn sàng của cảnh và đặt timeout điều hướng 60 giây. Lượt chạy đầy đủ
sau thay đổi này đã hoàn tất thành công.

Lượt duyệt giao diện sau sửa đã trả `disposition: ship` cho ba lỗi được chấm
lại: giữ Bo trong khung hình khi vào cua, đồng bộ biến mất của cổng và biển
sau khi đi qua, và giữ cổng phát âm vừa chiều ngang ở 320px. Ảnh chụp lại
sau khi sửa chuyển tư thế cũng được chấp nhận với một hình Bo rõ ràng;
không ghi nhận regression từ đợt sửa. Kết luận này áp dụng đúng các lỗi
được chấm lại trên bản local, không khẳng định khớp từng pixel với tranh
concept hoặc tốc độ khung hình trên thiết bị thật.

Phạm vi đạt gồm đủ 16 cổng HSK 1 (15 bài và phát âm), 10 bài HSK 2 và 15 bài
HSK 3; vị trí, khung bao và cao độ; cuộn tự nhiên, đi ngược và dừng; mở bài,
Back, reload, Escape; đổi kích thước ngang, giảm chuyển động, mất context và
fallback đồ họa. Các kiểm tra này giữ nguyên dữ liệu học và không deploy.

## Phạm vi hệ thống thiết kế

`DESIGN.md` và `.impeccable/design.json` được giữ nguyên. Pine/jade/cinnabar,
mặt điều khiển ivory, Noto Sans/Noto Sans SC, biểu tượng và bộ nhân vật hiện
có tiếp tục là nhận diện chung. Bậc đá, sườn núi và hình học camera thuộc
riêng hành trình, không được nâng thành token hoặc quy tắc cho mọi trang.

Drift có sẵn trong tài liệu gốc, như mô tả cỡ chữ có thể chỉnh, nguồn học và
trợ lý AI, không được sửa trong phạm vi mở rộng hình học này.
