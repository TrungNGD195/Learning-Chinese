import { apiClient } from '../../lib/api/client'
import type { ResponseBodyOf } from '../../lib/api/types'

const overviewPath = '/api/v1/me/progress'
const hskProgressPath = '/api/v1/me/progress/hsk/{hsk_id}'
const lessonProgressPath = '/api/v1/me/progress/lessons/{lesson_id}'

export function getProgressOverview() {
  return apiClient<ResponseBodyOf<typeof overviewPath, 'get'>>({ method: 'GET', path: '/me/progress' })
}

export function getHskProgress(hskId: string) {
  return apiClient<ResponseBodyOf<typeof hskProgressPath, 'get'>>({
    method: 'GET', path: `/me/progress/hsk/${encodeURIComponent(hskId)}`,
  })
}

export function getLessonProgress(lessonId: string) {
  return apiClient<ResponseBodyOf<typeof lessonProgressPath, 'get'>>({
    method: 'GET', path: `/me/progress/lessons/${encodeURIComponent(lessonId)}`,
  })
}
