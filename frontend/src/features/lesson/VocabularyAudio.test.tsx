import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { VocabularyAudio } from './VocabularyAudio'

afterEach(() => vi.unstubAllGlobals())

const mandarin = { lang: 'zh-CN', localService: true } as SpeechSynthesisVoice
function install(voices: SpeechSynthesisVoice[] = [mandarin]) {
  const synth = { getVoices: vi.fn(() => voices), addEventListener: vi.fn(), removeEventListener: vi.fn(), speak: vi.fn(), cancel: vi.fn() }
  vi.stubGlobal('speechSynthesis', synth)
  class Utterance { text: string; constructor(text: string) { this.text = text } }
  vi.stubGlobal('SpeechSynthesisUtterance', Utterance)
  return synth
}

describe('vocabulary pronunciation', () => {
  it('reads the selected Hanzi in Mandarin only after an explicit click', () => {
    const synth = install()
    render(<VocabularyAudio hanzi="你好"/>)
    const button = screen.getByRole('button', { name: 'Nghe phát âm 你好' })
    expect(synth.speak).not.toHaveBeenCalled()
    fireEvent.click(button)
    expect(synth.speak).toHaveBeenCalledWith(expect.objectContaining({ text: '你好', voice: mandarin, lang: 'zh-CN', rate: 0.8 }))
    expect(button).toHaveAttribute('aria-busy', 'true')
    const utterance = synth.speak.mock.calls[0][0] as SpeechSynthesisUtterance
    act(() => utterance.onend?.({} as SpeechSynthesisEvent))
    expect(button).toHaveAttribute('aria-busy', 'false')
  })

  it('does not read a Chinese word with an English or Cantonese voice', () => {
    const synth = install([{ lang: 'en-US' }, { lang: 'zh-HK' }] as SpeechSynthesisVoice[])
    render(<VocabularyAudio hanzi="好"/>)
    fireEvent.click(screen.getByRole('button', { name: 'Nghe phát âm 好' }))
    expect(synth.speak).not.toHaveBeenCalled()
    expect(screen.getByRole('status')).toHaveTextContent('Thiết bị chưa có giọng đọc tiếng Trung')
  })

  it('becomes playable when the browser loads a Mandarin voice later', () => {
    const synth = install([])
    render(<VocabularyAudio hanzi="你"/>)
    const button = screen.getByRole('button', { name: 'Nghe phát âm 你' })
    fireEvent.click(button)
    synth.getVoices.mockReturnValue([mandarin])
    act(() => synth.addEventListener.mock.calls[0][1]())
    fireEvent.click(button)
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    expect(synth.speak).toHaveBeenCalledWith(expect.objectContaining({ text: '你', lang: 'zh-CN' }))
  })

  it('allows retry after a playback error and stops its active reading on exit', () => {
    const synth = install()
    const { unmount } = render(<VocabularyAudio hanzi="不"/>)
    const button = screen.getByRole('button', { name: 'Nghe phát âm 不' })
    fireEvent.click(button)
    const utterance = synth.speak.mock.calls[0][0] as SpeechSynthesisUtterance
    act(() => utterance.onerror?.({ error: 'synthesis-failed' } as SpeechSynthesisErrorEvent))
    expect(screen.getByRole('status')).toHaveTextContent('Chưa thể phát âm thanh')
    expect(button).toHaveAttribute('aria-busy', 'false')
    fireEvent.click(button)
    expect(synth.speak).toHaveBeenCalledTimes(2)
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    synth.cancel.mockClear()
    unmount()
    expect(synth.cancel).toHaveBeenCalledOnce()
  })
})
