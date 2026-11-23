import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router'
import { beforeEach, expect, it, vi } from 'vitest'
import { VocabularyReviewPage } from './VocabularyReviewPage'
import { getReviewDeck, getReviewLessons, getReviewProgress, setReviewPreference, setReviewState } from './api'

vi.mock('./api', () => ({ getReviewDeck: vi.fn(), getReviewLessons: vi.fn(), getReviewProgress: vi.fn(), setReviewPreference: vi.fn(), setReviewState: vi.fn() }))

const lessons = [
  { lesson_id: 'l1', hsk_level: 1, lesson_number: 1, title: 'Xin chào' },
  { lesson_id: 'l2', hsk_level: 1, lesson_number: 2, title: 'Cảm ơn' },
  { lesson_id: 'l3', hsk_level: 2, lesson_number: 1, title: 'Ngày mới' },
]
const origin = { lesson_id: 'l1', hsk_level: 1, lesson_number: 1, title: 'Xin chào', note: null }
const cards = [
  { id: '0', hanzi: '你', pinyin: 'nǐ', vietnamese_meaning: 'bạn', part_of_speech: 'đại từ', lessons: [origin] },
  { id: '1', hanzi: '好', pinyin: 'hǎo', vietnamese_meaning: 'tốt', part_of_speech: 'tính từ', lessons: [origin] },
  { id: '2', hanzi: '我', pinyin: 'wǒ', vietnamese_meaning: 'tôi', part_of_speech: 'đại từ', lessons: [origin] },
]
let tracking: boolean
let states: Awaited<ReturnType<typeof getReviewProgress>>['cards']

beforeEach(() => {
  vi.clearAllMocks()
  tracking = true
  states = []
  vi.mocked(getReviewLessons).mockResolvedValue(lessons)
  vi.mocked(getReviewDeck).mockImplementation(async page => ({ items: cards, total: 3, page, page_size: 50 }))
  vi.mocked(getReviewProgress).mockImplementation(async () => ({ tracking_enabled: tracking, total: 3,
    known: states.filter(row => row.status === 'KNOWN').length, learning: states.filter(row => row.status === 'LEARNING').length,
    unseen: 3-states.filter(row => row.status !== null).length, cards: states }))
  vi.mocked(setReviewPreference).mockImplementation(async enabled => { tracking = enabled; return { tracking_enabled: enabled } })
  vi.mocked(setReviewState).mockImplementation(async (cardId, status, version) => {
    const row = { card_id: cardId, status, version: version+1 }
    states = [...states.filter(card => card.card_id !== cardId), row]
    return row
  })
})

function setup() {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><VocabularyReviewPage/></MemoryRouter></QueryClientProvider>)
}
async function start() {
  const button = await screen.findByRole('button', { name: 'Bắt đầu ôn' })
  await waitFor(() => expect(button).toBeEnabled())
  fireEvent.click(button)
  await screen.findByRole('button', { name: /Lật thẻ/ })
  await waitFor(() => expect(screen.getByRole('switch', { name: 'Theo dõi tiến độ' })).toBeEnabled())
}
async function key(key: string, position: number, total = 3) {
  fireEvent.keyDown(window, { key })
  await screen.findByText(`Thẻ ${position} / ${total}`)
  await waitFor(() => expect(screen.getByRole('switch', { name: 'Theo dõi tiến độ' })).toBeEnabled())
}

it('shows only the selection screen until explicitly confirmed, and keeps arrows inert there', async () => {
  setup()
  await screen.findByText('thẻ trong bộ ôn', { exact: false })
  expect(screen.queryByRole('button', { name: /Lật thẻ/ })).not.toBeInTheDocument()
  expect(getReviewProgress).not.toHaveBeenCalled()
  fireEvent.keyDown(window, { key: 'ArrowRight' })
  expect(setReviewState).not.toHaveBeenCalled()
  await start()
  expect(screen.queryByLabelText('Cấp độ HSK')).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /Tiếp theo|Quay lại|Bộ trước|Bộ sau/ })).not.toBeInTheDocument()
})

