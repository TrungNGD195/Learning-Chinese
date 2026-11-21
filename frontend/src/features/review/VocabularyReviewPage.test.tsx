import { fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router'
import { beforeEach, expect, it, vi } from 'vitest'
import { getReviewDeck } from './api'
import { VocabularyReviewPage } from './VocabularyReviewPage'

vi.mock('./api', () => ({ getReviewDeck: vi.fn() }))
const origin = { lesson_id: 'lesson-1', hsk_level: 1, lesson_number: 1, title: 'Xin chào', note: null }
const words = [
  { id: '1', hanzi: '你', pinyin: 'nǐ', vietnamese_meaning: 'bạn', part_of_speech: 'đại từ', lessons: [origin] },
  { id: '2', hanzi: '好', pinyin: 'hǎo', vietnamese_meaning: 'tốt', part_of_speech: 'tính từ', lessons: [origin] },
]
function mount() {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><VocabularyReviewPage/></MemoryRouter></QueryClientProvider>)
}
beforeEach(() => vi.resetAllMocks())
it('hides the answer initially, flips the card and hides the next answer again', async () => {
  vi.mocked(getReviewDeck).mockResolvedValue({ total: 2, page: 1, page_size: 50, items: words })
  mount()
  const card = await screen.findByRole('button', { name: 'Lật thẻ 你 để xem phiên âm và nghĩa' })
  expect(screen.queryByText('nǐ')).not.toBeInTheDocument()
  fireEvent.click(card)
  expect(screen.getByText('nǐ')).toBeInTheDocument()
  expect(screen.getByText('bạn')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Tiếp theo →' }))
  expect(screen.getByRole('button', { name: 'Lật thẻ 好 để xem phiên âm và nghĩa' })).toBeInTheDocument()
  expect(screen.queryByText('hǎo')).not.toBeInTheDocument()
  fireEvent.change(screen.getByRole('combobox'), { target: { value: '2' } })
  expect(getReviewDeck).toHaveBeenLastCalledWith(1, 2)
})
it('explains how completed lessons unlock the empty review deck', async () => {
  vi.mocked(getReviewDeck).mockResolvedValue({ total: 0, page: 1, page_size: 50, items: [] })
  mount()
  expect(await screen.findByRole('heading', { name: 'Bắt đầu từ một bài học' })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Về giáo trình' })).toHaveAttribute('href', '/pronunciation')
})
