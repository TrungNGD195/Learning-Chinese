import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { queryKeys } from '../../app/query/keys'
import { adminErrorText } from './AdminPrimitives'
import {
  attachGrammar, attachVocabulary, detachGrammar, detachVocabulary,
  listLessonGrammar, listLessonVocabulary, updateLessonGrammar, updateLessonVocabulary,
} from './api'
import { invalidateLessonContent } from './invalidation'

type Kind = 'vocabulary' | 'grammar'
type ContentItem = Awaited<ReturnType<typeof listLessonVocabulary>>[number]
type VocabularyBody = Parameters<typeof attachVocabulary>[1]
type GrammarBody = Parameters<typeof attachGrammar>[1]

function ContentItemEditor({ item, lessonId, hskId, kind, lessonStatus }: {
  item: ContentItem; lessonId: string; hskId: string; kind: Kind; lessonStatus: string
}) {
  const client = useQueryClient()
  const [hanzi, setHanzi] = useState(item.hanzi ?? '')
  const [pinyin, setPinyin] = useState(item.pinyin ?? '')
  const [meaning, setMeaning] = useState(item.vietnamese_meaning ?? '')
  const [pos, setPos] = useState(item.part_of_speech ?? '')
  const [name, setName] = useState(item.name ?? '')
  const [structure, setStructure] = useState(item.structure ?? '')
  const [explanation, setExplanation] = useState(item.explanation ?? '')
  const [usage, setUsage] = useState(item.usage ?? '')
  const [order, setOrder] = useState(String(item.order_index))
  const [note, setNote] = useState(item.note ?? '')
  const [example, setExample] = useState(item.example ?? '')
  const [editing, setEditing] = useState(false)
  const updateVocabulary = useMutation({
    mutationFn: (body: Parameters<typeof updateLessonVocabulary>[2]) => updateLessonVocabulary(lessonId, item.id, body),
    retry: false,
    onSuccess: () => invalidateLessonContent(client, lessonId, hskId, kind),
  })
  const updateGrammar = useMutation({
    mutationFn: (body: Parameters<typeof updateLessonGrammar>[2]) => updateLessonGrammar(lessonId, item.id, body),
    retry: false,
    onSuccess: () => invalidateLessonContent(client, lessonId, hskId, kind),
  })
  const remove = useMutation({
    mutationFn: () => kind === 'vocabulary' ? detachVocabulary(lessonId, item.id) : detachGrammar(lessonId, item.id),
    retry: false,
    onSuccess: () => invalidateLessonContent(client, lessonId, hskId, kind),
  })
  const updatePending = updateVocabulary.isPending || updateGrammar.isPending
  const updateError = updateVocabulary.error ?? updateGrammar.error
  const save = () => {
    const order_index = Number(order)
    if (!Number.isInteger(order_index) || order_index < 1) return
    if (kind === 'vocabulary') updateVocabulary.mutate({ hanzi: hanzi.trim(), pinyin: pinyin.trim(), vietnamese_meaning: meaning.trim(), part_of_speech: pos.trim() || null, order_index, note: note || null, example: example || null })
    else updateGrammar.mutate({ name: name.trim(), structure: structure || null, explanation: explanation.trim(), usage: usage || null, order_index, note: note || null, example: example || null })
  }
  return <article className="admin-content-item">
    <h3>{kind === 'vocabulary' ? `${item.hanzi ?? ''} (${item.pinyin ?? ''})` : item.name}</h3>
    <p>{kind === 'vocabulary' ? item.vietnamese_meaning : item.structure}</p>
    <p>Lesson placement: order {item.order_index}{item.note ? ` · ${item.note}` : ''}</p>
    {lessonStatus !== 'ARCHIVED' && <button type="button" onClick={() => setEditing((value) => !value)}>{editing ? 'Close editor' : 'Edit content and placement'}</button>}
    {editing && <div className="admin-edit-fields">
      <h4>Canonical {kind === 'vocabulary' ? 'Vocabulary' : 'Grammar'} content</h4>
      {kind === 'vocabulary' ? <>
        <label>Hanzi<input value={hanzi} onChange={(event) => setHanzi(event.target.value)} /></label>
        <label>Pinyin<input value={pinyin} onChange={(event) => setPinyin(event.target.value)} /></label>
        <label>Vietnamese meaning<input value={meaning} onChange={(event) => setMeaning(event.target.value)} /></label>
        <label>Part of speech<input value={pos} onChange={(event) => setPos(event.target.value)} /></label>
      </> : <>
        <label>Name<input value={name} onChange={(event) => setName(event.target.value)} /></label>
        <label>Structure<input value={structure} onChange={(event) => setStructure(event.target.value)} /></label>
        <label>Explanation<textarea value={explanation} onChange={(event) => setExplanation(event.target.value)} /></label>
        <label>Usage<textarea value={usage} onChange={(event) => setUsage(event.target.value)} /></label>
      </>}
      <h4>Lesson association</h4>
      <label>Order<input type="number" min="1" value={order} onChange={(event) => setOrder(event.target.value)} /></label>
      <label>Note<input value={note} onChange={(event) => setNote(event.target.value)} /></label>
      <label>Example<textarea value={example} onChange={(event) => setExample(event.target.value)} /></label>
      {(updateVocabulary.isError || updateGrammar.isError) && <p role="alert">{adminErrorText(updateError, 'Could not update lesson content.')}</p>}
      <button type="button" disabled={updatePending || !order || (kind === 'vocabulary' ? !hanzi.trim() || !pinyin.trim() || !meaning.trim() : !name.trim() || !explanation.trim())} onClick={save}>{updatePending ? 'Saving…' : 'Save content changes'}</button>
    </div>}
    {kind === 'vocabulary' ? updateVocabulary.isSuccess && <p role="status">Vocabulary updated.</p> : updateGrammar.isSuccess && <p role="status">Grammar updated.</p>}
    {lessonStatus === 'DRAFT' && <>
      {remove.isError && <p role="alert">{adminErrorText(remove.error, 'Could not detach this item.')}</p>}
      <button type="button" disabled={remove.isPending} onClick={() => {
        if (globalThis.confirm(`Detach this ${kind} from the lesson?`)) remove.mutate()
      }}>{remove.isPending ? 'Detaching…' : `Detach ${kind}`}</button>
    </>}
  </article>
}

