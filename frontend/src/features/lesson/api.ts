import { apiClient } from '../../lib/api/client'
import type { ResponseBodyOf } from '../../lib/api/types'

const lessonPath = '/api/v1/lessons/{lesson_id}'
const vocabularyViewedPath = '/api/v1/lessons/{lesson_id}/theory/vocabulary/{lesson_vocabulary_id}/view'
const grammarViewedPath = '/api/v1/lessons/{lesson_id}/theory/grammar/{lesson_grammar_id}/view'
const readingCompletePath = '/api/v1/lessons/{lesson_id}/theory/readings/{reading_id}/complete'

export function completeLessonReading(lessonId: string, readingId: string, version: number) {
  return apiClient<ResponseBodyOf<typeof readingCompletePath, 'post'>, { version: number }>({
    method: 'POST', path: `/lessons/${encodeURIComponent(lessonId)}/theory/readings/${encodeURIComponent(readingId)}/complete`, body: { version },
  })
}

export function getLesson(lessonId: string) {
  return apiClient<ResponseBodyOf<typeof lessonPath, 'get'>>({
    method: 'GET', path: `/lessons/${encodeURIComponent(lessonId)}`,
  })
}

export function markVocabularyViewed(lessonId: string, lessonVocabularyId: string) {
  return apiClient<ResponseBodyOf<typeof vocabularyViewedPath, 'post'>>({
    method: 'POST',
    path: `/lessons/${encodeURIComponent(lessonId)}/theory/vocabulary/${encodeURIComponent(lessonVocabularyId)}/view`,
  })
}

export function markGrammarViewed(lessonId: string, lessonGrammarId: string) {
  return apiClient<ResponseBodyOf<typeof grammarViewedPath, 'post'>>({
    method: 'POST',
    path: `/lessons/${encodeURIComponent(lessonId)}/theory/grammar/${encodeURIComponent(lessonGrammarId)}/view`,
  })
}
