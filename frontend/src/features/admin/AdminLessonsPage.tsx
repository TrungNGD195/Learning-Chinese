import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router'
import { queryKeys } from '../../app/query/keys'
import { adminErrorText } from './AdminPrimitives'
import { createAdminLesson, listAdminLessons, listHskLevels } from './api'
import { invalidateLessonList } from './invalidation'

export function AdminLessonsPage() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [status, setStatus] = useState('')
  const [hskId, setHskId] = useState('')
  const [page, setPage] = useState(1)
  const [showCreate, setShowCreate] = useState(false)
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
  return <section className="screen" aria-labelledby="page-title">
    <h1 id="page-title">Admin Lessons</h1>
    <div className="admin-filter-row">
      <label>Status<select value={status} onChange={(event) => { setStatus(event.target.value); setPage(1) }}>
        <option value="">All statuses</option><option value="DRAFT">Draft</option><option value="PUBLISHED">Published</option><option value="ARCHIVED">Archived</option>
      </select></label>
      <label>HSK<select value={hskId} onChange={(event) => { setHskId(event.target.value); setPage(1) }}>
        <option value="">All HSK levels</option>{(hskQuery.data ?? []).map((level) => <option value={level.id} key={level.id}>HSK {level.level_number}{level.title ? ` — ${level.title}` : ''}</option>)}
      </select></label>
      <button type="button" onClick={() => setShowCreate((shown) => !shown)}>{showCreate ? 'Close Create Lesson' : 'Create Lesson'}</button>
    </div>
    {showCreate && <form className="learning-card" onSubmit={(event) => { event.preventDefault(); create.mutate() }}>
      <h2>Create Lesson</h2>
      <label>HSK<select required value={createHsk} onChange={(event) => setCreateHsk(event.target.value)}>
        <option value="">Select HSK</option>{(hskQuery.data ?? []).map((level) => <option value={level.id} key={level.id}>HSK {level.level_number}{level.title ? ` — ${level.title}` : ''}</option>)}
      </select></label>
      <label>Lesson number<input type="number" min="1" required value={lessonNumber} onChange={(event) => setLessonNumber(event.target.value)} /></label>
      <label>Title<input required value={title} onChange={(event) => setTitle(event.target.value)} /></label>
      <label>Description<textarea value={description} onChange={(event) => setDescription(event.target.value)} /></label>
      {create.isError && <p role="alert">{adminErrorText(create.error, 'Could not create lesson.')}</p>}
      <button type="submit" disabled={create.isPending || !createHsk || !title.trim() || Number(lessonNumber) < 1}>{create.isPending ? 'Creating…' : 'Create Lesson'}</button>
    </form>}
    {list.isPending && !list.data && <p role="status">Loading lessons…</p>}
    {list.isError && !list.data && <><p role="alert">{adminErrorText(list.error, 'Could not load lessons.')}</p><button type="button" onClick={() => void list.refetch()}>Retry</button></>}
    {list.data && <>
      {list.isError && <p role="alert">Lesson list could not be refreshed.</p>}
      {list.data.items.length === 0 ? <p>No lessons match these filters.</p> : <table><thead><tr><th scope="col">HSK</th><th scope="col">Lesson</th><th scope="col">Title</th><th scope="col">Status</th><th scope="col">Action</th></tr></thead><tbody>
        {list.data.items.map((lesson) => <tr key={lesson.id}><td>{hskQuery.data?.find((level) => level.id === lesson.hsk_level_id)?.level_number ?? '—'}</td><td>{lesson.lesson_number}</td><td>{lesson.title}</td><td>{lesson.status}</td><td><Link to={`/admin/lessons/${lesson.id}`}>Open Editor</Link></td></tr>)}
      </tbody></table>}
      <div className="admin-page-controls"><button type="button" disabled={page <= 1 || list.isFetching} onClick={() => setPage((value) => Math.max(1, value - 1))}>Previous</button><span>Page {list.data.page}</span><button type="button" disabled={page * list.data.page_size >= list.data.total || list.isFetching} onClick={() => setPage((value) => value + 1)}>Next</button></div>
      {list.isFetching && <p role="status">Refreshing lessons…</p>}
    </>}
  </section>
}
