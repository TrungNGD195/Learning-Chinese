# Trường Thành không gian và cột mốc HSK — local

Lưu ý: đây là tài liệu lịch sử của renderer 3D. Người dùng đã chọn ưu tiên tranh
gốc và nối các cảnh minh họa gốc; hướng hiện hành ở `reference-great-wall.md`.

Người dùng bác bỏ cảnh nền đứng yên với lớp đường chuyển động, yêu cầu camera
tiến, lên cao và xoay theo đường leo; cảnh xa dần rõ hơn; cuối mỗi HSK có cột
mốc và chặng sau tiếp tục từ chính mốc đó. Bản này thay renderer Canvas2D bằng
thế giới Three.js/WebGL2. Hợp đồng: `.impeccable/surfaces/spatial-great-wall.md`.

## Cảnh và camera

Bậc, tường, cây, địa hình, tháp, cổng và cột mốc có tọa độ thế giới. Camera thực
sự di chuyển theo đường cong và độ cao; không thay ảnh nền, không cuộn texture
dưới chân trong khi giữ cảnh bên ngoài đứng yên. Camera nhìn theo Bo đi trước,
giữ phương thẳng đứng và làm êm độ cao qua các bậc. Chân Bo theo từng bậc;
camera theo độ dốc trung bình, tránh rung lên xuống ở mỗi mép bậc.

Bo tiếp tục là sprite minh hoạ tám frame trong không gian phối cảnh; cây dùng
ảnh alpha trên hai mặt phẳng cố định trong thế giới. Địa hình, bậc, tường, tháp
và trụ là mesh có chiều sâu. Cổng minh hoạ là mặt phẳng đặt cố định theo hướng
đường. Nhãn/vùng bấm HTML dùng ma trận chiếu cùng mặt phẳng cổng, nên nghiêng
đúng góc và vẫn dùng bàn phím/liên kết thật. Đây không phải mô hình rồng có rig
xương hay bộ cây 3D đầy đủ; không mô tả các sprite thành mô hình như vậy.

Sương theo khoảng cách và giảm khi camera lên cao. Texture có mipmap và độ sâu
thực, giúp chi tiết rõ dần khi đến gần. Địa hình xa lấy độ cao tham chiếu SRTM,
được đổi tỷ lệ và ghép với sống núi của đường học ảo. Không tuyên bố đây là bản
tái tạo địa lý chính xác hoặc bản đồ dẫn đường tại Trường Thành.

## Mốc nối ba chặng

| Chặng | Tọa độ dọc tuyến bắt đầu | Mốc cuối |
| --- | ---: | ---: |
| HSK 1 | 0 | 240 |
| HSK 2 | 240 | 405 |
| HSK 3 | 405 | 645 |

Mốc hiện tại là tháp canh theo ảnh người dùng cung cấp: thân thành đá, cửa vòm
với lòng cửa/sổ tối đen, lan can lỗ châu mai và gian gác mái ngói xám.
Các phần có chiều sâu 3D; móng chìm xuống dốc, không để hở đáy/chân tường.
Texture gạch phong hóa mới và mái ngói dựng bằng mesh được dùng cho công trình;
không dùng ảnh chụp làm phông. Tháp thay cho cột hoa biểu cũ. Nhãn HSK là texture
chữ tạo lúc chạy, đi kèm thao tác HTML trong bảng điều hướng. Không gắn mốc với
điểm thưởng hay tự đánh dấu hoàn thành HSK.

HSK 1 giữ 15 bài và phát âm; HSK 2/3 giữ 10/15 vị trí bài. Mốc đầu/cuối là
điểm điều hướng riêng, không tạo thêm lesson/unit trong DB. Các bài kiểm tra
định kỳ thật có thể làm tăng số cổng; vẫn giữ nguyên vị trí mốc và giãn các
cổng thật trong khoảng đó. Các cổng xa ở chặng khác là vị trí dự kiến.

