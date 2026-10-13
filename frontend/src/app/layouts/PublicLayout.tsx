import { Link, Outlet } from 'react-router'

export function PublicLayout() {
  return (
    <div className="app-shell public-shell">
      <header className="site-header">
        <Link className="brand" to="/login">Chinese Learning</Link>
      </header>
      <main className="page-container" data-layout="public">
        <Outlet />
      </main>
    </div>
  )
}
