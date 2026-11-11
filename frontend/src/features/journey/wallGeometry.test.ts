import { expect, it } from 'vitest'
import { WALL_WIDTH, dampWallCamera, wallCameraCenterAt, wallCameraX, wallCenterAt, wallStopPositions } from './wallGeometry'

it.each([10,15,16,20,45])('keeps %i stops vertically separated on one continuous ascent', count=>{
  const {points,sections,height,imageScaleY}=wallStopPositions(count)
  expect(points).toHaveLength(count)
  for(let index=0;index<count;index++) {
    const point=points[index]
    expect(point.x).toBe(wallCenterAt(point.y * imageScaleY,sections))
    expect(point.x).toBeGreaterThan(180)
    expect(point.x).toBeLessThan(WALL_WIDTH-140)
    expect(point.y).toBeGreaterThan(0)
    expect(point.y).toBeLessThan(height)
    if(index)expect(points[index-1].y-point.y).toBeGreaterThanOrEqual(200)
  }
})

it('bounds camera movement, tracks the wall and keeps reduced motion stable',()=>{
  const offsets=new Set<number>()
  for(let y=0;y<4608;y+=64) {
    const x=wallCameraX(y,3,390,.78,false)
    expect(x).toBeLessThanOrEqual(0)
    expect(x).toBeGreaterThanOrEqual(390-1024*.78)
    offsets.add(Math.round(x))
    expect(wallCameraX(y,3,390,.78,true)).toBe(wallCameraX(0,3,390,.78,true))
  }
  expect(offsets.size).toBeGreaterThan(15)
})

it('keeps camera position and velocity continuous through every turn and panel joint', () => {
  const h = .001
  for (const sections of [1, 2, 3, 5]) {
    for (let y = 96; y < sections * 1536; y += 96) {
      const center = wallCameraCenterAt(y, sections)
      const before = wallCameraCenterAt(y - h, sections), after = wallCameraCenterAt(y + h, sections)
      expect(Math.abs(after - before)).toBeLessThan(.01)
      expect(Math.abs((center - before) / h - (after - center) / h)).toBeLessThan(.001)
    }
    for (let y = 0; y < sections * 1536; y += 96) {
      const a = wallCameraCenterAt(y, sections), b = wallCameraCenterAt(y + 96, sections)
      for (let offset = 0; offset <= 96; offset += 8) {
        const center = wallCameraCenterAt(y + offset, sections)
        expect(center).toBeGreaterThanOrEqual(Math.min(a, b) - .001)
        expect(center).toBeLessThanOrEqual(Math.max(a, b) + .001)
      }
    }
  }
})

it('damps wheel steps without bounce and responds immediately to reversed input', () => {
  let camera = -100
  const first = dampWallCamera(camera, -300, 1000 / 60)
  expect(first).toBeLessThan(camera)
  expect(first).toBeGreaterThan(-300)
  camera = first
  expect(dampWallCamera(camera, 0, 1000 / 60)).toBeGreaterThan(camera)
  for (let frame = 0; frame < 50; frame++) {
    const next = dampWallCamera(camera, -300, 1000 / 60)
    expect(next).toBeLessThanOrEqual(camera)
    expect(next).toBeGreaterThanOrEqual(-300)
    camera = next
  }
  expect(camera).toBe(-300)
})

it('uses elapsed time so camera easing matches at different refresh rates', () => {
  const simulate = (hz: number) => {
    let x = 0
    for (let frame = 0; frame < hz / 5; frame++) x = dampWallCamera(x, -200, 1000 / hz)
    return x
  }
  expect(simulate(60)).toBeCloseTo(simulate(120), 8)
  expect(dampWallCamera(-50, -100, 0)).toBe(-50)
})
