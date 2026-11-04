import { Link, Navigate, Outlet, useLocation } from 'react-router'
import { useSession } from '../../features/auth/session'
import { Alert, Button, LoadingState, PageHeader } from '../../components/ui'

function RoleForbidden({
  role,
  testId,
}: {
  role: 'LEARNER' | 'ADMIN'
  testId: string
}) {
  const isLearner = role === 'LEARNER'
  return <section className="screen public-forbidden-page" data-testid={testId}>
    <PageHeader
      title={isLearner ? 'Không có quyền truy cập' : 'Access denied'}
      description={isLearner ? 'Khu vực này dành cho tài khoản quản trị.' : 'This area requires a Learner account.'}
    />
    <Link className="secondary-action" to={isLearner ? '/dashboard' : '/admin'}>
      {isLearner ? 'Quay lại góc học tập' : 'Go to Admin Dashboard'}
    </Link>
  </section>
}

export function ProtectedRoute() {
  const session = useSession()
  if (session.status === 'UNKNOWN') {
    if (session.isError) {
      return <section className="screen public-session-page"><PageHeader title="Session verification" /><Alert role="alert" tone="error">We could not verify your session.</Alert>
        <Button className="secondary-action" onClick={() => void session.refetch()}>Retry</Button></section>
    }
    return <section className="screen public-session-page"><PageHeader title="Session verification" /><LoadingState>Checking your session…</LoadingState></section>
  }
  if (session.status === 'UNAUTHENTICATED') return <Navigate to="/login" replace />
  if (session.user?.role !== 'LEARNER') return <RoleForbidden role="ADMIN" testId="learner-forbidden" />
  return <Outlet />
}

export function AdminRoute() {
  const session = useSession()
  if (session.status === 'UNKNOWN') return <section className="screen public-session-page"><PageHeader title="Xác thực phiên đăng nhập"/>{session.isError
    ? <><Alert role="alert" tone="error">Không thể xác thực phiên đăng nhập của bạn.</Alert><Button onClick={() => void session.refetch()}>Thử lại</Button></>
    : <LoadingState>Đang kiểm tra phiên đăng nhập…</LoadingState>}</section>
  if (session.status !== 'AUTHENTICATED') return <ProtectedRoute />
  if (session.user?.role !== 'ADMIN') {
    return <RoleForbidden role="LEARNER" testId="admin-forbidden" />
  }
  return <Outlet />
}

export function PublicAuthRoute() {
  const session = useSession()
  const { pathname } = useLocation()
  if (session.status === 'UNKNOWN') {
    if (session.isError) {
      return <section className="screen public-session-page"><PageHeader title="Session verification" /><Alert role="alert" tone="error">We could not verify your session.</Alert>
        <Button className="secondary-action" onClick={() => void session.refetch()}>Retry</Button></section>
    }
    return <section className="screen public-session-page"><PageHeader title="Session verification" /><LoadingState>Checking your session…</LoadingState></section>
  }
  if (session.status === 'AUTHENTICATED' && pathname !== '/reset-password') {
    return <Navigate to={session.user?.role === 'ADMIN' ? '/admin' : '/dashboard'} replace />
  }
  return <Outlet />
}
