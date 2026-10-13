import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { queryKeys } from '../query/keys'
import { ApiError } from '../../lib/api/errors'
import { authApi } from '../../features/auth/api'
import { AdminRoute, ProtectedRoute } from './RouteGuards'
import { RouteErrorBoundary } from '../RouteErrorBoundary'

vi.mock('../../features/auth/api', () => ({ authApi: { getMe: vi.fn() } }))

const learner = { id: 'learner-1', email: 'learner@example.test', full_name: 'Learner', role: 'LEARNER' }
const admin = { ...learner, id: 'admin-1', role: 'ADMIN' }
function renderAt(path: string, initialUser?: typeof learner) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  if (initialUser) client.setQueryData(queryKeys.authMe, initialUser)
  const router = createMemoryRouter([
    { element: <ProtectedRoute />, children: [{ path: '/learner', element: <p>Learner content</p> }] },
    { element: <AdminRoute />, children: [{ path: '/admin', element: <p>Admin content</p> }] },
    { path: '/login', element: <p>Login page</p> },
    { path: '/broken', element: <ThrowDuringRender />, errorElement: <RouteErrorBoundary /> },
  ], { initialEntries: [path] })
  return render(<QueryClientProvider client={client}><RouterProvider router={router} /></QueryClientProvider>)
}
function ThrowDuringRender(): never { throw new Error('unexpected render failure') }

beforeEach(() => vi.clearAllMocks())

describe('session-backed route guards', () => {
  it('waits while /auth/me is pending and does not redirect', () => {
    vi.mocked(authApi.getMe).mockReturnValue(new Promise(() => {}))
    renderAt('/learner')
    expect(screen.getByRole('status')).toHaveTextContent('Checking your session')
    expect(screen.queryByText('Login page')).not.toBeInTheDocument()
  })

  it('redirects to login only after a definitive unauthenticated result', async () => {
    vi.mocked(authApi.getMe).mockRejectedValue(new ApiError({ status: 401, code: 'INVALID_REFRESH_TOKEN', message: 'invalid', details: null }))
    renderAt('/learner')
    expect(await screen.findByText('Login page')).toBeInTheDocument()
  })

  it('shows recoverable verification error and retries without redirecting on technical failure', async () => {
    vi.mocked(authApi.getMe).mockRejectedValueOnce(new ApiError({ status: 503, code: 'HTTP_ERROR', message: 'unavailable', details: null })).mockResolvedValue(learner)
    renderAt('/learner')
    fireEvent.click(await screen.findByRole('button', { name: 'Retry' }))
    expect(await screen.findByText('Learner content')).toBeInTheDocument()
    expect(authApi.getMe).toHaveBeenCalledTimes(2)
  })

  it('keeps cached authenticated identity during a technical refetch failure', async () => {
    vi.mocked(authApi.getMe).mockRejectedValue(new ApiError({ status: 503, code: 'HTTP_ERROR', message: 'unavailable', details: null }))
    renderAt('/learner', learner)
    expect(await screen.findByText('Learner content')).toBeInTheDocument()
    expect(screen.queryByText('We could not verify your session.')).not.toBeInTheDocument()
  })

  it('renders authenticated learner and D-041 Forbidden for non-admin without Admin layout', () => {
    renderAt('/learner', learner)
    expect(screen.getByText('Learner content')).toBeInTheDocument()
  })

  it('allows Admin and shows Forbidden with Dashboard link to an authenticated learner', () => {
    const { unmount } = renderAt('/admin', admin)
    expect(screen.getByText('Admin content')).toBeInTheDocument()
    unmount()
    renderAt('/admin', learner)
    expect(screen.getByTestId('admin-forbidden')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to Dashboard' })).toHaveAttribute('href', '/dashboard')
    expect(screen.queryByText('Admin content')).not.toBeInTheDocument()
  })

  it('catches unexpected route render errors at the route boundary', () => {
    renderAt('/broken')
    expect(screen.getByTestId('route-error-boundary')).toBeInTheDocument()
  })
})
