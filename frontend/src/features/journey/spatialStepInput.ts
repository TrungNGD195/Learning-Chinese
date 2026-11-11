import { SPATIAL_TREAD } from './spatialWallPath'

export function snapSpatialStep(progress: number, interval: number, maximum: number) {
  return Math.max(0, Math.min(maximum, Math.round(progress * interval / SPATIAL_TREAD) * SPATIAL_TREAD / interval))
}

export function nextSpatialStep(progress: number, direction: number, interval: number, maximum: number) {
  return snapSpatialStep(progress + Math.sign(direction) * SPATIAL_TREAD / interval, interval, maximum)
}

/** A trackpad's event burst and inertial tail are one gesture, not extra steps. */
export function createWheelStepIntent() {
  let lastAt = -Infinity, lastDirection = 0
  return (delta: number, now: number, deltaMode = 0) => {
    if (!delta) return 0
    const direction = delta < 0 ? 1 : -1
    const notch = deltaMode !== 0 || Math.abs(delta) === 100 || Math.abs(delta) === 120
    const fresh = notch || now - lastAt > 160 || direction !== lastDirection
    lastAt = now;lastDirection = direction
    return fresh ? direction : 0
  }
}
