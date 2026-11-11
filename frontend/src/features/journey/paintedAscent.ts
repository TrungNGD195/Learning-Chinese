// A continuous world coordinate, shared by the treads, camera and Bo's feet.
// Never reset this distance when the selected lesson changes.
export const ASCENT_SPAN = 8
export const ASCENT_TREAD = .85
export const ASCENT_RISE = .18
export const ASCENT_GATE_DEPTH = 8.5
const slope = ASCENT_RISE / ASCENT_TREAD
export type AscentPoint = { x: number; y: number }

export function ascentY(depth: number, worldHeight: number, travel: number, height: number) {
  const residual = worldHeight - (travel + depth) * slope
  return height * (.46 + (1.19 - residual * .70) / depth)
}

export function ascentSteps(progress: number, height: number) {
  const travel = progress * ASCENT_SPAN
  const first = Math.floor((travel + 1.8) / ASCENT_TREAD)
  const last = Math.ceil((travel + 10) / ASCENT_TREAD)
  return Array.from({ length: last - first + 1 }, (_, index) => {
    const id = last - index
    const near = id * ASCENT_TREAD - travel, far = near + ASCENT_TREAD
    const level = id * ASCENT_RISE
    return { id, near, far,
      front: ascentY(near, level, travel, height),
      back: ascentY(far, level, travel, height),
      bottom: ascentY(near, level - ASCENT_RISE, travel, height) }
  }).filter(step => step.near > 1.4 && step.front < height * 1.5 && step.bottom > height * .59)
}

export function ascentFoot(progress: number, height: number, foot: number) {
  const depth = 1.19 / (foot / height - .46)
  const cycles = (progress * ASCENT_SPAN + depth) / ASCENT_TREAD
  const phase = cycles - Math.floor(cycles)
  const lift = Math.max(0, Math.min(1, (phase - .65) / .35))
  // A short, smooth lift onto the next tread, rather than a discontinuous jump
  // at a floor() boundary. The camera follows the mean incline.
  const residual = (lift * lift * (3 - 2 * lift) - phase) * ASCENT_RISE
  return foot - residual * .70 * height / depth
}

export type AscentCamera = { position: number; velocity: number }
export function advanceAscentCamera(state: AscentCamera, target: number, elapsed: number, walkingSpeed=.55) {
  const dt = Math.max(0, Math.min(64, elapsed)) / 1000
  const omega = 18, offset = state.position - target
  const impulse = state.velocity + omega * offset, decay = Math.exp(-omega * dt)
  const proposed = target + (offset + impulse * dt) * decay
  const previousVelocity = state.velocity
  const freeVelocity = (state.velocity - omega * impulse * dt) * decay
  const speed = walkingSpeed + Math.max(0, Math.abs(offset) - .85) * 2.5
  const acceleration = (3 + Math.max(0,Math.abs(offset)-.85)*10) * dt
  state.velocity = Math.max(-speed,Math.min(speed,Math.max(previousVelocity-acceleration,Math.min(previousVelocity+acceleration,freeVelocity))))
  const distance = state.velocity===freeVelocity ? proposed-state.position : (previousVelocity+state.velocity)*dt/2
  const delta = Math.max(-speed * dt, Math.min(speed * dt, distance))
  state.position += delta
  if (offset * (state.position - target) <= 0) {state.position=target;state.velocity=0}
  if (Math.abs(state.position - target) < .0004 && Math.abs(state.velocity) < .004) {
    state.position = target;state.velocity = 0
  }
  return state.position
}
