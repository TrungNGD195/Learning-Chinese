# Hành trình Trường Thành minh hoạ — bản local

> Cơ chế chuyển động mới đã thay phần đổi chéo ba ảnh bằng tiền cảnh bậc leo
> liên tục; xem `docs/continuous-painted-ascent.md`. Mô tả crossfade và bảy ảnh
> bên dưới ghi lại bản trước khi nhận phản hồi về cảm giác bước tại chỗ.

Người dùng yêu cầu dựng lại theo ảnh đã duyệt tại
`.impeccable/proposals/uphill-bo-v1/uphill-bo-v1.png` sau khi bác bỏ chất liệu
và bố cục của bản khối 3D trước. Hợp đồng bề mặt hiện hành là
`.impeccable/surfaces/painted-great-wall.md`. Phạm vi chỉ ở local; chưa deploy
bản dựng lại này và không đổi dữ liệu hay quyền học.

## Cách dựng cảnh hiện tại

`createForwardWallScene.ts` hiện dùng Canvas 2D để ghép các lớp minh hoạ,
thay cho đường, tường, mái và đèn lồng dựng bằng khối Three.js. Đây là trải
nghiệm **2.5D phân lớp**, gồm zoom/pan và chuyển chéo giữa ba góc cảnh vẽ
sẵn; không phải thế giới 3D có camera tự do. Các lớp giữ đá mòn có rêu,
bóng cây, cổng gỗ chạm, mái ngói đỏ, thung lũng jade và đường ôm sườn núi
của ảnh tham chiếu. Không dùng ảnh crop từ bản nháp làm hình nền sản phẩm.

Mỗi nhịp giữa hai bài dùng chuỗi chiếu nghỉ → leo bậc → qua cua → đến chiếu
nghỉ tiếp theo. `paintedWallGeometry.ts` tính trọng số chuyển cảnh, vị trí
cổng và khung Bo theo tiến độ cuộn. Bộ cảnh desktop/mobile tách riêng;
tỷ lệ vùng nhìn nhỏ hơn 1,15 chọn bản portrait. Ảnh được vẽ theo tỷ lệ gốc
với chế độ phủ khung, không kéo méo. Dịch ngang bị giới hạn để không lộ mép
trống; mật độ pixel canvas tối đa 1,5 lần CSS.

Canvas đợi đủ bảy ảnh trước khi báo cảnh sẵn sàng. Không có context 2D,
ảnh cốt lõi lỗi hoặc sự kiện mất context sẽ chuyển sang toàn lộ trình để
người học vẫn chọn bài được. Tháo cảnh giải phóng tham chiếu và handler ảnh,
đồng thời kết thúc các promise tải đang chờ.

## Bo, cổng và điều hướng

Bo tiếp tục dùng atlas tám frame mỗi chiều đã có. Cuộn điều khiển pha bước;
đi tới dùng góc nhìn từ sau, quay lại dùng hướng trước. Khi nghỉ theo hướng
đi tới, Bo dùng tư thế nhìn từ sau thay cho dáng đứng quay mặt mời gọi của
bản bị bác bỏ. Vị trí và kích thước được tính để giữ toàn thân trong khung;
khi vào bài, Bo tiến về cổng và nhỏ dần dưới lớp mây chuyển cảnh hiện có.

Cổng là ảnh có alpha gốc và lối giữa trong suốt. Toàn bộ khung cổng là vùng
liên kết/nút HTML; người học không phải bấm đúng dòng chữ. Biển chỉ hiện tên
ngắn của bài, còn tên đầy đủ và trạng thái nằm ở bảng điều hướng phía dưới.
Hoàn thành/khóa vẫn có biểu tượng và nhãn ngữ nghĩa; trạng thái và quyền mở
bài lấy từ dữ liệu thật. Chữ không được raster hoá vào ảnh cổng.

Tọa độ biển HTML bám vùng an toàn đo từ ảnh cổng:
`x=.314551, y=.277207, w=.371517, h=.132444`, với đường chân tại
`y=.972279`. Khi đi qua, hình cổng và vùng HTML mờ đồng bộ; cổng kế tiếp
hiện trong nhịp đến gần. Tổng quan, định vị bài đang học, lưu vị trí theo
tab, modifier-click và chuyển mây giữ cách hoạt động hiện có. Chế độ giảm
chuyển động mặc định mở tổng quan.

## Sau bài cuối mỗi HSK

Ảnh cảnh vẫn có đường thành vòng lên sườn núi và tháp phía xa sau cổng bài
cuối, không kết thúc bằng mép sàn cụt. `GreatWallJourneyPage.tsx` chọn cấp
kế tiếp từ danh sách API đã sắp theo số HSK. Nếu cấp đó tồn tại, bài cuối
hiện liên kết “Tiếp đến HSK …”; mũi tên tiếp theo dưới cùng cũng thành
liên kết sang cấp đó, qua chuyển mây ngắn.

