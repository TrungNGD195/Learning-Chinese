import { AcademyIcon } from '../../components/academy/AcademyIcon'
import { Button } from '../../components/ui'
import { useMandarinAudio } from '../../lib/audio/mandarinAudio'
import { finalCombinations, finalReadingNotes, specialIGroups } from './finalAudioExamples'
import type { Sound } from './pronunciationData'
import { ongClipForDuration } from './ongDuration'

export function FinalAudio({ sound }: { sound: Sound }) {
  const { voiceAvailable, speak, speechError, voiceName, zhongReference } = useMandarinAudio()
  const isolated = sound.symbol === 'ong' ? { ...sound, clip: ongClipForDuration(zhongReference?.voiceName === voiceName ? zhongReference?.seconds : undefined) } : sound
  const combined = finalCombinations[sound.symbol]
  const note = finalReadingNotes[sound.symbol]
  return <div className="phonetic-audio-panel">
    <div className="phonetic-audio-controls">
      <Button variant="secondary" disabled={sound.audioUnavailable || (!sound.clip && !voiceAvailable)}
        aria-label={`Nghe vận mẫu ${sound.symbol}`} onClick={() => speak(isolated)}>
        <AcademyIcon name="sound" size={20}/><span>Nghe vận mẫu riêng<strong>{sound.symbol}</strong></span>
      </Button>
      <Button variant="secondary" disabled={!voiceAvailable || !combined}
        aria-label={combined ? `Nghe âm ghép ${combined.pinyin}` : 'Không ghép với thanh mẫu'}
        onClick={() => { if (combined) speak(combined) }}>
        <AcademyIcon name="sound" size={20}/><span>Nghe âm ghép<strong>{combined?.pinyin ?? 'Không áp dụng'}</strong></span>
      </Button>
    </div>
    {sound.audioUnavailable && <small>{sound.note}</small>}
    {note && <div className="phonetic-reading-notes"><h3>Cách đọc cần phân biệt</h3><p className="phonetic-audio-note">{note}</p>
      {sound.symbol === 'i' && <>
        {specialIGroups.map(group=><div className="phonetic-special-group" key={group.title}><h4>{group.title}</h4>
          <div className="phonetic-special-examples">{group.sounds.map(example => <Button key={example.pinyin} variant="secondary" disabled={!example.clip && !voiceAvailable}
            aria-label={`Nghe i đặc biệt trong ${example.pinyin}`} onClick={() => speak(example)}><AcademyIcon name="sound" size={16}/>{example.pinyin}</Button>)}</div>
        </div>)}
      </>}
    </div>}
    {speechError && <p role="alert">{speechError}</p>}
  </div>
}
