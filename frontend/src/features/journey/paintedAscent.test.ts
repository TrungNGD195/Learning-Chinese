import { expect, it } from 'vitest'
import { ASCENT_SPAN, ASCENT_TREAD, advanceAscentCamera, ascentFoot, ascentSteps } from './paintedAscent'
import { paintedWallFrame } from './paintedWallGeometry'

it('moves a persistent world tread down the screen as the camera climbs, and back on reversal',()=>{
  const before=ascentSteps(3,786).find(step=>step.near>4&&step.near<6)!
  const after=ascentSteps(3.025,786).find(step=>step.id===before.id)!
  expect(after.front).toBeGreaterThan(before.front+1)
  expect(after.near).toBeLessThan(before.near)
  expect(ascentSteps(3,786).find(step=>step.id===before.id)!.front).toBe(before.front)
})

it('has stronger optical flow on near treads than on distant treads',()=>{
  const a=ascentSteps(3,786), b=ascentSteps(3.02,786)
  const near=a.find(step=>step.near>3&&step.near<4)!,far=a.find(step=>step.near>6&&step.near<7)!
  const shift=(id:number,y:number)=>b.find(step=>step.id===id)!.front-y
  expect(shift(near.id,near.front)).toBeGreaterThan(shift(far.id,far.front)*2)
})

it('keeps treads and gate continuous across a lesson boundary',()=>{
  const a=ascentSteps(3.999999,786),b=ascentSteps(4.000001,786)
  for(const step of a) {
    const next=b.find(item=>item.id===step.id)
    if(next) expect(Math.abs(next.front-step.front)).toBeLessThan(.1)
  }
  for(const [w,h] of [[320,692],[390,692],[824,786],[1214,786]]) {
    const before=paintedWallFrame(3.999999,16,w,h),after=paintedWallFrame(4.000001,16,w,h)
    expect(Math.abs(before.zoom-after.zoom)).toBeLessThan(.0001)
    expect(Math.abs(before.pan-after.pan)).toBeLessThan(.0001)
    expect(Math.abs(before.gates[4].y-after.gates[4].y)).toBeLessThan(.01)
    expect(Math.abs(before.avatar.y-after.avatar.y)).toBeLessThan(.01)
  }
})

it('lifts Bo continuously onto each tread without a floor-boundary pop',()=>{
  const height=786,foot=621,depth=1.19/(foot/height-.46)
  for(let n=40;n<60;n++) {
    const progress=(n*ASCENT_TREAD-depth)/ASCENT_SPAN
    expect(Math.abs(ascentFoot(progress-.000001,height,foot)-ascentFoot(progress+.000001,height,foot))).toBeLessThan(.01)
  }
})

it('accelerates from rest, bounds normal climbing speed and settles at the target',()=>{
  const state={position:3,velocity:0}
  const first=advanceAscentCamera(state,3.3,16)-3
  const second=advanceAscentCamera(state,3.3,16)-3-first
  expect(second).toBeGreaterThan(first)
  for(let i=0;i<240;i++) {
    const before=state.position
    advanceAscentCamera(state,3.3,16)
    expect(state.position-before).toBeLessThanOrEqual(.55*.016+.00001)
    expect(state.position).toBeLessThanOrEqual(3.3)
  }
  expect(state.position).toBe(3.3);expect(state.velocity).toBe(0)
})

it('reverses without teleporting and bounds a long suspended frame',()=>{
  const state={position:3,velocity:.5}
  const before=state.position
  advanceAscentCamera(state,2.8,5000)
  expect(Math.abs(state.position-before)).toBeLessThanOrEqual(.55*.064+.00001)
  for(let i=0;i<120;i++)advanceAscentCamera(state,2.8,16)
  expect(state.position).toBe(2.8)
})
