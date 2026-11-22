import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router'
import { beforeEach, expect, it, vi } from 'vitest'
import { VocabularyReviewPage } from './VocabularyReviewPage'
import { getReviewDeck, getReviewLessons } from './api'

vi.mock('./api', () => ({ getReviewDeck: vi.fn(), getReviewLessons: vi.fn() }))

const lessons = [
  { lesson_id: 'l1', hsk_level: 1, lesson_number: 1, title: 'Xin chào' },
  { lesson_id: 'l2', hsk_level: 1, lesson_number: 2, title: 'Cảm ơn' },
  { lesson_id: 'l3', hsk_level: 2, lesson_number: 1, title: 'Ngày mới' },
]

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(getReviewLessons).mockResolvedValue(lessons)
  vi.mocked(getReviewDeck).mockImplementation(async (page, _level, lessonId) => ({
    items: Array.from({ length: 50 }, (_, i) => ({ id: String(i), hanzi: lessonId ? '好' : '你', pinyin: 'nǐ', vietnamese_meaning: 'bạn', part_of_speech: null, lessons: [] })),
    total: 60, page, page_size: 50,
  }))
})

function setup() {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><VocabularyReviewPage/></MemoryRouter></QueryClientProvider>)
}

it('loads all completed lesson options, filters by HSK, and clears the lesson when HSK changes', async () => {
  setup()
  const selector = await screen.findByLabelText('Bài học')
  await screen.findByRole('option', { name: 'HSK 2 · Bài 1: Ngày mới' })
  fireEvent.change(selector, { target: { value: 'l3' } })
  await waitFor(() => expect(getReviewDeck).toHaveBeenLastCalledWith(1, undefined, 'l3'))
  fireEvent.change(screen.getByLabelText('Cấp độ HSK'), { target: { value: '1' } })
  await waitFor(() => expect(getReviewDeck).toHaveBeenLastCalledWith(1, 1, undefined))
  expect(selector).toHaveValue('')
  expect(within(selector).queryByRole('option', { name: /Ngày mới/ })).not.toBeInTheDocument()
  expect(within(selector).getByRole('option', { name: /Cảm ơn/ })).toBeInTheDocument()
})

it('resets pagination, card position and reveal state when choosing a lesson', async () => {
  setup()
  await screen.findByRole('button', { name: /Lật thẻ/ })
  fireEvent.click(screen.getByRole('button', { name: 'Bộ sau' }))
  await waitFor(() => expect(getReviewDeck).toHaveBeenLastCalledWith(2, undefined, undefined))
  fireEvent.click(await screen.findByRole('button', { name: /Lật thẻ/ }))
  expect(screen.getByRole('button', { name: /Ẩn phiên âm/ })).toHaveAttribute('aria-expanded', 'true')
  fireEvent.change(screen.getByLabelText('Bài học'), { target: { value: 'l1' } })
  await waitFor(() => expect(getReviewDeck).toHaveBeenLastCalledWith(1, undefined, 'l1'))
  expect(await screen.findByRole('button', { name: /Lật thẻ 好/ })).toHaveAttribute('aria-expanded', 'false')
  expect(screen.getByText('Thẻ 1 / 60')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Xóa bộ lọc' }))
  expect(screen.getByLabelText('Bài học')).toHaveValue('')
  expect(screen.getByLabelText('Cấp độ HSK')).toHaveValue('0')
})

it('offers recovery for an empty filtered deck', async () => {
  vi.mocked(getReviewDeck).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 })
  setup()
  fireEvent.change(screen.getByLabelText('Cấp độ HSK'), { target: { value: '3' } })
  await screen.findByRole('heading', { name: 'Chưa có từ trong lựa chọn này' })
  expect(screen.getByLabelText('Bài học')).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Xem tất cả từ đã học' }))
  await screen.findByRole('heading', { name: 'Bắt đầu từ một bài học' })
})

it('keeps HSK review available if lesson options fail to load', async () => {
  vi.mocked(getReviewLessons).mockRejectedValue(new Error('offline'))
  setup()
  await screen.findByRole('button', { name: 'Tải lại danh sách bài' })
  expect(screen.getByLabelText('Cấp độ HSK')).toBeEnabled()
  expect(screen.getByLabelText('Bài học')).toBeDisabled()
  expect(await screen.findByRole('button', { name: /Lật thẻ/ })).toBeInTheDocument()
})

it('hides the answer initially, flips the card and hides the next answer again', async () => {
  const origin = { lesson_id: 'l1', hsk_level: 1, lesson_number: 1, title: 'Xin chào', note: null }
  vi.mocked(getReviewDeck).mockResolvedValue({ total: 2, page: 1, page_size: 50, items: [
    { id: '1', hanzi: '你', pinyin: 'nǐ', vietnamese_meaning: 'bạn', part_of_speech: 'đại từ', lessons: [origin] },
    { id: '2', hanzi: '好', pinyin: 'hǎo', vietnamese_meaning: 'tốt', part_of_speech: 'tính từ', lessons: [origin] },
  ] })
  setup()
  const card = await screen.findByRole('button', { name: 'Lật thẻ 你 để xem phiên âm và nghĩa' })
  expect(screen.queryByText('nǐ')).not.toBeInTheDocument()
  fireEvent.click(card)
  expect(screen.getByText('nǐ')).toBeInTheDocument()
  expect(screen.getByText('bạn')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Tiếp theo →' }))
  expect(screen.getByRole('button', { name: 'Lật thẻ 好 để xem phiên âm và nghĩa' })).toBeInTheDocument()
  expect(screen.queryByText('hǎo')).not.toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Cấp độ HSK'), { target: { value: '2' } })
  await waitFor(() => expect(getReviewDeck).toHaveBeenLastCalledWith(1, 2, undefined))
})

it('explains how completed lessons unlock the empty review deck', async () => {
  vi.mocked(getReviewDeck).mockResolvedValue({ total: 0, page: 1, page_size: 50, items: [] })
  setup()
  expect(await screen.findByRole('heading', { name: 'Bắt đầu từ một bài học' })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Về giáo trình' })).toHaveAttribute('href', '/pronunciation')
})
