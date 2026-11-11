import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getCurriculum, getHskLevels } from '../curriculum/api'
import { getHskProgress, getProgressOverview } from '../progress/api'
import * as api from './api'
import { PronunciationPage } from './PronunciationPage'
import { HskCurriculumPage } from '../curriculum/HskCurriculumPage'
import { getDashboard } from '../dashboard/api'
import { PronunciationLessonPage, PronunciationSectionPage } from './PronunciationLessonPage'

vi.mock('./api', () => ({ getPronunciationLesson: vi.fn(), advancePronunciation: vi.fn(), completeSection: vi.fn(), finishPronunciationLesson: vi.fn() }))
vi.mock('../curriculum/api', () => ({ getHskLevels: vi.fn(), getCurriculum: vi.fn() }))
vi.mock('../progress/api', () => ({ getHskProgress: vi.fn(), getProgressOverview: vi.fn() }))
vi.mock('../dashboard/api', () => ({ getDashboard: vi.fn() }))

const initial: api.PronunciationLessonState = {
  sections: [
    { id: 'initials-id', code: 'INITIALS', completed_at: null, total_steps: 21 },
    { id: 'finals-id', code: 'FINALS', completed_at: null, total_steps: 36 },
    { id: 'tones-id', code: 'TONES', completed_at: null, total_steps: 5 },
    { id: 'sandhi-id', code: 'SANDHI', completed_at: null, total_steps: 12 },
  ],
  current_section: 'INITIALS', step_index: 0, total_steps: 21, completed_at: null, can_finish: false,
}

function setup(path = '/pronunciation') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  const router = createMemoryRouter([
    { path: '/pronunciation', element: <PronunciationPage /> },
    { path: '/hsk/:hskLevel', element: <HskCurriculumPage /> },
    { path: '/pronunciation/lesson', element: <PronunciationLessonPage /> },
    { path: '/pronunciation/lesson/:sectionSlug', element: <PronunciationSectionPage /> },
  ], { initialEntries: [path] })
  return { ...render(<QueryClientProvider client={client}><RouterProvider router={router} /></QueryClientProvider>), client, router }
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(getDashboard).mockResolvedValue({ current_hsk: null, current_unit: null, current_lesson: null, progress_percentage: 0, continue_learning: null })
  vi.mocked(api.getPronunciationLesson).mockResolvedValue(initial)
  vi.mocked(getHskLevels).mockResolvedValue([{ id: 'hsk-1', level_number: 1, title: 'HSK 1', description: null, state: 'LOCKED' }])
  vi.mocked(getProgressOverview).mockResolvedValue({ current_hsk: 1, progress_percentage: 37.25, pronunciation_complete: false, hsk_levels: [] })
  vi.mocked(getHskProgress).mockResolvedValue({ hsk: { id: 'hsk-1', level_number: 1, title: 'HSK 1' }, progress_percentage: 12, units: [] })
  vi.mocked(getCurriculum).mockResolvedValue({ hsk: { id: 'hsk-1', level_number: 1, title: 'HSK 1' }, units: [] })
})

