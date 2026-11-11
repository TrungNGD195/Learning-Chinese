import {describe,expect,it} from 'vitest'
import {ROUTE_SPAN,ROUTE_STEPS_PER_GATE,ROUTE_TREAD,ROUTE_BO_LEAD,ROUTE_TOWER_STEPS,routeGateVisibility,routeHeading,routeHeight,routeLevelStart,routePoint,routeTowerDistance,routeTowerEntry} from './firstPersonRoute'

describe('one continuous first-person Great Wall route',()=>{
  it('moves forward and upward through the gate without resetting coordinates',()=>{
    const before=routePoint(ROUTE_SPAN-.001,0,'eye'),after=routePoint(ROUTE_SPAN+.001,0,'eye')
    expect(Math.hypot(after.x-before.x,after.y-before.y,after.z-before.z)).toBeLessThan(.003)
    expect(after.y).toBeCloseTo(before.y,6)
    for(let s=0;s<100;s+=.5){const a=routePoint(s),b=routePoint(s+.5);expect(b.z).toBeLessThan(a.z);expect(b.y+1e-9).toBeGreaterThanOrEqual(a.y)}
  })
  it('starts each chapter beyond the preceding tower on the same road',()=>{
    expect(routeLevelStart(2)).toBe(18*ROUTE_SPAN)
    expect(routeLevelStart(3)).toBe(routeLevelStart(2)+12*ROUTE_SPAN)
    const arrival=routePoint(routeLevelStart(2)),exit=routePoint(routeTowerDistance(1,16)+ROUTE_SPAN)
    expect(arrival.x).toBeCloseTo(exit.x,10);expect(arrival.y).toBeCloseTo(exit.y,10);expect(arrival.z).toBeCloseTo(exit.z,10)
    expect(routePoint(routeLevelStart(3)).z).toBeLessThan(routePoint(routeTowerDistance(2,10)).z)
  })
  it('keeps the gateway opaque before crossing while its covering cloud thins with distance',()=>{
    const far=routeGateVisibility(0,ROUTE_SPAN),near=routeGateVisibility(ROUTE_SPAN-3,ROUTE_SPAN),crossed=routeGateVisibility(ROUTE_SPAN+1,ROUTE_SPAN)
    expect(far.opacity).toBe(1);expect(near.opacity).toBe(1);expect(near.mist).toBeLessThan(far.mist)
    expect(crossed.opacity).toBeLessThan(1)
    const distant=routeGateVisibility(0,ROUTE_SPAN*3)
    expect(distant.available).toBe(true)
    expect(distant.opacity).toBeGreaterThan(0)
    expect(distant.opacity).toBeLessThan(far.opacity)
    const before=routeGateVisibility(ROUTE_SPAN-.001,ROUTE_SPAN*2),after=routeGateVisibility(ROUTE_SPAN+.001,ROUTE_SPAN*2)
    expect(Math.abs(before.opacity-after.opacity)).toBeLessThan(.001)
    expect(Math.abs(before.mist-after.mist)).toBeLessThan(.001)
  })
  it('changes heading substantially around the curve and has a level landing through each gate',()=>{
    expect(Math.abs(routeHeading(ROUTE_SPAN*4)-routeHeading(ROUTE_SPAN*3))).toBeGreaterThan(.3)
    expect(routeHeight(ROUTE_SPAN-1, 'eye')).toBeCloseTo(routeHeight(ROUTE_SPAN+.4,'eye'),6)
  })
  it('reaches the next gate in six single-tread inputs',()=>{
    expect(ROUTE_STEPS_PER_GATE).toBe(6)
    expect(ROUTE_SPAN/ROUTE_STEPS_PER_GATE).toBe(ROUTE_TREAD)
  })
  it('fades Bo only inside the tower and reaches it in three further treads',()=>{
    const end=16*ROUTE_SPAN,tower=routeTowerDistance(1,16)
    expect(routeTowerEntry(end+ROUTE_BO_LEAD,tower)).toEqual({opacity:1,entered:false})
    expect(routeTowerEntry(tower-.01,tower)).toEqual({opacity:1,entered:false})
    expect(routeTowerEntry(end+(ROUTE_TOWER_STEPS-1)*ROUTE_TREAD+ROUTE_BO_LEAD,tower).entered).toBe(false)
    expect(routeTowerEntry(end+ROUTE_TOWER_STEPS*ROUTE_TREAD+ROUTE_BO_LEAD,tower)).toEqual({opacity:0,entered:true})
  })
})
