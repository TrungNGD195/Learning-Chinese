export const ROUTE_TREAD=1.8
export const ROUTE_STEPS_PER_GATE=6
export const ROUTE_SPAN=ROUTE_TREAD*ROUTE_STEPS_PER_GATE
const stairCount=4
export const ROUTE_RISE=.6
export const ROUTE_HALF_WIDTH=3.5
export function routeHalfWidth(s:number){const nearest=Math.round(s/ROUTE_SPAN)*ROUTE_SPAN,t=Math.max(0,1-Math.abs(s-nearest)/3.6);return ROUTE_HALF_WIDTH+t*t*(3-2*t)}
export const ROUTE_COUNTS=[16,10,15] as const // HSK 1 includes pronunciation.
export const ROUTE_TOWER_STEPS=3
export const ROUTE_BO_LEAD=6.3
// One span to reach the tower, then one to emerge beyond its guardroom.
export const routeLevelStart=(level:number)=>ROUTE_COUNTS.slice(0,Math.max(0,level-1)).reduce((sum,count)=>sum+(count+2)*ROUTE_SPAN,0)
export const ROUTE_END=ROUTE_COUNTS.reduce((sum,count)=>sum+(count+2)*ROUTE_SPAN,0)+100
export const routeTowerDistance=(level:number,total:number)=>routeLevelStart(level)+(total+1)*ROUTE_SPAN
export const routeHeading=(s:number)=>.46*Math.sin(s/ROUTE_SPAN)+.08*Math.sin(s/(ROUTE_SPAN*5/12))
const spacing=.3,begin=-72
const points=Array.from({length:Math.ceil((ROUTE_END-begin+50)/spacing)+1},()=>({x:0,z:0}))
for(let i=1;i<points.length;i++){const h=routeHeading(begin+(i-.5)*spacing);points[i].x=points[i-1].x+Math.sin(h)*spacing;points[i].z=points[i-1].z-Math.cos(h)*spacing}
const origin=points[Math.round(-begin/spacing)]
const originX=origin.x,originZ=origin.z
for(const p of points){p.x-=originX;p.z-=originZ}
export function routeHeight(s:number,mode:'floor'|'eye'|'foot'='floor'){
  const cycle=Math.floor(s/ROUTE_SPAN),phase=s-cycle*ROUTE_SPAN
  const raw=phase/ROUTE_TREAD,stairs=Math.min(stairCount,Math.max(0,raw)),index=Math.floor(stairs),fraction=stairs-index
  const smooth=(t:number)=>{const q=Math.max(0,Math.min(1,t));return q*q*(3-2*q)}
  const eye=Math.min(stairCount,Math.max(0,raw-.35)),remaining=stairCount-eye,roundedEye=eye<1?eye*eye*(2-eye):remaining<1?stairCount-remaining**2*(2-remaining):eye
  const rise=mode==='floor'?index:mode==='eye'?roundedEye:index+(index<stairCount?smooth((fraction-.58)/.42):0)
  return cycle*stairCount*ROUTE_RISE+rise*ROUTE_RISE
}
export function routePoint(s:number,side=0,mode:'floor'|'eye'|'foot'='floor'){
  const t=Math.max(0,Math.min(points.length-1.001,(s-begin)/spacing)),i=Math.floor(t),f=t-i,h=routeHeading(s)
  return{x:points[i].x+(points[i+1].x-points[i].x)*f+Math.cos(h)*side,y:routeHeight(s,mode),z:points[i].z+(points[i+1].z-points[i].z)*f+Math.sin(h)*side}
}
const smooth=(a:number,b:number,x:number)=>{const t=Math.max(0,Math.min(1,(x-a)/(b-a)));return t*t*(3-2*t)}
export function routeTowerEntry(boS:number,towerS:number){
  return{opacity:1-smooth(0,.7,boS-towerS),entered:boS>=towerS+.7}
}
export function routeGateVisibility(cameraS:number,gateS:number){
  const distance=gateS-cameraS,available=distance>-3&&distance<ROUTE_SPAN*5
  const opacity=distance>=0?1-smooth(ROUTE_SPAN*1.3,ROUTE_SPAN*5,distance):1-smooth(0,2.5,-distance)
  return{distance,opacity:available?opacity:0,mist:.82*smooth(3.5,ROUTE_SPAN*2,distance),available}
}
