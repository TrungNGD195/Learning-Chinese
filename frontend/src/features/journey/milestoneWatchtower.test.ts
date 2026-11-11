import { afterEach, expect, it, vi } from 'vitest'
import * as THREE from 'three'
import { milestoneWatchtower } from './milestoneWatchtower'
import { chapterRange, spatialCameraFrame, spatialFov, spatialHeading, spatialPoint } from './spatialWallPath'

afterEach(()=>vi.restoreAllMocks())
function tower(){
  vi.spyOn(HTMLCanvasElement.prototype,'getContext').mockReturnValue({fillRect:vi.fn(),strokeRect:vi.fn(),fillText:vi.fn()} as unknown as CanvasRenderingContext2D)
  const resources={geometries:new Set<THREE.BufferGeometry>(),materials:new Set<THREE.Material>()}
  const model=milestoneWatchtower(new THREE.MeshLambertMaterial({side:THREE.DoubleSide}),resources,1)
  return {model,dispose:()=>{resources.geometries.forEach(g=>g.dispose());resources.materials.forEach(m=>m.dispose());model.labelTexture.dispose()}}
}

it('keeps masonry clear of the full-height portal and backs its interior with black',()=>{
  const {model,dispose}=tower();model.group.updateMatrixWorld(true)
  try{
    for(const height of [1,2.25,3.3,4]){
      const ray=new THREE.Raycaster(new THREE.Vector3(0,height,12),new THREE.Vector3(0,0,-1),0,24)
      const hits=ray.intersectObject(model.group,true)
      expect(hits.length).toBeGreaterThan(0)
      expect(hits.every(hit=>hit.object.name==='watchtower-dark-interior')).toBe(true)
      const inside=(hits[0].object as THREE.Mesh).material as THREE.MeshBasicMaterial
      expect(inside.isMeshBasicMaterial).toBe(true)
      expect(inside.color.getHexString()).toBe('020302')
    }
    const masonry=new THREE.Raycaster(new THREE.Vector3(4,1.5,12),new THREE.Vector3(0,0,-1),0,24)
    expect(masonry.intersectObject(model.group,true).length).toBeGreaterThan(0)
  }finally{dispose()}
})

it('does not project a rear masonry arch across the uphill entrance',()=>{
  const {model,dispose}=tower();model.group.updateMatrixWorld(true)
  try{
    const eye=new THREE.Vector3(0,-3.5,24)
    for(let height=.25;height<5;height+=.25) {
      const direction=new THREE.Vector3(0,height,3.5).sub(eye).normalize()
      const hit=new THREE.Raycaster(eye,direction,0,50).intersectObject(model.group,true)[0]
      if(hit) {
        const object=hit.object as THREE.Mesh
        const material=object.material as THREE.Material
        expect(material.name).not.toBe('watchtower-masonry')
        expect(material.name).not.toBe('watchtower-trim')
      }
    }
  }finally{dispose()}
})

it.each([[320,692],[390,692],[824,786],[1214,786]])('frames the complete watchtower at %ipx wide',(w,h)=>{
  const {model,dispose}=tower()
  try{
    const bounds=new THREE.Box3().setFromObject(model.group)
    // The foundation continues below the sloped terrain; frame the structure
    // above its threshold, not the intentionally buried support courses.
    bounds.min.y=Math.max(0,bounds.min.y)
    for(const level of [1,2,3]){
      const s=chapterRange(level).end,p=spatialPoint(s),camera=new THREE.PerspectiveCamera(spatialFov(w,h),w/h,.15,1800),frame=spatialCameraFrame(s,h,camera.fov)
      model.group.position.set(p.x,p.y,p.z);model.group.rotation.y=-spatialHeading(s);model.group.updateMatrixWorld(true)
      camera.position.set(frame.eye.x,frame.eye.y,frame.eye.z);camera.lookAt(frame.look.x,frame.look.y,frame.look.z);camera.updateMatrixWorld()
      for(const x of [bounds.min.x,bounds.max.x])for(const y of [bounds.min.y,bounds.max.y])for(const z of [bounds.min.z,bounds.max.z]){
        const projected=new THREE.Vector3(x,y,z).applyMatrix4(model.group.matrixWorld).project(camera)
        expect(Math.abs(projected.x)).toBeLessThan(1)
        expect(projected.y).toBeLessThan(1)
      }
    }
  }finally{dispose()}
})
