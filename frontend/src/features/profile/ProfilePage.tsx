import { useState, type FormEvent } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { queryKeys } from '../../app/query/keys'
import { clearAuthenticatedSessionCache } from '../../app/query/queryClient'
import { ApiError } from '../../lib/api/errors'
import { authApi } from '../auth/api'
import { useSession } from '../auth/session'
import { getProgressOverview } from '../progress/api'
import {CompanionGuide} from './CompanionGuide'
import '../../styles/student-companions.css'
import { Alert, Button, PageHeader, Surface } from '../../components/ui'

export function ProfilePage() {
  const session = useSession()
  const navigate = useNavigate()
  const progressQuery = useQuery({ queryKey: queryKeys.progressOverview, queryFn: getProgressOverview })
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [formError, setFormError] = useState<string | null>(null)
  const [currentPasswordError, setCurrentPasswordError] = useState<string | null>(null)
  const [newPasswordError, setNewPasswordError] = useState<string | null>(null)
  const mutation = useMutation({
    mutationFn: authApi.changePassword,
    retry: false,
    onSuccess: async () => {
      setCurrentPassword(''); setNewPassword(''); setConfirmation('')
      await clearAuthenticatedSessionCache()
      await navigate('/login', { replace: true, state: { notice: 'password-changed' } })
    },
  })

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setFormError(null); setCurrentPasswordError(null); setNewPasswordError(null)
    if (!currentPassword || !newPassword || !confirmation) { setFormError("Vui lòng điền đầy đủ các trường mật khẩu."); return }
    if (newPassword !== confirmation) { setNewPasswordError("Mật khẩu xác nhận chưa khớp."); return }
    if (newPassword.length < 8 || newPassword.length > 128) { setNewPasswordError("Mật khẩu cần có từ 8 đến 128 ký tự."); return }
    try { await mutation.mutateAsync({ current_password: currentPassword, new_password: newPassword }) }
    catch (error) {
      if (error instanceof ApiError && error.code === 'INVALID_CURRENT_PASSWORD') setCurrentPasswordError("Mật khẩu hiện tại chưa chính xác.")
      else if (error instanceof ApiError && error.code === 'INVALID_PASSWORD') setNewPasswordError("Mật khẩu chưa đáp ứng yêu cầu bảo mật.")
      else if (error instanceof ApiError && (error.code === 'NETWORK_ERROR' || (error.status !== null && error.status >= 500))) setFormError("Chưa thể xác nhận việc đổi mật khẩu. Vui lòng thử lại.")
      else setFormError("Không thể đổi mật khẩu. Vui lòng thử lại.")
    }
  }

  const user = session.user
  return <section className="screen profile-page" aria-labelledby="page-title">
    <PageHeader title="Hồ sơ" titleId="page-title" description="Quản lý thông tin tài khoản và mật khẩu của bạn." />
    <div className="profile-sections">
      <Surface as="section" className="profile-surface" aria-labelledby="identity-title">
        <h2 id="identity-title">Thông tin tài khoản</h2>
        <dl className="profile-details"><dt>Họ và tên</dt><dd>{user?.full_name}</dd><dt>Email</dt><dd>{user?.email}</dd></dl>
      </Surface>
      <Surface as="section" className="profile-surface" aria-labelledby="progress-title">
        <h2 id="progress-title">Tiến độ học tập</h2>
        {progressQuery.isPending && <p role="status">Đang tải tiến độ…</p>}
        {progressQuery.isError && !progressQuery.data && <><Alert role="alert" tone="error">Không thể tải tổng quan tiến độ của bạn.</Alert><Button className="secondary-action" onClick={() => void progressQuery.refetch()}>Thử lại</Button></>}
        {progressQuery.data && <>
          {progressQuery.isFetching && <p className="profile-refresh" role="status">Đang cập nhật tiến độ…</p>}
          {progressQuery.isError && <Alert role="status" tone="warning">Chưa cập nhật được tiến độ. Đang hiển thị tổng quan đã tải.</Alert>}
          <div className="profile-learning-facts"><p>HSK hiện tại: {progressQuery.data.current_hsk === null ? "Chưa bắt đầu" : `HSK ${progressQuery.data.current_hsk}`}</p><p>Tiến độ tổng quan: {progressQuery.data.progress_percentage}%</p></div>
        </>}
      </Surface>
      <Surface as="section" className="profile-surface profile-security" aria-labelledby="password-title">
        <h2 id="password-title">Đổi mật khẩu</h2>
        <form className="profile-password-form" onSubmit={submit} noValidate>
          <label className="profile-field">Mật khẩu hiện tại<input type="password" name="current_password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required /></label>
          {currentPasswordError && <Alert role="alert" tone="error">{currentPasswordError}</Alert>}
          <label className="profile-field">Mật khẩu mới<input type="password" name="new_password" autoComplete="new-password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required /></label>
          {newPasswordError && <Alert role="alert" tone="error">{newPasswordError}</Alert>}
          <label className="profile-field">Xác nhận mật khẩu mới<input type="password" name="confirm_password" autoComplete="new-password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} required /></label>
          {formError && <Alert role="alert" tone="error">{formError}</Alert>}
          <Button variant="primary" type="submit" disabled={mutation.isPending}>{mutation.isPending ? "Đang đổi mật khẩu…" : "Đổi mật khẩu"}</Button>
        </form>
      </Surface>
    </div>
    <CompanionGuide/>
  </section>
}
