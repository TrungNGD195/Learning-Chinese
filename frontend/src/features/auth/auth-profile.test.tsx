import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { queryClient } from '../../app/query/queryClient'
import { queryKeys } from '../../app/query/keys'
import { ApiError } from '../../lib/api/errors'
import { getDashboard } from '../dashboard/api'
import { getProgressOverview } from '../progress/api'
import { createAppRoutes } from '../../app/router/routes'
import { authApi } from './api'
import { deriveSessionStatus } from './session'

vi.mock('./api', () => ({ authApi: {
  register: vi.fn(), login: vi.fn(), getMe: vi.fn(), refresh: vi.fn(), logout: vi.fn(), logoutAll: vi.fn(),
  changePassword: vi.fn(), requestPasswordReset: vi.fn(), confirmPasswordReset: vi.fn(),
} }))
vi.mock('../progress/api', () => ({ getProgressOverview: vi.fn(), getHskProgress: vi.fn(), getLessonProgress: vi.fn() }))
vi.mock('../curriculum/api',()=>({getHskLevels:vi.fn().mockResolvedValue([]),getCurriculum:vi.fn()}))
vi.mock('../pronunciation/api',()=>({getPronunciationLesson:vi.fn().mockResolvedValue({sections:[],completed_at:null})}))
vi.mock('../dashboard/api', () => ({ getDashboard: vi.fn() }))
vi.mock('../admin/api', async (importOriginal) => ({
  ...await importOriginal<typeof import('../admin/api')>(),
  listAdminLessons: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 3 }),
  listAdminAssessments: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 2 }),
  listAdminDocuments: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 1 }),
  listHskLevels: vi.fn().mockResolvedValue([]),
}))

const learner = { id: 'user-1', email: 'learner@example.test', full_name: 'Learner One', role: 'LEARNER' }
const admin = { ...learner, id: 'admin-1', email: 'admin@example.test', role: 'ADMIN' }
const dashboard = { current_hsk: null, current_unit: null, current_lesson: null, progress_percentage: 0, continue_learning: null }
const progress = { current_hsk: 2, progress_percentage: 42.5, pronunciation_complete: true, hsk_levels: [] }

function apiError(status: number | null, code: string) {
  return new ApiError({ status, code, message: 'safe test error', details: null })
}

async function endServerSession() {
  vi.mocked(authApi.getMe).mockRejectedValue(apiError(401, 'AUTHENTICATION_REQUIRED'))
}

function renderApp(path: string, currentUser?: typeof learner) {
  queryClient.setQueryDefaults(queryKeys.authMe, { retry: false })
  if (currentUser) {
    vi.mocked(authApi.getMe).mockResolvedValue(currentUser)
    queryClient.setQueryData(queryKeys.authMe, currentUser)
  }
  const router = createMemoryRouter(createAppRoutes(), { initialEntries: [path] })
  return { router, ...render(<QueryClientProvider client={queryClient}><RouterProvider router={router} /></QueryClientProvider>) }
}

beforeEach(() => {
  queryClient.clear()
  queryClient.setQueryDefaults(queryKeys.authMe, { retry: false })
  vi.clearAllMocks()
  for (const method of Object.values(authApi)) vi.mocked(method).mockReset()
  vi.mocked(authApi.getMe).mockRejectedValue(apiError(401, 'AUTHENTICATION_REQUIRED'))
  vi.mocked(authApi.login).mockResolvedValue(learner)
  vi.mocked(authApi.register).mockResolvedValue(learner)
  vi.mocked(authApi.logout).mockImplementation(endServerSession)
  vi.mocked(authApi.changePassword).mockImplementation(endServerSession)
  vi.mocked(authApi.requestPasswordReset).mockResolvedValue(undefined)
  vi.mocked(authApi.confirmPasswordReset).mockImplementation(endServerSession)
  vi.mocked(getDashboard).mockResolvedValue(dashboard)
  vi.mocked(getProgressOverview).mockResolvedValue(progress)
})

