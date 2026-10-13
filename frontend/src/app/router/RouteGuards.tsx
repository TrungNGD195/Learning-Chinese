import { Link, Navigate, Outlet, useLocation } from 'react-router'
import { useSession } from '../../features/auth/session'

export function ProtectedRoute() {
  const session = useSession()
  if (session.status === 'UNKNOWN') {
    if (session.isError) {
      return <section className="screen"><h1>Session verification</h1><p role="alert">We could not verify your session.</p>
        <button type="button" className="secondary-action" onClick={() => void session.refetch()}>Retry</button></section>
    }
    return <section className="screen"><p role="status">Checking your session…</p></section>
  }
  if (session.status === 'UNAUTHENTICATED') return <Navigate to="/login" replace />
  return <Outlet />
}

export function AdminRoute() {
  const session = useSession()
  if (session.status !== 'AUTHENTICATED') return <ProtectedRoute />
  if (session.user?.role !== 'ADMIN') {
    return <section className="screen" data-testid="admin-forbidden">
      <h1>Access denied</h1><p>This area requires an Admin account.</p>
      <Link className="secondary-action" to="/dashboard">Back to Dashboard</Link>
    </section>
  }
  return <Outlet />
}

export function PublicAuthRoute() {
  const session = useSession()
  const { pathname } = useLocation()
  if (session.status === 'UNKNOWN') {
    if (session.isError) {
      return <section className="screen"><h1>Session verification</h1><p role="alert">We could not verify your session.</p>
        <button type="button" className="secondary-action" onClick={() => void session.refetch()}>Retry</button></section>
    }
    return <section className="screen"><p role="status">Checking your session…</p></section>
  }
  if (session.status === 'AUTHENTICATED' && pathname !== '/reset-password') return <Navigate to="/dashboard" replace />
  return <Outlet />
}
