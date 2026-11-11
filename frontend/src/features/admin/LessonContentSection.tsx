import { useState, type FormEvent } from 'react'
import { VocabularyStudyCard } from '../lesson/VocabularyStudyCard'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { queryKeys } from '../../app/query/keys'
import { adminErrorText } from './AdminPrimitives'
import { attachGrammar, attachVocabulary, detachGrammar, detachVocabulary, listLessonGrammar, listLessonVocabulary, updateLessonGrammar, updateLessonVocabulary } from './api'
import { invalidateLessonContent } from './invalidation'
import { Button } from '../../components/ui/Button'
import { Dialog } from '../../components/ui/Dialog'
import { Alert } from '../../components/ui/Alert'
import { LoadingState } from '../../components/ui/PageState'
import { Surface } from '../../components/ui/Surface'
import { useAuthoringDirty } from './AuthoringSession'

type Kind = 'vocabulary' | 'grammar'
type ContentItem = Awaited<ReturnType<typeof listLessonVocabulary>>[number]
type ContentDraft = { hanzi: string; pinyin: string; meaning: string; pos: string; name: string; structure: string; explanation: string; usage: string; order: string; note: string; example: string }
function toDraft(item?: ContentItem): ContentDraft {
  return { hanzi: item?.hanzi ?? '', pinyin: item?.pinyin ?? '', meaning: item?.vietnamese_meaning ?? '', pos: item?.part_of_speech ?? '', name: item?.name ?? '', structure: item?.structure ?? '', explanation: item?.explanation ?? '', usage: item?.usage ?? '', order: String(item?.order_index ?? 1), note: item?.note ?? '', example: item?.example ?? '' }
}

function WordPreview({ draft, kind, dirty }: { draft: ContentDraft; kind: Kind; dirty: boolean }) {
  return <aside className="admin-editor-preview" aria-label="Xem trước nội dung bài học"><h3>Xem trước cho học sinh {dirty ? '· Chưa lưu' : ''}</h3>
    {kind === 'vocabulary' ? <VocabularyStudyCard word={{ hanzi: draft.hanzi || '汉字', pinyin: draft.pinyin || 'Phiên âm', vietnamese_meaning: draft.meaning || 'Nghĩa tiếng Việt', part_of_speech: draft.pos }} example={draft.example} note={draft.note}/> : <article className="admin-student-word">
      <h4 style={{ fontSize: 30 }}>{draft.name || 'Tên cấu trúc'}</h4>{draft.structure && <p lang="zh-Hans">{draft.structure}</p>}<p>{draft.explanation}</p>{draft.usage && <section><h5>Cách dùng</h5><p>{draft.usage}</p></section>}
      {draft.example && <section><h5>Ví dụ</h5><p>{draft.example}</p></section>}{draft.note && <section><h5>Lưu ý</h5><p>{draft.note}</p></section>}
    </article>}
  </aside>
}

