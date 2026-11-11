// Ground anchors in the interpolated painting, from staircase to bend to gate.
export const CLIMB_STATIONS = [
  [.405,.92],[.42,.85],[.43,.79],[.44,.72],[.45,.655],
  [.45,.655],[.395,.625],[.365,.60],[.365,.60],[.475,.575],[.51,.545],
] as const
export function climbLocalProgress(progress:number,total:number){
  return progress>=total?1:Math.max(0,Math.min(1,progress-Math.floor(progress)))
}
export function climbAction(p:number){return p<.43?'climb':p<.78?'bend':'gate'}

// One input means one footfall. Sprite phase is tied to distance, not wall time.
export function climbGait(p:number){
  const raw=Math.max(0,p)*10,step=Math.abs(raw-Math.round(raw))<.000001?Math.round(raw):raw,phase=step-Math.floor(step)
  return {frame:Math.floor(step*4+.000001)%8,lift:Math.sin(Math.PI*phase)*.11}
}
