import { apiClient } from '../../lib/api/client'
import type { QueryParametersOf, RequestBodyOf, ResponseBodyOf } from '../../lib/api/types'

const assessmentPath = '/api/v1/assessments/{assessment_id}'
const startAttemptPath = '/api/v1/assessments/{assessment_id}/attempts'
const submitAttemptPath = '/api/v1/assessment-attempts/{attempt_id}/submit'
const attemptsPath = '/api/v1/me/assessment-attempts'
const attemptPath = '/api/v1/me/assessment-attempts/{attempt_id}'

type SubmitAttemptRequest = RequestBodyOf<typeof submitAttemptPath, 'post'>
export type AssessmentAttemptFilters = QueryParametersOf<typeof attemptsPath, 'get'>

export function getAssessment(assessmentId: string) {
  return apiClient<ResponseBodyOf<typeof assessmentPath, 'get'>>({
    method: 'GET', path: `/assessments/${encodeURIComponent(assessmentId)}`,
  })
}

export function startAttempt(assessmentId: string) {
  return apiClient<ResponseBodyOf<typeof startAttemptPath, 'post'>>({
    method: 'POST', path: `/assessments/${encodeURIComponent(assessmentId)}/attempts`,
  })
}

export function submitAttempt(attemptId: string, body: SubmitAttemptRequest) {
  return apiClient<ResponseBodyOf<typeof submitAttemptPath, 'post'>, SubmitAttemptRequest>({
    method: 'POST', path: `/assessment-attempts/${encodeURIComponent(attemptId)}/submit`, body,
  })
}

export function getAttempts(filters: AssessmentAttemptFilters = {}) {
  return apiClient<ResponseBodyOf<typeof attemptsPath, 'get'>>({
    method: 'GET', path: '/me/assessment-attempts', query: filters,
  })
}

export function getAttempt(attemptId: string) {
  return apiClient<ResponseBodyOf<typeof attemptPath, 'get'>>({
    method: 'GET', path: `/me/assessment-attempts/${encodeURIComponent(attemptId)}`,
  })
}
