export type LessonPart = 'vocabulary' | 'grammar' | 'readings' | 'practice'

export function lessonPartPath(lessonId: string, part: LessonPart) {
  return `/lessons/${encodeURIComponent(lessonId)}/${part}`
}

export const legacyLessonParts: Record<string, LessonPart | undefined> = {
  '#vocabulary': 'vocabulary', '#grammar': 'grammar', '#readings': 'readings', '#exercise': 'practice',
}
