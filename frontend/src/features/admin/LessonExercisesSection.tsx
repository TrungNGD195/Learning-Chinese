import { adminLabel } from './labels'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { queryKeys } from '../../app/query/keys'
import { Alert, Button, LoadingState, StatusBadge, Surface } from '../../components/ui'
import { listAdminAssessments } from './api'

export function LessonExercisesSection({lessonId}:{lessonId:string}){
  const [page,setPage]=useState(1)
  const filters={lesson_id:lessonId,assessment_type:'LESSON_EXERCISE',page,page_size:20}
  const query=useQuery({queryKey:queryKeys.adminAssessments(filters),queryFn:()=>listAdminAssessments(filters)})
  return <Surface as="section" className="admin-editor-section" aria-labelledby="lesson-exercises-heading">
    <h2 id="lesson-exercises-heading">Luyện tập của bài học</h2>
    <p>Bài luyện tập có trạng thái xuất bản riêng. Bạn có thể duyệt câu hỏi, đáp án và ngưỡng đạt trước khi xuất bản.</p>
    {query.isPending&&<LoadingState>Đang tải bài luyện tập…</LoadingState>}
    {query.isError&&<Alert tone="error" action={<Button onClick={()=>void query.refetch()}>Thử lại</Button>}>Không thể tải bài luyện tập.</Alert>}
    {query.data?.items.length===0&&<p>Bài học này chưa có bài luyện tập.</p>}
    {query.data&&<><ul className="admin-lesson-exercise-links">{query.data.items.map(item=><li key={item.id}><div><Link to={'/admin/assessments/'+item.id}>{item.title}</Link><p>Điểm đạt: {item.pass_threshold}%</p></div><StatusBadge>{adminLabel(item.status)}</StatusBadge></li>)}</ul>
      {query.data.total>20&&<div className="admin-page-controls"><Button disabled={page===1} onClick={()=>setPage(p=>p-1)}>Trước</Button><span>Trang {page}</span><Button disabled={page*20>=query.data.total} onClick={()=>setPage(p=>p+1)}>Tiếp</Button></div>}</>}
  </Surface>
}
