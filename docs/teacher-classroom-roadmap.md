# Hanfolio — Giáo viên, lớp mặc định BO195 và học liệu theo lớp

Ngày ghi nhận: 14/11/2026.

Trạng thái: **Bản định hướng sản phẩm để triển khai trong tương lai**.
Tài liệu phân biệt yêu cầu người dùng đã nêu và các quy tắc đề xuất cần chốt.
Việc lưu tài liệu không cho phép tự tạo tài khoản/lớp, migration, chuyển dữ liệu,
bật AI, phát sinh phí hoặc deploy. Hiện chỉ thay đổi tài liệu.

## 1. Yêu cầu đã được người dùng xác nhận

- Thêm role giáo viên. Sau khi được cấp quyền, giáo viên được truy cập giáo
  trình được cung cấp và công cụ tạo bài học, luyện tập, đề test.
- Cùng một giáo trình, mỗi giáo viên có thể thêm/bớt từ vựng, ngữ pháp, bài khóa,
  lựa chọn dạng câu hỏi và tạo đề khác nhau.
- Ban đầu mỗi giáo viên quản lý một lớp. Học sinh sử dụng cùng giao diện học,
  nhưng nội dung phụ thuộc lớp đang xem.
- Chủ sản phẩm dự kiến tạo tài khoản giáo viên có tên **Teacher789**, phụ trách
  lớp **BO195**; đưa các nội dung đã biên soạn bằng admin vào lớp này.
- BO195 là lớp mặc định: học sinh đăng nhập sẽ thấy và học được mà không nhập mã.
- Các lớp khác tham gia bằng mã do giáo viên lớp đó cung cấp, theo trải nghiệm
  tương tự Google Classroom. Không yêu cầu mã lớp để vào BO195.
- Các nội dung chủ sản phẩm tạo tiếp về sau được bổ sung vào lớp của mình.
- Đây là hướng mở rộng sau này; giữ nguyên ứng dụng hiện tại cho đến khi có
  yêu cầu triển khai cụ thể.

Các điểm này thay thế đề xuất trước về một khu tự học chung độc lập bên ngoài
lớp và việc học sinh chỉ được tham gia một lớp đang hoạt động.

### 1.1. Quyết định bổ sung đã chốt ngày 14/11/2026

1. Tham gia lớp bằng mã bắt buộc có giáo viên duyệt; không có chế độ mã hợp lệ
   là được học ngay.
2. Học sinh được chủ động rời BO195.
3. Khi học sinh rời lớp hoặc lớp bị lưu trữ, học sinh không còn quyền xem nội
   dung của lớp đó. Không có chế độ xem lại chỉ đọc cho học sinh đã mất quyền.
4. Nếu bị loại khỏi lớp khi đang làm test, không lưu bài test đang làm của người
   đó. Cách xử lý lượt nháp và tranh chấp lúc nộp được cụ thể hóa tại mục 8.1.
5. Sửa bài đã xuất bản không yêu cầu người đã học phải học lại hoặc làm lại để
   giữ trạng thái hoàn thành/quyền luyện tập đã có.
6. Phải hoàn thành phần phát âm trước khi vào HSK1 ở mọi lớp; giáo viên không
   được bỏ qua điều kiện này.

Các quyết định này có ưu tiên cao hơn đề xuất chưa chốt ở các phiên bản trước.

## 2. Mô hình sản phẩm đề xuất

**Một nền tảng, nhiều lớp, một lớp mặc định và một giao diện học thống nhất.**

| Thành phần | Ý nghĩa |
| --- | --- |
| BO195 | Lớp mặc định do chủ sản phẩm vận hành; nội dung hiện có được gắn vào đây |
| Lớp giáo viên khác | Không công khai nội dung; học sinh tham gia bằng mã theo chính sách lớp |
| Giáo trình nguồn | Tài liệu tham khảo có quyền truy cập riêng, không phải lesson đang học |
| Bài học | Nội dung được biên soạn riêng trong phạm vi lớp |
| Bài giao / đề test | Nội dung, chính sách làm bài và phiên bản giao cho học sinh |
| Lớp đang xem | Ngữ cảnh điều hướng của giao diện; không tự tạo quyền truy cập |

BO195 là **tên hiển thị**, không phải bí mật, mã tham gia hay ID phân quyền.
Teacher789 là tên dự kiến, không phải mật khẩu mặc định hoặc xác nhận tài khoản
đã tồn tại. Hệ thống dùng ID nội bộ ổn định cho tài khoản và lớp.

## 3. Vai trò và quyền

