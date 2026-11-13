import { useState } from 'react'
import { useMandarinAudio } from '../../lib/audio/mandarinAudio'
import { AcademyIcon } from '../../components/academy/AcademyIcon'
import { Button } from '../../components/ui'


export function VocabularyAudio({ hanzi }: { hanzi: string }) {
  const { voiceAvailable, speak, isSpeaking, speechError } = useMandarinAudio()
  const [requested, setRequested] = useState(false)
  const message = requested && !voiceAvailable ? 'Thiết bị chưa có giọng đọc tiếng Trung. Hãy bật giọng tiếng Trung trong cài đặt giọng nói rồi thử lại.' : speechError
  return <div className="vocabulary-audio">
    <Button className="vocabulary-audio__button" variant="secondary" aria-label={`Nghe phát âm ${hanzi}`} aria-busy={isSpeaking} title="Nghe phát âm tiếng Trung" onClick={() => { setRequested(true); speak({ hanzi }) }}><AcademyIcon name="sound" size={21}/><span>Nghe phát âm</span></Button>
    {message && <p className="vocabulary-audio__message" role="status">{message}</p>}
  </div>
}
