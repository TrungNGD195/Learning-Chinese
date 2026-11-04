import { beforeEach, describe, expect, it } from 'vitest'
import { readReadingPreferences,saveReadingPreferences } from './readingPreferences'

beforeEach(()=>localStorage.clear())
describe('reading settings boundary',()=>{
  it('stores only the two allowed display preferences',()=>{
    saveReadingPreferences({size:21,pinyin:false,access_token:'must-not-persist',lesson_progress:100} as unknown as Parameters<typeof saveReadingPreferences>[0])
    expect(JSON.parse(localStorage.getItem('chinese-learning.reading.v1')!)).toEqual({size:21,pinyin:false})
  })
  it('rejects malformed or unsupported display sizes',()=>{
    localStorage.setItem('chinese-learning.reading.v1','{"size":999,"pinyin":false}')
    expect(readReadingPreferences()).toEqual({size:19,pinyin:false})
    localStorage.setItem('chinese-learning.reading.v1','null')
    expect(readReadingPreferences()).toEqual({size:19,pinyin:true})
  })
})