| Nghiệp vụ | Admin | Giáo viên | Học sinh |
| --- | --- | --- | --- |
| Cấp/thu hồi quyền giáo viên | Có | Không | Không |
| Quản lý tài khoản toàn hệ thống | Có | Không | Không |
| Xác định lớp mặc định | Có | Không | Không |
| Cấp quyền xem giáo trình nguồn | Có | Không tự cấp | Không |
| Biên soạn và xuất bản trong lớp | Có quyền quản trị | Lớp đang phụ trách | Không |
| Sửa bài/đề của lớp khác | Chỉ thao tác quản trị có ghi lịch sử | Không | Không |
| Xem tiến độ và chấm bài | Theo quyền quản trị | Thành viên/bài nộp của lớp phụ trách | Chỉ bản thân |
| Xem nội dung lớp riêng | Theo quyền quản trị | Phạm vi được giao | Là thành viên hợp lệ |
| Cấu hình AI và hạn mức | Có | Chỉ sử dụng khi được cấp | Không sử dụng API giáo viên |

Chủ sản phẩm có thể dùng một tài khoản admin và một tài khoản Teacher789 riêng,
đúng với ý tưởng đã nêu. Không cần mở hệ thống nhiều role trên cùng một tài khoản
trong bản đầu. Mỗi tài khoản phải có định danh và thông tin đăng nhập riêng.

Admin tiếp tục chịu trách nhiệm vận hành, quyền giáo trình, xử lý báo lỗi và
quản trị lớp; không chỉ có chức năng xem danh sách tài khoản.

## 4. Cấp quyền giáo viên và sở hữu lớp

Đề xuất: admin mời/xác minh rồi cấp role TEACHER; không cho người đăng ký tự
chọn role này và được quyền ngay. Quyền được kiểm tra từ backend.

- Giáo viên có tối đa một lớp ACTIVE trong giai đoạn đầu; có thể chưa có lớp
  trong lúc chờ admin hoàn tất thiết lập.
- Một lớp có một giáo viên phụ trách chính. Dữ liệu vẫn hỗ trợ mở rộng số lớp
  trong tương lai bằng thay đổi hạn mức, không thay cấu trúc tài khoản.
- Tên lớp không cần duy nhất toàn hệ thống; ID lớp phải duy nhất.
- Thu hồi role phải thu hồi quyền và phiên thích hợp, không xóa nội dung/bài nộp.
- Khi chuyển giáo viên, giữ nguyên lớp, nội dung, điểm và người tạo/người chấm cũ;
  chuyển quyền phụ trách một cách tường minh, ghi nhật ký, kiểm tra lại tác vụ nền.
- Không cho giáo viên tự đổi lớp của mình thành lớp mặc định hoặc đổi chủ lớp.
- Nếu chủ lớp bị vô hiệu hóa, lớp bị đóng băng thao tác quản lý để admin xử lý;
  không tự xóa lớp hoặc tự động công khai học liệu.

## 5. Đăng nhập, BO195 và tham gia lớp khác

### 5.1. Lớp mặc định

Đề xuất: học sinh được ghi nhận thành viên BO195 khi đăng ký thành công, trong
cùng giao dịch hoặc qua quy trình khởi tạo có thể chạy lại an toàn. Tài khoản
học sinh hiện có được gắn vào BO195 bằng đợt chuyển đổi được kiểm soát.

Sau đăng nhập:

1. Nếu chỉ có BO195: mở giáo trình BO195 trực tiếp, không dựng màn hình nhập mã.
2. Nếu có nhiều lớp: mở lớp gần nhất còn quyền; có bộ chọn lớp và đường về BO195
   khi học sinh vẫn là thành viên hợp lệ của BO195.
3. Nếu lớp gần nhất không còn quyền: về BO195 nếu hợp lệ, nếu không thì về danh
   sách lớp có thể truy cập. Nếu không còn lớp nào, hiện trạng thái chưa tham
   gia lớp và chức năng xin vào lớp; không tự thêm lại vào BO195.

Không thêm thành viên qua GET, không thêm lại sau mỗi lần đăng nhập, không
chuyển membership REMOVED/BLOCKED về ACTIVE một cách tự động.

BO195 không tự biến mất khi tham gia lớp khác, nhưng học sinh được chủ động
rời BO195 và mất quyền xem nội dung BO195 như với lớp khác. Sau khi rời, không
được quay lại nội dung bằng URL cũ hoặc đăng nhập lại để tự khôi phục membership.
Việc BO195 là lớp mặc định không cho Teacher789 quyền xem bài nộp/tiến độ lớp khác.

Đề xuất cần chốt thêm: người đã rời BO195 có nút "Xin tham gia lại BO195" không
cần mã, nhưng phải được giáo viên BO195 duyệt; người bị chặn không tự xin lại.
Đây khác với lần khởi tạo membership mặc định cho tài khoản mới.

### 5.2. Lớp khác

