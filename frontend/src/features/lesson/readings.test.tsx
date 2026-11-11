import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { components } from '../../types/api.generated'
import { ApiError } from '../../lib/api/errors'
import { queryKeys } from '../../app/query/keys'
import { LessonPage } from './LessonPage'
import { completeLessonReading, getLesson, markGrammarViewed, markVocabularyViewed } from './api'
import { getLessonProgress } from '../progress/api'
import { getHskLevels } from '../curriculum/api'
import { ReadingSection } from './ReadingSection'
import { LessonReadingsSection } from '../admin/LessonReadingsSection'
import { AuthoringSession, useHasUnsavedDrafts } from '../admin/AuthoringSession'
import { createLessonReading, listLessonReadings, updateLessonReading, deleteLessonReading } from '../admin/readingApi'

vi.mock('./api', () => ({ getLesson: vi.fn(), completeLessonReading: vi.fn(), markVocabularyViewed: vi.fn(), markGrammarViewed: vi.fn() }))
vi.mock('../progress/api', () => ({ getLessonProgress: vi.fn() }))
vi.mock('../curriculum/api', () => ({ getHskLevels: vi.fn() }))
vi.mock('../admin/readingApi', () => ({ createLessonReading: vi.fn(), listLessonReadings: vi.fn(), updateLessonReading: vi.fn(), deleteLessonReading: vi.fn() }))

const time = '2026-11-05T10:00:00Z'
const reading = { id: 'reading-1', order_index: 1, title: 'Chào hỏi', content: 'A：你好！\nB：你好！', pinyin: 'A: Nǐ hǎo!\nB: Nǐ hǎo!', vietnamese_translation: 'A: Xin chào!\nB: Xin chào!', source_reference: 'Giáo trình, bài 1, trang 1.', version: 1 }
const lesson: components['schemas']['LessonResponse'] = { id: 'lesson-1', hsk_level_id: 'hsk-1', lesson_number: 1, title: 'Xin chào', description: null, vocabulary: [], grammar: [], readings: [reading], assessment_ids: ['practice'] }
const progress: components['schemas']['LessonProgressResponse'] = { lesson_id: 'lesson-1', started_at: time, theory_completed_at: null, completed_at: null, vocabulary: [], grammar: [], readings: [{ id: reading.id, completed: false, completed_at: null }] }

function DirtyIndicator() { return <output data-testid="dirty">{String(useHasUnsavedDrafts())}</output> }
function mount(element = <LessonPage/>) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const router = createMemoryRouter([{ path: '/lessons/:lessonId', element }, { path: '/lessons/:lessonId/readings', element: <LessonPage part="readings"/> }, { path: '/lessons/:lessonId/practice', element: <LessonPage part="practice"/> }], { initialEntries: ['/lessons/lesson-1'] })
  return { client, ...render(<QueryClientProvider client={client}><RouterProvider router={router}/></QueryClientProvider>) }
}
beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(getLesson).mockResolvedValue(lesson)
  vi.mocked(getLessonProgress).mockResolvedValue(progress)
  vi.mocked(getHskLevels).mockResolvedValue([])
  vi.mocked(completeLessonReading).mockResolvedValue({ completed_at: time, theory_completed_at: time })
  vi.mocked(listLessonReadings).mockResolvedValue([reading])
  vi.mocked(updateLessonReading).mockResolvedValue(reading)
  vi.mocked(createLessonReading).mockResolvedValue({ ...reading, id: 'reading-2', order_index: 2 })
  vi.mocked(deleteLessonReading).mockResolvedValue({ deleted: true })
})

