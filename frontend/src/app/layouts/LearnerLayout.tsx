import { ArtworkProvider } from '../../components/academy/AcademyArtwork'
import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router'
import { LogoutAction } from '../../features/auth/PublicPages'
import { useSession } from '../../features/auth/session'
import { AcademyIcon } from '../../components/academy/AcademyIcon'
import { JourneyCloudProvider } from '../../features/journey/JourneyCloudTransition'

const learnerLinks = [
  ['Giáo trình', '/pronunciation', 'book'],
  ['Hồ sơ', '/profile', 'profile'],
] as const

const sidebarMedia = '(max-width: 800px)'
function subscribeSidebar(listener: () => void) {
  const query = window.matchMedia?.(sidebarMedia)
  query?.addEventListener('change', listener)
  return () => query?.removeEventListener('change', listener)
}

function compactSidebar() { return window.matchMedia?.(sidebarMedia).matches ?? false }

export function LearnerLayout() {
  const {user}=useSession()
  const { pathname } = useLocation()
  const compact = useSyncExternalStore(subscribeSidebar, compactSidebar, () => false)
  const [drawerPath, setDrawerPath] = useState<string | null>(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const collapsed = !compact && sidebarCollapsed
  const drawerOpen = compact && drawerPath === pathname
  const sidebar = useRef<HTMLElement>(null)
  const closeButton = useRef<HTMLButtonElement>(null)
  const closeSidebar = () => setDrawerPath(null)

  useEffect(() => {
    const query = window.matchMedia?.(sidebarMedia)
    const close = () => setDrawerPath(null)
    query?.addEventListener('change', close)
    return () => query?.removeEventListener('change', close)
  }, [])

  useEffect(() => {
    if (!drawerOpen) return
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    closeButton.current?.focus()
    const containFocus = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { event.preventDefault(); setDrawerPath(null); return }
      if (event.key !== 'Tab') return
      const links = Array.from(sidebar.current?.querySelectorAll<HTMLElement>('a[href], button:not(:disabled)') ?? [])
        .filter(element => element.getClientRects().length > 0)
      const first = links[0], last = links.at(-1)
      if (!first || !last) return
      const active = document.activeElement
      if (event.shiftKey && (active === first || !sidebar.current?.contains(active))) { event.preventDefault(); last.focus() }
      else if (!event.shiftKey && (active === last || !sidebar.current?.contains(active))) { event.preventDefault(); first.focus() }
    }
    document.addEventListener('keydown', containFocus)
    return () => {
      document.body.style.overflow = previousOverflow
      document.removeEventListener('keydown', containFocus)
      if (previous?.isConnected) previous.focus()
    }
  }, [drawerOpen])

  return (
    <JourneyCloudProvider><div className="app-shell learner-shell bo-shell" data-sidebar-collapsed={collapsed}>
      <a className="skip-link" href="#main-content">Chuyển đến nội dung</a>
      {drawerOpen && <button type="button" className="academy-sidebar-backdrop" tabIndex={-1} aria-label="Đóng menu điều hướng" onClick={closeSidebar}/>}
      <aside ref={sidebar} id="learner-sidebar" className="academy-sidebar" data-open={drawerOpen} role={compact ? 'dialog' : undefined} aria-modal={drawerOpen || undefined} aria-label="Khu vực học viên" inert={compact && !drawerOpen}>
        <button type="button" ref={closeButton} className="academy-sidebar-close" onClick={closeSidebar} aria-label="Đóng menu"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18"/></svg></button>
        <div className="academy-sidebar-header"><Link className="academy-brand" to="/pronunciation" onClick={closeSidebar} aria-label="Hanfolio — về giáo trình"><span lang="zh-Hans">中</span><span>Hanfolio<small>CÙNG BO HỌC TIẾNG TRUNG</small></span></Link>
          <button type="button" className="academy-sidebar-collapse" aria-label={collapsed ? 'Mở rộng thanh bên' : 'Thu gọn thanh bên'} title={collapsed ? 'Mở rộng thanh bên' : 'Thu gọn thanh bên'} aria-expanded={!collapsed} aria-controls="learner-sidebar" onClick={() => setSidebarCollapsed(value => !value)}><AcademyIcon name={collapsed ? 'sidebar-open' : 'sidebar-close'} size={20}/></button></div>
        <p className="academy-motto">Chậm một chút.<br/>Hiểu thêm một điều.</p>
        <nav aria-label="Điều hướng học viên" className="academy-nav">{learnerLinks.map(([label,to,icon])=><NavLink key={to} to={to} end={to==='/pronunciation'} className={({isActive})=>isActive||(to==='/pronunciation'&&(/^\/hsk\//.test(pathname)||pathname==='/measure-words'))?'active':undefined} aria-label={label} title={label} onClick={closeSidebar}><AcademyIcon name={icon}/><span>{label}</span></NavLink>)}</nav>

        <div className="academy-sidebar-account"><div className="academy-user" title={user?.full_name??'Học viên'}><span className="academy-user-avatar">{user?.full_name?.charAt(0)??'B'}</span><div>Chào, {user?.full_name??'Học viên'}<small>Học theo nhịp của bạn</small></div></div><LogoutAction iconOnly={collapsed}/></div>
      </aside>
      <div className="academy-workspace" inert={drawerOpen}><header className="academy-mobile-toolbar"><button type="button" className="academy-sidebar-toggle" aria-label="Mở menu học viên" aria-controls="learner-sidebar" aria-expanded={drawerOpen} onClick={() => setDrawerPath(pathname)}><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16"/></svg><span>Danh mục</span></button></header><main className="page-container" id="main-content" data-layout="learner" tabIndex={-1}><ArtworkProvider><Outlet/></ArtworkProvider></main><footer className="academy-footer"><span>Học một chút. Hiểu thêm một điều.</span><span>Bo luôn sẵn sàng học cùng bạn.</span></footer></div>
      <nav className="academy-mobile-nav" aria-label="Điều hướng trên điện thoại" inert={drawerOpen}>{learnerLinks.map(([label,to,icon])=><NavLink key={to} to={to} end={to==='/pronunciation'} className={({isActive})=>isActive||(to==='/pronunciation'&&(/^\/hsk\//.test(pathname)||pathname==='/measure-words'))?'active':undefined} aria-label={label}><AcademyIcon name={icon}/><span>{label}</span></NavLink>)}</nav>
    </div></JourneyCloudProvider>
  )
}