it('filters by HSK, clears an incompatible lesson, and starts only the confirmed selection', async () => {
  setup()
  const selector = await screen.findByLabelText('Bài học')
  await screen.findByRole('option', { name: 'HSK 2 · Bài 1: Ngày mới' })
  fireEvent.change(selector, { target: { value: 'l3' } })
  await waitFor(() => expect(getReviewDeck).toHaveBeenLastCalledWith(1, undefined, 'l3'))
  fireEvent.change(screen.getByLabelText('Cấp độ HSK'), { target: { value: '1' } })
  await waitFor(() => expect(getReviewDeck).toHaveBeenLastCalledWith(1, 1, undefined))
  expect(selector).toHaveValue('')
  expect(within(selector).queryByRole('option', { name: /Ngày mới/ })).not.toBeInTheDocument()
  fireEvent.change(selector, { target: { value: 'l2' } })
  await waitFor(() => expect(getReviewDeck).toHaveBeenLastCalledWith(1, 1, 'l2'))
  await start()
  expect(getReviewProgress).toHaveBeenLastCalledWith(1, 'l2')
  expect(screen.getByText('HSK 1 · Bài 2: Cảm ơn')).toBeInTheDocument()
})

it('returns to selection without displaying cards and requires confirmation again', async () => {
  setup(); await start()
  await key('ArrowRight', 2)
  fireEvent.click(screen.getByRole('button', { name: 'Đổi bài ôn' }))
  expect(screen.getByLabelText('Bài học')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /Lật thẻ/ })).not.toBeInTheDocument()
  await start()
  expect(screen.getByText('Thẻ 1 / 3')).toBeInTheDocument()
  expect(screen.getByRole('progressbar', { name: 'Số từ đã nhớ' })).toHaveAttribute('value', '1')
})

it('offers recovery and disables confirmation for an empty deck', async () => {
  vi.mocked(getReviewDeck).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 })
  setup()
  fireEvent.change(screen.getByLabelText('Cấp độ HSK'), { target: { value: '3' } })
  await screen.findByRole('heading', { name: 'Chưa có từ trong lựa chọn này' })
  expect(screen.getByRole('button', { name: 'Bắt đầu ôn' })).toBeDisabled()
  expect(screen.getByLabelText('Bài học')).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Xem tất cả từ đã học' }))
  await screen.findByRole('heading', { name: 'Bắt đầu từ một bài học' })
  expect(screen.getByRole('link', { name: 'Về giáo trình' })).toHaveAttribute('href', '/pronunciation')
})

it('keeps HSK review available if lesson options fail to load', async () => {
  vi.mocked(getReviewLessons).mockRejectedValue(new Error('offline'))
  setup()
  await screen.findByRole('button', { name: 'Tải lại danh sách bài' })
  expect(screen.getByLabelText('Cấp độ HSK')).toBeEnabled()
  expect(screen.getByLabelText('Bài học')).toBeDisabled()
  await start()
  expect(screen.getByRole('button', { name: /Lật thẻ/ })).toBeInTheDocument()
})

it('flips using up/down without rating, and hides the next answer after a right-arrow rating', async () => {
  setup(); await start()
  expect(screen.getByText('nǐ').closest('[aria-hidden]')).toHaveAttribute('aria-hidden', 'true')
  fireEvent.keyDown(window, { key: 'ArrowUp' })
  expect(screen.getByRole('button', { name: 'Lật về mặt chữ Hán' })).toHaveAccessibleDescription('nǐ bạn')
  fireEvent.keyDown(window, { key: 'ArrowDown' })
  expect(screen.getByRole('button', { name: /Lật thẻ 你/ })).toHaveAttribute('aria-pressed', 'false')
  expect(setReviewState).not.toHaveBeenCalled()
  await key('ArrowRight', 2)
  expect(setReviewState).toHaveBeenLastCalledWith('0', 'KNOWN', 0)
  expect(screen.getByText('hǎo').closest('[aria-hidden]')).toHaveAttribute('aria-hidden', 'true')
})

