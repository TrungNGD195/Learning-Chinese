import { useEffect, useState, type FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router'
import { clearAuthenticatedSessionCache, prepareAuthenticatedSessionCache } from '../../app/query/queryClient'
import { ApiError } from '../../lib/api/errors'
import { authApi } from './api'
import { authMeQueryOptions } from './session'
import { Alert, Button, PageHeader, Surface } from '../../components/ui'

const fieldClass = 'auth-field'

function isTechnicalError(error: unknown) {
  return error instanceof ApiError && (error.code === 'NETWORK_ERROR' || (error.status !== null && error.status >= 500))
}

function safeFormError(error: unknown) {
  return isTechnicalError(error) ? 'A temporary problem prevented this request. Please try again.' : 'We could not complete this request. Please try again.'
}

async function restoreAuthoritativeSession(queryClient: ReturnType<typeof useQueryClient>) {
  await prepareAuthenticatedSessionCache()
  const user = await queryClient.fetchQuery(authMeQueryOptions())
  if (!user) throw new ApiError({ status: null, code: 'INVALID_RESPONSE', message: 'Session verification failed', details: null })
  return user
}

export function LoginPage() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [formError, setFormError] = useState<string | null>(null)
  const [restoring, setRestoring] = useState(false)
  const mutation = useMutation({ mutationFn: authApi.login, retry: false })
  const [notice] = useState((location.state as { notice?: string } | null)?.notice)
  useEffect(() => {
    if (notice === 'password-reset' || notice === 'password-changed') void navigate(location.pathname, { replace: true, state: null })
  }, [location.pathname, navigate, notice])

  const restore = async () => {
    setRestoring(true)
    setFormError(null)
    try {
      const user = await restoreAuthoritativeSession(queryClient)
      await navigate(user.role === 'ADMIN' ? '/admin' : '/dashboard', { replace: true })
    } catch {
      setFormError('Your sign-in was submitted, but we could not verify the session. Retry session verification.')
    } finally {
      setRestoring(false)
    }
  }

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setFormError(null)
    if (!email.trim() || !password) { setFormError('Enter your email and password.'); return }
    try {
      await mutation.mutateAsync({ email: email.trim(), password })
      await restore()
    } catch (error) {
      if (error instanceof ApiError && error.code === 'INVALID_CREDENTIALS') setFormError('Email or password is incorrect.')
      else if (error instanceof ApiError && error.code === 'ACCOUNT_DISABLED') setFormError('This account is disabled. Contact support for help.')
      else setFormError(safeFormError(error))
    }
  }

  const busy = mutation.isPending || restoring
  return <section className="screen public-auth-page public-login-page" aria-labelledby="page-title">
    <div className="public-login-layout">
      <div className="public-login-introduction" />

      <div className="public-login-artwork" aria-hidden="true"><img src="/academy/landscape.png" alt=""/><span className="academy-companion public-login-bo"/></div>

      <section className="public-login-panel" aria-labelledby="page-title">
        <div className="public-login-card">
          <h1 id="page-title">Login</h1>
          <p className="public-login-intro">Sign in to continue your learning journey.</p>
          {notice === 'password-reset' && <Alert role="status" tone="success">Password reset successfully. Please sign in with your new password.</Alert>}
          {notice === 'password-changed' && <Alert role="status" tone="success">Password changed successfully. Please sign in again.</Alert>}
          <form className="public-auth-form public-login-form" onSubmit={submit} noValidate>
            <label className={fieldClass}>Email<input autoComplete="email" type="email" name="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
            <label className={fieldClass}>Password<input autoComplete="current-password" type="password" name="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
            <div className="public-login-help-row"><span>We’re glad you’re here.</span><Link to="/forgot-password">Forgot password?</Link></div>
            {formError && <Alert role="alert" tone="error">{formError}</Alert>}
            <Button variant="primary" className="primary-action" type="submit" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</Button>
            {formError?.includes('Retry session verification') && <Button className="secondary-action" disabled={busy} onClick={() => void restore()}>Retry session verification</Button>}
          </form>
          <p className="public-login-register">New to learning Chinese? <Link to="/register">Create an account <span aria-hidden="true">↗</span></Link></p>
        </div>
        <p className="public-login-security"><span aria-hidden="true">◇</span> Your learning space, ready when you are.</p>
      </section>

      <section className="public-login-story" aria-labelledby="login-story-title">
        <div className="public-login-story-copy">
          <p id="login-story-title" className="public-login-chinese-line">在每一次学习中，遇见新的可能</p>
        </div>
        <div className="public-login-greeting" aria-label="Nǐ hǎo, hello">
          <span className="public-login-greeting__characters" lang="zh">你好</span>
          <span className="public-login-greeting__pinyin">nǐ hǎo <span aria-hidden="true">/</span> hello</span>
          <span className="public-login-greeting__seal" aria-hidden="true">学</span>
        </div>
      </section>
    </div>
  </section>
}

