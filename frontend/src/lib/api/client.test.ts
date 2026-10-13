import { QueryClient } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { waitFor } from '@testing-library/react'
import { queryClient, shouldRetryQuery } from '../../app/query/queryClient'
import { queryKeys } from '../../app/query/keys'
import { ApiError } from './errors'
import { apiClient, normalizeApiBaseUrl } from './client'
import { notifySessionInvalidated, subscribeToSessionInvalidation } from './sessionInvalidation'

afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs() })

describe('Step 4.2 API transport contract', () => {
  it('accepts absolute and same-origin API roots and normalizes trailing slashes', () => {
    expect(normalizeApiBaseUrl('  https://api.example.test/api/v1///  ')).toBe('https://api.example.test/api/v1')
    expect(normalizeApiBaseUrl('/api/v1///')).toBe('/api/v1')
  })

  it.each([undefined, '', '   '])('requires VITE_API_BASE_URL for %s', async (value) => {
    vi.stubEnv('VITE_API_BASE_URL', value ?? '')
    await expect(apiClient({ path: '/auth/me' })).rejects.toThrow('VITE_API_BASE_URL is required')
  })

  it.each(['localhost:8000/api/v1', 'ftp://api.example.test/api/v1', '/backend', '//api.example.test/api/v1'])(
    'rejects invalid API root %s', async (value) => {
      vi.stubEnv('VITE_API_BASE_URL', value)
      await expect(apiClient({ path: '/auth/me' })).rejects.toThrow(/VITE_API_BASE_URL/)
    },
  )

  it('does not duplicate the configured API prefix and rejects prefixed feature paths', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.test/api/v1/')
    await expect(apiClient({ path: '/api/v1/auth/me' })).rejects.toThrow('must not repeat the /api/v1 prefix')
    await expect(apiClient({ path: 'auth/me' })).rejects.toThrow('API paths must be relative to the configured API root')
  })

  it('includes credentials and Accept, and adds JSON Content-Type only when a body exists', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.test/api/v1')
    const fetchMock = vi.fn().mockResolvedValueOnce(new Response('{"user":"learner"}', { status: 200 }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)
    await apiClient({ path: '/auth/me' })
    expect(fetchMock.mock.calls[0][0]).toBe('https://api.example.test/api/v1/auth/me')
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ credentials: 'include', headers: { Accept: 'application/json' } })
    expect((fetchMock.mock.calls[0][1] as RequestInit).headers).not.toHaveProperty('Content-Type')
    await apiClient({ method: 'POST', path: '/auth/login', body: { email: 'a@example.test' } })
    expect((fetchMock.mock.calls[1][1] as RequestInit).headers).toEqual({ Accept: 'application/json', 'Content-Type': 'application/json' })
    expect((fetchMock.mock.calls[1][1] as RequestInit).body).toBe('{"email":"a@example.test"}')
  })

  it('passes FormData by identity without JSON serialization or a manual multipart Content-Type', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    const fetchMock = vi.fn().mockResolvedValue(new Response('{"id":"document-1"}', { status: 201 }))
    vi.stubGlobal('fetch', fetchMock)
    const formData = new FormData()
    formData.append('title', 'Source')
    await apiClient({ method: 'POST', path: '/admin/documents', body: formData })
    const init = fetchMock.mock.calls[0][1] as RequestInit
    expect(init.body).toBe(formData)
    expect(init.body).toBeInstanceOf(FormData)
    expect(init.headers).toEqual({ Accept: 'application/json' })
    expect(init.credentials).toBe('include')
  })

  it('serializes scalar query values and omits null and undefined', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1/')
    const fetchMock = vi.fn().mockResolvedValue(new Response('{"items":[]}', { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    await apiClient({ path: '/me/assessment-attempts', query: { page: 2, include: true, blank: '', omittedNull: null, omittedUndefined: undefined } })
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/me/assessment-attempts?page=2&include=true&blank=')
  })

  it('parses typed JSON and returns undefined for empty 200, 202, 204, and 205 responses', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    const fetchMock = vi.fn().mockResolvedValueOnce(new Response('{"count":3}', { status: 200 }))
    for (const status of [200, 202, 204, 205]) fetchMock.mockResolvedValueOnce(new Response(null, { status }))
    vi.stubGlobal('fetch', fetchMock)
    await expect(apiClient<{ count: number }>({ path: '/me/dashboard' })).resolves.toEqual({ count: 3 })
    for (let index = 0; index < 4; index += 1) await expect(apiClient({ path: '/auth/logout' })).resolves.toBeUndefined()
  })

  it('maps malformed success JSON to INVALID_RESPONSE without exposing the body', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('private malformed payload', { status: 202 })))
    await expect(apiClient({ path: '/auth/password-reset/request' })).rejects.toMatchObject({ status: 202, code: 'INVALID_RESPONSE', details: null })
  })

  it('preserves the backend error status, code, message, and details', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: { code: 'INVALID_FILTER', message: 'Filter rejected', details: { field: 'page' } } }), { status: 422 })))
    await expect(apiClient({ path: '/me/assessment-attempts' })).rejects.toMatchObject({ status: 422, code: 'INVALID_FILTER', message: 'Filter rejected', details: { field: 'page' } })
  })

  it.each([
    ['<html><body>proxy exception private detail</body></html>', 502],
    ['{"error":', 502],
    ['{"error":{"code":4,"message":false}}', 400],
  ])('normalizes malformed HTTP %s responses without leaking the body', async (body, status) => {
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body, { status })))
    try {
      await apiClient({ path: '/auth/me' })
      throw new Error('Expected request to fail')
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError)
      expect(error).toMatchObject({ status, code: 'HTTP_ERROR', details: null })
      expect((error as Error).message).toBe('The request failed')
    }
  })

  it('maps network failures to a safe canonical NETWORK_ERROR', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('private transport detail')))
    await expect(apiClient({ path: '/auth/me' })).rejects.toMatchObject({ status: null, code: 'NETWORK_ERROR', message: 'Network request failed', details: null })
  })

  it('does not remap a canonical ApiError after receiving an HTTP response', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{"error":{"code":"ACCOUNT_DISABLED","message":"Disabled","details":null}}', { status: 403 })))
    await expect(apiClient({ path: '/auth/me' })).rejects.toMatchObject({ status: 403, code: 'ACCOUNT_DISABLED' })
  })
})

