import { useEffect, useState, type FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { adminErrorText } from './AdminPrimitives'
import { createAssessmentQuestion, deleteAssessmentQuestion, listAssessmentQuestions, updateAssessmentQuestion } from './api'
import { invalidateAssessmentQuestions } from './invalidation'
import { Button } from '../../components/ui/Button'
import { Dialog } from '../../components/ui/Dialog'
import { useAuthoringDirty } from './AuthoringSession'
import { QuestionRenderer, type AssessmentQuestion, type DraftAnswer } from '../assessment/QuestionRenderer'

type Question = Awaited<ReturnType<typeof listAssessmentQuestions>>[number]
type QuestionCreate = Parameters<typeof createAssessmentQuestion>[1]
type QuestionPatch = Parameters<typeof updateAssessmentQuestion>[2]
type QuestionType = QuestionCreate['type']
type MatchRow = { id: string; text: string }
type OptionRow = { text: string; correct: boolean }

function previewQuestion(id: string, type: QuestionType, prompt: string, order: string, points: string, options: OptionRow[], left: MatchRow[], right: MatchRow[], items: MatchRow[]): AssessmentQuestion {
  const base = { id: `admin-preview-${id}`, prompt: prompt || 'Nội dung câu hỏi', order_index: Number(order), points: Number(points) }
  if (type === 'multiple_choice') return { ...base, type, config: {}, options: options.map((item, index) => ({ id: `${id}-option-${index}`, option_text: item.text || `Lựa chọn ${index + 1}` })) }
  if (type === 'matching') return { ...base, type, config: { left_items: left, right_items: right } }
  if (type === 'reorder_sentence') return { ...base, type, config: { items } }
  return { ...base, type, config: {} }
}

function QuestionPreview({ question, dirty = false }: { question: AssessmentQuestion; dirty?: boolean }) {
  const [answer, setAnswer] = useState<DraftAnswer>()
  return <aside className="admin-editor-preview"><h3>Xem trước cho học sinh {dirty ? '· Chưa lưu' : ''}</h3><div className="admin-question-preview"><p>{question.points || '—'} điểm · Thử tương tác</p><QuestionRenderer language="vi" question={question} draft={answer} onChange={setAnswer}/><p className="admin-preview-hint">Thao tác tại đây không lưu kết quả học tập.</p></div></aside>
}

const types: QuestionType[] = ['multiple_choice', 'fill_blank', 'matching', 'reorder_sentence', 'translate_vi_zh', 'translate_zh_vi', 'sentence_writing']
const typeLabels: Record<QuestionType, string> = {
  multiple_choice: "Chọn đáp án", fill_blank: "Điền vào chỗ trống", matching: "Nối cặp", reorder_sentence: "Sắp xếp câu",
  translate_vi_zh: "Dịch Việt → Trung", translate_zh_vi: "Dịch Trung → Việt", sentence_writing: "Viết câu",
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

function QuestionForm({ assessmentId, question, onClose, onPendingChange, removing = false }: { assessmentId: string; question: Question | null; onClose: () => void; onPendingChange?: (pending: boolean) => void; removing?: boolean }) {
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
  const [mobilePane, setMobilePane] = useState<'edit' | 'preview'>('edit')
  const [cancelOpen, setCancelOpen] = useState(false)
  const snapshot = JSON.stringify({ type, prompt, order, points, referenceAnswer, rubric, acceptedAnswers, options, left, right, items, pairs })
  const [baseline] = useState(snapshot)
  const dirty = snapshot !== baseline

  const create = useMutation({ mutationFn: (body: QuestionCreate) => createAssessmentQuestion(assessmentId, body), retry: false,
    onSuccess: async () => { await invalidateAssessmentQuestions(client, assessmentId); onClose() },
  })
  const update = useMutation({ mutationFn: (body: QuestionPatch) => updateAssessmentQuestion(assessmentId, question!.id, body), retry: false,
    onSuccess: async () => { await invalidateAssessmentQuestions(client, assessmentId); onClose() },
  })

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (pending || removing) return
    setError('')
    const order_index = Number(order)
    const numericPoints = Number(points)
    if (!prompt.trim() || !Number.isInteger(order_index) || order_index < 1 || !Number.isFinite(numericPoints) || numericPoints <= 0) {
      setError("Nhập nội dung câu hỏi, thứ tự và số điểm lớn hơn 0.")
      return
    }
    let payload: QuestionCreate
    if (type === 'multiple_choice') {
      const validOptions = options.filter((item) => item.text.trim())
      if (validOptions.length < 2 || validOptions.filter((item) => item.correct).length !== 1) { setError("Thêm ít nhất hai lựa chọn và đánh dấu đúng một đáp án đúng."); return }
      payload = { type, prompt: prompt.trim(), order_index, points: numericPoints, options: validOptions.map((item) => ({ option_text: item.text.trim(), is_correct: item.correct })) }
    } else if (type === 'fill_blank') {
      if (!referenceAnswer.trim()) { setError("Nhập đáp án tham khảo."); return }
      payload = { type, prompt: prompt.trim(), order_index, points: numericPoints, reference_answer: referenceAnswer.trim(), config: { accepted_answers: acceptedAnswers.split('\n').map((value) => value.trim()).filter(Boolean) } }
    } else if (type === 'matching') {
      const leftItems = left.filter((item) => item.text.trim())
      const rightItems = right.filter((item) => item.text.trim())
      if (!leftItems.length || !rightItems.length || leftItems.some((item) => !pairs[item.id] || !rightItems.some((rightItem) => rightItem.id === pairs[item.id]))) { setError("Thêm nội dung ở cả hai cột và chọn đáp án ghép cho từng mục bên trái."); return }
      payload = { type, prompt: prompt.trim(), order_index, points: numericPoints, config: { left_items: leftItems.map((item) => ({ ...item, text: item.text.trim() })), right_items: rightItems.map((item) => ({ ...item, text: item.text.trim() })), correct_pairs: leftItems.map((item) => ({ left_id: item.id, right_id: pairs[item.id] })) } }
    } else if (type === 'reorder_sentence') {
      const ordered = items.filter((item) => item.text.trim())
      if (!ordered.length) { setError("Thêm ít nhất một mảnh câu."); return }
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
  useAuthoringDirty(`question-${question?.id ?? 'new'}`, dirty || pending || removing)
  useEffect(() => { onPendingChange?.(pending); return () => onPendingChange?.(false) }, [onPendingChange, pending])
  const apiError = create.error ?? update.error
  const addRow = (setter: (fn: (rows: MatchRow[]) => MatchRow[]) => void) => setter((rows) => [...rows, { id: opaqueId(), text: '' }])
  const moveItem = (index: number, offset: number) => setItems((rows) => { const target = index + offset; if (target < 0 || target >= rows.length) return rows; const next = [...rows]; [next[index], next[target]] = [next[target], next[index]]; return next })

  const preview = previewQuestion(question?.id ?? 'new', type, prompt, order, points, options, left, right, items)
  return <><div className="admin-content-mobile-switch" role="group" aria-label="Chế độ biên soạn"><button type="button" aria-pressed={mobilePane === 'edit'} onClick={() => setMobilePane('edit')}>Biên soạn</button><button type="button" aria-pressed={mobilePane === 'preview'} onClick={() => setMobilePane('preview')}>Xem trước</button></div>
    <div className="admin-content-edit-preview" data-mobile-pane={mobilePane}><div className="admin-question-edit-pane"><form className="learning-card admin-question-form admin-assessment-question-form" onSubmit={submit}>
    <fieldset className="admin-studio-fieldset" disabled={pending || removing}>
    <h3 className="admin-assessment-form-title">{question ? "Chỉnh sửa câu hỏi" : "Tạo câu hỏi"}</h3>
    <div className="admin-assessment-question-basics">
      <label className="admin-assessment-question-type-field">Dạng câu hỏi{question
        ? <input readOnly value={typeLabels[question.type]} />
        : <select value={type} onChange={(event) => setType(event.target.value as QuestionType)}>{types.map((value) => <option key={value} value={value}>{typeLabels[value]}</option>)}</select>}
      </label>
      <label className="admin-assessment-question-prompt-field">Nội dung câu hỏi<textarea required value={prompt} onChange={(event) => setPrompt(event.target.value)} /></label>
      <label className="admin-assessment-question-order-field">Thứ tự<input required type="number" min="1" value={order} onChange={(event) => setOrder(event.target.value)} /></label>
      <label className="admin-assessment-question-points-field">Số điểm<input required type="number" min="0.01" step="any" value={points} onChange={(event) => setPoints(event.target.value)} /></label>
    </div>
    {type === 'multiple_choice' && <fieldset><legend>Các lựa chọn</legend>{options.map((option, index) => <div className="admin-option-row" key={index}>
      <label>Lựa chọn {index + 1}<input value={option.text} onChange={(event) => setOptions((rows) => rows.map((row, rowIndex) => rowIndex === index ? { ...row, text: event.target.value } : row))} /></label>
      <label><input type="radio" name={`correct-option-${question?.id ?? 'new'}`} checked={option.correct} onChange={() => setOptions((rows) => rows.map((row, rowIndex) => ({ ...row, correct: rowIndex === index })))} /> Đáp án đúng</label>
      <button type="button" disabled={options.length <= 2} onClick={() => setOptions((rows) => rows.filter((_, rowIndex) => rowIndex !== index))}>Xóa lựa chọn</button>
    </div>)}<button type="button" onClick={() => setOptions((rows) => [...rows, { text: '', correct: false }])}>Thêm lựa chọn</button></fieldset>}
    {type === 'fill_blank' && <>
      <label>Đáp án tham khảo<input required value={referenceAnswer} onChange={(event) => setReferenceAnswer(event.target.value)} /></label>
      <label>Đáp án được chấp nhận (mỗi dòng một đáp án)<textarea value={acceptedAnswers} onChange={(event) => setAcceptedAnswers(event.target.value)} /></label>
    </>}
    {type === 'matching' && <>
      <fieldset><legend>Cột bên trái</legend>{left.map((item, index) => <div key={item.id} className="admin-option-row"><label>Mục bên trái {index + 1}<input value={item.text} onChange={(event) => setLeft((rows) => rows.map((row) => row.id === item.id ? { ...row, text: event.target.value } : row))} /></label><button type="button" onClick={() => setLeft((rows) => rows.filter((row) => row.id !== item.id))}>Xóa mục bên trái</button></div>)}<button type="button" onClick={() => addRow(setLeft)}>Thêm mục bên trái</button></fieldset>
      <fieldset><legend>Cột bên phải</legend>{right.map((item, index) => <div key={item.id} className="admin-option-row"><label>Mục bên phải {index + 1}<input value={item.text} onChange={(event) => setRight((rows) => [...rows.slice(0, index), { ...rows[index], text: event.target.value }, ...rows.slice(index + 1)])} /></label><button type="button" onClick={() => setRight((rows) => rows.filter((row) => row.id !== item.id))}>Xóa mục bên phải</button></div>)}<button type="button" onClick={() => addRow(setRight)}>Thêm mục bên phải</button></fieldset>
      <fieldset><legend>Các cặp đúng</legend>{left.map((item, index) => <label key={item.id}>Ghép cho {item.text || `mục bên trái ${index + 1}`}<select value={pairs[item.id] ?? ''} onChange={(event) => setPairs((current) => ({ ...current, [item.id]: event.target.value }))}><option value="">Chọn mục bên phải</option>{right.map((candidate, rightIndex) => <option key={candidate.id} value={candidate.id}>{candidate.text || `Mục bên phải ${rightIndex + 1}`}</option>)}</select></label>)}</fieldset>
    </>}
    {type === 'reorder_sentence' && <fieldset><legend>Các mảnh câu theo thứ tự đúng</legend>{items.map((item, index) => <div className="admin-option-row" key={item.id}>
      <label>Mảnh câu {index + 1}<input value={item.text} onChange={(event) => setItems((rows) => rows.map((row) => row.id === item.id ? { ...row, text: event.target.value } : row))} /></label>
      <button type="button" aria-label={`Đưa ${item.text || `mảnh câu ${index + 1}`} lên`} disabled={index === 0} onClick={() => moveItem(index, -1)}>Đưa lên</button><button type="button" aria-label={`Đưa ${item.text || `mảnh câu ${index + 1}`} xuống`} disabled={index === items.length - 1} onClick={() => moveItem(index, 1)}>Đưa xuống</button><button type="button" onClick={() => setItems((rows) => rows.filter((row) => row.id !== item.id))}>Xóa mảnh câu</button>
    </div>)}<button type="button" onClick={() => addRow(setItems)}>Thêm mảnh câu</button><p>Đáp án đúng theo thứ tự các mảnh câu đang hiển thị.</p></fieldset>}
    {['translate_vi_zh', 'translate_zh_vi', 'sentence_writing'].includes(type) && <>
      <label>Đáp án tham khảo (không bắt buộc)<textarea value={referenceAnswer} onChange={(event) => setReferenceAnswer(event.target.value)} /></label>
      <label>Tiêu chí chấm (không bắt buộc)<textarea value={rubric} onChange={(event) => setRubric(event.target.value)} /></label>
    </>}
    {error && <p role="alert">{error}</p>}
    {apiError && <p role="alert">{adminErrorText(apiError, "Không thể lưu câu hỏi.")}</p>}
    <div className="admin-item-save-bar"><span role="status">{dirty ? 'Chưa lưu thay đổi' : 'Nội dung đã tải từ hệ thống'}</span><button type="submit" disabled={pending || removing}>{pending ? "Đang lưu câu hỏi…" : "Lưu câu hỏi"}</button>
    <button type="button" disabled={pending || removing} onClick={() => dirty ? setCancelOpen(true) : onClose()}>Hủy</button></div>
    </fieldset></form></div><QuestionPreview key={JSON.stringify(preview)} question={preview} dirty={dirty}/></div>
    <Dialog cancelLabel="Hủy" open={cancelOpen} title="Bỏ thay đổi của câu hỏi?" confirmLabel="Bỏ thay đổi" confirmVariant="danger" onConfirm={onClose} onCancel={() => setCancelOpen(false)} onClose={() => setCancelOpen(false)}>Nội dung chưa lưu của câu hỏi này sẽ bị mất.</Dialog>
  </>
}

function QuestionRow({ question, assessmentId, editable }: { question: Question; assessmentId: string; editable: boolean }) {
  const client = useQueryClient()
  const [editing, setEditing] = useState(editable)
  const [saving, setSaving] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const remove = useMutation({ mutationFn: () => deleteAssessmentQuestion(assessmentId, question.id), retry: false,
    onSuccess: () => invalidateAssessmentQuestions(client, assessmentId),
    onError: async (error) => { if (error instanceof Error && 'status' in error && error.status === 409) await invalidateAssessmentQuestions(client, assessmentId) },
  })
  const preview = previewQuestion(question.id, question.type, question.prompt, String(question.order_index), String(question.points), question.options.map((option) => ({ text: option.option_text, correct: option.is_correct })), configRows(question, 'left_items'), configRows(question, 'right_items'), configRows(question, 'items'))
  return <article className="admin-assessment-question-row">
    {editing && editable ? <QuestionForm assessmentId={assessmentId} question={question} onClose={() => setEditing(false)} onPendingChange={setSaving} removing={remove.isPending} /> : <>
    <h3 className="admin-assessment-question-prompt">{question.order_index}. {question.prompt}</h3><p className="admin-assessment-question-meta">{typeLabels[question.type]} · {question.points} điểm</p>
    <QuestionPreview key={JSON.stringify(preview)} question={preview}/>
    {editable && <button type="button" onClick={() => setEditing(true)}>Chỉnh sửa câu hỏi</button>}</>}
    {editable && <>
      {remove.isError && <p role="alert">{adminErrorText(remove.error, "Không thể xóa câu hỏi.")}</p>}
      <Button variant="danger" disabled={remove.isPending || saving} onClick={() => setDeleteOpen(true)}>{remove.isPending ? "Đang xóa…" : "Xóa câu hỏi"}</Button>
      <Dialog cancelLabel="Hủy" open={deleteOpen} title="Xóa câu hỏi?" confirmLabel="Xóa câu hỏi" confirmVariant="danger" busy={remove.isPending}
        onCancel={() => setDeleteOpen(false)} onClose={() => setDeleteOpen(false)}
        onConfirm={() => { if (!saving && !remove.isPending) remove.mutate(); setDeleteOpen(false) }}>
        Câu hỏi sẽ bị xóa khỏi bài luyện tập. Hệ thống sẽ ngăn xóa nếu đã có lịch sử làm bài.
      </Dialog></>}
  </article>
}

export function QuestionEditor({ assessmentId, questions, editable }: { assessmentId: string; questions: Question[]; editable: boolean }) {
  const [creating, setCreating] = useState(false)
  const [selectedId, setSelectedId] = useState('')
  const selected = selectedId === 'new' && creating ? 'new' : questions.find((question) => question.id === selectedId)?.id ?? questions[0]?.id
  return <section className="admin-editor-section admin-assessment-questions admin-question-workshop" aria-label="Câu hỏi của bài luyện tập">
    <div className="admin-assessment-questions-heading"><h2 className="admin-assessment-section-title">Câu hỏi</h2><span className="admin-assessment-question-count">{questions.length} câu hỏi</span></div>
    <div className="admin-content-workshop"><nav className="admin-content-outline" aria-label="Danh sách câu hỏi"><h3>Nội dung bài luyện</h3><ol>{questions.map((question) => <li key={question.id}><button type="button" aria-pressed={selected === question.id} onClick={() => setSelectedId(question.id)}><span>{String(question.order_index).padStart(2, '0')}</span><span>{question.prompt}</span></button></li>)}</ol>
      {editable && <button type="button" onClick={() => { setCreating(true); setSelectedId('new') }}>Thêm câu hỏi</button>}</nav>
      <div className="admin-content-stage">{questions.length === 0 && !creating && <p className="admin-assessment-questions-empty">Chưa có câu hỏi nào.</p>}
        {questions.map((question) => <div key={question.id} hidden={selected !== question.id}><QuestionRow question={question} assessmentId={assessmentId} editable={editable}/></div>)}
        {editable && creating && <div hidden={selected !== 'new'}><QuestionForm assessmentId={assessmentId} question={null} onClose={() => { setCreating(false); setSelectedId('') }}/></div>}
      </div>
    </div>
  </section>
}
