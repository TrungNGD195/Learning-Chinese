import { useId, useState, useSyncExternalStore } from 'react'
import { Companion, VocabularyIllustration } from '../../components/academy/Companion'
import { StrokeOrder } from '../../components/hanzi/StrokeOrder'
import { learnerLabel } from '../../lib/learnerLabels'
import { VocabularyAudio } from './VocabularyAudio'
import { VocabularyDiscovery } from './VocabularyDiscovery'
import { vocabularyDiscovery } from './vocabularyDiscoveries'

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
  const discovery = vocabularyDiscovery(word.hanzi)
  return <div className="vocabulary-study-frame"><article className="vocabulary-study-card" data-has-discovery={!!discovery} aria-label={'Từ vựng ' + word.hanzi}>
    <div className="vocabulary-study-card__summary">
      <div className="vocabulary-study-card__identity"><h2 lang="zh-Hans">{word.hanzi}</h2><div className="vocabulary-study-card__pronunciation"><p className="vocabulary-study-card__pinyin">{word.pinyin}</p><VocabularyAudio key={word.hanzi} hanzi={word.hanzi}/></div>{word.part_of_speech && <p className="vocabulary-study-card__pos">Loại từ: {learnerLabel(word.part_of_speech)}</p>}<p className="vocabulary-study-card__meaning">{word.vietnamese_meaning}</p></div>
    </div>
    <div className="vocabulary-study-card__media"><div className="vocabulary-study-card__artwork"><VocabularyIllustration hanzi={word.hanzi} partOfSpeech={word.part_of_speech}/><span className="vocabulary-study-card__artwork-placeholder">Chưa có hình minh họa</span></div>{discovery && <VocabularyDiscovery key={word.hanzi} discovery={discovery} hanzi={word.hanzi} pinyin={word.pinyin}/>}</div>
    <div className="vocabulary-study-card__writing">{collapsibleWriting && <button type="button" className="lesson-writing-toggle" aria-expanded={showWriting} aria-controls={writingId} onClick={() => setWritingOpen(value => !value)}>Luyện viết nét<span aria-hidden="true">{writingOpen ? '−' : '+'}</span></button>}<div id={writingId} hidden={!showWriting}>{showWriting && <StrokeOrder hanzi={word.hanzi}/>}</div></div>
    <div className="vocabulary-study-card__details">
      {example?.trim() && <section className="vocabulary-study-card__example"><h3>Ví dụ</h3><p>{example}</p></section>}
      {note?.trim() && <section className="vocabulary-study-card__note"><div><h3>Lưu ý khi dùng</h3><p>{note}</p></div>{!discovery && <Companion pose="truc" decorative/>}</section>}
    </div>
  </article></div>
}
