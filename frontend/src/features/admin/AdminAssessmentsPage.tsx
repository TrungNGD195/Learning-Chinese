import { adminLabel, adminDate } from './labels'
import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, Navigate, useParams } from 'react-router'
import { queryKeys } from '../../app/query/keys'
import { ApiError } from '../../lib/api/errors'
import { adminErrorText, isNotFound } from './AdminPrimitives'
import {
  archiveAdminAssessment, getAdminAssessment, getAdminLesson,
  listAssessmentQuestions, listHskLevels,
  publishAdminAssessment, submitAssessmentReview, updateAdminAssessment,
} from './api'
import { AuthoringSession, AuthoringNotice, useAuthoringDirty, useHasUnsavedDrafts } from './AuthoringSession'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Dialog } from '../../components/ui/Dialog'
import { LoadingState } from '../../components/ui/PageState'
import { PageHeader } from '../../components/ui/PageHeader'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { Surface } from '../../components/ui/Surface'
import {
  invalidateAssessmentLifecycle, invalidateAssessmentMetadata,
} from './invalidation'
import { QuestionEditor } from './QuestionEditor'

function assessmentStatusTone(status: string) {
  if (status === 'REVIEW') return 'info' as const
  if (status === 'PUBLISHED') return 'success' as const
  return 'neutral' as const
}

export { AdminPeriodicTestsPage as AdminAssessmentsPage } from './AdminPeriodicTestsPage'

export function AssessmentEditor({ assessmentId, embedded = false, readOnly = false }: { assessmentId: string; embedded?: boolean; readOnly?: boolean }) {
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
  useAuthoringDirty(`assessment-metadata-${assessmentId}`, Boolean(dirty && assessment.data && (title.trim() !== assessment.data.title || description !== (assessment.data.description ?? '') || Number(threshold) !== assessment.data.pass_threshold)))
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
  if (embedded && assessment.isPending && !assessment.data) return <LoadingState>Đang tải bài luyện tập…</LoadingState>
  if (embedded && assessment.isError && !assessment.data) return <Alert tone="error" action={<Button onClick={() => void assessment.refetch()}>Thử lại</Button>}>{adminErrorText(assessment.error, 'Không thể tải bài luyện tập.')}</Alert>
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
  const editable = !readOnly && (item.status === 'DRAFT' || item.status === 'REVIEW')
  const changed = title.trim() !== item.title || description !== (item.description ?? '') || Number(threshold) !== item.pass_threshold
  const titleContext = item.lesson_id && lesson.data ? `HSK ${hsk.data?.find((level) => level.id === lesson.data.hsk_level_id)?.level_number ?? '—'} · Bài ${lesson.data.lesson_number} · ${lesson.data.title}` : item.type === 'PERIODIC_TEST' ? "Kiểm tra định kỳ" : "Bài luyện tập"
  if (!embedded && item.lesson_id) return <Navigate replace to={`/admin/lessons/${encodeURIComponent(item.lesson_id)}?section=exercises&exercise=${encodeURIComponent(item.id)}`} />
  const headingId = embedded ? `exercise-${assessmentId}-title` : 'page-title'
  return <section className={embedded ? 'admin-assessment-editor-page admin-embedded-assessment' : 'screen admin-screen admin-assessment-editor-page'} aria-labelledby={headingId}>
    {embedded ? <div className="admin-embedded-assessment-heading"><h3 id={headingId}>{item.title}</h3><StatusBadge tone={assessmentStatusTone(item.status)}>{adminLabel(item.status)}</StatusBadge><p>Điểm đạt: {item.pass_threshold}% · Chỉnh sửa và xem trước câu hỏi ngay trong bài học.</p></div> : <>
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
    <AuthoringNotice/></>}
    <nav className="admin-studio-nav" aria-label="Khu vực biên soạn bài luyện tập"><button type="button" aria-pressed={area === 'questions'} onClick={() => setArea('questions')}>Câu hỏi ({questions.data?.length ?? '—'})</button><button type="button" aria-pressed={area === 'metadata'} onClick={() => setArea('metadata')}>Thông tin bài luyện tập</button></nav>
    <div hidden={area !== 'metadata'}><Surface as="section" className="admin-editor-section admin-editor-card admin-assessment-metadata" aria-labelledby={`assessment-${assessmentId}-metadata-title`}>
      <div className="admin-page-header admin-assessment-section-heading"><div><h2 id={`assessment-${assessmentId}-metadata-title`}>Thông tin bài luyện tập</h2><p>{editable ? "Chỉnh sửa tiêu đề, mô tả và ngưỡng điểm đạt." : "Thông tin bài đã xuất bản hoặc lưu trữ chỉ có thể xem."}</p></div>{changed && editable && <StatusBadge tone="warning">Thông tin chưa được lưu</StatusBadge>}</div>
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
