import { SectionIcon } from '../../components/academy/AcademyArtwork'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { Alert, Button, EmptyState, LoadingState, StatusBadge } from '../../components/ui'
import { Companion } from '../../components/academy/Companion'
import { AcademyIcon } from '../../components/academy/AcademyIcon'
import { queryKeys } from '../../app/query/keys'
import { getDashboard } from './api'
import { continueLearningPath } from './continueLearning'

export function DashboardPage(){
  const query=useQuery({queryKey:queryKeys.dashboard,queryFn:getDashboard})
  const dashboard=query.data
  if(query.isPending&&!dashboard)return <section className="learner-page dashboard-page screen"><h1 id="page-title" className="dashboard-page-title">Dashboard</h1><LoadingState>Loading learning overview…</LoadingState></section>
  if(!dashboard)return <section className="learner-page dashboard-page screen"><h1 id="page-title" className="dashboard-page-title">Dashboard</h1><Alert tone="error" role="alert" action={<Button onClick={()=>void query.refetch()}>Retry</Button>}>Could not load your learning overview.</Alert></section>
  const target=dashboard.continue_learning
  const pronunciation=target?.type==='PRONUNCIATION'
  const destination=target?continueLearningPath(target):null
  return <section className="learner-page dashboard-page academy-dashboard screen" aria-labelledby="page-title">
    <h1 id="page-title" className="dashboard-page-title">Dashboard</h1>
    <div className="academy-greeting"><h2>Một chút tiếng Trung,<br/><span>một thế giới mới.</span></h2><p>{pronunciation?'Bắt đầu từ phát âm. Bo cùng bạn xây một nền tảng thật vững.':'Mừng bạn quay lại. Cùng Bo tiếp tục từ nơi bạn đã dừng.'}</p></div>
    {query.isError&&<Alert tone="warning" role="status">Could not refresh learning overview. Showing the last loaded information.</Alert>}
    <div className="academy-home-grid"><section className="academy-resume-scene" aria-label="Continue Learning"><div className="academy-resume-copy"><h3>{pronunciation?'Bài học phát âm':dashboard.current_lesson?.title??dashboard.current_hsk?.title??'Hành trình của bạn'}</h3><p>{pronunciation?'Thanh mẫu, vận mẫu và thanh điệu. Từng âm nhỏ, một nền tảng lớn.':dashboard.current_lesson?.description??'Học có trình tự. Hiểu thêm một điều sau mỗi lần quay lại.'}</p>{!pronunciation&&dashboard.current_hsk&&<span className="academy-context-label">{dashboard.current_hsk.title??('HSK '+dashboard.current_hsk.level_number)}</span>}{destination?<Link className="learner-link-action" to={destination}>Continue Learning<AcademyIcon name="arrow"/></Link>:<EmptyState title="No next step is available yet">There is no current Continue Learning target.</EmptyState>}<small>Tiến độ học được lưu theo tài khoản của bạn.</small></div><div className="academy-hero-friend"><p>Chào bạn! Mình là Bo.<br/>Mình học tiếp nhé?</p><Companion pose="welcome"/></div></section>
    <aside className="academy-study-context"><h2>{pronunciation?'Nền tảng trước HSK 1':'Vị trí của bạn'}</h2>{pronunciation?<><p>Hoàn thành bài phát âm trước khi mở giáo trình HSK 1.</p><ol><li><span>1</span><div>Thanh mẫu<small>Luyện âm đầu và âm bật hơi</small></div></li><li><span>2</span><div>Vận mẫu<small>Khẩu hình và quy tắc ghép âm</small></div></li><li><span>3</span><div>Thanh điệu<small>Bốn thanh và thanh nhẹ</small></div></li></ol></>:<><p>Tiến độ giáo trình hiện tại</p><strong className="academy-progress-number">{dashboard.progress_percentage}%</strong><progress aria-label="Overall progress" value={dashboard.progress_percentage} max={100}/>{dashboard.current_hsk&&<Link to={'/hsk/'+dashboard.current_hsk.level_number}>{dashboard.current_hsk.title??('HSK '+dashboard.current_hsk.level_number)}</Link>}{dashboard.current_unit&&<p>{dashboard.current_unit.lesson?.title??dashboard.current_unit.assessment?.title}<br/><span>{dashboard.current_unit.unit_type==='LESSON'?'Lesson':'Periodic Test'}{' · '}{dashboard.current_unit.state}</span><br/><StatusBadge>{dashboard.current_unit.state}</StatusBadge></p>}</>}<Link className="academy-text-link" to="/pronunciation">Xem lộ trình học<AcademyIcon name="arrow" size={17}/></Link></aside></div>
    {pronunciation&&<p className="academy-pronunciation-metric">HSK progress: <strong>{dashboard.progress_percentage}%</strong></p>}<section className="academy-next-steps"><div><h2>Mỗi lần quay lại, hiểu thêm một điều.</h2><p>Bo giữ mạch học, Trúc giải thích những điểm dễ nhầm, Bút cùng bạn luyện tập.</p></div><div className="academy-helper-pair"><Companion pose="truc" decorative/><Companion pose="but" decorative/></div><Link className="academy-text-link" to="/companions">Gặp các bạn đồng hành<AcademyIcon name="arrow" size={17}/></Link></section>
    <section className="academy-real-overview"><h2>Giáo trình của bạn</h2><div><SectionIcon kind="path"/><span>Cấp độ hiện tại</span><strong>{dashboard.current_hsk?.title??(dashboard.current_hsk?'HSK '+dashboard.current_hsk.level_number:'Chưa bắt đầu')}</strong></div><div><SectionIcon kind="vocabulary"/><span>Bài đang học</span><strong>{pronunciation?'Phát âm nền tảng':dashboard.current_lesson?.title??'Chưa có bài học khả dụng'}</strong></div><div><SectionIcon kind="practice"/><span>Bước tiếp theo</span><strong>{pronunciation?'Hoàn thành ba phần phát âm':dashboard.current_unit?.unit_type==='PERIODIC_TEST'?'Bài kiểm tra định kỳ':'Tiếp tục theo lộ trình'}</strong></div></section>
  </section>
}