Không có cấp kế tiếp trong API thì không tạo liên kết hay cấp giả. Cảnh
vẫn nối vào đường phía xa, nhưng không gán cho phần xa một quyền học mới.
Chuyển cấp không ghi hoàn thành bài, xuất bản nội dung hoặc sửa quy tắc
tiến độ. HSK 1/2/3 tiếp tục có dự kiến 15/10/15 bài, cùng phần phát âm và
các kiểm tra thật theo curriculum.

## Tài sản và nguồn gốc

Tệp phục vụ nằm trong `frontend/public/academy/great-wall/painted-v2/`:

| Tệp | Vai trò |
| --- | --- |
| `landing-desktop.webp`, `climb-desktop.webp`, `bend-desktop.webp` | Ba góc cảnh landscape, mỗi ảnh 1774×887. |
| `landing-mobile.webp`, `climb-mobile.webp`, `bend-mobile.webp` | Ba góc portrait; giữ tỷ lệ nguồn 1024×1536 hoặc 941×1672. |
| `gate.webp` | Cổng RGBA 1615×974; lối giữa giữ alpha trong suốt. |
| `gate.metrics.json` | Bounds, vùng biển an toàn và đường chân để ghép HTML. |

Các ảnh mới được tạo bằng công cụ tích hợp `image_gen`. PNG nguồn ở
`assets/plates/`; prompt chính xác nằm cạnh từng WebP dưới tên
`landing-desktop.prompt.txt`, `climb-desktop.prompt.txt`,
`bend-desktop.prompt.txt`, các tên `*-mobile.prompt.txt` và `gate.prompt.txt`.
`desktop-environment.provenance.json`, các `*-mobile.provenance.json` và
`gate.provenance.json` ghi nguồn, chuyển đổi và hash. Prompt được nhúng
trong metadata nguồn/WebP và có sidecar CLI; lượt scan ghi bảy raster,
không thiếu provenance. Atlas Bo và mây chuyển cảnh giữ nguồn hiện có.

## Kiểm chứng và giới hạn

Lượt TypeScript đã qua; `tmp/painted-unit.log` ghi **157/157 tests đạt**
trong 11 file, gồm khung bao cổng/Bo và chuỗi trọng số cảnh. Kết quả này
không chứng minh độ giống ảnh tham chiếu hoặc tốc độ khung hình thực tế.

Kiểm tra trình duyệt dùng fixture API có kiểm soát trên frontend thật ở local.
Các lượt desktop và mobile đã kiểm tra đủ cổng ở 1440/1024/390/320px; chuyển
HSK 1→2 và 2→3; đi/quay lại/dừng; mở bài, Back, reload; giảm chuyển động và
fallback context/ảnh. Lượt desktop dừng ở ngưỡng sai số cuộn quá nhỏ khi bắt
đầu mobile; runner đã sửa ngưỡng thành tối đa một CSS pixel của bước cuộn đo
được. Lượt mobile đầy đủ sau đó đạt. Đây là sửa phép đo, không sửa vị trí bài.

Helper chụp stage cũ dùng cùng khoảng cuộn cho leo và cua, khiến cả hai ảnh
vẫn là góc leo. Đã sửa sang pha .36/.70, xác nhận `data-scene` và chụp lại
đúng các đường dẫn. Báo cáo tách lượt trong `.impeccable/review/painted-journey/`;
không dùng bốn ảnh visual-only để khẳng định toàn bộ kiểm thử đã đạt.
Oxlint không có lỗi, còn các cảnh báo có sẵn ngoài phần hành trình.
Không dùng fixture để xác nhận curriculum thật hoặc cam kết FPS thiết bị thật.

Lượt duyệt độc lập mới (`full-review.md`) xác nhận vật liệu, bố cục, Bo và
đường tiếp nối; yêu cầu dời nút HSK khỏi tháp xa. Đã dời nút desktop sang vùng
trời giữa; ở khung 701–1200px dùng góc trái phía trên để tránh đường bậc chéo,
còn mobile giữ góc phải không che landmark. Kết quả chụp/duyệt lại được ghi
tại `finish-verdict.md`: lỗi che tuyến thành đã được xác nhận giải quyết trên
desktop, tablet và mobile; không thấy regression từ lần sửa này. Kết luận của
bản 3D cũ không áp dụng cho bản này. Toàn bộ thay đổi vẫn chỉ ở local.

## Hệ thống thiết kế

Giữ nguyên `DESIGN.md` và `.impeccable/design.json`: pine/jade/cinnabar,
ivory, Noto Sans/Noto Sans SC và bộ điều khiển học viện tiếp tục dùng như
hiện có. Cách ghép cảnh và tọa độ biển thuộc riêng hành trình, không trở
thành token cho toàn bộ sản phẩm. Drift cũ trong PRODUCT/DESIGN về nguồn
học, trợ lý AI và chỉnh cỡ chữ nằm ngoài phạm vi này, không được sửa hoặc
chuẩn hoá thành quy tắc mới.
