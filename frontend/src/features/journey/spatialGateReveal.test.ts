import { expect, it } from 'vitest'
import { spatialGateReveal } from './spatialGateReveal'

it('shows the current gate clearly and hides all later gates under mist', () => {
  for(const bo of [-6,-3,0]) {
    expect(spatialGateReveal(bo,0).opacity).toBe(1)
    expect(spatialGateReveal(bo,0).mist).toBe(0)
    for(const next of [15,30,45])expect(spatialGateReveal(bo,next)).toEqual({opacity:0,reveal:0,mist:1})
  }
})

it('finishes passing one gate before revealing the next, one tread at a time', () => {
  for(const bo of [.1,.75,1.4]) {
    expect(spatialGateReveal(bo,0).opacity).toBeGreaterThan(0)
    expect(spatialGateReveal(bo,15).opacity).toBe(0)
  }
  const reveal=Array.from({length:6},(_,i)=>spatialGateReveal(1.5+i*1.5,15))
  expect(spatialGateReveal(1.5,0).opacity).toBe(0)
  expect(reveal[0].opacity).toBe(0)
  expect(reveal[5].opacity).toBe(1)
  for(let i=1;i<reveal.length;i++) {
    expect(reveal[i].opacity).toBeGreaterThan(reveal[i-1].opacity)
    expect(reveal[i].mist).toBeLessThan(reveal[i-1].mist)
  }
})

it('reverses without timers and never shows two overlapping numbered gates', () => {
  const forward=Array.from({length:91},(_,i)=>i/10-6)
  for(const bo of [...forward,...forward.toReversed()]) {
    const a=spatialGateReveal(bo,0),b=spatialGateReveal(bo,15)
    expect(a.opacity+b.opacity).toBeLessThanOrEqual(1)
    expect(a.mist).toBeGreaterThanOrEqual(0)
    expect(a.mist).toBeLessThanOrEqual(1)
  }
})

it('carries the same reveal rule across milestone / chapter boundaries', () => {
  expect(spatialGateReveal(234,240).reveal).toBe(1)
  expect(spatialGateReveal(240,240).opacity).toBe(1)
  expect(spatialGateReveal(241.5,240).opacity).toBe(0)
  expect(spatialGateReveal(234,255,240).opacity).toBe(0)
  expect(spatialGateReveal(241.5,255,240).opacity).toBe(0)
  expect(spatialGateReveal(249,255,240).opacity).toBe(1)
})