function ContentItemEditor({ item, lessonId, hskId, kind, lessonStatus, onAttached }: {
  item?: ContentItem; lessonId: string; hskId: string; kind: Kind; lessonStatus: string; onAttached?: (id: string) => void
}) {
  const client = useQueryClient()
  const [draft, setDraft] = useState(() => toDraft(item))
  const [baseline, setBaseline] = useState(() => toDraft(item))
  const [mobilePane, setMobilePane] = useState<'edit' | 'preview'>('edit')
  const [detachOpen, setDetachOpen] = useState(false)
  const readonly = lessonStatus === 'ARCHIVED'
  const kindLabel = kind === 'vocabulary' ? 'từ vựng' : 'ngữ pháp'
  const dirty = JSON.stringify(draft) !== JSON.stringify(baseline)
  const set = (field: keyof ContentDraft, value: string) => setDraft((current) => ({ ...current, [field]: value }))
  const save = useMutation({
    mutationFn: () => {
      const association = { order_index: Number(draft.order), note: draft.note || null, example: draft.example || null }
      if (kind === 'vocabulary') {
        const body = { ...association, hanzi: draft.hanzi.trim(), pinyin: draft.pinyin.trim(), vietnamese_meaning: draft.meaning.trim(), part_of_speech: draft.pos.trim() || null }
        if (item) return updateLessonVocabulary(lessonId, item.id, body)
        const { note, example, part_of_speech, ...required } = body
        return attachVocabulary(lessonId, { ...required, ...(note ? { note } : {}), ...(example ? { example } : {}), ...(part_of_speech ? { part_of_speech } : {}) })
      }
      const body = { ...association, name: draft.name.trim(), structure: draft.structure || null, explanation: draft.explanation.trim(), usage: draft.usage || null }
      return item ? updateLessonGrammar(lessonId, item.id, body) : attachGrammar(lessonId, body)
    }, retry: false,
    onSuccess: async (result) => {
      const saved = toDraft(result)
      setDraft(saved); setBaseline(saved)
      await invalidateLessonContent(client, lessonId, hskId, kind)
      if (!item) onAttached?.(result.id)
    },
  })
  const remove = useMutation({
    mutationFn: () => kind === 'vocabulary' ? detachVocabulary(lessonId, item!.id) : detachGrammar(lessonId, item!.id), retry: false,
    onSuccess: () => invalidateLessonContent(client, lessonId, hskId, kind),
  })
  useAuthoringDirty(`${kind}-${item?.id ?? 'new'}`, !readonly && (dirty || save.isPending || remove.isPending))
  const valid = Number.isInteger(Number(draft.order)) && Number(draft.order) >= 1 && (kind === 'vocabulary' ? Boolean(draft.hanzi.trim() && draft.pinyin.trim() && draft.meaning.trim()) : Boolean(draft.name.trim() && draft.explanation.trim()))
  const submit = (event: FormEvent) => { event.preventDefault(); if (valid && !readonly && !save.isPending) save.mutate() }
  const input = (label: string, field: keyof ContentDraft, required = false, multiline = false) => <label>{label}{multiline ? <textarea name={field} required={required} value={draft[field]} onChange={(event) => set(field, event.target.value)}/> : <input name={field} required={required} lang={field === 'hanzi' ? 'zh-Hans' : undefined} type={field === 'order' ? 'number' : 'text'} min={field === 'order' ? '1' : undefined} value={draft[field]} onChange={(event) => set(field, event.target.value)}/>}</label>
  return <>
    <div className="admin-content-mobile-switch" role="group" aria-label="Chế độ biên soạn"><button type="button" aria-pressed={mobilePane === 'edit'} onClick={() => setMobilePane('edit')}>Biên soạn</button><button type="button" aria-pressed={mobilePane === 'preview'} onClick={() => setMobilePane('preview')}>Xem trước</button></div>
    <article className="admin-content-edit-preview" data-mobile-pane={mobilePane}>
      <form className="admin-edit-fields" onSubmit={submit}>
        <h4>{item ? "Chỉnh sửa nội dung" : `Thêm ${kindLabel} vào bài học`}</h4>
        <p>{item ? "Nội dung gốc được dùng chung. Thay đổi sẽ áp dụng ở mọi bài học sử dụng nội dung này." : "Tạo nội dung gốc mới và thêm vào bài học này."}</p>
        <fieldset disabled={readonly || save.isPending} className="admin-studio-fieldset">
          <legend>Nội dung gốc · {kindLabel}</legend>
          {kind === 'vocabulary' ? <>{input("Chữ Hán", 'hanzi', true)}{input("Phiên âm", 'pinyin', true)}{input("Nghĩa tiếng Việt", 'meaning', true)}{input("Loại từ", 'pos')}</> : <>{input("Tên", 'name', true)}{input("Cấu trúc", 'structure')}{input("Giải thích", 'explanation', true, true)}{input("Cách dùng", 'usage', false, true)}</>}
          <h5>Thông tin trong bài học này</h5>{input("Thứ tự", 'order', true)}{input("Lưu ý", 'note', false, true)}{input("Ví dụ", 'example', false, true)}
        </fieldset>
        {save.isError && <Alert role="alert" tone="error">{adminErrorText(save.error, `Không thể lưu ${kindLabel}.`)}</Alert>}
        <div className="admin-item-save-bar"><span role="status">{dirty ? 'Chưa lưu thay đổi' : save.isSuccess ? 'Đã lưu nội dung.' : readonly ? 'Chỉ đọc' : 'Nội dung đã tải từ hệ thống'}</span>
          {!readonly && <Button type="submit" variant="primary" disabled={save.isPending || !valid || (Boolean(item) && !dirty)}>{save.isPending ? "Đang lưu…" : item ? "Lưu nội dung" : `Tạo và thêm ${kindLabel}`}</Button>}
        </div>
        {item && lessonStatus === 'DRAFT' && <><Button variant="danger" disabled={remove.isPending || save.isPending} onClick={() => setDetachOpen(true)}>{remove.isPending ? "Đang gỡ…" : `Gỡ ${kindLabel}`}</Button>{remove.isError && <Alert role="alert" tone="error">{adminErrorText(remove.error, "Không thể gỡ nội dung này.")}</Alert>}</>}
      </form>
      <WordPreview draft={draft} kind={kind} dirty={dirty}/>
    </article>
    <Dialog cancelLabel="Hủy" open={detachOpen} title={`Gỡ ${kindLabel} khỏi bài học?`} confirmLabel={`Gỡ ${kindLabel}`} confirmVariant="danger" busy={remove.isPending} onCancel={() => setDetachOpen(false)} onClose={() => setDetachOpen(false)} onConfirm={() => { remove.mutate(); setDetachOpen(false) }}>Chỉ gỡ nội dung khỏi bài học này. Nội dung gốc dùng chung vẫn được giữ lại. {dirty && "Các thay đổi chưa lưu của mục này sẽ bị mất."}</Dialog>
  </>
}

