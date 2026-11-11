import { pronunciationContent, useMandarinSpeech, type PronunciationCode } from './pronunciationData'

export function PronunciationContent({ code }: { code: string }) {
  const { voiceAvailable, speak } = useMandarinSpeech()
  const lesson = pronunciationContent[code as PronunciationCode]
  if (!lesson) return null

  return <details className="pronunciation-lesson">
    <summary className="pronunciation-lesson__summary">Mở nội dung học <span aria-hidden="true">↓</span></summary>
    <div className="pronunciation-lesson__body">
      <p>{lesson.intro}</p>
      <p className="pronunciation-lesson__audio-note" role="status">{voiceAvailable
        ? 'Chọn một ví dụ để nghe giọng đọc tiếng Trung của thiết bị. Giọng máy có thể khác giọng giáo viên.'
        : 'Thiết bị chưa có giọng đọc tiếng Trung phù hợp. Bạn vẫn có thể học các ví dụ chữ và Pinyin bên dưới.'}</p>
      {lesson.groups.map((group) => <section className="pronunciation-sound-group" key={group.title}>
        <h3>{group.title}</h3><p>{group.tip}</p>
        <ul className="pronunciation-sounds">{group.sounds.map((sound) => <li key={sound.symbol}>
          <button type="button" className="pronunciation-sound" disabled={!voiceAvailable} onClick={() => speak(sound)} aria-label={`Nghe ${sound.pinyin}, ví dụ ${sound.hanzi}`}>
            <span className="pronunciation-sound__symbol">{sound.symbol}</span>
            <span><span lang="zh-Hans">{sound.hanzi}</span> · {sound.pinyin}</span>
            <span aria-hidden="true">{voiceAvailable ? '♪' : '—'}</span>
          </button>
        </li>)}</ul>
      </section>)}
      <div className="pronunciation-lesson__notes"><h3>Ghi nhớ</h3><ul>{lesson.notes.map((note) => <li key={note}>{note}</li>)}</ul></div>
    </div>
  </details>
}
