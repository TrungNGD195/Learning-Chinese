import { useState, type FormEvent } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { queryKeys } from '../../app/query/keys'
import { clearAuthenticatedSessionCache } from '../../app/query/queryClient'
import { ApiError } from '../../lib/api/errors'
import { authApi } from '../auth/api'
import { useSession } from '../auth/session'
import { getProgressOverview } from '../progress/api'

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
  return <section className="screen" aria-labelledby="page-title">
    <h1 id="page-title">Profile</h1>
    <div className="section-grid">
      <section className="learning-card" aria-labelledby="identity-title">
        <h2 id="identity-title">Account</h2>
        <dl className="profile-details"><dt>Full name</dt><dd>{user?.full_name}</dd><dt>Email</dt><dd>{user?.email}</dd></dl>
      </section>
      <section className="learning-card" aria-labelledby="progress-title">
        <h2 id="progress-title">Learning progress</h2>
        {progressQuery.isPending && <p role="status">Loading progress…</p>}
        {progressQuery.isError && !progressQuery.data && <><p role="alert">Could not load your progress summary.</p><button type="button" className="secondary-action" onClick={() => void progressQuery.refetch()}>Retry</button></>}
        {progressQuery.data && <>
          {progressQuery.isFetching && <p role="status">Refreshing progress…</p>}
          {progressQuery.isError && <p role="status">Could not refresh progress. Showing the last loaded summary.</p>}
          <p>Current HSK: {progressQuery.data.current_hsk === null ? 'Not started yet' : `HSK ${progressQuery.data.current_hsk}`}</p>
          <p>Overall progress: {progressQuery.data.progress_percentage}%</p>
        </>}
      </section>
      <section className="learning-card" aria-labelledby="password-title">
        <h2 id="password-title">Change password</h2>
        <form className="form-card" onSubmit={submit} noValidate>
          <label className="form-field">Current password<input type="password" name="current_password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required /></label>
          {currentPasswordError && <p className="field-error" role="alert">{currentPasswordError}</p>}
          <label className="form-field">New password<input type="password" name="new_password" autoComplete="new-password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required /></label>
          {newPasswordError && <p className="field-error" role="alert">{newPasswordError}</p>}
          <label className="form-field">Confirm new password<input type="password" name="confirm_password" autoComplete="new-password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} required /></label>
          {formError && <p role="alert">{formError}</p>}
          <button className="primary-action" type="submit" disabled={mutation.isPending}>{mutation.isPending ? 'Changing password…' : 'Change password'}</button>
        </form>
      </section>
    </div>
  </section>
}
