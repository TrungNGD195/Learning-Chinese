import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createMemoryRouter, Link, RouterProvider } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { queryKeys } from '../../app/query/keys'
import { ApiError } from '../../lib/api/errors'
import { getDashboard } from '../dashboard/api'
import { DashboardPage } from '../dashboard/DashboardPage'
import * as api from './api'
import { PronunciationPage } from './PronunciationPage'

vi.mock('./api', () => ({ getSections: vi.fn(), completeSection: vi.fn() }))
vi.mock('../dashboard/api', () => ({ getDashboard: vi.fn() }))

const initialSections = [
  { id: 'section-tones-id', code: 'TONES', title: 'Tones', description: null, order_index: 1, completed_at: null },
  { id: 'section-initials-id', code: 'INITIALS', title: 'Initials', description: null, order_index: 2, completed_at: null },
  { id: 'section-finals-id', code: 'FINALS', title: 'Finals', description: null, order_index: 3, completed_at: null },
]

function setup(path = '/pronunciation') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  const router = createMemoryRouter([
    { path: '/pronunciation', element: <><PronunciationPage /><Link to="/dashboard">Dashboard</Link></> },
    { path: '/dashboard', element: <DashboardPage /> },
  ], { initialEntries: [path] })
  const view = render(<QueryClientProvider client={client}><RouterProvider router={router} /></QueryClientProvider>)
  return { ...view, client, router }
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(api.getSections).mockResolvedValue(initialSections)
  vi.mocked(api.completeSection).mockResolvedValue({} as Awaited<ReturnType<typeof api.completeSection>>)
})

describe('Step 8.1 B1 pronunciation completion', () => {
  it('loads canonical sections and makes every incomplete section actionable', async () => {
    setup()
    expect(await screen.findByRole('button', { name: 'Mark Tones complete' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Mark Initials complete' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Mark Finals complete' })).toBeInTheDocument()
    expect(api.getSections).toHaveBeenCalledTimes(1)
  })

  it('posts the canonical backend section id when the learner marks a section complete', async () => {
    setup()
    fireEvent.click(await screen.findByRole('button', { name: 'Mark Tones complete' }))
    await waitFor(() => expect(api.completeSection).toHaveBeenCalledWith('section-tones-id', expect.any(Object)))
  })

  it('disables all completion actions while one request is pending', async () => {
    let resolve!: (value: Awaited<ReturnType<typeof api.completeSection>>) => void
    vi.mocked(api.completeSection).mockReturnValueOnce(new Promise((done) => { resolve = done }))
    setup()
    const tones = await screen.findByRole('button', { name: 'Mark Tones complete' })
    fireEvent.click(tones)
    expect(await screen.findByRole('button', { name: 'Completing…' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Mark Initials complete' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Completing…' }))
    expect(api.completeSection).toHaveBeenCalledTimes(1)
    resolve({} as Awaited<ReturnType<typeof api.completeSection>>)
  })

  it('surfaces a safe error and keeps the backend section incomplete after failure', async () => {
    vi.mocked(api.completeSection).mockRejectedValueOnce(new ApiError({
      status: 503, code: 'HTTP_ERROR', message: 'private server details', details: null,
    }))
    setup()
    fireEvent.click(await screen.findByRole('button', { name: 'Mark Tones complete' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('A temporary problem prevented completion. Please try again.')
    expect(screen.queryByText('Completed')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Mark Tones complete' })).toBeEnabled()
  })

  it('refetches completion state and invalidates backend-owned progression reads', async () => {
    let canonical = initialSections
    vi.mocked(api.getSections).mockImplementation(async () => canonical)
    vi.mocked(api.completeSection).mockImplementationOnce(async (id) => {
      canonical = canonical.map((section) => section.id === id ? { ...section, completed_at: '2026-10-13T00:00:00Z' } : section)
      return {} as Awaited<ReturnType<typeof api.completeSection>>
    })
    const { client } = setup()
    const invalidate = vi.spyOn(client, 'invalidateQueries')
    fireEvent.click(await screen.findByRole('button', { name: 'Mark Tones complete' }))
    expect(await screen.findByText('Completed')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Mark Tones complete' })).not.toBeInTheDocument()
    await waitFor(() => expect(api.getSections).toHaveBeenCalledTimes(2))
    expect(invalidate).toHaveBeenCalledWith({ queryKey: queryKeys.pronunciation })
    expect(invalidate).toHaveBeenCalledWith({ queryKey: queryKeys.dashboard })
    expect(invalidate).toHaveBeenCalledWith({ queryKey: queryKeys.curriculumLevels })
    expect(invalidate).toHaveBeenCalledWith({ queryKey: queryKeys.curriculumHskRoot })
    expect(invalidate).toHaveBeenCalledWith({ queryKey: queryKeys.progressOverview })
    expect(invalidate).toHaveBeenCalledWith({ queryKey: queryKeys.progressHskRoot })
  })

  it('shows persisted completion after a fresh mount from the canonical GET response', async () => {
    vi.mocked(api.getSections).mockResolvedValueOnce(initialSections).mockResolvedValueOnce([
      { ...initialSections[0], completed_at: '2026-10-13T00:00:00Z' }, ...initialSections.slice(1),
    ])
    const first = setup()
    expect(await screen.findByRole('button', { name: 'Mark Tones complete' })).toBeInTheDocument()
    first.unmount()
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const router = createMemoryRouter([{ path: '/pronunciation', element: <PronunciationPage /> }], { initialEntries: ['/pronunciation'] })
    render(<QueryClientProvider client={client}><RouterProvider router={router} /></QueryClientProvider>)
    expect(await screen.findByText('Completed')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Mark Tones complete' })).not.toBeInTheDocument()
  })

  it('renders HSK availability from the backend Dashboard read after completion', async () => {
    let canonical = initialSections
    vi.mocked(api.getSections).mockImplementation(async () => canonical)
    vi.mocked(api.completeSection).mockImplementation(async (id) => {
      canonical = canonical.map((section) => ({ ...section, completed_at: section.id === id ? '2026-10-13T00:00:00Z' : section.completed_at }))
      return {} as Awaited<ReturnType<typeof api.completeSection>>
    })
    vi.mocked(getDashboard).mockResolvedValue({
      current_hsk: { id: 'hsk-1', level_number: 1, title: 'HSK 1' },
      current_unit: { id: 'unit-1', order_index: 1, unit_type: 'LESSON', state: 'AVAILABLE', lesson: { id: 'lesson-1', lesson_number: 1, title: 'Lesson One', status: 'PUBLISHED' }, assessment: null },
      current_lesson: { id: 'lesson-1', lesson_number: 1, title: 'Lesson One', description: null },
      progress_percentage: 0, continue_learning: { type: 'LESSON', section_id: null, code: null, lesson_id: 'lesson-1', assessment_id: null },
    })
    const { router } = setup()
    for (const label of ['Tones', 'Initials', 'Finals']) {
      fireEvent.click(await screen.findByRole('button', { name: `Mark ${label} complete` }))
      await screen.findByText(`${label} marked complete.`)
    }
    await router.navigate('/dashboard')
    expect(await screen.findByText('Lesson · AVAILABLE')).toBeInTheDocument()
    expect(getDashboard).toHaveBeenCalledTimes(1)
  })
})
