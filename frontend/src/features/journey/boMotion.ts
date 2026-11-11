import { ASCENT_SPAN, ASCENT_TREAD } from './paintedAscent'

export type BoMotion = { position: number; phase: number; speed: number; direction: 1 | -1; lastMoved: number }
export function createBoMotion(position: number): BoMotion {
  return { position, phase: 0, speed: 0, direction: 1, lastMoved: -1000 }
}
export function updateBoMotion(state: BoMotion, position: number, elapsedMs: number, now: number, stride={span:ASCENT_SPAN,length:ASCENT_TREAD*2}) {
  const elapsed = Math.max(1, Math.min(250, elapsedMs)), delta = position - state.position
  const speed = Math.abs(delta) * 1000 / elapsed
  state.speed += (speed - state.speed) * (1 - Math.exp(-elapsed / 130))
  if (Math.abs(delta) > .0001) {
    state.direction = delta > 0 ? 1 : -1
    state.lastMoved = now
    state.phase += Math.min(Math.abs(delta) * stride.span / stride.length, elapsed / 1000 * 3)
  }
  state.position = position
  const walking = now - state.lastMoved < 190 && state.speed > .012
  return { walking, frame: Math.floor(state.phase * 8) % 8, direction: state.direction, speed: state.speed }
}
