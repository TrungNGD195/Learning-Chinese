import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getHskLevels } from '../curriculum/api'
import { getHskProgress, getProgressOverview } from '../progress/api'
import * as api from './api'
import { PronunciationPage } from './PronunciationPage'
import { PronunciationLessonPage } from './PronunciationLessonPage'

vi.mock('./api', () => ({ getPronunciationLesson: vi.fn(), advancePronunciation: vi.fn(), completeSection: vi.fn(), finishPronunciationLesson: vi.fn() }))
vi.mock('../curriculum/api', () => ({ getHskLevels: vi.fn() }))
vi.mock('../progress/api', () => ({ getHskProgress: vi.fn(), getProgressOverview: vi.fn() }))

const initial: api.PronunciationLessonState = {
  sections: [
    { id: 'initials-id', code: 'INITIALS', completed_at: null, total_steps: 21 },
    { id: 'finals-id', code: 'FINALS', completed_at: null, total_steps: 36 },
    { id: 'tones-id', code: 'TONES', completed_at: null, total_steps: 5 },
  ],
  current_section: 'INITIALS', step_index: 0, total_steps: 21, completed_at: null, can_finish: false,
}

function setup(path = '/pronunciation') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  const router = createMemoryRouter([
    { path: '/pronunciation', element: <PronunciationPage /> },
    { path: '/pronunciation/lesson', element: <PronunciationLessonPage /> },
  ], { initialEntries: [path] })
  return { ...render(<QueryClientProvider client={client}><RouterProvider router={router} /></QueryClientProvider>), client, router }
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(api.getPronunciationLesson).mockResolvedValue(initial)
  vi.mocked(getHskLevels).mockResolvedValue([{ id: 'hsk-1', level_number: 1, title: 'HSK 1', description: null, state: 'LOCKED' }])
  vi.mocked(getProgressOverview).mockResolvedValue({ current_hsk: 1, progress_percentage: 37.25, pronunciation_complete: false, hsk_levels: [] })
  vi.mocked(getHskProgress).mockResolvedValue({ hsk: { id: 'hsk-1', level_number: 1, title: 'HSK 1' }, progress_percentage: 12, units: [] })
})