describe('server-owned pronunciation lesson', () => {
  it('navigates between the current and completed sections from the compact index without saving review steps', async () => {
    vi.mocked(api.getPronunciationLesson).mockResolvedValue({ ...initial, current_section: 'FINALS', total_steps: 36, sections: initial.sections.map(section => section.code === 'INITIALS' ? { ...section, completed_at: '2026-11-07T00:00:00Z' } : section) })
    const { router } = setup('/pronunciation/lesson/van-mau')
    expect(await screen.findByRole('navigation', { name: 'Các phần phát âm' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Học vận mẫu' })).toHaveAttribute('aria-current', 'page')
    expect(screen.queryByRole('link', { name: 'Học thanh điệu' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('link', { name: 'Ôn thanh mẫu' }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/pronunciation/lesson/thanh-mau'))
    expect(await screen.findByText('b', { selector: '.pronunciation-session__symbol' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Tiếp theo' }))
    expect(await screen.findByText('p', { selector: '.pronunciation-session__symbol' })).toBeInTheDocument()
    expect(api.advancePronunciation).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('link', { name: 'Học vận mẫu' }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/pronunciation/lesson/van-mau'))
    expect(await screen.findByText('a', { selector: '.pronunciation-session__symbol' })).toBeInTheDocument()
  })

  it.each([2, 3])('allows direct HSK %i entry before pronunciation and earlier levels', async (number) => {
    vi.mocked(getHskLevels).mockResolvedValue([1, 2, 3].map(value => ({ id: `hsk-${value}`, level_number: value, title: `HSK ${value}`, description: null, state: 'LOCKED' })))
    vi.mocked(getCurriculum).mockResolvedValue({ hsk: { id: `hsk-${number}`, level_number: number, title: `HSK ${number}` }, units: [{ id: 'advanced-unit', order_index: 1, unit_type: 'LESSON', state: 'AVAILABLE', lesson: { id: 'advanced-lesson', lesson_number: 1, title: 'Bài nâng cao', status: 'PUBLISHED' }, assessment: null }] })
    setup(`/hsk/${number}`)
    expect(await screen.findByRole('link', { name: 'Học Bài học 1: Bài nâng cao' })).toHaveAttribute('href', '/lessons/advanced-lesson')
    expect(screen.getByRole('link', { name: new RegExp(`^HSK ${number}`) })).toHaveAttribute('aria-current', 'page')
    expect(screen.queryByRole('button', { name: `Điều kiện mở HSK ${number}` })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Học phát âm nền tảng' })).toHaveAttribute('href', '/pronunciation/lesson')
    expect(api.advancePronunciation).not.toHaveBeenCalled()
  })

  it('keeps an empty HSK 3 selectable when pronunciation is unavailable', async () => {
    vi.mocked(getHskLevels).mockResolvedValue([1, 2, 3].map(value => ({ id: `hsk-${value}`, level_number: value, title: `HSK ${value}`, description: null, state: value === 1 ? 'LOCKED' : 'AVAILABLE' })))
    vi.mocked(api.getPronunciationLesson).mockRejectedValue(new Error('Unavailable'))
    vi.mocked(getCurriculum).mockResolvedValue({ hsk: { id: 'hsk-3', level_number: 3, title: 'HSK 3' }, units: [] })
    setup('/hsk/3')
    expect(await screen.findByRole('list', { name: 'Các bài trong cấp độ HSK' })).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /Sắp có nội dung/ })).toHaveLength(15)
    expect(screen.getByRole('link', { name: /^HSK 2/ })).toHaveAttribute('href', '/hsk/2')
    expect(screen.getByRole('link', { name: /^HSK 3/ })).toHaveAttribute('aria-current', 'page')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('uses full section blocks to navigate to separate pages and keeps future parts locked', async () => {
    const { router } = setup('/pronunciation/lesson')
    const block = await screen.findByRole('link', { name: 'Học thanh mẫu' })
    expect(block).toHaveAttribute('href', '/pronunciation/lesson/thanh-mau')
    expect(screen.queryByRole('link', { name: 'Học vận mẫu' })).not.toBeInTheDocument()
    expect(screen.queryByText('b', { selector: '.pronunciation-session__symbol' })).not.toBeInTheDocument()
    fireEvent.click(block)
    await waitFor(() => expect(router.state.location.pathname).toBe('/pronunciation/lesson/thanh-mau'))
    expect(await screen.findByText('b', { selector: '.pronunciation-session__symbol' })).toBeInTheDocument()
    expect(screen.queryByRole('list', { name: 'Các phần của bài học' })).not.toBeInTheDocument()
    await router.navigate(-1)
    await screen.findByRole('list', { name: 'Các phần của bài học' })
    expect(await screen.findByRole('link', { name: 'Học thanh mẫu' })).toBeInTheDocument()
    expect(api.advancePronunciation).not.toHaveBeenCalled()
  })

  it('does not expose exercises through direct URLs to locked or unknown parts', async () => {
    const { router } = setup('/pronunciation/lesson/van-mau')
    expect(await screen.findByRole('heading', { name: 'Phần học này chưa mở' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Tiếp theo' })).not.toBeInTheDocument()
    await router.navigate('/pronunciation/lesson/khong-co')
    expect(await screen.findByRole('heading', { name: 'Không tìm thấy phần phát âm' })).toBeInTheDocument()
    expect(api.advancePronunciation).not.toHaveBeenCalled()
  })
  it('offers the new sandhi section to earlier graduates without a redundant legacy banner', async () => {
    const state: api.PronunciationLessonState = { ...initial, current_section: 'SANDHI', total_steps: 12, completed_at: '2026-11-03T00:00:00Z', sections: initial.sections.map(row => row.code === 'SANDHI' ? row : { ...row, completed_at: '2026-11-03T00:00:00Z' }) }
    vi.mocked(api.getPronunciationLesson).mockResolvedValue(state)
    vi.mocked(api.advancePronunciation).mockResolvedValue({ ...state, step_index: 1 })
    setup('/pronunciation/lesson/bien-dieu')
    expect(await screen.findByText('ní hǎo')).toBeInTheDocument()
    expect(screen.queryByText(/quyền học HSK được giữ nguyên/)).not.toBeInTheDocument()
    expect(screen.getByText('ní hǎo')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Tiếp theo' }))
    await waitFor(() => expect(api.advancePronunciation).toHaveBeenCalledWith('SANDHI', 0))
    expect(await screen.findByText('老师')).toBeInTheDocument()
  })
  it('shows one pronunciation block and a locked HSK 1 without a self-complete action', async () => {
    setup()
    vi.mocked(getCurriculum).mockResolvedValue({ hsk: { id: 'hsk-1', level_number: 1, title: 'HSK 1' }, units: [{ id: 'unit-1', order_index: 1, unit_type: 'LESSON', state: 'AVAILABLE', lesson: { id: 'lesson-1', lesson_number: 1, title: 'Xin chào', status: 'PUBLISHED' }, assessment: null }] })
    expect(await screen.findByRole('link', { name: 'Học phát âm nền tảng' })).toHaveAttribute('href', '/pronunciation/lesson')
    fireEvent.click(await screen.findByRole('button', { name: 'Bài 1: Chưa mở' }))
    expect(screen.getByRole('status')).toHaveTextContent('Hoàn thành bài phát âm để mở HSK 1.')
    expect(screen.queryByRole('link', { name: 'Học Bài học 1: Xin chào' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Mark .* complete/ })).not.toBeInTheDocument()
  })

  it('shows the curriculum without the retired journey map or global progress panel', async () => {
    setup()
    expect(await screen.findByRole('link', { name: 'Học phát âm nền tảng' })).toBeInTheDocument()
    expect(screen.queryByText('37.25%')).not.toBeInTheDocument()
    expect(screen.queryByText('12%')).not.toBeInTheDocument()
    expect(document.querySelector('.wall-field-notes')).not.toBeInTheDocument()
    expect(getHskProgress).not.toHaveBeenCalled()
    expect(document.querySelector('.learning-hub__unit-details')).not.toBeInTheDocument()
  })

  it('allows completed material to be reviewed without altering saved progress', async () => {
    const doneSections = initial.sections.map((item) => ({ ...item, completed_at: '2026-11-03T00:00:00Z' }))
    vi.mocked(api.getPronunciationLesson).mockResolvedValue({ ...initial, sections: doneSections, current_section: null, step_index: 0, total_steps: 0, completed_at: '2026-11-03T00:00:00Z', can_finish: false })
    const { router } = setup('/pronunciation/lesson')
    fireEvent.click(await screen.findByRole('link', { name: 'Ôn thanh mẫu' }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/pronunciation/lesson/thanh-mau'))
    expect(await screen.findByText('b', { selector: '.pronunciation-session__symbol' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Tiếp theo' }))
    expect(screen.getByText('p', { selector: '.pronunciation-session__symbol' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Quay lại' }))
    expect(screen.getByText('b', { selector: '.pronunciation-session__symbol' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Quay lại' })).toBeDisabled()
    fireEvent.click(screen.getByRole('link', { name: '← Các phần phát âm' }))
    fireEvent.click(await screen.findByRole('link', { name: 'Ôn vận mẫu' }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/pronunciation/lesson/van-mau'))
    expect(screen.getByText('a', { selector: '.pronunciation-session__symbol' })).toBeInTheDocument()
    expect(api.advancePronunciation).not.toHaveBeenCalled()
    expect(api.completeSection).not.toHaveBeenCalled()
    expect(api.finishPronunciationLesson).not.toHaveBeenCalled()
  })

  it('shows HSK as available only when the backend reports it available', async () => {
    vi.mocked(api.getPronunciationLesson).mockResolvedValue({ ...initial, current_section: null, step_index: 0, total_steps: 0, completed_at: '2026-11-03T00:00:00Z', can_finish: false })
    vi.mocked(getHskLevels).mockResolvedValue([{ id: 'hsk-1', level_number: 1, title: 'HSK 1', description: null, state: 'AVAILABLE' }])
    setup()
    expect(await screen.findByRole('link', { name: /^HSK 1/ })).toHaveAttribute('href', '/hsk/1')
    expect(await screen.findByRole('link', { name: 'Ôn phát âm nền tảng' })).toBeInTheDocument()
  })

  it('resumes the step returned by the backend and advances one sound at a time', async () => {
    vi.mocked(api.getPronunciationLesson).mockResolvedValue({ ...initial, step_index: 1 })
    vi.mocked(api.advancePronunciation).mockResolvedValue({ ...initial, step_index: 2 })
    setup('/pronunciation/lesson/thanh-mau')
    expect(await screen.findByText('p', { selector: '.pronunciation-session__symbol' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Tiếp theo' }))
    await waitFor(() => expect(api.advancePronunciation).toHaveBeenCalledWith('INITIALS', 1))
    expect(await screen.findByText('m', { selector: '.pronunciation-session__symbol' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Hoàn thành thanh mẫu/ })).not.toBeInTheDocument()
  })

  it('goes back through visited sounds without changing saved progress', async () => {
    vi.mocked(api.getPronunciationLesson).mockResolvedValue({ ...initial, step_index: 2 })
    vi.mocked(api.advancePronunciation).mockResolvedValue({ ...initial, step_index: 3 })
    setup('/pronunciation/lesson/thanh-mau')
    expect(await screen.findByText('m', { selector: '.pronunciation-session__symbol' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Quay lại' }))
    expect(screen.getByText('p', { selector: '.pronunciation-session__symbol' })).toBeInTheDocument()
    expect(screen.getByRole('progressbar', { name: 'Tiến độ thanh mẫu' })).toHaveAttribute('value', '2')
    fireEvent.click(screen.getByRole('button', { name: 'Quay lại' }))
    expect(screen.getByText('b', { selector: '.pronunciation-session__symbol' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Quay lại' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Tiếp theo' }))
    fireEvent.click(screen.getByRole('button', { name: 'Tiếp theo' }))
    expect(api.advancePronunciation).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Tiếp theo' }))
    await waitFor(() => expect(api.advancePronunciation).toHaveBeenCalledWith('INITIALS', 2))
  })

  it('disables the next action while the backend is saving', async () => {
    let resolve!: (state: api.PronunciationLessonState) => void
    vi.mocked(api.advancePronunciation).mockReturnValueOnce(new Promise((done) => { resolve = done }))
    setup('/pronunciation/lesson/thanh-mau')
    fireEvent.click(await screen.findByRole('button', { name: 'Tiếp theo' }))
    expect(await screen.findByRole('button', { name: 'Đang lưu…' })).toBeDisabled()
    expect(api.advancePronunciation).toHaveBeenCalledTimes(1)
    resolve({ ...initial, step_index: 1 })
  })

  it('sends the backend section id only after all its sounds have been visited', async () => {
    const last = { ...initial, step_index: 21 }
    const next: api.PronunciationLessonState = { ...initial, current_section: 'FINALS', total_steps: 36, sections: initial.sections.map((item) => item.code === 'INITIALS' ? { ...item, completed_at: '2026-11-03T00:00:00Z' } : item) }
    vi.mocked(api.getPronunciationLesson).mockResolvedValueOnce(last).mockResolvedValue(next)
    vi.mocked(api.completeSection).mockResolvedValue({} as Awaited<ReturnType<typeof api.completeSection>>)
    const { router } = setup('/pronunciation/lesson/thanh-mau')
    fireEvent.click(await screen.findByRole('button', { name: 'Hoàn thành thanh mẫu' }))
    await waitFor(() => expect(api.completeSection).toHaveBeenCalledWith('initials-id', expect.any(Object)))
    await waitFor(() => expect(router.state.location.pathname).toBe('/pronunciation/lesson'))
    await waitFor(() => expect(screen.getByRole('link', { name: 'Học vận mẫu' })).toBeInTheDocument())
  })

  it('requires the separate final completion after the four sections', async () => {
    const doneSections = initial.sections.map((item) => ({ ...item, completed_at: '2026-11-03T00:00:00Z' }))
    vi.mocked(api.getPronunciationLesson).mockResolvedValue({ ...initial, sections: doneSections, current_section: null, step_index: 0, total_steps: 0, can_finish: true })
    setup('/pronunciation/lesson')
    expect(await screen.findByRole('button', { name: 'Hoàn thành bài học' })).toBeInTheDocument()
    expect(api.finishPronunciationLesson).not.toHaveBeenCalled()
  })

  it('shows a safe error and reloads the backend step when saving fails', async () => {
    vi.mocked(api.advancePronunciation).mockRejectedValueOnce(new Error('private details'))
    setup('/pronunciation/lesson/thanh-mau')
    fireEvent.click(await screen.findByRole('button', { name: 'Tiếp theo' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Không thể lưu bước học')
    await waitFor(() => expect(api.getPronunciationLesson).toHaveBeenCalledTimes(2))
    expect(screen.queryByText('private details')).not.toBeInTheDocument()
  })

  it('does not advance when the client and backend disagree on the curriculum length', async () => {
    vi.mocked(api.getPronunciationLesson).mockResolvedValue({ ...initial, total_steps: 20 })
    setup('/pronunciation/lesson/thanh-mau')
    expect(await screen.findByRole('alert')).toHaveTextContent('chưa đồng bộ với máy chủ')
    expect(screen.queryByRole('button', { name: 'Tiếp theo' })).not.toBeInTheDocument()
  })
})
