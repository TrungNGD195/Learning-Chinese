import { SceneIllustration, sceneForTitle } from '../../components/academy/AcademyArtwork'
import { AcademyIcon } from '../../components/academy/AcademyIcon'
import { useId, useState, type ReactNode } from 'react'
import { Link } from 'react-router'
import { Companion, VocabularyIllustration } from '../../components/academy/Companion'
import { useQuery } from '@tanstack/react-query'
import { queryKeys } from '../../app/query/keys'
import { listLessonVocabulary, listLessonGrammar } from './api'

export type LibraryRecord = {
  id: string; title: string; context: string; status: ReactNode; detail?: ReactNode
  href: string; action: string
}

export function AdminLibrary({ records, label, total, kind, preview }: {
  records: LibraryRecord[]; label: string; total: number; kind: 'lessons' | 'assessments' | 'documents'
  preview?: (id: string) => ReactNode
}) {
  const [view, setView] = useState<'cards' | 'table'>('cards')
  const [selectedId, setSelectedId] = useState('')
  const selected = records.find((item) => item.id === selectedId) ?? records[0]
  const previewId = useId()
  return <div className={`admin-library admin-library--${kind}`}>
    <div className="admin-library-toolbar">
      <p><strong>{total}</strong> {label} <span>· {records.length} trên trang này</span></p>
      <div className="admin-view-switch" role="group" aria-label="Cách hiển thị">
        <button type="button" aria-pressed={view === 'cards'} onClick={() => setView('cards')}>Thẻ</button>
        <button type="button" aria-pressed={view === 'table'} onClick={() => setView('table')}>Bảng</button>
      </div>
    </div>
    <div className="admin-library-layout">
      <div className="admin-library-results">
        {view === 'cards' ? <div className="admin-library-grid">{records.map((item, index) => {
          const content = <>
            <div className={`admin-book-cover admin-book-cover--${index % 3}`} aria-hidden="true"><SceneIllustration scene={kind === 'lessons' ? sceneForTitle(item.title) : kind === 'assessments' ? 'practice' : 'library'}/></div>
            <div className="admin-library-card-copy"><p className="admin-record-context">{item.context}</p><h2>{kind === 'lessons' ? item.title : <button type="button" aria-pressed={selected?.id === item.id} aria-controls={previewId} onClick={() => setSelectedId(item.id)}>{item.title}</button>}</h2>
              <div className="admin-record-status">{item.status}</div>{item.detail && <div className="admin-record-detail">{item.detail}</div>}
              {kind !== 'lessons' && <Link className="admin-link-action" to={item.href}>{item.action}<span aria-hidden="true"> →</span></Link>}
              {kind === 'lessons' && <span className="admin-library-card-action" aria-hidden="true">Biên soạn bài học<AcademyIcon name="arrow" size={18}/></span>}
            </div>
          </>
          const className = `admin-library-card ${selected?.id === item.id ? 'is-selected' : ''}`
          return kind === 'lessons'
            ? <Link key={item.id} className={`${className} admin-library-card--link`} to={item.href} aria-label={`Biên soạn bài học: ${item.title}`} onMouseEnter={() => setSelectedId(item.id)} onFocus={() => setSelectedId(item.id)}>{content}</Link>
            : <article key={item.id} className={className}>{content}</article>
        })}</div> : <div className="admin-library-table" role="region" aria-label={`Bảng ${label}`} tabIndex={0}><table><thead><tr><th scope="col">Nội dung</th><th scope="col">Trạng thái</th>{kind !== 'lessons' && <th scope="col">Thao tác</th>}</tr></thead><tbody>{records.map((item) => <tr key={item.id} className={selected?.id === item.id ? 'is-selected' : ''}><td>{kind === 'lessons' ? <Link to={item.href}>{item.title}</Link> : <button type="button" aria-pressed={selected?.id === item.id} aria-controls={previewId} onClick={() => setSelectedId(item.id)}>{item.title}</button>}<p>{item.context}</p>{item.detail}</td><td>{item.status}</td>{kind !== 'lessons' && <td><Link to={item.href}>{item.action}</Link></td>}</tr>)}</tbody></table></div>}
      </div>
      {selected && <aside className="admin-quick-preview" id={previewId} aria-label="Xem nhanh nội dung">
        <div className="admin-preview-heading"><h2>Xem nhanh</h2><Companion pose={kind === 'documents' ? 'truc' : 'but'} className="admin-library-companion" decorative /></div>
        <p className="admin-record-context">{selected.context}</p><h3>{selected.title}</h3><div className="admin-record-status">{selected.status}</div>
        {selected.detail && <details className="admin-preview-description"><summary>Thông tin chi tiết</summary>{selected.detail}</details>}
        {preview?.(selected.id)}
        <Link className="admin-preview-open" to={selected.href}>{kind === 'lessons' ? 'Đi đến bài học' : selected.action}<span aria-hidden="true"> →</span></Link>
      </aside>}
    </div>
  </div>
}

export function LessonLibraryPreview({ lessonId }: { lessonId: string }) {
  const vocabulary = useQuery({ queryKey: queryKeys.adminLessonVocabulary(lessonId), queryFn: () => listLessonVocabulary(lessonId) })
  const grammar = useQuery({ queryKey: queryKeys.adminLessonGrammar(lessonId), queryFn: () => listLessonGrammar(lessonId) })
  if (vocabulary.isPending || grammar.isPending) return <p role="status">Đang tải nội dung…</p>
  if (vocabulary.isError || grammar.isError) return <div><p role="alert">Chưa tải được nội dung xem nhanh.</p><button type="button" onClick={() => { void vocabulary.refetch(); void grammar.refetch() }}>Thử lại</button></div>
  const word = vocabulary.data[0]
  return <div className="admin-lesson-glimpse"><p>{vocabulary.data.length} từ vựng · {grammar.data.length} mục ngữ pháp</p>{word ? <><VocabularyIllustration hanzi={word.hanzi ?? ''}/><p className="admin-glimpse-hanzi" lang="zh-Hans">{word.hanzi}</p><p>{word.pinyin}</p><p>{word.vietnamese_meaning}</p></> : <p>Bài học chưa có từ vựng.</p>}</div>
}
