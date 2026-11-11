import { ASCENT_GATE_DEPTH, ASCENT_SPAN, ascentFoot } from './paintedAscent'

export type PaintedStage = 'landing' | 'climb' | 'bend'
export type PaintedGate = { x: number; y: number; width: number; height: number; opacity: number; visible: boolean }
const smooth = (a: number, b: number, value: number) => { const t = Math.max(0, Math.min(1, (value - a) / (b - a)));return t * t * (3 - 2 * t) }

export function paintedWallFrame(progress: number, count: number, width: number, height: number, entry = 0) {
  const index = Math.min(count - 1, Math.max(0, Math.floor(progress + .00001)))
  const phase = Math.max(0, Math.min(1, progress - index))
  const portrait = width / height < 1.15
  const gateWidth = Math.min(width * (portrait ? .87 : .35), height * .68)
  const baseline = height * (portrait ? .58 : .60)
  // Navigation cadence only. These phases no longer swap independent images.
  const stage: PaintedStage = phase < .15 || phase > .9 ? 'landing' : phase < .55 ? 'climb' : 'bend'
  const gates: PaintedGate[] = Array.from({ length: count }, () => ({ x: 0, y: 0, width: 0, height: 0, opacity: 0, visible: false }))
  function gate(at: number, scale: number, floor: number, opacity: number, x = .5) {
    if (at >= count || opacity < .015) return
    const w = gateWidth * scale, h = w * 974 / 1615
    gates[at] = { x: width * x - w / 2, y: floor - h * .972279, width: w, height: h, opacity, visible: true }
  }
  for (let at = Math.max(0, index - 1); at <= Math.min(count - 1, index + 1); at++) {
    const depth = ASCENT_GATE_DEPTH + (at - progress) * ASCENT_SPAN - entry * 3
    if (depth < 3 || depth > 12.8) continue
    const scale = ASCENT_GATE_DEPTH / depth
    const floor = height * .46 + (baseline - height * .46) * scale
    gate(at, scale, floor, smooth(3, 4, depth) * (1 - smooth(11.5, 12.8, depth)) * (1 - smooth(.55, .95, entry)))
  }
  const avatarHeight = Math.min(height * (portrait ? .25 : .315), width * .48, 260) * (1 - entry * .32)
  const foot = Math.min(height * .81, height - 165)
  const plantedFoot = ascentFoot(progress, height, foot)
  return { gates, stage, phase, portrait, zoom: 1.025 + entry * .075, pan: Math.sin(progress * Math.PI / 3) * .012,
    avatar: { x: width * (.40 + entry * .1), y: plantedFoot + (baseline - plantedFoot - height * .025) * entry, height: avatarHeight, elevation: progress * 9 } }
}
