import { QueryClient } from '@tanstack/react-query'
import { ApiError } from '../../lib/api/errors'
import { subscribeToSessionInvalidation } from '../../lib/api/sessionInvalidation'
import { queryKeys } from './keys'

export function shouldRetryQuery(failureCount: number, error: unknown) {
  if (failureCount >= 2 || !(error instanceof ApiError)) return false
  return error.code === 'NETWORK_ERROR' || (error.status !== null && error.status >= 500)
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: shouldRetryQuery },
    mutations: { retry: false },
  },
})

export async function clearAuthenticatedSessionCache() {
  queryClient.setQueryData(queryKeys.authMe, null)
  await queryClient.cancelQueries({ predicate: (query) => query.queryKey[0] !== 'auth' })
  await new Promise<void>((resolve) => globalThis.setTimeout(resolve, 0))
  queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== 'auth' })
}

export async function prepareAuthenticatedSessionCache() {
  await queryClient.cancelQueries({ predicate: (query) => query.queryKey[0] !== 'auth' })
  await new Promise<void>((resolve) => globalThis.setTimeout(resolve, 0))
  queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== 'auth' })
  await queryClient.cancelQueries({ queryKey: queryKeys.authMe, exact: true })
  queryClient.getQueryCache().find({ queryKey: queryKeys.authMe, exact: true })?.setState({
    data: undefined,
    error: null,
    status: 'pending',
    fetchStatus: 'idle',
    dataUpdatedAt: 0,
    errorUpdatedAt: 0,
    fetchFailureCount: 0,
    fetchFailureReason: null,
  })
}

subscribeToSessionInvalidation(() => { void clearAuthenticatedSessionCache() })
