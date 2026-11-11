// Image-space coordinates (1024 × 1536 per painted section). Seals follow the
// measured centerline; the camera follows a rounded version of the same road.
export const WALL_WIDTH = 1024
export const WALL_SECTION_HEIGHT = 1536
export type WallPoint = { x: number; y: number }
const paintedCenterlines = [
  [506,549,630,600,455,300,274,413,534,654,694,678,586,502,475,453,424],
  [432,520,627,622,506,375,286,296,394,546,642,666,666,620,478,421,387],
  [464,524,636,614,506,373,282,258,360,486,604,686,676,605,524,420,397],
]

export function wallRegion(sectionFromTop: number, sections: number) {
  return Math.min(2, Math.round((sections - 1 - sectionFromTop) / Math.max(1, sections - 1) * 2))
}

export function wallCenterAt(y: number, sections: number): number {
  const bounded = Math.max(0, Math.min(sections * WALL_SECTION_HEIGHT - .001, y))
  const section = Math.floor(bounded / WALL_SECTION_HEIGHT)
  const local = bounded % WALL_SECTION_HEIGHT
  const samples = paintedCenterlines[wallRegion(section, sections)]
  const left = Math.min(samples.length - 2, Math.floor(local / 96))
  const t = (local - left * 96) / 96
  return samples[left] + (samples[left + 1] - samples[left]) * t
}

export function wallStopPositions(count: number, step = 200, edge = 160, bottomEdge = edge) {
  const height = Math.max(edge + bottomEdge, Math.max(0, count - 1) * step + edge + bottomEdge)
  const sections = Math.max(1, Math.ceil(height / WALL_SECTION_HEIGHT))
  const sectionHeight = height / sections
  const imageScaleY = sections * WALL_SECTION_HEIGHT / height
  return { sections, height, sectionHeight, imageScaleY, points: Array.from({ length: count }, (_, index) => {
    const y = height - bottomEdge - index * step
    return { x: wallCenterAt(y * imageScaleY, sections), y }
  }) }
}

// A shape-preserving cubic rounds the camera's turns without moving the seals.
// Shared samples at panel joints remove the discontinuity between painted roads.
export function wallCameraCenterAt(y: number, sections: number) {
  const last = sections * 16
  const sample = (index: number) => {
    const bounded = Math.max(0, Math.min(last, index))
    if (bounded === last) return paintedCenterlines[wallRegion(sections - 1, sections)][16]
    const section = Math.floor(bounded / 16), local = bounded % 16
    const value = paintedCenterlines[wallRegion(section, sections)][local]
    return !local && section > 0 ? (value + paintedCenterlines[wallRegion(section - 1, sections)][16]) / 2 : value
  }
  const position = Math.max(0, Math.min(last, y / 96))
  const left = Math.min(last - 1, Math.floor(position)), t = position - left
  const a = sample(left), b = sample(left + 1), delta = b - a
  const tangent = (before: number, after: number) => before * after <= 0 ? 0 : 2 * before * after / (before + after)
  const start = tangent(a - sample(left - 1), delta)
  const end = tangent(delta, sample(left + 2) - b)
  return (2 * t ** 3 - 3 * t ** 2 + 1) * a + (t ** 3 - 2 * t ** 2 + t) * start
    + (-2 * t ** 3 + 3 * t ** 2) * b + (t ** 3 - t ** 2) * end
}

// Time-based damping feels the same on 60/120Hz displays, with no spring bounce.
export function dampWallCamera(current: number, target: number, elapsedMs: number) {
  const next = current + (target - current) * (1 - Math.exp(-Math.max(0, elapsedMs) / 80))
  return Math.abs(target - next) < .1 ? target : next
}

export function wallCameraX(worldY: number, sections: number, viewportWidth: number, scale: number, reducedMotion: boolean) {
  let center = wallCameraCenterAt(worldY, sections)
  if (reducedMotion) center = WALL_WIDTH / 2
  const desired = viewportWidth / 2 - center * scale
  const minimum = Math.min(0, viewportWidth - WALL_WIDTH * scale)
  return Math.max(minimum, Math.min(0, desired))
}
