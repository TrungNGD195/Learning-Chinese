import { adminLabel, adminDate } from './labels'
import { useEffect, useState } from 'react'
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router'
import { queryKeys } from '../../app/query/keys'
import { ApiError } from '../../lib/api/errors'
import { adminErrorText, isNotFound } from './AdminPrimitives'
import {
  archiveAdminAssessment, createAdminAssessment, getAdminAssessment, getAdminLesson,
  listAdminAssessments, listAdminLessons, listAssessmentQuestions, listHskLevels,
  publishAdminAssessment, submitAssessmentReview, updateAdminAssessment,
} from './api'
import { AdminLibrary } from './AdminLibrary'
import { AuthoringSession, AuthoringNotice, useAuthoringDirty, useHasUnsavedDrafts } from './AuthoringSession'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Dialog } from '../../components/ui/Dialog'
import { EmptyState, LoadingState } from '../../components/ui/PageState'
import { PageHeader } from '../../components/ui/PageHeader'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { Surface } from '../../components/ui/Surface'
import {
  invalidateAssessmentLifecycle, invalidateAssessmentList, invalidateAssessmentMetadata,
} from './invalidation'
import { QuestionEditor } from './QuestionEditor'
import { AssessmentGenerationForm } from './AssessmentGenerationForm'

const pageSize = 20

function assessmentStatusTone(status: string) {
  if (status === 'REVIEW') return 'info' as const
  if (status === 'PUBLISHED') return 'success' as const
  return 'neutral' as const
}

