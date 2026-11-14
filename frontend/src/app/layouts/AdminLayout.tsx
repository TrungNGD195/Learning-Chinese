import { ArtworkProvider } from '../../components/academy/AcademyArtwork'
import { useEffect, useRef } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router'
import { LogoutAction } from '../../features/auth/PublicPages'

const adminLinks = [
  ["Tổng quan", '/admin', <><rect x="3" y="3" width="7" height="9" rx="1" /><rect x="14" y="3" width="7" height="5" rx="1" /><rect x="14" y="12" width="7" height="9" rx="1" /><rect x="3" y="16" width="7" height="5" rx="1" /></>],
  ["Bài học", '/admin/lessons', <><path d="M4 3h11a2 2 0 0 1 2 2v4M4 3v18h9M2 7h4M2 12h4M2 17h4" /><path d="m14 18 5-5a1.4 1.4 0 0 1 2 2l-5 5-3 .8z" /></>],
  ["Kiểm tra định kỳ", '/admin/assessments', <><rect x="4" y="4" width="16" height="17" rx="2" /><path d="M9 4.5h6v-2H9zM8 12l2.5 2.5L16 9" /></>],
  ["Tài liệu", '/admin/documents', <><path d="M8 3h8l4 4v12a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z" /><path d="M16 3v5h4M3 7v12a2 2 0 0 0 2 2M10 12h6M10 16h6" /></>],
  ['Người dùng', '/admin/users', <><circle cx="9" cy="8" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3M16 5a3 3 0 0 1 0 6M18 15a5 5 0 0 1 3 5"/></>],
  ['Hồ sơ', '/admin/profile', <><circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/></>],
] as const

export function AdminLayout() {
  const navigation = useRef<HTMLElement>(null)
  const { pathname } = useLocation()
  useEffect(() => {
    const nav = navigation.current
    const active = nav?.querySelector<HTMLElement>('[aria-current="page"]')
    if (!nav || !active || nav.scrollWidth <= nav.clientWidth) return
    const bounds = nav.getBoundingClientRect(), item = active.getBoundingClientRect()
    if (item.right > bounds.right) nav.scrollLeft += item.right - bounds.right + 8
    else if (item.left < bounds.left) nav.scrollLeft += item.left - bounds.left - 8
  }, [pathname])
  return (
    <div className="app-shell admin-shell admin-academy-workspace">
      <a className="skip-link" href="#main-content">Chuyển đến nội dung</a>
      <aside className="admin-sidebar" aria-label="Khu vực quản trị">
        <Link className="brand" to="/admin">Quản trị</Link>
        <p className="admin-nav-hint">Cuộn để xem các mục <span aria-hidden="true">→</span></p>
        <nav ref={navigation} aria-label="Điều hướng quản trị" className="primary-nav">
          {adminLinks.map(([label, to, icon]) => (
            <NavLink key={to} to={to} end={to === '/admin'} className={to === '/admin/profile' ? 'admin-profile-nav' : undefined}>
              <svg className="admin-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">{icon}</svg>
              {label}
            </NavLink>
          ))}
        </nav>
        <LogoutAction />
      </aside>
      <div className="admin-main">
        <main className="page-container" id="main-content" data-layout="admin" tabIndex={-1}>
          <ArtworkProvider admin><Outlet /></ArtworkProvider>
        </main>
      </div>
    </div>
  )
}
