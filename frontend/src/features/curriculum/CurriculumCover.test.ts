import {describe,expect,it} from 'vitest'
import {curriculumCoverTopic} from './curriculumCoverData'

describe('covers match existing lesson content rather than lesson numbers',()=>{
 it.each([
  ['你好 · Xin chào','greetings'],
  ['我叫小丽 · Tôi tên là Tiểu Lệ','introductions'],
  ['我是越南人 · Tôi là người Việt Nam','nationality'],
  ['我有两个孩子 · Tôi có hai đứa con','family'],
  ['今天几月几号？ · Hôm nay là ngày mấy tháng mấy?','dates-food'],
 ])('%s gets its own subject cover',(title,topic)=>expect(curriculumCoverTopic(title)).toBe(topic))
 it('keeps unknown and unpublished topics neutral',()=>{
  expect(curriculumCoverTopic('Một chủ đề khác')).toBe('study')
  expect(curriculumCoverTopic('我有两个孩子',true)).toBe('study')
 })
})
