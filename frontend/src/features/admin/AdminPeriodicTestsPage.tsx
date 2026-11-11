import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router'
import { queryKeys } from '../../app/query/keys'
import { Alert, Button, EmptyState, LoadingState, PageHeader, StatusBadge, Surface } from '../../components/ui'
import { createAdminAssessment, listAdminAssessments } from './api'
import { AdminLibrary } from './AdminLibrary'
import { AssessmentGenerationForm } from './AssessmentGenerationForm'
import { adminErrorText } from './AdminPrimitives'
import { invalidateAssessmentList } from './invalidation'
import { adminLabel } from './labels'

export function AdminPeriodicTestsPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const client = useQueryClient()
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)
  const [creating, setCreating] = useState(params.get('create') === '1')
  const [generating, setGenerating] = useState(params.get('generate') === '1')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [threshold, setThreshold] = useState('90')
  const filters = { page, page_size: 20, assessment_type: 'PERIODIC_TEST', ...(status ? { status } : {}) }
  const list = useQuery({ queryKey: queryKeys.adminAssessments(filters), queryFn: () => listAdminAssessments(filters) })
  const create = useMutation({
    mutationFn: () => createAdminAssessment({ type: 'PERIODIC_TEST', title: title.trim(), ...(description.trim() ? { description: description.trim() } : {}), pass_threshold: Number(threshold) }), retry: false,
    onSuccess: async (item) => { await invalidateAssessmentList(client); await navigate(`/admin/assessments/${item.id}`) },
  })
  // Bookmarks for lesson practice now open the owning lesson, including creation.
  const legacyLesson = params.get('lesson')
  if (legacyLesson) return <Navigate replace to={`/admin/lessons/${encodeURIComponent(legacyLesson)}?section=exercises${creating ? '&create=1' : ''}${generating ? '&generate=1' : ''}`} />
  return <section className="screen admin-screen admin-assessments-page" aria-labelledby="page-title">
    <PageHeader title="Kiểm tra định kỳ" titleId="page-title" description="Biên soạn và duyệt bài kiểm tra tổng hợp trong lộ trình HSK."
      actions={<div className="admin-action-bar"><Button variant="primary" aria-expanded={creating} onClick={() => setCreating((value) => !value)}>{creating ? 'Đóng tạo bài kiểm tra' : 'Tạo bài kiểm tra'}</Button><Button aria-expanded={generating} onClick={() => setGenerating((value) => !value)}>{generating ? 'Đóng tạo bản nháp bằng AI' : 'Tạo bản nháp bằng AI'}</Button></div>} />
    <p>Luyện tập của từng bài học được biên soạn và duyệt ngay trong <Link to="/admin/lessons">Bài học</Link>.</p>
    {generating && <AssessmentGenerationForm periodicOnly />}
    {creating && <Surface as="section" className="admin-editor-section"><h2>Tạo bài kiểm tra</h2><form className="admin-form-grid" onSubmit={(event) => { event.preventDefault(); if (!create.isPending) create.mutate() }}>
      <label>Tiêu đề<input required value={title} onChange={(event) => setTitle(event.target.value)} /></label>
      <label>Mô tả<textarea value={description} onChange={(event) => setDescription(event.target.value)} /></label>
      <label>Điểm đạt (%)<input required type="number" min="0" max="100" value={threshold} onChange={(event) => setThreshold(event.target.value)} /></label>
      {create.isError && <Alert role="alert" tone="error">{adminErrorText(create.error, 'Không thể tạo bài kiểm tra.')}</Alert>}
      <div className="admin-form-actions"><Button type="submit" variant="primary" disabled={create.isPending || !title.trim() || threshold === '' || Number(threshold) < 0 || Number(threshold) > 100}>{create.isPending ? 'Đang tạo…' : 'Tạo bài kiểm tra'}</Button></div>
    </form></Surface>}
    <Surface className="admin-filter-toolbar" aria-label="Bộ lọc bài kiểm tra"><label>Trạng thái<select value={status} onChange={(event) => { setStatus(event.target.value); setPage(1) }}><option value="">Tất cả trạng thái</option>{['DRAFT', 'REVIEW', 'PUBLISHED', 'ARCHIVED'].map((value) => <option key={value} value={value}>{adminLabel(value)}</option>)}</select></label></Surface>
    {list.isPending && !list.data && <LoadingState>Đang tải bài kiểm tra…</LoadingState>}
    {list.isError && !list.data && <Alert role="alert" tone="error" action={<Button onClick={() => void list.refetch()}>Thử lại</Button>}>{adminErrorText(list.error, 'Không thể tải bài kiểm tra.')}</Alert>}
    {list.data && <>
      {list.isError && <Alert tone="warning">Chưa cập nhật được danh sách. Đang hiển thị kết quả đã tải.</Alert>}
      {list.data.items.length === 0 ? <EmptyState title="Chưa có bài kiểm tra phù hợp">Tạo bài kiểm tra mới hoặc thay đổi bộ lọc.</EmptyState> : <AdminLibrary label="bài kiểm tra" kind="assessments" total={list.data.total} records={list.data.items.map((item) => ({ id: item.id, title: item.title, context: 'Kiểm tra định kỳ', status: <StatusBadge tone={item.status === 'PUBLISHED' ? 'success' : item.status === 'REVIEW' ? 'info' : 'neutral'}>{adminLabel(item.status)}</StatusBadge>, detail: <><p>Điểm đạt: {item.pass_threshold}%</p>{item.description && <p>{item.description}</p>}</>, href: `/admin/assessments/${item.id}`, action: 'Mở biên soạn' }))} />}
      <div className="admin-page-controls"><Button disabled={page <= 1 || list.isFetching} onClick={() => setPage((value) => value - 1)}>Trước</Button><span>Trang {list.data.page}</span><Button disabled={page * list.data.page_size >= list.data.total || list.isFetching} onClick={() => setPage((value) => value + 1)}>Tiếp</Button></div>
    </>}
  </section>
}
