import {fireEvent,render,screen} from '@testing-library/react'
import {MemoryRouter} from 'react-router'
import {describe,expect,it,vi} from 'vitest'
import {JourneyCloudContext} from './journeyCloudContext'
import {LessonEntryLink} from './LessonEntryLink'

describe('lesson entry cloud links',()=>{
 it('uses return timing and preserves query destinations while repeated clicks stay intercepted',()=>{
  const travel=vi.fn().mockReturnValueOnce(true).mockReturnValue(false)
  render(<MemoryRouter><JourneyCloudContext value={{travel,cancel:vi.fn()}}><LessonEntryLink to="/lessons/real?part=grammar">Học bài</LessonEntryLink></JourneyCloudContext></MemoryRouter>)
  const link=screen.getByRole('link')
  expect(fireEvent.click(link)).toBe(false)
  expect(fireEvent.click(link)).toBe(false)
  expect(travel).toHaveBeenCalledWith({destination:'/lessons/real?part=grammar',returning:true})
 })
 it('preserves modified clicks and opening a new tab',()=>{
  const travel=vi.fn()
  render(<MemoryRouter><JourneyCloudContext value={{travel,cancel:vi.fn()}}><LessonEntryLink to="/lessons/real">Học bài</LessonEntryLink><LessonEntryLink target="_blank" to="/lessons/other">Tab mới</LessonEntryLink></JourneyCloudContext></MemoryRouter>)
  fireEvent.click(screen.getByText('Học bài'),{ctrlKey:true})
  fireEvent.click(screen.getByText('Học bài'),{metaKey:true})
  fireEvent.click(screen.getByText('Tab mới'))
  expect(travel).not.toHaveBeenCalled()
 })
})
