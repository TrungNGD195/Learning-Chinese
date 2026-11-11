import { adminLabel } from './labels'
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { queryKeys } from '../../app/query/keys'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { EmptyState, LoadingState } from '../../components/ui/PageState'
import { PageHeader } from '../../components/ui/PageHeader'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { Surface } from '../../components/ui/Surface'
import { AdminLibrary, LessonLibraryPreview } from './AdminLibrary'
import { adminErrorText } from './AdminPrimitives'
import { createAdminLesson, listAdminLessons, listHskLevels } from './api'
import { invalidateLessonList } from './invalidation'
import { AdminCurriculumPage } from './AdminCurriculumPage'

function lessonTone(status: string) {
  return status === 'PUBLISHED' ? 'success' as const : 'neutral' as const
}

export function AdminLessonsPage() {
  const [params] = useSearchParams()
  return params.get('view') === 'curriculum' ? <AdminCurriculumPage /> : <LessonLibraryPage />
}

function LessonLibraryPage() {
  const [searchParams] = useSearchParams()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [status, setStatus] = useState('')
  const [hskId, setHskId] = useState('')
  const [page, setPage] = useState(1)
  const [showCreate, setShowCreate] = useState(()=>searchParams.get('create')==='1')
  const [createHsk, setCreateHsk] = useState('')
  const [lessonNumber, setLessonNumber] = useState('')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const hskQuery = useQuery({ queryKey: queryKeys.adminHskLevels, queryFn: listHskLevels })
  const filters = { page, page_size: 20, ...(status ? { status } : {}), ...(hskId ? { hsk_level_id: hskId } : {}) }
  const list = useQuery({ queryKey: queryKeys.adminLessons(filters), queryFn: () => listAdminLessons(filters) })
  const create = useMutation({
    mutationFn: () => createAdminLesson({
      hsk_level_id: createHsk,
      lesson_number: Number(lessonNumber),
      title: title.trim(),
      ...(description.trim() ? { description: description.trim() } : {}),
    }),
    retry: false,
    onSuccess: async (lesson) => { await invalidateLessonList(queryClient); await navigate(`/admin/lessons/${lesson.id}`) },
  })
  return <section className="screen admin-screen admin-lessons-page" aria-labelledby="page-title">
    <PageHeader title="Bài học" titleId="page-title" description="Biên soạn, cập nhật và xuất bản nội dung bài học."
      actions={<div className="admin-action-bar"><Button variant="primary" className="admin-primary-action" aria-expanded={showCreate} onClick={() => setShowCreate((shown) => !shown)}>{showCreate ? "Đóng tạo bài học" : "Tạo bài học"}</Button><Link className="ui-button ui-button--secondary" to="/admin/lessons?view=curriculum">Sắp xếp HSK</Link></div>} />
    {showCreate && <Surface as="section" className="admin-editor-section">
      <h2>Tạo bài học</h2>
      <form className="admin-form-grid" onSubmit={(event) => { event.preventDefault(); create.mutate() }}>
        <label>HSK<select required value={createHsk} onChange={(event) => setCreateHsk(event.target.value)}>
          <option value="">Chọn HSK</option>{(hskQuery.data ?? []).map((level) => <option value={level.id} key={level.id}>HSK {level.level_number}{level.title ? ` — ${level.title}` : ''}</option>)}
        </select></label>
        <label>Số thứ tự bài học<input type="number" min="1" required value={lessonNumber} onChange={(event) => setLessonNumber(event.target.value)} /></label>
        <label>Tiêu đề<input required value={title} onChange={(event) => setTitle(event.target.value)} /></label>
        <label>Mô tả<textarea value={description} onChange={(event) => setDescription(event.target.value)} /></label>
        {create.isError && <Alert role="alert" tone="error">{adminErrorText(create.error, "Không thể tạo bài học.")}</Alert>}
        <div className="admin-form-actions"><Button type="submit" variant="primary" className="admin-primary-action" disabled={create.isPending || !createHsk || !title.trim() || Number(lessonNumber) < 1}>{create.isPending ? "Đang tạo…" : "Tạo bài học"}</Button></div>
      </form>
    </Surface>}
    <Surface as="section" className="admin-filter-toolbar" aria-label="Bộ lọc bài học">
      <label>Trạng thái<select value={status} onChange={(event) => { setStatus(event.target.value); setPage(1) }}>
        <option value="">Tất cả trạng thái</option><option value="DRAFT">Bản nháp</option><option value="PUBLISHED">Đã xuất bản</option><option value="ARCHIVED">Đã lưu trữ</option>
      </select></label>
      <label>HSK<select value={hskId} onChange={(event) => { setHskId(event.target.value); setPage(1) }}>
        <option value="">Tất cả cấp độ HSK</option>{(hskQuery.data ?? []).map((level) => <option value={level.id} key={level.id}>HSK {level.level_number}{level.title ? ` — ${level.title}` : ''}</option>)}
      </select></label>
    </Surface>
    {list.isPending && !list.data && <LoadingState>Đang tải bài học…</LoadingState>}
    {list.isError && !list.data && <Alert role="alert" tone="error" action={<Button onClick={() => void list.refetch()}>Thử lại</Button>}>{adminErrorText(list.error, "Không thể tải bài học.")}</Alert>}
    {list.data && <>
      {list.isError && <Alert tone="warning">Chưa cập nhật được danh sách bài học. Đang hiển thị kết quả đã tải.</Alert>}
      {list.data.items.length === 0 ? <EmptyState title="Không có bài học phù hợp">Không có bài học phù hợp với bộ lọc.</EmptyState> : <AdminLibrary label="bài học" kind="lessons" total={list.data.total} records={list.data.items.map((lesson) => ({
        id: lesson.id, title: lesson.title,
        context: `HSK ${hskQuery.data?.find((level) => level.id === lesson.hsk_level_id)?.level_number ?? '—'} · Bài ${lesson.lesson_number}`,
        status: <StatusBadge tone={lessonTone(lesson.status)}>{adminLabel(lesson.status)}</StatusBadge>,
        detail: lesson.description, href: `/admin/lessons/${lesson.id}`, action: "Mở biên soạn",
      }))} preview={(id) => <LessonLibraryPreview key={id} lessonId={id}/>} />}
      <div className="admin-page-controls"><Button disabled={page <= 1 || list.isFetching} onClick={() => setPage((value) => Math.max(1, value - 1))}>Trước</Button><span>Trang {list.data.page}</span><Button disabled={page * list.data.page_size >= list.data.total || list.isFetching} onClick={() => setPage((value) => value + 1)}>Tiếp</Button></div>
      {list.isFetching && <LoadingState>Đang cập nhật bài học…</LoadingState>}
    </>}
  </section>
}
