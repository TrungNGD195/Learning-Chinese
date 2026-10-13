import type { components } from '../../types/api.generated'

type Lesson = components['schemas']['LessonResponse']
type LessonProgress = components['schemas']['LessonProgressResponse']

export function LessonHeader({ lesson, progress, hskLabel }: { lesson: Lesson; progress: LessonProgress; hskLabel: string | null }) {
  return <header className="learning-card lesson-header">
    {hskLabel && <p className="eyebrow">{hskLabel}</p>}
    <h1 id="page-title">Lesson {lesson.lesson_number}: {lesson.title}</h1>
    {lesson.description && <p>{lesson.description}</p>}
    <p>Started: {progress.started_at ? 'Yes' : 'Not started'}</p>
    <p>Theory: {progress.theory_completed_at ? 'Complete' : 'In progress'}</p>
    <p>Lesson: {progress.completed_at ? 'Complete' : 'In progress'}</p>
  </header>
}
