import { expect, it } from 'vitest'
import { spatialGateOpacity } from './spatialGateOpacity'

it('keeps the gateway fully readable until Bo begins crossing it', () => {
  for (const distance of [-40, -6, -1.5, -.01, 0]) expect(spatialGateOpacity(distance)).toBe(1)
  for (const distance of [1.5, 3, 20]) expect(spatialGateOpacity(distance)).toBe(0)
  expect(spatialGateOpacity(.75)).toBe(.5)
})

it('fades continuously with distance and retraces the same fade on reversal', () => {
  const approach = Array.from({ length: 101 }, (_, i) => spatialGateOpacity(i * .015))
  const retreat = Array.from({ length: 101 }, (_, i) => spatialGateOpacity(1.5 - i * .015)).reverse()
  approach.forEach((opacity, i) => {
    expect(opacity).toBeCloseTo(retreat[i], 10)
    expect(opacity).toBeGreaterThanOrEqual(0)
    expect(opacity).toBeLessThanOrEqual(1)
    if (i) expect(approach[i - 1] - opacity).toBeGreaterThanOrEqual(0)
    if (i) expect(approach[i - 1] - opacity).toBeLessThan(.016)
  })
})
