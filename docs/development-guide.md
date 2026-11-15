# Nguyên tắc phát triển và bảo vệ dữ liệu

## Trước khi sửa

Đọc yêu cầu hiện tại, [kiến trúc](architecture.md) và hướng dẫn nghiệp vụ liên
quan trong [mục lục](README.md). Đối chiếu router, service, schema và test thực
tế. Decision Log giữ bằng chứng lịch sử; không coi mô tả Step cũ là yêu cầu
khôi phục tính năng hoặc một lần phê duyệt trả phí mới.

Giữ thay đổi trong phạm vi được yêu cầu. Không gộp migration, reset dữ liệu,
đổi provider hoặc deploy vào một tác vụ UI local. Phần giáo viên/lớp học là
roadmap, chỉ triển khai khi có yêu cầu riêng.

## Bảo vệ hợp đồng và lịch sử

- Quyền learner/admin kiểm tra ở backend và trên từng tài nguyên. Kiểm thử cả
  truy cập trực tiếp, sai role, tài khoản vô hiệu và tài nguyên thuộc người khác.
- Token/cookie, password hash và provider credential không xuất trong DTO,
  browser storage, log, screenshot hoặc dữ liệu kiểm thử đã commit.
- Giữ tên trường và ý nghĩa trạng thái API khi chỉ sửa giao diện; thay đổi API
  có chủ đích phải cập nhật schema, generated types và các client liên quan.
- Không viết lại migration đã áp dụng. Thay schema bằng forward migration,
  đánh giá tương thích và backup trước tác vụ có nguy cơ mất dữ liệu.
- Giữ khóa và lịch sử đã tồn tại. Không seed/restore dữ liệu local đè lên
  production, không tự publish nội dung sau sửa hoặc deploy.
- GET trong luồng learner có thể tạo progress theo hành vi hiện hữu. Không
  giả định mọi thao tác mở trang là chỉ đọc DB; dùng API admin phù hợp hoặc
  mock API khi kiểm tra giao diện và số liệu.
- Khi thay bài khóa, tôn trọng completion theo phiên bản hiện có; không tự
  áp dụng chính sách không học lại của roadmap lớp học vào dữ liệu hiện tại.

## Kiểm tra phù hợp với thay đổi

Lệnh cài đặt, test và build ở [README dự án](../README.md); trình tự CI thực tế
ở [.github/workflows/ci.yml](../.github/workflows/ci.yml).

- UI: kiểm tra desktop/mobile, nội dung thật, loading/error/empty, bàn phím và
  focus; chạy test liên quan, lint và build theo phạm vi thay đổi.
- Nghiệp vụ: kiểm tra điều kiện học, lưu/publish, retry/idempotency, rollback,
  lịch sử và quyền trên backend. Không dùng frontend để tự tính quyền mở bài.
- API: kiểm tra DTO thành công/lỗi, thông tin nhạy cảm và generated contract.
- DB: chỉ reset/seed CSDL test riêng `chinese_learning_test`; giữ guard nhận
  diện database, môi trường và schema. Playwright E2E có thể reset CSDL test.
- AI: dùng fixture/fake trong CI; chạy provider thật, benchmark, GPU hoặc
  evaluation trả phí cần yêu cầu và giới hạn chi phí riêng. Không tự retry
  vượt quota hoặc biến lỗi provider thành kết quả giả.
- Tài liệu: kiểm tra đường dẫn và phân biệt trạng thái đã làm, yêu cầu cần
  kiểm chứng, định hướng tương lai. Không chạy migration/deploy chỉ để sửa Markdown.

## Khi thiết kế tính năng mới

Đặc tả ngắn cần đủ: mục tiêu, vai trò, phạm vi, trạng thái/chuyển trạng thái,
quyền trên dữ liệu, API/DB chịu ảnh hưởng, giao dịch, lỗi/retry, chi phí, kiểm
thử và tiêu chí chấp nhận. Ghi rõ quyết định còn mở trước khi triển khai phần
phụ thuộc; tránh lập lại bộ template dài cho từng việc nhỏ.

Thay đổi liên quan auth, public API, dữ liệu lịch sử, publication, provider,
chi phí hoặc topology cần được mô tả rõ để người dùng đánh giá. Một báo cáo
PASS cũ không thay thế kiểm chứng trên thay đổi mới.