Luồng đã chốt: **Đăng nhập → Tham gia lớp → Nhập mã → Xác nhận lớp → Chờ duyệt
→ Truy cập nội dung sau khi được duyệt**.

- Giáo viên được đổi mã, tắt mã, đặt hạn nhận thành viên và giới hạn sĩ số.
- Mã đủ khó đoán, sinh ngẫu nhiên; tên lớp như BO195 không dùng làm mã bí mật.
- Giới hạn lượt thử theo tài khoản và nguồn truy cập, không trả toàn bộ thông
  tin lớp/danh sách học sinh khi mã chưa hợp lệ.
- Sau mã hợp lệ chỉ hiển thị thông tin tối thiểu để xác nhận đúng lớp; chưa cho
  người đang chờ duyệt xem học liệu, bài test hoặc thành viên.
- Một học sinh có thể thuộc BO195 và các lớp khác. Mỗi lần chỉ có một lớp đang
  xem. Chuyển lớp không thay role hoặc chuyển dữ liệu học giữa các lớp.
- Gửi lại yêu cầu hoặc nhiều tab cùng tham gia không tạo membership trùng.
- Mã mới không loại thành viên cũ; mã hết hạn không cắt quyền thành viên đã duyệt.
- Người bị BLOCKED không được dùng mã mới để vào lại; chỉ admin/giáo viên có
  quyền phù hợp mới gỡ trạng thái theo chính sách đã chốt.
- Rời lớp là hành động xác nhận rõ, hiển thị cảnh báo sẽ mất quyền truy cập lớp.
  Không xóa tài khoản hoặc ảnh hưởng quyền của học sinh ở lớp khác.
- Người đang PENDING vẫn bị chặn ở API bài học, đề, bài nộp và file. Khi duyệt,
  phải kiểm tra lớp còn hoạt động và giáo viên còn phụ trách, tránh duyệt trễ
  sau lưu trữ/chuyển giáo viên.

Membership đề xuất: PENDING, ACTIVE, LEFT, REMOVED, BLOCKED. Lớp có trạng thái
DRAFT, ACTIVE, ARCHIVED. Không gộp trạng thái lớp với trạng thái thành viên.

## 6. Giáo trình nguồn và quyền truy cập file

Giáo viên được thấy **giáo trình admin đã cấp quyền**, không phải mọi file mà
hệ thống đang lưu. Tài liệu riêng của lớp khác, bản thu học sinh, bản sao lưu
và file nội bộ không thuộc thư viện giáo trình.

- Thư viện có tên, phiên bản, mô tả, quyền xem/tải và thông tin nguồn.
- Admin quyết định quyền tải PDF. Không suy từ quyền biên soạn rằng được phép
  phân phối lại toàn bộ giáo trình.
- Kiểm tra quyền ở endpoint tải và kho file; không đưa PDF riêng vào thư mục
  public của frontend. Link có hạn chỉ được cấp sau khi kiểm tra quyền.
- Bản đầu dùng thư viện được cấp quyền rõ ràng; chưa cho giáo viên tự tải tài
  liệu bất kỳ để AI xử lý mà không có kiểm soát.
- Nếu dùng AI/RAG sau này, tài liệu truy xuất và tác vụ nền cũng phải lọc theo
  quyền nguồn/lớp; không chỉ lọc danh sách file trên giao diện.
- Giáo trình PDF local hiện tại được Git bỏ qua, không có nghĩa là đã được
  upload hoặc có quyền phân phối cho giáo viên trên production.

## 7. Biên soạn riêng theo lớp

Giáo trình là đầu vào tham khảo. Bài học là sản phẩm biên soạn độc lập của lớp:
hai giáo viên dùng cùng giáo trình không chia sẻ một bản lesson có thể sửa chung.

Giáo viên có trình biên soạn bốn phần: Từ vựng, Ngữ pháp, Bài khóa, Luyện tập.
Có thể thêm/bớt/sắp xếp theo mục tiêu bài; phần không áp dụng được xác nhận rõ,
không tạo nội dung giả để vượt điều kiện xuất bản.

- Lesson, thứ tự lộ trình, bài luyện và đề test thuộc phạm vi lớp cụ thể.
- Giáo viên A không được cập nhật hoặc xuất bản tài nguyên của giáo viên B.
- Được dùng tài liệu nguồn chung không đồng nghĩa với quyền sao chép bài của
  giáo viên khác. Việc chia sẻ bài cần cấp quyền tường minh.
- Khi được phép lấy mẫu từ lớp khác: tạo bản sao riêng với ID mới, giữ thông tin
  nguồn; không mang theo học sinh, đáp án đã nộp, tiến độ hoặc điểm.
- Sửa từ vựng/ngữ pháp dùng trong lớp không được lan sang các lớp khác thông qua
  một bản ghi dùng chung có thể sửa. Phân biệt catalog tham khảo và nội dung
  đã biên soạn/phiên bản đang dùng.
