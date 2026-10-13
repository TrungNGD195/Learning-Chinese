import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
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
vi.mock('../dashboard/api', () => ({ getDashboard: vi.fn() }))

const learner = { id: 'user-1', email: 'learner@example.test', full_name: 'Learner One', role: 'LEARNER' }
const admin = { ...learner, id: 'admin-1', email: 'admin@example.test', role: 'ADMIN' }
const dashboard = { current_hsk: null, current_unit: null, current_lesson: null, progress_percentage: 0, continue_learning: null }
const progress = { current_hsk: 2, progress_percentage: 42.5, pronunciation_complete: true, hsk_levels: [] }

function apiError(status: number | null, code: string) {
  return new ApiError({ status, code, message: 'safe test error', details: null })
}

function renderApp(path: string, currentUser?: typeof learner) {
  queryClient.setQueryDefaults(queryKeys.authMe, { retry: false })
  if (currentUser) queryClient.setQueryData(queryKeys.authMe, currentUser)
  const router = createMemoryRouter(createAppRoutes(), { initialEntries: [path] })
  return { router, ...render(<QueryClientProvider client={queryClient}><RouterProvider router={router} /></QueryClientProvider>) }
}

beforeEach(() => {
  queryClient.clear()
  queryClient.setQueryDefaults(queryKeys.authMe, { retry: false })
  vi.clearAllMocks()
  vi.mocked(authApi.getMe).mockRejectedValue(apiError(401, 'AUTHENTICATION_REQUIRED'))
  vi.mocked(authApi.login).mockResolvedValue(learner)
  vi.mocked(authApi.register).mockResolvedValue(learner)
  vi.mocked(authApi.logout).mockResolvedValue(undefined)
  vi.mocked(authApi.changePassword).mockResolvedValue(undefined)
  vi.mocked(authApi.requestPasswordReset).mockResolvedValue(undefined)
  vi.mocked(authApi.confirmPasswordReset).mockResolvedValue(undefined)
  vi.mocked(getDashboard).mockResolvedValue(dashboard)
  vi.mocked(getProgressOverview).mockResolvedValue(progress)
})

afterEach(() => { queryClient.clear() })

