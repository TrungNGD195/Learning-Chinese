export type TerrainGrid={width:number;height:number;minimum:number;maximum:number;values:number[]}
export function validTerrainGrid(value:unknown):value is TerrainGrid {
  if(!value||typeof value!=='object')return false
  const g=value as TerrainGrid
  return Number.isInteger(g.width)&&g.width>1&&Number.isInteger(g.height)&&g.height>1&&Number.isFinite(g.minimum)&&Number.isFinite(g.maximum)&&g.maximum>g.minimum&&Array.isArray(g.values)&&g.values.length===g.width*g.height&&g.values.every(Number.isFinite)
}
export function terrainSample(g:TerrainGrid,u:number,v:number) {
  const x=Math.max(0,Math.min(g.width-1.000001,u*(g.width-1))),y=Math.max(0,Math.min(g.height-1.000001,v*(g.height-1)))
  const i=Math.floor(x),j=Math.floor(y),tx=x-i,ty=y-j
  const a=g.values[j*g.width+i],b=g.values[j*g.width+i+1],c=g.values[(j+1)*g.width+i],d=g.values[(j+1)*g.width+i+1]
  return (a*(1-tx)+b*tx)*(1-ty)+(c*(1-tx)+d*tx)*ty
}
