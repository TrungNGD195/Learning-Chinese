import { PageHeader, StatusBadge } from '../../components/ui'
import type { components } from '../../types/api.generated'
import { HeaderArtwork, sceneForTitle } from '../../components/academy/AcademyArtwork'

type Lesson = components['schemas']['LessonResponse']
type LessonProgress = components['schemas']['LessonProgressResponse']

export function LessonHeader({ lesson, progress, hskLabel }: { lesson: Lesson; progress: LessonProgress; hskLabel: string | null }) {
  return <div className="learner-surface lesson-header">
    <PageHeader title={`Lesson ${lesson.lesson_number}: ${lesson.title}`} titleId="page-title" description={lesson.description ?? undefined} artwork={<HeaderArtwork scene={sceneForTitle(lesson.title)} pose={progress.completed_at?'celebrate':'think'}/>} />
    {hskLabel&&<span className="academy-context-label">{hskLabel}</span>}
    <ul className="lesson-progress" aria-label="Lesson progress">
      <li><StatusBadge tone={progress.started_at ? 'info' : 'neutral'}>Started: {progress.started_at ? 'Yes' : 'Not started'}</StatusBadge></li>
      <li><StatusBadge tone={progress.theory_completed_at ? 'success' : 'neutral'}>Theory: {progress.theory_completed_at ? 'Complete' : 'In progress'}</StatusBadge></li>
      <li><StatusBadge tone={progress.completed_at ? 'success' : 'neutral'}>Lesson: {progress.completed_at ? 'Complete' : 'In progress'}</StatusBadge></li>
    </ul>
  </div>
}
