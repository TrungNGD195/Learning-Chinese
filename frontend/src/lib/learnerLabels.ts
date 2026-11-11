const labels: Record<string, string> = {
  AVAILABLE: 'Có thể học', COMPLETED: 'Đã hoàn thành', LOCKED: 'Đã khóa', UNAVAILABLE: 'Chưa khả dụng',
  IN_PROGRESS: 'Đang làm', SUBMITTED: 'Đã nộp', GRADING: 'Đang chấm điểm',
  GRADED: 'Đã chấm điểm', GRADING_FAILED: 'Chấm điểm không thành công',
  PENDING: 'Đang chờ xử lý', FAILED: 'Không thành công', UNCERTAIN: 'Chưa xác định',
  DRAFT: 'Bản nháp', REVIEW: 'Chờ duyệt', PUBLISHED: 'Đã xuất bản', ARCHIVED: 'Đã lưu trữ',
  noun: 'danh từ', verb: 'động từ', adjective: 'tính từ', adverb: 'phó từ',
  pronoun: 'đại từ', numeral: 'số từ', number: 'số từ', classifier: 'lượng từ',
  'measure word': 'lượng từ', particle: 'trợ từ', conjunction: 'liên từ',
  preposition: 'giới từ', interjection: 'thán từ', phrase: 'cụm từ', greeting: 'lời chào',
  'proper noun': 'danh từ riêng',
}

/** Display labels only: API enums, authored text and saved answers stay intact. */
export function learnerLabel(value: string): string {
  return labels[value] ?? labels[value.toLowerCase()] ?? value
}