describe('server-owned pronunciation lesson', () => {
  it('shows one pronunciation block and a locked HSK 1 without a self-complete action', async () => {
    setup()
    expect(await screen.findByRole('link', { name: /Mở bài học/ })).toHaveAttribute('href', '/pronunciation/lesson')
    expect(screen.getByText('Hoàn thành bài phát âm để mở khóa.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Mở HSK 1/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Mark .* complete/ })).not.toBeInTheDocument()
  })

  it('shows the backend progress alongside the learning path', async () => {
    setup()
    expect(await screen.findByText('37.25%')).toBeInTheDocument()
    expect(await screen.findByText('12%')).toBeInTheDocument()
    expect(screen.getByText('Chi tiết bài học (0)')).toBeInTheDocument()
  })

  it('allows completed material to be reviewed without altering saved progress', async () => {
    const doneSections = initial.sections.map((item) => ({ ...item, completed_at: '2026-11-03T00:00:00Z' }))
    vi.mocked(api.getPronunciationLesson).mockResolvedValue({ ...initial, sections: doneSections, current_section: null, step_index: 0, total_steps: 0, completed_at: '2026-11-03T00:00:00Z', can_finish: false })
    setup('/pronunciation/lesson')
    fireEvent.click(await screen.findByRole('button', { name: 'Học lại từ đầu' }))
    expect(await screen.findByText('b', { selector: '.pronunciation-session__symbol' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Tiếp theo' }))
    expect(screen.getByText('p', { selector: '.pronunciation-session__symbol' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Quay lại' }))
    expect(screen.getByText('b', { selector: '.pronunciation-session__symbol' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Quay lại' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Ôn vận mẫu' }))
    expect(screen.getByText('a', { selector: '.pronunciation-session__symbol' })).toBeInTheDocument()
    expect(api.advancePronunciation).not.toHaveBeenCalled()
    expect(api.completeSection).not.toHaveBeenCalled()
    expect(api.finishPronunciationLesson).not.toHaveBeenCalled()
  })

  it('shows HSK as available only when the backend reports it available', async () => {
    vi.mocked(api.getPronunciationLesson).mockResolvedValue({ ...initial, current_section: null, step_index: 0, total_steps: 0, completed_at: '2026-11-03T00:00:00Z', can_finish: false })
    vi.mocked(getHskLevels).mockResolvedValue([{ id: 'hsk-1', level_number: 1, title: 'HSK 1', description: null, state: 'AVAILABLE' }])
    setup()
    expect(await screen.findByRole('link', { name: 'Mở HSK 1' })).toHaveAttribute('href', '/hsk/1')
  })

  it('resumes the step returned by the backend and advances one sound at a time', async () => {
    vi.mocked(api.getPronunciationLesson).mockResolvedValue({ ...initial, step_index: 1 })
    vi.mocked(api.advancePronunciation).mockResolvedValue({ ...initial, step_index: 2 })
    setup('/pronunciation/lesson')
    expect(await screen.findByText('p', { selector: '.pronunciation-session__symbol' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Tiếp theo' }))
    await waitFor(() => expect(api.advancePronunciation).toHaveBeenCalledWith('INITIALS', 1))
    expect(await screen.findByText('m', { selector: '.pronunciation-session__symbol' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Hoàn thành thanh mẫu/ })).not.toBeInTheDocument()
  })

  it('goes back through visited sounds without changing saved progress', async () => {
    vi.mocked(api.getPronunciationLesson).mockResolvedValue({ ...initial, step_index: 2 })
    vi.mocked(api.advancePronunciation).mockResolvedValue({ ...initial, step_index: 3 })
    setup('/pronunciation/lesson')
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
    setup('/pronunciation/lesson')
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
    setup('/pronunciation/lesson')
    fireEvent.click(await screen.findByRole('button', { name: 'Hoàn thành thanh mẫu' }))
    await waitFor(() => expect(api.completeSection).toHaveBeenCalledWith('initials-id', expect.any(Object)))
    expect(await screen.findByText('a', { selector: '.pronunciation-session__symbol' })).toBeInTheDocument()
  })

  it('requires the separate final completion after the three sections', async () => {
    const doneSections = initial.sections.map((item) => ({ ...item, completed_at: '2026-11-03T00:00:00Z' }))
    vi.mocked(api.getPronunciationLesson).mockResolvedValue({ ...initial, sections: doneSections, current_section: null, step_index: 0, total_steps: 0, can_finish: true })
    setup('/pronunciation/lesson')
    expect(await screen.findByRole('button', { name: 'Hoàn thành bài học' })).toBeInTheDocument()
    expect(api.finishPronunciationLesson).not.toHaveBeenCalled()
  })

  it('shows a safe error and reloads the backend step when saving fails', async () => {
    vi.mocked(api.advancePronunciation).mockRejectedValueOnce(new Error('private details'))
    setup('/pronunciation/lesson')
    fireEvent.click(await screen.findByRole('button', { name: 'Tiếp theo' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Không thể lưu bước học')
    await waitFor(() => expect(api.getPronunciationLesson).toHaveBeenCalledTimes(2))
    expect(screen.queryByText('private details')).not.toBeInTheDocument()
  })

  it('does not advance when the client and backend disagree on the curriculum length', async () => {
    vi.mocked(api.getPronunciationLesson).mockResolvedValue({ ...initial, total_steps: 20 })
    setup('/pronunciation/lesson')
    expect(await screen.findByRole('alert')).toHaveTextContent('chưa đồng bộ với máy chủ')
    expect(screen.queryByRole('button', { name: 'Tiếp theo' })).not.toBeInTheDocument()
  })
})
