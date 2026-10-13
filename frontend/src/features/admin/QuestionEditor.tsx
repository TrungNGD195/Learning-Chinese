import { useState, type FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { adminErrorText } from './AdminPrimitives'
import { createAssessmentQuestion, deleteAssessmentQuestion, listAssessmentQuestions, updateAssessmentQuestion } from './api'
import { invalidateAssessmentQuestions } from './invalidation'

type Question = Awaited<ReturnType<typeof listAssessmentQuestions>>[number]
type QuestionCreate = Parameters<typeof createAssessmentQuestion>[1]
type QuestionPatch = Parameters<typeof updateAssessmentQuestion>[2]
type QuestionType = QuestionCreate['type']
type MatchRow = { id: string; text: string }
type OptionRow = { text: string; correct: boolean }

const types: QuestionType[] = ['multiple_choice', 'fill_blank', 'matching', 'reorder_sentence', 'translate_vi_zh', 'translate_zh_vi', 'sentence_writing']
const typeLabels: Record<QuestionType, string> = {
  multiple_choice: 'Multiple choice', fill_blank: 'Fill blank', matching: 'Matching', reorder_sentence: 'Reorder sentence',
  translate_vi_zh: 'Translate Vietnamese to Chinese', translate_zh_vi: 'Translate Chinese to Vietnamese', sentence_writing: 'Sentence writing',
}

function opaqueId() {
  if (typeof globalThis.crypto.randomUUID === 'function') return globalThis.crypto.randomUUID()
  return Array.from(globalThis.crypto.getRandomValues(new Uint8Array(16)), (value) => value.toString(16).padStart(2, '0')).join('')
}

function configRows(question: Question | null, key: 'left_items' | 'right_items' | 'items'): MatchRow[] {
  const config = question?.config
  if (config && key in config) {
    const value = config[key]
    if (Array.isArray(value)) return value.map((item) => ({ id: item.id, text: item.text }))
  }
  return []
}

function QuestionForm({ assessmentId, question, onClose }: { assessmentId: string; question: Question | null; onClose: () => void }) {
  const client = useQueryClient()
  const [type, setType] = useState<QuestionType>(question?.type ?? 'multiple_choice')
  const [prompt, setPrompt] = useState(question?.prompt ?? '')
  const [order, setOrder] = useState(String(question?.order_index ?? 1))
  const [points, setPoints] = useState(String(question?.points ?? 1))
  const [referenceAnswer, setReferenceAnswer] = useState(question?.reference_answer ?? '')
  const [rubric, setRubric] = useState(question?.rubric ?? '')
  const [acceptedAnswers, setAcceptedAnswers] = useState((question?.config && 'accepted_answers' in question.config ? question.config.accepted_answers : []).join('\n'))
  const [options, setOptions] = useState<OptionRow[]>(question?.options.length ? question.options.map((item) => ({ text: item.option_text, correct: item.is_correct })) : [{ text: '', correct: true }, { text: '', correct: false }])
  const [left, setLeft] = useState(() => configRows(question, 'left_items'))
  const [right, setRight] = useState(() => configRows(question, 'right_items'))
  const [items, setItems] = useState(() => configRows(question, 'items'))
  const [pairs, setPairs] = useState<Record<string, string>>(() => {
    const config = question?.config
    if (config && 'correct_pairs' in config) return Object.fromEntries(config.correct_pairs.map((pair) => [pair.left_id, pair.right_id]))
    return {}
  })
  const [error, setError] = useState('')

  const create = useMutation({ mutationFn: (body: QuestionCreate) => createAssessmentQuestion(assessmentId, body), retry: false,
    onSuccess: async () => { await invalidateAssessmentQuestions(client, assessmentId); onClose() },
  })
  const update = useMutation({ mutationFn: (body: QuestionPatch) => updateAssessmentQuestion(assessmentId, question!.id, body), retry: false,
    onSuccess: async () => { await invalidateAssessmentQuestions(client, assessmentId); onClose() },
  })

  const submit = (event: FormEvent) => {
    event.preventDefault()
    setError('')
    const order_index = Number(order)
    const numericPoints = Number(points)
    if (!prompt.trim() || !Number.isInteger(order_index) || order_index < 1 || !Number.isFinite(numericPoints) || numericPoints <= 0) {
      setError('Enter a prompt, positive order, and positive points.')
      return
    }
    let payload: QuestionCreate
    if (type === 'multiple_choice') {
      const validOptions = options.filter((item) => item.text.trim())
      if (validOptions.length < 2 || validOptions.filter((item) => item.correct).length !== 1) { setError('Add at least two options and mark exactly one as correct.'); return }
      payload = { type, prompt: prompt.trim(), order_index, points: numericPoints, options: validOptions.map((item) => ({ option_text: item.text.trim(), is_correct: item.correct })) }
    } else if (type === 'fill_blank') {
      if (!referenceAnswer.trim()) { setError('Enter a reference answer.'); return }
      payload = { type, prompt: prompt.trim(), order_index, points: numericPoints, reference_answer: referenceAnswer.trim(), config: { accepted_answers: acceptedAnswers.split('\n').map((value) => value.trim()).filter(Boolean) } }
    } else if (type === 'matching') {
      const leftItems = left.filter((item) => item.text.trim())
      const rightItems = right.filter((item) => item.text.trim())
      if (!leftItems.length || !rightItems.length || leftItems.some((item) => !pairs[item.id] || !rightItems.some((rightItem) => rightItem.id === pairs[item.id]))) { setError('Add both sides and choose a right item for every left item.'); return }
      payload = { type, prompt: prompt.trim(), order_index, points: numericPoints, config: { left_items: leftItems.map((item) => ({ ...item, text: item.text.trim() })), right_items: rightItems.map((item) => ({ ...item, text: item.text.trim() })), correct_pairs: leftItems.map((item) => ({ left_id: item.id, right_id: pairs[item.id] })) } }
    } else if (type === 'reorder_sentence') {
      const ordered = items.filter((item) => item.text.trim())
      if (!ordered.length) { setError('Add at least one sentence item.'); return }
      payload = { type, prompt: prompt.trim(), order_index, points: numericPoints, config: { items: ordered.map((item) => ({ ...item, text: item.text.trim() })), correct_order: ordered.map((item) => item.id) } }
    } else {
      const freeFormFields = question
        ? { reference_answer: referenceAnswer.trim() || null, rubric: rubric.trim() || null }
        : { ...(referenceAnswer.trim() ? { reference_answer: referenceAnswer.trim() } : {}), ...(rubric.trim() ? { rubric: rubric.trim() } : {}) }
      payload = { type, prompt: prompt.trim(), order_index, points: numericPoints, ...freeFormFields }
    }
    if (question) {
      const { type: _immutableType, ...body } = payload
      update.mutate(body)
    } else create.mutate(payload)
  }
  const pending = create.isPending || update.isPending
  const apiError = create.error ?? update.error
  const addRow = (setter: (fn: (rows: MatchRow[]) => MatchRow[]) => void) => setter((rows) => [...rows, { id: opaqueId(), text: '' }])
  const moveItem = (index: number, offset: number) => setItems((rows) => { const target = index + offset; if (target < 0 || target >= rows.length) return rows; const next = [...rows]; [next[index], next[target]] = [next[target], next[index]]; return next })

  return <form className="learning-card admin-question-form" onSubmit={submit}>
    <h3>{question ? 'Edit question' : 'Create question'}</h3>
    <label>Question type{question
      ? <input readOnly value={typeLabels[question.type]} />
      : <select value={type} onChange={(event) => setType(event.target.value as QuestionType)}>{types.map((value) => <option key={value} value={value}>{typeLabels[value]}</option>)}</select>}
    </label>
    <label>Prompt<textarea required value={prompt} onChange={(event) => setPrompt(event.target.value)} /></label>
    <label>Order<input required type="number" min="1" value={order} onChange={(event) => setOrder(event.target.value)} /></label>
    <label>Points<input required type="number" min="0.01" step="any" value={points} onChange={(event) => setPoints(event.target.value)} /></label>
    {type === 'multiple_choice' && <fieldset><legend>Options</legend>{options.map((option, index) => <div className="admin-option-row" key={index}>
      <label>Option {index + 1}<input value={option.text} onChange={(event) => setOptions((rows) => rows.map((row, rowIndex) => rowIndex === index ? { ...row, text: event.target.value } : row))} /></label>
      <label><input type="radio" name="correct-option" checked={option.correct} onChange={() => setOptions((rows) => rows.map((row, rowIndex) => ({ ...row, correct: rowIndex === index })))} /> Correct answer</label>
      <button type="button" disabled={options.length <= 2} onClick={() => setOptions((rows) => rows.filter((_, rowIndex) => rowIndex !== index))}>Remove option</button>
    </div>)}<button type="button" onClick={() => setOptions((rows) => [...rows, { text: '', correct: false }])}>Add option</button></fieldset>}
    {type === 'fill_blank' && <>
      <label>Reference answer<input required value={referenceAnswer} onChange={(event) => setReferenceAnswer(event.target.value)} /></label>
      <label>Accepted answers (one per line)<textarea value={acceptedAnswers} onChange={(event) => setAcceptedAnswers(event.target.value)} /></label>
    </>}
    {type === 'matching' && <>
      <fieldset><legend>Left items</legend>{left.map((item, index) => <div key={item.id} className="admin-option-row"><label>Left item {index + 1}<input value={item.text} onChange={(event) => setLeft((rows) => rows.map((row) => row.id === item.id ? { ...row, text: event.target.value } : row))} /></label><button type="button" onClick={() => setLeft((rows) => rows.filter((row) => row.id !== item.id))}>Remove left item</button></div>)}<button type="button" onClick={() => addRow(setLeft)}>Add left item</button></fieldset>
      <fieldset><legend>Right items</legend>{right.map((item, index) => <div key={item.id} className="admin-option-row"><label>Right item {index + 1}<input value={item.text} onChange={(event) => setRight((rows) => [...rows.slice(0, index), { ...rows[index], text: event.target.value }, ...rows.slice(index + 1)])} /></label><button type="button" onClick={() => setRight((rows) => rows.filter((row) => row.id !== item.id))}>Remove right item</button></div>)}<button type="button" onClick={() => addRow(setRight)}>Add right item</button></fieldset>
      <fieldset><legend>Correct pairs</legend>{left.map((item, index) => <label key={item.id}>Pair for {item.text || `left item ${index + 1}`}<select value={pairs[item.id] ?? ''} onChange={(event) => setPairs((current) => ({ ...current, [item.id]: event.target.value }))}><option value="">Choose right item</option>{right.map((candidate, rightIndex) => <option key={candidate.id} value={candidate.id}>{candidate.text || `Right item ${rightIndex + 1}`}</option>)}</select></label>)}</fieldset>
    </>}
    {type === 'reorder_sentence' && <fieldset><legend>Sentence items in correct order</legend>{items.map((item, index) => <div className="admin-option-row" key={item.id}>
      <label>Item {index + 1}<input value={item.text} onChange={(event) => setItems((rows) => rows.map((row) => row.id === item.id ? { ...row, text: event.target.value } : row))} /></label>
      <button type="button" aria-label={`Move ${item.text || `item ${index + 1}`} up`} disabled={index === 0} onClick={() => moveItem(index, -1)}>Move Up</button><button type="button" aria-label={`Move ${item.text || `item ${index + 1}`} down`} disabled={index === items.length - 1} onClick={() => moveItem(index, 1)}>Move Down</button><button type="button" onClick={() => setItems((rows) => rows.filter((row) => row.id !== item.id))}>Remove item</button>
    </div>)}<button type="button" onClick={() => addRow(setItems)}>Add sentence item</button><p>Correct order follows the current row order.</p></fieldset>}
    {['translate_vi_zh', 'translate_zh_vi', 'sentence_writing'].includes(type) && <>
      <label>Reference answer (optional)<textarea value={referenceAnswer} onChange={(event) => setReferenceAnswer(event.target.value)} /></label>
      <label>Rubric (optional)<textarea value={rubric} onChange={(event) => setRubric(event.target.value)} /></label>
    </>}
    {error && <p role="alert">{error}</p>}
    {apiError && <p role="alert">{adminErrorText(apiError, 'Could not save question.')}</p>}
    <button type="submit" disabled={pending}>{pending ? 'Saving question…' : 'Save question'}</button>
    <button type="button" disabled={pending} onClick={onClose}>Cancel</button>
  </form>
}

function QuestionRow({ question, assessmentId, editable }: { question: Question; assessmentId: string; editable: boolean }) {
  const client = useQueryClient()
  const [editing, setEditing] = useState(false)
  const remove = useMutation({ mutationFn: () => deleteAssessmentQuestion(assessmentId, question.id), retry: false,
    onSuccess: () => invalidateAssessmentQuestions(client, assessmentId),
    onError: async (error) => { if (error instanceof Error && 'status' in error && error.status === 409) await invalidateAssessmentQuestions(client, assessmentId) },
  })
  if (editing) return <QuestionForm assessmentId={assessmentId} question={question} onClose={() => setEditing(false)} />
  return <article className="admin-content-item">
    <h3>{question.order_index}. {question.prompt}</h3><p>{typeLabels[question.type]} · {question.points} points</p>
    {editable && <><button type="button" onClick={() => setEditing(true)}>Edit question</button>
      {remove.isError && <p role="alert">{adminErrorText(remove.error, 'Could not delete question.')}</p>}
      <button type="button" disabled={remove.isPending} onClick={() => { if (globalThis.confirm('Delete this question?')) remove.mutate() }}>{remove.isPending ? 'Deleting…' : 'Delete question'}</button></>}
  </article>
}

export function QuestionEditor({ assessmentId, questions, editable }: { assessmentId: string; questions: Question[]; editable: boolean }) {
  const [creating, setCreating] = useState(false)
  return <section className="learning-card" aria-label="Assessment questions">
    <h2>Questions</h2>
    {questions.length === 0 ? <p>No questions have been added.</p> : <div className="admin-content-list">{questions.map((question) => <QuestionRow key={question.id} question={question} assessmentId={assessmentId} editable={editable} />)}</div>}
    {editable && (creating ? <QuestionForm assessmentId={assessmentId} question={null} onClose={() => setCreating(false)} /> : <button type="button" onClick={() => setCreating(true)}>Add Question</button>)}
  </section>
}
