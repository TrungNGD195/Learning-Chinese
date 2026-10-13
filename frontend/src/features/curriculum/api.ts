import { apiClient } from '../../lib/api/client'
import type { ResponseBodyOf } from '../../lib/api/types'

const hskLevelsPath = '/api/v1/hsk-levels'
const curriculumPath = '/api/v1/hsk-levels/{hsk_id}/curriculum'

export function getHskLevels() {
  return apiClient<ResponseBodyOf<typeof hskLevelsPath, 'get'>>({ method: 'GET', path: '/hsk-levels' })
}

export function getCurriculum(hskId: string) {
  return apiClient<ResponseBodyOf<typeof curriculumPath, 'get'>>({
    method: 'GET', path: `/hsk-levels/${encodeURIComponent(hskId)}/curriculum`,
  })
}