afterEach(async () => {
  // Session clearing yields once before removing cached learner data. Wait for
  // the previous mutation before another test seeds the shared query client.
  await waitFor(() => expect(queryClient.isMutating()).toBe(0))
  queryClient.clear()
})

describe('Login and Register session restoration', () => {
  it.each([[learner, '/pronunciation'], [admin, '/admin']] as const)('sends exact Login fields and routes from restored /auth/me role $user.role', async (user, destination) => {
    vi.mocked(authApi.getMe).mockRejectedValueOnce(apiError(401, 'AUTHENTICATION_REQUIRED')).mockResolvedValueOnce(user)
    const { router } = renderApp('/login')
    fireEvent.change(await screen.findByLabelText('Email'), { target: { value: user.email } })
    fireEvent.change(screen.getByLabelText("Mật khẩu"), { target: { value: 'secret-pass' } })
    fireEvent.click(screen.getByRole('button', { name: "Đăng nhập" }))
    await waitFor(() => expect(router.state.location.pathname).toBe(destination))
    expect(authApi.login).toHaveBeenCalledTimes(1)
    expect(vi.mocked(authApi.login).mock.calls[0]?.[0]).toEqual({ email: user.email, password: 'secret-pass' })
    expect(authApi.getMe).toHaveBeenCalledTimes(2)
    expect(queryClient.getQueryData(queryKeys.authMe)).toEqual(user)
    if (destination === '/pronunciation') expect(await screen.findByRole('heading', { name: "Giáo trình của bạn" })).toBeInTheDocument()
    else expect(await screen.findByRole('heading', { name: 'Quản trị học liệu' })).toBeInTheDocument()
  })

  it('does not navigate before authoritative /auth/me resolves and blocks duplicate Login submit', async () => {
    vi.mocked(authApi.getMe).mockRejectedValueOnce(apiError(401, 'AUTHENTICATION_REQUIRED'))
    let finish!: (value: typeof learner) => void
    vi.mocked(authApi.getMe).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve }))
    let finishLogin!: (value: typeof learner) => void
    vi.mocked(authApi.login).mockImplementationOnce(() => new Promise((resolve) => { finishLogin = resolve }))
    const { router } = renderApp('/login')
    fireEvent.change(await screen.findByLabelText('Email'), { target: { value: learner.email } })
    fireEvent.change(screen.getByLabelText("Mật khẩu"), { target: { value: 'secret-pass' } })
    fireEvent.click(screen.getByRole('button', { name: "Đăng nhập" }))
    await waitFor(() => expect(authApi.login).toHaveBeenCalledTimes(1))
    expect(screen.getByRole('button', { name: "Đang đăng nhập…" })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: "Đang đăng nhập…" }))
    expect(authApi.login).toHaveBeenCalledTimes(1)
    await act(async () => { finishLogin(learner) })
    await waitFor(() => expect(authApi.getMe).toHaveBeenCalledTimes(2))
    expect(router.state.location.pathname).toBe('/login')
    expect(screen.queryByRole('heading', { name: "Giáo trình của bạn" })).not.toBeInTheDocument()
    await act(async () => { finish(learner) })
    await waitFor(() => expect(router.state.location.pathname).toBe('/pronunciation'))
  })

  it('requires Login fields before calling the backend', async () => {
    renderApp('/login')
    fireEvent.click(await screen.findByRole('button', { name: "Đăng nhập" }))
    expect(await screen.findByRole('alert')).toHaveTextContent("Vui lòng nhập email và mật khẩu.")
    expect(authApi.login).not.toHaveBeenCalled()
  })

  it('offers session-verification retry after successful Login without submitting credentials again', async () => {
    vi.mocked(authApi.getMe).mockRejectedValueOnce(apiError(401, 'AUTHENTICATION_REQUIRED'))
      .mockRejectedValueOnce(apiError(503, 'HTTP_ERROR')).mockResolvedValueOnce(learner)
    const { router } = renderApp('/login')
    fireEvent.change(await screen.findByLabelText('Email'), { target: { value: learner.email } })
    fireEvent.change(screen.getByLabelText("Mật khẩu"), { target: { value: 'secret-pass' } })
    fireEvent.click(screen.getByRole('button', { name: "Đăng nhập" }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/chưa thể xác thực phiên/i)
    expect(router.state.location.pathname).toBe('/login')
    expect(screen.queryByRole('heading', { name: "Giáo trình của bạn" })).not.toBeInTheDocument()
    expect(deriveSessionStatus(queryClient.getQueryData(queryKeys.authMe), queryClient.getQueryState(queryKeys.authMe)?.error)).toBe('UNKNOWN')
    expect(authApi.login).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: /Thử/ }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/pronunciation'))
    expect(authApi.login).toHaveBeenCalledTimes(1)
  })

  it('uses the restored Admin role after successful Login session-verification retry', async () => {
    vi.mocked(authApi.getMe).mockRejectedValueOnce(apiError(401, 'AUTHENTICATION_REQUIRED'))
      .mockRejectedValueOnce(apiError(503, 'HTTP_ERROR')).mockResolvedValueOnce(admin)
    const { router } = renderApp('/login')
    fireEvent.change(await screen.findByLabelText('Email'), { target: { value: admin.email } })
    fireEvent.change(screen.getByLabelText("Mật khẩu"), { target: { value: 'secret-pass' } })
    fireEvent.click(screen.getByRole('button', { name: "Đăng nhập" }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/chưa thể xác thực phiên/i)
    expect(router.state.location.pathname).toBe('/login')
    fireEvent.click(screen.getByRole('button', { name: /Thử/ }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/admin'))
    expect(authApi.login).toHaveBeenCalledTimes(1)
  })

  it.each([
    ['INVALID_CREDENTIALS', "Email hoặc mật khẩu chưa chính xác."],
    ['ACCOUNT_DISABLED', "Tài khoản đã bị vô hiệu hóa. Vui lòng liên hệ hỗ trợ."],
    ['NETWORK_ERROR', "Có sự cố tạm thời. Vui lòng thử lại."],
    ['SERVER_FAILURE', "Có sự cố tạm thời. Vui lòng thử lại."],
  ])('maps Login %s to safe feedback', async (code, feedback) => {
    vi.mocked(authApi.login).mockRejectedValueOnce(apiError(code === 'SERVER_FAILURE' ? 503 : code === 'ACCOUNT_DISABLED' ? 403 : code === 'INVALID_CREDENTIALS' ? 401 : null, code))
    renderApp('/login')
    fireEvent.change(await screen.findByLabelText('Email'), { target: { value: learner.email } })
    fireEvent.change(screen.getByLabelText("Mật khẩu"), { target: { value: 'secret-pass' } })
    fireEvent.click(screen.getByRole('button', { name: "Đăng nhập" }))
    expect(await screen.findByRole('alert')).toHaveTextContent(feedback)
  })

  it('validates Register locally and sends no role or confirmation field', async () => {
    vi.mocked(authApi.getMe).mockRejectedValueOnce(apiError(401, 'AUTHENTICATION_REQUIRED')).mockResolvedValueOnce(learner)
    const { router } = renderApp('/register')
    fireEvent.change(await screen.findByLabelText("Họ và tên"), { target: { value: '  Learner One  ' } })
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: learner.email } })
    fireEvent.change(screen.getByLabelText("Mật khẩu"), { target: { value: 'secret-pass' } })
    fireEvent.change(screen.getByLabelText("Xác nhận mật khẩu"), { target: { value: 'different-pass' } })
    fireEvent.click(screen.getByRole('button', { name: "Tạo tài khoản" }))
    expect(await screen.findByRole('alert')).toHaveTextContent("Mật khẩu xác nhận chưa khớp.")
    expect(authApi.register).not.toHaveBeenCalled()
    fireEvent.change(screen.getByLabelText("Xác nhận mật khẩu"), { target: { value: 'secret-pass' } })
    fireEvent.click(screen.getByRole('button', { name: "Tạo tài khoản" }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/pronunciation'))
    expect(authApi.register).toHaveBeenCalledTimes(1)
    expect(vi.mocked(authApi.register).mock.calls[0]?.[0]).toEqual({ full_name: 'Learner One', email: learner.email, password: 'secret-pass' })
    expect(authApi.login).not.toHaveBeenCalled()
    expect(authApi.getMe).toHaveBeenCalledTimes(2)
  })

  it('enforces the client password length range for Register', async () => {
    renderApp('/register')
    for (const [label, value] of [["Họ và tên", 'Learner'], ['Email', learner.email], ["Mật khẩu", 'short'], ["Xác nhận mật khẩu", 'short']]) {
      fireEvent.change(await screen.findByLabelText(label), { target: { value } })
    }
    fireEvent.click(screen.getByRole('button', { name: "Tạo tài khoản" }))
    expect(await screen.findByRole('alert')).toHaveTextContent('từ 8 đến 128 ký tự')
    expect(authApi.register).not.toHaveBeenCalled()
  })

  it('offers explicit session restoration retry after successful Register without registering again', async () => {
    vi.mocked(authApi.getMe).mockRejectedValueOnce(apiError(401, 'AUTHENTICATION_REQUIRED'))
      .mockRejectedValueOnce(apiError(503, 'HTTP_ERROR')).mockResolvedValueOnce(learner)
    renderApp('/register')
    for (const [label, value] of [["Họ và tên", 'Learner'], ['Email', learner.email], ["Mật khẩu", 'secret-pass'], ["Xác nhận mật khẩu", 'secret-pass']]) {
      fireEvent.change(await screen.findByLabelText(label), { target: { value } })
    }
    fireEvent.click(screen.getByRole('button', { name: "Tạo tài khoản" }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/chưa thể xác thực phiên/i)
    expect(screen.queryByRole('heading', { name: "Giáo trình của bạn" })).not.toBeInTheDocument()
    expect(deriveSessionStatus(queryClient.getQueryData(queryKeys.authMe), queryClient.getQueryState(queryKeys.authMe)?.error)).toBe('UNKNOWN')
    expect(authApi.register).toHaveBeenCalledTimes(1)
    expect(authApi.login).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: /Thử/ }))
    expect(await screen.findByRole('heading', { name: "Giáo trình của bạn" })).toBeInTheDocument()
    expect(authApi.register).toHaveBeenCalledTimes(1)
  })

  it.each([
    ['EMAIL_ALREADY_REGISTERED', 'Email này đã được đăng ký tài khoản.'],
    ['INVALID_PASSWORD', "Mật khẩu chưa đáp ứng yêu cầu bảo mật."],
  ])('maps Register %s', async (code, message) => {
    vi.mocked(authApi.register).mockRejectedValueOnce(apiError(code === 'EMAIL_ALREADY_REGISTERED' ? 409 : 422, code))
    renderApp('/register')
    for (const [label, value] of [["Họ và tên", 'Learner'], ['Email', learner.email], ["Mật khẩu", 'secret-pass'], ["Xác nhận mật khẩu", 'secret-pass']]) {
      fireEvent.change(await screen.findByLabelText(label), { target: { value } })
    }
    fireEvent.click(screen.getByRole('button', { name: "Tạo tài khoản" }))
    expect(await screen.findByRole('alert')).toHaveTextContent(message)
  })
})

