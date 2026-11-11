import { describe, expect, it } from 'vitest'
import { continuousJourneyStops, journeyUnitStop, orderedJourneyUnits, type JourneyUnit } from './journeyData'

const lesson: JourneyUnit = { id: 'unit-real', order_index: 7, unit_type: 'LESSON', state: 'AVAILABLE', lesson: { id: 'lesson-real', lesson_number: 6, title: 'Chào hỏi', status: 'PUBLISHED' }, assessment: null }

describe('server curriculum to Great Wall', () => {
  it('uses real IDs and lesson numbers and never grants access to a locked level or unpublished lesson', () => {
    expect(journeyUnitStop(lesson, 1, true)).toMatchObject({ id: 'unit-real', name: 'Bài học 6: Chào hỏi', destination: '/lessons/lesson-real', state: 'AVAILABLE' })
    expect(journeyUnitStop(lesson, 1, false)).toMatchObject({ destination: null, state: 'LOCKED' })
    expect(journeyUnitStop({ ...lesson, state: 'LOCKED' }, 1, true).destination).toBeNull()
    expect(journeyUnitStop({ ...lesson, lesson: { ...lesson.lesson!, status: 'DRAFT' } }, 1, true).destination).toBeNull()
    expect(journeyUnitStop({ ...lesson, lesson: null }, 1, true).destination).toBeNull()
  })
  it('routes a real periodic assessment and preserves server order without changing the cached data', () => {
    const test: JourneyUnit = { id: 'test-unit', order_index: 2, unit_type: 'PERIODIC_TEST', state: 'COMPLETED', lesson: null, assessment: { id: 'test-real', title: 'Ôn tập', type: 'PERIODIC_TEST', status: 'PUBLISHED' } }
    const input = [lesson, test]
    expect(orderedJourneyUnits(input).map(row => row.id)).toEqual(['test-unit', 'unit-real'])
    expect(input[0]).toBe(lesson)
    expect(journeyUnitStop(test, 2, true)).toMatchObject({ state: 'COMPLETED', kind: 'test', destination: '/assessments/test-real' })
  })
  it.each([[1,15],[2,10],[3,15]])('lays out every planned lesson in HSK %i without publishing invented content', (level,count) => {
    const stops = continuousJourneyStops([],level,true)
    expect(stops).toHaveLength(count)
    expect(stops.map(stop=>stop.lessonNumber)).toEqual(Array.from({length:count},(_,index)=>index+1))
    expect(stops.every(stop=>stop.planned && !stop.destination && stop.state==='LOCKED')).toBe(true)
  })
  it('keeps the real lesson and test order and inserts only missing lesson placeholders', () => {
    const test: JourneyUnit = {id:'test',order_index:8,unit_type:'PERIODIC_TEST',state:'AVAILABLE',lesson:null,assessment:{id:'assessment-real',title:'Ôn tập',status:'PUBLISHED',type:'PERIODIC_TEST'}}
    const next: JourneyUnit = {...lesson,id:'next',order_index:9,lesson:{...lesson.lesson!,id:'lesson-7',lesson_number:7}}
    const stops=continuousJourneyStops([next,test,lesson],1,true)
    expect(stops).toHaveLength(16)
    expect(stops.slice(5,8).map(stop=>stop.id)).toEqual(['unit-real','test','next'])
    expect(stops[5].destination).toBe('/lessons/lesson-real')
    expect(stops[6].destination).toBe('/assessments/assessment-real')
    expect(stops[7].destination).toBe('/lessons/lesson-7')
  })
})
