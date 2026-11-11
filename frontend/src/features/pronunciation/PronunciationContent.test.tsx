import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { PronunciationContent } from './PronunciationContent'
import { sandhiGroups } from './sandhiData'
import { pronunciationContent, type PronunciationCode } from './pronunciationData'
import { pronunciationTip } from './pronunciationTips'

afterEach(() => vi.unstubAllGlobals())

describe('pronunciation learning content', () => {
  it.each(['INITIALS', 'FINALS', 'TONES', 'SANDHI'] as PronunciationCode[])('provides a specific reminder for every example in %s', code => {
    const sounds = pronunciationContent[code].groups.flatMap(group => group.sounds)
    const reminders = sounds.map(sound => pronunciationTip(code, sound))
    expect(reminders.every(tip => Boolean(tip?.trim()))).toBe(true)
    expect(new Set(reminders).size).toBe(sounds.length)
  })

  it('distinguishes lip-teeth f, nasal m and the neutral-tone example instead of reusing a group instruction', () => {
    const findTip = (code: PronunciationCode, symbol: string) => pronunciationTip(code, pronunciationContent[code].groups.flatMap(group => group.sounds).find(sound => sound.symbol === symbol)!)
    expect(findTip('INITIALS', 'f')).toContain('răng trên vào môi dưới')
    expect(findTip('INITIALS', 'm')).toContain('hơi thoát qua mũi')
    expect(findTip('TONES', 'Thanh nhẹ')).toContain('ma thứ hai')
    expect(findTip('FINALS', 'un')).toContain('Đừng nhầm với ün')
  })

  it('provides twelve sandhi examples with original tones, spoken forms and meaningful notes', () => {
    const examples = sandhiGroups.flatMap(group => group.sounds)
    expect(examples).toHaveLength(12)
    for (const example of examples) {
      expect(example.hanzi && example.pinyin && example.spoken && example.meaning && example.explanation).toBeTruthy()
    }
    expect(examples.find(row => row.hanzi === '你好')?.spoken).toBe('ní hǎo')
    expect(examples.find(row => row.hanzi === '第一')?.spoken).toBe('dìyī')
    expect(examples.find(row => row.hanzi === '看一看')?.spoken).toBe('kàn yi kàn')
  })
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
