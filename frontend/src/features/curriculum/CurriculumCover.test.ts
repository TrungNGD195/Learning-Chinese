import {describe,expect,it} from 'vitest'
import {curriculumCoverTopic,curriculumCoverAtlas} from './curriculumCoverData'

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
 it('gives all 25 actual HSK1–2 lessons a distinct, available subject image',()=>{
  const definitions=Object.values(import.meta.glob<{lesson:{title:string;hsk_level:number;lesson_number:number}}>('../../../../backend/content/curriculum-refresh/hsk*-lesson-*.json',{eager:true,import:'default'}))
  const assigned=definitions.map(({lesson})=>curriculumCoverTopic(lesson.title,false,{hskLevel:lesson.hsk_level,lessonNumber:lesson.lesson_number}))
  expect(definitions).toHaveLength(25)
  expect(new Set(assigned).size).toBe(25)
  expect(assigned).not.toContain('study')
  for(const topic of assigned){
   const atlas=curriculumCoverAtlas(topic)
   expect(atlas.src).toMatch(/^\/academy\/curriculum-v[23]\//)
   expect(atlas.position.split(' ').map(parseFloat).every(value=>value>=0&&value<=100)).toBe(true)
  }
 })
 it('gives all 15 HSK3 lessons a dedicated subject cover',()=>{
  const definitions=Object.values(import.meta.glob<{lesson:{title:string;lesson_number:number}}>('../../../../backend/content/hsk3/lesson-*.json',{eager:true,import:'default'}))
  const assigned=definitions.map(({lesson})=>curriculumCoverTopic(lesson.title,false,{hskLevel:3,lessonNumber:lesson.lesson_number}))
  expect(assigned).toHaveLength(15)
  expect(new Set(assigned).size).toBe(15)
  for(const topic of assigned){
   const atlas=curriculumCoverAtlas(topic)
   expect(atlas.src).toBe('/academy/curriculum-v4/hsk3-covers.webp')
   expect(atlas.position.split(' ').map(parseFloat).every(value=>value>=0&&value<=100)).toBe(true)
  }
 })
})
