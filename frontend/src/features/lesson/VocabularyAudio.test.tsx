import {fireEvent,render,screen} from '@testing-library/react'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import {VocabularyAudio} from './VocabularyAudio'
const shared=vi.hoisted(()=>({voiceAvailable:true,speak:vi.fn(),isSpeaking:false,speechError:null as string|null}))
vi.mock('../../lib/audio/mandarinAudio',()=>({useMandarinAudio:()=>shared}))
beforeEach(()=>{shared.speak.mockClear();shared.voiceAvailable=true;shared.isSpeaking=false;shared.speechError=null})
describe('vocabulary uses the application Mandarin player',()=>{
 it('requests only the selected Hanzi after an explicit click',()=>{
  render(<VocabularyAudio hanzi="学生"/> )
  expect(shared.speak).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button',{name:'Nghe phát âm 学生'}))
  expect(shared.speak).toHaveBeenCalledWith({hanzi:'学生'})
 })
 it('exposes loading state from the common player',()=>{
  shared.isSpeaking=true
  render(<VocabularyAudio hanzi="学生"/> )
  expect(screen.getByRole('button')).toHaveAttribute('aria-busy','true')
 })
 it('shows a retry message without asking for an operating-system voice',()=>{
  shared.speechError='Chưa phát được âm thanh. Bạn hãy bấm nghe lại.'
  render(<VocabularyAudio hanzi="学生"/> )
  expect(screen.getByRole('status')).toHaveTextContent('bấm nghe lại')
  expect(screen.queryByText(/cài đặt giọng/)).toBeNull()
 })
 it('explains a missing Mandarin device voice after clicking',()=>{
  shared.voiceAvailable=false
  render(<VocabularyAudio hanzi="学生"/> )
  fireEvent.click(screen.getByRole('button'))
  expect(screen.getByRole('status')).toHaveTextContent('Thiết bị chưa có giọng đọc tiếng Trung')
 })
})
