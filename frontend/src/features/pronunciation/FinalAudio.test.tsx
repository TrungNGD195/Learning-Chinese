import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { FinalAudio } from './FinalAudio'
import { pronunciationContent } from './pronunciationData'

const shared = vi.hoisted(() => ({ voiceAvailable: true, speak: vi.fn(), speechError: null as string | null }))
vi.mock('../../lib/audio/mandarinAudio', () => ({ useMandarinAudio: () => shared }))
const sound = (symbol: string) => pronunciationContent.FINALS.groups.flatMap(group => group.sounds).find(row => row.symbol === symbol)!
beforeEach(() => { shared.voiceAvailable = true; shared.speechError = null; shared.speak.mockClear() })

describe('separate final and tone-one combination playback', () => {
  it('plays a alone on the left and ma on the right, without exposing the carrier characters', () => {
    render(<FinalAudio sound={sound('a')}/>)
    const buttons = screen.getAllByRole('button')
    expect(buttons[0]).toHaveAccessibleName('Nghe vận mẫu a')
    expect(buttons[1]).toHaveAccessibleName('Nghe âm ghép ma')
    fireEvent.click(buttons[0]); fireEvent.click(buttons[1])
    expect(shared.speak.mock.calls.map(([input]) => input.hanzi)).toEqual(['阿', '妈'])
    expect(screen.queryByText('阿')).toBeNull()
    expect(screen.queryByText('妈')).toBeNull()
  })

  it.each([['eng', 'feng', '风'], ['ong', 'zhong', '中']])('plays %s from its isolated recording and retains its combined example', (symbol, pinyin, hanzi) => {
    render(<FinalAudio sound={sound(symbol)}/>)
    const isolated = screen.getByRole('button', { name: `Nghe vận mẫu ${symbol}` })
    expect(isolated).toBeEnabled()
    fireEvent.click(isolated)
    expect(shared.speak).toHaveBeenCalledWith(expect.objectContaining({ clip: expect.stringMatching(/\.wav$/) }))
    fireEvent.click(screen.getByRole('button', { name: `Nghe âm ghép ${pinyin}` }))
    expect(shared.speak).toHaveBeenCalledWith(expect.objectContaining({ hanzi }))
  })

  it.each(['ueng', 'er'])('never invents a consonant combination for %s', symbol => {
    render(<FinalAudio sound={sound(symbol)}/>)
    expect(screen.getByRole('button', { name: `Nghe vận mẫu ${symbol}` })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Không ghép với thanh mẫu' })).toBeDisabled()
  })

  it('places special i readings below the ordinary i and mi pair', () => {
    render(<FinalAudio sound={sound('i')}/>)
    const buttons = screen.getAllByRole('button')
    expect(buttons[0]).toHaveAccessibleName('Nghe vận mẫu i')
    expect(buttons[1]).toHaveAccessibleName('Nghe âm ghép mi')
    fireEvent.click(buttons[0]); fireEvent.click(buttons[1])
    fireEvent.click(screen.getByRole('button', { name: 'Nghe i đặc biệt trong chi' }))
    expect(shared.speak.mock.calls.map(([input]) => input.hanzi)).toEqual(['衣', '咪', '吃'])
    expect(shared.speak.mock.calls[2][0]).toEqual(expect.objectContaining({clip:'/academy/audio/special-i-native-v7/cmn-chi1.wav'}))
    expect(screen.getByRole('heading', { name: 'Cách đọc cần phân biệt' })).toBeVisible()
    expect(screen.getByText(/không phải vận mẫu ü/)).toBeVisible()
  })

  it('does not enable either tile without the existing Mandarin voice', () => {
    shared.voiceAvailable = false
    render(<FinalAudio sound={sound('a')}/>)
    for (const button of screen.getAllByRole('button')) expect(button).toBeDisabled()
  })

  it('keeps all seven native comparison recordings in their tongue-position groups without a browser Mandarin voice', () => {
    shared.voiceAvailable = false
    render(<FinalAudio sound={sound('i')}/>)
    const comparisons=screen.getAllByRole('button',{name:/^Nghe i đặc biệt/})
    expect(comparisons).toHaveLength(7)
    expect(screen.getByRole('heading',{name:'i sau z, c, s'})).toBeVisible()
    expect(screen.getByRole('heading',{name:'i sau zh, ch, sh, r'})).toBeVisible()
    for(const button of comparisons){expect(button).toBeEnabled();fireEvent.click(button)}
    expect(shared.speak.mock.calls.map(([input])=>input.clip)).toEqual(['zi','ci','si','zhi','chi','shi','ri'].map(pinyin=>`/academy/audio/special-i-native-v7/cmn-${pinyin}1.wav`))
  })
})
