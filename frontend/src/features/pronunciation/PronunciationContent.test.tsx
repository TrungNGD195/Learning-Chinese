import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { PronunciationContent } from './PronunciationContent'

afterEach(() => vi.unstubAllGlobals())

describe('pronunciation learning content', () => {
  it('shows all 21 initials and keeps written examples available without an audio voice', () => {
    render(<PronunciationContent code="INITIALS" />)
    fireEvent.click(screen.getByText('Mở nội dung học'))
    expect(screen.getAllByRole('button')).toHaveLength(21)
    expect(screen.getByRole('button', { name: 'Nghe zhī, ví dụ 知' })).toBeDisabled()
    expect(screen.getByText(/Thiết bị chưa có giọng đọc tiếng Trung/)).toBeInTheDocument()
  })

  it('shows the grouped finals and their spelling notes', () => {
    render(<PronunciationContent code="FINALS" />)
    fireEvent.click(screen.getByText('Mở nội dung học'))
    expect(screen.getAllByRole('button')).toHaveLength(36)
    expect(screen.getByRole('button', { name: 'Nghe yuè, ví dụ 月' })).toBeInTheDocument()
    expect(screen.getByText(/hai chấm của ü thường được lược/)).toBeInTheDocument()
  })

  it('offers four tones and a neutral-tone example', () => {
    render(<PronunciationContent code="TONES" />)
    fireEvent.click(screen.getByText('Mở nội dung học'))
    expect(screen.getAllByRole('button')).toHaveLength(5)
    expect(screen.getByText('Thanh nhẹ')).toBeInTheDocument()
    expect(screen.getByText(/cách viết vẫn giữ nguyên dấu thanh 3/)).toBeInTheDocument()
  })

  it('plays the selected Chinese example only when a Mandarin voice is available', () => {
    const speak = vi.fn()
    const cancel = vi.fn()
    const voice = { lang: 'zh-CN', localService: true }
    vi.stubGlobal('speechSynthesis', { getVoices: () => [voice], addEventListener: vi.fn(), removeEventListener: vi.fn(), speak, cancel })
    class Utterance {
      text: string
      voice: unknown
      lang = ''
      rate = 1
      constructor(text: string) { this.text = text }
    }
    vi.stubGlobal('SpeechSynthesisUtterance', Utterance)
    render(<PronunciationContent code="INITIALS" />)
    fireEvent.click(screen.getByText('Mở nội dung học'))
    fireEvent.click(screen.getByRole('button', { name: 'Nghe bā, ví dụ 八' }))
    expect(cancel).toHaveBeenCalledOnce()
    expect(speak).toHaveBeenCalledWith(expect.objectContaining({ text: '八', voice, lang: 'zh-CN', rate: 0.8 }))
  })
})