Camera ở cuối HSK 1 và đầu HSK 2 dùng cùng phép tính với tọa độ 240; tương tự
HSK 2→3 tại 405. Cây, địa hình, ánh sáng và tháp canh dùng cùng thế giới, không
đặt lại tại mỗi chặng. Đi bằng liên kết ở cột mốc sẽ ưu tiên điểm bắt đầu
chặng kế tiếp thay vì một vị trí giữa chặng đã lưu trước đó. Mở chặng theo
cách thông thường vẫn có thể khôi phục vị trí đã lưu theo tab.

Liên kết “Tiếp đến HSK…” hiện là hoạt cảnh cổng chuyển chặng: camera đứng yên,
Bo bước 3,1 đơn vị trong 1.350ms, tối dần và biến mất khi vào ngưỡng cửa đen.
Sau đó mây mới nhập (chờ 120ms sau nhịp đi). Điểm đến là đầu dốc bài 1 của
HSK kế tiếp, waypoint 0,5: tháp cũ đã khuất, cổng mới còn dưới mây như ảnh mẫu.
Escape trước khi chuyển trang hủy chuyến và phục hồi Bo; giảm chuyển động thì
đi thẳng tới chặng mới. Ý định đến đầu dốc được lưu riêng theo marker, không
ghi tiến độ học. Giá trị marker cũ theo tab vẫn đọc được.

Trong nhịp vào tháp, nền 3D được dựng một lần vì camera không đổi; Bo và bóng
chuyển động theo phép chiếu mỗi frame. Resize/cancel dựng lại nền đúng trạng thái.

Đường còn tiếp sau mốc HSK 3; không bịa thêm cấp HSK hoặc nội dung đã xuất bản.
API vẫn quyết định quyền học, draft/publish, hoàn thành và ngưỡng luyện tập.

## Độ mượt và hồi phục

- Mỗi khoảng cổng dài 15 đơn vị thay vì 24, gồm tám bậc cao 0,675 đơn vị
  và hai đoạn chiếu nghỉ. Mặt bậc sâu 1,5 đơn vị; khoảng cách cổng giảm 37,5%.
- Nút lên/xuống, phím ↑/↓ và từng nấc chuột tiến/lùi đúng một mặt bậc.
  Đuôi quán tính touchpad được gom thành một lượt; phím giữ không tự lặp.
  Lệnh bấm liên tiếp được cộng vào đích đến, không bỏ mất lệnh khi camera đang đi.
- Camera có vận tốc, giới hạn tăng tốc và tốc độ đi bộ; chỉ camera nội suy,
  cuộn trang đồng bộ tức thời để tránh chồng hai lớp làm mượt.
- Tích phân theo bước nhỏ để nhịp di chuyển không phụ thuộc từng frame chậm.
- Cuộn bằng cảm ứng hoặc thanh cuộn được hút về mặt bậc gần nhất. Bản vị trí
  theo tab dùng khóa v2 để không khôi phục nhầm khoảng cách của hình học cũ.
- Chi tiết hình học gần/xa tách riêng: khối gần có cạnh bo; khối xa có ít tam
  giác hơn. Giảm mật độ và độ phân giải khi dùng renderer phần mềm; Bo và chữ
  HTML vẫn giữ độ phân giải giao diện. Không gọi kết quả headless là chứng nhận FPS.
- Tháo cảnh giải phóng geometry, material, texture và context GPU.
- Back giữa lúc vào cổng hủy hiệu ứng đang đi, tránh vòng lặp camera bị kẹt.
- Giảm chuyển động mặc định mở tổng quan. WebGL/asset lỗi vẫn chọn bài bằng
  danh sách; không thay bằng một cảnh giả vẫn cuộn đường trên ảnh tĩnh.

## Tài sản và tham khảo

Tài sản mới tạo bằng công cụ tích hợp `image_gen`:

