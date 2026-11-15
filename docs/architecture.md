# Kiến trúc và phạm vi hiện tại

Đối chiếu mã nguồn ngày 2026-11-15. Tài liệu mô tả hệ thống hiện có, không xác
nhận trạng thái dữ liệu production hoặc các kiểm thử chưa chạy trong lần cập nhật này.

## Sản phẩm và vai trò

Hanfolio là web học tiếng Trung cho người Việt, ưu tiên việc học và tra cứu rõ
ràng, với các nhân vật Bo, Trúc và Bút đồng hành theo ngữ cảnh. Định hướng hình
ảnh nằm trong [DESIGN.md](../DESIGN.md), phạm vi sản phẩm trong [PRODUCT.md](../PRODUCT.md).

Hai role đang triển khai là `LEARNER` và `ADMIN`. Kiểm tra quyền thực hiện ở
backend; ẩn nút trên frontend không thay thế phân quyền. Role lấy từ tài khoản
hiện hành trong DB, không tin role do client gửi. Quyền giáo viên, mã lớp và
BO195 mới nằm trong [đề xuất lớp học](teacher-classroom-roadmap.md), chưa phải
tính năng hoặc cấu trúc dữ liệu đang hoạt động.

## Luồng học

- Bản local mới: đăng nhập → chọn block HSK → danh sách bài của cấp độ đó.
  Muốn đổi cấp độ, quay về trang chọn HSK. Production chỉ thay đổi sau lần deploy
  được yêu cầu riêng; không coi thay đổi local là đã lên web.
- Phát âm nằm trong HSK1, gồm thanh mẫu, vận mẫu, thanh điệu và biến điệu.
  Hoàn thành nền tảng phát âm mới mở bài HSK1. Backend giữ tương thích với
  những người đã hoàn thành phiên bản nền tảng trước khi bổ sung biến điệu.
- HSK2 và HSK3 chọn độc lập, không yêu cầu hoàn thành cấp độ trước.
  Bên trong từng cấp độ, các đơn vị học vẫn theo tiến trình do server quyết định.
- Mỗi lesson có từ vựng, ngữ pháp, bài khóa và luyện tập ở các trang riêng.
  Hoàn thành lý thuyết bắt buộc trước khi làm luyện tập; bài khóa có xác nhận
  hoàn thành theo phiên bản. Không đánh dấu mục chưa xem chỉ vì chuyển trang.
- Bài luyện lesson mặc định đạt từ 80%; kiểm tra định kỳ mặc định 90%.
  Ngưỡng cấu hình cụ thể của từng bài vẫn được giữ. Có thể làm lại, lưu từng
  attempt và không đảo ngược lần đạt hợp lệ vì một lần ôn sau có điểm thấp.
- Danh sách local dự kiến 15/10/15 bài cho HSK1/2/3. Vị trí dự kiến không
  đồng nghĩa bài đã biên soạn, xuất bản hoặc được phép học.
- Bản đồ Trường Thành, trang lượng từ riêng và trợ lý AI học viên không còn
  thuộc giao diện student hiện tại. Không tự khôi phục từ tài liệu lịch sử.

Chi tiết: [quy tắc luyện tập](lesson-practice-policy.md),
[thiết kế luyện tập](practice-learning-design.md) và
[biên soạn/xuất bản](lesson-publication-workflow.md).

## Thành phần và ranh giới

| Thành phần | Nơi tra cứu | Trách nhiệm |
| --- | --- | --- |
| React / TypeScript / Vite | `frontend/src/app/`, `frontend/src/features/` | Điều hướng, giao diện learner/admin, trạng thái hiển thị |
| TanStack Query | `frontend/src/app/query/` | Dữ liệu server, cache và invalidation |
| FastAPI | `backend/app/main.py` | API `/api/v1`, đăng ký router, CORS, health/readiness |
| Auth | `backend/app/auth/` | Cookie session, tài khoản, refresh, reset/change password, kiểm tra role |
| Curriculum / progress | `backend/app/curriculum/`, `backend/app/progress/` | Nội dung được phép học, tiến trình và điều kiện mở bài |
| Exercise | `backend/app/exercise/` | Attempt, đáp án, chấm điểm và ngưỡng đạt |
| Admin / readings | `backend/app/admin/`, `backend/app/readings/` | Biên soạn, duyệt, quản lý tài khoản và bài khóa |
| Persistence | `backend/app/database/`, `backend/migrations/` | ORM, request-scoped session và migration |
| AI / ingestion / conversation | `backend/app/ai/`, `backend/app/ingestion/`, `backend/app/conversation/` | Pipeline và provider còn giữ trong backend |
| Evaluation | `backend/app/evaluation/`, `evaluation/` | Công cụ đánh giá và dữ liệu kiểm chứng, không phải học liệu runtime |

