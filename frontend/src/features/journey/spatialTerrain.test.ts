import {expect,it} from 'vitest'
import {terrainSample,validTerrainGrid} from './spatialTerrain'
const grid={width:2,height:2,minimum:0,maximum:30,values:[0,10,20,30]}
it('samples elevation continuously between measured grid points',()=>{
  expect(terrainSample(grid,.5,.5)).toBeCloseTo(15)
  expect(terrainSample(grid,-1,-1)).toBe(0)
  expect(terrainSample(grid,2,2)).toBeCloseTo(30,3)
  expect(terrainSample(grid,.50001,.5)-terrainSample(grid,.49999,.5)).toBeLessThan(.001)
})
it('rejects incomplete or non-finite relief before building GPU geometry',()=>{
  expect(validTerrainGrid(grid)).toBe(true)
  expect(validTerrainGrid({...grid,values:[0,10,20]})).toBe(false)
  expect(validTerrainGrid({...grid,values:[0,NaN,20,30]})).toBe(false)
  expect(validTerrainGrid({...grid,maximum:0})).toBe(false)
})