it('marks left as not known, advances, and undoes the rating to the same card', async () => {
  setup(); await start()
  await key('ArrowLeft', 2)
  expect(setReviewState).toHaveBeenLastCalledWith('0', 'LEARNING', 0)
  fireEvent.click(screen.getByRole('button', { name: 'Hoàn tác đánh giá vừa rồi' }))
  await screen.findByText('Thẻ 1 / 3')
  expect(setReviewState).toHaveBeenLastCalledWith('0', null, 1)
  expect(screen.getByRole('button', { name: 'Lật về mặt chữ Hán' })).toBeInTheDocument()
})

it('does not submit repeated, modified or overlapping keys while saving', async () => {
  let resolve!: (value: Awaited<ReturnType<typeof setReviewState>>) => void
  vi.mocked(setReviewState).mockReturnValueOnce(new Promise(done => { resolve = done }))
  setup(); await start()
  fireEvent.keyDown(window, { key: 'ArrowRight', repeat: true })
  fireEvent.keyDown(window, { key: 'ArrowRight', ctrlKey: true })
  fireEvent.keyDown(screen.getByRole('heading', { name: 'Ôn từ vựng' }), { key: 'ArrowRight' })
  expect(setReviewState).not.toHaveBeenCalled()
  fireEvent.keyDown(window, { key: 'ArrowRight' })
  fireEvent.keyDown(window, { key: 'ArrowLeft' })
  fireEvent.keyDown(window, { key: 'ArrowRight' })
  expect(setReviewState).toHaveBeenCalledTimes(1)
  expect(screen.getByText('Thẻ 1 / 3')).toBeInTheDocument()
  await act(async () => resolve({ card_id: '0', status: 'KNOWN', version: 1 }))
  await screen.findByText('Thẻ 2 / 3')
})

it('does not advance or show a successful rating when saving fails', async () => {
  vi.mocked(setReviewState).mockRejectedValueOnce(new Error('offline'))
  setup(); await start()
  fireEvent.keyDown(window, { key: 'ArrowLeft' })
  expect(await screen.findByText(/Chưa xác nhận được thay đổi/)).toBeInTheDocument()
  expect(screen.getByText('Thẻ 1 / 3')).toBeInTheDocument()
  expect(screen.queryByText('Chưa nhớ: 你')).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Hoàn tác đánh giá vừa rồi' })).toBeDisabled()
})

it('keeps keyboard actions locked until the saved card has finished leaving', async () => {
  const descriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'animate')
  let finish!: () => void
  const animate = vi.fn().mockReturnValueOnce({ finished: new Promise<void>(resolve => { finish = resolve }), cancel: vi.fn() })
    .mockImplementation(() => ({ finished: Promise.resolve(), cancel: vi.fn() }))
  Object.defineProperty(HTMLElement.prototype, 'animate', { configurable: true, value: animate })
  try {
    setup(); await start()
    fireEvent.keyDown(window, { key: 'ArrowRight' })
    await waitFor(() => expect(animate).toHaveBeenCalledTimes(1))
    expect(setReviewState).toHaveBeenCalledTimes(1)
    expect(screen.getByText('Thẻ 1 / 3')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Đổi bài ôn' })).toBeDisabled()
    fireEvent.keyDown(window, { key: 'ArrowLeft' })
    expect(setReviewState).toHaveBeenCalledTimes(1)
    await act(async () => finish())
    await screen.findByText('Thẻ 2 / 3')
    await waitFor(() => expect(screen.getByRole('button', { name: 'Đã nhớ' })).toBeEnabled())
  } finally {
    if (descriptor) Object.defineProperty(HTMLElement.prototype, 'animate', descriptor)
    else Reflect.deleteProperty(HTMLElement.prototype, 'animate')
  }
})

