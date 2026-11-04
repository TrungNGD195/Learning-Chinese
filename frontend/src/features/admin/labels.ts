const labels: Record<string, string> = {
  DRAFT: 'Bản nháp', REVIEW: 'Chờ duyệt', PUBLISHED: 'Đã xuất bản', ARCHIVED: 'Đã lưu trữ',
  LESSON_EXERCISE: 'Luyện tập bài học', PERIODIC_TEST: 'Kiểm tra định kỳ', LESSON: 'Bài học',
  UPLOADED: 'Đã tải lên', PROCESSING: 'Đang xử lý', PREVIEW_READY: 'Sẵn sàng duyệt', FAILED: 'Xử lý thất bại',
  PENDING: 'Chờ duyệt', APPROVED: 'Đã duyệt', REJECTED: 'Đã từ chối',
  NOT_STARTED: 'Chưa bắt đầu', QUEUED: 'Đang chờ', BUILDING: 'Đang tạo dữ liệu', READY: 'Sẵn sàng', ACTIVE: 'Đang hoạt động',
  INACTIVE: 'Chưa kích hoạt', SKIPPED: 'Đã bỏ qua', SUCCEEDED: 'Thành công', COMPLETED: 'Hoàn thành',
  CURRICULUM_MATERIAL: 'Giáo trình', INTERNAL_AUTHORED: 'Tài liệu nội bộ', vi: 'Tiếng Việt', zh: 'Tiếng Trung', en: 'Tiếng Anh',
  EASY: 'Dễ', MEDIUM: 'Trung bình', HARD: 'Khó',
}
export function adminLabel(value: string | null | undefined) { return value ? labels[value] ?? value : '—' }
export function adminDate(value: string | null | undefined) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Chưa xác định' : new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}
