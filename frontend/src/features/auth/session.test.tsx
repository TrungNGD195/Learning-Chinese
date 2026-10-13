import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { queryClient, shouldRetryQuery } from '../../app/query/queryClient'
import { queryKeys } from '../../app/query/keys'
import { deriveSessionStatus, useSession } from './session'

function SessionProbe() {
  const session = useSession()
  return <div><p data-testid="session-status">{session.status}</p>{session.verificationError && <p role="alert">verification error</p>}</div>
}
function renderProbe() { return render(<QueryClientProvider client={queryClient}><SessionProbe /></QueryClientProvider>) }
function unauthorized(code?: string) {
  return new Response(code ? JSON.stringify({ error: { code, message: 'unauthorized', details: null } }) : null, { status: 401 })
}

afterEach(() => { cleanup(); queryClient.clear(); queryClient.setQueryDefaults(queryKeys.authMe, { retry: shouldRetryQuery }); vi.unstubAllGlobals(); vi.unstubAllEnvs() })

describe('/auth/me session bootstrap', () => {
  it('keeps a technical auth.me error UNKNOWN even when cache data is null', () => {
    expect(deriveSessionStatus(null, new Error('temporary failure'))).toBe('UNKNOWN')
    expect(deriveSessionStatus(null, { status: 503 })).toBe('UNKNOWN')
    expect(deriveSessionStatus(null, null)).toBe('UNAUTHENTICATED')
  })

  it('retains null auth.me data as UNKNOWN and exposes a technical verification error', async () => {
    queryClient.setQueryDefaults(queryKeys.authMe, { retry: false })
    queryClient.setQueryData(queryKeys.authMe, null)
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: { code: 'HTTP_ERROR', message: 'unavailable', details: null } }), { status: 503 })))
    renderProbe()
    expect(await screen.findByRole('alert')).toHaveTextContent('verification error')
    expect(screen.getByTestId('session-status')).toHaveTextContent('UNKNOWN')
    expect(queryClient.getQueryData(queryKeys.authMe)).toBeNull()
  })

  it('uses Refresh and one /auth/me replay to resolve the backend User', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    const user = { id: 'user-1', email: 'learner@example.test', full_name: 'Learner', role: 'LEARNER' }
    const fetchMock = vi.fn().mockResolvedValueOnce(unauthorized()).mockResolvedValueOnce(new Response(null, { status: 204 })).mockResolvedValueOnce(new Response(JSON.stringify(user), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    renderProbe()
    await waitFor(() => expect(screen.getByTestId('session-status')).toHaveTextContent('AUTHENTICATED'))
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual(['/api/v1/auth/me', '/api/v1/auth/refresh', '/api/v1/auth/me'])
  })

  it('maps a definitive invalid refresh to UNAUTHENTICATED', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(unauthorized()).mockResolvedValueOnce(unauthorized('INVALID_REFRESH_TOKEN')))
    renderProbe()
    await waitFor(() => expect(screen.getByTestId('session-status')).toHaveTextContent('UNAUTHENTICATED'))
  })

  it('keeps initial technical Refresh failure UNKNOWN and preserves cached User on technical refetch failure', async () => {
    queryClient.setQueryDefaults(queryKeys.authMe, { retry: shouldRetryQuery, retryDelay: 0 })
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    const fetchMock = vi.fn((input: RequestInfo | URL) => Promise.resolve(String(input).endsWith('/auth/refresh')
      ? new Response(null, { status: 503 })
      : unauthorized()))
    vi.stubGlobal('fetch', fetchMock)
    renderProbe()
    expect(await screen.findByRole('alert', {}, { timeout: 5000 })).toBeInTheDocument()
    expect(screen.getByTestId('session-status')).toHaveTextContent('UNKNOWN')
    expect(fetchMock).toHaveBeenCalledTimes(6)

    cleanup()
    queryClient.clear()
    queryClient.setQueryData(queryKeys.authMe, { id: 'cached-user', email: 'learner@example.test', full_name: 'Learner', role: 'LEARNER' })
    const secondFetch = vi.fn((input: RequestInfo | URL) => String(input).endsWith('/auth/refresh')
      ? Promise.reject(new TypeError('network unavailable'))
      : Promise.resolve(unauthorized()))
    vi.stubGlobal('fetch', secondFetch)
    renderProbe()
    await waitFor(() => expect(secondFetch).toHaveBeenCalledTimes(6), { timeout: 5000 })
    expect(screen.getByTestId('session-status')).toHaveTextContent('AUTHENTICATED')
  })
})