- Bộ lọc HSK là phân loại trình độ; không xác định quyền hoặc chủ sở hữu bài.
- Số bài và thứ tự được ràng buộc theo lớp + cấp độ, không duy nhất toàn web.

Luồng đề xuất: **DRAFT → Giáo viên xem thử/kiểm tra → PUBLISHED trong lớp → ARCHIVED**.
Bản AI tạo luôn là DRAFT. Xuất bản trong lớp không tự đưa bài vào lớp BO195
hay thành thư viện chung. Admin có thể gỡ nội dung sai phạm kèm lý do/nhật ký.

## 8. Nội dung đã xuất bản, luyện tập và bài test

Giữ các nguyên tắc đã nêu ở lần đánh giá trước:

- Luyện tập để học có thể làm lại, giải thích sai và lấy điểm theo chính sách.
- Bài test có giờ mở, thời lượng, hạn nộp, số lần làm, cách chọn điểm và lịch
  công bố đáp án. Chốt chính sách trước khi học sinh bắt đầu.
- Không áp ngầm mọi quy tắc tự học vào mọi đề test của giáo viên.
- Mặc định BO195 giữ đủ lý thuyết trước luyện tập, 30 câu và ngưỡng 80% như hiện
  tại. Không tự thay chính sách cũ trong đợt chuyển sang lớp.
- Mỗi lần giao đề khóa phiên bản câu hỏi, đáp án, tiêu chí và cách tính điểm.
  Sửa sau khi có bài làm phải tạo phiên bản mới hoặc quy trình sửa điểm có kiểm
  soát; không ghi đè đề làm thay đổi lịch sử. Không tự yêu cầu học lại chỉ vì
  lesson đã được sửa.
- Một bài nộp thuộc đúng học sinh, bài giao và lớp; server kiểm tra membership,
  thời gian và số lượt làm. Chống nộp trùng và lưu tự động thất bại.
- Bị loại khi đang làm test: hủy lượt đang làm theo mục 8.1, không lưu bài hoặc
  tính điểm. Hiển thị lý do mất quyền; không chuyển thành điểm 0.
- Khi lớp lưu trữ: chặn học sinh truy cập mọi nội dung lớp, kể cả bài/điểm cũ;
  ngừng nhận thành viên, bài nộp và tác vụ AI mới. Giữ dữ liệu quản trị theo
  chính sách lưu trữ, không đồng nghĩa với xóa lớp hoặc toàn bộ lịch sử.

### 8.1. Hủy lượt test khi bị loại và các thao tác đồng thời

"Không lưu test đang làm" có nghĩa là lượt chưa nộp không được trở thành bài
nộp, không được chấm/công bố điểm và không được tính là một kết quả hoàn thành.
Các câu trả lời nháp đã tự lưu phải được bỏ, không giữ dưới dạng một bài có
thể khôi phục sau khi học sinh bị loại.

- Vô hiệu hóa lượt ngay tại giao dịch loại thành viên; xóa câu trả lời nháp và
  tệp tạm thuộc lượt đó, hoặc lên lịch dọn an toàn sau khi đã chặn mọi quyền đọc.
- Không xóa tệp dùng chung với bài khác. Hủy tác vụ upload/chấm AI còn chờ và
  bỏ kết quả tác vụ cũ nếu nó hoàn tất sau thời điểm mất quyền.
- Có thể giữ sự kiện quản trị tối thiểu (ai bị loại, lớp, thời điểm, lý do hủy)
  để đối chiếu; không chứa câu trả lời, bản thu hoặc điểm của lượt bị hủy.
- Endpoint lưu nháp/nộp/chấm kiểm tra lại quyền tại lúc ghi dữ liệu. Không chỉ
  kiểm tra một lần lúc mở đề; làm mới trang, nhiều tab và gửi lại request cũ
  đều không được khôi phục lượt đã hủy.
- Giao dịch nộp bài và loại thành viên phải được tuần tự hóa theo cùng cơ chế
  khóa/kiểm tra phiên bản quyền. Nếu loại thành viên có hiệu lực trước, từ chối
  nộp và bỏ lượt nháp. Nếu nộp đã commit hợp lệ trước, đó là bài đã nộp, không
  thuộc quy tắc hủy "đang làm". Không dựa vào thời gian do trình duyệt gửi lên.
- Bài đã nộp trước đó không tự bị xóa theo lượt đang làm. Học sinh vẫn không
  được xem các bài/điểm này sau khi mất quyền lớp; dữ liệu quản trị được giữ.
- Được duyệt vào lại lớp không phục hồi bài test đã hủy. Nếu cần làm lại, tạo
  lượt mới theo quyền và chính sách số lần làm mà giáo viên cho phép.

