import { SPATIAL_TREAD } from './spatialWallPath'

/** Keep the arch solid until Bo crosses its plane, then clear it over one tread. */
export function spatialGateOpacity(distancePastGate: number) {
  const crossing = Math.max(0, Math.min(1, distancePastGate / SPATIAL_TREAD))
  return 1 - crossing * crossing * (3 - 2 * crossing)
}
