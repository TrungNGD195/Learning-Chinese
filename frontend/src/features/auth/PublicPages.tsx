import { useEffect, useState, type FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router'
import { clearAuthenticatedSessionCache, prepareAuthenticatedSessionCache } from '../../app/query/queryClient'
import { ApiError } from '../../lib/api/errors'
import { authApi } from './api'
import { authMeQueryOptions } from './session'

const fieldClass = 'form-field'

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
      await restoreAuthoritativeSession(queryClient)
      await navigate('/dashboard', { replace: true })
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
  return <section className="screen auth-screen" aria-labelledby="page-title">
    <h1 id="page-title">Login</h1>
    {notice === 'password-reset' && <p role="status">Password reset successfully. Please sign in with your new password.</p>}
    {notice === 'password-changed' && <p role="status">Password changed successfully. Please sign in again.</p>}
    <form className="form-card" onSubmit={submit} noValidate>
      <label className={fieldClass}>Email<input autoComplete="email" type="email" name="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
      <label className={fieldClass}>Password<input autoComplete="current-password" type="password" name="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
      {formError && <p role="alert">{formError}</p>}
      <button className="primary-action" type="submit" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
      {formError?.includes('Retry session verification') && <button className="secondary-action" type="button" disabled={busy} onClick={() => void restore()}>Retry session verification</button>}
    </form>
    <p><Link to="/register">Create an account</Link> · <Link to="/forgot-password">Forgot password?</Link></p>
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
  return <section className="screen auth-screen" aria-labelledby="page-title">
    <h1 id="page-title">Create an account</h1>
    <form className="form-card" onSubmit={submit} noValidate>
      <label className={fieldClass}>Full name<input autoComplete="name" name="full_name" value={fullName} onChange={(event) => setFullName(event.target.value)} required /></label>
      <label className={fieldClass}>Email<input autoComplete="email" type="email" name="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
      <label className={fieldClass}>Password<input autoComplete="new-password" type="password" name="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
      <label className={fieldClass}>Confirm password<input autoComplete="new-password" type="password" name="confirm_password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} required /></label>
      {formError && <p role="alert">{formError}</p>}
      {registrationComplete && formError?.includes('Retry session verification')
        ? <button className="secondary-action" type="button" disabled={busy} onClick={() => void restore()}>Retry session verification</button>
        : <button className="primary-action" type="submit" disabled={busy || registrationComplete}>{busy ? 'Creating account…' : 'Create account'}</button>}
    </form>
    <p>Already have an account? <Link to="/login">Sign in</Link></p>
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
  return <section className="screen auth-screen" aria-labelledby="page-title">
    <h1 id="page-title">Forgot password</h1>
    <p>Request a password-reset link.</p>
    <form className="form-card" onSubmit={submit} noValidate>
      <label className={fieldClass}>Email<input autoComplete="email" type="email" name="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
      {formError && <p role="alert">{formError}</p>}
      {acknowledged && <p role="status">If an eligible account exists for that email, password-reset instructions will be sent.</p>}
      <button className="primary-action" type="submit" disabled={mutation.isPending}>{mutation.isPending ? 'Sending…' : formError ? 'Retry' : 'Send reset instructions'}</button>
    </form>
    <p><Link to="/login">Back to login</Link></p>
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

  if (!token || invalidLink) return <section className="screen auth-screen" aria-labelledby="page-title">
    <h1 id="page-title">Reset password</h1><p role="alert">This password reset link is missing or invalid.</p><Link className="secondary-action" to="/forgot-password">Request a new reset link</Link>
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

  return <section className="screen auth-screen" aria-labelledby="page-title">
    <h1 id="page-title">Reset password</h1>
    <form className="form-card" onSubmit={submit} noValidate>
      <label className={fieldClass}>New password<input autoComplete="new-password" type="password" name="new_password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
      <label className={fieldClass}>Confirm new password<input autoComplete="new-password" type="password" name="confirm_password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} required /></label>
      {formError && <p role="alert">{formError}</p>}
      <button className="primary-action" type="submit" disabled={mutation.isPending}>{mutation.isPending ? 'Resetting…' : 'Reset password'}</button>
    </form>
  </section>
}

export function LogoutAction() {
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
    {error && <p role="alert">Logout could not be confirmed. Your session is still shown as active; retry when ready.</p>}
    <button type="button" className="secondary-action" disabled={mutation.isPending} onClick={() => mutation.mutate()}>{mutation.isPending ? 'Signing out…' : error ? 'Retry logout' : 'Logout'}</button>
  </div>
}
