import {expect,it} from 'vitest'
import {chapterArrivalWaypoint,chapterEntryPose,CHAPTER_ENTRY_MS,CHAPTER_COVER_DELAY_MS} from './chapterEntry'
import {chapterRange,spatialCameraFrame,spatialGround} from './spatialWallPath'

it('walks Bo from the milestone pose into the doorway, darkening only at the threshold',()=>{
  for(const level of [1,2]){
    const s=chapterRange(level).end,start=chapterEntryPose(s,0),frame=spatialCameraFrame(s,786,54)
    expect(start.point).toEqual(frame.bo)
    expect(start.opacity).toBe(1)
    let last=start.distance
    for(let i=1;i<=20;i++){
      const step=chapterEntryPose(s,i/20)
      expect(step.distance).toBeGreaterThan(last);last=step.distance
      if(i<=14)expect(step.opacity).toBe(1)
    }
    const end=chapterEntryPose(s,1)
    expect(end.distance).toBeGreaterThan(s-3.5)
    expect(end.point.y).toBe(spatialGround(s,true))
    expect(end.opacity).toBe(0)
    expect(end.brightness).toBeCloseTo(.2)
  }
  expect(CHAPTER_COVER_DELAY_MS).toBeGreaterThan(CHAPTER_ENTRY_MS)
})

it('arrives at the first lesson for portal links and honors matching marker identity',()=>{
  expect(chapterArrivalWaypoint(JSON.stringify({marker:240,firstLesson:true}),240,1)).toBe(.5)
  expect(chapterArrivalWaypoint(JSON.stringify({marker:405,firstLesson:true}),405,1)).toBe(.5)
  expect(chapterArrivalWaypoint(JSON.stringify({marker:240,firstLesson:true}),405,1)).toBeNull()
  expect(chapterArrivalWaypoint(null,240,1)).toBeNull()
  expect(chapterArrivalWaypoint('not json',240,1)).toBeNull()
  expect(chapterArrivalWaypoint('240',240,1)).toBe(0)
})
