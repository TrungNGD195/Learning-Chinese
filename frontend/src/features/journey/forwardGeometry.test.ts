import { expect, it } from 'vitest'
import { clampJourneyProgress, dampJourneyProgress, forwardProgressAt, forwardRoadHeading, forwardRoadPoint, forwardRoadSlope, forwardRoadX, forwardRoadY, forwardRoadZ, forwardScrollAt, forwardStepY, FORWARD_GATE_RISE, FORWARD_GATE_STEP, FORWARD_RISER } from './forwardGeometry'

it.each([10, 15, 16, 20])('maps every one of %i gates to native scrolling in both directions', count => {
  for (const step of [205, 235]) for (let index = 0; index < count; index++) {
    const scroll = forwardScrollAt(index, 64, step, count)
    expect(forwardProgressAt(scroll, 64, step, count)).toBe(index)
    if (index) expect(scroll).toBeLessThan(forwardScrollAt(index - 1, 64, step, count))
  }
  expect(clampJourneyProgress(-3, count)).toBe(0)
  expect(clampJourneyProgress(count + 3, count)).toBe(count - 1)
})

it('follows the winding ridge at a constant horizontal walking speed', () => {
  for (let s = -50; s <= 500; s++) {
    const dx = (forwardRoadX(s + .25) - forwardRoadX(s - .25)) / .5
    const dz = (forwardRoadZ(s + .25) - forwardRoadZ(s - .25)) / .5
    expect(forwardRoadSlope(s)).toBeCloseTo(dx, 4)
    expect(Math.hypot(dx, dz)).toBeCloseTo(1, 4)
    expect(Math.abs(forwardRoadHeading(s + .25) - forwardRoadHeading(s))).toBeLessThan(.011)
  }
  expect(forwardRoadHeading(20)).toBeGreaterThan(.9)
  expect(forwardRoadHeading(104)).toBeLessThan(-.9)
})

it('puts each gate on a level landing and climbs real steps between landings', () => {
  for (let gate = 0; gate < 20; gate++) {
    const s = gate * FORWARD_GATE_STEP, y = gate * FORWARD_GATE_RISE
    for (const offset of [-8, 0, 8]) {
      expect(forwardStepY(s + offset)).toBe(y)
      expect(forwardRoadY(s + offset)).toBe(y)
    }
    expect(forwardStepY(s + 10)).toBeGreaterThan(y)
    expect(forwardStepY(s + 32)).toBeLessThan(y + FORWARD_GATE_RISE)
  }
  let previous = forwardStepY(-60)
  for (let s = -59.9; s < 840; s += .1) {
    const y = forwardStepY(s)
    expect(y).toBeGreaterThanOrEqual(previous)
    expect(y - previous).toBeLessThanOrEqual(FORWARD_RISER + .00001)
    expect(forwardRoadY(s) - y).toBeGreaterThanOrEqual(-.00001)
    expect(forwardRoadY(s) - y).toBeLessThan(FORWARD_RISER + .00001)
    previous = y
  }
})

it('keeps the full walkway between the parapets on both sides of a bend', () => {
  for (let s = -50; s < 800; s += 2) {
    const left = forwardRoadPoint(s, -8), right = forwardRoadPoint(s, 8)
    expect(Math.hypot(right.x - left.x, right.z - left.z)).toBeCloseTo(16, 8)
    expect(left.y).toBe(right.y)
  }
})

it('eases and reverses without overshooting, then stops exactly at the destination', () => {
  let progress = 5
  progress = dampJourneyProgress(progress, 6, 16)
  expect(progress).toBeGreaterThan(5);expect(progress).toBeLessThan(6)
  expect(dampJourneyProgress(progress, 4, 16)).toBeLessThan(progress)
  for (let i = 0; i < 80; i++) {
    const next = dampJourneyProgress(progress, 6, 16)
    expect(next).toBeGreaterThanOrEqual(progress);expect(next).toBeLessThanOrEqual(6)
    progress = next
  }
  expect(progress).toBe(6)
})

it('damps consistently across different display refresh rates', () => {
  function run(hz: number) {
    let progress = 3
    for (let frame = 0; frame < hz / 2; frame++) progress = dampJourneyProgress(progress, 4, 1000 / hz)
    return progress
  }
  expect(run(60)).toBeCloseTo(run(120), 8)
})