export function RegisterPage() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [formError, setFormError] = useState<string | null>(null)
  const [restoring, setRestoring] = useState(false)
  const [registrationComplete, setRegistrationComplete] = useState(false)
  const mutation = useMutation({ mutationFn: authApi.register, retry: false })

  const restore = async () => {
    setRestoring(true)
    setFormError(null)
    try {
      await restoreAuthoritativeSession(queryClient)
      await navigate('/dashboard', { replace: true })
    } catch {
      setFormError('Your account was created, but we could not verify the session. Retry session verification.')
    } finally { setRestoring(false) }
  }

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setFormError(null)
    if (!fullName.trim() || !email.trim() || !password || !confirmation) { setFormError('Complete all fields.'); return }
    if (password !== confirmation) { setFormError('Passwords do not match.'); return }
    if (password.length < 8 || password.length > 128) { setFormError('Password must be between 8 and 128 characters.'); return }
    try {
      await mutation.mutateAsync({ full_name: fullName.trim(), email: email.trim(), password })
      setPassword(''); setConfirmation(''); setRegistrationComplete(true)
      await restore()
    } catch (error) {
      if (registrationComplete) return
      if (error instanceof ApiError && error.code === 'EMAIL_ALREADY_REGISTERED') setFormError('An account already exists for this email.')
      else if (error instanceof ApiError && error.code === 'INVALID_PASSWORD') setFormError('Password does not meet the required policy.')
      else setFormError(safeFormError(error))
    } finally { setRestoring(false) }
  }

  const busy = mutation.isPending || restoring
  return <section className="screen public-auth-page public-register-page" aria-labelledby="page-title">
    <PageHeader title="Create an account" titleId="page-title" description="Create your learner account to begin." />
    <Surface as="section" className="public-auth-surface"><form className="public-auth-form" onSubmit={submit} noValidate>
      <label className={fieldClass}>Full name<input autoComplete="name" name="full_name" value={fullName} onChange={(event) => setFullName(event.target.value)} required /></label>
      <label className={fieldClass}>Email<input autoComplete="email" type="email" name="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
      <label className={fieldClass}>Password<input autoComplete="new-password" type="password" name="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
      <label className={fieldClass}>Confirm password<input autoComplete="new-password" type="password" name="confirm_password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} required /></label>
      {formError && <Alert role="alert" tone="error">{formError}</Alert>}
      {registrationComplete && formError?.includes('Retry session verification')
        ? <Button className="secondary-action" disabled={busy} onClick={() => void restore()}>Retry session verification</Button>
        : <Button variant="primary" className="primary-action" type="submit" disabled={busy || registrationComplete}>{busy ? 'Creating account…' : 'Create account'}</Button>}
    </form></Surface>
    <p className="public-auth-links">Already have an account? <Link to="/login">Sign in</Link></p>
  </section>
}

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [acknowledged, setAcknowledged] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const mutation = useMutation({ mutationFn: authApi.requestPasswordReset, retry: false })
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setFormError(null); setAcknowledged(false)
    if (!email.trim()) { setFormError('Enter your email.'); return }
    try { await mutation.mutateAsync({ email: email.trim() }); setAcknowledged(true) }
    catch (error) { setFormError(safeFormError(error)) }
  }
  return <section className="screen public-auth-page public-forgot-page" aria-labelledby="page-title">
    <PageHeader title="Forgot password" titleId="page-title" description="Request a password-reset link." />
    <Surface as="section" className="public-auth-surface"><form className="public-auth-form" onSubmit={submit} noValidate>
      <label className={fieldClass}>Email<input autoComplete="email" type="email" name="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
      {formError && <Alert role="alert" tone="error">{formError}</Alert>}
      {acknowledged && <Alert role="status" tone="info">If an eligible account exists for that email, password-reset instructions will be sent.</Alert>}
      <Button variant="primary" className="primary-action" type="submit" disabled={mutation.isPending}>{mutation.isPending ? 'Sending…' : formError ? 'Retry' : 'Send reset instructions'}</Button>
    </form></Surface>
    <p className="public-auth-links"><Link to="/login">Back to login</Link></p>
  </section>
}

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')?.trim() ?? ''
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [formError, setFormError] = useState<string | null>(null)
  const [invalidLink, setInvalidLink] = useState(false)
  const mutation = useMutation({ mutationFn: authApi.confirmPasswordReset, retry: false })

  if (!token || invalidLink) return <section className="screen public-auth-page public-reset-page" aria-labelledby="page-title">
    <PageHeader title="Reset password" titleId="page-title" description="Choose a new password for your account." /><Alert role="alert" tone="error">This password reset link is missing or invalid.</Alert><Link className="secondary-action" to="/forgot-password">Request a new reset link</Link>
  </section>

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setFormError(null)
    if (!password || !confirmation) { setFormError('Enter and confirm your new password.'); return }
    if (password !== confirmation) { setFormError('Passwords do not match.'); return }
    if (password.length < 8 || password.length > 128) { setFormError('Password must be between 8 and 128 characters.'); return }
    try {
      await mutation.mutateAsync({ token, new_password: password })
      setPassword(''); setConfirmation('')
      await clearAuthenticatedSessionCache()
      await navigate('/login', { replace: true, state: { notice: 'password-reset' } })
    } catch (error) {
      if (error instanceof ApiError && error.code === 'INVALID_RESET_TOKEN') setInvalidLink(true)
      else if (error instanceof ApiError && error.code === 'INVALID_PASSWORD') setFormError('Password does not meet the required policy.')
      else setFormError(safeFormError(error))
    }
  }

  return <section className="screen public-auth-page public-reset-page" aria-labelledby="page-title">
    <PageHeader title="Reset password" titleId="page-title" description="Choose a new password for your account." />
    <Surface as="section" className="public-auth-surface"><form className="public-auth-form" onSubmit={submit} noValidate>
      <label className={fieldClass}>New password<input autoComplete="new-password" type="password" name="new_password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
      <label className={fieldClass}>Confirm new password<input autoComplete="new-password" type="password" name="confirm_password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} required /></label>
      {formError && <Alert role="alert" tone="error">{formError}</Alert>}
      <Button variant="primary" className="primary-action" type="submit" disabled={mutation.isPending}>{mutation.isPending ? 'Resetting…' : 'Reset password'}</Button>
    </form></Surface>
  </section>
}

export function LogoutAction({ language = 'en' }: { language?: 'en' | 'vi' }) {
  const navigate = useNavigate()
  const [error, setError] = useState(false)
  const mutation = useMutation({
    mutationFn: authApi.logout,
    retry: false,
    onSuccess: async () => {
      await clearAuthenticatedSessionCache()
      setError(false)
      await navigate('/login', { replace: true })
    },
    onError: () => setError(true),
  })
  return <div className="logout-action">
    {error && <Alert role="alert" tone="error">{language === 'vi' ? 'Chưa thể xác nhận đăng xuất. Phiên đăng nhập vẫn đang hoạt động; bạn có thể thử lại.' : 'Logout could not be confirmed. Your session is still shown as active; retry when ready.'}</Alert>}
    <Button className="secondary-action" disabled={mutation.isPending} onClick={() => mutation.mutate()}>{language === 'vi' ? mutation.isPending ? 'Đang đăng xuất…' : error ? 'Thử đăng xuất lại' : 'Đăng xuất' : mutation.isPending ? 'Signing out…' : error ? 'Retry logout' : 'Logout'}</Button>
  </div>
}
