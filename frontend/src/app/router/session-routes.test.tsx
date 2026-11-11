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
    { element: <ProtectedRoute />, children: [{ path: '/learner', element: <p>Learner content</p> }, { path: '/pronunciation', element: <p>Learner dashboard</p> }] },
    { element: <AdminRoute />, children: [{ path: '/admin', element: <p>Admin content</p> }] },
    { path: '/login', element: <p>Login page</p> },
    { path: '/broken', element: <ThrowDuringRender />, errorElement: <RouteErrorBoundary /> },
    {
      path: '/broken-response',
      loader: () => {
        throw new Response('SYNTHETIC_RESPONSE_BODY_MUST_NOT_BE_SHOWN', {
          status: 418,
          statusText: 'SYNTHETIC_STATUS_TEXT_MUST_NOT_BE_SHOWN',
        })
      },
      element: <p>Unreachable route content</p>,
      errorElement: <RouteErrorBoundary />,
    },
  ], { initialEntries: [path] })
  return { client, router, ...render(<QueryClientProvider client={client}><RouterProvider router={router} /></QueryClientProvider>) }
}
function ThrowDuringRender(): never { throw new Error('unexpected render failure') }

beforeEach(() => vi.clearAllMocks())

describe('session-backed route guards', () => {
  it('waits while /auth/me is pending and does not redirect', () => {
    vi.mocked(authApi.getMe).mockReturnValue(new Promise(() => {}))
    renderAt('/learner')
    expect(screen.getByRole('status')).toHaveTextContent('Đang kiểm tra phiên đăng nhập')
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
    fireEvent.click(await screen.findByRole('button', { name: "Thử lại" }))
    expect(await screen.findByText('Learner content')).toBeInTheDocument()
    expect(authApi.getMe).toHaveBeenCalledTimes(2)
  })

  it('keeps cached authenticated identity during a technical refetch failure', async () => {
    vi.mocked(authApi.getMe).mockRejectedValue(new ApiError({ status: 503, code: 'HTTP_ERROR', message: 'unavailable', details: null }))
    renderAt('/learner', learner)
    expect(await screen.findByText('Learner content')).toBeInTheDocument()
    expect(screen.queryByText("Không thể xác thực phiên đăng nhập của bạn.")).not.toBeInTheDocument()
  })

  it('allows a Learner on Learner routes', () => {
    renderAt('/learner', learner)
    expect(screen.getByText('Learner content')).toBeInTheDocument()
  })

  it('allows Admin routes and keeps a Learner authenticated after Admin denial', async () => {
    const { unmount } = renderAt('/admin', admin)
    expect(screen.getByText('Admin content')).toBeInTheDocument()
    unmount()
    const { router, client } = renderAt('/admin', learner)
    expect(screen.getByTestId('admin-forbidden')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Quay lại góc học tập' })).toHaveAttribute('href', '/pronunciation')
    expect(screen.queryByText('Admin content')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('link', { name: 'Quay lại góc học tập' }))
    expect(await screen.findByText('Learner dashboard')).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/pronunciation')
    expect(client.getQueryData(queryKeys.authMe)).toEqual(learner)
  })

  it('denies an Admin from Learner routes without rendering Learner content or clearing session', async () => {
    const { router, client } = renderAt('/learner', admin)
    expect(screen.getByTestId('learner-forbidden')).toBeInTheDocument()
    expect(screen.getByText("Khu vực này dành cho tài khoản học viên.")).toBeInTheDocument()
    expect(screen.getByRole('link', { name: "Về trang quản trị" })).toHaveAttribute('href', '/admin')
    expect(screen.queryByText('Learner content')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('link', { name: "Về trang quản trị" }))
    expect(await screen.findByText('Admin content')).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/admin')
    expect(client.getQueryData(queryKeys.authMe)).toEqual(admin)
  })

  it('shows a generic message and login recovery link for unexpected route render errors', () => {
    renderAt('/broken')
    expect(screen.getByTestId('route-error-boundary')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: "Đã có sự cố xảy ra" })).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent(/^Đã xảy ra lỗi ngoài dự kiến\. Vui lòng quay lại trang học tập và thử lại\.$/)
    expect(screen.getByRole('alert')).not.toHaveTextContent('unexpected render failure')
    expect(screen.getByRole('link', { name: "Về trang học tập" })).toHaveAttribute('href', '/login')
  })

  it('does not expose route response status, statusText, or body details', async () => {
    renderAt('/broken-response')
    expect(await screen.findByTestId('route-error-boundary')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: "Đã có sự cố xảy ra" })).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent(/^Đã xảy ra lỗi ngoài dự kiến\. Vui lòng quay lại trang học tập và thử lại\.$/)
    expect(screen.getByRole('alert')).not.toHaveTextContent('418')
    expect(screen.getByRole('alert')).not.toHaveTextContent('SYNTHETIC_STATUS_TEXT_MUST_NOT_BE_SHOWN')
    expect(screen.getByRole('alert')).not.toHaveTextContent('SYNTHETIC_RESPONSE_BODY_MUST_NOT_BE_SHOWN')
    const recoveryLink = screen.getByRole('link', { name: "Về trang học tập" })
    expect(recoveryLink).toHaveAttribute('href', '/login')
    fireEvent.click(recoveryLink)
    expect(await screen.findByText('Login page')).toBeInTheDocument()
  })
})