Đề xuất cần chốt thêm: dùng cùng cơ chế bỏ lượt chưa nộp khi học sinh tự rời
lớp hoặc khi lớp bị lưu trữ. Dù chọn cơ chế dọn dữ liệu nào, sau mất quyền đều
không được tiếp tục đọc, lưu nháp, nộp hoặc chấm lượt đang làm.

### 8.2. Sửa lesson mà không bắt học lại

- Giữ các trạng thái đã xem/hoàn thành, điểm và lượt làm đã có. Không tự xóa
  completion hoặc khóa lại luyện tập vì từ vựng/ngữ pháp/bài khóa bị sửa.
- Từ/bài khóa được bổ sung không được tự đánh dấu đã xem thay học sinh. Với
  người đã hoàn thành lesson, chúng là nội dung bổ sung có thể xem thêm;
  completion cũ vẫn được công nhận.
- Lưu phiên bản/mốc yêu cầu đã dùng để công nhận hoàn thành, thay vì tính lại
  toàn bộ điều kiện bằng danh sách mục đang thay đổi. Không để API tiến độ tự
  làm mất trạng thái hoàn thành do số mục mới tăng hoặc reading_version đổi.
- Người chưa hoàn thành tiếp tục theo mốc yêu cầu của lượt học đã bắt đầu;
  người bắt đầu mới học bản đã xuất bản mới. Việc xem nội dung cập nhật phải
  phân biệt với việc công nhận hoàn thành; không giả trạng thái đã xem.
- Sửa lesson không sửa ngược câu hỏi/đáp án/rubric trong lượt test đã bắt đầu
  hoặc đã nộp. Cần phiên bản nội dung và đề/bài giao riêng.
- Quy tắc này áp dụng khi sửa cùng lesson. Tạo lesson mới là nhiệm vụ mới,
  không được lấy completion của lesson cũ để tự hoàn thành lesson mới.

AI chấm viết/nói chỉ đề xuất; giáo viên duyệt điểm chính thức. Nhận dạng lời nói
không được coi là bằng chứng thanh điệu/phát âm đã chuẩn. Chấm theo đáp án xác
định không cần gọi AI. AI lỗi/hết ngân sách chuyển sang chấm thủ công, không
chấm 0 hoặc tự làm mất quyền học.

## 9. Phát âm, lượng từ và tiến độ

Đề xuất: phát âm và lượng từ là module nền tảng do nền tảng quản lý, có phiên
bản, các lớp có thể sử dụng. Giáo viên không sửa trực tiếp bản module chung.
Nếu cần khác biệt thì tạo nội dung bổ sung trong lớp riêng.

**Điều kiện đã chốt: hoàn thành phát âm mới được vào HSK1 ở mọi lớp.** Giáo viên
không thể tắt điều kiện này. Backend phải kiểm tra khi đọc lesson HSK1, bắt đầu
lượt luyện/test thuộc lộ trình HSK1 và lưu tiến độ; không chỉ ẩn nút ở frontend.
Không áp điều kiện này thành việc khóa HSK2/HSK3 hoặc bắt hoàn thành HSK trước.

Đề xuất triển khai: dùng một module phát âm nền tảng chung và một completion
cá nhân được công nhận ở tất cả lớp; đã hoàn thành thì không bắt học lại mỗi
lần đổi lớp. Completion nền tảng là thuộc tài khoản, không bị xóa khi rời BO195.
Tuy nhiên, hoàn thành phát âm không cấp quyền vào lớp: vẫn cần membership ACTIVE
và lớp ACTIVE. Không tự chuyển điểm test/lesson của BO195 sang lớp khác.

Đường vào module phát âm phải tồn tại trong mọi lớp đang có quyền, không dẫn
bắt buộc sang BO195 mà học sinh đã rời. Nếu không còn lớp hợp lệ, chỉ hiện màn
hình tham gia lớp; không dùng module chung để đi vòng vào học liệu lớp cũ.

Mỗi lesson riêng có ID riêng nên tiến độ theo lesson không trùng giữa lớp.
Tiến độ tổng hợp HSK phải tính trong phạm vi lớp đang xem. Không dùng tiến độ
HSK toàn cục hiện tại để tự mở bài trong mọi lớp.

## 10. Chuyển dữ liệu hiện có sang Teacher789 / BO195

Đây là đợt chuyển đổi sau này, không thực hiện khi viết tài liệu này.

1. Kiểm kê, sao lưu và kiểm tra khôi phục trước thay đổi; xác định chính xác DB
   production và mốc triển khai. Không dùng seed/reset DB cho chuyển đổi.
2. Tạo hoặc xác minh tài khoản Teacher789 và cấp quyền đúng quy trình. Không
   đoán tài khoản bằng tên hiển thị, không hard-code mật khẩu.
