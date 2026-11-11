# Hành trình Trường Thành hướng về phía trước

Lộ trình dùng cảnh kết hợp: camera nhìn dọc con đường 3D giữa hai thành đá,
phía sau là tranh núi. Đường cua nhẹ, lên dốc chậm; khoảng 3–4 cổng hiện trước
mặt tùy vị trí và khung nhìn. Cổng gần có tên bài, trạng thái và Bo bên bài hiện
tại; cổng xa chỉ giữ nhãn ngắn. Bảng điều hướng dưới cảnh có nút bài trước,
bài tiếp theo, tên bài gần nhất và vị trí trong tổng số cổng. Thanh HSK, bộ đếm
bài đã hoàn thành, “Về bài đang học” và “Xem toàn bộ lộ trình” vẫn ở phía trên.

## Nội dung và quyền học

Giữ 15 bài HSK 1, 10 bài HSK 2 và 15 bài HSK 3. HSK 1 thêm cổng phát âm ở
đầu; các kiểm tra định kỳ thật giữ thứ tự `order_index` từ backend và có cổng
riêng. Vì vậy tổng số cổng có thể lớn hơn số bài học. Bộ đếm hoàn thành chỉ tính
bài học, không tính phát âm và kiểm tra. HSK 2/3 vẫn mở được trực tiếp; điều kiện
phát âm chỉ áp dụng cho HSK 1.

Mốc còn thiếu hiển thị “Sắp có nội dung”, không tạo bản ghi hay đường dẫn học.
Bài thật chỉ có liên kết khi đã xuất bản và trạng thái cho phép truy cập. Mốc
khóa hoặc đang chuẩn bị có nút giải thích. Giao diện đọc dữ liệu giáo trình,
tiến độ và phát âm; không ghi tiến độ, mở khóa, xuất bản nội dung hay đổi cơ sở
dữ liệu. Quy tắc học và hoàn thành vẫn do backend quyết định.

## Cuộn, camera và chuyển cảnh

Cuộn trang tự nhiên điều khiển tiến độ camera; cuộn lên đi tới cổng kế tiếp,
cuộn xuống quay lại. Không chặn wheel/touch. Mỗi bước tương ứng 235px cuộn,
giảm còn 205px khi vùng cảnh hẹp hơn 700px. Vị trí đích được giới hạn trong
lộ trình; camera đuổi theo bằng giảm chấn mũ theo thời gian với hằng số 105ms:
`1 - exp(-dt / 105)`. Cùng một tiến độ điều khiển camera, nhãn DOM và nền núi,
giúp chúng chuyển động đồng bộ qua các khúc cua.

`requestAnimationFrame` chỉ chạy khi có thay đổi hoặc camera chưa đến đích;
tab ẩn dừng vòng lặp. Chỉ số bài gần nhất cập nhật khi đổi cổng, không render
React mỗi frame. Đổi kích thước đo lại vùng sticky và giữ tiến độ hiện tại.
Khi mở bài bằng liên kết thông thường, cảnh mờ dần trước khi điều hướng sau
200ms; Ctrl/Cmd-click và thao tác mở tab khác giữ hành vi liên kết trình duyệt.
Vùng học có hiệu ứng xuất hiện ngắn khi vào bài.

## Đồ họa và phương án thay thế

`createForwardWallScene.ts` tải động Three.js, dựng mặt đường và tường bằng
geometry dải; răng thành, trụ và mái cổng dùng geometry dùng chung qua
`InstancedMesh`. Cảnh dùng WebGL2, ánh sáng và sương, không dùng shadow map
hay hậu kỳ; pixel ratio giới hạn ở 1.5. Tranh núi là lớp ảnh phía sau canvas;
texture đá lặp trên kiến trúc. Nhãn tương tác là liên kết/nút HTML được chiếu
theo tọa độ 3D. Nếu texture không tải được, vật liệu đá màu ấm vẫn dùng được.
Mái cổng là một mặt mái cong có độ dày, mái đua và phần gỗ phía dưới. Chỉ dựng
các cổng trong chuỗi gần tương ứng với nhãn; cổng xa và đường tan dần theo
độ sâu, tránh chồng nhiều mái ở chân trời.

“Toàn bộ lộ trình” hiển thị mọi mốc bằng danh sách thẻ, cho phép mở bài và
định vị lại cổng trong cảnh. `prefers-reduced-motion` mặc định dùng danh sách;
bật tùy chọn này trong lúc xem cũng chuyển sang danh sách. Nếu chủ động quay
lại cảnh, camera định vị ngay, không giảm chấn. Tùy chọn này cũng bỏ chuyển
cảnh và hiệu ứng vào bài. Thiếu WebGL2, lỗi khởi tạo hoặc mất graphics context
đưa về danh sách, kèm thông báo; nút trở lại cảnh bị khóa sau lỗi đồ họa.

