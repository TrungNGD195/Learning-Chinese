import { apiClient } from '../../lib/api/client'
import type { RequestBodyOf, ResponseBodyOf } from '../../lib/api/types'

const path = '/api/v1/me/vocabulary-review'
export function getReviewDeck(page: number, hskLevel?: number, lessonId?: string, shuffleSeed?: string) {
  return apiClient<ResponseBodyOf<typeof path, 'get'>>({ method: 'GET', path: '/me/vocabulary-review', query: { page, page_size: 50, ...(hskLevel ? { hsk_level: hskLevel } : {}), ...(lessonId ? { lesson_id: lessonId } : {}), ...(shuffleSeed ? { shuffle_seed: shuffleSeed } : {}) } })
}

export function getReviewLessons() {
  return apiClient<ResponseBodyOf<'/api/v1/me/vocabulary-review/lessons', 'get'>>({ method: 'GET', path: '/me/vocabulary-review/lessons' })
}

export function getReviewProgress(hskLevel?: number, lessonId?: string) {
  return apiClient<ResponseBodyOf<'/api/v1/me/vocabulary-review/progress', 'get'>>({ path: '/me/vocabulary-review/progress', query: {
    ...(hskLevel ? { hsk_level: hskLevel } : {}), ...(lessonId ? { lesson_id: lessonId } : {}),
  } })
}

export function setReviewPreference(trackingEnabled: boolean) {
  return apiClient<ResponseBodyOf<'/api/v1/me/vocabulary-review/preferences', 'put'>,
    RequestBodyOf<'/api/v1/me/vocabulary-review/preferences', 'put'>>({ method: 'PUT', path: '/me/vocabulary-review/preferences', body: { tracking_enabled: trackingEnabled } })
}

export type ReviewRating = 'LEARNING' | 'KNOWN' | null
export function setReviewState(cardId: string, status: ReviewRating, expectedVersion: number) {
  return apiClient<ResponseBodyOf<'/api/v1/me/vocabulary-review/cards/{card_id}', 'put'>,
    RequestBodyOf<'/api/v1/me/vocabulary-review/cards/{card_id}', 'put'>>({ method: 'PUT', path: `/me/vocabulary-review/cards/${encodeURIComponent(cardId)}`, body: { status, expected_version: expectedVersion } })
}
