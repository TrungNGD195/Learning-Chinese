import { apiClient } from '../../lib/api/client'
import type { RequestBodyOf, ResponseBodyOf } from '../../lib/api/types'

const sectionsPath = '/api/v1/pronunciation'
const completeSectionPath = '/api/v1/pronunciation/{section_id}/complete'
const lessonPath = '/api/v1/pronunciation/lesson'
const advancePath = '/api/v1/pronunciation/lesson/advance'
const finishPath = '/api/v1/pronunciation/lesson/complete'
export type PronunciationLessonState = ResponseBodyOf<typeof lessonPath, 'get'>
type AdvanceBody = RequestBodyOf<typeof advancePath, 'post'>

export function getSections() {
  return apiClient<ResponseBodyOf<typeof sectionsPath, 'get'>>({ method: 'GET', path: '/pronunciation' })
}

export function completeSection(sectionId: string) {
  return apiClient<
    ResponseBodyOf<typeof completeSectionPath, 'post'>,
    RequestBodyOf<typeof completeSectionPath, 'post'>
  >({ method: 'POST', path: `/pronunciation/${encodeURIComponent(sectionId)}/complete` })
}

export function getPronunciationLesson() {
  return apiClient<PronunciationLessonState>({ method: 'GET', path: '/pronunciation/lesson' })
}

export function advancePronunciation(sectionCode: AdvanceBody['section_code'], stepIndex: number) {
  return apiClient<ResponseBodyOf<typeof advancePath, 'post'>, AdvanceBody>({
    method: 'POST', path: '/pronunciation/lesson/advance', body: { section_code: sectionCode, step_index: stepIndex },
  })
}

export function finishPronunciationLesson() {
  return apiClient<ResponseBodyOf<typeof finishPath, 'post'>>({ method: 'POST', path: '/pronunciation/lesson/complete' })
}
