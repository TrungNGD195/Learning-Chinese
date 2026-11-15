# Yêu cầu bảo mật và vận hành cần kiểm chứng

Tổng hợp các yêu cầu còn hữu ích từ đặc tả triển khai cũ. Đây là yêu cầu và
checklist kiểm chứng, không phải báo cáo đã hoàn thành. Lần dọn tài liệu
2026-11-15 không truy cập cloud, chạy backup/restore hoặc xác nhận cấu hình production.

## Những gì đang có trong mã nguồn

- FastAPI `/health` kiểm tra tiến trình; `/ready` thực hiện probe DB, không
  chứng minh email, AI, backup hoặc toàn bộ tính năng đã sẵn sàng.
- Cookie auth, role guard, kiểm tra tài khoản và session version ở backend.
  Chi tiết vòng đời đăng nhập: [tab-session-policy.md](tab-session-policy.md).
- GitHub Actions kiểm tra migration, backend, frontend, API contract và E2E
  bằng DB test riêng. Không coi CI offline là kết quả đánh giá AI production.
- Railway/Vercel, volumes, migration startup và learning-only mode được ghi
  trong [hướng dẫn deploy](deployment-railway-vercel.md). Không ghi đè các
  thiết lập này chỉ vì tài liệu baseline nói chưa chọn vendor hoặc chưa có Docker app.

## Yêu cầu trước khi coi vận hành ổn định

| Hạng mục | Điều cần xác minh và bằng chứng cần lưu |
| --- | --- |
| Phiên và quyền | HTTPS, Secure/HttpOnly/SameSite cookie, refresh/revoke, role và quyền trên tài nguyên; kiểm tra origin/CORS/CSRF phù hợp topology thực tế |
| Dữ liệu đầu vào | Validate payload, loại/kích thước file, đường dẫn storage và URL ra ngoài; không tin file/tài liệu do người dùng cung cấp |
| Chống lạm dụng | Đánh giá rate limit cho auth và API tốn tài nguyên; kiểm chứng HTTP 429 và hành vi retry, không chỉ dựa vào lỗi rate limit từ provider |
| Secret và log | Secret ở môi trường backend bảo mật; log có stage/error để chẩn đoán nhưng không chứa password, token, API key hoặc nội dung riêng tư mặc định |
| Backup DB | Lịch backup ít nhất hằng ngày, có bằng chứng job thành công và cảnh báo thất bại; ghi retention và nơi lưu thực tế |
| Storage | Uploaded documents và dữ liệu cần giữ sống qua redeploy; xác minh retention/backup theo hạ tầng thực tế |
| Restore | Thử phục hồi vào môi trường cô lập, xác minh tài khoản, liên kết lesson/assessment/progress và file storage; không thử bằng cách ghi đè production |
| RPO/RTO | Ghi mục tiêu thực tế dựa trên lịch backup và thời gian restore đã đo, không mặc định hạ tầng đã bảo đảm |
| Migration/release | Backup phù hợp, tương thích phiên bản, migration failure ngăn startup, phương án phục hồi/rollback đã xét rủi ro dữ liệu |
| Smoke | Auth, deep link/reload, learner/admin, draft visibility, progression và chức năng đã cấu hình; dùng tài khoản test cô lập, không sửa tài khoản thật |

Không có bằng chứng restore thành công, backup hiện hành hoặc rate limit
trong lần rà soát tài liệu này; không đánh dấu các hạng mục đó PASS. Đặc biệt,
email reset vẫn được mô tả là placeholder chưa gửi trong tài liệu deploy:
cần kiểm chứng adapter thật trước khi quảng bá chức năng khôi phục mật khẩu.

## Ranh giới chi phí và AI

BGE/Modal vẫn tạm dừng vì gate phương thức thanh toán/chi phí. Không thêm
payment method, cấp GPU, chạy cache population/re-embedding hoặc bật AI chỉ
vì hợp nhất tài liệu. Xem [trạng thái hiện hành](PROJECT_STATUS.md) và
[Decision Log](architecture-decisions.md).

Khi được yêu cầu bật AI, phải kiểm tra riêng cấu hình provider, quota/budget,
ngưỡng chất lượng, timeout/rate limit, log redaction và hành vi fail an toàn.
Những gate evaluation trả phí/human review chưa hoàn thành vẫn còn hiệu lực;
không tự chuyển thành PASS sau khi test offline đạt.
