import { apiClient } from '../../lib/api/client'
import type { ResponseBodyOf } from '../../lib/api/types'

const dashboardPath = '/api/v1/me/dashboard'

export function getDashboard() {
  return apiClient<ResponseBodyOf<typeof dashboardPath, 'get'>>({ method: 'GET', path: '/me/dashboard' })
}
