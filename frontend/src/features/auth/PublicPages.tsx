import { useEffect, useState, type FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router'
import { clearAuthenticatedSessionCache, prepareAuthenticatedSessionCache } from '../../app/query/queryClient'
import { ApiError } from '../../lib/api/errors'
import { authApi } from './api'
import { queryKeys } from '../../app/query/keys'
import { Alert, Button, PageHeader, Surface } from '../../components/ui'
import { AcademyIcon } from '../../components/academy/AcademyIcon'

const fieldClass = 'auth-field'
const loginSessionRestoreError = 'Đã gửi thông tin đăng nhập nhưng chưa thể xác thực phiên. Hãy thử xác thực lại.'
const registerSessionRestoreError = 'Tài khoản đã được tạo nhưng chưa thể xác thực phiên đăng nhập. Hãy thử xác thực lại.'

function isTechnicalError(error: unknown) {
  return error instanceof ApiError && (error.code === 'NETWORK_ERROR' || (error.status !== null && error.status >= 500))
}

function safeFormError(error: unknown) {
  return isTechnicalError(error) ? "Có sự cố tạm thời. Vui lòng thử lại." : "Không thể hoàn tất yêu cầu. Vui lòng thử lại."
}

async function restoreAuthoritativeSession(queryClient: ReturnType<typeof useQueryClient>) {
  await prepareAuthenticatedSessionCache()
  // Keep the public form mounted while verifying the new cookie session. An
  // unobserved request failure must not replace it with the route guard.
  const user = await authApi.getMe()
  if (!user) throw new ApiError({ status: null, code: 'INVALID_RESPONSE', message: "Không thể xác thực phiên đăng nhập", details: null })
  queryClient.setQueryData(queryKeys.authMe, user)
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
      await navigate(user.role === 'ADMIN' ? '/admin' : '/pronunciation', { replace: true })
    } catch {
      setFormError(loginSessionRestoreError)
    } finally {
      setRestoring(false)
    }
  }

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setFormError(null)
    if (!email.trim() || !password) { setFormError("Vui lòng nhập email và mật khẩu."); return }
    try {
      await mutation.mutateAsync({ email: email.trim(), password })
      await restore()
    } catch (error) {
      if (error instanceof ApiError && error.code === 'INVALID_CREDENTIALS') setFormError("Email hoặc mật khẩu chưa chính xác.")
      else if (error instanceof ApiError && error.code === 'ACCOUNT_DISABLED') setFormError("Tài khoản đã bị vô hiệu hóa. Vui lòng liên hệ hỗ trợ.")
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
          <h1 id="page-title">Đăng nhập</h1>
          <p className="public-login-intro">Đăng nhập để tiếp tục hành trình học của bạn.</p>
          {notice === 'password-reset' && <Alert role="status" tone="success">Đã đặt lại mật khẩu thành công. Vui lòng đăng nhập bằng mật khẩu mới.</Alert>}
          {notice === 'password-changed' && <Alert role="status" tone="success">Đã đổi mật khẩu thành công. Vui lòng đăng nhập lại.</Alert>}
          <form className="public-auth-form public-login-form" onSubmit={submit} noValidate>
            <label className={fieldClass}>Email<input autoComplete="email" type="email" name="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
            <div className={`${fieldClass} public-login-password`}>
              <div className="public-login-password-heading"><label htmlFor="login-password">Mật khẩu</label><div className="public-login-help-row"><Link to="/forgot-password">Quên mật khẩu?</Link></div></div>
              <input id="login-password" autoComplete="current-password" type="password" name="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
            </div>
            {formError && <Alert role="alert" tone="error">{formError}</Alert>}
            <Button variant="primary" className="primary-action" type="submit" disabled={busy}>{busy ? "Đang đăng nhập…" : "Đăng nhập"}</Button>
            {formError === loginSessionRestoreError && <Button className="secondary-action" disabled={busy} onClick={() => void restore()}>Thử xác thực phiên đăng nhập lại</Button>}
          </form>
          <p className="public-login-register">Bạn mới bắt đầu học tiếng Trung? <Link to="/register">Tạo tài khoản <span aria-hidden="true">↗</span></Link></p>
        </div>
        <p className="public-login-security"><span aria-hidden="true">◇</span> Không gian học tập của bạn, luôn sẵn sàng khi bạn cần.</p>
      </section>

      <section className="public-login-story" aria-labelledby="login-story-title">
        <div className="public-login-story-copy">
          <p id="login-story-title" className="public-login-chinese-line">在每一次学习中，遇见新的可能</p>
        </div>
        <div className="public-login-greeting" aria-label="Nǐ hǎo, xin chào">
          <span className="public-login-greeting__characters" lang="zh">你好</span>
          <span className="public-login-greeting__pinyin">nǐ hǎo <span aria-hidden="true">/</span> xin chào</span>
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
      await navigate('/pronunciation', { replace: true })
    } catch {
      setFormError(registerSessionRestoreError)
    } finally { setRestoring(false) }
  }

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setFormError(null)
    if (!fullName.trim() || !email.trim() || !password || !confirmation) { setFormError("Vui lòng điền đầy đủ thông tin."); return }
    if (password !== confirmation) { setFormError("Mật khẩu xác nhận chưa khớp."); return }
    if (password.length < 8 || password.length > 128) { setFormError("Mật khẩu cần có từ 8 đến 128 ký tự."); return }
    try {
      await mutation.mutateAsync({ full_name: fullName.trim(), email: email.trim(), password })
      setPassword(''); setConfirmation(''); setRegistrationComplete(true)
      await restore()
    } catch (error) {
      if (registrationComplete) return
      if (error instanceof ApiError && error.code === 'EMAIL_ALREADY_REGISTERED') setFormError('Email này đã được đăng ký tài khoản.')
      else if (error instanceof ApiError && error.code === 'INVALID_PASSWORD') setFormError("Mật khẩu chưa đáp ứng yêu cầu bảo mật.")
      else setFormError(safeFormError(error))
    } finally { setRestoring(false) }
  }

  const busy = mutation.isPending || restoring
  return <section className="screen public-auth-page public-register-page" aria-labelledby="page-title">
    <PageHeader title="Tạo tài khoản" titleId="page-title" description="Tạo tài khoản học viên để bắt đầu học." />
    <Surface as="section" className="public-auth-surface"><form className="public-auth-form" onSubmit={submit} noValidate>
      <label className={fieldClass}>Họ và tên<input autoComplete="name" name="full_name" value={fullName} onChange={(event) => setFullName(event.target.value)} required /></label>
      <label className={fieldClass}>Email<input autoComplete="email" type="email" name="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
      <label className={fieldClass}>Mật khẩu<input autoComplete="new-password" type="password" name="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
      <label className={fieldClass}>Xác nhận mật khẩu<input autoComplete="new-password" type="password" name="confirm_password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} required /></label>
      {formError && <Alert role="alert" tone="error">{formError}</Alert>}
      {registrationComplete && formError === registerSessionRestoreError
        ? <Button className="secondary-action" disabled={busy} onClick={() => void restore()}>Thử xác thực phiên đăng nhập lại</Button>
        : <Button variant="primary" className="primary-action" type="submit" disabled={busy || registrationComplete}>{busy ? "Đang tạo tài khoản…" : "Tạo tài khoản"}</Button>}
    </form></Surface>
    <p className="public-auth-links">Bạn đã có tài khoản? <Link to="/login">Đăng nhập</Link></p>
  </section>
}

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [acknowledged, setAcknowledged] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const mutation = useMutation({ mutationFn: authApi.requestPasswordReset, retry: false })
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setFormError(null); setAcknowledged(false)
    if (!email.trim()) { setFormError("Vui lòng nhập email."); return }
    try { await mutation.mutateAsync({ email: email.trim() }); setAcknowledged(true) }
    catch (error) { setFormError(safeFormError(error)) }
  }
  return <section className="screen public-auth-page public-forgot-page" aria-labelledby="page-title">
    <PageHeader title="Quên mật khẩu" titleId="page-title" description="Nhận liên kết để đặt lại mật khẩu." />
    <Surface as="section" className="public-auth-surface"><form className="public-auth-form" onSubmit={submit} noValidate>
      <label className={fieldClass}>Email<input autoComplete="email" type="email" name="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
      {formError && <Alert role="alert" tone="error">{formError}</Alert>}
      {acknowledged && <Alert role="status" tone="info">Nếu email này thuộc tài khoản hợp lệ, hướng dẫn đặt lại mật khẩu sẽ được gửi đến bạn.</Alert>}
      <Button variant="primary" className="primary-action" type="submit" disabled={mutation.isPending}>{mutation.isPending ? "Đang gửi…" : formError ? "Thử lại" : "Gửi liên kết đặt lại mật khẩu"}</Button>
    </form></Surface>
    <p className="public-auth-links"><Link to="/login">Quay lại đăng nhập</Link></p>
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
    <PageHeader title="Đặt lại mật khẩu" titleId="page-title" description="Tạo mật khẩu mới cho tài khoản của bạn." /><Alert role="alert" tone="error">Liên kết đặt lại mật khẩu bị thiếu hoặc không hợp lệ.</Alert><Link className="secondary-action" to="/forgot-password">Yêu cầu liên kết đặt lại mật khẩu mới</Link>
  </section>

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setFormError(null)
    if (!password || !confirmation) { setFormError("Vui lòng nhập và xác nhận mật khẩu mới."); return }
    if (password !== confirmation) { setFormError("Mật khẩu xác nhận chưa khớp."); return }
    if (password.length < 8 || password.length > 128) { setFormError("Mật khẩu cần có từ 8 đến 128 ký tự."); return }
    try {
      await mutation.mutateAsync({ token, new_password: password })
      setPassword(''); setConfirmation('')
      await clearAuthenticatedSessionCache()
      await navigate('/login', { replace: true, state: { notice: 'password-reset' } })
    } catch (error) {
      if (error instanceof ApiError && error.code === 'INVALID_RESET_TOKEN') setInvalidLink(true)
      else if (error instanceof ApiError && error.code === 'INVALID_PASSWORD') setFormError("Mật khẩu chưa đáp ứng yêu cầu bảo mật.")
      else setFormError(safeFormError(error))
    }
  }

  return <section className="screen public-auth-page public-reset-page" aria-labelledby="page-title">
    <PageHeader title="Đặt lại mật khẩu" titleId="page-title" description="Tạo mật khẩu mới cho tài khoản của bạn." />
    <Surface as="section" className="public-auth-surface"><form className="public-auth-form" onSubmit={submit} noValidate>
      <label className={fieldClass}>Mật khẩu mới<input autoComplete="new-password" type="password" name="new_password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
      <label className={fieldClass}>Xác nhận mật khẩu mới<input autoComplete="new-password" type="password" name="confirm_password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} required /></label>
      {formError && <Alert role="alert" tone="error">{formError}</Alert>}
      <Button variant="primary" className="primary-action" type="submit" disabled={mutation.isPending}>{mutation.isPending ? "Đang đặt lại mật khẩu…" : "Đặt lại mật khẩu"}</Button>
    </form></Surface>
  </section>
}

export function LogoutAction({ iconOnly = false }: { iconOnly?: boolean }) {
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
  const label = mutation.isPending ? 'Đang đăng xuất…' : error ? 'Thử đăng xuất lại' : 'Đăng xuất'
  return <div className="logout-action">
    {error && <Alert role="alert" tone="error">Chưa thể xác nhận đăng xuất. Phiên đăng nhập vẫn đang hoạt động; bạn có thể thử lại.</Alert>}
    <Button className="secondary-action" aria-label={label} title={iconOnly ? label : undefined} disabled={mutation.isPending} onClick={() => mutation.mutate()}>{iconOnly ? <AcademyIcon name="logout"/> : label}</Button>
  </div>
}
