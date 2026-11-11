import { spatialGateOpacity } from './spatialGateOpacity'
import { SPATIAL_GATE_SPAN, SPATIAL_TREAD } from './spatialWallPath'

const smooth = (value: number) => {
  const t = Math.max(0, Math.min(1, value))
  return t * t * (3 - 2 * t)
}

export function spatialGateReveal(boDistance: number, gateDistance: number, previousDistance = gateDistance - SPATIAL_GATE_SPAN) {
  const start = previousDistance + SPATIAL_TREAD
  // Fully clear at the normal gate stop, six world units ahead of Bo.
  const finish = Math.max(start + .01, gateDistance - 6)
  const reveal = smooth((boDistance - start) / (finish - start))
  return { reveal, opacity: reveal * spatialGateOpacity(boDistance - gateDistance), mist: 1 - reveal }
}
