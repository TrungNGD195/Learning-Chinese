import { expect, it } from 'vitest'
import { createWheelStepIntent, nextSpatialStep, snapSpatialStep } from './spatialStepInput'
import { chapterRange, spatialGround, spatialLayout, SPATIAL_GATE_SPAN, SPATIAL_TREAD } from './spatialWallPath'

it('uses eight taller risers between nearby gates', () => {
  let rises = 0
  for (let s = 0; s < SPATIAL_GATE_SPAN; s += SPATIAL_TREAD) {
    const rise = spatialGround(s + SPATIAL_TREAD + .001, true) - spatialGround(s + .001, true)
    if (rise > .001) { rises++; expect(rise).toBeCloseTo(.675) }
  }
  expect(rises).toBe(8)
  expect(SPATIAL_GATE_SPAN).toBeLessThan(24)
  expect(chapterRange(1).end).toBe(chapterRange(2).start)
})

it('moves one tread on each command and queues repeated commands without drifting', () => {
  for (const [level, count] of [[1, 16], [2, 10], [3, 15]]) {
    const layout = spatialLayout(level, count)
    let position = 0
    for (let i = 0; i < 10; i++) position = nextSpatialStep(position, 1, layout.interval, layout.maxProgress)
    expect(position).toBeCloseTo(1)
    position = nextSpatialStep(position, -1, layout.interval, layout.maxProgress)
    expect(position).toBeCloseTo(.9)
    expect(nextSpatialStep(0, -1, layout.interval, layout.maxProgress)).toBe(0)
    expect(nextSpatialStep(layout.maxProgress, 1, layout.interval, layout.maxProgress)).toBe(layout.maxProgress)
    expect(snapSpatialStep(.347, layout.interval, layout.maxProgress)).toBeCloseTo(.3)
  }
})

it('counts an inertial wheel burst once, accepts a new gesture and immediate reversal', () => {
  const wheel = createWheelStepIntent()
  expect(wheel(-120, 0)).toBe(1)
  for (const [delta, time] of [[-80, 15], [-30, 45], [-2, 120]]) expect(wheel(delta, time)).toBe(0)
  expect(wheel(-120, 300)).toBe(1)
  expect(wheel(100, 320)).toBe(-1)
  expect(wheel(0, 330)).toBe(0)
})

it('keeps distinct mouse notches even when they arrive quickly', () => {
  const wheel = createWheelStepIntent()
  expect(wheel(-120, 0)).toBe(1)
  expect(wheel(-120, 30)).toBe(1)
  expect(wheel(-100, 60)).toBe(1)
  expect(wheel(-3, 80, 1)).toBe(1)
})
