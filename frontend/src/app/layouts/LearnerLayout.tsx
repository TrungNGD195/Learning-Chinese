import { ArtworkProvider } from '../../components/academy/AcademyArtwork'
import { Link, NavLink, Outlet } from 'react-router'
import { LogoutAction } from '../../features/auth/PublicPages'
import { useSession } from '../../features/auth/session'
import { AcademyIcon } from '../../components/academy/AcademyIcon'
import { Companion } from '../../components/academy/Companion'
import { ReadingSettings } from '../../components/academy/ReadingSettings'

const learnerLinks = [
  ['Góc học tập', '/dashboard', 'home'],
  ['Hành trình', '/pronunciation', 'path'],
  ['Lịch sử', '/history', 'history'],
  ['Hồ sơ', '/profile', 'profile'],
] as const

export function LearnerLayout() {
  const {user}=useSession()
  return (
    <div className="app-shell learner-shell bo-shell">
      <a className="skip-link" href="#main-content">Skip to content</a>
      <aside className="academy-sidebar"><Link className="academy-brand" to="/dashboard" aria-label="Chinese Learning — về góc học tập"><span lang="zh-Hans">中</span><span>Chinese Learning<small>CÙNG BO HỌC TIẾNG TRUNG</small></span></Link><p className="academy-motto">Chậm một chút.<br/>Hiểu thêm một điều.</p><nav aria-label="Learner navigation" className="academy-nav">{learnerLinks.map(([label,to,icon])=><NavLink key={to} to={to} end={to==='/dashboard'} aria-label={label} title={label}><AcademyIcon name={icon}/><span>{label}</span></NavLink>)}</nav><Link className="academy-meet-bo" to="/companions"><Companion pose="rest" decorative/><span>Bo và những người bạn<AcademyIcon name="arrow" size={15}/></span></Link><div className="academy-user"><span className="academy-user-avatar">{user?.full_name?.charAt(0)??'B'}</span><div>Chào, {user?.full_name??'Học viên'}<small>Học theo nhịp của bạn</small></div></div></aside>
      <div className="academy-workspace"><header className="academy-topbar"><span><AcademyIcon name="leaf" size={18}/>Không gian nhỏ, hành trình lớn.</span><div><ReadingSettings/><LogoutAction/></div></header><main className="page-container" id="main-content" data-layout="learner" tabIndex={-1}><ArtworkProvider><Outlet/></ArtworkProvider></main><footer className="academy-footer"><span>Học một chút. Hiểu thêm một điều.</span><span>Bo luôn sẵn sàng học cùng bạn.</span></footer></div>
      <nav className="academy-mobile-nav" aria-label="Điều hướng trên điện thoại">{learnerLinks.map(([label,to,icon])=><NavLink key={to} to={to} end={to==='/dashboard'} aria-label={label}><AcademyIcon name={icon}/><span>{label}</span></NavLink>)}</nav>
    </div>
  )
}
