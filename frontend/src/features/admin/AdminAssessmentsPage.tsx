import { useEffect, useState } from 'react'
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router'
import { queryKeys } from '../../app/query/keys'
import { ApiError } from '../../lib/api/errors'
import { adminErrorText, isNotFound } from './AdminPrimitives'
import {
  archiveAdminAssessment, createAdminAssessment, getAdminAssessment, getAdminLesson,
  listAdminAssessments, listAdminLessons, listAssessmentQuestions, listHskLevels,
  publishAdminAssessment, submitAssessmentReview, updateAdminAssessment,
} from './api'
import {
  invalidateAssessmentLifecycle, invalidateAssessmentList, invalidateAssessmentMetadata,
} from './invalidation'
import { QuestionEditor } from './QuestionEditor'
import { AssessmentGenerationForm } from './AssessmentGenerationForm'

const pageSize = 20

export function AdminAssessmentsPage() {
  const client = useQueryClient()
  const navigate = useNavigate()
  const [status, setStatus] = useState('')
  const [type, setType] = useState('')
  const [page, setPage] = useState(1)
  const [creating, setCreating] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [newType, setNewType] = useState<'LESSON_EXERCISE' | 'PERIODIC_TEST'>('LESSON_EXERCISE')
  const [lessonId, setLessonId] = useState('')
  const [selectorPage, setSelectorPage] = useState(1)
  const [selectorHsk, setSelectorHsk] = useState('')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [threshold, setThreshold] = useState('90')
  const filters = { page, page_size: pageSize, ...(status ? { status } : {}), ...(type ? { assessment_type: type } : {}) }
  const list = useQuery({ queryKey: queryKeys.adminAssessments(filters), queryFn: () => listAdminAssessments(filters) })
  const hsk = useQuery({ queryKey: queryKeys.adminHskLevels, queryFn: listHskLevels })
  const targetLessons = [...new Set((list.data?.items ?? []).flatMap((item) => item.lesson_id ? [item.lesson_id] : []))]
  const lessonTargets = useQueries({ queries: targetLessons.map((id) => ({ queryKey: queryKeys.adminLesson(id), queryFn: () => getAdminLesson(id) })) })
  const lessonTargetById = new Map(targetLessons.map((id, index) => [id, lessonTargets[index]?.data]))
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
  return <section className="screen" aria-labelledby="page-title">
    <h1 id="page-title">Admin Assessments</h1>
    <div className="admin-filter-row">
      <label>Status<select value={status} onChange={(event) => { setStatus(event.target.value); setPage(1) }}><option value="">All statuses</option><option>DRAFT</option><option>REVIEW</option><option>PUBLISHED</option><option>ARCHIVED</option></select></label>
      <label>Type<select value={type} onChange={(event) => { setType(event.target.value); setPage(1) }}><option value="">All types</option><option value="LESSON_EXERCISE">Lesson Exercise</option><option value="PERIODIC_TEST">Periodic Test</option></select></label>
      <button type="button" onClick={() => setCreating((value) => !value)}>{creating ? 'Close Create Assessment' : 'Create Assessment'}</button>
      <button type="button" onClick={() => setGenerating((value) => !value)}>{generating ? 'Close AI Draft Form' : 'Generate AI Draft'}</button>
    </div>
    {generating && <AssessmentGenerationForm />}
    {creating && <form className="learning-card" onSubmit={(event) => { event.preventDefault(); create.mutate() }}>
      <h2>Create Assessment</h2>
      <label>Type<select value={newType} onChange={(event) => { setNewType(event.target.value as typeof newType); setLessonId('') }}><option value="LESSON_EXERCISE">Lesson Exercise</option><option value="PERIODIC_TEST">Periodic Test</option></select></label>
      {newType === 'LESSON_EXERCISE' && <>
        <label>Filter lesson choices by HSK<select value={selectorHsk} onChange={(event) => { setSelectorHsk(event.target.value); setSelectorPage(1) }}><option value="">All HSK levels</option>{(hsk.data ?? []).map((level) => <option value={level.id} key={level.id}>HSK {level.level_number}{level.title ? ` — ${level.title}` : ''}</option>)}</select></label>
        <label>Lesson<select required value={lessonId} onChange={(event) => setLessonId(event.target.value)}><option value="">Select lesson</option>{targetChoices.map((lesson) => <option value={lesson.id} key={lesson.id}>HSK {hsk.data?.find((level) => level.id === lesson.hsk_level_id)?.level_number ?? '—'} · Lesson {lesson.lesson_number} · {lesson.title}</option>)}</select></label>
        {lessons.isPending && <p role="status">Loading lesson choices…</p>}
        {lessons.isError && <p role="alert">{adminErrorText(lessons.error, 'Could not load lesson choices.')}</p>}
        {lessons.data && <div className="admin-page-controls"><button type="button" disabled={selectorPage <= 1} onClick={() => setSelectorPage((value) => Math.max(1, value - 1))}>Previous lessons</button><span>Page {lessons.data.page}</span><button type="button" disabled={selectorPage * lessons.data.page_size >= lessons.data.total} onClick={() => setSelectorPage((value) => value + 1)}>Next lessons</button></div>}
      </>}
      <label>Title<input required value={title} onChange={(event) => setTitle(event.target.value)} /></label>
      <label>Description<textarea value={description} onChange={(event) => setDescription(event.target.value)} /></label>
      <label>Pass threshold<input required type="number" min="0" max="100" value={threshold} onChange={(event) => setThreshold(event.target.value)} /></label>
      {create.isError && <p role="alert">{adminErrorText(create.error, 'Could not create assessment.')}</p>}
      <button type="submit" disabled={create.isPending || (newType === 'LESSON_EXERCISE' && !lessonId) || !title.trim() || Number(threshold) < 0 || Number(threshold) > 100}>{create.isPending ? 'Creating…' : 'Create Assessment'}</button>
    </form>}
    {list.isPending && !list.data && <p role="status">Loading assessments…</p>}
    {list.isError && !list.data && <><p role="alert">{adminErrorText(list.error, 'Could not load assessments.')}</p><button type="button" onClick={() => void list.refetch()}>Retry</button></>}
    {list.data && <>
      {list.isError && <p role="alert">Assessment list could not be refreshed.</p>}
      {list.data.items.length === 0 ? <p>No assessments match these filters.</p> : <table><thead><tr><th scope="col">Type</th><th scope="col">Title</th><th scope="col">Status</th><th scope="col">Pass threshold</th><th scope="col">Lesson</th><th scope="col">Action</th></tr></thead><tbody>
        {list.data.items.map((assessment) => {
          const target = assessment.lesson_id ? lessonTargetById.get(assessment.lesson_id) : undefined
          return <tr key={assessment.id}><td>{assessment.type === 'LESSON_EXERCISE' ? 'Lesson Exercise' : 'Periodic Test'}</td><td>{assessment.title}</td><td>{assessment.status}</td><td>{assessment.pass_threshold}</td><td>{assessment.lesson_id ? target ? `Lesson ${target.lesson_number} · ${target.title}` : 'Loading lesson target…' : '—'}</td><td><Link to={`/admin/assessments/${assessment.id}`}>Open Editor</Link></td></tr>
        })}
      </tbody></table>}
      <div className="admin-page-controls"><button type="button" disabled={page <= 1 || list.isFetching} onClick={() => setPage((value) => Math.max(1, value - 1))}>Previous</button><span>Page {list.data.page}</span><button type="button" disabled={page * list.data.page_size >= list.data.total || list.isFetching} onClick={() => setPage((value) => value + 1)}>Next</button></div>
      {list.isFetching && <p role="status">Refreshing assessments…</p>}
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
  useEffect(() => {
    if (assessment.data && !dirty) { setTitle(assessment.data.title); setDescription(assessment.data.description ?? ''); setThreshold(String(assessment.data.pass_threshold)) }
  }, [assessment.data, dirty])
  const metadata = useMutation({
    mutationFn: () => updateAdminAssessment(assessmentId, { title: title.trim(), description: description || null, pass_threshold: Number(threshold) }),
    retry: false,
    onSuccess: async (result) => { setTitle(result.title); setDescription(result.description ?? ''); setThreshold(String(result.pass_threshold)); setDirty(false); await invalidateAssessmentMetadata(client, result.id) },
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
  if (assessment.isPending && !assessment.data) return <section className="screen"><h1>Admin Assessment Editor</h1><p role="status">Loading assessment…</p></section>
  if (assessment.isError && !assessment.data) return <section className="screen"><h1>Admin Assessment Editor</h1><p role="alert">{isNotFound(assessment.error) ? 'Assessment not found.' : adminErrorText(assessment.error, 'Could not load assessment.')}</p><button type="button" onClick={() => void assessment.refetch()}>Retry</button><Link to="/admin/assessments">Back to Assessments</Link></section>
  if (!assessment.data) return null
  const item = assessment.data
  const editable = item.status === 'DRAFT' || item.status === 'REVIEW'
  const changed = title.trim() !== item.title || description !== (item.description ?? '') || Number(threshold) !== item.pass_threshold
  return <section className="screen" aria-labelledby="page-title">
    <p><Link to="/admin/assessments">Back to Assessments</Link></p><h1 id="page-title">Admin Assessment Editor</h1>
    {assessment.isError && <p role="alert">Assessment could not be refreshed. Current server data remains visible.</p>}
    <section className="learning-card"><h2>Assessment identity</h2><p>Type: {item.type === 'LESSON_EXERCISE' ? 'Lesson Exercise' : 'Periodic Test'}</p>
      {item.lesson_id && <p>Lesson: {lesson.data ? `HSK ${hsk.data?.find((level) => level.id === lesson.data.hsk_level_id)?.level_number ?? '—'} · Lesson ${lesson.data.lesson_number} · ${lesson.data.title}` : lesson.isError ? 'Lesson target unavailable.' : 'Loading lesson target…'}</p>}
      <p>Status: {item.status}</p>{item.published_at && <p>Published: {item.published_at}</p>}{assessment.isFetching && <p role="status">Refreshing assessment…</p>}
    </section>
    <form className="learning-card" onSubmit={(event) => { event.preventDefault(); metadata.mutate() }}>
      <h2>Assessment metadata</h2><label>Title<input value={title} disabled={!editable} onChange={(event) => { setTitle(event.target.value); setDirty(true) }} /></label>
      <label>Description<textarea value={description} disabled={!editable} onChange={(event) => { setDescription(event.target.value); setDirty(true) }} /></label>
      <label>Pass threshold<input type="number" min="0" max="100" value={threshold} disabled={!editable} onChange={(event) => { setThreshold(event.target.value); setDirty(true) }} /></label>
      {metadata.isError && <p role="alert">{adminErrorText(metadata.error, 'Could not save assessment metadata.')}</p>}
      <button type="submit" disabled={!editable || !changed || metadata.isPending || Number(threshold) < 0 || Number(threshold) > 100}>{metadata.isPending ? 'Saving…' : 'Save metadata'}</button>
    </form>
    {item.status === 'DRAFT' && <button type="button" disabled={lifecycle.isPending || questions.isPending || !questions.data?.length} onClick={() => lifecycle.mutate('review')}>{lifecycle.isPending ? 'Updating status…' : 'Submit Review'}</button>}
    {item.status === 'REVIEW' && <button type="button" disabled={lifecycle.isPending} onClick={() => lifecycle.mutate('publish')}>{lifecycle.isPending ? 'Updating status…' : 'Publish Assessment'}</button>}
    {item.status === 'PUBLISHED' && <button type="button" disabled={lifecycle.isPending} onClick={() => { if (globalThis.confirm('Archive this assessment?')) lifecycle.mutate('archive') }}>{lifecycle.isPending ? 'Updating status…' : 'Archive Assessment'}</button>}
    {questions.isError && !questions.data && <><p role="alert">{adminErrorText(questions.error, 'Could not load questions.')}</p><button type="button" onClick={() => void questions.refetch()}>Retry questions</button></>}
    {questions.isPending && !questions.data && <p role="status">Loading questions…</p>}
    {questions.data && <QuestionEditor assessmentId={item.id} questions={questions.data} editable={editable} />}
    {lifecycle.isError && <p role="alert">{adminErrorText(lifecycle.error, 'Could not change assessment status.')}</p>}
  </section>
}

export function AdminAssessmentEditorPage() {
  const { assessmentId } = useParams()
  if (!assessmentId) return <section className="screen"><h1>Admin Assessment Editor</h1><p role="alert">Assessment not found.</p></section>
  return <AssessmentEditor key={assessmentId} assessmentId={assessmentId} />
}
