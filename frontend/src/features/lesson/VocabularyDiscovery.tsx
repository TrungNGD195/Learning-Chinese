import { useRef } from 'react'
import { AcademyIcon } from '../../components/academy/AcademyIcon'
import { Companion } from '../../components/academy/Companion'
import type { VocabularyDiscovery as Discovery } from './vocabularyDiscoveries'
import './vocabulary-discovery.css'

export function VocabularyDiscovery({ discovery, hanzi, pinyin }: { discovery: Discovery; hanzi: string; pinyin: string }) {
  const popup = useRef<HTMLDialogElement>(null)
  return <>
    <button type="button" className="vocabulary-discovery-entry" aria-label={`Khám phá thêm về ${hanzi}`} aria-haspopup="dialog" onClick={() => popup.current?.showModal()}>
      <Companion pose="truc" decorative/>
      <span className="vocabulary-discovery-entry__teaser">{discovery.teaser}</span>
      <span className="vocabulary-discovery-entry__action">Khám phá thêm<AcademyIcon name="arrow" size={18}/></span>
    </button>
    <dialog ref={popup} className="vocabulary-discovery-popup" aria-label={discovery.title} onClick={event => {
      const bounds = event.currentTarget.getBoundingClientRect()
      if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) popup.current?.close()
    }}>
      <header className="vocabulary-discovery-popup__header"><div><Companion pose="truc" decorative/><span>Khám phá cùng Trúc</span></div><button type="button" autoFocus onClick={() => popup.current?.close()} aria-label="Đóng khám phá">Đóng ×</button></header>
      <h2>{discovery.title}</h2>
      <p className="vocabulary-discovery-popup__word"><span lang="zh-Hans">{hanzi}</span> · {pinyin}</p>
      <p className="vocabulary-discovery-popup__text">{discovery.text}</p>
      <details className="vocabulary-discovery-popup__sources"><summary>Nguồn tham khảo</summary><a href={discovery.sourceUrl} target="_blank" rel="noreferrer">{discovery.sourceLabel} ↗</a></details>
      <button type="button" className="vocabulary-discovery-popup__return" onClick={() => popup.current?.close()}>Quay lại từ đang học<AcademyIcon name="arrow" size={18}/></button>
    </dialog>
  </>
}
