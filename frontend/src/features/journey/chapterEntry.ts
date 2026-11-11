import { spatialFoot, spatialGround, spatialPoint } from './spatialWallPath'

export const CHAPTER_ENTRY_MS = 1350
export const CHAPTER_COVER_DELAY_MS = CHAPTER_ENTRY_MS + 120
const smooth=(v:number)=>{const t=Math.max(0,Math.min(1,v));return t*t*(3-2*t)}

export function chapterEntryPose(marker:number,amount:number) {
  const t=Math.max(0,Math.min(1,amount)),distance=marker-6+t*3.1
  const point=spatialPoint(distance,.35*(1-smooth(t)))
  const threshold=smooth((t-.55)/.45),ground=spatialFoot(distance)
  point.y=ground+(spatialGround(marker,true)-ground)*threshold
  const fade=smooth((t-.72)/.25)
  return {point,distance,opacity:1-fade,brightness:1-fade*.8}
}

export function chapterArrivalWaypoint(raw:string|null,start:number,firstLesson:number):number|null {
  if(raw===String(start))return 0 // Retain older tab-local marker links.
  // Stand on the first lesson's approach: the old tower has cleared, while
  // the next gate is still concealed by the cloud bank, as in the reference.
  try {const value=JSON.parse(raw??'null');return value?.marker===start&&value?.firstLesson===true?Math.max(0,firstLesson-.5):null}
  catch{return null}
}
