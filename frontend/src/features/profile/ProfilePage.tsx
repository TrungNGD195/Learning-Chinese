import { useState, type FormEvent } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { queryKeys } from '../../app/query/keys'
import { clearAuthenticatedSessionCache } from '../../app/query/queryClient'
import { ApiError } from '../../lib/api/errors'
import { authApi } from '../auth/api'
import { useSession } from '../auth/session'
import { getProgressOverview } from '../progress/api'
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
    if (!currentPassword || !newPassword || !confirmation) { setFormError('Complete all password fields.'); return }
    if (newPassword !== confirmation) { setNewPasswordError('Passwords do not match.'); return }
    if (newPassword.length < 8 || newPassword.length > 128) { setNewPasswordError('Password must be between 8 and 128 characters.'); return }
    try { await mutation.mutateAsync({ current_password: currentPassword, new_password: newPassword }) }
    catch (error) {
      if (error instanceof ApiError && error.code === 'INVALID_CURRENT_PASSWORD') setCurrentPasswordError('Current password is incorrect.')
      else if (error instanceof ApiError && error.code === 'INVALID_PASSWORD') setNewPasswordError('Password does not meet the required policy.')
      else if (error instanceof ApiError && (error.code === 'NETWORK_ERROR' || (error.status !== null && error.status >= 500))) setFormError("We couldn't confirm the password change. Please try again.")
      else setFormError('Could not change the password. Please try again.')
    }
  }

  const user = session.user
  return <section className="screen profile-page" aria-labelledby="page-title">
    <PageHeader title="Profile" titleId="page-title" eyebrow="学习档案 · LEARNER PROFILE" description="Manage your account details and password." />
    <div className="profile-sections">
      <Surface as="section" className="profile-surface" aria-labelledby="identity-title">
        <p className="profile-eyebrow">Account</p><h2 id="identity-title">Account details</h2>
        <dl className="profile-details"><dt>Full name</dt><dd>{user?.full_name}</dd><dt>Email</dt><dd>{user?.email}</dd></dl>
      </Surface>
      <Surface as="section" className="profile-surface" aria-labelledby="progress-title">
        <p className="profile-eyebrow">Learning context</p><h2 id="progress-title">Learning progress</h2>
        {progressQuery.isPending && <p role="status">Loading progress…</p>}
        {progressQuery.isError && !progressQuery.data && <><Alert role="alert" tone="error">Could not load your progress summary.</Alert><Button className="secondary-action" onClick={() => void progressQuery.refetch()}>Retry</Button></>}
        {progressQuery.data && <>
          {progressQuery.isFetching && <p className="profile-refresh" role="status">Refreshing progress…</p>}
          {progressQuery.isError && <Alert role="status" tone="warning">Could not refresh progress. Showing the last loaded summary.</Alert>}
          <div className="profile-learning-facts"><p>Current HSK: {progressQuery.data.current_hsk === null ? 'Not started yet' : `HSK ${progressQuery.data.current_hsk}`}</p><p>Overall progress: {progressQuery.data.progress_percentage}%</p></div>
        </>}
      </Surface>
      <Surface as="section" className="profile-surface profile-security" aria-labelledby="password-title">
        <p className="profile-eyebrow">Security</p><h2 id="password-title">Change password</h2>
        <form className="profile-password-form" onSubmit={submit} noValidate>
          <label className="profile-field">Current password<input type="password" name="current_password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required /></label>
          {currentPasswordError && <Alert role="alert" tone="error">{currentPasswordError}</Alert>}
          <label className="profile-field">New password<input type="password" name="new_password" autoComplete="new-password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required /></label>
          {newPasswordError && <Alert role="alert" tone="error">{newPasswordError}</Alert>}
          <label className="profile-field">Confirm new password<input type="password" name="confirm_password" autoComplete="new-password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} required /></label>
          {formError && <Alert role="alert" tone="error">{formError}</Alert>}
          <Button variant="primary" type="submit" disabled={mutation.isPending}>{mutation.isPending ? 'Changing password…' : 'Change password'}</Button>
        </form>
      </Surface>
    </div>
  </section>
}