it('starts the toss immediately while saving and advances without a progress refetch', async () => {
  const descriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'animate')
  const animate = vi.fn(() => ({ finished: Promise.resolve(), cancel: vi.fn() }))
  Object.defineProperty(HTMLElement.prototype, 'animate', { configurable: true, value: animate })
  let resolve!: (value: Awaited<ReturnType<typeof setReviewState>>) => void
  vi.mocked(setReviewState).mockReturnValueOnce(new Promise(done => { resolve = done }))
  try {
    setup(); await start()
    const reads = vi.mocked(getReviewProgress).mock.calls.length
    fireEvent.keyDown(window, { key: 'ArrowRight' })
    expect(animate).toHaveBeenCalledTimes(1)
    expect(setReviewState).toHaveBeenCalledTimes(1)
    expect(screen.getByText('Thẻ 1 / 3')).toBeInTheDocument()
    await act(async () => resolve({ card_id: '0', status: 'KNOWN', version: 1 }))
    await screen.findByText('Thẻ 2 / 3')
    expect(getReviewProgress).toHaveBeenCalledTimes(reads)
    expect(screen.getByRole('progressbar', { name: 'Số từ đã nhớ' })).toHaveAttribute('value', '1')
  } finally {
    if (descriptor) Object.defineProperty(HTMLElement.prototype, 'animate', descriptor)
    else Reflect.deleteProperty(HTMLElement.prototype, 'animate')
  }
})

it.each([{ key: 'ArrowRight', sign: 1 }, { key: 'ArrowLeft', sign: -1 }])('tosses $key diagonally in the correct direction', async ({ key: arrow, sign }) => {
  const descriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'animate')
  const animate = vi.fn(() => ({ finished: Promise.resolve(), cancel: vi.fn() }))
  Object.defineProperty(HTMLElement.prototype, 'animate', { configurable: true, value: animate })
  try {
    setup(); await start()
    const card = screen.getByRole('button', { name: /Lật thẻ/ })
    Object.defineProperties(card, { clientWidth: { value: 800 }, clientHeight: { value: 380 } })
    await key(arrow, 2)
    const call = vi.mocked(animate).mock.calls[0] as unknown as [Keyframe[], KeyframeAnimationOptions]
    const [, x, y] = String(call[0].at(-1)?.transform).match(/translate3d\((-?[\d.]+)px,(-?[\d.]+)px/)!
    expect(Number(x) * sign).toBeGreaterThan(0)
    expect(Number(y) * sign).toBeLessThan(0)
    expect(call[1].duration).toBe(150)
  } finally {
    if (descriptor) Object.defineProperty(HTMLElement.prototype, 'animate', descriptor)
    else Reflect.deleteProperty(HTMLElement.prototype, 'animate')
  }
})

it('returns the tossed card to its original position if saving fails', async () => {
  const descriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'animate')
  const animate = vi.fn(() => ({ finished: Promise.resolve(), cancel: vi.fn() }))
  Object.defineProperty(HTMLElement.prototype, 'animate', { configurable: true, value: animate })
  vi.mocked(setReviewState).mockRejectedValueOnce(new Error('offline'))
  try {
    setup(); await start()
    fireEvent.keyDown(window, { key: 'ArrowLeft' })
    await screen.findByText(/Chưa xác nhận được thay đổi/)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Chưa nhớ' })).toBeEnabled())
    expect(screen.getByText('Thẻ 1 / 3')).toBeInTheDocument()
    expect(animate).toHaveBeenCalledTimes(2)
    const call = vi.mocked(animate).mock.calls[1] as unknown as [Keyframe[]]
    expect(call[0].at(-1)).toEqual({ transform: 'translate3d(0,0,0) rotate(0deg) scale(1)', opacity: 1 })
    expect(screen.getByRole('button', { name: 'Hoàn tác đánh giá vừa rồi' })).toBeDisabled()
  } finally {
    if (descriptor) Object.defineProperty(HTMLElement.prototype, 'animate', descriptor)
    else Reflect.deleteProperty(HTMLElement.prototype, 'animate')
  }
})