3. Tạo BO195 có ID nội bộ, giáo viên phụ trách, chính sách lớp mặc định và các
   cấp độ/lộ trình ban đầu.
4. Gắn các lesson, bài luyện, kiểm tra và lộ trình hiện có vào BO195. **Giữ ID,
   trạng thái DRAFT/PUBLISHED/ARCHIVED, thứ tự, tài liệu, đáp án và phiên bản**.
   Không xuất bản thêm bản nháp chỉ vì đưa vào lớp.
5. Giữ người tạo cũ là admin trong lịch sử. Quyền Teacher789 đến từ việc phụ
   trách BO195, không sửa giả danh tính tác giả cũ.
6. Thêm membership cho tài khoản LEARNER hiện có; không biến admin thành học
   sinh/giáo viên hoặc xóa/tạo lại bất kỳ tài khoản hiện có nào.
7. Giữ mật khẩu, ID học sinh, phiên đăng nhập phù hợp, lượt đã xem, bài nộp,
   điểm, số lần làm và ngày hoàn thành. Không clone lesson cũ rồi bỏ ID cũ.
8. Chuyển/ánh xạ tiến độ HSK hiện tại vào ngữ cảnh BO195 có thể đối chiếu được.
   Cân nhắc module phát âm chung theo mục 9; không bắt mọi người học lại.
9. Cập nhật liên kết cũ để vẫn tới đúng bài trong BO195 qua kiểm tra quyền;
   không dùng việc đổi URL làm cơ chế bảo mật.
10. Đối chiếu số lượng và tập ID tài khoản, nội dung, tiến độ, attempts/điểm
    trước/sau; thử lại chuyển đổi phải không sinh trùng. Có kế hoạch quay lui
    cùng dữ liệu phát sinh sau khi mở hệ thống, không chỉ quay lui mã nguồn.

Sau đó chủ sản phẩm dùng Teacher789 để thêm bài vào BO195. Nếu admin vẫn có
chức năng tạo bài, form phải yêu cầu lớp đích hoặc quyền sở hữu rõ ràng; không
tự đẩy mọi bài admin tạo vào mọi lớp.

## 11. Các thay đổi cấu trúc cần dự kiến

Hiện repo chỉ có ADMIN/LEARNER, lesson dùng ràng buộc HSK + số bài toàn cục,
curriculum theo HSK toàn cục và tiến độ HSK theo user + HSK. Vì vậy cần thiết kế
migration bổ sung, không chỉ thêm menu giáo viên.

| Nhóm | Dữ liệu/trách nhiệm dự kiến |
| --- | --- |
| Quyền | TEACHER, cấp/thu hồi, phiên và quyền quản trị tương ứng |
| Lớp | ID, tên, giáo viên phụ trách, trạng thái, cấu hình lớp mặc định |
| Thành viên | Lớp + tài khoản duy nhất, trạng thái, ngày tham gia/rời |
| Mã lớp | Phạm vi lớp, vòng đời, khả năng thu hồi, hạn mức và bảo vệ dò mã |
| Nguồn giáo trình | Phiên bản tài liệu, quyền xem/tải và quyền dùng cho AI |
| Học liệu | Phạm vi lớp, người tạo, bản sao có nguồn, phiên bản |
| Lộ trình | Lớp + HSK + thứ tự; giữ HSK như phân loại chung |
| Bài giao | Lớp, phiên bản nội dung, thời gian, số lượt, chính sách điểm |
| Kết quả | Bài nộp/điểm và lịch sử duyệt/sửa, không ghi đè |
| Nhật ký | Cấp quyền, chuyển lớp, xuất bản, đổi mã, duyệt thành viên, sửa điểm |

Thiết kế bảng và API chính xác chỉ được chốt sau khi kiểm tra lại mã nguồn và
DB tại thời điểm triển khai. Không áp tên bảng trong tài liệu như schema đã có.

## 12. Phân quyền và bảo mật bắt buộc

Backend kiểm tra **role + lớp + quan hệ sở hữu/phụ trách/thành viên + trạng thái
nội dung + thời điểm thao tác** cho từng tài nguyên. ID hay lớp đang chọn ở
frontend chỉ là đầu vào, không phải bằng chứng quyền truy cập.

- Lọc phạm vi trước khi phân trang, thống kê, tìm kiếm, xuất file và truy xuất AI.
- BO195 hiển thị cho thành viên có quyền không công khai danh sách thành viên,
  email, bài nộp, điểm hoặc giáo trình nguồn cho các học sinh khác.
- Học sinh LEFT/REMOVED/BLOCKED hoặc lớp ARCHIVED không có quyền đọc nội dung,
  kết quả, tệp, tìm kiếm hoặc API xuất dữ liệu của lớp đó. Quyền lưu dữ liệu của
  admin/giáo viên không làm phát sinh quyền xem lại cho học sinh.