describe('Forgot and reset password', () => {
  it('sends exact Forgot Password body and shows enumeration-safe acknowledgement', async () => {
    renderApp('/forgot-password')
    fireEvent.change(await screen.findByLabelText('Email'), { target: { value: learner.email } })
    fireEvent.click(screen.getByRole('button', { name: "Gửi liên kết đặt lại mật khẩu" }))
    expect(await screen.findByRole('status')).toHaveTextContent('Nếu email này thuộc tài khoản hợp lệ, hướng dẫn đặt lại mật khẩu sẽ được gửi đến bạn.')
    expect(authApi.requestPasswordReset).toHaveBeenCalledTimes(1)
    expect(vi.mocked(authApi.requestPasswordReset).mock.calls[0]?.[0]).toEqual({ email: learner.email })
    expect(screen.queryByText('This account exists.')).not.toBeInTheDocument()
    expect(screen.queryByText('This account does not exist.')).not.toBeInTheDocument()
  })

  it('preserves Forgot email and permits an explicit technical retry', async () => {
    vi.mocked(authApi.requestPasswordReset).mockRejectedValueOnce(apiError(null, 'NETWORK_ERROR')).mockResolvedValueOnce(undefined)
    renderApp('/forgot-password')
    const email = await screen.findByLabelText('Email')
    fireEvent.change(email, { target: { value: learner.email } })
    fireEvent.click(screen.getByRole('button', { name: "Gửi liên kết đặt lại mật khẩu" }))
    expect(await screen.findByRole('alert')).toHaveTextContent('sự cố tạm thời')
    expect(email).toHaveValue(learner.email)
    fireEvent.click(screen.getByRole('button', { name: "Thử lại" }))
    expect(await screen.findByRole('status')).toHaveTextContent('Nếu email này thuộc tài khoản hợp lệ')
    expect(authApi.requestPasswordReset).toHaveBeenCalledTimes(2)
  })

  it('missing reset token shows invalid-link state without calling confirm', async () => {
    renderApp('/reset-password')
    expect(await screen.findByRole('alert')).toHaveTextContent('bị thiếu hoặc không hợp lệ')
    expect(screen.getByRole('link', { name: "Yêu cầu liên kết đặt lại mật khẩu mới" })).toHaveAttribute('href', '/forgot-password')
    expect(authApi.confirmPasswordReset).not.toHaveBeenCalled()
  })

  it('submits query token only in exact reset body, clears session data, and navigates with transient notice', async () => {
    const rawToken = 'opaque-test-token'
    queryClient.setQueryData(queryKeys.dashboard, dashboard)
    const { router } = renderApp(`/reset-password?token=${rawToken}`, learner)
    fireEvent.change(await screen.findByLabelText("Mật khẩu mới"), { target: { value: 'new-secret-123' } })
    fireEvent.change(screen.getByLabelText("Xác nhận mật khẩu mới"), { target: { value: 'new-secret-123' } })
    await waitFor(() => expect(authApi.getMe).toHaveBeenCalledTimes(1))
    const meCallsBeforeReset = vi.mocked(authApi.getMe).mock.calls.length
    fireEvent.click(screen.getByRole('button', { name: "Đặt lại mật khẩu" }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'))
    expect(authApi.confirmPasswordReset).toHaveBeenCalledTimes(1)
    expect(vi.mocked(authApi.confirmPasswordReset).mock.calls[0]?.[0]).toEqual({ token: rawToken, new_password: 'new-secret-123' })
    expect(authApi.getMe).toHaveBeenCalledTimes(meCallsBeforeReset)
    expect(queryClient.getQueryData(queryKeys.authMe)).toBeNull()
    expect(queryClient.getQueryData(queryKeys.dashboard)).toBeUndefined()
    expect(JSON.stringify(queryClient.getQueryCache().getAll().map((query) => [query.queryKey, query.state.data]))).not.toContain(rawToken)
    expect(await screen.findByRole('status')).toHaveTextContent("Đã đặt lại mật khẩu thành công. Vui lòng đăng nhập bằng mật khẩu mới.")
    expect(document.body.textContent).not.toContain(rawToken)
    expect(Object.values(router.state.location.state ?? {}).join(' ')).not.toContain(rawToken)
  })

  it('normalizes invalid reset tokens and does not display token values', async () => {
    vi.mocked(authApi.confirmPasswordReset).mockRejectedValueOnce(apiError(400, 'INVALID_RESET_TOKEN'))
    const rawToken = 'invalid-secret-token'
    renderApp(`/reset-password?token=${rawToken}`)
    fireEvent.change(await screen.findByLabelText("Mật khẩu mới"), { target: { value: 'new-secret-123' } })
    fireEvent.change(screen.getByLabelText("Xác nhận mật khẩu mới"), { target: { value: 'new-secret-123' } })
    fireEvent.click(screen.getByRole('button', { name: "Đặt lại mật khẩu" }))
    expect(await screen.findByRole('alert')).toHaveTextContent('bị thiếu hoặc không hợp lệ')
    expect(document.body.textContent).not.toContain(rawToken)
    expect(authApi.confirmPasswordReset).toHaveBeenCalledTimes(1)
  })
})

describe('Logout, Profile, and change password', () => {
  it('adds learner logout and clears the shared authenticated cache only after backend success', async () => {
    queryClient.setQueryData(queryKeys.dashboard, dashboard)
    const { router } = renderApp('/pronunciation', learner)
    const logout = await screen.findByRole('button', { name: "Đăng xuất" })
    expect(logout.closest('.logout-action')).toBeInTheDocument()
    expect(logout.closest('.learner-shell .logout-action')).toBeInTheDocument()
    expect(logout.closest('.academy-sidebar')).toBeInTheDocument()
    expect(logout.closest('.academy-topbar')).toBeNull()
    fireEvent.click(logout)
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'))
    expect(authApi.logout).toHaveBeenCalledTimes(1)
    expect(queryClient.getQueryData(queryKeys.authMe)).toBeNull()
    expect(queryClient.getQueryData(queryKeys.dashboard)).toBeUndefined()
  })

  it('shows Logout in the existing Admin shell without changing Admin page scope', async () => {
    renderApp('/admin', admin)
    const logout = await screen.findByRole('button', { name: 'Đăng xuất' })
    expect(logout.closest('.logout-action')).toBeInTheDocument()
    expect(logout.closest('.admin-sidebar > .logout-action')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Quản trị học liệu' })).toBeInTheDocument()
    fireEvent.click(logout)
    await waitFor(() => expect(authApi.logout).toHaveBeenCalledTimes(1))
    expect(await screen.findByRole('heading', { name: "Đăng nhập" })).toBeInTheDocument()
  })

  it('keeps explanatory logout failure feedback and alert semantics in the Admin shell', async () => {
    vi.mocked(authApi.logout).mockRejectedValueOnce(apiError(503, 'HTTP_ERROR'))
    renderApp('/admin', admin)
    const logout = await screen.findByRole('button', { name: 'Đăng xuất' })
    const logoutRegion = within(logout.closest('.logout-action') as HTMLElement)
    fireEvent.click(logout)
    expect(await logoutRegion.findByRole('alert')).toHaveTextContent('Chưa thể xác nhận đăng xuất. Phiên đăng nhập vẫn đang hoạt động; bạn có thể thử lại.')
    expect(screen.getByRole('button', { name: 'Thử đăng xuất lại' })).toBeEnabled()
    expect(authApi.logout).toHaveBeenCalledTimes(1)
  })

  it('keeps the session/cache after technical Logout failure and retries only on learner action', async () => {
    vi.mocked(authApi.logout).mockRejectedValueOnce(apiError(503, 'HTTP_ERROR')).mockImplementationOnce(endServerSession)
    queryClient.setQueryData(queryKeys.dashboard, dashboard)
    renderApp('/pronunciation', learner)
    await screen.findByRole('heading', {name:'Giáo trình của bạn'})
    await waitFor(() => expect(queryClient.getQueryData(queryKeys.dashboard)).toEqual(dashboard))
    fireEvent.click(await screen.findByRole('button', { name: "Đăng xuất" }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Chưa thể xác nhận đăng xuất')
    expect(queryClient.getQueryData(queryKeys.authMe)).toEqual(learner)
    expect(queryClient.getQueryData(queryKeys.dashboard)).toEqual(dashboard)
    fireEvent.click(screen.getByRole('button', { name: "Thử đăng xuất lại" }))
    expect(await screen.findByRole('heading', { name: "Đăng nhập" })).toBeInTheDocument()
    expect(authApi.logout).toHaveBeenCalledTimes(2)
  })

  it('shows auth.me identity while progress loads independently and renders backend summary verbatim', async () => {
    let finish!: (value: typeof progress) => void
    vi.mocked(getProgressOverview).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve }))
    renderApp('/profile', learner)
    expect(await screen.findByText('Learner One')).toBeInTheDocument()
    expect(screen.getByText('learner@example.test')).toBeInTheDocument()
    expect(screen.getByText("Đang tải tiến độ…")).toBeInTheDocument()
    await act(async () => { finish(progress) })
    expect(await screen.findByText('HSK hiện tại: HSK 2')).toBeInTheDocument()
    expect(screen.getByText('Tiến độ tổng quan: 42.5%')).toBeInTheDocument()
  })

  it('renders neutral null-HSK state and keeps identity visible after Progress error with retry', async () => {
    vi.mocked(getProgressOverview).mockRejectedValueOnce(new Error('unavailable'))
    renderApp('/profile', learner)
    expect(await screen.findByText('Learner One')).toBeInTheDocument()
    expect(await screen.findByRole('alert')).toHaveTextContent('Không thể tải tổng quan tiến độ của bạn')
    vi.mocked(getProgressOverview).mockResolvedValueOnce({ ...progress, current_hsk: null })
    fireEvent.click(screen.getByRole('button', { name: "Thử lại" }))
    expect(await screen.findByText('HSK hiện tại: Chưa bắt đầu')).toBeInTheDocument()
  })

  it('keeps cached Progress visible during a background refresh', async () => {
    queryClient.setQueryData(queryKeys.progressOverview, progress)
    let finish!: (value: typeof progress) => void
    vi.mocked(getProgressOverview).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve }))
    renderApp('/profile', learner)
    expect(await screen.findByText('Tiến độ tổng quan: 42.5%')).toBeInTheDocument()
    expect(screen.getByText("Đang cập nhật tiến độ…")).toBeInTheDocument()
    await act(async () => { finish({ ...progress, progress_percentage: 43 }) })
    expect(await screen.findByText('Tiến độ tổng quan: 43%')).toBeInTheDocument()
  })

  it('sends exact Change Password fields, clears cache, forces login, and does not reverify auth.me', async () => {
    queryClient.setQueryData(queryKeys.dashboard, dashboard)
    const { router } = renderApp('/profile', learner)
    fireEvent.change(await screen.findByLabelText("Mật khẩu hiện tại"), { target: { value: 'old-secret' } })
    fireEvent.change(screen.getByLabelText("Mật khẩu mới"), { target: { value: 'new-secret-123' } })
    fireEvent.change(screen.getByLabelText("Xác nhận mật khẩu mới"), { target: { value: 'new-secret-123' } })
    await waitFor(() => expect(authApi.getMe).toHaveBeenCalledTimes(1))
    const meCallsBeforeChange = vi.mocked(authApi.getMe).mock.calls.length
    fireEvent.click(screen.getByRole('button', { name: "Đổi mật khẩu" }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'))
    expect(authApi.changePassword).toHaveBeenCalledTimes(1)
    expect(vi.mocked(authApi.changePassword).mock.calls[0]?.[0]).toEqual({ current_password: 'old-secret', new_password: 'new-secret-123' })
    expect(authApi.getMe).toHaveBeenCalledTimes(meCallsBeforeChange)
    expect(queryClient.getQueryData(queryKeys.authMe)).toBeNull()
    expect(queryClient.getQueryData(queryKeys.dashboard)).toBeUndefined()
    expect(await screen.findByRole('status')).toHaveTextContent("Đã đổi mật khẩu thành công. Vui lòng đăng nhập lại.")
  })

  it.each([
    ['INVALID_CURRENT_PASSWORD', "Mật khẩu hiện tại chưa chính xác."],
    ['INVALID_PASSWORD', "Mật khẩu chưa đáp ứng yêu cầu bảo mật."],
    ['NETWORK_ERROR', "Chưa thể xác nhận việc đổi mật khẩu. Vui lòng thử lại."],
  ])('maps Change Password %s without clearing the current session', async (code, message) => {
    vi.mocked(authApi.changePassword).mockRejectedValueOnce(apiError(code === 'INVALID_CURRENT_PASSWORD' ? 400 : code === 'INVALID_PASSWORD' ? 422 : null, code))
    renderApp('/profile', learner)
    fireEvent.change(await screen.findByLabelText("Mật khẩu hiện tại"), { target: { value: 'old-secret' } })
    fireEvent.change(screen.getByLabelText("Mật khẩu mới"), { target: { value: 'new-secret-123' } })
    fireEvent.change(screen.getByLabelText("Xác nhận mật khẩu mới"), { target: { value: 'new-secret-123' } })
    fireEvent.click(screen.getByRole('button', { name: "Đổi mật khẩu" }))
    expect(await screen.findByRole('alert')).toHaveTextContent(message)
    expect(queryClient.getQueryData(queryKeys.authMe)).toEqual(learner)
  })
})

describe('public Auth route boundary', () => {
  it.each([[learner, '/pronunciation'], [admin, '/admin']] as const)('%s redirects authenticated public-auth pages by /auth/me role', async (user, destination) => {
    for (const path of ['/login', '/register', '/forgot-password']) {
      const { router, unmount } = renderApp(path, user)
      await waitFor(() => expect(router.state.location.pathname).toBe(destination))
      unmount()
      queryClient.clear()
    }
  })

  it.each([learner, admin])('keeps reset accessible for authenticated role $role', async (user) => {
    renderApp('/reset-password?token=recovery-token', user)
    expect(await screen.findByRole('heading', { name: "Đặt lại mật khẩu" })).toBeInTheDocument()
    expect(screen.getByLabelText("Mật khẩu mới")).toBeInTheDocument()
  })

  it('waits without redirecting while the current session is unknown and then uses the restored role', async () => {
    let finish!: (value: typeof learner) => void
    vi.mocked(authApi.getMe).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve }))
    const { router } = renderApp('/login')
    expect(await screen.findByRole('status')).toHaveTextContent('Đang kiểm tra phiên đăng nhập')
    expect(router.state.location.pathname).toBe('/login')
    expect(screen.queryByRole('heading', { name: "Đăng nhập" })).not.toBeInTheDocument()
    await act(async () => { finish(admin) })
    await waitFor(() => expect(router.state.location.pathname).toBe('/admin'))
  })

  it('preserves recoverable technical session-verification UI on public routes', async () => {
    vi.mocked(authApi.getMe).mockRejectedValue(apiError(503, 'HTTP_ERROR'))
    const { router } = renderApp('/login')
    expect(await screen.findByRole('alert')).toHaveTextContent('Không thể xác thực phiên đăng nhập của bạn')
    expect(router.state.location.pathname).toBe('/login')
    expect(screen.queryByRole('heading', { name: "Đăng nhập" })).not.toBeInTheDocument()
    vi.mocked(authApi.getMe).mockRejectedValueOnce(apiError(401, 'AUTHENTICATION_REQUIRED'))
    fireEvent.click(screen.getByRole('button', { name: "Thử lại" }))
    expect(await screen.findByRole('heading', { name: "Đăng nhập" })).toBeInTheDocument()
  })
})