function apiError(status: number, code = 'HTTP_ERROR') {
  return new Response(JSON.stringify({ error: { code, message: 'failed', details: null } }), { status, headers: { 'Content-Type': 'application/json' } })
}

describe('central API session recovery', () => {
  it('refreshes once and replays a JSON POST with the same body exactly once', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(apiError(401))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true }), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    await expect(apiClient({ method: 'POST', path: '/messages', body: { content: 'hello' } })).resolves.toEqual({ ok: true })
    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(['/api/v1/messages', '/api/v1/auth/refresh', '/api/v1/messages'])
    expect(JSON.parse((fetchMock.mock.calls[0][1] as RequestInit).body as string)).toEqual({ content: 'hello' })
    expect(fetchMock.mock.calls[2][1]).toMatchObject(fetchMock.mock.calls[0][1])
  })

  it('shares one refresh across concurrent eligible 401 responses', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    let releaseRefresh!: (response: Response) => void
    let reachedRefresh!: () => void
    const refreshStarted = new Promise<void>((resolve) => { reachedRefresh = resolve })
    const refreshResponse = new Promise<Response>((resolve) => { releaseRefresh = resolve })
    const seen = new Map<string, number>()
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/auth/refresh')) { reachedRefresh(); return refreshResponse }
      const count = (seen.get(url) ?? 0) + 1
      seen.set(url, count)
      return Promise.resolve(count === 1 ? apiError(401) : new Response(JSON.stringify({ path: url }), { status: 200 }))
    })
    vi.stubGlobal('fetch', fetchMock)
    const first = apiClient({ path: '/me/dashboard' })
    const second = apiClient({ path: '/me/progress' })
    await refreshStarted
    releaseRefresh(new Response(null, { status: 204 }))
    await expect(Promise.all([first, second])).resolves.toHaveLength(2)
    expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/auth/refresh'))).toHaveLength(1)
    expect(seen.get('/api/v1/me/dashboard')).toBe(2)
    expect(seen.get('/api/v1/me/progress')).toBe(2)
  })

  it('shares a definitive Refresh failure across all concurrent requests and invalidates once', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    const invalidated = vi.fn()
    const unsubscribe = subscribeToSessionInvalidation(invalidated)
    let reachedRefresh!: () => void
    const refreshStarted = new Promise<void>((resolve) => { reachedRefresh = resolve })
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.endsWith('/auth/refresh')) { reachedRefresh(); return Promise.resolve(apiError(401, 'INVALID_REFRESH_TOKEN')) }
      return Promise.resolve(apiError(401))
    })
    vi.stubGlobal('fetch', fetchMock)
    const pending = Promise.allSettled([apiClient({ path: '/me/dashboard' }), apiClient({ path: '/me/progress' })])
    await refreshStarted
    const results = await pending
    expect(results.map((result) => result.status)).toEqual(['rejected', 'rejected'])
    expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/auth/refresh'))).toHaveLength(1)
    expect(invalidated).toHaveBeenCalledTimes(1)
    unsubscribe()
  })

  it('does not refresh a replayed 401 or recurse on /auth/refresh', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    const fetchMock = vi.fn().mockResolvedValueOnce(apiError(401)).mockResolvedValueOnce(new Response(null, { status: 204 })).mockResolvedValueOnce(apiError(401))
    vi.stubGlobal('fetch', fetchMock)
    await expect(apiClient({ path: '/me/dashboard' })).rejects.toBeInstanceOf(ApiError)
    expect(fetchMock).toHaveBeenCalledTimes(3)
    fetchMock.mockClear()
    fetchMock.mockResolvedValue(apiError(401))
    await expect(apiClient({ method: 'POST', path: '/auth/refresh' })).rejects.toBeInstanceOf(ApiError)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it.each(['/auth/login', '/auth/register', '/auth/password-reset/request', '/auth/password-reset/confirm', '/auth/logout'])('%s is excluded from automatic refresh', async (path) => {
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    const fetchMock = vi.fn().mockResolvedValue(apiError(401))
    vi.stubGlobal('fetch', fetchMock)
    await expect(apiClient({ method: 'POST', path })).rejects.toBeInstanceOf(ApiError)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('invalidates session on disabled account but not ordinary authorization 403', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    const invalidated = vi.fn()
    const unsubscribe = subscribeToSessionInvalidation(invalidated)
    const fetchMock = vi.fn().mockResolvedValueOnce(apiError(403, 'ACCOUNT_DISABLED')).mockResolvedValueOnce(apiError(403, 'ADMIN_REQUIRED'))
    vi.stubGlobal('fetch', fetchMock)
    await expect(apiClient({ path: '/auth/me' })).rejects.toMatchObject({ code: 'ACCOUNT_DISABLED' })
    expect(invalidated).toHaveBeenCalledTimes(1)
    await expect(apiClient({ path: '/admin/lessons' })).rejects.toMatchObject({ code: 'ADMIN_REQUIRED' })
    expect(invalidated).toHaveBeenCalledTimes(1)
    unsubscribe()
  })

  it('does not invalidate the session on a technical refresh failure', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    const invalidated = vi.fn()
    const unsubscribe = subscribeToSessionInvalidation(invalidated)
    const fetchMock = vi.fn().mockResolvedValueOnce(apiError(401)).mockResolvedValueOnce(apiError(503))
    vi.stubGlobal('fetch', fetchMock)
    await expect(apiClient({ path: '/auth/me' })).rejects.toMatchObject({ status: 503 })
    expect(invalidated).not.toHaveBeenCalled()
    unsubscribe()
  })

  it('retries a final technical Refresh 503 twice, with one bounded recovery per Query attempt', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    const fetchMock = vi.fn((input: RequestInfo | URL) => Promise.resolve(String(input).endsWith('/auth/refresh') ? apiError(503) : apiError(401)))
    vi.stubGlobal('fetch', fetchMock)
    const client = new QueryClient({ defaultOptions: { queries: { retry: shouldRetryQuery, retryDelay: 0 } } })
    await expect(client.fetchQuery({ queryKey: ['test', 'auth-recovery-503'], queryFn: () => apiClient({ path: '/auth/me' }) })).rejects.toMatchObject({ status: 503 })
    expect(fetchMock).toHaveBeenCalledTimes(6)
    expect(fetchMock.mock.calls.map(([url]) => String(url))).toEqual([
      '/api/v1/auth/me', '/api/v1/auth/refresh',
      '/api/v1/auth/me', '/api/v1/auth/refresh',
      '/api/v1/auth/me', '/api/v1/auth/refresh',
    ])
    client.clear()
  })

  it('retries a final Refresh NETWORK_ERROR at most twice', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    const fetchMock = vi.fn((input: RequestInfo | URL) => String(input).endsWith('/auth/refresh')
      ? Promise.reject(new TypeError('offline'))
      : Promise.resolve(apiError(401)))
    vi.stubGlobal('fetch', fetchMock)
    const client = new QueryClient({ defaultOptions: { queries: { retry: shouldRetryQuery, retryDelay: 0 } } })
    await expect(client.fetchQuery({ queryKey: ['test', 'auth-recovery-network'], queryFn: () => apiClient({ path: '/auth/me' }) })).rejects.toMatchObject({ status: null, code: 'NETWORK_ERROR' })
    expect(fetchMock).toHaveBeenCalledTimes(6)
    expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/auth/refresh'))).toHaveLength(3)
    client.clear()
  })

  it('does not Query-retry definitive Refresh rejection and invalidates the session once', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    const invalidated = vi.fn()
    const unsubscribe = subscribeToSessionInvalidation(invalidated)
    const fetchMock = vi.fn((input: RequestInfo | URL) => Promise.resolve(String(input).endsWith('/auth/refresh') ? apiError(401, 'INVALID_REFRESH_TOKEN') : apiError(401)))
    vi.stubGlobal('fetch', fetchMock)
    const client = new QueryClient({ defaultOptions: { queries: { retry: shouldRetryQuery, retryDelay: 0 } } })
    await expect(client.fetchQuery({ queryKey: ['test', 'invalid-refresh'], queryFn: () => apiClient({ path: '/auth/me' }) })).rejects.toMatchObject({ code: 'INVALID_REFRESH_TOKEN' })
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(invalidated).toHaveBeenCalledTimes(1)
    unsubscribe()
    client.clear()
  })

  it('invalidates ACCOUNT_DISABLED and does not Query-retry it', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    const invalidated = vi.fn()
    const unsubscribe = subscribeToSessionInvalidation(invalidated)
    const fetchMock = vi.fn().mockResolvedValue(apiError(403, 'ACCOUNT_DISABLED'))
    vi.stubGlobal('fetch', fetchMock)
    const client = new QueryClient({ defaultOptions: { queries: { retry: shouldRetryQuery, retryDelay: 0 } } })
    await expect(client.fetchQuery({ queryKey: ['test', 'account-disabled'], queryFn: () => apiClient({ path: '/auth/me' }) })).rejects.toMatchObject({ code: 'ACCOUNT_DISABLED' })
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(invalidated).toHaveBeenCalledTimes(1)
    unsubscribe()
    client.clear()
  })

  it('does not retry a final replayed 401 or refresh again', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    const invalidated = vi.fn()
    const unsubscribe = subscribeToSessionInvalidation(invalidated)
    const fetchMock = vi.fn().mockResolvedValueOnce(apiError(401)).mockResolvedValueOnce(new Response(null, { status: 204 })).mockResolvedValueOnce(apiError(401))
    vi.stubGlobal('fetch', fetchMock)
    const client = new QueryClient({ defaultOptions: { queries: { retry: shouldRetryQuery, retryDelay: 0 } } })
    await expect(client.fetchQuery({ queryKey: ['test', 'replayed-401'], queryFn: () => apiClient({ path: '/auth/me' }) })).rejects.toMatchObject({ status: 401 })
    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(invalidated).toHaveBeenCalledTimes(1)
    unsubscribe()
    client.clear()
  })
})