export function AdminAssessmentsPage() {
  const [searchParams] = useSearchParams()
  const client = useQueryClient()
  const navigate = useNavigate()
  const [status, setStatus] = useState('')
  const [type, setType] = useState('')
  const [page, setPage] = useState(1)
  const [creating, setCreating] = useState(()=>searchParams.get('create')==='1')
  const [generating, setGenerating] = useState(()=>searchParams.get('generate')==='1')
  const [newType, setNewType] = useState<'LESSON_EXERCISE' | 'PERIODIC_TEST'>('LESSON_EXERCISE')
  const [lessonId, setLessonId] = useState('')
  const [selectorPage, setSelectorPage] = useState(1)
  const [selectorHsk, setSelectorHsk] = useState('')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [threshold, setThreshold] = useState('80')
  const filters = { page, page_size: pageSize, ...(status ? { status } : {}), ...(type ? { assessment_type: type } : {}) }
  const list = useQuery({ queryKey: queryKeys.adminAssessments(filters), queryFn: () => listAdminAssessments(filters) })
  const hsk = useQuery({ queryKey: queryKeys.adminHskLevels, queryFn: listHskLevels })
  const targetLessons = [...new Set((list.data?.items ?? []).flatMap((item) => item.lesson_id ? [item.lesson_id] : []))]
  const lessonTargets = useQueries({ queries: targetLessons.map((id) => ({ queryKey: queryKeys.adminLesson(id), queryFn: () => getAdminLesson(id) })) })
  const lessonTargetById = new Map(targetLessons.map((id, index) => [id, lessonTargets[index]]))
  const lessonFilters = { page: selectorPage, page_size: 50, ...(selectorHsk ? { hsk_level_id: selectorHsk } : {}) }
  const lessons = useQuery({ queryKey: queryKeys.adminLessons(lessonFilters), queryFn: () => listAdminLessons(lessonFilters), enabled: creating && newType === 'LESSON_EXERCISE' })
  const create = useMutation({
    mutationFn: () => {
      const common = { title: title.trim(), ...(description.trim() ? { description: description.trim() } : {}), pass_threshold: Number(threshold) }
      return newType === 'LESSON_EXERCISE'
        ? createAdminAssessment({ type: newType, lesson_id: lessonId, ...common })
        : createAdminAssessment({ type: newType, ...common })
    },
    retry: false,
    onSuccess: async (assessment) => { await invalidateAssessmentList(client); await navigate(`/admin/assessments/${assessment.id}`) },
  })
  const targetChoices = (lessons.data?.items ?? []).filter((lesson) => lesson.status !== 'ARCHIVED')
  return <section className="screen admin-screen admin-assessments-page" aria-labelledby="page-title">
    <PageHeader title="Luyện tập" titleId="page-title" description="Biên soạn câu hỏi, thiết lập điểm đạt và quản lý xuất bản."
      actions={<div className="admin-action-bar"><Button variant="primary" className="admin-primary-action" aria-expanded={creating} onClick={() => setCreating((value) => !value)}>{creating ? "Đóng tạo bài luyện tập" : "Tạo bài luyện tập"}</Button><Button variant="secondary" aria-expanded={generating} onClick={() => setGenerating((value) => !value)}>{generating ? "Đóng tạo bản nháp bằng AI" : "Tạo bản nháp bằng AI"}</Button></div>} />
    {generating && <AssessmentGenerationForm />}
    {creating && <Surface as="section" className="admin-editor-section"><h2>Tạo bài luyện tập</h2><form className="admin-form-grid" onSubmit={(event) => { event.preventDefault(); create.mutate() }}>
      <label>Loại<select value={newType} onChange={(event) => { setNewType(event.target.value as typeof newType); setThreshold(event.target.value === 'LESSON_EXERCISE' ? '80' : '90'); setLessonId('') }}><option value="LESSON_EXERCISE">Luyện tập bài học</option><option value="PERIODIC_TEST">Kiểm tra định kỳ</option></select></label>
      {newType === 'LESSON_EXERCISE' && <>
        <label>Lọc bài học theo HSK<select value={selectorHsk} onChange={(event) => { setSelectorHsk(event.target.value); setSelectorPage(1) }}><option value="">Tất cả cấp độ HSK</option>{(hsk.data ?? []).map((level) => <option value={level.id} key={level.id}>HSK {level.level_number}{level.title ? ` — ${level.title}` : ''}</option>)}</select></label>
        <label>Bài học<select required value={lessonId} onChange={(event) => setLessonId(event.target.value)}><option value="">Chọn bài học</option>{targetChoices.map((lesson) => <option value={lesson.id} key={lesson.id}>HSK {hsk.data?.find((level) => level.id === lesson.hsk_level_id)?.level_number ?? '—'} · Bài {lesson.lesson_number} · {lesson.title}</option>)}</select></label>
        {lessons.isPending && <p role="status">Đang tải danh sách bài học…</p>}
        {lessons.isError && <p role="alert">{adminErrorText(lessons.error, "Không thể tải danh sách bài học.")}</p>}
        {lessons.data && <div className="admin-page-controls"><button type="button" disabled={selectorPage <= 1} onClick={() => setSelectorPage((value) => Math.max(1, value - 1))}>Bài học trước</button><span>Trang {lessons.data.page}</span><button type="button" disabled={selectorPage * lessons.data.page_size >= lessons.data.total} onClick={() => setSelectorPage((value) => value + 1)}>Bài học tiếp</button></div>}
      </>}
      <label>Tiêu đề<input required value={title} onChange={(event) => setTitle(event.target.value)} /></label>
      <label>Mô tả<textarea value={description} onChange={(event) => setDescription(event.target.value)} /></label>
      <label>Điểm đạt (%)<input required type="number" min="0" max="100" value={threshold} onChange={(event) => setThreshold(event.target.value)} /></label>
      {create.isError && <Alert role="alert" tone="error">{adminErrorText(create.error, "Không thể tạo bài luyện tập.")}</Alert>}
      <div className="admin-form-actions"><Button type="submit" variant="primary" className="admin-primary-action" disabled={create.isPending || (newType === 'LESSON_EXERCISE' && !lessonId) || !title.trim() || Number(threshold) < 0 || Number(threshold) > 100}>{create.isPending ? "Đang tạo…" : "Tạo bài luyện tập"}</Button></div>
    </form></Surface>}
    <Surface className="admin-filter-toolbar" aria-label="Bộ lọc bài luyện tập">
      <label>Trạng thái<select value={status} onChange={(event) => { setStatus(event.target.value); setPage(1) }}><option value="">Tất cả trạng thái</option><option value="DRAFT">Bản nháp</option><option value="REVIEW">Chờ duyệt</option><option value="PUBLISHED">Đã xuất bản</option><option value="ARCHIVED">Đã lưu trữ</option></select></label>
      <label>Loại<select value={type} onChange={(event) => { setType(event.target.value); setPage(1) }}><option value="">Tất cả loại</option><option value="LESSON_EXERCISE">Luyện tập bài học</option><option value="PERIODIC_TEST">Kiểm tra định kỳ</option></select></label>
    </Surface>
    {list.isPending && !list.data && <LoadingState>Đang tải bài luyện tập…</LoadingState>}
    {list.isError && !list.data && <Alert role="alert" tone="error" action={<Button onClick={() => void list.refetch()}>Thử lại</Button>}>{adminErrorText(list.error, "Không thể tải bài luyện tập.")}</Alert>}
    {list.data && <>
      {list.isError && <Alert tone="warning">Chưa cập nhật được danh sách bài luyện tập. Đang hiển thị kết quả đã tải.</Alert>}
      {list.data.items.length === 0 ? <EmptyState title="Không có bài luyện tập phù hợp">Không có bài luyện tập phù hợp với bộ lọc.</EmptyState> : <AdminLibrary label="bài luyện tập" kind="assessments" total={list.data.total} records={list.data.items.map((item) => {
        const targetQuery = item.lesson_id ? lessonTargetById.get(item.lesson_id) : undefined
        const target = targetQuery?.data
        return { id: item.id, title: item.title,
          context: item.type === 'LESSON_EXERCISE' ? "Luyện tập bài học" : "Kiểm tra định kỳ",
          status: <StatusBadge tone={assessmentStatusTone(item.status)}>{adminLabel(item.status)}</StatusBadge>,
          detail: <><p>Điểm đạt: {item.pass_threshold}%</p>{item.description && <p>{item.description}</p>}{item.lesson_id && <p>{target ? `Bài ${target.lesson_number} · ${target.title}` : targetQuery?.isError ? "Chưa tải được bài học liên kết." : "Đang tải bài học liên kết…"}</p>}</>,
          href: `/admin/assessments/${item.id}`, action: "Mở biên soạn",
        }
      })} />}
      <div className="admin-page-controls"><Button disabled={page <= 1 || list.isFetching} onClick={() => setPage((value) => Math.max(1, value - 1))}>Trước</Button><span>Trang {list.data.page}</span><Button disabled={page * list.data.page_size >= list.data.total || list.isFetching} onClick={() => setPage((value) => value + 1)}>Tiếp</Button></div>
      {list.isFetching && <LoadingState>Đang cập nhật bài luyện tập…</LoadingState>}
    </>}
  </section>
}

