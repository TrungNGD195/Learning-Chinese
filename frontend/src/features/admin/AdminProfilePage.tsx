import { useState, type FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { queryKeys } from '../../app/query/keys'
import { clearAuthenticatedSessionCache } from '../../app/query/queryClient'
import { authApi } from '../auth/api'
import { useSession } from '../auth/session'
import { ApiError } from '../../lib/api/errors'
import { Alert, Button, PageHeader } from '../../components/ui'
import { Dialog } from '../../components/ui/Dialog'

function PasswordField({ id, label, value, onChange, error, disabled }: { id: string; label: string; value: string; onChange: (value: string) => void; error?: string; disabled: boolean }) {
  const [visible, setVisible] = useState(false)
  return <div className="admin-profile-field">
    <label htmlFor={id}>{label}</label>
    <div className="admin-profile-password-input"><input id={id} type={visible ? 'text' : 'password'} autoComplete={id === 'admin-current-password' ? 'current-password' : 'new-password'} value={value} onChange={event => onChange(event.target.value)} disabled={disabled} required aria-invalid={Boolean(error)} aria-describedby={error ? id + '-error' : id === 'admin-new-password' ? 'admin-password-policy' : undefined}/><button type="button" onClick={() => setVisible(!visible)} aria-label={`${visible ? 'Ẩn' : 'Hiện'} ${label.toLocaleLowerCase('vi')}`} title={`${visible ? 'Ẩn' : 'Hiện'} mật khẩu`} aria-pressed={visible}><svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>{visible && <path d="m3 3 18 18"/>}</svg></button></div>
    {error && <p className="admin-profile-field-error" id={id + '-error'} role="alert">{error}</p>}
  </div>
}

export function AdminProfilePage() {
  const { user } = useSession()
  const client = useQueryClient()
  const navigate = useNavigate()
  const [nameDraft, setNameDraft] = useState<string | null>(null)
  const name = nameDraft ?? user?.full_name ?? ''
  const [nameError, setNameError] = useState('')
  const [saved, setSaved] = useState(false)
  const [current, setCurrent] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [confirmLogout, setConfirmLogout] = useState(false)
  const leave = async (notice?: string) => {
    setCurrent(''); setPassword(''); setConfirmation('')
    await clearAuthenticatedSessionCache()
    await navigate('/login', { replace: true, state: notice ? { notice } : undefined })
  }
  const profile = useMutation({ mutationFn: authApi.updateProfile, retry: false,
    onSuccess: result => { client.setQueryData(queryKeys.authMe, result); setNameDraft(null); setSaved(true) } })
  const change = useMutation({ mutationFn: authApi.changePassword, retry: false, onSuccess: () => leave('password-changed') })
  const logout = useMutation({ mutationFn: authApi.logoutAll, retry: false, onSuccess: () => leave() })
  const busy = change.isPending || logout.isPending
  const saveName = async (event: FormEvent) => {
    event.preventDefault(); setNameError(''); setSaved(false)
    if (!name.trim() || name.trim().length > 120) { setNameError('Họ tên cần có từ 1 đến 120 ký tự.'); return }
    try { await profile.mutateAsync({ full_name: name.trim() }) }
    catch { setNameError('Chưa thể lưu họ tên. Vui lòng thử lại.') }
  }
  const savePassword = async (event: FormEvent) => {
    event.preventDefault()
    const next: Record<string, string> = {}
    if (!current) next.current = 'Nhập mật khẩu hiện tại.'
    if (password.length < 8 || password.length > 128) next.password = 'Mật khẩu cần có từ 8 đến 128 ký tự.'
    else if (password === current) next.password = 'Mật khẩu mới phải khác mật khẩu hiện tại.'
    if (!confirmation || confirmation !== password) next.confirmation = 'Mật khẩu xác nhận chưa khớp.'
    setErrors(next)
    if (Object.keys(next).length) return
    try { await change.mutateAsync({ current_password: current, new_password: password }) }
    catch (error) {
      const code = error instanceof ApiError ? error.code : ''
      setErrors(code === 'INVALID_CURRENT_PASSWORD' ? { current: 'Mật khẩu hiện tại chưa chính xác.' } : code === 'PASSWORD_UNCHANGED' ? { password: 'Mật khẩu mới phải khác mật khẩu hiện tại.' } : code === 'INVALID_PASSWORD' ? { password: 'Mật khẩu chưa đáp ứng yêu cầu bảo mật.' } : { form: 'Chưa thể xác nhận việc đổi mật khẩu. Vui lòng thử lại.' })
    }
  }
  return <section className="screen admin-screen admin-profile-page" aria-labelledby="page-title">
    <PageHeader title="Hồ sơ" titleId="page-title" description="Thông tin tài khoản và bảo mật của bạn." artwork={false}/>
    <div className="admin-profile-columns">
      <section className="admin-profile-panel" aria-labelledby="admin-identity-title">
        <div className="admin-profile-identity"><span className="admin-profile-avatar" aria-hidden="true">{(user?.full_name?.trim() || 'Q').charAt(0).toLocaleUpperCase('vi')}</span><div><h2 id="admin-identity-title">Thông tin tài khoản</h2><span className="admin-profile-role">Quản trị viên</span></div></div>
        <form onSubmit={saveName} noValidate>
          <div className="admin-profile-field"><label htmlFor="admin-profile-name">Họ và tên</label><input id="admin-profile-name" autoComplete="name" value={name} maxLength={120} disabled={profile.isPending || busy} onChange={event => { setNameDraft(event.target.value); setSaved(false); setNameError('') }} aria-invalid={Boolean(nameError)} aria-describedby={nameError ? 'admin-profile-name-error' : undefined}/>{nameError && <p id="admin-profile-name-error" className="admin-profile-field-error" role="alert">{nameError}</p>}</div>
          <div className="admin-profile-field"><label htmlFor="admin-profile-email">Email</label><input id="admin-profile-email" value={user?.email ?? ''} readOnly autoComplete="email"/><p className="admin-profile-help">Email đăng nhập không thể thay đổi tại đây.</p></div>
          <Button type="submit" disabled={profile.isPending || busy || !name.trim() || name.trim() === user?.full_name}>{profile.isPending ? 'Đang lưu…' : 'Lưu thông tin'}</Button>
          {saved && <p className="admin-profile-success" role="status">Đã cập nhật thông tin tài khoản.</p>}
        </form>
      </section>
      <section className="admin-profile-panel" aria-labelledby="admin-password-title">
        <h2 id="admin-password-title">Đổi mật khẩu</h2><p id="admin-password-policy" className="admin-profile-help">Dùng từ 8 đến 128 ký tự và khác mật khẩu hiện tại.</p>
        <form onSubmit={savePassword} noValidate>
          <PasswordField id="admin-current-password" label="Mật khẩu hiện tại" value={current} onChange={setCurrent} error={errors.current} disabled={busy}/>
          <PasswordField id="admin-new-password" label="Mật khẩu mới" value={password} onChange={setPassword} error={errors.password} disabled={busy}/>
          <PasswordField id="admin-confirm-password" label="Xác nhận mật khẩu mới" value={confirmation} onChange={setConfirmation} error={errors.confirmation} disabled={busy}/>
          <p className="admin-profile-help">Sau khi đổi mật khẩu, bạn cần đăng nhập lại trên tất cả thiết bị.</p>
          {errors.form && <Alert tone="error" role="alert">{errors.form}</Alert>}
          <Button type="submit" variant="primary" disabled={busy || profile.isPending}>{change.isPending ? 'Đang đổi mật khẩu…' : 'Đổi mật khẩu'}</Button>
        </form>
      </section>
    </div>
    <section className="admin-profile-sessions" aria-labelledby="admin-sessions-title"><div><h2 id="admin-sessions-title">Phiên đăng nhập</h2><p>Đăng xuất tài khoản trên tất cả thiết bị, bao gồm thiết bị này.</p>{logout.isError && <Alert tone="error" role="alert">Chưa thể đăng xuất tất cả thiết bị. Vui lòng thử lại.</Alert>}</div><Button onClick={() => setConfirmLogout(true)} disabled={busy || profile.isPending}>Đăng xuất tất cả thiết bị</Button></section>
    <Dialog open={confirmLogout} title="Đăng xuất tất cả thiết bị?" confirmLabel="Đăng xuất tất cả" cancelLabel="Hủy" busy={logout.isPending} onClose={() => setConfirmLogout(false)} onCancel={() => setConfirmLogout(false)} onConfirm={async () => { try { await logout.mutateAsync() } catch { setConfirmLogout(false) } }}><p>Bạn sẽ cần đăng nhập lại, kể cả trên thiết bị đang sử dụng.</p></Dialog>
  </section>
}
