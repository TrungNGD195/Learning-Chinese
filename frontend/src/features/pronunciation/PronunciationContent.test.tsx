import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { PronunciationContent } from './PronunciationContent'
import { sandhiGroups } from './sandhiData'
import { pronunciationContent, type PronunciationCode } from './pronunciationData'
import { pronunciationTip } from './pronunciationTips'
import { pronunciationComparison } from './pronunciationComparisons'
const shared=vi.hoisted(()=>({voiceAvailable:true,speak:vi.fn(),voiceName:'Mandarin fixture',zhongReference:null as {seconds:number;voiceName:string}|null}))
vi.mock('../../lib/audio/mandarinAudio',()=>({useMandarinAudio:()=>shared}))

beforeEach(()=>{shared.voiceAvailable=true;shared.speak.mockClear();shared.zhongReference=null})
afterEach(() => vi.unstubAllGlobals())

describe('pronunciation learning content', () => {
  it('matches ong to the latest same-voice zhong duration without changing the combined example',()=>{
    shared.zhongReference={seconds:.62,voiceName:shared.voiceName}
    render(<PronunciationContent code="FINALS"/>)
    fireEvent.click(screen.getByText('Mở nội dung học'))
    fireEvent.click(screen.getByRole('button',{name:'Nghe vận mẫu ong'}))
    expect(shared.speak).toHaveBeenLastCalledWith(expect.objectContaining({clip:'/academy/audio/isolated-finals-v4/ong-600.wav'}))
    fireEvent.click(screen.getByRole('button',{name:'Nghe âm ghép zhong'}))
    expect(shared.speak).toHaveBeenLastCalledWith(expect.objectContaining({hanzi:'中',pinyin:'zhong'}))
  })
  it.each(['ai','eng','ong','er'])('plays isolated %s from a recording even without a device TTS voice',symbol=>{
    shared.voiceAvailable=false
    render(<PronunciationContent code="FINALS"/>)
    fireEvent.click(screen.getByText('Mở nội dung học'))
    const button=screen.getByRole('button',{name:`Nghe vận mẫu ${symbol}`})
    expect(button).toBeEnabled()
    fireEvent.click(button)
    expect(shared.speak).toHaveBeenCalledWith(expect.objectContaining({symbol,hanzi:'',clip:symbol==='ong'?'/academy/audio/isolated-finals-v4/ong-550.wav':`/academy/audio/isolated-finals-v1/${symbol}.wav`}))
    expect(screen.queryByText(/Đang bổ sung bản thu riêng cho/)).toBeNull()
    expect(pronunciationContent.FINALS.groups.flatMap(g=>g.sounds)).toHaveLength(36)
  })
  it.each(['INITIALS', 'FINALS'] as PronunciationCode[])('provides a specific Vietnamese/English approximation for each sound in %s', code => {
    const sounds=pronunciationContent[code].groups.flatMap(group=>group.sounds)
    const comparisons=sounds.map(sound=>pronunciationComparison(code,sound.symbol))
    expect(comparisons.every(text=>Boolean(text?.trim()))).toBe(true)
    if(code==='FINALS')expect(new Set(comparisons).size).toBe(sounds.length)
  })

  it('preserves the supplied ü tongue-position cue without adding tone/sandhi comparisons',()=>{
    expect(pronunciationComparison('FINALS','ü')).toBe('Đọc như “u” nhưng không lùi lưỡi về phía sau.')
    expect(pronunciationComparison('INITIALS','b')).toBe('Gần âm “p” trong tiếng Việt.')
    expect(pronunciationComparison('TONES','Thanh 1 · ˉ')).toBeUndefined()
    expect(pronunciationComparison('SANDHI','你好')).toBeUndefined()
  })
  it('keeps special apical-i syllables out of introductory initial examples', () => {
    const examples = pronunciationContent.INITIALS.groups.flatMap(group => group.sounds)
    expect(examples.map(example => example.pinyin)).not.toEqual(expect.arrayContaining(['chi']))
    expect(examples.some(example => /^(zhi|chi|shi|ri|zi|ci|si)$/.test(example.pinyin))).toBe(false)
    expect(examples).toHaveLength(21)
  })
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
    expect(screen.getByRole('button', { name: 'Nghe zha, ví dụ 渣' })).toBeEnabled()
    expect(screen.queryByText(/Thiết bị chưa có giọng đọc tiếng Trung/)).toBeNull()
  })

  it('shows the grouped finals and their spelling notes', () => {
    render(<PronunciationContent code="FINALS" />)
    fireEvent.click(screen.getByText('Mở nội dung học'))
    expect(screen.getAllByRole('button', { name: /^Nghe vận mẫu / })).toHaveLength(36)
    expect(screen.getByRole('button', { name: 'Nghe vận mẫu üe' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Nghe âm ghép que' })).toBeInTheDocument()
    expect(screen.getByText(/hai chấm của ü thường được lược/)).toBeInTheDocument()
  })

  it('offers four tones and a neutral-tone example', () => {
    render(<PronunciationContent code="TONES" />)
    fireEvent.click(screen.getByText('Mở nội dung học'))
    expect(screen.getAllByRole('button')).toHaveLength(5)
    expect(screen.getByText('Thanh nhẹ')).toBeInTheDocument()
    expect(screen.getByText(/cách viết vẫn giữ nguyên dấu thanh 3/)).toBeInTheDocument()
  })

  it.each([['ba', '八'], ['pa', '趴'], ['ma', '妈'], ['sa', '仨'], ['zha', '渣']])('plays the selected %s example without ambiguous 撒 or 扎 carrier characters', (pinyin, hanzi) => {
    shared.speak.mockClear()
    render(<PronunciationContent code="INITIALS" />)
    fireEvent.click(screen.getByText('Mở nội dung học'))
    fireEvent.click(screen.getByRole('button', { name: `Nghe ${pinyin}, ví dụ ${hanzi}` }))
    expect(shared.speak).toHaveBeenCalledWith(expect.objectContaining({hanzi}))
  })
})
