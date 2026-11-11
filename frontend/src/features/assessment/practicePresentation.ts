import type { AssessmentQuestion } from './QuestionRenderer'

export const skillLabels = { vocabulary: 'Từ vựng', grammar: 'Ngữ pháp', listening: 'Nghe hiểu', reading: 'Đọc hiểu', communication: 'Giao tiếp' }
export const difficultyLabels = { easy: 'Cơ bản', medium: 'Vận dụng', challenge: 'Thử thách' }

function shuffled<T>(values: T[], seed: string): T[] {
  const result = [...values]
  let state = [...seed].reduce((hash, char) => Math.imul(hash ^ char.charCodeAt(0), 16777619), 2166136261) >>> 0
  for (let i = result.length - 1; i > 0; i--) {
    state ^= state << 13; state ^= state >>> 17; state ^= state << 5
    const j = (state >>> 0) % (i + 1)
    ;[result[i], result[j]] = [result[j], result[i]]
  }
  return result
}

export function questionForAttempt(question: AssessmentQuestion, attemptId: string): AssessmentQuestion {
  const seed = `${attemptId}:${question.id}`
  if (question.type === 'multiple_choice') return { ...question, options: shuffled(question.options, seed) }
  if (question.type === 'matching') return { ...question, config: { ...question.config, right_items: shuffled(question.config.right_items, seed) } }
  if (question.type === 'reorder_sentence') return { ...question, config: { ...question.config, items: shuffled(question.config.items, seed) } }
  return question
}
