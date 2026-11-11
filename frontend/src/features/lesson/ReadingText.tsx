import type { components } from '../../types/api.generated'

export type LessonReading = components['schemas']['ReadingResponse']

export function ReadingText({ reading }: { reading: Pick<LessonReading, 'content' | 'pinyin' | 'vietnamese_translation' | 'source_reference'> }) {
  return <div className="lesson-reading-text">
    <p className="lesson-reading-text__hanzi" lang="zh-Hans">{reading.content}</p>
    {reading.pinyin && <div className="lesson-reading-text__support"><h4>Phiên âm</h4><p className="lesson-reading-text__pinyin">{reading.pinyin}</p></div>}
    {reading.vietnamese_translation && <div className="lesson-reading-text__support"><h4>Nghĩa tiếng Việt</h4><p>{reading.vietnamese_translation}</p></div>}
  </div>
}
