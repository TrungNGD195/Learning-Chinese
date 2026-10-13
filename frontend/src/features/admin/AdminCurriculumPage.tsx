import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { queryKeys } from '../../app/query/keys'
import { adminErrorText } from './AdminPrimitives'
import { getAdminCurriculum, listAdminAssessments, listAdminLessons, listHskLevels, replaceAdminCurriculum, updateHskLevel } from './api'
import { invalidateCurriculumOrder, invalidateHskMetadata } from './invalidation'

type HskLevel = Awaited<ReturnType<typeof listHskLevels>>[number]
type UnitDraft = { unit_type: 'LESSON' | 'PERIODIC_TEST'; target_id: string; title: string; order_index: number }

function toDraft(units: Awaited<ReturnType<typeof getAdminCurriculum>>): UnitDraft[] {
  return units.flatMap((unit) => {
    const target = unit.unit_type === 'LESSON' ? unit.lesson_id : unit.assessment_id
    const title = unit.unit_type === 'LESSON' ? unit.lesson_title : unit.assessment_title
    return target ? [{ unit_type: unit.unit_type, target_id: target, title: title ?? '(Untitled)', order_index: unit.order_index }] : []
  })
}

function HskMetadataEditor({ hsk }: { hsk: HskLevel }) {
  const queryClient = useQueryClient()
  const [title, setTitle] = useState(hsk.title ?? '')
  const [description, setDescription] = useState(hsk.description ?? '')
  const [dirty, setDirty] = useState(false)
  useEffect(() => {
    if (!dirty) { setTitle(hsk.title ?? ''); setDescription(hsk.description ?? '') }
  }, [hsk.title, hsk.description, dirty])
  const mutation = useMutation({
    mutationFn: () => updateHskLevel(hsk.id, { title, description: description || null }),
    retry: false,
    onSuccess: async () => { setDirty(false); await invalidateHskMetadata(queryClient, hsk.id) },
  })
  const changed = title !== (hsk.title ?? '') || description !== (hsk.description ?? '')
  return <section className="learning-card" aria-labelledby="hsk-metadata-title">
    <h2 id="hsk-metadata-title">HSK {hsk.level_number} metadata</h2>
    <p>Level number and catalog order are fixed.</p>
    <label>Title<input value={title} onChange={(event) => { setTitle(event.target.value); setDirty(true) }} /></label>
    <label>Description<textarea value={description} onChange={(event) => { setDescription(event.target.value); setDirty(true) }} /></label>
    {mutation.isError && <p role="alert">{adminErrorText(mutation.error, 'Could not save HSK metadata.')}</p>}
    <button type="button" disabled={!changed || mutation.isPending} onClick={() => mutation.mutate()}>{mutation.isPending ? 'Saving…' : 'Save HSK metadata'}</button>
  </section>
}

function useHskRecord() {
  const levels = useQuery({ queryKey: queryKeys.adminHskLevels, queryFn: listHskLevels })
  const [selected, setSelected] = useState('')
  useEffect(() => {
    if (!selected && levels.data?.length) setSelected(levels.data[0].id)
  }, [levels.data, selected])
  return { levels, selected, setSelected, hsk: levels.data?.find((item) => item.id === selected) }
}

