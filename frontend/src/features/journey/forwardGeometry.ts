// Distance is horizontal arc length: turns must not change the walking speed.
export const FORWARD_GATE_STEP = 42
export const FORWARD_GATE_RISE = 9
export const FORWARD_LANDING_HALF = 9
export const FORWARD_TREAD = .75
export const FORWARD_RISER = FORWARD_GATE_RISE / 32
export const forwardRoadHeading = (distance: number) => 1.12 * Math.sin((distance + 18) * Math.PI * 2 / (FORWARD_GATE_STEP * 4))
export const forwardRoadSlope = (distance: number) => Math.sin(forwardRoadHeading(distance))

// Integrate the heading once. Rendering interpolates the table without allocating
// vectors or numerically integrating the entire road on each animation frame.
const SAMPLE = .25, FROM = -168, TO = 2016
const samples = Array.from({ length: (TO - FROM) / SAMPLE + 1 }, () => ({ x: 0, z: 0 }))
for (let i = 1; i < samples.length; i++) {
  const heading = forwardRoadHeading(FROM + (i - .5) * SAMPLE)
  samples[i].x = samples[i - 1].x + Math.sin(heading) * SAMPLE
  samples[i].z = samples[i - 1].z - Math.cos(heading) * SAMPLE
}
const origin = { ...samples[-FROM / SAMPLE] }
for (const sample of samples) { sample.x -= origin.x;sample.z -= origin.z }
function horizontal(distance: number, axis: 'x' | 'z') {
  const position = (distance - FROM) / SAMPLE
  const index = Math.max(0, Math.min(samples.length - 2, Math.floor(position)))
  return samples[index][axis] + (samples[index + 1][axis] - samples[index][axis]) * (position - index)
}
export const forwardRoadX = (distance: number) => horizontal(distance, 'x')
export const forwardRoadZ = (distance: number) => horizontal(distance, 'z')

function flight(distance: number) {
  const gate = Math.floor((distance + FORWARD_LANDING_HALF) / FORWARD_GATE_STEP)
  const run = Math.max(0, distance - gate * FORWARD_GATE_STEP - FORWARD_LANDING_HALF)
  return { gate, run }
}
// Continuous navigation profile; the camera never jumps over individual risers.
export function forwardRoadY(distance: number) {
  const { gate, run } = flight(distance)
  return gate * FORWARD_GATE_RISE + run * FORWARD_RISER / FORWARD_TREAD
}
export function forwardStepY(distance: number) {
  const { gate, run } = flight(distance)
  return gate * FORWARD_GATE_RISE + Math.floor((run + .000001) / FORWARD_TREAD) * FORWARD_RISER
}
export function forwardRoadPoint(distance: number, offset = 0) {
  const heading = forwardRoadHeading(distance)
  return { x: forwardRoadX(distance) + offset * Math.cos(heading), y: forwardRoadY(distance), z: forwardRoadZ(distance) + offset * Math.sin(heading) }
}

export function forwardCameraFrame(distance: number, entry = 0, side = 0) {
  const boDistance = distance - 8 + entry * 16
  const bo = forwardRoadPoint(boDistance, -side * 1.4)
  const behind = forwardRoadPoint(boDistance - 10), ahead = forwardRoadPoint(boDistance + 14)
  const heading = Math.atan2(ahead.x - behind.x, behind.z - ahead.z)
  const dx = Math.sin(heading), dz = -Math.cos(heading)
  const ground = (forwardRoadY(boDistance - 3) + 2 * forwardRoadY(boDistance) + forwardRoadY(boDistance + 3)) / 4
  // Chase Bo rather than a point far behind on the winding road. The camera can
  // overhang the valley; the avatar cannot drift out of frame on the inside bend.
  return {
    boDistance, bo: { ...bo, y: forwardStepY(boDistance) }, heading,
    eye: { x: bo.x - dx * 22 + Math.cos(heading) * 1.8, y: ground + 9.8, z: bo.z - dz * 22 + Math.sin(heading) * 1.8 },
    look: { x: bo.x + dx * 14, y: ground + 3, z: bo.z + dz * 14 },
  }
}
export const clampJourneyProgress = (progress: number, count: number) => Math.max(0, Math.min(Math.max(0, count - 1), progress))

export function forwardProgressAt(scrollY: number, start: number, step: number, count: number) {
  return clampJourneyProgress(count - 1 - (scrollY - start) / step, count)
}

export function forwardScrollAt(progress: number, start: number, step: number, count: number) {
  return Math.max(0, start + (count - 1 - clampJourneyProgress(progress, count)) * step)
}

export function dampJourneyProgress(current: number, target: number, elapsedMs: number) {
  const next = current + (target - current) * (1 - Math.exp(-Math.max(0, elapsedMs) / 105))
  return Math.abs(target - next) < .0005 ? target : next
}