describe('Query retry policy', () => {
  it.each([new ApiError({ status: null, code: 'NETWORK_ERROR', message: 'network', details: null }), new ApiError({ status: 503, code: 'HTTP_ERROR', message: 'server', details: null })])('allows two bounded retries for transient reads', async (failure) => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: shouldRetryQuery, retryDelay: 0 } } })
    const queryFn = vi.fn().mockRejectedValue(failure)
    await expect(client.fetchQuery({ queryKey: ['retry'], queryFn })).rejects.toBe(failure)
    expect(queryFn).toHaveBeenCalledTimes(3)
    client.clear()
  })

  it.each([400, 401, 403, 404, 409, 422])('does not retry HTTP %s', async (status) => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: shouldRetryQuery, retryDelay: 0 } } })
    const queryFn = vi.fn().mockRejectedValue(new ApiError({ status, code: 'HTTP_ERROR', message: 'failed', details: null }))
    await expect(client.fetchQuery({ queryKey: ['no-retry', status], queryFn })).rejects.toBeInstanceOf(ApiError)
    expect(queryFn).toHaveBeenCalledTimes(1)
    client.clear()
  })

  it('does not retry mutations and invalidation bridge clears authenticated server cache', async () => {
    expect(queryClient.getDefaultOptions().mutations?.retry).toBe(false)
    queryClient.setQueryData(queryKeys.authMe, { id: 'u', role: 'LEARNER' })
    queryClient.setQueryData(queryKeys.dashboard, { progress_percentage: 55 })
    queryClient.setQueryData(queryKeys.assessment('a'), { id: 'a' })
    notifySessionInvalidated()
    expect(queryClient.getQueryData(queryKeys.authMe)).toBeNull()
    await waitFor(() => {
      expect(queryClient.getQueryData(queryKeys.dashboard)).toBeUndefined()
      expect(queryClient.getQueryData(queryKeys.assessment('a'))).toBeUndefined()
    })
  })
})