- Sau mất quyền: xóa cache lớp ở frontend, hủy truy vấn và cập nhật các tab khi
  phát hiện thay đổi. Endpoint/file riêng tư kiểm tra quyền trên mỗi lần đọc;
  không coi một signed URL sống lâu là cách thu hồi quyền đầy đủ. Thiết kế cache
  không để CDN phục vụ nội dung riêng tư sau thu hồi quyền.
- Không thể thu hồi thông tin người dùng đã đọc, chụp hoặc tải về trước đó.
  Cam kết mất quyền là chặn các yêu cầu truy cập tiếp theo; giao diện đang mở
  phải cập nhật khi nhận/kiểm tra được trạng thái mới, không hứa xóa mọi bản sao.
- Teacher789 chỉ xem hoạt động BO195, không xem hoạt động trong lớp khác của
  cùng học sinh. Giáo viên lớp khác cũng không xem toàn bộ hoạt động BO195.
- Không đưa đáp án, rubric nội bộ hay điểm chưa công bố vào DTO học sinh.
- Bản thu/tệp đính kèm riêng tư, giới hạn dung lượng/thời lượng, kiểm tra kiểu
  file; có chính sách đồng ý, lưu giữ và xóa phù hợp trước khi thu âm.
- Feedback của học sinh chỉ gửi tới đúng người xử lý; không tạo luồng đọc chéo
  thông tin lớp hoặc công khai đề/đáp án qua báo lỗi.
- Khi thay đổi quyền/lớp, tác vụ AI và đường tải file cũng kiểm tra lại quyền.
- Hạn mức AI được kiểm soát ở backend, có giới hạn đồng thời và chống chạy trùng;
  không tự bật dịch vụ trả phí theo hành động xuất bản hoặc đăng nhập.

## 13. Giao diện đề xuất

Học sinh giữ trang học và cách chuyển từ hiện tại. Trên giáo trình có bộ chọn
lớp: **BO195** và các lớp đã tham gia, cùng nút **Tham gia lớp bằng mã**.
Tên lớp/giáo viên hiện rõ để tránh làm nhầm bài; đường dẫn bài giữ ngữ cảnh lớp.
Chưa có lớp riêng vẫn học BO195 được nếu chưa chủ động rời/bị loại/chặn và lớp
còn hoạt động. Nếu đã rời mọi lớp, hiện màn hình tham gia lớp, không tự đăng ký
lại BO195. Không thêm màn hình nhập mã bắt buộc cho lần vào lớp mặc định.

Giáo viên có: **Tổng quan · Lớp của tôi · Giáo trình nguồn · Bài học · Bài giao
& Kiểm tra · Chấm bài · Phản hồi · Hồ sơ**. Có thể tái sử dụng khung editor admin,
nhưng quyền và dữ liệu phải đi qua use case giáo viên có phạm vi lớp.

Admin có quản lý giáo viên/lớp/nguồn tài liệu bên cạnh chức năng đang có.
Tính năng xem thử vai trò không đăng nhập giả thành học sinh hoặc ghi tiến độ
thật. Không bắt giáo viên thao tác trên một trang admin được mở quyền tạm.

## 14. Quyết định đã chốt và những điểm còn cần chốt

Các dòng ghi **Đã chốt** là quyết định người dùng đã xác nhận. Những dòng ghi
đề xuất/khuyến nghị vẫn cần chốt trước khi triển khai, không được suy thành đã duyệt:

| Quyết định | Khuyến nghị ban đầu |
| --- | --- |
| BO195 nhìn thấy hay tự là thành viên? | Là thành viên mặc định để theo dõi học, tạo một lần an toàn |
| Vào lớp riêng bằng mã có cần duyệt? | **Đã chốt: luôn cần giáo viên duyệt** |
| Học sinh được bao nhiêu lớp? | BO195 + nhiều lớp riêng, giới hạn cấu hình; một lớp đang xem |
| Có được rời BO195? | **Đã chốt: được rời và không được tự thêm lại** |
| Lớp bị lưu trữ/thành viên rời lớp? | **Đã chốt: học sinh mất quyền xem mọi nội dung lớp**; dữ liệu quản trị không tự xóa |
| Bị loại trong khi làm test? | **Đã chốt: bỏ lượt đang làm, không lưu/chấm/tính điểm**; xử lý cạnh tranh theo mục 8.1 |
| Sửa bài đã xuất bản? | **Đã chốt: không yêu cầu học lại hoặc thu hồi completion đã có** |
| Điều kiện HSK1? | **Đã chốt: phải hoàn thành phát âm ở mọi lớp, không cho giáo viên bỏ qua** |
| Cách ghi nhận phát âm, lượng từ? | Đề xuất module chung chỉ đọc; completion phát âm cá nhân được công nhận giữa các lớp |
| Giáo viên có được tải PDF? | Chỉ khi admin cấp quyền phân phối phù hợp |
| Bài chưa nộp khi tự rời/lưu trữ lớp? | Đề xuất bỏ lượt nháp như khi bị loại; cần chốt trước implement |
| Xin vào lại BO195? | Đề xuất không cần mã nhưng phải giáo viên duyệt; không tự khôi phục membership |
| Chấm AI và ngân sách? | Tắt mặc định; bật có hạn mức, người duyệt và phương án chấm tay |
| Admin tạo nội dung mới vào đâu? | Chọn lớp đích rõ ràng, chủ sản phẩm chủ yếu dùng Teacher789 |

