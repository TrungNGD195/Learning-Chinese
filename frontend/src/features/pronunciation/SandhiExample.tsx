import { Button } from '../../components/ui'
import { AcademyIcon } from '../../components/academy/AcademyIcon'
import type { Sound } from './pronunciationData'

export function SandhiExample({ sound, voiceAvailable, onListen }: { sound: Sound; voiceAvailable: boolean; onListen: () => void }) {
  return <div className="sandhi-example">
    <p className="sandhi-example__rule">{sound.symbol}</p>
    <p className="sandhi-example__hanzi" lang="zh-Hans">{sound.hanzi}</p>
    <p className="sandhi-example__meaning">{sound.meaning}</p>
    <dl className="sandhi-example__comparison"><div><dt>Thanh gốc</dt><dd>{sound.pinyin}</dd></div><div><dt>Cách đọc</dt><dd>{sound.spoken}</dd></div></dl>
    <p>{sound.explanation}</p>{sound.note && <p className="sandhi-example__note">{sound.note}</p>}
    <Button variant="secondary" disabled={!voiceAvailable} onClick={onListen}><AcademyIcon name="sound" size={19}/>Nghe cả cụm</Button>
    <small>Giọng đọc của thiết bị để tham khảo; hãy đọc lại theo quy tắc ở trên.</small>
  </div>
}