function AttachForm({ lessonId, hskId, kind }: { lessonId: string; hskId: string; kind: Kind }) {
  const client = useQueryClient()
  const [hanzi, setHanzi] = useState('')
  const [pinyin, setPinyin] = useState('')
  const [meaning, setMeaning] = useState('')
  const [pos, setPos] = useState('')
  const [name, setName] = useState('')
  const [structure, setStructure] = useState('')
  const [explanation, setExplanation] = useState('')
  const [usage, setUsage] = useState('')
  const [order, setOrder] = useState('1')
  const [note, setNote] = useState('')
  const [example, setExample] = useState('')
  const vocabulary = useMutation({
    mutationFn: (body: VocabularyBody) => attachVocabulary(lessonId, body), retry: false,
    onSuccess: () => invalidateLessonContent(client, lessonId, hskId, kind),
  })
  const grammar = useMutation({
    mutationFn: (body: GrammarBody) => attachGrammar(lessonId, body), retry: false,
    onSuccess: () => invalidateLessonContent(client, lessonId, hskId, kind),
  })
  const pending = vocabulary.isPending || grammar.isPending
  const error = vocabulary.error ?? grammar.error
  const submit = (event: React.FormEvent) => {
    event.preventDefault()
    const order_index = Number(order)
    if (!Number.isInteger(order_index) || order_index < 1) return
    if (kind === 'vocabulary') vocabulary.mutate({ hanzi: hanzi.trim(), pinyin: pinyin.trim(), vietnamese_meaning: meaning.trim(), ...(pos.trim() ? { part_of_speech: pos.trim() } : {}), order_index, ...(note ? { note } : {}), ...(example ? { example } : {}) })
    else grammar.mutate({ name: name.trim(), ...(structure ? { structure } : {}), explanation: explanation.trim(), ...(usage ? { usage } : {}), order_index, ...(note ? { note } : {}), ...(example ? { example } : {}) })
  }
  return <form className="admin-edit-fields" onSubmit={submit}>
    <h3>Create new {kind === 'vocabulary' ? 'Vocabulary' : 'Grammar'} and attach</h3>
    <p>This creates canonical content and its Lesson association together.</p>
    {kind === 'vocabulary' ? <>
      <label>Hanzi<input required value={hanzi} onChange={(event) => setHanzi(event.target.value)} /></label>
      <label>Pinyin<input required value={pinyin} onChange={(event) => setPinyin(event.target.value)} /></label>
      <label>Vietnamese meaning<input required value={meaning} onChange={(event) => setMeaning(event.target.value)} /></label>
      <label>Part of speech<input value={pos} onChange={(event) => setPos(event.target.value)} /></label>
    </> : <>
      <label>Name<input required value={name} onChange={(event) => setName(event.target.value)} /></label>
      <label>Structure<input value={structure} onChange={(event) => setStructure(event.target.value)} /></label>
      <label>Explanation<textarea required value={explanation} onChange={(event) => setExplanation(event.target.value)} /></label>
      <label>Usage<textarea value={usage} onChange={(event) => setUsage(event.target.value)} /></label>
    </>}
    <h4>Lesson association</h4>
    <label>Order<input required type="number" min="1" value={order} onChange={(event) => setOrder(event.target.value)} /></label>
    <label>Note<input value={note} onChange={(event) => setNote(event.target.value)} /></label>
    <label>Example<textarea value={example} onChange={(event) => setExample(event.target.value)} /></label>
    {error && <p role="alert">{adminErrorText(error, `Could not attach ${kind}.`)}</p>}
    <button type="submit" disabled={pending || !order}>{pending ? 'Attaching…' : `Create and attach ${kind}`}</button>
  </form>
}

