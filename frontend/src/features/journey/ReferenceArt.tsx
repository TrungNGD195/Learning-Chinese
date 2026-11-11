import {REFERENCE_ART,referenceRegions,type ReferenceRegion} from './referenceArtData'

/** Direct source-image regions; no repainting or approximation of the artwork. */
export function ReferenceArt({region,className}:{region:ReferenceRegion;className?:string}) {
  return <svg className={className} viewBox={referenceRegions[region].join(' ')} preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false" data-reference-region={region}><image href={REFERENCE_ART} width="1536" height="1024"/></svg>
}
