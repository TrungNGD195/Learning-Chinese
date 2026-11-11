import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { StrokeOrder } from './StrokeOrder'
import { loadStrokeData } from './strokeData'

vi.mock('./strokeData', async original => ({ ...await original<typeof import('./strokeData')>(), loadStrokeData: vi.fn() }))
const data = { strokes: ['M0 0L200 0L200 50Z', 'M20 50L100 400L150 450Z'], medians: [[[0, 20], [200, 20]], [[50, 80], [120, 400]]] as [number, number][][] }
const players: { pause: ReturnType<typeof vi.fn>; play: ReturnType<typeof vi.fn>; cancel: ReturnType<typeof vi.fn>; onfinish: (() => void) | null }[] = []
let originalAnimate: PropertyDescriptor | undefined
let reduced = false
beforeEach(() => {
  vi.resetAllMocks(); players.length = 0; reduced = false
  vi.mocked(loadStrokeData).mockResolvedValue(data)
  vi.stubGlobal('matchMedia', () => ({ matches: reduced, addEventListener: vi.fn(), removeEventListener: vi.fn() }))
  originalAnimate = Object.getOwnPropertyDescriptor(Element.prototype, 'animate')
  Object.defineProperty(Element.prototype, 'animate', { configurable: true, value: vi.fn(() => {
    const player = { pause: vi.fn(), play: vi.fn(), cancel: vi.fn(), onfinish: null }
    players.push(player); return player
  }) })
})
afterEach(() => {
  vi.unstubAllGlobals()
  if (originalAnimate) Object.defineProperty(Element.prototype, 'animate', originalAnimate)
  else Reflect.deleteProperty(Element.prototype, 'animate')
})

describe('real stroke-sequence player controls', () => {
  it('can pause, inspect strokes, restart and change character without marking learner progress', async () => {
    const { container, unmount } = render(<StrokeOrder hanzi="你好"/>)
    const pause = await screen.findByRole('button', { name: 'Tạm dừng chữ 你' })
    await waitFor(() => expect(players[0].play).toHaveBeenCalled())
    fireEvent.click(pause)
    expect(players[0].pause).toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Nét tiếp theo của chữ 你' }))
    expect(screen.getByText('Đã viết 1 / 2 nét')).toBeInTheDocument()
    expect(container.querySelectorAll('.hanzi-stroke-active')).toHaveLength(2)
    fireEvent.click(screen.getByRole('button', { name: 'Nét tiếp theo của chữ 你' }))
    expect(screen.getByText('Đã viết đủ 2 / 2 nét')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Bắt đầu lại chữ 你' }))
    expect(screen.getByText('Đã viết 0 / 2 nét')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Chữ 好, vị trí 2' }))
    await waitFor(() => expect(loadStrokeData).toHaveBeenCalledWith('好'))
    expect(screen.getByRole('img', { name: /Thứ tự nét chữ 好/ })).toBeInTheDocument()
    unmount()
    expect(players.every(player => player.cancel.mock.calls.length)).toBe(true)
  })

  it('uses manual steps without autoplay for reduced motion', async () => {
    reduced = true
    render(<StrokeOrder hanzi="字"/>)
    await screen.findByText('Đã viết 0 / 2 nét')
    expect(players[0].play).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: /Tạm dừng/ })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Nét tiếp theo của chữ 字' }))
    expect(screen.getByText('Đã viết 1 / 2 nét')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Nét tiếp theo của chữ 字' }))
    expect(screen.getByText('Đã viết đủ 2 / 2 nét')).toBeInTheDocument()
  })

  it('advances the sequence only when each real animation finishes', async () => {
    render(<StrokeOrder hanzi="字"/>)
    await screen.findByText('Đã viết 0 / 2 nét')
    await act(async () => players.at(-1)!.onfinish?.())
    expect(screen.getByText('Đã viết 1 / 2 nét')).toBeInTheDocument()
    await act(async () => players.at(-1)!.onfinish?.())
    expect(screen.getByText('Đã viết đủ 2 / 2 nét')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Viết lại chữ 字' })).toBeInTheDocument()
  })

  it('keeps static Chinese visible when data is unavailable and retries network failures', async () => {
    vi.mocked(loadStrokeData).mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce(data)
    render(<StrokeOrder hanzi="字"/>)
    expect(await screen.findByText(/Chưa tải được thứ tự nét/)).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Thứ tự nét chữ 字' })).toHaveTextContent('字')
    fireEvent.click(screen.getByRole('button', { name: 'Thử lại' }))
    expect(await screen.findByText('Đã viết 0 / 2 nét')).toBeInTheDocument()
  })

  it('resumes after rapid scrolling queues multiple visibility changes in one observer callback', async () => {
    let notify!: (entries: { isIntersecting: boolean }[]) => void
    vi.stubGlobal('IntersectionObserver', class {
      constructor(callback: typeof notify) { notify = callback }
      observe() {}
      disconnect() {}
    })
    render(<StrokeOrder hanzi="字"/>)
    act(() => notify([{ isIntersecting: true }]))
    await screen.findByText('Đã viết 0 / 2 nét')
    await waitFor(() => expect(players[0].play).toHaveBeenCalled())
    act(() => notify([{ isIntersecting: false }]))
    const before = players[0].play.mock.calls.length
    act(() => notify([{ isIntersecting: false }, { isIntersecting: true }]))
    expect(players[0].play.mock.calls.length).toBeGreaterThan(before)
  })
})