export function LessonContentSection({ lessonId, hskId, kind, lessonStatus }: {
  lessonId: string; hskId: string; kind: Kind; lessonStatus: string
}) {
  const [selectedId, setSelectedId] = useState('')
  const [created, setCreated] = useState(false)
  const [newKey, setNewKey] = useState(0)
  const kindLabel = kind === 'vocabulary' ? 'từ vựng' : 'ngữ pháp'
  const queryKey = kind === 'vocabulary' ? queryKeys.adminLessonVocabulary(lessonId) : queryKeys.adminLessonGrammar(lessonId)
  const query = useQuery({ queryKey, queryFn: kind === 'vocabulary' ? () => listLessonVocabulary(lessonId) : () => listLessonGrammar(lessonId) })
  if (query.isPending && !query.data) return <LoadingState>Đang tải {kindLabel}…</LoadingState>
  if (query.isError && !query.data) return <Surface><Alert role="alert" tone="error">{adminErrorText(query.error, `Không thể tải ${kindLabel}.`)}</Alert><button type="button" onClick={() => void query.refetch()}>Thử lại</button></Surface>
  const items = query.data ?? []
  const selected = selectedId === 'new' ? 'new' : items.find((item) => item.id === selectedId)?.id ?? items[0]?.id
  return <section className="admin-content-workshop" aria-label={`Bài học · ${kindLabel}`}>
    <nav className="admin-content-outline" aria-label={`Danh sách ${kindLabel}`}><h3>{kind === 'vocabulary' ? "Từ vựng" : "Ngữ pháp"} · {items.length}</h3>
      <ol>{items.map((item) => <li key={item.id}><button type="button" aria-pressed={selected === item.id} onClick={() => setSelectedId(item.id)}><span>{String(item.order_index).padStart(2, '0')}</span><span lang={kind === 'vocabulary' ? 'zh-Hans' : undefined}>{kind === 'vocabulary' ? item.hanzi : item.name}</span></button></li>)}</ol>
      {lessonStatus !== 'ARCHIVED' && <Button onClick={() => { setCreated(true); setSelectedId('new') }}>{kind === 'vocabulary' ? 'Thêm từ vựng' : 'Thêm ngữ pháp'}</Button>}
    </nav>
    <div className="admin-content-stage">
      {query.isError && <Alert tone="warning">Chưa cập nhật được {kindLabel}. Đang hiển thị nội dung đã tải.</Alert>}
      {!items.length && selected !== 'new' && <Surface><h3>{kind === 'vocabulary' ? "Từ vựng" : "Ngữ pháp"}</h3><p>Bài học này chưa có {kindLabel}.</p></Surface>}
      {items.map((item) => <div key={item.id} hidden={selected !== item.id}><ContentItemEditor item={item} lessonId={lessonId} hskId={hskId} kind={kind} lessonStatus={lessonStatus}/></div>)}
      {created && lessonStatus !== 'ARCHIVED' && <div hidden={selected !== 'new'}><ContentItemEditor key={newKey} lessonId={lessonId} hskId={hskId} kind={kind} lessonStatus={lessonStatus} onAttached={(id) => { setSelectedId(id); setCreated(false); setNewKey((key) => key + 1) }}/></div>}
      {query.isFetching && <LoadingState>Đang cập nhật {kindLabel}…</LoadingState>}
    </div>
  </section>
}