## Bàn phím, khôi phục và dọn tài nguyên

Canvas và tranh trang trí không đọc bởi trình đọc màn hình. Danh sách cổng,
trạng thái, nút điều hướng và thông báo có nhãn tiếng Việt. Chỉ cổng gần được
tương tác trong cảnh; cổng xa đặt `inert`. Focus bằng bàn phím định vị camera
ngay; toàn bộ mốc cũng truy cập được trong chế độ tổng quan. Các nút HUD có
focus rõ và vô hiệu hóa ở đầu/cuối lộ trình hoặc khi cảnh đang tải.

`sessionStorage` lưu tiến độ camera đích cùng chuỗi ID cổng theo khóa
`bo-forward-wall-v1-hsk-{level}`. Ghi sau 200ms nghỉ cuộn, khi ẩn/rời trang
và khi tháo cảnh; chỉ khôi phục nếu danh sách ID còn khớp, rồi giới hạn vị trí
hợp lệ. Đây là vị trí trình bày trong tab, không phải tiến độ học. Nút “Về bài
đang học” định vị lại theo dữ liệu hiện tại. Storage không khả dụng không chặn
việc học.

Khi đổi chế độ hoặc rời trang, component hủy frame, timer, observer và listener;
scene giải phóng geometry, material, texture, instanced mesh và renderer, rồi
đóng WebGL context. Texture tải xong sau khi scene đã tháo cũng được giải phóng.

## Tệp triển khai và nguồn ảnh

Mã chính nằm trong `frontend/src/features/journey/ForwardWallJourney.tsx`,
`createForwardWallScene.ts`, `forwardGeometry.ts`, `GreatWallJourneyPage.tsx`
và `journeyData.ts`; kiểu hiển thị nằm trong
`frontend/src/styles/forward-great-wall.css` và `great-wall-journey.css`.
Đây là phần mở rộng học viện minh họa: giữ jade, cinnabar, ivory, Noto Sans/SC
và Bo theo `DESIGN.md`; vật liệu đá vàng chỉ thuộc cảnh Trường Thành.

Hai ảnh raster mới được tạo bằng công cụ tích hợp `image_gen` ngày 08/11/2026:

- `frontend/public/academy/great-wall/forward-mountains-v1.webp`: tranh núi làm nền.
- `frontend/public/academy/great-wall/forward-stone-v1.webp`: texture đá lát lặp.

Prompt đầy đủ và tên PNG nguồn được ghi trong
`frontend/public/academy/great-wall/forward-assets-v1.prompt.txt`. PNG gốc giữ
trong thư mục `generated_images` mặc định của công cụ; bản đưa vào ứng dụng là
WebP chất lượng 88, giữ kích thước gốc, không chỉnh sửa hình ảnh.

## Triển khai

Gói nguồn CLI loại `public/hanzi-data` qua `.vercelignore`; `npm run build`
vẫn gọi `prebuild` để tạo lại dữ liệu nét chữ từ gói đã khóa phiên bản. Dữ liệu
tiếp tục nằm trong bản web cuối. Việc này giảm gói nguồn từ gần 10.000 tệp xuống
423 tệp tại thời điểm triển khai tính năng. Gói nén `--archive=tgz` đã tải lên
thành công sau lỗi kết nối khi gửi danh sách tệp thông thường; tùy chọn này được
[Vercel hỗ trợ cho gói nhiều tệp](https://vercel.com/docs/cli/deploy#archive).

## Xác minh

Đã kiểm tra 138 test trong các nhóm hành trình, bài học, phát âm và router;
một timeout của bài kiểm tra điều hướng được chạy lại cả tệp 42 test và qua.
TypeScript, lint và build thành công. Browser kiểm tra 28 ảnh ở desktop,
điện thoại và màn hình ngang, tất cả các cổng HSK 1, số bài 15/10/15, đổi chiều
cuộn, mở bài/quay lại, reload, bàn phím, giảm chuyển động, thiếu WebGL và mất
context thật. Kết quả không có lỗi trình duyệt/shader hoặc ghi dữ liệu học.

Bản production đã xác minh ngày 08/11/2026:
https://learn-chinese-oudel1yf0-mcbo1.vercel.app, sau đó đưa lên tên miền chính.
Runner: `frontend/scripts/verify-forward-wall.mjs`; biên bản và ảnh nằm ở
`.impeccable/review/forward-great-wall`. Kiểm duyệt hoàn thiện: `disposition: ship`.
