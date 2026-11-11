import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router'
import { queryKeys } from '../../app/query/keys'
import { Alert, Button, LoadingState } from '../../components/ui'
import { createAdminAssessment, listAdminAssessments } from './api'
import { AssessmentEditor } from './AdminAssessmentsPage'
import { adminLabel } from './labels'
import { AssessmentGenerationForm } from './AssessmentGenerationForm'
import { adminErrorText } from './AdminPrimitives'
import { useAuthoringDirty } from './AuthoringSession'

function CreateLessonPractice({ lessonId, onCreated }: { lessonId: string; onCreated: (id: string) => void }) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [threshold, setThreshold] = useState('80')
  useAuthoringDirty(`new-practice-${lessonId}`, Boolean(title || description || threshold !== '80'))
  const create = useMutation({ mutationFn: () => createAdminAssessment({ type: 'LESSON_EXERCISE', lesson_id: lessonId, title: title.trim(), description: description.trim() || null, pass_threshold: Number(threshold) }), retry: false,
    onSuccess: (item) => { setTitle(''); setDescription(''); setThreshold('80'); onCreated(item.id) },
  })
  return <form className="admin-form-grid" aria-label="Thêm bài luyện tập" onSubmit={(event) => { event.preventDefault(); if (!create.isPending && title.trim()) create.mutate() }}>
    <label>Tiêu đề bài luyện tập<input required value={title} disabled={create.isPending} onChange={(event) => setTitle(event.target.value)} /></label>
    <label>Mô tả bài luyện tập<textarea value={description} disabled={create.isPending} onChange={(event) => setDescription(event.target.value)} /></label>
    <label>Điểm đạt (%)<input required type="number" min="0" max="100" value={threshold} disabled={create.isPending} onChange={(event) => setThreshold(event.target.value)} /></label>
    {create.isError && <Alert role="alert" tone="error">{adminErrorText(create.error, 'Không thể tạo bài luyện tập.')}</Alert>}
    <div className="admin-form-actions"><Button type="submit" variant="primary" disabled={create.isPending || !title.trim() || threshold === '' || Number(threshold) < 0 || Number(threshold) > 100}>{create.isPending ? 'Đang tạo…' : 'Tạo bài luyện tập'}</Button></div>
  </form>
}

export function useLessonExercises(lessonId: string) {
  const filters = { lesson_id: lessonId, assessment_type: 'LESSON_EXERCISE', page: 1, page_size: 100 }
  return useQuery({
    queryKey: queryKeys.adminAssessments(filters),
    queryFn: async () => {
      const first = await listAdminAssessments(filters)
      const items = [...first.items]
      for (let page = 2; (page - 1) * first.page_size < first.total; page++) {
        const next = await listAdminAssessments({ ...filters, page })
        items.push(...next.items)
      }
      return items
    },
  })
}

export function LessonExercisesSection({ lessonId, readOnly, initialExerciseId }: { lessonId: string; readOnly: boolean; initialExerciseId?: string | null }) {
  const client = useQueryClient()
  const [params] = useSearchParams()
  const [creating, setCreating] = useState(params.get('create') === '1')
  const [generating, setGenerating] = useState(params.get('generate') === '1')
  const query = useLessonExercises(lessonId)
  const [selectedId, setSelectedId] = useState(initialExerciseId ?? '')
  const [visitedIds, setVisitedIds] = useState<string[]>([])
  const selected = query.data?.find((item) => item.id === selectedId)?.id ?? query.data?.find((item) => item.status !== 'ARCHIVED')?.id ?? query.data?.[0]?.id
  const editors = query.data?.filter((item) => item.id === selected || visitedIds.includes(item.id)) ?? []
  const onCreated = (id: string) => {
    setVisitedIds((ids) => [...new Set([...ids, selected ?? '', id])])
    setSelectedId(id); setCreating(false); setGenerating(false)
    void client.invalidateQueries({ queryKey: queryKeys.adminAssessmentsRoot })
  }
  return <section className="admin-editor-section admin-lesson-exercises" aria-labelledby="lesson-exercises-heading">
    <div className="admin-page-header"><div><h2 id="lesson-exercises-heading">Luyện tập của bài học</h2><p>Sửa câu hỏi, đáp án và xem trước tại đây. Duyệt cả bài học trong mục Duyệt xuất bản.</p></div>
      {!readOnly && <div className="admin-action-bar"><Button aria-expanded={creating} onClick={() => setCreating((value) => !value)}>Thêm bài luyện tập</Button><Button aria-expanded={generating} onClick={() => setGenerating((value) => !value)}>Tạo bản nháp bằng AI</Button></div>}
    </div>
    {!readOnly && <><div hidden={!creating}><CreateLessonPractice lessonId={lessonId} onCreated={onCreated}/></div><div hidden={!generating}>{generating && <AssessmentGenerationForm fixedLessonId={lessonId} onCreated={onCreated}/>}</div></>}
    {query.isPending && <LoadingState>Đang tải bài luyện tập…</LoadingState>}
    {query.isError && <Alert role="alert" tone="error" action={<Button onClick={() => void query.refetch()}>Thử lại</Button>}>Không thể tải bài luyện tập.</Alert>}
    {query.data?.length === 0 && <p>Bài học này chưa có bài luyện tập.</p>}
    {(query.data?.length ?? 0) > 1 && <nav className="admin-studio-nav" aria-label="Chọn bài luyện tập">{query.data?.map((item) => <button key={item.id} type="button" aria-pressed={selected === item.id} onClick={() => { setVisitedIds((ids) => [...new Set([...ids, selected ?? '', item.id])]); setSelectedId(item.id) }}>{item.title} · {adminLabel(item.status)}</button>)}</nav>}
    {editors.map((item) => <div key={item.id} hidden={selected !== item.id}><AssessmentEditor assessmentId={item.id} embedded readOnly={readOnly} /></div>)}
  </section>
}
