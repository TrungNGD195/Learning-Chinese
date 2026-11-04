import { Link, Outlet } from 'react-router'

export function PublicLayout() {
  return (
    <div className="app-shell public-shell">
      <a className="skip-link" href="#main-content">Skip to content</a>
      <header className="site-header">
        <Link className="brand" to="/login">Chinese Learning</Link>
      </header>
      <main className="page-container" id="main-content" data-layout="public" tabIndex={-1}>
        <Outlet />
      </main>
    </div>
  )
}
