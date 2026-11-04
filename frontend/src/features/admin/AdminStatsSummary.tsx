import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { queryKeys } from '../../app/query/keys'
import { Alert, Button, LoadingState } from '../../components/ui'
import { AcademyIcon } from '../../components/academy/AcademyIcon'
import { getAdminStats } from './api'

export function AdminStatsSummary(){
  const stats=useQuery({queryKey:queryKeys.adminStats,queryFn:getAdminStats})
  return <section className="admin-workbench-stats" aria-labelledby="workspace-stats-title">
    <h2 id="workspace-stats-title">Thống kê tóm tắt</h2>
    {stats.isPending&&!stats.data&&<LoadingState>Đang tải thống kê…</LoadingState>}
    {stats.isError&&<Alert role={stats.data?'status':'alert'} tone={stats.data?'warning':'error'} action={<Button variant="secondary" onClick={()=>void stats.refetch()}>Thử tải lại thống kê</Button>}>{stats.data?'Chưa cập nhật được thống kê.':'Không thể tải thống kê.'}</Alert>}
    {stats.data&&<dl><div><dt>Tài khoản</dt><dd>{stats.data.total_users}</dd></div><div><dt>Điểm luyện tập trung bình</dt><dd>{stats.data.average_exercise_score===null?<span>Chưa có kết quả</span>:`${stats.data.average_exercise_score}%`}</dd></div></dl>}
    <Link to="/admin/stats">Xem chi tiết<AcademyIcon name="arrow" size={18}/></Link>
  </section>
}
