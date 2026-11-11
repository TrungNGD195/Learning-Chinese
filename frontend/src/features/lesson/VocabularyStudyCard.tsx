import { useId, useState, useSyncExternalStore } from 'react'
import { Companion, VocabularyIllustration } from '../../components/academy/Companion'
import { StrokeOrder } from '../../components/hanzi/StrokeOrder'
import { learnerLabel } from '../../lib/learnerLabels'
import { VocabularyAudio } from './VocabularyAudio'

type Word = { hanzi: string; pinyin: string; vietnamese_meaning: string; part_of_speech?: string | null }

function subscribeCompact(listener: () => void) {
  const query = window.matchMedia?.('(max-width: 800px)')
  query?.addEventListener('change', listener)
  return () => query?.removeEventListener('change', listener)
}
function compactSnapshot() { return window.matchMedia?.('(max-width: 800px)').matches ?? false }

export function VocabularyStudyCard({ word, example, note, collapsibleWriting = false }: { word: Word; example?: string | null; note?: string | null; collapsibleWriting?: boolean }) {
  const compact = useSyncExternalStore(subscribeCompact, compactSnapshot, () => false)
  const [writingOpen, setWritingOpen] = useState(false)
  const writingId = useId()
  const showWriting = !collapsibleWriting || !compact || writingOpen
  return <div className="vocabulary-study-frame"><article className="vocabulary-study-card" aria-label={'Từ vựng ' + word.hanzi}>
    <div className="vocabulary-study-card__summary">
      <div className="vocabulary-study-card__identity"><h2 lang="zh-Hans">{word.hanzi}</h2><div className="vocabulary-study-card__pronunciation"><p className="vocabulary-study-card__pinyin">{word.pinyin}</p><VocabularyAudio key={word.hanzi} hanzi={word.hanzi}/></div><p className="vocabulary-study-card__meaning">{word.vietnamese_meaning}</p>{word.part_of_speech && <p className="vocabulary-study-card__pos">Loại từ: {learnerLabel(word.part_of_speech)}</p>}</div>
      <VocabularyIllustration hanzi={word.hanzi} partOfSpeech={word.part_of_speech}/>
    </div>
    <div className="vocabulary-study-card__writing">{collapsibleWriting && <button type="button" className="lesson-writing-toggle" aria-expanded={showWriting} aria-controls={writingId} onClick={() => setWritingOpen(value => !value)}>Luyện viết nét<span aria-hidden="true">{writingOpen ? '−' : '+'}</span></button>}<div id={writingId} hidden={!showWriting}>{showWriting && <StrokeOrder hanzi={word.hanzi}/>}</div></div>
    <div className="vocabulary-study-card__details">
      {example?.trim() && <section className="vocabulary-study-card__example"><h3>Ví dụ</h3><p>{example}</p></section>}
      {note?.trim() && <section className="vocabulary-study-card__note"><div><h3>Lưu ý khi dùng</h3><p>{note}</p></div><Companion pose="truc" decorative/></section>}
    </div>
  </article></div>
}
