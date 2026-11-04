import { SceneIllustration, HeaderArtwork } from '../../components/academy/AcademyArtwork'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { queryKeys } from '../../app/query/keys'
import { Alert, Button, LoadingState, StatusBadge } from '../../components/ui'
import { AcademyIcon } from '../../components/academy/AcademyIcon'
import { Companion } from '../../components/academy/Companion'
import { listAdminAssessments, listAdminDocuments, listAdminLessons, listHskLevels } from './api'
import { AdminStatsSummary } from './AdminStatsSummary'

const draftFilters = { status: 'DRAFT', page: 1, page_size: 3 }
const exerciseFilters = { assessment_type: 'LESSON_EXERCISE', page: 1, page_size: 2 }
const documentFilters = { page: 1, page_size: 1 }
const statuses:Record<string,string> = { DRAFT:'Bản nháp', REVIEW:'Chờ duyệt', PUBLISHED:'Đã xuất bản', ARCHIVED:'Đã lưu trữ' }

function LoadFeedback({pending,error,hasData,label,onRetry}:{pending:boolean;error:boolean;hasData:boolean;label:string;onRetry:()=>void}){
  if(pending)return <LoadingState>Đang tải {label}…</LoadingState>
  if(error)return <Alert role={hasData?'status':'alert'} tone={hasData?'warning':'error'} action={<Button variant="secondary" onClick={onRetry}>Thử lại</Button>}>{hasData?'Chưa cập nhật được':'Không thể tải'} {label}.{hasData?' Đang hiển thị dữ liệu đã tải.':''}</Alert>
  return null
}

