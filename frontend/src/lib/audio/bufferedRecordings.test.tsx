import {act,cleanup,fireEvent,render,screen} from '@testing-library/react'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import {useMandarinAudio} from './mandarinAudio'

const clip='/academy/audio/special-i-native-v7/cmn-chi1.wav'
const buffer={} as AudioBuffer
class Source {
 buffer:AudioBuffer|null=null; playbackRate={value:1}; onended:(()=>void)|null=null
 connect=vi.fn();disconnect=vi.fn();start=vi.fn();stop=vi.fn()
}
class Context {
 static instances:Context[]=[]
 state='running';destination={};sources:Source[]=[]
 output={gain:{value:1},connect:vi.fn()}
 resume=vi.fn(async()=>{this.state='running'})
 close=vi.fn(async()=>{this.state='closed'})
 decodeAudioData=vi.fn(async()=>buffer)
 createGain=vi.fn(()=>this.output)
 createBufferSource=vi.fn(()=>{const source=new Source();this.sources.push(source);return source})
 constructor(){Context.instances.push(this)}
}
const synth={getVoices:vi.fn(()=>[{lang:'zh-CN',localService:true}]),addEventListener:vi.fn(),removeEventListener:vi.fn(),cancel:vi.fn(),speak:vi.fn()}
function Probe({label='native',src=clip}:{label?:string;src?:string|null}){
 const audio=useMandarinAudio()
 return <><button aria-busy={audio.isSpeaking} onClick={()=>audio.speak(src?{clip:src,hanzi:'吃'}:{hanzi:'你好'})}>{label}</button>{audio.speechError&&<p role="alert">{audio.speechError}</p>}</>
}
beforeEach(()=>{
 Context.instances=[];vi.clearAllMocks()
 vi.stubGlobal('AudioContext',Context)
 vi.stubGlobal('speechSynthesis',synth)
 vi.stubGlobal('SpeechSynthesisUtterance',class{text:string;constructor(text:string){this.text=text}})
 vi.stubGlobal('Audio',vi.fn(()=>{throw new Error('No detached media element')}))
 vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,arrayBuffer:async()=>new ArrayBuffer(4)})))
})
afterEach(()=>{cleanup();vi.unstubAllGlobals()})
async function click(label='native'){await act(async()=>{fireEvent.click(screen.getByRole('button',{name:label}))})}

describe('fully buffered native recordings',()=>{
 it('loads and decodes the whole file before starting, then keeps the output open at natural end',async()=>{
  synth.getVoices.mockReturnValueOnce([])
  let finishDownload!:(value:ArrayBuffer)=>void
  vi.mocked(fetch).mockResolvedValue({ok:true,arrayBuffer:()=>new Promise(resolve=>{finishDownload=resolve})} as Response)
  render(<Probe/>);await click()
  const context=Context.instances[0]
  expect(context.sources).toHaveLength(0)
  await act(async()=>finishDownload(new ArrayBuffer(4)))
  const source=context.sources[0]
  expect(source.buffer).toBe(buffer);expect(source.start).toHaveBeenCalledOnce()
  expect(source.playbackRate.value).toBe(1)
  act(()=>source.onended?.())
  expect(context.close).not.toHaveBeenCalled();expect(source.stop).not.toHaveBeenCalled()
  expect(screen.getByRole('button',{name:'native'})).toHaveAttribute('aria-busy','false')
  expect(Audio).not.toHaveBeenCalled();expect(synth.speak).not.toHaveBeenCalled()
 })
 it('reuses decoded data and one output context for repeated listens',async()=>{
  render(<Probe/>);await click()
  const context=Context.instances[0];act(()=>context.sources[0].onended?.())
  await click()
  expect(Context.instances).toHaveLength(1)
  expect(fetch).toHaveBeenCalledOnce();expect(context.decodeAudioData).toHaveBeenCalledOnce()
  expect(context.sources).toHaveLength(2)
 })
 it('aborts a pending download on another action and never starts a late result',async()=>{
  let finishDownload!:(value:ArrayBuffer)=>void
  vi.mocked(fetch).mockResolvedValue({ok:true,arrayBuffer:()=>new Promise(resolve=>{finishDownload=resolve})} as Response)
  render(<><Probe/><Probe label="word" src={null}/></>);await click()
  const signal=vi.mocked(fetch).mock.calls[0][1]?.signal
  await click('word');expect(signal?.aborted).toBe(true)
  await act(async()=>finishDownload(new ArrayBuffer(4)))
  expect(Context.instances[0].sources).toHaveLength(0)
  expect(synth.speak).toHaveBeenCalledOnce()
 })
 it('stops a prior recording without allowing its late end to clear the new one',async()=>{
  render(<><Probe/><Probe label="second" src="/academy/audio/special-i-native-v7/cmn-ri1.wav"/></>);await click()
  const first=Context.instances[0].sources[0],lateEnd=first.onended
  await click('second');expect(first.stop).toHaveBeenCalledOnce()
  act(()=>lateEnd?.())
  expect(screen.getByRole('button',{name:'second'})).toHaveAttribute('aria-busy','true')
 })
 it('shares cancellation with browser speech in both directions',async()=>{
  render(<><Probe/><Probe label="word" src={null}/></>)
  await click('word');const before=synth.cancel.mock.calls.length
  await click();expect(synth.cancel.mock.calls.length).toBeGreaterThan(before)
  const source=Context.instances[0].sources[0]
  await click('word');expect(source.stop).toHaveBeenCalledOnce()
  expect(Context.instances[0].close).not.toHaveBeenCalled()
 })
 it('reports fetch/decode failures and retries without a browser-voice fallback',async()=>{
  vi.mocked(fetch).mockRejectedValueOnce(new Error('offline'))
  render(<Probe/>);await click()
  expect(screen.getByRole('alert')).toHaveTextContent('Chưa thể phát bản thu')
  expect(synth.speak).not.toHaveBeenCalled()
  await click();expect(screen.queryByRole('alert')).toBeNull()
  expect(Context.instances[0].sources[0].start).toHaveBeenCalledOnce()
 })
 it('closes only on final unmount, and rejects unlisted audio URLs before fetch',async()=>{
  const {unmount}=render(<Probe/>);await click()
  const context=Context.instances[0];unmount()
  expect(context.sources[0].stop).toHaveBeenCalledOnce();expect(context.close).toHaveBeenCalledOnce()
  render(<Probe src="https://example.invalid/unlisted.wav"/>);await click()
  expect(fetch).toHaveBeenCalledOnce()
  expect(screen.getByRole('alert')).toHaveTextContent('chưa được cấu hình')
 })
})
