export const REFERENCE_ART = '/academy/great-wall/reference-v1/approved-layout.png'
export const referenceRegions = {
  hero: [271,119,1216,604],
  climb: [45,754,448,207],
  bend: [544,754,448,207],
  gate: [1043,754,448,207],
  climbCard: [45,754,448,248],
  bendCard: [544,754,448,248],
  gateCard: [1043,754,448,248],
  restingBo: [83,394,115,113],
} as const
export type ReferenceRegion = keyof typeof referenceRegions