it('turns tracking off without deleting ratings and browses without new writes', async () => {
  states = [{ card_id: '2', status: 'KNOWN', version: 1 }]
  setup(); await start()
  const toggle = screen.getByRole('switch', { name: 'Theo dõi tiến độ' })
  fireEvent.click(toggle)
  await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', 'false'))
  await waitFor(() => expect(toggle).toBeEnabled())
  await key('ArrowRight', 2)
  await key('ArrowLeft', 1)
  expect(setReviewState).not.toHaveBeenCalled()
  fireEvent.click(toggle)
  await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', 'true'))
  expect(screen.getByRole('progressbar', { name: 'Số từ đã nhớ' })).toHaveAttribute('value', '1')
})

it('finishes the round, supports undoing the final card, and can restart', async () => {
  setup(); await start()
  await key('ArrowRight', 2)
  await key('ArrowLeft', 3)
  fireEvent.keyDown(window, { key: 'ArrowRight' })
  await screen.findByRole('heading', { name: 'Bạn đã đi hết bộ thẻ!' })
  await waitFor(() => expect(screen.getByRole('button', { name: 'Hoàn tác đánh giá vừa rồi' })).toBeEnabled())
  fireEvent.click(screen.getByRole('button', { name: 'Hoàn tác đánh giá vừa rồi' }))
  await screen.findByText('Thẻ 3 / 3')
  await waitFor(() => expect(screen.getByRole('button', { name: 'Đã nhớ' })).toBeEnabled())
  fireEvent.click(screen.getByRole('button', { name: 'Đã nhớ' }))
  await screen.findByRole('heading', { name: 'Bạn đã đi hết bộ thẻ!' })
  await waitFor(() => expect(screen.getByRole('button', { name: 'Học lại bộ thẻ' })).toBeEnabled())
  fireEvent.click(screen.getByRole('button', { name: 'Học lại bộ thẻ' }))
  await screen.findByText('Thẻ 1 / 3')
  expect(screen.getByRole('button', { name: /Lật thẻ 你/ })).toHaveAttribute('aria-pressed', 'false')
})

it('automatically crosses data pages with the same shuffle seed, without batch navigation', async () => {
  tracking = false
  vi.mocked(getReviewDeck).mockImplementation(async page => ({ total: 51, page, page_size: 50,
    items: Array.from({ length: page === 1 ? 50 : 1 }, (_, i) => ({ ...cards[0], id: String((page-1)*50+i) })) }))
  setup(); await start()
  fireEvent.click(screen.getByRole('button', { name: 'Trộn thẻ' }))
  await waitFor(() => expect(getReviewDeck).toHaveBeenLastCalledWith(1, undefined, undefined, expect.any(String)))
  const seed = vi.mocked(getReviewDeck).mock.lastCall![3]
  await waitFor(() => expect(screen.getByRole('button', { name: 'Thẻ kế' })).toBeEnabled())
  for (let i = 2; i <= 51; i++) await key('ArrowRight', i, 51)
  expect(getReviewDeck).toHaveBeenCalledWith(2, undefined, undefined, seed)
  expect(screen.queryByRole('button', { name: /Bộ trước|Bộ sau/ })).not.toBeInTheDocument()
  await key('ArrowLeft', 50, 51)
  expect(setReviewState).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Tắt trộn thẻ' }))
  await screen.findByText('Thẻ 1 / 51')
  await waitFor(() => expect(getReviewDeck).toHaveBeenLastCalledWith(1, undefined, undefined))
})