function CurriculumOrderEditor({ hskId }: { hskId: string }) {
  const queryClient = useQueryClient()
  const query = useQuery({ queryKey: queryKeys.adminCurriculum(hskId), queryFn: () => getAdminCurriculum(hskId) })
  const [draft, setDraft] = useState<UnitDraft[]>([])
  const [baseline, setBaseline] = useState('')
  const [lessonPage, setLessonPage] = useState(1)
  const [assessmentPage, setAssessmentPage] = useState(1)
  const current = JSON.stringify(draft.map(({ unit_type, target_id }) => ({ unit_type, target_id })))
  const dirty = baseline !== '' && current !== baseline
  const lessonFilters = { page: lessonPage, page_size: 20, status: 'PUBLISHED', hsk_level_id: hskId }
  const assessmentFilters = { page: assessmentPage, page_size: 20, status: 'PUBLISHED', assessment_type: 'PERIODIC_TEST' }
  const lessonCandidates = useQuery({ queryKey: queryKeys.adminLessons(lessonFilters), queryFn: () => listAdminLessons(lessonFilters) })
  const assessmentCandidates = useQuery({ queryKey: queryKeys.adminAssessments(assessmentFilters), queryFn: () => listAdminAssessments(assessmentFilters) })
  useEffect(() => {
    if (query.data && !dirty) {
      const next = toDraft(query.data)
      setDraft(next)
      setBaseline(JSON.stringify(next.map(({ unit_type, target_id }) => ({ unit_type, target_id }))))
    }
  }, [query.data, dirty])
  const mutation = useMutation({
    mutationFn: (units: UnitDraft[]) => replaceAdminCurriculum(hskId, { units: units.map(({ unit_type, target_id }, index) => ({ unit_type, target_id, order_index: index + 1 })) }),
    retry: false,
    onSuccess: async (result) => {
      queryClient.setQueryData(queryKeys.adminCurriculum(hskId), result)
      await invalidateCurriculumOrder(queryClient, hskId)
      const canonical = queryClient.getQueryData(queryKeys.adminCurriculum(hskId)) ?? result
      if (canonical) {
        const next = toDraft(canonical as Awaited<ReturnType<typeof getAdminCurriculum>>)
        setDraft(next)
        setBaseline(JSON.stringify(next.map(({ unit_type, target_id }) => ({ unit_type, target_id }))))
      }
    },
  })
  const move = (index: number, offset: number) => setDraft((items) => {
    const target = index + offset
    if (target < 0 || target >= items.length) return items
    const next = [...items]
    ;[next[index], next[target]] = [next[target], next[index]]
    return next.map((item, position) => ({ ...item, order_index: position + 1 }))
  })
  const addUnit = (unit: UnitDraft) => setDraft((items) => {
    if (items.some((item) => item.unit_type === unit.unit_type && item.target_id === unit.target_id)) return items
    return [...items, { ...unit, order_index: items.length + 1 }]
  })
  const removeUnit = (unit: UnitDraft) => setDraft((items) => items
    .filter((item) => item.unit_type !== unit.unit_type || item.target_id !== unit.target_id)
    .map((item, index) => ({ ...item, order_index: index + 1 })))
  if (query.isPending && !query.data) return <section className="learning-card"><h2>Curriculum order</h2><p role="status">Loading curriculum…</p></section>
  if (query.isError && !query.data) return <section className="learning-card"><h2>Curriculum order</h2><p role="alert">{adminErrorText(query.error, 'Could not load curriculum.')}</p><button type="button" onClick={() => void query.refetch()}>Retry</button></section>
  return <section className="learning-card" aria-labelledby="curriculum-order-title">
    <h2 id="curriculum-order-title">Curriculum membership and order</h2>
    {query.isError && <p role="alert">Curriculum could not be refreshed.</p>}
    {draft.length === 0 ? <p>No curriculum units are selected for this HSK.</p> : <ol aria-label="Desired curriculum membership">
      {draft.map((unit, index) => <li key={`${unit.unit_type}:${unit.target_id}`}>
        <span>{unit.order_index}. {unit.unit_type === 'LESSON' ? 'Lesson' : 'Periodic test'}: {unit.title}</span>
        <button type="button" aria-label={`Move ${unit.title} up`} disabled={index === 0} onClick={() => move(index, -1)}>Move Up</button>
        <button type="button" aria-label={`Move ${unit.title} down`} disabled={index === draft.length - 1} onClick={() => move(index, 1)}>Move Down</button>
        <button type="button" aria-label={`Remove ${unit.title} from curriculum`} onClick={() => removeUnit(unit)}>Remove from curriculum</button>
      </li>)}
    </ol>}
    <fieldset>
      <legend>Published Lesson candidates</legend>
      {lessonCandidates.isPending && <p role="status">Loading published Lessons…</p>}
      {lessonCandidates.isError && <><p role="alert">{adminErrorText(lessonCandidates.error, 'Could not load published Lessons.')}</p><button type="button" onClick={() => void lessonCandidates.refetch()}>Retry Lessons</button></>}
      {lessonCandidates.data && <>
        <ul>{lessonCandidates.data.items.filter((item) => item.status === 'PUBLISHED').map((item) => {
          const included = draft.some((unit) => unit.unit_type === 'LESSON' && unit.target_id === item.id)
          return <li key={item.id}><span>{item.title}</span>{included ? <span>Already included</span> : <button type="button" disabled={mutation.isPending} onClick={() => addUnit({ unit_type: 'LESSON', target_id: item.id, title: item.title, order_index: draft.length + 1 })}>Add {item.title} to curriculum</button>}</li>
        })}</ul>
        <button type="button" disabled={lessonPage <= 1} onClick={() => setLessonPage((page) => page - 1)}>Previous Lesson candidates</button>
        <span>Lesson candidate page {lessonCandidates.data.page}</span>
        <button type="button" disabled={lessonPage * lessonCandidates.data.page_size >= lessonCandidates.data.total} onClick={() => setLessonPage((page) => page + 1)}>Next Lesson candidates</button>
      </>}
    </fieldset>
    <fieldset>
      <legend>Published Periodic Test candidates</legend>
      {assessmentCandidates.isPending && <p role="status">Loading published Periodic Tests…</p>}
      {assessmentCandidates.isError && <><p role="alert">{adminErrorText(assessmentCandidates.error, 'Could not load published Periodic Tests.')}</p><button type="button" onClick={() => void assessmentCandidates.refetch()}>Retry Periodic Tests</button></>}
      {assessmentCandidates.data && <>
        <ul>{assessmentCandidates.data.items.filter((item) => item.status === 'PUBLISHED' && item.type === 'PERIODIC_TEST').map((item) => {
          const included = draft.some((unit) => unit.unit_type === 'PERIODIC_TEST' && unit.target_id === item.id)
          return <li key={item.id}><span>{item.title}</span>{included ? <span>Already included</span> : <button type="button" disabled={mutation.isPending} onClick={() => addUnit({ unit_type: 'PERIODIC_TEST', target_id: item.id, title: item.title, order_index: draft.length + 1 })}>Add {item.title} to curriculum</button>}</li>
        })}</ul>
        <button type="button" disabled={assessmentPage <= 1} onClick={() => setAssessmentPage((page) => page - 1)}>Previous Periodic Test candidates</button>
        <span>Periodic Test candidate page {assessmentCandidates.data.page}</span>
        <button type="button" disabled={assessmentPage * assessmentCandidates.data.page_size >= assessmentCandidates.data.total} onClick={() => setAssessmentPage((page) => page + 1)}>Next Periodic Test candidates</button>
      </>}
    </fieldset>
    {mutation.isError && <p role="alert">{adminErrorText(mutation.error, 'Could not save curriculum. Your unsaved draft is still available.')}</p>}
    {query.isFetching && <p role="status">Refreshing curriculum…</p>}
    <button type="button" disabled={!dirty || mutation.isPending} onClick={() => {
      if (globalThis.confirm('Save this curriculum membership and order?')) mutation.mutate(draft)
    }}>{mutation.isPending ? 'Saving curriculum…' : 'Save curriculum'}</button>
  </section>
}