export function LessonContentSection({ lessonId, hskId, kind, lessonStatus }: {
  lessonId: string; hskId: string; kind: Kind; lessonStatus: string
}) {
  const queryKey = kind === 'vocabulary' ? queryKeys.adminLessonVocabulary(lessonId) : queryKeys.adminLessonGrammar(lessonId)
  const queryFn = kind === 'vocabulary' ? () => listLessonVocabulary(lessonId) : () => listLessonGrammar(lessonId)
  const query = useQuery({ queryKey, queryFn })
  if (query.isPending && !query.data) return <section className="learning-card"><h2>{kind === 'vocabulary' ? 'Vocabulary' : 'Grammar'}</h2><p role="status">Loading {kind}…</p></section>
  if (query.isError && !query.data) return <section className="learning-card"><h2>{kind === 'vocabulary' ? 'Vocabulary' : 'Grammar'}</h2><p role="alert">{adminErrorText(query.error, `Could not load ${kind}.`)}</p><button type="button" onClick={() => void query.refetch()}>Retry</button></section>
  return <section className="learning-card" aria-label={`Lesson ${kind}`}>
    <h2>{kind === 'vocabulary' ? 'Vocabulary' : 'Grammar'}</h2>
    {query.isError && <p role="alert">{kind} could not be refreshed.</p>}
    {query.data?.length ? <div className="admin-content-list">{query.data.map((item) => <ContentItemEditor key={item.id} item={item} lessonId={lessonId} hskId={hskId} kind={kind} lessonStatus={lessonStatus} />)}</div> : <p>No {kind} is attached to this lesson.</p>}
    {lessonStatus !== 'ARCHIVED' && <AttachForm lessonId={lessonId} hskId={hskId} kind={kind} />}
    {query.isFetching && <p role="status">Refreshing {kind}…</p>}
  </section>
}
