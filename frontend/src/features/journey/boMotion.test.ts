import { expect, it } from 'vitest'
import { createBoMotion, updateBoMotion } from './boMotion'

it('advances real walk frames only when the character travels', () => {
  const state = createBoMotion(3)
  const frames = new Set<number>()
  for (let i = 1; i <= 30; i++) frames.add(updateBoMotion(state, 3 + i * .025, 16, i * 16).frame)
  expect(frames.size).toBeGreaterThan(4)
  const phase = state.phase
  const idle = updateBoMotion(state, state.position, 32, 1000)
  expect(idle.walking).toBe(false)
  expect(state.phase).toBe(phase)
})
it('uses a forward animation cycle for both travel directions and changes the view on reversal', () => {
  const state = createBoMotion(2)
  expect(updateBoMotion(state, 2.05, 16, 100).direction).toBe(1)
  const phase = state.phase
  const reverse = updateBoMotion(state, 2.02, 16, 116)
  expect(reverse.direction).toBe(-1)
  expect(reverse.walking).toBe(true)
  expect(state.phase).toBeGreaterThan(phase)
})
it('bounds the footfall rate during fast scrolling and ignores a stationary initial frame', () => {
  const state = createBoMotion(0)
  expect(updateBoMotion(state, 0, 16, 0).walking).toBe(false)
  const result = updateBoMotion(state, 10, 16, 16)
  expect(state.phase).toBeLessThanOrEqual(.048)
  expect(result.frame).toBeGreaterThanOrEqual(0)
  expect(result.frame).toBeLessThan(8)
})
