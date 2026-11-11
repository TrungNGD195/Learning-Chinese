import { it, expect } from 'vitest'
import { PerspectiveCamera, Vector3 } from 'three'
import { FORWARD_GATE_STEP, forwardCameraFrame, forwardRoadPoint } from './forwardGeometry'

it.each([[320, 692], [390, 692], [1024, 786], [1440, 786]])('keeps Bo and each landing plaque in frame at %ipx', (width, height) => {
  const camera = new PerspectiveCamera(width < 700 ? 56 : 51, width / height, .5, 300)
  function project(x: number, y: number, z: number) {
    const p = new Vector3(x, y, z).project(camera)
    return { x: (p.x + 1) * width / 2, y: (1 - p.y) * height / 2 }
  }
  for (let progress = 0; progress <= 15; progress += 1 / 16) {
    const frame = forwardCameraFrame(progress * FORWARD_GATE_STEP, 0, 1)
    camera.position.set(frame.eye.x, frame.eye.y, frame.eye.z)
    camera.lookAt(frame.look.x, frame.look.y, frame.look.z);camera.updateMatrixWorld()
    const foot = project(frame.bo.x, frame.bo.y, frame.bo.z)
    const head = project(frame.bo.x, frame.bo.y + 4.8, frame.bo.z)
    const avatarHeight = Math.abs(head.y - foot.y)
    // The entire atlas cell is stricter than the visible alpha silhouette.
    expect(foot.x - avatarHeight * .6).toBeGreaterThan(0)
    expect(foot.x + avatarHeight * .6).toBeLessThan(width)
    expect(foot.y - avatarHeight * 1.5).toBeGreaterThan(0)
    expect(foot.y).toBeLessThan(height - 110)
    if (Number.isInteger(progress)) {
      const gate = forwardRoadPoint(progress * FORWARD_GATE_STEP)
      const right = forwardRoadPoint(progress * FORWARD_GATE_STEP, 4.7)
      const p = project(gate.x, gate.y + 8.45, gate.z), e = project(right.x, right.y + 8.45, right.z)
      const dx = e.x - p.x, dy = e.y - p.y, angle = Math.atan2(dy, dx)
      const scale = Math.min(1.3, Math.hypot(dx, dy) / 120)
      const halfWidth = (240 * Math.abs(Math.cos(angle)) + 57 * Math.abs(Math.sin(angle))) * scale / 2
      expect(p.x - halfWidth).toBeGreaterThan(0)
      expect(p.x + halfWidth).toBeLessThan(width)
    }
  }
})
