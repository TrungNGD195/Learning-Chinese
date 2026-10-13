import { apiClient } from '../../lib/api/client'
import type { RequestBodyOf, ResponseBodyOf } from '../../lib/api/types'

const sectionsPath = '/api/v1/pronunciation'
const completeSectionPath = '/api/v1/pronunciation/{section_id}/complete'

export function getSections() {
  return apiClient<ResponseBodyOf<typeof sectionsPath, 'get'>>({ method: 'GET', path: '/pronunciation' })
}

export function completeSection(sectionId: string) {
  return apiClient<
    ResponseBodyOf<typeof completeSectionPath, 'post'>,
    RequestBodyOf<typeof completeSectionPath, 'post'>
  >({ method: 'POST', path: `/pronunciation/${encodeURIComponent(sectionId)}/complete` })
}
