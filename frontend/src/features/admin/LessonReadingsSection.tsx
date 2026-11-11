import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Button, Dialog, LoadingState, Surface } from '../../components/ui'
import { queryKeys } from '../../app/query/keys'
import { ReadingText, type LessonReading } from '../lesson/ReadingText'
import { useAuthoringDirty } from './AuthoringSession'
import { adminErrorText } from './AdminPrimitives'
import { createLessonReading, deleteLessonReading, listLessonReadings, updateLessonReading, type ReadingInput } from './readingApi'

function ReadingEditor({ reading, lessonId, nextOrder, lessonStatus, onSaved, onDeleted }: { reading?: LessonReading; lessonId: string; nextOrder: number; lessonStatus: string; onSaved: (id: string) => void; onDeleted: () => void }) {
  const client = useQueryClient()
  const initial: ReadingInput = { order_index: reading?.order_index ?? nextOrder, title: reading?.title ?? '', content: reading?.content ?? '', pinyin: reading?.pinyin ?? null, vietnamese_translation: reading?.vietnamese_translation ?? null, source_reference: reading?.source_reference ?? null }
  const [draft, setDraft] = useState(initial)
  const [baseline, setBaseline] = useState(initial)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const readonly = lessonStatus === 'ARCHIVED'
  const dirty = JSON.stringify(draft) !== JSON.stringify(baseline)
  useAuthoringDirty('reading-' + (reading?.id ?? 'new'), dirty && !readonly)
  const invalidate = () => Promise.all([queryKeys.adminLessonReadings(lessonId), queryKeys.lesson(lessonId), queryKeys.lessonProgress(lessonId), queryKeys.dashboard].map(queryKey => client.invalidateQueries({ queryKey })))
  const save = useMutation({
    mutationFn: () => reading ? updateLessonReading(lessonId, reading.id, draft) : createLessonReading(lessonId, draft),
    retry: false,
    onSuccess: async result => {
      const stored: ReadingInput = { order_index: result.order_index, title: result.title, content: result.content, pinyin: result.pinyin, vietnamese_translation: result.vietnamese_translation, source_reference: result.source_reference }
      setDraft(stored); setBaseline(stored)
      await invalidate(); onSaved(result.id)
    },
  })
  const remove = useMutation({ mutationFn: () => deleteLessonReading(lessonId, reading!.id), retry: false, onSuccess: async () => { await invalidate(); onDeleted() } })
  const setText = (field: 'title' | 'content' | 'pinyin' | 'vietnamese_translation' | 'source_reference', value: string) => setDraft(current => ({ ...current, [field]: value || (field === 'title' || field === 'content' ? '' : null) }))
  const valid = Number.isInteger(draft.order_index) && draft.order_index >= 1 && draft.title.trim() && draft.content.trim()
  const submit = (event: FormEvent) => { event.preventDefault(); if (valid && !readonly && !save.isPending) save.mutate() }
  return <>
    <div className="admin-reading-editor">
      <form className="admin-edit-fields" onSubmit={submit}>
        <h3>{reading ? 'Biên soạn bài khóa' : 'Thêm bài khóa'}</h3>
        <p>Nhập nội dung đọc theo giáo trình. Học viên cần xác nhận hoàn thành từng bài khóa để mở luyện tập.</p>
        <fieldset className="admin-studio-fieldset" disabled={readonly || save.isPending || remove.isPending}>
          <legend>Nội dung bài khóa</legend>
          <label>Tiêu đề bài khóa<input value={draft.title} required maxLength={30000} onChange={event => setText('title', event.target.value)}/></label>
          <label>Thứ tự bài khóa<input type="number" min="1" step="1" required value={Number.isNaN(draft.order_index) ? '' : draft.order_index} onChange={event => setDraft(current => ({ ...current, order_index: event.target.valueAsNumber }))}/></label>
          <label>Nội dung tiếng Trung<textarea value={draft.content} lang="zh-Hans" required maxLength={30000} onChange={event => setText('content', event.target.value)}/></label>
          <label>Phiên âm (không bắt buộc)<textarea value={draft.pinyin ?? ''} maxLength={30000} onChange={event => setText('pinyin', event.target.value)}/></label>
          <label>Nghĩa tiếng Việt (không bắt buộc)<textarea value={draft.vietnamese_translation ?? ''} maxLength={30000} onChange={event => setText('vietnamese_translation', event.target.value)}/></label>
        </fieldset>
        {save.isError && <Alert role="alert" tone="error">{adminErrorText(save.error, 'Không thể lưu bài khóa. Vui lòng thử lại.')}</Alert>}
        {remove.isError && <Alert role="alert" tone="error">{adminErrorText(remove.error, 'Không thể xóa bài khóa này.')}</Alert>}
        <div className="admin-item-save-bar"><span role="status">{dirty ? 'Chưa lưu thay đổi' : save.isSuccess ? 'Đã lưu bài khóa.' : readonly ? 'Chỉ đọc' : 'Nội dung đã tải từ hệ thống'}</span>
          {!readonly && <Button type="submit" variant="primary" disabled={!valid || save.isPending || remove.isPending || (Boolean(reading) && !dirty)}>{save.isPending ? 'Đang lưu…' : 'Lưu bài khóa'}</Button>}
        </div>
        {reading && lessonStatus === 'DRAFT' && <Button variant="danger" disabled={save.isPending || remove.isPending} onClick={() => setConfirmDelete(true)}>Xóa bài khóa</Button>}
        {lessonStatus === 'PUBLISHED' && <p>Nội dung đã sửa sẽ cần được học viên đọc và xác nhận hoàn thành lại.</p>}
      </form>
      <aside className="admin-reading-preview" aria-label="Xem trước bài khóa"><h3>{draft.title || 'Bài khóa chưa có tiêu đề'}</h3><ReadingText reading={{ content: draft.content || 'Nội dung tiếng Trung sẽ xuất hiện tại đây.', pinyin: draft.pinyin ?? null, vietnamese_translation: draft.vietnamese_translation ?? null, source_reference: draft.source_reference ?? null }}/></aside>
    </div>
    <Dialog open={confirmDelete} title="Xóa bài khóa này?" confirmLabel="Xóa bài khóa" confirmVariant="danger" cancelLabel="Hủy" busy={remove.isPending} onCancel={() => setConfirmDelete(false)} onConfirm={() => { setConfirmDelete(false); remove.mutate() }}>Bài khóa sẽ được gỡ khỏi bài học này. Bài khóa có lịch sử hoàn thành của học viên được giữ lại.</Dialog>
  </>
}