describe('learner reading completion', () => {
  it('renders the textbook reading without auto-completing; server progress unlocks practice after explicit completion', async () => {
    mount()
    fireEvent.click(await screen.findByRole('link', { name: 'Bài khóa' }))
    expect(await screen.findByRole('heading', { name: 'Chào hỏi', level: 3 })).toBeInTheDocument()
    expect(screen.queryByText(/Nguồn:/)).not.toBeInTheDocument()
    expect(screen.queryByText(reading.source_reference)).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Bài khóa' })).toHaveAttribute('href', '/lessons/lesson-1/readings')
    expect(completeLessonReading).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: 'Mở luyện tập 1' })).not.toBeInTheDocument()
    vi.mocked(getLessonProgress).mockResolvedValue({ ...progress, theory_completed_at: time, readings: [{ id: reading.id, completed: true, completed_at: time }] })
    fireEvent.click(screen.getByRole('button', { name: 'Hoàn thành bài khóa: Chào hỏi' }))
    await waitFor(() => expect(completeLessonReading).toHaveBeenCalledWith('lesson-1', 'reading-1', 1))
    expect(await screen.findByRole('button', { name: 'Đã hoàn thành bài khóa: Chào hỏi' })).toBeDisabled()
    fireEvent.click(screen.getByRole('link', { name: 'Luyện tập' }))
    expect(await screen.findByRole('link', { name: 'Mở luyện tập 1' })).toHaveAttribute('href', '/assessments/practice')
  })

  it('does not unlock for a stale theory timestamp when a reading is still incomplete', async () => {
    vi.mocked(getLessonProgress).mockResolvedValue({ ...progress, theory_completed_at: time })
    mount()
    fireEvent.click(await screen.findByRole('link', { name: 'Luyện tập' }))
    expect(await screen.findByRole('button', { name: 'Mở luyện tập 1' })).toBeDisabled()
    expect(screen.queryByRole('link', { name: 'Mở luyện tập 1' })).not.toBeInTheDocument()
  })

  it('preserves the incomplete state on failure and permits retry without duplicate pending requests', async () => {
    let reject!: (reason: unknown) => void
    vi.mocked(completeLessonReading).mockImplementationOnce(() => new Promise((_, fail) => { reject = fail }))
    mount(<ReadingSection lessonId="lesson-1" readings={[reading]} completedIds={new Set()}/>)
    const button = screen.getByRole('button', { name: 'Hoàn thành bài khóa: Chào hỏi' })
    fireEvent.click(button); fireEvent.click(button)
    await waitFor(() => expect(completeLessonReading).toHaveBeenCalledTimes(1))
    expect(button).toBeDisabled()
    await act(async () => reject(new Error('offline')))
    expect(await screen.findByRole('alert')).toHaveTextContent('Chưa thể lưu trạng thái hoàn thành')
    expect(button).toBeEnabled()
    fireEvent.click(button)
    await waitFor(() => expect(completeLessonReading).toHaveBeenCalledTimes(2))
  })

  it('refreshes content and progress after a stale reading version is rejected', async () => {
    vi.mocked(completeLessonReading).mockRejectedValue(new ApiError({ status: 409, code: 'READING_VERSION_CHANGED', message: 'changed', details: null }))
    const { client } = mount(<ReadingSection lessonId="lesson-1" readings={[reading]} completedIds={new Set()}/>)
    const invalidate = vi.spyOn(client, 'invalidateQueries')
    fireEvent.click(screen.getByRole('button', { name: 'Hoàn thành bài khóa: Chào hỏi' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Bài khóa vừa được cập nhật')
    expect(invalidate).toHaveBeenCalledWith({ queryKey: queryKeys.lesson('lesson-1') })
    expect(invalidate).toHaveBeenCalledWith({ queryKey: queryKeys.lessonProgress('lesson-1') })
  })
})

describe('admin reading authoring', () => {
  const editor = () => mount(<AuthoringSession><DirtyIndicator/><LessonReadingsSection lessonId="lesson-1" lessonStatus="DRAFT" active/></AuthoringSession>)
  const form = () => within(Array.from(document.querySelectorAll<HTMLFormElement>('.admin-reading-editor form')).find(node => !node.closest('[hidden]'))!)

  it('preserves a new unsaved reading across selection changes and failed saves, and sends reading-only fields', async () => {
    editor()
    await screen.findByRole('button', { name: '1. Chào hỏi' })
    fireEvent.click(screen.getByRole('button', { name: 'Thêm bài khóa' }))
    fireEvent.change(form().getByLabelText('Tiêu đề bài khóa'), { target: { value: 'Đọc tiếp' } })
    fireEvent.change(form().getByLabelText('Nội dung tiếng Trung'), { target: { value: '我很好。' } })
    expect(screen.getByTestId('dirty')).toHaveTextContent('true')
    fireEvent.click(screen.getByRole('button', { name: '1. Chào hỏi' }))
    fireEvent.click(screen.getByRole('button', { name: 'Thêm bài khóa' }))
    expect(form().getByLabelText('Nội dung tiếng Trung')).toHaveValue('我很好。')
    vi.mocked(createLessonReading).mockRejectedValueOnce(new Error('save failed'))
    fireEvent.click(screen.getByRole('button', { name: 'Lưu bài khóa' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Không thể lưu bài khóa')
    expect(form().getByLabelText('Nội dung tiếng Trung')).toHaveValue('我很好。')
    expect(createLessonReading).toHaveBeenCalledWith('lesson-1', { title: 'Đọc tiếp', order_index: 2, content: '我很好。', pinyin: null, vietnamese_translation: null, source_reference: null })
    expect(markVocabularyViewed).not.toHaveBeenCalled(); expect(markGrammarViewed).not.toHaveBeenCalled(); expect(completeLessonReading).not.toHaveBeenCalled()
  })

  it('requires explicit delete confirmation and displays archived readings as read only', async () => {
    const { unmount } = editor()
    const remove = await screen.findByRole('button', { name: 'Xóa bài khóa' })
    fireEvent.click(remove)
    expect(deleteLessonReading).not.toHaveBeenCalled()
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Hủy' }))
    expect(deleteLessonReading).not.toHaveBeenCalled()
    fireEvent.click(remove)
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Xóa bài khóa' }))
    await waitFor(() => expect(deleteLessonReading).toHaveBeenCalledWith('lesson-1', 'reading-1'))
    unmount()
    mount(<AuthoringSession><LessonReadingsSection lessonId="lesson-1" lessonStatus="ARCHIVED" active/></AuthoringSession>)
    expect(await screen.findByLabelText('Nội dung tiếng Trung')).toBeDisabled()
    expect(screen.queryByRole('button', { name: 'Lưu bài khóa' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Thêm bài khóa' })).not.toBeInTheDocument()
  })
})
