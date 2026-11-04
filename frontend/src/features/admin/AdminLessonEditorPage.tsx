import { adminLabel, adminDate } from './labels'
import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'
import { queryKeys } from '../../app/query/keys'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Dialog } from '../../components/ui/Dialog'
import { LoadingState } from '../../components/ui/PageState'
import { PageHeader } from '../../components/ui/PageHeader'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { Surface } from '../../components/ui/Surface'
import { ApiError } from '../../lib/api/errors'
import { adminErrorText, isNotFound } from './AdminPrimitives'
import { getAdminLesson, listHskLevels, publishAdminLesson, archiveAdminLesson, updateAdminLesson } from './api'
import { invalidateLessonLifecycle, invalidateLessonMetadata } from './invalidation'
import { LessonContentSection } from './LessonContentSection'
import { LessonExercisesSection } from './LessonExercisesSection'
import { AuthoringSession, AuthoringNotice, useAuthoringDirty, useHasUnsavedDrafts } from './AuthoringSession'

function LessonEditor({ lessonId }: { lessonId: string }) {
  const client = useQueryClient()
  const query = useQuery({ queryKey: queryKeys.adminLesson(lessonId), queryFn: () => getAdminLesson(lessonId) })
  const hskQuery = useQuery({ queryKey: queryKeys.adminHskLevels, queryFn: listHskLevels })
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [dirty, setDirty] = useState(false)
  const [archiveOpen, setArchiveOpen] = useState(false)
  const [area, setArea] = useState<'vocabulary' | 'grammar' | 'metadata' | 'exercises'>('vocabulary')
  const unsaved = useHasUnsavedDrafts()
  useAuthoringDirty('lesson-metadata', Boolean(dirty && query.data && (title.trim() !== query.data.title || description !== (query.data.description ?? ''))))
  useEffect(() => {
    if (query.data && !dirty) { setTitle(query.data.title); setDescription(query.data.description ?? '') }
  }, [query.data, dirty])
  const save = useMutation({
    mutationFn: () => updateAdminLesson(lessonId, { title: title.trim(), description: description || null }),
    retry: false,
    onSuccess: async (lesson) => {
      await client.cancelQueries({ queryKey: queryKeys.adminLesson(lessonId), exact: true })
      client.setQueryData(queryKeys.adminLesson(lessonId), lesson)
      setTitle(lesson.title)
      setDescription(lesson.description ?? '')
      setDirty(false)
      await invalidateLessonMetadata(client, lesson.id, lesson.hsk_level_id)
    },
    onError: async (error) => {
      if (error instanceof ApiError && error.status === 409 && query.data) await invalidateLessonMetadata(client, lessonId, query.data.hsk_level_id)
    },
  })
  const lifecycle = useMutation({
    mutationFn: (action: 'publish' | 'archive') => action === 'publish' ? publishAdminLesson(lessonId) : archiveAdminLesson(lessonId),
    retry: false,
    onSuccess: async (lesson) => await invalidateLessonLifecycle(client, lesson.id, lesson.hsk_level_id),
    onError: async (error) => {
      if (error instanceof ApiError && error.status === 409 && query.data) await invalidateLessonLifecycle(client, lessonId, query.data.hsk_level_id)
    },
  })
  if (query.isPending && !query.data) return <section className="screen admin-screen admin-lesson-editor-page" aria-labelledby="page-title">
    <div className="admin-lesson-hero admin-lesson-hero--state"><PageHeader title="Biên soạn bài học" titleId="page-title" back={<Link to="/admin/lessons">Quay lại bài học</Link>} /></div>
    <Surface className="admin-lesson-state-panel"><LoadingState>Đang tải bài học…</LoadingState></Surface>
  </section>
  if (query.isError && !query.data) return <section className="screen admin-screen admin-lesson-editor-page" aria-labelledby="page-title">
    <div className="admin-lesson-hero admin-lesson-hero--state"><PageHeader title="Biên soạn bài học" titleId="page-title" back={<Link to="/admin/lessons">Quay lại bài học</Link>} /></div>
    <Surface className="admin-lesson-state-panel"><Alert role="alert" tone="error" action={<Button onClick={() => void query.refetch()}>Thử lại</Button>}>{isNotFound(query.error) ? "Không tìm thấy bài học." : adminErrorText(query.error, "Không thể tải bài học.")}</Alert></Surface>
  </section>
  if (!query.data) return null
  const lesson = query.data
  const hskNumber = hskQuery.data?.find((level) => level.id === lesson.hsk_level_id)?.level_number
  const metadataChanged = title.trim() !== lesson.title || description !== (lesson.description ?? '')
  return <section className="screen admin-screen admin-lesson-editor-page" aria-labelledby="page-title">
    <div className="admin-lesson-hero">
      <PageHeader title={`Bài ${lesson.lesson_number} · ${lesson.title}`} titleId="page-title"
        description={`HSK ${hskNumber ?? '—'} · ${lesson.lesson_number}`}
        back={<Link to="/admin/lessons">Quay lại bài học</Link>} />
      {query.isError && <Alert tone="warning">Chưa cập nhật được bài học. Đang hiển thị dữ liệu đã tải.</Alert>}
      {hskQuery.isError && <Alert tone="warning">Chưa cập nhật được thông tin cấp độ HSK.</Alert>}
      <Surface as="section" className="admin-editor-card admin-lesson-lifecycle-panel" aria-labelledby="lesson-lifecycle-title">
        <h2 id="lesson-lifecycle-title">Trạng thái bài học</h2>
        <div className="admin-current-state"><p><span>Trạng thái: {adminLabel(lesson.status)}</span></p><StatusBadge aria-hidden="true" tone={lesson.status === 'PUBLISHED' ? 'success' : 'neutral'}>{adminLabel(lesson.status)}</StatusBadge></div>
        {lesson.published_at && <p>Ngày xuất bản: {adminDate(lesson.published_at)}</p>}
        <div className="admin-action-bar">
          {lesson.status === 'DRAFT' && <Button variant="primary" className="admin-primary-action" disabled={unsaved || lifecycle.isPending} onClick={() => lifecycle.mutate('publish')}>{lifecycle.isPending ? "Đang cập nhật trạng thái…" : "Xuất bản bài học"}</Button>}
          {lesson.status === 'PUBLISHED' && <Button variant="danger" disabled={lifecycle.isPending} onClick={() => setArchiveOpen(true)}>{lifecycle.isPending ? "Đang cập nhật trạng thái…" : "Lưu trữ bài học"}</Button>}
        </div>
        {lifecycle.isError && <Alert role="alert" tone="error">{adminErrorText(lifecycle.error, "Không thể thay đổi trạng thái bài học.")}</Alert>}
      </Surface>
    </div>
    <AuthoringNotice/>
    <nav className="admin-studio-nav" aria-label="Khu vực biên soạn bài học">{(['vocabulary', 'grammar', 'exercises', 'metadata'] as const).map((value) => <button key={value} type="button" aria-pressed={area === value} onClick={() => setArea(value)}>{{vocabulary: "Từ vựng", grammar: "Ngữ pháp", exercises: 'Luyện tập', metadata: "Thông tin bài học"}[value]}</button>)}</nav>
    <div className="admin-lesson-workspace">
      <div hidden={area !== 'metadata'}>
      <Surface as="section" className="admin-editor-section admin-editor-card admin-lesson-metadata-panel" aria-labelledby="lesson-metadata-title">
        <div className="admin-page-header"><div><h2 id="lesson-metadata-title">Thông tin bài học</h2><p>Tiêu đề và mô tả của bài học.</p></div>{metadataChanged && lesson.status !== 'ARCHIVED' && <StatusBadge tone="warning">Thông tin chưa được lưu</StatusBadge>}</div>
        <form className="admin-form-grid admin-lesson-metadata-form" onSubmit={(event) => { event.preventDefault(); if (lesson.status !== 'ARCHIVED' && metadataChanged && !save.isPending) save.mutate() }}>
          <label>Tiêu đề<input value={title} disabled={lesson.status === 'ARCHIVED' || save.isPending} onChange={(event) => { setTitle(event.target.value); setDirty(true) }} /></label>
          <label>Mô tả<textarea value={description} disabled={lesson.status === 'ARCHIVED' || save.isPending} onChange={(event) => { setDescription(event.target.value); setDirty(true) }} /></label>
          {save.isError && <Alert role="alert" tone="error">{adminErrorText(save.error, "Không thể lưu thông tin bài học.")}</Alert>}
          <div className="admin-form-actions"><Button type="submit" variant="primary" className="admin-primary-action" disabled={lesson.status === 'ARCHIVED' || !metadataChanged || save.isPending}>{save.isPending ? "Đang lưu…" : "Lưu thông tin"}</Button></div>
        </form>
      </Surface>
      </div>
      <div hidden={area !== 'vocabulary'}>
        <LessonContentSection lessonId={lesson.id} hskId={lesson.hsk_level_id} kind="vocabulary" lessonStatus={lesson.status} />
      </div>
      <div hidden={area !== 'grammar'}><LessonContentSection lessonId={lesson.id} hskId={lesson.hsk_level_id} kind="grammar" lessonStatus={lesson.status} />
      </div>
    </div>
    <div hidden={area !== 'exercises'}><LessonExercisesSection lessonId={lesson.id}/></div>
    {lesson.status === 'ARCHIVED' && <Alert tone="info">Bài học đã lưu trữ chỉ có thể xem.</Alert>}
    <Dialog cancelLabel="Hủy" open={archiveOpen} title="Lưu trữ bài học?" confirmLabel="Lưu trữ bài học" confirmVariant="danger" busy={lifecycle.isPending}
      onCancel={() => setArchiveOpen(false)} onClose={() => setArchiveOpen(false)}
      onConfirm={() => { lifecycle.mutate('archive'); setArchiveOpen(false) }}>
      Bài học sẽ được chuyển sang trạng thái lưu trữ.
    </Dialog>
  </section>
}

export function AdminLessonEditorPage() {
  const { lessonId } = useParams()
  if (!lessonId) return <section className="screen admin-screen admin-lesson-editor-page" aria-labelledby="page-title">
    <div className="admin-lesson-hero admin-lesson-hero--state"><PageHeader title="Biên soạn bài học" titleId="page-title" /></div>
    <Surface className="admin-lesson-state-panel"><Alert role="alert" tone="error">Không tìm thấy bài học.</Alert></Surface>
  </section>
  return <AuthoringSession key={lessonId}><LessonEditor lessonId={lessonId} /></AuthoringSession>
}
