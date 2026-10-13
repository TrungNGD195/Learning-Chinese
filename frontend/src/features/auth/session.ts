import { queryOptions, useQuery } from '@tanstack/react-query'
import { ApiError, INVALID_RESPONSE_MESSAGE } from '../../lib/api/errors'
import { queryKeys } from '../../app/query/keys'
import { authApi } from './api'

export type SessionStatus = 'AUTHENTICATED' | 'UNAUTHENTICATED' | 'UNKNOWN'

export function deriveSessionStatus(data: unknown, error: unknown): SessionStatus {
  if (data) return 'AUTHENTICATED'
  if (error instanceof ApiError) {
    if (error.status === 401 || error.code === 'INVALID_REFRESH_TOKEN' || error.code === 'ACCOUNT_DISABLED') return 'UNAUTHENTICATED'
    return 'UNKNOWN'
  }
  if (error) return 'UNKNOWN'
  return data === null ? 'UNAUTHENTICATED' : 'UNKNOWN'
}

export function authMeQueryOptions() {
  return queryOptions({
    queryKey: queryKeys.authMe,
    queryFn: async () => {
      const user = await authApi.getMe()
      if (!user) {
        throw new ApiError({ status: null, code: 'INVALID_RESPONSE', message: INVALID_RESPONSE_MESSAGE, details: null })
      }
      return user
    },
  })
}

export function useSession() {
  const query = useQuery(authMeQueryOptions())
  const status = deriveSessionStatus(query.data, query.error)
  return {
    ...query,
    status,
    user: query.data ?? null,
    verificationError: status === 'UNKNOWN' ? query.error : null,
  }
}