| Asset | Kích thước | Vai trò |
| --- | --- | --- |
| `spatial-v1/pines.webp` | 2172×724 RGBA | Ba cây thông minh hoạ alpha, ba ô bằng nhau. |
| `spatial-v1/pillar-relief.webp` | 1024×1024 RGB | Tài sản của cột cũ, giữ lịch sử; renderer hiện tại không tải. |
| `realistic-v1/masonry.webp` | 1254×1254 RGB | Gạch đá phong hóa cho tường/tháp/lỗ châu mai. |
| `realistic-v1/paving.webp` | 1254×1254 RGB | Phiến đá lát xám cho mặt bậc và cổ bậc. |
| `realistic-v1/pines.webp` | 2172×724 RGBA | Atlas thông tự nhiên, thay atlas minh họa trong renderer. |

Đường dẫn gốc: `frontend/public/academy/great-wall/`; PNG nguồn trong
`assets/plates/spatial-*.png`. Prompt chính xác, provenance và metadata cạnh
WebP (`pines.prompt.txt`, `pillar-relief.prompt.txt`). Cổng, đá, mây và Bo dùng
tài sản hiện có. Không chép ảnh du lịch trên web vào sản phẩm.

Nguồn PNG mới và prompt đầy đủ: `assets/great-wall/realistic-v1/generation.md`.
Runtime WebP giữ alpha; provenance cạnh file ghi hash và kích thước thực tế.
Các mặt đá dùng MeshStandardMaterial, độ nhám cao, bump map và ACES tone mapping.
Ánh sáng trời/tán xạ, màu địa hình và sương bớt vàng gắt; phần cứng có shadow
map mềm, software renderer tắt shadow map. Cây vẫn là atlas trên mặt phẳng chéo
để giữ chi phí; đây là nâng chất liệu/ánh sáng, không phải mô hình thực vật đầy đủ.

