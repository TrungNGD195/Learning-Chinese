import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { expect, it, vi } from 'vitest'
import type { components } from '../../types/api.generated'
import { JourneyCloudContext } from '../journey/journeyCloudContext'
import { LessonHeader } from './LessonHeader'

const lesson: components['schemas']['LessonResponse'] = { id: 'lesson', hsk_level_id: 'hsk', lesson_number: 2, title: 'Bài học', description: null, vocabulary: [], grammar: [], readings: [], assessment_ids: [] }
const progress: components['schemas']['LessonProgressResponse'] = { lesson_id: 'lesson', started_at: null, theory_completed_at: null, completed_at: null, vocabulary: [], grammar: [], readings: [], prerequisites_bypassed: false }

it.each([1, 2, 3])('returns directly to the lesson list for HSK %s, including its cloud destination', level => {
  const travel = vi.fn(() => true)
  render(<MemoryRouter><JourneyCloudContext.Provider value={{ travel, cancel: vi.fn() }}><LessonHeader lesson={lesson} progress={progress} hskLabel={`HSK ${level}`} hskLevelNumber={level}/></JourneyCloudContext.Provider></MemoryRouter>)
  const link = screen.getByRole('link', { name: `Về danh sách bài HSK ${level}` })
  expect(link).toHaveAttribute('href', `/hsk/${level}`)
  fireEvent.click(link)
  expect(travel).toHaveBeenCalledWith({ destination: `/hsk/${level}`, returning: true })
  travel.mockClear()
  fireEvent.click(link, { ctrlKey: true })
  expect(travel).not.toHaveBeenCalled()
})

it('still targets the same HSK list before level metadata has loaded', () => {
  render(<MemoryRouter><LessonHeader lesson={lesson} progress={progress} hskLabel={null}/></MemoryRouter>)
  expect(screen.getByRole('link', { name: 'Về giáo trình' })).toHaveAttribute('href', '/hsk/hsk')
})