export function LessonReadingsSection({ lessonId, lessonStatus, active }: { lessonId: string; lessonStatus: string; active: boolean }) {
  const [selectedId, setSelectedId] = useState('')
  const [adding, setAdding] = useState(false)
  const [newDraftCreated, setNewDraftCreated] = useState(false)
  const query = useQuery({ queryKey: queryKeys.adminLessonReadings(lessonId), queryFn: () => listLessonReadings(lessonId), enabled: active })
  if (!active && !query.data) return null
  if (query.isPending && !query.data) return <LoadingState>Đang tải bài khóa…</LoadingState>
  if (query.isError && !query.data) return <Alert role="alert" tone="error" action={<Button onClick={() => void query.refetch()}>Thử lại</Button>}>{adminErrorText(query.error, 'Không thể tải bài khóa.')}</Alert>
  const items = query.data ?? []
  const selected = adding ? 'new' : items.find(item => item.id === selectedId)?.id ?? items[0]?.id
  const nextOrder = Math.max(0, ...items.map(item => item.order_index)) + 1
  return <section className="admin-content-workshop" aria-label="Bài học · bài khóa">
    <nav className="admin-content-outline" aria-label="Danh sách bài khóa"><h3>Bài khóa · {items.length}</h3><ol>{items.map(item => <li key={item.id}><button type="button" aria-pressed={selected === item.id} onClick={() => { setAdding(false); setSelectedId(item.id) }}>{item.order_index}. {item.title}</button></li>)}</ol>
      {lessonStatus !== 'ARCHIVED' && <Button onClick={() => { setNewDraftCreated(true); setAdding(true) }}>Thêm bài khóa</Button>}
    </nav>
    <div className="admin-content-stage">
      {query.isError && <Alert tone="warning">Chưa cập nhật được danh sách bài khóa. Đang hiển thị nội dung đã tải.</Alert>}
      {!items.length && !adding && <Surface><h3>Chưa có bài khóa</h3><p>Thêm bài khóa từ giáo trình để học viên đọc và xác nhận hoàn thành.</p></Surface>}
      {items.map(item => <div key={item.id} hidden={selected !== item.id}><ReadingEditor reading={item} lessonId={lessonId} nextOrder={nextOrder} lessonStatus={lessonStatus} onSaved={setSelectedId} onDeleted={() => setSelectedId('')}/></div>)}
      {newDraftCreated && <div hidden={!adding}><ReadingEditor lessonId={lessonId} nextOrder={nextOrder} lessonStatus={lessonStatus} onSaved={id => { setAdding(false); setNewDraftCreated(false); setSelectedId(id) }} onDeleted={() => setAdding(false)}/></div>}
    </div>
  </section>
}
