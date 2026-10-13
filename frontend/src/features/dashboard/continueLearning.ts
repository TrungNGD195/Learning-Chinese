import type { components } from '../../types/api.generated'

export type ContinueLearningTarget = NonNullable<
  components['schemas']['DashboardResponse']['continue_learning']
>

export function continueLearningPath(target: ContinueLearningTarget): string {
  switch (target.type) {
    case 'PRONUNCIATION':
      return '/pronunciation'
    case 'LESSON':
      return `/lessons/${encodeURIComponent(target.lesson_id)}`
    case 'PERIODIC_TEST':
      return `/assessments/${encodeURIComponent(target.assessment_id)}`
  }
}
