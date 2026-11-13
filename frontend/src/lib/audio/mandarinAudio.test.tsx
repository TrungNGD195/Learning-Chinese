import {act,cleanup,fireEvent,render,screen} from '@testing-library/react'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import {useMandarinAudio as useBrowserMandarinAudio} from './mandarinAudio'

const mandarin={name:'Installed Mandarin',lang:'zh-CN',localService:true} as SpeechSynthesisVoice
let voices:SpeechSynthesisVoice[]
let changed:()=>void
let synth:{getVoices:ReturnType<typeof vi.fn>;addEventListener:ReturnType<typeof vi.fn>;removeEventListener:ReturnType<typeof vi.fn>;speak:ReturnType<typeof vi.fn>;cancel:ReturnType<typeof vi.fn>}
function Sound({label,text,clip,rate}:{label:string;text:string;clip?:string;rate?:0.8|1}) {
 const audio=useBrowserMandarinAudio()
 return <><button aria-busy={audio.isSpeaking} data-available={String(audio.voiceAvailable)} data-reference={audio.zhongReference?.seconds} onClick={()=>audio.speak({hanzi:text,clip,rate})}>{label}</button>{audio.speechError&&<p role="alert">{audio.speechError}</p>}</>
}

beforeEach(()=>{
 voices=[mandarin]
 synth={getVoices:vi.fn(()=>voices),addEventListener:vi.fn((_type,callback)=>{changed=callback}),removeEventListener:vi.fn(),speak:vi.fn(),cancel:vi.fn()}
 vi.stubGlobal('speechSynthesis',synth)
 vi.stubGlobal('SpeechSynthesisUtterance',class {text:string;constructor(text:string){this.text=text}})
 vi.stubGlobal('Audio',vi.fn(()=>{throw new Error('Deployed mode must not load trial audio files')}))
 vi.stubGlobal('fetch',vi.fn(()=>{throw new Error('Speech must not call backend/Azure')}))
})
afterEach(()=>{cleanup();vi.unstubAllGlobals()})
describe('deployed browser Mandarin voice',()=>{
 it('records only completed zhong duration and ignores a canceled attempt',()=>{
  render(<><Sound label="zhong" text="中"/><Sound label="other" text="妈"/></>)
  fireEvent.click(screen.getByText('zhong'))
  const first=synth.speak.mock.calls[0][0] as SpeechSynthesisUtterance
  fireEvent.click(screen.getByText('other'))
  act(()=>first.onend?.({elapsedTime:.6} as SpeechSynthesisEvent))
  expect(screen.getByText('zhong')).not.toHaveAttribute('data-reference')
  fireEvent.click(screen.getByText('zhong'))
  const finished=synth.speak.mock.calls.at(-1)![0] as SpeechSynthesisUtterance
  act(()=>finished.onend?.({elapsedTime:.6} as SpeechSynthesisEvent))
  expect(screen.getByText('zhong')).toHaveAttribute('data-reference','0.6')
 })
 it('allows the isolated preview to use natural tempo while keeping voice and pitch',()=>{
  render(<Sound label="trial" text="滋" rate={1}/>)
  fireEvent.click(screen.getByText('trial'))
  expect(synth.speak).toHaveBeenCalledWith(expect.objectContaining({text:'滋',voice:mandarin,lang:'zh-CN',rate:1,pitch:1,volume:1}))
  expect(fetch).not.toHaveBeenCalled()
 })
 it('uses the exact deployed selection and rate only after a click',()=>{
  voices=[{lang:'en-US',localService:true} as SpeechSynthesisVoice,{lang:'zh-CN',localService:false} as SpeechSynthesisVoice,mandarin]
  render(<Sound label="word" text="你好"/> )
  expect(synth.speak).not.toHaveBeenCalled()
  fireEvent.click(screen.getByText('word'))
  expect(synth.speak).toHaveBeenCalledWith(expect.objectContaining({text:'你好',voice:mandarin,lang:'zh-CN',rate:.8,pitch:1,volume:1}))
  expect(fetch).not.toHaveBeenCalled();expect(Audio).not.toHaveBeenCalled()
 })
 it('never substitutes Vietnamese, English or Cantonese',()=>{
  voices=[{lang:'vi-VN'},{lang:'en-US'},{lang:'zh-HK'}] as SpeechSynthesisVoice[]
  render(<Sound label="word" text="学习"/> );fireEvent.click(screen.getByText('word'))
  expect(synth.speak).not.toHaveBeenCalled()
  expect(screen.getByRole('alert')).toHaveTextContent('Thiết bị chưa có giọng đọc tiếng Trung')
 })
 it('loads Mandarin voices asynchronously',()=>{
  voices=[];render(<Sound label="word" text="中国"/> )
  expect(screen.getByText('word')).toHaveAttribute('data-available','false')
  fireEvent.click(screen.getByText('word'))
  expect(screen.getByRole('alert')).toHaveTextContent('Thiết bị chưa có giọng đọc tiếng Trung')
  voices=[mandarin];act(()=>changed())
  expect(screen.queryByRole('alert')).toBeNull()
  fireEvent.click(screen.getByText('word'));expect(synth.speak).toHaveBeenCalledOnce()
 })
 it('cancels the previous component and ignores its late events',()=>{
  render(<><Sound label="first" text="你好"/><Sound label="second" text="汉语"/></>)
  fireEvent.click(screen.getByText('first'))
  const first=synth.speak.mock.calls[0][0] as SpeechSynthesisUtterance
  fireEvent.click(screen.getByText('second'))
  act(()=>first.onend?.({} as SpeechSynthesisEvent))
  expect(synth.cancel).toHaveBeenCalled();expect(screen.getByText('second')).toHaveAttribute('aria-busy','true')
  const second=synth.speak.mock.calls[1][0] as SpeechSynthesisUtterance
  act(()=>second.onend?.({} as SpeechSynthesisEvent))
  expect(screen.getByText('second')).toHaveAttribute('aria-busy','false')
 })
 it('permits retry and cancels active speech on exit',()=>{
  const {unmount}=render(<Sound label="word" text="银行"/> )
  fireEvent.click(screen.getByText('word'))
  const first=synth.speak.mock.calls[0][0] as SpeechSynthesisUtterance
  act(()=>first.onerror?.({error:'synthesis-failed'} as SpeechSynthesisErrorEvent))
  expect(screen.getByRole('alert')).toHaveTextContent('bấm nghe lại')
  fireEvent.click(screen.getByText('word'));expect(screen.queryByRole('alert')).toBeNull()
  const before=synth.cancel.mock.calls.length;unmount()
  expect(synth.cancel.mock.calls.length).toBeGreaterThan(before)
 })
})