Tháp hiện tại theo ảnh tham chiếu người dùng gửi trong hội thoại, được dựng
bằng geometry trong `milestoneWatchtower.ts`. Tham khảo kiến trúc ở lượt trước:
[hoa biểu — Cố Cung](https://www.dpm.org.cn/lemmas/245264.html),
[đường leo Kim Sơn Lĩnh](https://www.travelchinaguide.com/china_great_wall/scene/beijing/jinshanling.htm).
Độ cao: [Terrain Tiles trên AWS](https://registry.opendata.aws/terrain-tiles/),
[định dạng Terrarium](https://github.com/tilezen/joerd/blob/master/docs/formats.md).
Ghi nguồn và biến đổi dữ liệu ở `assets/terrain/README.md`; dữ liệu chạy được
phục vụ từ cùng origin, không gọi dịch vụ địa hình bên ngoài khi học.

## Cổng khi đi ngang qua

Cổng n rõ hoàn toàn tại điểm dừng bình thường (Bo còn cách 6 đơn vị), giữ nguyên
đến lúc Bo chạm mặt phẳng cổng rồi mờ đi trong một mặt bậc. Cổng n+1 và xa hơn
bị ẩn, có các lớp mây minh họa đặt trong thế giới tại các cổng phía trước.
Sau khi n đã mất, n+1 hiện từ 0 đến 100% qua năm nhịp bậc; mây tản sang hai bên
và giảm dần cùng vị trí leo. Cổng n+2 vẫn ẩn. Đi ngược phục hồi cùng trạng thái,
không dùng timer tự chạy. Hiệu ứng này chỉ thay cách nhìn, không thay quyền học.
Mỗi cổng có material riêng; độ rõ của bảng tên và ảnh cổng được đồng bộ. Cổng
đang mờ không ghi depth; vùng bấm dưới 15% độ rõ ngừng nhận chuột và focus.

Nút “Về bài đang học” dùng cùng lớp chuyển cảnh mây như mở bài. Sau khi mây phủ
kín (620ms), vị trí camera được đặt tức thời tại cổng hiện tại. Mây giữ thêm
260ms rồi tản ra trong 560ms; CSS và controller lấy cùng giá trị thời gian.
Không đi lùi qua những cổng trung gian, không thêm lịch sử điều hướng. Trạng thái
đi bộ/hướng nhìn cũ của Bo được đặt lại; Escape trước thời điểm đổi cảnh sẽ hủy
chuyển vị trí. Khi giảm chuyển động, đổi vị trí trực tiếp.

Camera lùi nhẹ và ngắm vào giữa tháp khi đến mốc để giữ đủ toàn bộ mái, thân,
cửa vòm trên màn hình nhỏ. Đầu/cuối hai HSK vẫn dùng cùng phép tính camera.
Vùng đổi góc chỉ bắt đầu trong nửa đoạn cuối đến tháp, sau khi cổng bài cuối
đã khuất; bài 15 và các cổng trước giữ cùng khoảng cách camera bình thường.
Lòng tháp có một cửa vòm phía trước và lối ra sau rộng, không đặt hai mặt cửa
vòm chồng nhau gây một dải tường giả chắn ngang khung cửa khi nhìn từ dưới lên.
Sau khi Bo đi qua, tháp cũng tan trong một nhịp để trần và tường không che
camera đang theo sau; ở mốc cuối/đầu HSK, tháp vẫn hiện rõ hoàn toàn.
Yêu cầu “Về bài đang học” cũ không được phát lại khi mount HSK tiếp theo.

Lớp chuyển cảnh chỉ chứa mây, không render dòng chữ hay trạng thái tải.

Kiểm chứng riêng bằng `frontend/scripts/verify-spatial-gate-fade.mjs`: desktop
1440px và mobile 390px, bốn vị trí tiếp cận, chuyển tiếp trong bước qua cổng,
quay lại, cổng kế tiếp, mở lesson và trở về cổng dưới mây phủ kín.
Ảnh cùng kết quả ở `.impeccable/review/spatial-great-wall/gate-fade/`.

## Kiểm chứng

Lượt cổng tuần tự/tháp canh có runner `frontend/scripts/verify-sequential-clouds.mjs`;
ảnh desktop/mobile và số liệu theo bậc ở
`.impeccable/review/spatial-great-wall/sequential-clouds/`. Các capture cột trụ
trước đó là lịch sử của bản cũ.

81 tests hành trình đạt trong 15 file ở lượt cửa tháp/chuyển chặng. Các kiểm tra gồm
viền đá không chắn cửa bằng raycast và lớp lòng cửa đen, khung hình toàn tháp tại 320–1214px,
thời lượng nhập/giữ/tản, cổng tuần tự không chồng nhau và điểm mốc chung,
tính liên tục camera/chân, tọa độ thực, các cỡ màn hình 320–1440px và dữ liệu
độ cao hợp lệ trước khi tạo mesh. TypeScript đã qua ở các lượt dựng.

Runner hiện tại `frontend/scripts/verify-tower-entry-realism.mjs` kiểm tra Bo
đi/khuất trước mây, camera giữ nguyên, Escape, đích đầu dốc HSK2/3 và tải các
tài sản mới trên 1440/390px. Capture/trace ở
`.impeccable/review/spatial-great-wall/tower-entry-realism/`.

Runner `frontend/scripts/verify-spatial-wall.mjs` dùng frontend thật cùng fixture
API tổng hợp, đo camera x/y/z, yaw, sương và vị trí màn hình của cây/tháp cố định;
kiểm tra đi/lùi, cổng, Back, reload và mốc nối HSK. Lượt cuối đạt 21 capture
desktop/mobile; sáu ảnh bổ sung kiểm tra 320px, landscape, mất context thật qua
extension WebGL, giảm chuyển động, thiếu WebGL và thiếu ảnh. Báo cáo/capture tại
`.impeccable/review/spatial-great-wall/`. Lượt chốt sau tối ưu và xử lý gián đoạn
được ghi trong thư mục đó. Duyệt cuối được thực hiện inline vì agent duyệt độc
lập hết hạn mức, không ghi nhận như phê duyệt độc lập. Không dùng kiểm tra pixel mặt đường cũ làm bằng chứng
cho việc toàn bộ cảnh thay đổi góc.

Giữ `DESIGN.md` và `.impeccable/design.json` hiện có. Phạm vi chỉ local, chưa
deploy; không thay dữ liệu học tập hoặc luật tiến độ.