## 15. Tiêu chí nghiệm thu tối thiểu

1. Học sinh mới đăng nhập thấy BO195, không bị buộc nhập mã.
2. Tài khoản cũ tiếp tục đăng nhập được, nội dung/tiến độ/điểm cũ được giữ.
3. Teacher789 quản lý được nội dung chuyển vào BO195; bản nháp vẫn là bản nháp.
4. Hai giáo viên tạo Bài 1 HSK1 khác nhau không xung đột và không sửa lẫn nhau.
5. Sửa từ hoặc ngữ pháp ở lớp A không làm bài lớp B thay đổi.
6. Đổi ID lớp/bài/bài nộp/file trong URL/API không vượt quyền.
7. Mã sai/hết hạn/đã đổi/tắt, lớp đầy, thành viên chờ duyệt và bị chặn đều được xử lý.
8. Yêu cầu tham gia lặp lại/nhiều tab không sinh membership trùng.
9. Tham gia một lớp không tự rời lớp khác; học sinh được rời BO195, chỉ mất
   quyền lớp vừa rời và không bị tự thêm lại khi đăng nhập.
10. Không tự thêm lại tài khoản đã bị loại/chặn ở lớp mặc định.
11. Giáo viên chỉ xem học sinh và hoạt động thuộc lớp phụ trách.
12. Học sinh không xem danh sách riêng tư, bài người khác hoặc đáp án chưa mở.
13. Lượt làm giữ đúng phiên bản đề, thời gian, số lượt và chính sách điểm.
14. Thu hồi role/chuyển giáo viên chặn quyền cũ, kể cả file/tác vụ nền.
15. Không có migration reset/seed production; đối chiếu dữ liệu và thử khôi phục.
16. Không tự kích hoạt AI hoặc tài nguyên trả phí.
17. Nhập đúng mã lớp vẫn không đọc được học liệu khi chưa được giáo viên duyệt.
18. Rời lớp/lớp lưu trữ chặn nội dung và điểm cũ, URL trực tiếp, file và cache;
    không làm mất tài khoản hoặc dữ liệu lớp khác.
19. Loại thành viên giữa test bỏ lượt nháp/câu trả lời/tệp tạm, không chấm 0;
    request lưu/nộp gửi trễ và kết quả AI đến muộn không khôi phục được lượt.
20. Kiểm thử hai thứ tự nộp/loại đồng thời và việc tham gia lại lớp; bài đã nộp
    hợp lệ trước đó được giữ nhưng không đọc được sau mất quyền.
21. Sửa/bổ sung lesson không khóa lại luyện tập hay yêu cầu người đã hoàn thành
    học lại; không tự đánh dấu các mục mới là đã xem.
22. Chưa hoàn thành phát âm thì không mở được HSK1 ở bất kỳ lớp nào kể cả URL/API
    trực tiếp. Hoàn thành rồi không cần học lại khi đổi lớp theo mô hình module
    chung; vẫn không vượt được điều kiện thành viên/lớp.

## 16. Thứ tự triển khai khi được yêu cầu

1. Chốt mục 14, kiểm kê DB và thiết kế migration bảo toàn dữ liệu.
2. Bổ sung role, lớp, membership và kiểm thử phân quyền ở backend trước.
3. Chuyển học liệu/tài khoản hiện có vào BO195 theo mục 10.
4. Thêm điều hướng lớp và khu giáo viên; kiểm tra đọc, biên soạn, xuất bản riêng lớp.
5. Thêm mã lớp, duyệt thành viên, chuyển lớp và bài giao/chấm thủ công.
6. Triển khai bốn kỹ năng/thu âm theo chính sách dữ liệu đã chốt.
7. Chỉ thêm AI sau khi kiểm định chất lượng và được duyệt chi phí.

Không cần triển khai toàn bộ các bước ngay. Mục tiêu bản đầu là lớp mặc định
BO195 và một cơ chế lớp riêng có phân quyền đúng, không thay đổi cách học hiện có
một cách không cần thiết.
