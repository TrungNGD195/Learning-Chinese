import { Link } from 'react-router'
import type { components } from '../../types/api.generated'
import { AcademyIcon } from '../../components/academy/AcademyIcon'
import { useJourneyCloud } from '../journey/journeyCloudContext'

type Lesson = components['schemas']['LessonResponse']
type LessonProgress = components['schemas']['LessonProgressResponse']

export function LessonHeader({ lesson, progress, hskLabel, refreshing = false }: { lesson: Lesson; progress: LessonProgress; hskLabel: string | null; refreshing?: boolean }) {
  const travel = useJourneyCloud()
  const total = lesson.vocabulary.length + lesson.grammar.length + (lesson.readings?.length ?? 0)
  const viewed = lesson.vocabulary.filter(word => progress.vocabulary.some(row => row.id === word.id && row.viewed)).length
    + lesson.grammar.filter(item => progress.grammar.some(row => row.id === item.id && row.viewed)).length
    + (lesson.readings ?? []).filter(item => progress.readings?.some(row => row.id === item.id && row.completed)).length
  return <header className="lesson-header lesson-header--compact">
    <div className="lesson-header__identity"><Link className="lesson-header__back" to="/pronunciation" aria-label="Về giáo trình" onClick={event => { if (event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey && travel?.travel({ destination: '/pronunciation', returning: true })) event.preventDefault() }}><AcademyIcon name="arrow" size={18}/>{hskLabel ?? 'Giáo trình'}</Link>
      <h1 id="page-title" title={`Bài học ${lesson.lesson_number}: ${lesson.title}`}>Bài học {lesson.lesson_number}: {lesson.title}</h1>
    </div>
    <div className="lesson-header__progress" aria-label="Tiến độ bài học"><p>{progress.completed_at ? 'Bài học: Đã hoàn thành' : progress.theory_completed_at ? 'Lý thuyết: Đã hoàn thành' : 'Lý thuyết: Đang học'}</p>
      <div><progress aria-label="Tiến độ lý thuyết" max={Math.max(1, total)} value={viewed}/><span>{viewed}/{total} mục</span><span className="lesson-header__sync" data-busy={refreshing} aria-live="polite"><span className="sr-only">{refreshing ? 'Đang cập nhật bài học.' : ''}</span></span></div>
    </div>
  </header>
}
