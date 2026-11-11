import { ApiError } from '../../lib/api/errors'

const knownErrors: Record<string, string> = {
  KNOWLEDGE_AI_DISABLED: 'Xử lý và tìm kiếm tài liệu bằng AI đang tạm tắt trên bản triển khai này.',
  ADMIN_REQUIRED: "Tài khoản của bạn không có quyền quản trị.",
  NOT_FOUND: "Không tìm thấy nội dung này.",
  INVALID_FIELDS: "Kiểm tra các trường thông tin và thử lại.",
  INVALID_CURRICULUM: "Thứ tự lộ trình không hợp lệ.",
  INVALID_CURRICULUM_TARGET: "Một nội dung trong lộ trình không còn khả dụng.",
  INVALID_LESSON: "Thông tin bài học không hợp lệ.",
  LESSON_IMMUTABLE: "Bài học này không còn cho phép chỉnh sửa.",
  LESSON_CONTENT_IMMUTABLE: "Không thể chỉnh sửa nội dung của bài học đã lưu trữ.",
  LESSON_CONTENT_DETACH_DRAFT_ONLY: "Chỉ có thể gỡ nội dung khỏi bài học còn ở dạng nháp.",
  ITEM_HAS_LEARNER_HISTORY: "Nội dung đã có lịch sử học tập nên không thể gỡ.",
  INVALID_ITEM_MODE: "Thao tác với nội dung không hợp lệ.",
  READING_ORDER_CONFLICT: 'Thứ tự này đã được dùng cho một bài khóa khác. Hãy chọn thứ tự khác.',
  INVALID_ASSESSMENT: "Thông tin bài luyện tập không hợp lệ.",
  INVALID_ASSESSMENT_TARGET: "Chọn bài học hợp lệ cho bài luyện tập này.",
  INVALID_ASSESSMENT_SCOPE: "Phạm vi bài luyện tập không hợp lệ.",
  ASSESSMENT_IMMUTABLE: "Bài luyện tập này không còn cho phép chỉnh sửa.",
  ASSESSMENT_HAS_NO_QUESTIONS: "Thêm ít nhất một câu hỏi trước khi gửi duyệt.",
  LESSON_PRACTICE_REQUIRED: 'Thêm bài luyện tập trước khi xuất bản bài học.',
  LESSON_PRACTICE_NOT_READY: 'Mỗi bài luyện tập cần đủ 30 câu hỏi và ít nhất 3 dạng bài. Hãy kiểm tra lại mục Luyện tập.',
  INVALID_LIFECYCLE_TRANSITION: "Trạng thái nội dung đã thay đổi. Hệ thống đã tải lại trạng thái hiện tại.",
  INVALID_QUESTION: "Kiểm tra nội dung câu hỏi và thử lại.",
  QUESTION_TYPE_IMMUTABLE: "Không thể đổi dạng câu hỏi sau khi tạo.",
  QUESTIONS_IMMUTABLE: "Bài luyện tập này không cho phép chỉnh sửa câu hỏi.",
  QUESTION_HAS_HISTORY: "Câu hỏi đã có lịch sử làm bài nên không thể xóa.",
  INVALID_REQUEST: "Kiểm tra thông tin tài liệu và điều kiện sử dụng.",
  UNSUPPORTED_DOCUMENT_TYPE: "Chọn tệp PDF, DOCX, TXT hoặc MD.",
  DOCUMENT_TOO_LARGE: "Tài liệu vượt quá giới hạn dung lượng cho phép.",
  EMPTY_DOCUMENT: "Tệp đã chọn không có nội dung.",
  INVALID_DOCUMENT_FILE: "Tệp đã chọn không hợp lệ hoặc không đúng định dạng khai báo.",
  DUPLICATE_DOCUMENT: "Tài liệu giống hệt đã được tải lên trước đó.",
  RAW_STORAGE_FAILED: "Không thể lưu tài liệu. Vui lòng thử lại.",
  PROCESSING_ALREADY_IN_PROGRESS: "Tài liệu đang được xử lý.",
  INVALID_SOURCE_STATE: "Trạng thái tài liệu đã thay đổi. Vui lòng sử dụng trạng thái vừa tải lại.",
  INGESTION_PROCESSING_FAILED: "Xử lý thất bại. Tải lại tài liệu trước khi thử lại.",
  DOCUMENT_NOT_PREVIEW_READY: "Hiện chưa có bản xem trước để duyệt.",
  DOCUMENT_ALREADY_APPROVED: "Tài liệu đã được duyệt. Đang tải lại trạng thái hiện tại.",
  KNOWLEDGE_BUILD_FAILED: "Không thể tạo dữ liệu tra cứu. Đang tải lại trạng thái hiện tại.",
}

export function adminErrorText(error: unknown, fallback: string) {
  if (!(error instanceof ApiError)) return fallback
  if (error.code === 'ADMIN_REQUIRED') return knownErrors.ADMIN_REQUIRED
  if (error.status === 404 || error.code === 'NOT_FOUND') return knownErrors.NOT_FOUND
  const mappedMessage = knownErrors[error.code]
  if (mappedMessage) return mappedMessage
  if (error.code === 'NETWORK_ERROR' || (error.status !== null && error.status >= 500)) return "Có sự cố tạm thời. Vui lòng thử lại."
  return fallback
}

export function isAdminRequired(error: unknown) {
  return error instanceof ApiError && error.code === 'ADMIN_REQUIRED'
}

export function isNotFound(error: unknown) {
  return error instanceof ApiError && (error.status === 404 || error.code === 'NOT_FOUND')
}
