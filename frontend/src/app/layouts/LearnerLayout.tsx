import { Link, NavLink, Outlet } from 'react-router'
import { LogoutAction } from '../../features/auth/PublicPages'

const learnerLinks = [
  ['Dashboard', '/dashboard'],
  ['Learn', '/pronunciation'],
  ['Progress', '/progress'],
  ['History', '/history'],
  ['Profile', '/profile'],
] as const

export function LearnerLayout() {
  return (
    <div className="app-shell learner-shell">
      <header className="site-header">
        <Link className="brand" to="/dashboard">Chinese Learning</Link>
        <nav aria-label="Learner navigation" className="primary-nav">
          {learnerLinks.map(([label, to]) => (
            <NavLink key={to} to={to} end={to === '/dashboard'}>
              {label}
            </NavLink>
          ))}
        </nav>
        <LogoutAction />
      </header>
      <main className="page-container" data-layout="learner">
        <Outlet />
      </main>
    </div>
  )
}
