import { ASCENT_RISE, ASCENT_SPAN, ASCENT_TREAD, ascentSteps, ascentY, type AscentPoint } from './paintedAscent'

export type PaintedPlacement = { x: number; y: number; width: number; height: number }
type Edge = readonly [number, number, number]
const landscape: readonly Edge[] = [[.63,.285,.65],[.71,.238,.665],[.82,.174,.685],[1,.105,.71],[1.25,-.02,.75]]
const portrait: readonly Edge[] = [[.58,.26,.77],[.70,.10,.97],[.90,-.15,1.15],[1.25,-.40,1.40]]

function edges(y: number, placement: PaintedPlacement, tall: boolean) {
  const points = tall ? portrait : landscape
  const sourceY = (y - placement.y) / placement.height
  const found = points.findIndex((_, i) => i < points.length - 1 && sourceY <= points[i + 1][0])
  const index = found < 0 ? points.length - 2 : found
  const a = points[index], b = points[index + 1]
  const t = (sourceY - a[0]) / (b[0] - a[0])
  return [placement.x + (a[1] + (b[1] - a[1]) * t) * placement.width,
    placement.x + (a[2] + (b[2] - a[2]) * t) * placement.width]
}

// The source is orthographic. World-space UVs preserve the stone scale instead
// of stretching a perspective photograph across each step.
function quad(ctx: CanvasRenderingContext2D, image: HTMLImageElement, source: number[], points: AscentPoint[]) {
  const [sx, sy, sw, sh] = source
  for (let half = 0; half < 2; half++) {
    const [p, x, y] = half ? [points[2], points[3], points[1]] : [points[0], points[1], points[3]]
    const sign = half ? -1 : 1
    const a = (x.x - p.x) / (sw * sign), b = (x.y - p.y) / (sw * sign)
    const c = (y.x - p.x) / (sh * sign), d = (y.y - p.y) / (sh * sign)
    const u = sx + (half ? sw : 0), v = sy + (half ? sh : 0)
    ctx.save();ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(x.x,x.y);ctx.lineTo(y.x,y.y);ctx.closePath();ctx.clip()
    ctx.transform(a,b,c,d,p.x-a*u-c*v,p.y-b*u-d*v);ctx.drawImage(image,0,0);ctx.restore()
  }
}

export function paintMovingTreads(ctx: CanvasRenderingContext2D, texture: HTMLImageElement, progress: number, height: number, placement: PaintedPlacement, tall: boolean) {
  const outline = tall ? portrait : landscape
  ctx.save();ctx.beginPath()
  outline.forEach(([y,left], i) => { const x = placement.x+left*placement.width, py=placement.y+y*placement.height;if(i)ctx.lineTo(x,py);else ctx.moveTo(x,py) })
  for (const [y,,right] of [...outline].reverse()) ctx.lineTo(placement.x+right*placement.width,placement.y+y*placement.height)
  ctx.closePath();ctx.clip()
  const density=texture.naturalWidth/8, panel=texture.naturalHeight/2
  const sx=density, sw=density*6, travel=progress*ASCENT_SPAN
  for (const step of ascentSteps(progress,height)) {
    const [nearLeft,nearRight] = edges(step.front,placement,tall)
    const [lowLeft,lowRight] = edges(step.bottom,placement,tall)
    ctx.globalAlpha=Math.max(0,Math.min(1,(9-step.near)/2))
    // Subdivide in depth for perspective correction, including a UV wrap that
    // can fall inside a tread. Absolute world coordinates survive lesson changes.
    let remaining=ASCENT_TREAD*density, distance=0
    let v=((step.id*ASCENT_TREAD*density)%panel+panel)%panel
    while(remaining>.001) {
      const length=Math.min(remaining,panel-v)
      const slices=4
      for(let i=0;i<slices;i++) {
        const a=distance+length*i/slices,b=distance+length*(i+1)/slices
        const yNear=ascentY(step.near+a/density,step.id*ASCENT_RISE,travel,height)
        const yFar=ascentY(step.near+b/density,step.id*ASCENT_RISE,travel,height)
        const [nl,nr]=edges(yNear,placement,tall),[fl,fr]=edges(yFar,placement,tall)
        quad(ctx,texture,[sx,v+length*i/slices,sw,length/slices],[{x:nl,y:yNear},{x:nr,y:yNear},{x:fr,y:yFar},{x:fl,y:yFar}])
      }
      distance+=length;remaining-=length;v=0
    }
    const course=((step.id%4)+4)%4
    const faceY=panel+(course+.5)*panel/4-ASCENT_RISE*density/2
    const facePoints=[{x:nearLeft,y:step.front},{x:nearRight,y:step.front},{x:lowRight,y:step.bottom},{x:lowLeft,y:step.bottom}]
    quad(ctx,texture,[sx,faceY,sw,ASCENT_RISE*density],facePoints)
    // A riser faces away from the overhead light. No repeated painted bright
    // border is added along the tread, and the source grain keeps its scale.
    ctx.fillStyle='rgba(70,48,25,.13)';ctx.beginPath();facePoints.forEach((p,i)=>{if(i)ctx.lineTo(p.x,p.y);else ctx.moveTo(p.x,p.y)});ctx.closePath();ctx.fill()
  }
  ctx.restore()
}