export function AdminDashboardPage() {
  const drafts=useQuery({queryKey:queryKeys.adminLessons(draftFilters),queryFn:()=>listAdminLessons(draftFilters)})
  const exercises=useQuery({queryKey:queryKeys.adminAssessments(exerciseFilters),queryFn:()=>listAdminAssessments(exerciseFilters)})
  const levels=useQuery({queryKey:queryKeys.adminHskLevels,queryFn:listHskLevels})
  const documents=useQuery({queryKey:queryKeys.adminDocuments(documentFilters),queryFn:()=>listAdminDocuments(documentFilters)})
  const levelNumber=(id:string)=>levels.data?.find(level=>level.id===id)?.level_number
  return <section className="screen admin-screen admin-dashboard-page admin-workbench" aria-labelledby="page-title">
    <header className="admin-workbench-heading"><div><h1 id="page-title">Quản trị học liệu</h1><p>Tiếp tục soạn bài, hoàn thiện luyện tập và sắp xếp hành trình học.</p></div><HeaderArtwork scene="study"/><Link className="admin-workbench-create" to="/admin/lessons?create=1"><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>Tạo bài học</Link></header>

    <div className="admin-workbench-primary">
      <section className="admin-workbench-panel admin-workbench-lessons" aria-labelledby="workspace-lessons-title">
        <header className="admin-workbench-panel-heading"><div><h2 id="workspace-lessons-title">Bài học</h2><p>Hoàn thiện từ vựng, ngữ pháp và hình minh họa từ bản nháp của bạn.</p></div><Companion pose="guide" decorative/></header>
        <LoadFeedback pending={drafts.isPending} error={drafts.isError} hasData={!!drafts.data} label="bản nháp bài học" onRetry={()=>void drafts.refetch()}/>
        {drafts.data&&<>{drafts.data.items.length===0?<div className="admin-workbench-empty"><h3>Bắt đầu bản nháp mới?</h3><p>Các bài đang soạn sẽ xuất hiện ở đây để bạn mở lại nhanh.</p><Link to="/admin/lessons?create=1">Tạo một bản nháp<AcademyIcon name="arrow" size={18}/></Link></div>:<ul className="admin-workbench-drafts" aria-label="Bản nháp bài học">{drafts.data.items.map(lesson=><li key={lesson.id}><div><h3>{lesson.title}</h3><p>{levelNumber(lesson.hsk_level_id)?`HSK ${levelNumber(lesson.hsk_level_id)} · `:''}Bài {lesson.lesson_number}<span>· Bản nháp</span></p></div><Link to={'/admin/lessons/'+lesson.id} aria-label={'Tiếp tục chỉnh sửa: '+lesson.title}>Tiếp tục chỉnh sửa<AcademyIcon name="arrow" size={18}/></Link></li>)}</ul>}</>}
        <footer className="admin-workbench-panel-footer"><Link to="/admin/lessons">Quản lý tất cả bài học<AcademyIcon name="arrow" size={18}/></Link>{drafts.data&&<span>{drafts.data.total} bản nháp</span>}</footer>
      </section>

      <section className="admin-workbench-panel admin-workbench-exercises" aria-labelledby="workspace-exercises-title">
        <header className="admin-workbench-panel-heading"><SceneIllustration scene="practice"/><div><h2 id="workspace-exercises-title">Luyện tập</h2><p>Duyệt câu hỏi, đáp án và ngưỡng đạt trước khi xuất bản.</p></div></header>
        <LoadFeedback pending={exercises.isPending} error={exercises.isError} hasData={!!exercises.data} label="bài luyện tập" onRetry={()=>void exercises.refetch()}/>
        {exercises.data&&<>{exercises.data.items.length===0?<p className="admin-workbench-empty">Chưa có bài luyện tập. Bắt đầu từ nội dung của một bài học để tạo đề ôn tập.</p>:<ul className="admin-workbench-exercise-list" aria-label="Bài luyện tập">{exercises.data.items.map(exercise=><li key={exercise.id}><Link to={'/admin/assessments/'+exercise.id}>{exercise.title}<AcademyIcon name="arrow" size={17}/></Link><div><StatusBadge tone={exercise.status==='PUBLISHED'?'success':exercise.status==='REVIEW'?'warning':'neutral'}>{statuses[exercise.status]??exercise.status}</StatusBadge><span>Đạt từ {exercise.pass_threshold}%</span></div></li>)}</ul>}</>}
        <footer className="admin-workbench-panel-footer"><Link to="/admin/assessments?generate=1">Tạo đề bằng AI<AcademyIcon name="arrow" size={18}/></Link><Link to="/admin/assessments">Quản lý đề</Link></footer>
      </section>
    </div>

    <div className="admin-workbench-secondary">
      <section className="admin-workbench-panel" aria-labelledby="workspace-curriculum-title"><SceneIllustration scene="path"/><header className="admin-workbench-secondary-heading"><AcademyIcon name="path" size={26}/><h2 id="workspace-curriculum-title">Lộ trình HSK</h2></header><p>Sắp xếp bài học, bài kiểm tra và thứ tự mở khóa trong từng cấp độ.</p>
        <LoadFeedback pending={levels.isPending} error={levels.isError} hasData={!!levels.data} label="cấp độ HSK" onRetry={()=>void levels.refetch()}/>
        {levels.data&&<p className="admin-workbench-context">{levels.data.length?levels.data.map(level=>'HSK '+level.level_number).join(' · '):'Chưa có cấp độ HSK.'}</p>}
        <Link className="admin-workbench-section-link" to="/admin/curriculum">Quản lý lộ trình<AcademyIcon name="arrow" size={18}/></Link>
      </section>
      <section className="admin-workbench-panel" aria-labelledby="workspace-documents-title"><SceneIllustration scene="library"/><header className="admin-workbench-secondary-heading"><AcademyIcon name="book" size={26}/><h2 id="workspace-documents-title">Tài liệu nguồn</h2></header><p>Quản lý giáo trình, kiểm tra nội dung đã xử lý và duyệt nguồn kiến thức.</p>
        <LoadFeedback pending={documents.isPending} error={documents.isError} hasData={!!documents.data} label="tài liệu nguồn" onRetry={()=>void documents.refetch()}/>
        {documents.data&&<p className="admin-workbench-context">{documents.data.total?`${documents.data.total} tài liệu trong kho`:'Chưa có tài liệu được tải lên.'}</p>}
        <Link className="admin-workbench-section-link" to="/admin/documents">Mở kho tài liệu<AcademyIcon name="arrow" size={18}/></Link>
      </section>
    </div>
    <AdminStatsSummary/>
  </section>
}
