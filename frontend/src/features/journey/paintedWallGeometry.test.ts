import { it, expect } from 'vitest'
import { paintedWallFrame } from './paintedWallGeometry'

it.each([[320,692],[390,692],[798,786],[1214,786]])('keeps the full painted gate and Bo in view at %ipx', (width,height) => {
  for(let index=0;index<16;index++) {
    const frame=paintedWallFrame(index,16,width,height)
    const gate=frame.gates[index]
    expect(gate.visible).toBe(true)
    expect(gate.x).toBeGreaterThanOrEqual(0)
    expect(gate.x+gate.width).toBeLessThanOrEqual(width)
    expect(gate.y).toBeGreaterThan(0)
    expect(gate.y+gate.height).toBeLessThan(height-120)
  }
  for(let p=0;p<15;p+=.025) {
    const {avatar}=paintedWallFrame(p,16,width,height)
    expect(avatar.x-avatar.height*.6).toBeGreaterThan(0)
    expect(avatar.x+avatar.height*.6).toBeLessThan(width)
    expect(avatar.y-avatar.height*1.5).toBeGreaterThan(0)
    expect(avatar.y).toBeLessThan(height-110)
  }
})
it('follows the landing, climb, bend and next landing sequence without a passed gate ghost',()=>{
  expect(paintedWallFrame(3,16,1200,786).stage).toBe('landing')
  expect(paintedWallFrame(3.36,16,1200,786).stage).toBe('climb')
  expect(paintedWallFrame(3.7,16,1200,786).stage).toBe('bend')
  const halfway=paintedWallFrame(3.75,16,1200,786)
  expect(halfway.gates[3].visible).toBe(false)
  expect(paintedWallFrame(4,16,1200,786).gates[4].visible).toBe(true)
  expect(paintedWallFrame(15,16,1200,786).stage).toBe('landing')
})
