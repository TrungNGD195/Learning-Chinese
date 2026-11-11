import type { components } from '../../types/api.generated'

export type JourneyUnit = components['schemas']['UnitProgress']
export type JourneyStop = { id: string; name: string; shortName: string; hanzi?: string; kind: 'foundation' | 'lesson' | 'test'; state: JourneyUnit['state']; destination: string | null; slot: number; planned?: boolean; unpublished?: boolean; lessonNumber?: number }
export const plannedLessonCounts: Record<number, number> = { 1: 15, 2: 10, 3: 15 }

export function orderedJourneyUnits(units: JourneyUnit[]) {
  return [...units].sort((a, b) => a.order_index - b.order_index)
}
export function journeyUnitStop(unit: JourneyUnit, slot: number, unlocked: boolean): JourneyStop {
  const lesson = unit.unit_type === 'LESSON'
  const target = lesson ? unit.lesson : unit.assessment
  const published = target?.status === 'PUBLISHED'
  const name = lesson ? `Bài học ${unit.lesson?.lesson_number ?? unit.order_index}: ${unit.lesson?.title ?? 'Chưa có nội dung'}` : `Kiểm tra định kỳ ${unit.order_index}: ${unit.assessment?.title ?? 'Chưa có nội dung'}`
  return { id: unit.id, name, shortName: lesson ? `Bài ${unit.lesson?.lesson_number ?? unit.order_index}` : 'Kiểm tra', hanzi: target?.title.match(/\p{Script=Han}+/gu)?.join(''), kind: lesson ? 'lesson' : 'test', state: unlocked && published ? unit.state : 'LOCKED', destination: unlocked && published && unit.state !== 'LOCKED' ? `${lesson ? '/lessons/' : '/assessments/'}${encodeURIComponent(target!.id)}` : null, slot, unpublished: !published, lessonNumber: lesson ? unit.lesson?.lesson_number : undefined }
}

export function continuousJourneyStops(units: JourneyUnit[], level: number, unlocked: boolean): JourneyStop[] {
  const stops: JourneyStop[] = []
  const plannedCount = plannedLessonCounts[level] ?? 0
  let nextNumber = 1
  const appendPlanned = (number: number) => stops.push({ id: `planned-hsk-${level}-${number}`, name: `Bài học ${number}: Sắp có nội dung`, shortName: `Bài ${number}`, kind: 'lesson', state: 'LOCKED', destination: null, slot: stops.length, planned: true, lessonNumber: number })
  for (const unit of orderedJourneyUnits(units)) {
    const number = unit.lesson?.lesson_number
    if (unit.unit_type === 'LESSON' && number) {
      while (nextNumber < number && nextNumber <= plannedCount) appendPlanned(nextNumber++)
      nextNumber = Math.max(nextNumber, number + 1)
    }
    stops.push(journeyUnitStop(unit, stops.length, unlocked))
  }
  while (nextNumber <= plannedCount) appendPlanned(nextNumber++)
  return stops.map((stop, slot) => ({ ...stop, slot }))
}
