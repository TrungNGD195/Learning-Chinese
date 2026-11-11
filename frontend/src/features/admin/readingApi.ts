import { apiClient } from '../../lib/api/client'
import type { RequestBodyOf, ResponseBodyOf } from '../../lib/api/types'

const readingsPath = '/api/v1/admin/lessons/{lesson_id}/readings'
const readingPath = '/api/v1/admin/lessons/{lesson_id}/readings/{reading_id}'
export type ReadingInput = RequestBodyOf<typeof readingsPath, 'post'>
export const listLessonReadings = (lessonId: string) => apiClient<ResponseBodyOf<typeof readingsPath, 'get'>>({ method: 'GET', path: `/admin/lessons/${encodeURIComponent(lessonId)}/readings` })
export const createLessonReading = (lessonId: string, body: ReadingInput) => apiClient<ResponseBodyOf<typeof readingsPath, 'post'>, ReadingInput>({ method: 'POST', path: `/admin/lessons/${encodeURIComponent(lessonId)}/readings`, body })
export const updateLessonReading = (lessonId: string, readingId: string, body: ReadingInput) => apiClient<ResponseBodyOf<typeof readingPath, 'put'>, ReadingInput>({ method: 'PUT', path: `/admin/lessons/${encodeURIComponent(lessonId)}/readings/${encodeURIComponent(readingId)}`, body })
export const deleteLessonReading = (lessonId: string, readingId: string) => apiClient<ResponseBodyOf<typeof readingPath, 'delete'>>({ method: 'DELETE', path: `/admin/lessons/${encodeURIComponent(lessonId)}/readings/${encodeURIComponent(readingId)}` })