describe('Login and Register session restoration', () => {
  it.each([learner, admin])('sends exact Login fields and restores /auth/me before Dashboard for role $role', async (user) => {
    vi.mocked(authApi.getMe).mockRejectedValueOnce(apiError(401, 'AUTHENTICATION_REQUIRED')).mockResolvedValueOnce(user)
    const { router } = renderApp('/login')
    fireEvent.change(await screen.findByLabelText('Email'), { target: { value: user.email } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret-pass' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/dashboard'))
    expect(authApi.login).toHaveBeenCalledTimes(1)
    expect(vi.mocked(authApi.login).mock.calls[0]?.[0]).toEqual({ email: user.email, password: 'secret-pass' })
    expect(authApi.getMe).toHaveBeenCalledTimes(2)
    expect(queryClient.getQueryData(queryKeys.authMe)).toEqual(user)
    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
  })

  it('does not navigate before authoritative /auth/me resolves and blocks duplicate Login submit', async () => {
    vi.mocked(authApi.getMe).mockRejectedValueOnce(apiError(401, 'AUTHENTICATION_REQUIRED'))
    let finish!: (value: typeof learner) => void
    vi.mocked(authApi.getMe).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve }))
    let finishLogin!: (value: typeof learner) => void
    vi.mocked(authApi.login).mockImplementationOnce(() => new Promise((resolve) => { finishLogin = resolve }))
    const { router } = renderApp('/login')
    fireEvent.change(await screen.findByLabelText('Email'), { target: { value: learner.email } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret-pass' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    await waitFor(() => expect(authApi.login).toHaveBeenCalledTimes(1))
    expect(screen.getByRole('button', { name: 'Signing in…' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Signing in…' }))
    expect(authApi.login).toHaveBeenCalledTimes(1)
    await act(async () => { finishLogin(learner) })
    await waitFor(() => expect(authApi.getMe).toHaveBeenCalledTimes(2))
    expect(router.state.location.pathname).toBe('/login')
    expect(screen.queryByRole('heading', { name: 'Dashboard' })).not.toBeInTheDocument()
    await act(async () => { finish(learner) })
    await waitFor(() => expect(router.state.location.pathname).toBe('/dashboard'))
  })

  it('requires Login fields before calling the backend', async () => {
    renderApp('/login')
    fireEvent.click(await screen.findByRole('button', { name: 'Sign in' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Enter your email and password.')
    expect(authApi.login).not.toHaveBeenCalled()
  })

  it('offers session-verification retry after successful Login without submitting credentials again', async () => {
    vi.mocked(authApi.getMe).mockRejectedValueOnce(apiError(401, 'AUTHENTICATION_REQUIRED'))
      .mockRejectedValueOnce(apiError(503, 'HTTP_ERROR')).mockResolvedValueOnce(learner)
    const { router } = renderApp('/login')
    fireEvent.change(await screen.findByLabelText('Email'), { target: { value: learner.email } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret-pass' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/could not verify .*session/i)
    expect(router.state.location.pathname).toBe('/login')
    expect(screen.queryByRole('heading', { name: 'Dashboard' })).not.toBeInTheDocument()
    expect(deriveSessionStatus(queryClient.getQueryData(queryKeys.authMe), queryClient.getQueryState(queryKeys.authMe)?.error)).toBe('UNKNOWN')
    expect(authApi.login).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: /Retry/ }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/dashboard'))
    expect(authApi.login).toHaveBeenCalledTimes(1)
  })

  it.each([
    ['INVALID_CREDENTIALS', 'Email or password is incorrect.'],
    ['ACCOUNT_DISABLED', 'This account is disabled. Contact support for help.'],
    ['NETWORK_ERROR', 'A temporary problem prevented this request. Please try again.'],
    ['SERVER_FAILURE', 'A temporary problem prevented this request. Please try again.'],
  ])('maps Login %s to safe feedback', async (code, feedback) => {
    vi.mocked(authApi.login).mockRejectedValueOnce(apiError(code === 'SERVER_FAILURE' ? 503 : code === 'ACCOUNT_DISABLED' ? 403 : code === 'INVALID_CREDENTIALS' ? 401 : null, code))
    renderApp('/login')
    fireEvent.change(await screen.findByLabelText('Email'), { target: { value: learner.email } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret-pass' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(feedback)
  })

  it('validates Register locally and sends no role or confirmation field', async () => {
    vi.mocked(authApi.getMe).mockRejectedValueOnce(apiError(401, 'AUTHENTICATION_REQUIRED')).mockResolvedValueOnce(learner)
    const { router } = renderApp('/register')
    fireEvent.change(await screen.findByLabelText('Full name'), { target: { value: '  Learner One  ' } })
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: learner.email } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret-pass' } })
    fireEvent.change(screen.getByLabelText('Confirm password'), { target: { value: 'different-pass' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create account' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Passwords do not match.')
    expect(authApi.register).not.toHaveBeenCalled()
    fireEvent.change(screen.getByLabelText('Confirm password'), { target: { value: 'secret-pass' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create account' }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/dashboard'))
    expect(authApi.register).toHaveBeenCalledTimes(1)
    expect(vi.mocked(authApi.register).mock.calls[0]?.[0]).toEqual({ full_name: 'Learner One', email: learner.email, password: 'secret-pass' })
    expect(authApi.login).not.toHaveBeenCalled()
    expect(authApi.getMe).toHaveBeenCalledTimes(2)
  })

  it('enforces the client password length range for Register', async () => {
    renderApp('/register')
    for (const [label, value] of [['Full name', 'Learner'], ['Email', learner.email], ['Password', 'short'], ['Confirm password', 'short']]) {
      fireEvent.change(await screen.findByLabelText(label), { target: { value } })
    }
    fireEvent.click(screen.getByRole('button', { name: 'Create account' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('between 8 and 128 characters')
    expect(authApi.register).not.toHaveBeenCalled()
  })

  it('offers explicit session restoration retry after successful Register without registering again', async () => {
    vi.mocked(authApi.getMe).mockRejectedValueOnce(apiError(401, 'AUTHENTICATION_REQUIRED'))
      .mockRejectedValueOnce(apiError(503, 'HTTP_ERROR')).mockResolvedValueOnce(learner)
    renderApp('/register')
    for (const [label, value] of [['Full name', 'Learner'], ['Email', learner.email], ['Password', 'secret-pass'], ['Confirm password', 'secret-pass']]) {
      fireEvent.change(await screen.findByLabelText(label), { target: { value } })
    }
    fireEvent.click(screen.getByRole('button', { name: 'Create account' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/could not verify .*session/i)
    expect(screen.queryByRole('heading', { name: 'Dashboard' })).not.toBeInTheDocument()
    expect(deriveSessionStatus(queryClient.getQueryData(queryKeys.authMe), queryClient.getQueryState(queryKeys.authMe)?.error)).toBe('UNKNOWN')
    expect(authApi.register).toHaveBeenCalledTimes(1)
    expect(authApi.login).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: /Retry/ }))
    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
    expect(authApi.register).toHaveBeenCalledTimes(1)
  })

  it.each([
    ['EMAIL_ALREADY_REGISTERED', 'An account already exists for this email.'],
    ['INVALID_PASSWORD', 'Password does not meet the required policy.'],
  ])('maps Register %s', async (code, message) => {
    vi.mocked(authApi.register).mockRejectedValueOnce(apiError(code === 'EMAIL_ALREADY_REGISTERED' ? 409 : 422, code))
    renderApp('/register')
    for (const [label, value] of [['Full name', 'Learner'], ['Email', learner.email], ['Password', 'secret-pass'], ['Confirm password', 'secret-pass']]) {
      fireEvent.change(await screen.findByLabelText(label), { target: { value } })
    }
    fireEvent.click(screen.getByRole('button', { name: 'Create account' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(message)
  })
})

describe('Forgot and reset password', () => {
  it('sends exact Forgot Password body and shows enumeration-safe acknowledgement', async () => {
    renderApp('/forgot-password')
    fireEvent.change(await screen.findByLabelText('Email'), { target: { value: learner.email } })
    fireEvent.click(screen.getByRole('button', { name: 'Send reset instructions' }))
    expect(await screen.findByRole('status')).toHaveTextContent('If an eligible account exists for that email, password-reset instructions will be sent.')
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
    fireEvent.click(screen.getByRole('button', { name: 'Send reset instructions' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('temporary problem')
    expect(email).toHaveValue(learner.email)
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByRole('status')).toHaveTextContent('If an eligible account exists')
    expect(authApi.requestPasswordReset).toHaveBeenCalledTimes(2)
  })

  it('missing reset token shows invalid-link state without calling confirm', async () => {
    renderApp('/reset-password')
    expect(await screen.findByRole('alert')).toHaveTextContent('missing or invalid')
    expect(screen.getByRole('link', { name: 'Request a new reset link' })).toHaveAttribute('href', '/forgot-password')
    expect(authApi.confirmPasswordReset).not.toHaveBeenCalled()
  })

  it('submits query token only in exact reset body, clears session data, and navigates with transient notice', async () => {
    const rawToken = 'opaque-test-token'
    queryClient.setQueryData(queryKeys.dashboard, dashboard)
    const { router } = renderApp(`/reset-password?token=${rawToken}`, learner)
    fireEvent.change(await screen.findByLabelText('New password'), { target: { value: 'new-secret-123' } })
    fireEvent.change(screen.getByLabelText('Confirm new password'), { target: { value: 'new-secret-123' } })
    await waitFor(() => expect(authApi.getMe).toHaveBeenCalledTimes(1))
    const meCallsBeforeReset = vi.mocked(authApi.getMe).mock.calls.length
    fireEvent.click(screen.getByRole('button', { name: 'Reset password' }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'))
    expect(authApi.confirmPasswordReset).toHaveBeenCalledTimes(1)
    expect(vi.mocked(authApi.confirmPasswordReset).mock.calls[0]?.[0]).toEqual({ token: rawToken, new_password: 'new-secret-123' })
    expect(authApi.getMe).toHaveBeenCalledTimes(meCallsBeforeReset)
    expect(queryClient.getQueryData(queryKeys.authMe)).toBeNull()
    expect(queryClient.getQueryData(queryKeys.dashboard)).toBeUndefined()
    expect(JSON.stringify(queryClient.getQueryCache().getAll().map((query) => [query.queryKey, query.state.data]))).not.toContain(rawToken)
    expect(await screen.findByRole('status')).toHaveTextContent('Password reset successfully. Please sign in with your new password.')
    expect(document.body.textContent).not.toContain(rawToken)
    expect(Object.values(router.state.location.state ?? {}).join(' ')).not.toContain(rawToken)
  })

  it('normalizes invalid reset tokens and does not display token values', async () => {
    vi.mocked(authApi.confirmPasswordReset).mockRejectedValueOnce(apiError(400, 'INVALID_RESET_TOKEN'))
    const rawToken = 'invalid-secret-token'
    renderApp(`/reset-password?token=${rawToken}`)
    fireEvent.change(await screen.findByLabelText('New password'), { target: { value: 'new-secret-123' } })
    fireEvent.change(screen.getByLabelText('Confirm new password'), { target: { value: 'new-secret-123' } })
    fireEvent.click(screen.getByRole('button', { name: 'Reset password' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('missing or invalid')
    expect(document.body.textContent).not.toContain(rawToken)
    expect(authApi.confirmPasswordReset).toHaveBeenCalledTimes(1)
  })
})

describe('Logout, Profile, and change password', () => {
  it('adds learner logout and clears the shared authenticated cache only after backend success', async () => {
    queryClient.setQueryData(queryKeys.dashboard, dashboard)
    const { router } = renderApp('/dashboard', learner)
    fireEvent.click(await screen.findByRole('button', { name: 'Logout' }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'))
    expect(authApi.logout).toHaveBeenCalledTimes(1)
    expect(queryClient.getQueryData(queryKeys.authMe)).toBeNull()
    expect(queryClient.getQueryData(queryKeys.dashboard)).toBeUndefined()
  })

  it('shows Logout in the existing Admin shell without changing Admin page scope', async () => {
    renderApp('/admin', admin)
    expect(await screen.findByRole('button', { name: 'Logout' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Admin Dashboard' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Logout' }))
    await waitFor(() => expect(authApi.logout).toHaveBeenCalledTimes(1))
  })

  it('keeps the session/cache after technical Logout failure and retries only on learner action', async () => {
    vi.mocked(authApi.logout).mockRejectedValueOnce(apiError(503, 'HTTP_ERROR')).mockResolvedValueOnce(undefined)
    queryClient.setQueryData(queryKeys.dashboard, dashboard)
    renderApp('/dashboard', learner)
    fireEvent.click(await screen.findByRole('button', { name: 'Logout' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Logout could not be confirmed')
    expect(queryClient.getQueryData(queryKeys.authMe)).toEqual(learner)
    expect(queryClient.getQueryData(queryKeys.dashboard)).toEqual(dashboard)
    fireEvent.click(screen.getByRole('button', { name: 'Retry logout' }))
    expect(await screen.findByRole('heading', { name: 'Login' })).toBeInTheDocument()
    expect(authApi.logout).toHaveBeenCalledTimes(2)
  })

  it('shows auth.me identity while progress loads independently and renders backend summary verbatim', async () => {
    let finish!: (value: typeof progress) => void
    vi.mocked(getProgressOverview).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve }))
    renderApp('/profile', learner)
    expect(await screen.findByText('Learner One')).toBeInTheDocument()
    expect(screen.getByText('learner@example.test')).toBeInTheDocument()
    expect(screen.getByText('Loading progress…')).toBeInTheDocument()
    await act(async () => { finish(progress) })
    expect(await screen.findByText('Current HSK: HSK 2')).toBeInTheDocument()
    expect(screen.getByText('Overall progress: 42.5%')).toBeInTheDocument()
  })

  it('renders neutral null-HSK state and keeps identity visible after Progress error with retry', async () => {
    vi.mocked(getProgressOverview).mockRejectedValueOnce(new Error('unavailable'))
    renderApp('/profile', learner)
    expect(await screen.findByText('Learner One')).toBeInTheDocument()
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load your progress summary')
    vi.mocked(getProgressOverview).mockResolvedValueOnce({ ...progress, current_hsk: null })
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByText('Current HSK: Not started yet')).toBeInTheDocument()
  })

  it('keeps cached Progress visible during a background refresh', async () => {
    queryClient.setQueryData(queryKeys.progressOverview, progress)
    let finish!: (value: typeof progress) => void
    vi.mocked(getProgressOverview).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve }))
    renderApp('/profile', learner)
    expect(await screen.findByText('Overall progress: 42.5%')).toBeInTheDocument()
    expect(screen.getByText('Refreshing progress…')).toBeInTheDocument()
    await act(async () => { finish({ ...progress, progress_percentage: 43 }) })
    expect(await screen.findByText('Overall progress: 43%')).toBeInTheDocument()
  })

  it('sends exact Change Password fields, clears cache, forces login, and does not reverify auth.me', async () => {
    queryClient.setQueryData(queryKeys.dashboard, dashboard)
    const { router } = renderApp('/profile', learner)
    fireEvent.change(await screen.findByLabelText('Current password'), { target: { value: 'old-secret' } })
    fireEvent.change(screen.getByLabelText('New password'), { target: { value: 'new-secret-123' } })
    fireEvent.change(screen.getByLabelText('Confirm new password'), { target: { value: 'new-secret-123' } })
    await waitFor(() => expect(authApi.getMe).toHaveBeenCalledTimes(1))
    const meCallsBeforeChange = vi.mocked(authApi.getMe).mock.calls.length
    fireEvent.click(screen.getByRole('button', { name: 'Change password' }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'))
    expect(authApi.changePassword).toHaveBeenCalledTimes(1)
    expect(vi.mocked(authApi.changePassword).mock.calls[0]?.[0]).toEqual({ current_password: 'old-secret', new_password: 'new-secret-123' })
    expect(authApi.getMe).toHaveBeenCalledTimes(meCallsBeforeChange)
    expect(queryClient.getQueryData(queryKeys.authMe)).toBeNull()
    expect(queryClient.getQueryData(queryKeys.dashboard)).toBeUndefined()
    expect(await screen.findByRole('status')).toHaveTextContent('Password changed successfully. Please sign in again.')
  })

  it.each([
    ['INVALID_CURRENT_PASSWORD', 'Current password is incorrect.'],
    ['INVALID_PASSWORD', 'Password does not meet the required policy.'],
    ['NETWORK_ERROR', "We couldn't confirm the password change. Please try again."],
  ])('maps Change Password %s without clearing the current session', async (code, message) => {
    vi.mocked(authApi.changePassword).mockRejectedValueOnce(apiError(code === 'INVALID_CURRENT_PASSWORD' ? 400 : code === 'INVALID_PASSWORD' ? 422 : null, code))
    renderApp('/profile', learner)
    fireEvent.change(await screen.findByLabelText('Current password'), { target: { value: 'old-secret' } })
    fireEvent.change(screen.getByLabelText('New password'), { target: { value: 'new-secret-123' } })
    fireEvent.change(screen.getByLabelText('Confirm new password'), { target: { value: 'new-secret-123' } })
    fireEvent.click(screen.getByRole('button', { name: 'Change password' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(message)
    expect(queryClient.getQueryData(queryKeys.authMe)).toEqual(learner)
  })
})

describe('D-044 public Auth route boundary', () => {
  it.each(['/login', '/register', '/forgot-password'])('redirects an authenticated User from %s to Dashboard', async (path) => {
    const { router } = renderApp(path, learner)
    await waitFor(() => expect(router.state.location.pathname).toBe('/dashboard'))
  })

  it('keeps reset accessible to authenticated users', async () => {
    renderApp('/reset-password?token=recovery-token', learner)
    expect(await screen.findByRole('heading', { name: 'Reset password' })).toBeInTheDocument()
    expect(screen.getByLabelText('New password')).toBeInTheDocument()
  })

  it('waits without redirecting while the current session is unknown', async () => {
    let finish!: (value: typeof learner) => void
    vi.mocked(authApi.getMe).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve }))
    const { router } = renderApp('/login')
    expect(await screen.findByRole('status')).toHaveTextContent('Checking your session')
    expect(router.state.location.pathname).toBe('/login')
    expect(screen.queryByRole('heading', { name: 'Login' })).not.toBeInTheDocument()
    await act(async () => { finish(learner) })
    await waitFor(() => expect(router.state.location.pathname).toBe('/dashboard'))
  })

  it('preserves recoverable technical session-verification UI on public routes', async () => {
    vi.mocked(authApi.getMe).mockRejectedValue(apiError(503, 'HTTP_ERROR'))
    const { router } = renderApp('/login')
    expect(await screen.findByRole('alert')).toHaveTextContent('We could not verify your session')
    expect(router.state.location.pathname).toBe('/login')
    expect(screen.queryByRole('heading', { name: 'Login' })).not.toBeInTheDocument()
    vi.mocked(authApi.getMe).mockRejectedValueOnce(apiError(401, 'AUTHENTICATION_REQUIRED'))
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByRole('heading', { name: 'Login' })).toBeInTheDocument()
  })
})
