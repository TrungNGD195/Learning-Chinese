import { expect,it } from 'vitest'
import * as THREE from 'three'
import { chapterRange,spatialLayout,spatialPoint,spatialCameraFrame,spatialFoot,spatialGround,spatialFov,SPATIAL_TREAD,SPATIAL_GATE_SPAN } from './spatialWallPath'

it('shares the exact world milestone between consecutive chapters',()=>{
  expect(chapterRange(1).end).toBe(chapterRange(2).start)
  expect(chapterRange(2).end).toBe(chapterRange(3).start)
  for(const [level,count] of [[1,16],[2,10]]){
    const a=spatialLayout(level,count),b=spatialLayout(level+1,level===1?10:15)
    const end=a.start+a.maxProgress*a.interval
    expect(spatialCameraFrame(end,786,54)).toEqual(spatialCameraFrame(b.start,786,54))
  }
})
it('keeps milestone positions when periodic tests add real curriculum gates',()=>{
  const ordinary=spatialLayout(1,16),withTests=spatialLayout(1,19)
  expect(ordinary.end).toBe(withTests.end)
  expect(withTests.start+withTests.maxProgress*withTests.interval).toBeCloseTo(ordinary.end)
})
it('translates, rises and turns the actual camera along a fixed world road',()=>{
  const a=spatialCameraFrame(168,786,54),b=spatialCameraFrame(176,786,54)
  expect(Math.hypot(b.eye.x-a.eye.x,b.eye.z-a.eye.z)).toBeGreaterThan(7)
  expect(b.eye.y).toBeGreaterThan(a.eye.y)
  expect(Math.abs(b.heading-a.heading)).toBeGreaterThan(.01)
})
it('has no camera reset at chapter boundaries or landing edges',()=>{
  for(const s of [0,24,168,chapterRange(1).end,chapterRange(2).end,chapterRange(3).end]){
    const a=spatialCameraFrame(s-.00001,786,54),b=spatialCameraFrame(s+.00001,786,54)
    expect(Math.hypot(a.eye.x-b.eye.x,a.eye.y-b.eye.y,a.eye.z-b.eye.z)).toBeLessThan(.001)
    expect(Math.abs(a.heading-b.heading)).toBeLessThan(.001)
  }
})

it('keeps the last lesson gate at the ordinary walking camera scale until it is passed',()=>{
  for(const level of [1,2,3]) {
    const gate=chapterRange(level).end-SPATIAL_GATE_SPAN
    for(const offset of [0,1.5,3,4.5,6,7.5]) {
      const s=gate+offset,frame=spatialCameraFrame(s,786,54),ordinary=spatialPoint(s-13)
      expect(frame.eye.x).toBeCloseTo(ordinary.x,10)
      expect(frame.eye.z).toBeCloseTo(ordinary.z,10)
    }
    const tower=spatialCameraFrame(chapterRange(level).end,786,54),normalEye=spatialPoint(chapterRange(level).end-13)
    expect(Math.hypot(tower.eye.x-normalEye.x,tower.eye.z-normalEye.z)).toBeGreaterThan(10)
  }
})
it('smoothly lifts the feet across each real tread',()=>{
  for(let i=5;i<30;i++){
    const s=3+i*SPATIAL_TREAD
    expect(Math.abs(spatialFoot(s-.000001)-spatialFoot(s+.000001))).toBeLessThan(.001)
    expect(spatialFoot(s+.000001)).toBeGreaterThanOrEqual(spatialGround(s-.001,true))
  }
})
it.each([[320,692],[390,692],[824,786],[1214,786]])('keeps the projected guide and full milestone in the %ipx viewport',(w,h)=>{
  const camera=new THREE.PerspectiveCamera(spatialFov(w,h),w/h,.15,1800)
  const project=(p:{x:number;y:number;z:number})=>{const v=new THREE.Vector3(p.x,p.y,p.z).project(camera);return{x:(v.x*.5+.5)*w,y:(-.5*v.y+.5)*h}}
  for(let s=0;s<chapterRange(3).end;s+=5.7){
    const f=spatialCameraFrame(s,h,camera.fov);camera.position.set(f.eye.x,f.eye.y,f.eye.z);camera.lookAt(f.look.x,f.look.y,f.look.z);camera.updateMatrixWorld()
    const foot=project(f.bo),top=project({...f.bo,y:f.bo.y+2.25}),height=foot.y-top.y
    expect(foot.x-height*.6).toBeGreaterThanOrEqual(0)
    expect(foot.x+height*.6).toBeLessThanOrEqual(w)
    expect(top.y).toBeGreaterThan(0);expect(foot.y).toBeLessThan(h-115)
  }
  for(const level of [1,2,3]){
    const s=chapterRange(level).end,f=spatialCameraFrame(s,h,camera.fov),p=spatialPoint(s,2.75)
    camera.position.set(f.eye.x,f.eye.y,f.eye.z);camera.lookAt(f.look.x,f.look.y,f.look.z);camera.updateMatrixWorld()
    const center=project({...p,y:p.y+3})
    expect(center.x).toBeGreaterThan(w*.25);expect(center.x).toBeLessThan(w*.9)
    expect(center.y).toBeGreaterThan(0);expect(center.y).toBeLessThan(h-120)
  }
})