export function AdminCurriculumPage() {
  const { levels, selected, setSelected, hsk } = useHskRecord()
  if (levels.isPending && !levels.data) return <section className="screen"><h1>Admin Curriculum</h1><p role="status">Loading HSK levels…</p></section>
  if (levels.isError && !levels.data) return <section className="screen"><h1>Admin Curriculum</h1><p role="alert">{adminErrorText(levels.error, 'Could not load HSK levels.')}</p><button type="button" onClick={() => void levels.refetch()}>Retry</button></section>
  return <section className="screen" aria-labelledby="page-title">
    <h1 id="page-title">Admin Curriculum</h1>
    {levels.isError && <p role="alert">HSK levels could not be refreshed.</p>}
    <label>Select HSK<select value={selected} onChange={(event) => setSelected(event.target.value)}>
      {(levels.data ?? []).map((item) => <option key={item.id} value={item.id}>HSK {item.level_number}{item.title ? ` — ${item.title}` : ''}</option>)}
    </select></label>
    {levels.data?.length === 0 && <p>No HSK levels are available.</p>}
    {hsk && <><HskMetadataEditor key={`metadata:${hsk.id}`} hsk={hsk} /><CurriculumOrderEditor key={`curriculum:${hsk.id}`} hskId={hsk.id} /></>}
  </section>
}
