import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { Alert, Button, LoadingState, Surface, TableContainer } from '../../components/ui'
import { queryKeys } from '../../app/query/keys'
import { getAdminStats } from './api'

export function AdminStatsPage() {
  const stats = useQuery({ queryKey: queryKeys.adminStats, queryFn: getAdminStats })
  return <section className="screen admin-screen admin-stats-page admin-stats-detail-page" aria-labelledby="page-title">
    <header className="admin-stats-detail-heading"><Link to="/admin">← Quản trị học liệu</Link><h1 id="page-title">Thống kê</h1><p>Dữ liệu học tập được cập nhật từ hệ thống.</p></header>
    {stats.isPending && !stats.data && <LoadingState>Đang tải thống kê…</LoadingState>}
    {stats.isError && !stats.data && <><Alert role="alert" tone="error">Không thể tải thống kê.</Alert><Button className="secondary-action" onClick={() => void stats.refetch()}>Thử lại</Button></>}
    {stats.data && <>
    {stats.isError && <Alert role="status" tone="warning">Chưa cập nhật được thống kê.</Alert>}
    <div className="admin-stats-grid">
      <Surface as="section" className="admin-stats-card"><h2>Tổng tài khoản</h2><p className="admin-stats-value">{stats.data.total_users}</p></Surface>
      <Surface as="section" className="admin-stats-card admin-stats-card--table"><h2>Học viên theo cấp độ HSK</h2>
        {stats.data.users_by_current_hsk.length === 0
          ? <p>Chưa có dữ liệu cấp độ HSK của học viên.</p>
          : <TableContainer role="region" tabIndex={0} aria-label="Bảng học viên theo cấp độ HSK" className="admin-stats-table-wrap"><table className="admin-stats-table"><thead><tr><th scope="col">Cấp độ HSK</th><th scope="col">Học viên</th></tr></thead><tbody>
            {stats.data.users_by_current_hsk.map((bucket) => <tr key={bucket.hsk_level}><th scope="row">HSK {bucket.hsk_level}</th><td>{bucket.users}</td></tr>)}
          </tbody></table></TableContainer>}
      </Surface>
      <Surface as="section" className="admin-stats-card"><h2>Điểm luyện tập trung bình</h2>
        {stats.data.average_exercise_score === null
          ? <p>Chưa có lượt luyện tập bài học được chấm điểm.</p>
          : <p className="admin-stats-value">{stats.data.average_exercise_score}%</p>}
      </Surface>
    </div>
    {stats.isFetching && <p role="status">Đang cập nhật thống kê…</p>}
    {stats.isError && <Button className="secondary-action" onClick={() => void stats.refetch()}>Thử lại</Button>}
    </>}
  </section>
}
