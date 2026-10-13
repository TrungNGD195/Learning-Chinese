import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'
import { queryKeys } from '../../app/query/keys'
import { ApiError } from '../../lib/api/errors'
import { adminErrorText, isNotFound } from './AdminPrimitives'
import { getAdminLesson, listHskLevels, publishAdminLesson, archiveAdminLesson, updateAdminLesson } from './api'
import { invalidateLessonLifecycle, invalidateLessonMetadata } from './invalidation'
import { LessonContentSection } from './LessonContentSection'

function LessonEditor({ lessonId }: { lessonId: string }) {
  const client = useQueryClient()
  const query = useQuery({ queryKey: queryKeys.adminLesson(lessonId), queryFn: () => getAdminLesson(lessonId) })
  const hskQuery = useQuery({ queryKey: queryKeys.adminHskLevels, queryFn: listHskLevels })
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [dirty, setDirty] = useState(false)
  useEffect(() => {
    if (query.data && !dirty) { setTitle(query.data.title); setDescription(query.data.description ?? '') }
  }, [query.data, dirty])
  const save = useMutation({
    mutationFn: () => updateAdminLesson(lessonId, { title: title.trim(), description: description || null }),
    retry: false,
    onSuccess: async (lesson) => { setTitle(lesson.title); setDescription(lesson.description ?? ''); setDirty(false); await invalidateLessonMetadata(client, lesson.id, lesson.hsk_level_id) },
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
  if (query.isPending && !query.data) return <section className="screen"><h1>Admin Lesson Editor</h1><p role="status">Loading lesson…</p></section>
  if (query.isError && !query.data) return <section className="screen"><h1>Admin Lesson Editor</h1><p role="alert">{isNotFound(query.error) ? 'Lesson not found.' : adminErrorText(query.error, 'Could not load lesson.')}</p><button type="button" onClick={() => void query.refetch()}>Retry</button><Link to="/admin/lessons">Back to Lessons</Link></section>
  if (!query.data) return null
  const lesson = query.data
  const metadataChanged = title.trim() !== lesson.title || description !== (lesson.description ?? '')
  return <section className="screen" aria-labelledby="page-title">
    <p><Link to="/admin/lessons">Back to Lessons</Link></p>
    <h1 id="page-title">Admin Lesson Editor</h1>
    {query.isError && <p role="alert">Lesson could not be refreshed. Current server data remains visible.</p>}
    <section className="learning-card"><h2>Lesson identity</h2>
      <p>HSK {hskQuery.data?.find((level) => level.id === lesson.hsk_level_id)?.level_number ?? '—'}</p><p>Lesson number: {lesson.lesson_number}</p><p>Status: {lesson.status}</p>
      {lesson.published_at && <p>Published: {lesson.published_at}</p>}
      {query.isFetching && <p role="status">Refreshing lesson…</p>}
    </section>
    <form className="learning-card" onSubmit={(event) => { event.preventDefault(); save.mutate() }}>
      <h2>Lesson metadata</h2>
      <label>Title<input value={title} disabled={lesson.status === 'ARCHIVED'} onChange={(event) => { setTitle(event.target.value); setDirty(true) }} /></label>
      <label>Description<textarea value={description} disabled={lesson.status === 'ARCHIVED'} onChange={(event) => { setDescription(event.target.value); setDirty(true) }} /></label>
      {save.isError && <p role="alert">{adminErrorText(save.error, 'Could not save lesson metadata.')}</p>}
      <button type="submit" disabled={lesson.status === 'ARCHIVED' || !metadataChanged || save.isPending}>{save.isPending ? 'Saving…' : 'Save metadata'}</button>
    </form>
    {lesson.status === 'DRAFT' && <button type="button" disabled={lifecycle.isPending} onClick={() => lifecycle.mutate('publish')}>{lifecycle.isPending ? 'Updating status…' : 'Publish Lesson'}</button>}
    {lesson.status === 'PUBLISHED' && <button type="button" disabled={lifecycle.isPending} onClick={() => {
      if (globalThis.confirm('Archive this lesson?')) lifecycle.mutate('archive')
    }}>{lifecycle.isPending ? 'Updating status…' : 'Archive Lesson'}</button>}
    {lifecycle.isError && <p role="alert">{adminErrorText(lifecycle.error, 'Could not change lesson status.')}</p>}
    <LessonContentSection lessonId={lesson.id} hskId={lesson.hsk_level_id} kind="vocabulary" lessonStatus={lesson.status} />
    <LessonContentSection lessonId={lesson.id} hskId={lesson.hsk_level_id} kind="grammar" lessonStatus={lesson.status} />
    {lesson.status === 'ARCHIVED' && <p>Archived lesson content is read-only.</p>}
  </section>
}

export function AdminLessonEditorPage() {
  const { lessonId } = useParams()
  if (!lessonId) return <section className="screen"><h1>Admin Lesson Editor</h1><p role="alert">Lesson not found.</p></section>
  return <LessonEditor key={lessonId} lessonId={lessonId} />
}
