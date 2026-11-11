# Chuyển động leo bậc liên tục — local

> Cơ chế tiền cảnh 2.5D bên dưới đã được thay bằng thế giới 3D có camera thực,
> theo yêu cầu cảnh xung quanh cùng thay đổi góc nhìn. Xem `docs/spatial-great-wall.md`.

Người dùng phản hồi rằng chuyển chéo giữa ba ảnh tạo cảm giác cảnh đứt đoạn,
còn Bo bước tại chỗ. Bản sửa này giữ tranh Trường Thành đã duyệt và đổi cách
di chuyển, thay cho việc tiếp tục chỉnh thời lượng fade.

## Chuyển động hiện tại

- Một tọa độ quãng đường liên tục dùng chung cho bậc, vị trí chân Bo và độ sâu
  cổng. Quãng đường không đặt lại khi qua số bài mới.
- Mặt bậc và mặt đứng dùng texture đá vẽ tay trực giao riêng, chiếu lên các
  bề mặt chuyển động theo phối cảnh. Bậc gần đi qua nhanh hơn bậc xa. Cuộn ngược
  trả về cùng vị trí và dừng cuộn giữ mặt đường đứng yên.
- Cổng tăng kích thước theo khoảng cách, rồi đi khỏi khung khi camera vượt qua.
  Cổng xa vẽ trước cổng gần; nhãn/vùng bấm HTML bám cùng phép chiếu.
- Camera có vận tốc, giới hạn tăng tốc và tốc độ ở quãng ngắn; quãng cuộn lớn
  tăng tốc để tránh phải chờ đi hết từng bước. Dừng và đổi hướng giữ quán tính
  ngắn. Một frame bị treo không tạo bước nhảy toàn bộ quãng cuộn.
- Nhịp chân lấy quãng đường chia độ dài hai bậc. Chân Bo nâng dần lên mặt bậc
  tiếp theo bằng hàm liên tục; tư thế đứng nằm trên phần đường còn nhìn được
  phía trên bảng điều hướng. Quay lại dùng bộ sprite hướng trước đã có.

Không còn đổi chéo ảnh `landing/climb/bend` hay zoom lặp lại ở từng bài.
Các nhãn pha trong dữ liệu debug chỉ là nhịp điều hướng, không biểu thị việc
đổi ảnh/camera sang một góc vẽ khác. Bộ tải chính có bốn ảnh: nền desktop,
nền portrait, cổng và texture đá. Các ảnh góc cũ được giữ làm tài liệu tham chiếu.

## Texture và phép chiếu

Nguồn cắt từ ảnh có phối cảnh đã bị lượt duyệt mới bác bỏ vì đá bị kéo thành
dải. Nguồn cuối là `frontend/public/academy/great-wall/painted-v2/ascent-stone-atlas.webp`
(1254×1254), tạo bằng công cụ tích hợp `image_gen`; nguồn PNG tại
`assets/plates/ascent-stone-atlas.png`. Prompt chính xác, provenance và metadata
nằm cạnh WebP dưới tên `ascent-stone-atlas.*`. Đây là tài sản mới duy nhất của
lượt sửa chuyển động; phong cảnh, cổng và sprite Bo tiếp tục dùng tài sản cũ.

Nửa trên là bề mặt lát đá trực giao; nửa dưới có bốn hàng đá mặt đứng. Mật độ
texture cố định 156,75 px/đơn vị thế giới: mặt bậc sâu 0,85, mặt đứng cao 0,18,
đường rộng 6. UV theo tọa độ thế giới; bậc đi qua mép texture được tách tại
điểm wrap. Không kéo cả một hàng đá cao thành một mặt đứng mỏng. Mặt bậc chia
nhỏ theo chiều sâu để giảm méo affine; mặt đứng chỉ thêm bóng nhẹ, không vẽ
vạch sáng lặp lại ở mép bậc. Mép xa hòa vào cảnh nền qua vùng chuyển tiếp ngắn.

## Phạm vi và giới hạn

Đây vẫn là cảnh **2.5D với tiền cảnh bậc chuyển động**, không phải camera tự do
trong mô hình 3D của toàn bộ địa hình. Núi và tường hai bên thuộc lớp tranh nền;
bản sửa không tuyên bố đã đi xuyên một thế giới 3D hoặc hoàn thành toàn bộ cua
3D. Mục tiêu kiểm chứng là có chuyển động tương đối thật ở mặt đường gần,
chân và cổng, liên tục khi qua bài, thay cho đổi ảnh trong khi chân đi tại chỗ.

Giữ nguyên learning states, draft/publish, quyền vào bài, lưu vị trí theo tab,
tổng quan, chuyển mây khi mở bài và liên kết sang HSK sau. Chế độ giảm chuyển
động tiếp tục dùng tổng quan. Canvas hoặc ảnh lỗi vẫn có lối chọn bài.
Không sửa dữ liệu học tập; **chỉ local, chưa deploy**.

## Mã và kiểm chứng

`paintedAscent.ts` chứa hình học bậc/chân và bộ camera; `paintedTreads.ts`
chiếu texture từ tranh; `paintedWallGeometry.ts` tính cổng/chân;
`createForwardWallScene.ts` ghép các lớp; `boMotion.ts` đồng bộ nhịp sprite.

- TypeScript đã qua; **47 tests của hành trình đạt** trong tám file, gồm
  chuyển động bậc gần/xa, liên tục qua ranh giới bài và ranh giới bậc, tăng tốc,
  đổi hướng, frame treo, cổng/Bo trên bốn kích thước và hành vi có sẵn.
- `verify-painted-ascent-motion.mjs` dùng cuộn native qua mốc 6.85→7.18 rồi
  cuộn ngược trên 1440/390px. So sánh pixel canvas xác nhận mặt đường đổi rõ
  hơn cảnh xa; quay lại khôi phục pixel cũ, đứng nghỉ không trôi nền. Đồng thời
  kiểm tra frame bước chân, thay đổi vị trí chân và hướng quay lại.
- Hai chuỗi motion đạt, không page error hay API write. Video và các ảnh
  `boundary-*`, `reverse-*` ở `.impeccable/review/continuous-painted-ascent/`.
  Đây là video chẩn đoán headless local, không chứng nhận FPS thiết bị thật.
- Lượt điều hướng và fallback sau sửa được ghi trong cùng thư mục review.
  Bộ điều hướng đạt 27 capture trước thay texture; sau thay texture có 18 ảnh
  ở bốn kích thước, hai chuỗi motion đạt và năm capture fallback/resize đạt,
  bao gồm giả lập thiếu chính atlas đá mới.
- Lượt duyệt độc lập mới yêu cầu sửa nguồn/mapping đá; lượt chấm lại xác nhận
  đã giải quyết và không thấy regression ở các khung desktop/mobile được chấm.
  Xem `full-review.md` và `finish-verdict.md`; không dùng kết luận cũ để duyệt
  cơ chế chuyển động mới.

Giữ nguyên `DESIGN.md` và `.impeccable/design.json`. Không đưa cơ chế tiền cảnh
riêng này thành quy tắc thiết kế chung hoặc sửa các mô tả sản phẩm cũ ngoài phạm vi.
