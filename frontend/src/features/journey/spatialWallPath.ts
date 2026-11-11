export const SPATIAL_GATE_SPAN = 15
export const SPATIAL_TREAD = 1.5
export const SPATIAL_GATE_RISE = 5.4
export const spatialFov=(width:number,height:number)=>width/height<.5?76:width/height<.9?68:54
const landing = 1.5
const counts: Record<number,number> = {1:15,2:10,3:15}

export function chapterRange(level: number) {
  let start=0
  for(let n=1;n<level;n++)start+=((counts[n]??15)+1)*SPATIAL_GATE_SPAN
  return {start,end:start+((counts[level]??15)+1)*SPATIAL_GATE_SPAN}
}
export function spatialLayout(level: number, gateCount: number) {
  const {start,end}=chapterRange(level),leadIn=level>1?1:0,maxProgress=gateCount+leadIn
  return {start,end,leadIn,maxProgress,interval:(end-start)/Math.max(1,maxProgress)}
}
export const spatialHeading=(s:number)=>.78*Math.sin(s/90)+.18*Math.sin(s/41)
const from=-120,to=2000,spacing=.4
const samples=Array.from({length:Math.ceil((to-from)/spacing)+1},()=>({x:0,z:0}))
for(let i=1;i<samples.length;i++){
  const heading=spatialHeading(from+(i-.5)*spacing)
  samples[i].x=samples[i-1].x+Math.sin(heading)*spacing
  samples[i].z=samples[i-1].z-Math.cos(heading)*spacing
}
const origin={...samples[Math.round(-from/spacing)]}
for(const p of samples){p.x-=origin.x;p.z-=origin.z}
export function spatialGround(s:number, stepped=false) {
  const n=Math.floor((s+landing)/SPATIAL_GATE_SPAN)
  const run=Math.max(0,s-n*SPATIAL_GATE_SPAN-landing)
  const slope=SPATIAL_GATE_RISE/(SPATIAL_GATE_SPAN-landing*2)
  return n*SPATIAL_GATE_RISE+(stepped?Math.floor(run/SPATIAL_TREAD)*SPATIAL_TREAD:run)*slope
}
export function spatialFoot(s:number) {
  const n=Math.floor((s+landing)/SPATIAL_GATE_SPAN),run=Math.max(0,s-n*SPATIAL_GATE_SPAN-landing)
  const phase=run/SPATIAL_TREAD-Math.floor(run/SPATIAL_TREAD)
  const lift=Math.max(0,Math.min(1,(phase-.65)/.35))
  return spatialGround(s,true)+lift*lift*(3-2*lift)*SPATIAL_GATE_RISE/(SPATIAL_GATE_SPAN-landing*2)*SPATIAL_TREAD
}
export function spatialPoint(s:number,offset=0) {
  const position=Math.max(0,Math.min(samples.length-1.001,(s-from)/spacing)),i=Math.floor(position),t=position-i
  const h=spatialHeading(s)
  return {x:samples[i].x+(samples[i+1].x-samples[i].x)*t+offset*Math.cos(h),
    y:spatialGround(s),z:samples[i].z+(samples[i+1].z-samples[i].z)*t+offset*Math.sin(h)}
}
export function spatialRoadHalfWidth(s:number) {
  let widen=0
  for(const level of [1,2,3])widen=Math.max(widen,Math.max(0,1-Math.abs(s-chapterRange(level).end)/10))
  return 4.6+2.4*widen*widen*(3-2*widen)
}
export function spatialCameraFrame(s:number,height:number,fov:number,entry=0) {
  let marker=0
  // Keep every lesson gate at the ordinary camera scale. Pull back only once
  // the preceding gate has cleared, within the final half-segment to the tower.
  const radius=SPATIAL_GATE_SPAN/2
  for(const level of [1,2,3]){const t=Math.max(0,Math.min(1,(radius-Math.abs(s-chapterRange(level).end))/radius));marker=Math.max(marker,t*t*(3-2*t))}
  const eyeS=s-13-marker*11+entry*2.2,boS=s-6+entry*3.2
  const eye=spatialPoint(eyeS,marker*2.2),bo=spatialPoint(boS,-.55+marker*.9),look=spatialPoint(s+2,marker*.2)
  eye.y=(spatialGround(eyeS-2)+2*spatialGround(eyeS)+spatialGround(eyeS+2))/4+3.3
  const groundBo=spatialGround(boS),dx=look.x-eye.x,dz=look.z-eye.z
  const horizontal=Math.hypot(bo.x-eye.x,bo.z-eye.z)
  const footY=Math.min(height*.79,height-150)/height
  const pitch=Math.atan2(groundBo-eye.y,horizontal)+Math.atan((footY*2-1)*Math.tan(fov*Math.PI/360))
  const distance=Math.hypot(dx,dz)
  look.y=eye.y+Math.tan(pitch)*distance
  // Only the actor's feet follow individual risers; the camera never stair-bobs.
  bo.y=spatialFoot(boS)
  return {eye,bo,look,heading:Math.atan2(dx,-dz),distance:s,boDistance:boS}
}