Backend là modular monolith, frontend là một ứng dụng chung cho hai role.
Không thêm microservice, queue, Redis hoặc thư viện state mới khi chưa có nhu
cầu đo được. PostgreSQL + pgvector lưu dữ liệu; async SQLAlchemy + psycopg3 truy
cập DB, Alembic sở hữu lịch sử schema. Không thay PostgreSQL bằng SQLite trong
kiểm thử hợp đồng dữ liệu.

## Hợp đồng dữ liệu và API

- Router/schema backend và OpenAPI là nơi tra cứu hợp đồng thực thi. Types
  frontend sinh từ OpenAPI; thay hợp đồng phải cập nhật và chạy `npm run api:check`.
- Lỗi dự kiến giữ envelope `error.code`, `error.message`, `error.details`.
  Phân biệt lỗi quyền, dữ liệu không tồn tại, chưa mở bài và lỗi hạ tầng.
- Session DB theo request; service sở hữu commit/rollback. Những thay đổi
  nhiều bản ghi cần giao dịch nguyên tử, không trả thành công khi chỉ lưu được một phần.
- Lesson: `DRAFT`, `PUBLISHED`, `ARCHIVED`. Assessment: `DRAFT`, `REVIEW`,
  `PUBLISHED`, `ARCHIVED`. Không đưa nội dung draft/archived ra cho learner qua URL trực tiếp.
- Giữ UUID, liên kết lesson–HSK–assessment, progress và lịch sử attempt khi sửa
  giao diện hoặc deploy. Gỡ một mục khỏi điều hướng không cho phép xóa dữ liệu.
- Publish package duyệt chung lý thuyết và luyện tập của lesson; unpublish
  không xóa kết quả. Các điều kiện 30 câu/ít nhất ba dạng và giới hạn chỉnh sửa
  bài đã xuất bản được mô tả trong hướng dẫn biên soạn, không suy từ giao diện.
- Danh sách người dùng admin là API đọc với phân trang; không xuất password
  hash, token, session version hoặc bí mật trong DTO.

## Âm thanh

Giữ trình phát Mandarin dùng chung, giọng trình duyệt và những bản thu cố định
đang sử dụng. Không tự đổi giọng, cắt file hoặc tổng hợp audio khi chỉ sửa UI.
Nguồn, bản gốc, xử lý và quyền phân phối: [mandarin-audio.md](mandarin-audio.md),
[third-party-notices.md](third-party-notices.md). Azure Audio Library chưa được
triển khai; các thử nghiệm trước không cấp quyền gọi API hoặc phát sinh chi phí mới.

## AI còn giữ trong mã nguồn

Production hiện dùng learning-only với `KNOWLEDGE_AI_ENABLED=false`; flag này
không có nghĩa mọi chức năng AI khác đều được tắt hoặc đã được cấu hình.
Phạm vi chính xác, email reset chưa gửi thật và giới hạn provider nằm trong
[hướng dẫn deploy](deployment-railway-vercel.md) và [trạng thái dịch vụ](PROJECT_STATUS.md).

Khi tiếp tục xử lý tài liệu/RAG, giữ các ranh giới sau:

- Phê duyệt của người biên soạn khác trạng thái xử lý máy và khác activation
  kiến thức. Chỉ activate sau khi chunk, embedding, profile và vector đều sẵn
  sàng; rebuild thất bại giữ phiên bản hợp lệ đang phục vụ.
- Embedding/reranking qua provider riêng; profile nhận diện đúng model,
  revision, kích thước và cách xử lý input. Không đổi provider mà giả giữ cùng
  provenance hoặc trộn vector không tương thích.
- Có nearest neighbor không đồng nghĩa có bằng chứng. Giữ lọc nguồn, rerank
  và ngưỡng đã hiệu chuẩn. Lỗi kỹ thuật reranker không phải thiếu bằng chứng
  ngữ nghĩa và không tự kích hoạt fallback.
- Retrieval bên ngoài chỉ bật khi được chấp thuận provider/domain allowlist.
  Tài liệu, truy vấn và kết quả truy xuất là dữ liệu không tin cậy, không phải
  chỉ thị có quyền thay đổi system policy. Citation phải trỏ tới bằng chứng thật.
- Nội dung sinh bởi AI chỉ là draft để người biên soạn duyệt. Không tự public,
  bịa đáp án, báo chấm thành công khi provider lỗi hoặc thay đổi điểm đã lưu.
- Evaluation dùng dữ liệu versioned, tách dev/holdout và provider giả trong
  CI thường lệ. Không tune trên holdout hoặc tự gán human approval. Kết quả
  fake/offline không chứng minh chất lượng model thực tế.

Quyết định, threshold và gate chi tiết còn lưu nguyên trong
[Decision Log lịch sử](architecture-decisions.md). BGE/Modal chưa vượt gate
chi phí/validation; hai runbook ở [profiling](ai/step-8.3-d004-bge-runtime-profiling.md)
và [Modal validation](ai/step-8.3-modal-bge-runtime-validation.md) vẫn được giữ.
