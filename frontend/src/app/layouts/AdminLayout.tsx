import { Link, NavLink, Outlet } from 'react-router'
import { LogoutAction } from '../../features/auth/PublicPages'

const adminLinks = [
  ['Dashboard', '/admin'],
  ['Curriculum', '/admin/curriculum'],
  ['Lessons', '/admin/lessons'],
  ['Assessments', '/admin/assessments'],
  ['Documents', '/admin/documents'],
  ['Stats', '/admin/stats'],
] as const

export function AdminLayout() {
  return (
    <div className="app-shell admin-shell">
      <header className="site-header">
        <Link className="brand" to="/admin">Admin</Link>
        <nav aria-label="Admin navigation" className="primary-nav">
          {adminLinks.map(([label, to]) => (
            <NavLink key={to} to={to} end={to === '/admin'}>
              {label}
            </NavLink>
          ))}
        </nav>
        <LogoutAction />
      </header>
      <main className="page-container" data-layout="admin">
        <Outlet />
      </main>
    </div>
  )
}
