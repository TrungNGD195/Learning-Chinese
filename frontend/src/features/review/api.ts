import { apiClient } from '../../lib/api/client'
import type { ResponseBodyOf } from '../../lib/api/types'

const path = '/api/v1/me/vocabulary-review'
export function getReviewDeck(page: number, hskLevel?: number, lessonId?: string) {
  return apiClient<ResponseBodyOf<typeof path, 'get'>>({ method: 'GET', path: '/me/vocabulary-review', query: { page, page_size: 50, ...(hskLevel ? { hsk_level: hskLevel } : {}), ...(lessonId ? { lesson_id: lessonId } : {}) } })
}

export function getReviewLessons() {
  return apiClient<ResponseBodyOf<'/api/v1/me/vocabulary-review/lessons', 'get'>>({ method: 'GET', path: '/me/vocabulary-review/lessons' })
}
