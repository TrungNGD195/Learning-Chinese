import { learnerLabel } from '../../lib/learnerLabels'
import { SectionIcon } from '../../components/academy/AcademyArtwork'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { Alert, Button, EmptyState, LoadingState, StatusBadge } from '../../components/ui'
import { Companion } from '../../components/academy/Companion'
import { StudyAdvice } from '../../components/academy/StudyAdvice'
import { AcademyIcon } from '../../components/academy/AcademyIcon'
import { queryKeys } from '../../app/query/keys'
import { getDashboard } from './api'
import {LessonEntryLink} from '../journey/LessonEntryLink'
import { continueLearningPath } from './continueLearning'

export function DashboardPage(){
  const query=useQuery({queryKey:queryKeys.dashboard,queryFn:getDashboard})
  const dashboard=query.data
  if(query.isPending&&!dashboard)return <section className="learner-page dashboard-page screen"><h1 id="page-title" className="dashboard-page-title">Góc học tập</h1><LoadingState>Đang tải tổng quan học tập…</LoadingState></section>
  if(!dashboard)return <section className="learner-page dashboard-page screen"><h1 id="page-title" className="dashboard-page-title">Góc học tập</h1><Alert tone="error" role="alert" action={<Button onClick={()=>void query.refetch()}>Thử lại</Button>}>Không thể tải tổng quan học tập của bạn.</Alert></section>
  const target=dashboard.continue_learning
  const pronunciation=target?.type==='PRONUNCIATION'
  const destination=target?continueLearningPath(target):null
  return <section className="learner-page dashboard-page academy-dashboard screen" aria-labelledby="page-title">
    <h1 id="page-title" className="dashboard-page-title">Góc học tập</h1>
    {query.isError&&<Alert tone="warning" role="status">Chưa cập nhật được tổng quan học tập. Đang hiển thị thông tin đã tải.</Alert>}
    <div className="academy-home-grid"><section className="academy-resume-scene" aria-label="Tiếp tục học"><div className="academy-resume-copy"><h2>{pronunciation?'Bài học phát âm':dashboard.current_lesson?.title??dashboard.current_hsk?.title??'Hành trình của bạn'}</h2>{(pronunciation||!dashboard.current_lesson)&&<p>{pronunciation?'Thanh mẫu, vận mẫu, thanh điệu và biến điệu. Từng âm nhỏ, một nền tảng lớn.':'Học có trình tự. Hiểu thêm một điều sau mỗi lần quay lại.'}</p>}{!pronunciation&&dashboard.current_hsk&&<span className="academy-context-label">{dashboard.current_hsk.title??('HSK '+dashboard.current_hsk.level_number)}</span>}{destination?<LessonEntryLink className="learner-link-action" to={destination}>Tiếp tục học<AcademyIcon name="arrow"/></LessonEntryLink>:<EmptyState title="Chưa có bước học tiếp theo">Hiện chưa có bước học tiếp theo.</EmptyState>}<small>Tiến độ học được lưu theo tài khoản của bạn.</small></div><div className="academy-hero-friend"><p>Chào bạn! Mình là Bo.<br/>Mình học tiếp nhé?</p><Companion pose="welcome"/></div></section>
    <aside className="academy-study-context"><h2>{pronunciation?'Nền tảng trước HSK 1':'Vị trí của bạn'}</h2>{pronunciation?<><p>Hoàn thành bài phát âm trước khi mở giáo trình HSK 1.</p><ol><li><span>1</span><div>Thanh mẫu<small>Luyện âm đầu và âm bật hơi</small></div></li><li><span>2</span><div>Vận mẫu<small>Khẩu hình và quy tắc ghép âm</small></div></li><li><span>3</span><div>Thanh điệu<small>Bốn thanh và thanh nhẹ</small></div></li><li><span>4</span><div>Biến điệu<small>Cách đọc các thanh khi nói liền</small></div></li></ol></>:<><p>Tiến độ giáo trình hiện tại</p><strong className="academy-progress-number">{dashboard.progress_percentage}%</strong><progress aria-label="Tiến độ tổng quan" value={dashboard.progress_percentage} max={100}/>{dashboard.current_hsk&&<Link to={'/hsk/'+dashboard.current_hsk.level_number}>{dashboard.current_hsk.title??('HSK '+dashboard.current_hsk.level_number)}</Link>}{dashboard.current_unit&&<p>{dashboard.current_unit.lesson?.title??dashboard.current_unit.assessment?.title}<br/><span>{dashboard.current_unit.unit_type==='LESSON'?"Bài học":"Kiểm tra định kỳ"}{' · '}{learnerLabel(dashboard.current_unit.state)}</span><br/><StatusBadge>{learnerLabel(dashboard.current_unit.state)}</StatusBadge></p>}</>}<Link className="academy-text-link" to="/pronunciation">Xem lộ trình học<AcademyIcon name="arrow" size={17}/></Link></aside></div>
    {pronunciation&&<p className="academy-pronunciation-metric">Tiến độ HSK: <strong>{dashboard.progress_percentage}%</strong></p>}<StudyAdvice topic={pronunciation ? 'pronunciation' : 'recall'}/>
    <section className="academy-real-overview" aria-labelledby="curriculum-overview-title"><h2 id="curriculum-overview-title">Giáo trình của bạn</h2>
      <div className="academy-overview-item"><SectionIcon kind="path"/><div className="academy-overview-copy"><span>Cấp độ hiện tại</span><strong>{dashboard.current_hsk?.title??(dashboard.current_hsk?'HSK '+dashboard.current_hsk.level_number:'Chưa bắt đầu')}</strong></div></div>
      <div className="academy-overview-item"><SectionIcon kind="vocabulary"/><div className="academy-overview-copy"><span>Bài đang học</span><strong>{pronunciation?'Phát âm nền tảng':dashboard.current_lesson?.title??'Chưa có bài học khả dụng'}</strong></div></div>
      <div className="academy-overview-item"><SectionIcon kind="practice"/><div className="academy-overview-copy"><span>Bước tiếp theo</span><strong>{pronunciation?'Hoàn thành bốn phần phát âm':dashboard.current_unit?.unit_type==='PERIODIC_TEST'?'Bài kiểm tra định kỳ':'Tiếp tục theo lộ trình'}</strong></div></div>
    </section>
  </section>
}