function AssessmentEditor({ assessmentId }: { assessmentId: string }) {
  const client = useQueryClient()
  const assessment = useQuery({ queryKey: queryKeys.adminAssessment(assessmentId), queryFn: () => getAdminAssessment(assessmentId) })
  const questions = useQuery({ queryKey: queryKeys.adminQuestions(assessmentId), queryFn: () => listAssessmentQuestions(assessmentId) })
  const hsk = useQuery({ queryKey: queryKeys.adminHskLevels, queryFn: listHskLevels })
  const lessonId = assessment.data?.lesson_id
  const lesson = useQuery({ queryKey: queryKeys.adminLesson(lessonId ?? ''), queryFn: () => getAdminLesson(lessonId!), enabled: Boolean(lessonId) })
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [threshold, setThreshold] = useState('90')
  const [dirty, setDirty] = useState(false)
  const [archiveOpen, setArchiveOpen] = useState(false)
  const [area, setArea] = useState<'questions' | 'metadata'>('questions')
  const unsaved = useHasUnsavedDrafts()
  useAuthoringDirty('assessment-metadata', Boolean(dirty && assessment.data && (title.trim() !== assessment.data.title || description !== (assessment.data.description ?? '') || Number(threshold) !== assessment.data.pass_threshold)))
  useEffect(() => {
    if (assessment.data && !dirty) { setTitle(assessment.data.title); setDescription(assessment.data.description ?? ''); setThreshold(String(assessment.data.pass_threshold)) }
  }, [assessment.data, dirty])
  const metadata = useMutation({
    mutationFn: () => updateAdminAssessment(assessmentId, { title: title.trim(), description: description || null, pass_threshold: Number(threshold) }),
    retry: false,
    onSuccess: async (result) => {
      await client.cancelQueries({ queryKey: queryKeys.adminAssessment(assessmentId), exact: true })
      client.setQueryData(queryKeys.adminAssessment(assessmentId), result)
      setTitle(result.title)
      setDescription(result.description ?? '')
      setThreshold(String(result.pass_threshold))
      setDirty(false)
      await invalidateAssessmentMetadata(client, result.id)
    },
    onError: async (error) => { if (error instanceof ApiError && error.status === 409) await invalidateAssessmentMetadata(client, assessmentId) },
  })
  const lifecycle = useMutation({
    mutationFn: (action: 'review' | 'publish' | 'archive') => action === 'review' ? submitAssessmentReview(assessmentId) : action === 'publish' ? publishAdminAssessment(assessmentId) : archiveAdminAssessment(assessmentId),
    retry: false,
    onSuccess: async (result, action) => {
      if (action === 'review') await invalidateAssessmentMetadata(client, result.id)
      else await invalidateAssessmentLifecycle(client, result)
    },
    onError: async (error) => { if (error instanceof ApiError && error.status === 409) await invalidateAssessmentMetadata(client, assessmentId) },
  })
  if (assessment.isPending && !assessment.data) return <section className="screen admin-screen admin-assessment-editor-page" aria-labelledby="page-title">
    <div className="admin-assessment-hero"><PageHeader title="Biên soạn bài luyện tập" titleId="page-title" back={<Link to="/admin/assessments">Quay lại luyện tập</Link>} /></div>
    <Surface className="admin-assessment-state-panel"><LoadingState>Đang tải bài luyện tập…</LoadingState></Surface>
  </section>
  if (assessment.isError && !assessment.data) return <section className="screen admin-screen admin-assessment-editor-page" aria-labelledby="page-title">
    <div className="admin-assessment-hero"><PageHeader title="Biên soạn bài luyện tập" titleId="page-title" back={<Link to="/admin/assessments">Quay lại luyện tập</Link>} /></div>
    <Surface className="admin-assessment-state-panel"><Alert role="alert" tone="error" action={<Button onClick={() => void assessment.refetch()}>Thử lại</Button>}>{isNotFound(assessment.error) ? "Không tìm thấy bài luyện tập." : adminErrorText(assessment.error, "Không thể tải bài luyện tập.")}</Alert></Surface>
  </section>
  if (!assessment.data) return null
  const item = assessment.data
  const editable = item.status === 'DRAFT' || item.status === 'REVIEW'
  const changed = title.trim() !== item.title || description !== (item.description ?? '') || Number(threshold) !== item.pass_threshold
  const titleContext = item.lesson_id && lesson.data ? `HSK ${hsk.data?.find((level) => level.id === lesson.data.hsk_level_id)?.level_number ?? '—'} · Bài ${lesson.data.lesson_number} · ${lesson.data.title}` : item.type === 'PERIODIC_TEST' ? "Kiểm tra định kỳ" : "Bài luyện tập"
  return <section className="screen admin-screen admin-assessment-editor-page" aria-labelledby="page-title">
    <div className="admin-assessment-hero">
      <PageHeader title={item.title} titleId="page-title" back={<Link to="/admin/assessments">Quay lại luyện tập</Link>} description={`${item.type === 'LESSON_EXERCISE' ? "Luyện tập bài học" : "Kiểm tra định kỳ"} · ${titleContext}`} />
      {assessment.isError && <Alert tone="warning">Chưa cập nhật được bài luyện tập. Đang hiển thị dữ liệu đã tải.</Alert>}
      {lesson.isError && <Alert tone="warning">Không thể tải thông tin bài học liên kết.</Alert>}
      <Surface as="section" className="admin-editor-card admin-assessment-lifecycle" aria-label="Trạng thái xuất bản bài luyện tập">
        <div className="admin-current-state admin-assessment-current-state"><h2>Xuất bản</h2><p><span>Trạng thái: {adminLabel(item.status)}</span></p><StatusBadge aria-hidden="true" tone={assessmentStatusTone(item.status)}>{adminLabel(item.status)}</StatusBadge>{item.published_at && <span>Ngày xuất bản: {adminDate(item.published_at)}</span>}</div>
        <ol className="admin-lifecycle-track admin-assessment-lifecycle-track" aria-label="Quy trình xuất bản bài luyện tập">{(['DRAFT', 'REVIEW', 'PUBLISHED', 'ARCHIVED'] as const).map((state) => <li key={state} aria-current={item.status === state ? 'step' : undefined}>{adminLabel(state)}</li>)}</ol>
        <div className="admin-action-bar admin-assessment-lifecycle-actions" aria-label="Thao tác xuất bản bài luyện tập">
          {item.status === 'DRAFT' && <Button variant="primary" className="admin-primary-action" disabled={unsaved || lifecycle.isPending || questions.isPending || !questions.data?.length} onClick={() => lifecycle.mutate('review')}>{lifecycle.isPending ? "Đang cập nhật trạng thái…" : "Gửi duyệt"}</Button>}
          {item.status === 'REVIEW' && <Button variant="primary" className="admin-primary-action" disabled={unsaved || lifecycle.isPending} onClick={() => lifecycle.mutate('publish')}>{lifecycle.isPending ? "Đang cập nhật trạng thái…" : "Xuất bản bài luyện tập"}</Button>}
          {item.status === 'PUBLISHED' && <Button variant="danger" disabled={lifecycle.isPending} onClick={() => setArchiveOpen(true)}>{lifecycle.isPending ? "Đang cập nhật trạng thái…" : "Lưu trữ bài luyện tập"}</Button>}
        </div>
        {lifecycle.isError && <Alert role="alert" tone="error">{adminErrorText(lifecycle.error, "Không thể thay đổi trạng thái bài luyện tập.")}</Alert>}
      </Surface>
    </div>
    <AuthoringNotice/>
    <nav className="admin-studio-nav" aria-label="Khu vực biên soạn bài luyện tập"><button type="button" aria-pressed={area === 'questions'} onClick={() => setArea('questions')}>Câu hỏi ({questions.data?.length ?? '—'})</button><button type="button" aria-pressed={area === 'metadata'} onClick={() => setArea('metadata')}>Thông tin bài luyện tập</button></nav>
    <div hidden={area !== 'metadata'}><Surface as="section" className="admin-editor-section admin-editor-card admin-assessment-metadata" aria-labelledby="assessment-metadata-title">
      <div className="admin-page-header admin-assessment-section-heading"><div><h2 id="assessment-metadata-title">Thông tin bài luyện tập</h2><p>{editable ? "Chỉnh sửa tiêu đề, mô tả và ngưỡng điểm đạt." : "Thông tin bài đã xuất bản hoặc lưu trữ chỉ có thể xem."}</p></div>{changed && editable && <StatusBadge tone="warning">Thông tin chưa được lưu</StatusBadge>}</div>
      <form className="admin-form-grid admin-assessment-metadata-form" onSubmit={(event) => { event.preventDefault(); if (editable && changed && !metadata.isPending && !(Number(threshold) < 0 || Number(threshold) > 100)) metadata.mutate() }}>
        <label className="admin-assessment-title-field">Tiêu đề<input value={title} disabled={!editable || metadata.isPending} onChange={(event) => { setTitle(event.target.value); setDirty(true) }} /></label>
        <label className="admin-assessment-description-field">Mô tả<textarea value={description} disabled={!editable || metadata.isPending} onChange={(event) => { setDescription(event.target.value); setDirty(true) }} /></label>
        <label className="admin-assessment-threshold-field">Điểm đạt (%)<input type="number" min="0" max="100" value={threshold} disabled={!editable || metadata.isPending} onChange={(event) => { setThreshold(event.target.value); setDirty(true) }} /></label>
        {metadata.isError && <Alert role="alert" tone="error">{adminErrorText(metadata.error, "Không thể lưu thông tin bài luyện tập.")}</Alert>}
        <div className="admin-form-actions"><Button type="submit" variant="primary" className="admin-primary-action" disabled={!editable || !changed || metadata.isPending || Number(threshold) < 0 || Number(threshold) > 100}>{metadata.isPending ? "Đang lưu…" : "Lưu thông tin"}</Button></div>
      </form>
    </Surface>
    </div>
    <div hidden={area !== 'questions'}>
    {questions.isError && !questions.data && <Alert role="alert" tone="error" action={<Button onClick={() => void questions.refetch()}>Thử tải lại câu hỏi</Button>}>{adminErrorText(questions.error, "Không thể tải câu hỏi.")}</Alert>}
    {questions.isPending && !questions.data && <LoadingState>Đang tải câu hỏi…</LoadingState>}
    {questions.data && <QuestionEditor assessmentId={item.id} questions={questions.data} editable={editable} />}
    </div>
    <Dialog cancelLabel="Hủy" open={archiveOpen} title="Lưu trữ bài luyện tập?" confirmLabel="Lưu trữ bài luyện tập" confirmVariant="danger" busy={lifecycle.isPending}
      onCancel={() => setArchiveOpen(false)} onClose={() => setArchiveOpen(false)}
      onConfirm={() => { lifecycle.mutate('archive'); setArchiveOpen(false) }}>
      Bài luyện tập sẽ được chuyển sang trạng thái lưu trữ.
    </Dialog>
  </section>
}

export function AdminAssessmentEditorPage() {
  const { assessmentId } = useParams()
  if (!assessmentId) return <section className="screen admin-screen admin-assessment-editor-page" aria-labelledby="page-title">
    <div className="admin-assessment-hero"><PageHeader title="Biên soạn bài luyện tập" titleId="page-title" /></div>
    <Surface className="admin-assessment-state-panel"><Alert role="alert" tone="error">Không tìm thấy bài luyện tập.</Alert></Surface>
  </section>
  return <AuthoringSession key={assessmentId}><AssessmentEditor assessmentId={assessmentId} /></AuthoringSession>
}
