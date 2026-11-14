import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'
import { Alert, Button, EmptyState, LoadingState, PageHeader, StatusBadge, Surface, TableContainer } from '../../components/ui'
import { queryKeys } from '../../app/query/keys'
import { getAdminUser, listAdminUsers } from './api'

const date = (value: string | null) => value ? new Date(value).toLocaleDateString('vi-VN') : '—'
const roleLabel = (role: string) => role === 'ADMIN' ? 'Quản trị viên' : 'Học viên'

export function AdminUsersPage() {
  const [input, setInput] = useState('')
  const [search, setSearch] = useState('')
  const [role, setRole] = useState<'' | 'ADMIN' | 'LEARNER'>('')
  const [page, setPage] = useState(1)
  const filters = { page, page_size: 20, search, ...(role ? { role } : {}) }
  const users = useQuery({ queryKey: queryKeys.adminUsers(filters), queryFn: () => listAdminUsers(filters) })
  return <section className="screen admin-screen admin-users-page" aria-labelledby="page-title">
    <PageHeader titleId="page-title" title="Người dùng" description="Xem tài khoản và tiến độ học. Người đăng ký mới nhất hiển thị trước."/>
    <form className="admin-users-filters" onSubmit={event => { event.preventDefault(); setPage(1); setSearch(input.trim()) }}>
      <label>Tìm người dùng<input type="search" maxLength={100} placeholder="Nhập họ tên hoặc email…" value={input} onChange={event => setInput(event.target.value)}/></label>
      <label>Vai trò<select value={role} onChange={event => { setRole(event.target.value as typeof role); setPage(1) }}><option value="">Tất cả vai trò</option><option value="LEARNER">Học viên</option><option value="ADMIN">Quản trị viên</option></select></label>
      <Button type="submit" variant="primary">Tìm kiếm</Button>
    </form>
    {users.isPending && <LoadingState>Đang tải người dùng…</LoadingState>}
    {users.isError && <Alert role="alert" tone="error" action={<Button onClick={() => void users.refetch()}>Thử lại</Button>}>Không thể tải danh sách người dùng.</Alert>}
    {users.data && <>
      <p className="admin-users-count">{users.data.total} tài khoản{search ? ` khớp với “${search}”` : ''}</p>
      {!users.data.items.length ? <EmptyState title="Không có tài khoản phù hợp">Thử đổi tên, email hoặc vai trò để tìm lại.</EmptyState> : <TableContainer role="region" aria-label="Danh sách người dùng" tabIndex={0}>
        <table className="admin-users-table"><thead><tr><th>Họ tên / Email</th><th>Vai trò</th><th>Trạng thái</th><th>Ngày đăng ký</th><th>Bài hoàn thành</th><th><span className="sr-only">Thao tác</span></th></tr></thead><tbody>
          {users.data.items.map(user => <tr key={user.id}><th scope="row"><strong>{user.full_name}</strong><span className="admin-user-email">{user.email}</span></th><td>{roleLabel(user.role)}</td><td><StatusBadge tone={user.is_active ? 'success' : 'neutral'}>{user.is_active ? 'Đang hoạt động' : 'Đã vô hiệu hóa'}</StatusBadge></td><td>{date(user.created_at)}</td><td>{user.role === 'LEARNER' ? user.completed_lessons : '—'}</td><td><Link className="learner-link-action" to={`/admin/users/${user.id}`} aria-label={`Xem ${user.full_name}`}>Xem chi tiết</Link></td></tr>)}
        </tbody></table>
      </TableContainer>}
      <nav className="admin-users-pagination" aria-label="Phân trang người dùng"><Button disabled={page === 1} onClick={() => setPage(page - 1)}>Trang trước</Button><span>Trang {page} / {Math.max(1, Math.ceil(users.data.total / 20))}</span><Button disabled={page * 20 >= users.data.total} onClick={() => setPage(page + 1)}>Trang sau</Button></nav>
    </>}
  </section>
}

export function AdminUserDetailPage() {
  const { userId = '' } = useParams()
  const detail = useQuery({ queryKey: queryKeys.adminUser(userId), queryFn: () => getAdminUser(userId), enabled: Boolean(userId) })
  const user = detail.data
  return <section className="screen admin-screen admin-users-page" aria-labelledby="page-title">
    <PageHeader titleId="page-title" title={user?.full_name ?? 'Chi tiết người dùng'} back={<Link className="learner-link-action" to="/admin/users">← Danh sách người dùng</Link>}/>
    {detail.isPending && <LoadingState>Đang tải tài khoản…</LoadingState>}
    {detail.isError && <Alert role="alert" tone="error" action={<Button onClick={() => void detail.refetch()}>Thử lại</Button>}>Không thể tải tài khoản. Tài khoản có thể không tồn tại hoặc bạn chưa có quyền xem.</Alert>}
    {user && <>
      <Surface><h2>Thông tin tài khoản</h2><dl className="admin-user-facts"><div><dt>Email</dt><dd>{user.email}</dd></div><div><dt>Vai trò</dt><dd>{roleLabel(user.role)}</dd></div><div><dt>Trạng thái</dt><dd>{user.is_active ? 'Đang hoạt động' : 'Đã vô hiệu hóa'}</dd></div><div><dt>Ngày đăng ký</dt><dd>{date(user.created_at)}</dd></div></dl></Surface>
      {user.role === 'LEARNER' && <>
        <Surface><h2>Tiến độ học tập</h2><dl className="admin-user-facts"><div><dt>Phát âm nền tảng</dt><dd>{user.pronunciation_completed ? 'Đã hoàn thành' : 'Chưa hoàn thành'}</dd></div><div><dt>Bài học hoàn thành</dt><dd>{user.completed_lessons}</dd></div><div><dt>Lượt luyện đã chấm</dt><dd>{user.graded_attempts}</dd></div><div><dt>Điểm trung bình các lượt đã chấm</dt><dd>{user.average_score === null ? 'Chưa có kết quả' : `${user.average_score.toFixed(1)}%`}</dd></div></dl></Surface>
        <Surface><h2>Các bài đã học</h2>{!user.lesson_activity.length ? <p>Chưa có hoạt động bài học.</p> : <ul className="admin-user-lessons">{user.lesson_activity.map(lesson => <li key={lesson.lesson_id}><div><strong>HSK {lesson.hsk_level} · Bài {lesson.lesson_number}: {lesson.title}</strong><p>Bắt đầu: {date(lesson.started_at)}{lesson.completed_at ? ` · Hoàn thành: ${date(lesson.completed_at)}` : ''}</p></div><StatusBadge tone={lesson.completed_at ? 'success' : 'neutral'}>{lesson.completed_at ? 'Đã hoàn thành' : lesson.theory_completed_at ? 'Đã học lý thuyết' : 'Đang học'}</StatusBadge></li>)}</ul>}</Surface>
      </>}
    </>}
  </section>
}
