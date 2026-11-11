import { useState } from 'react'
import type { AssessmentQuestion } from './QuestionRenderer'
import { VocabularyAudio } from '../lesson/VocabularyAudio'
import { VocabularyIllustration } from '../../components/academy/Companion'

export function QuestionMedia({ question }: { question: AssessmentQuestion }) {
  const presentation = question.config.presentation
  const [transcript, setTranscript] = useState(false)
  if (!presentation) return null
  return <div className="practice-question-media">
    {presentation.audio_text && <div className="practice-listen"><div><strong>Nghe tiếng Trung</strong><p>Nghe lại bao nhiêu lần bạn cần, rồi chọn câu trả lời.</p></div><VocabularyAudio hanzi={presentation.audio_text}/><button type="button" className="practice-transcript" aria-expanded={transcript} onClick={() => setTranscript(!transcript)}>{transcript ? 'Ẩn bản chữ' : 'Xem bản chữ nếu không nghe được'}</button>{transcript && <p lang="zh-Hans" className="practice-reading">{presentation.audio_text}</p>}<small>Giọng đọc tiếng Trung của thiết bị.</small></div>}
    {presentation.image_hanzi && <div className="practice-image"><VocabularyIllustration hanzi={presentation.image_hanzi}/></div>}
    {presentation.reading_text && <div className="practice-reading" lang="zh-Hans">{presentation.reading_text}</div>}
  </div>
}
