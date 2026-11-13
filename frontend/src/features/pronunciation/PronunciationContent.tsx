import { useMandarinAudio } from '../../lib/audio/mandarinAudio'
import { pronunciationContent, type PronunciationCode } from './pronunciationData'
import { FinalAudio } from './FinalAudio'

export function PronunciationContent({ code }: { code: string }) {
  const { voiceAvailable, speak } = useMandarinAudio()
  const lesson = pronunciationContent[code as PronunciationCode]
  if (!lesson) return null

  return <details className="pronunciation-lesson">
    <summary className="pronunciation-lesson__summary">Mở nội dung học <span aria-hidden="true">↓</span></summary>
    <div className="pronunciation-lesson__body">
      {code!=='INITIALS'&&code!=='FINALS'&&<p>{lesson.intro}</p>}
      <p className="pronunciation-lesson__audio-note" role="status">Chọn một ví dụ để nghe, rồi đọc lại theo mẫu.</p>
      {lesson.groups.map((group) => <section className="pronunciation-sound-group" key={group.title}>
        <h3>{group.title}</h3><p>{group.tip}</p>
        <ul className="pronunciation-sounds">{group.sounds.map((sound) => <li key={sound.symbol}>
          {code==='FINALS'?<><strong>{sound.symbol}</strong><FinalAudio sound={sound}/></>:<button type="button" className="pronunciation-sound" disabled={!voiceAvailable||sound.audioUnavailable} onClick={() => speak(sound)} aria-label={`Nghe ${sound.pinyin}, ví dụ ${sound.hanzi}`}>
            <span className="pronunciation-sound__symbol">{sound.symbol}</span>
            <span><span lang="zh-Hans">{sound.hanzi}</span> · {sound.pinyin}</span>
            <span aria-hidden="true">{voiceAvailable&&!sound.audioUnavailable ? '♪' : '—'}</span>
          </button>}
          {code!=='FINALS'&&sound.note&&<small>{sound.note}</small>}
        </li>)}</ul>
      </section>)}
      <div className="pronunciation-lesson__notes"><h3>Ghi nhớ</h3><ul>{lesson.notes.map((note) => <li key={note}>{note}</li>)}</ul></div>
    </div>
  </details>
}
