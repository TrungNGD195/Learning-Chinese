import * as THREE from 'three'

type Resources = { geometries: Set<THREE.BufferGeometry>; materials: Set<THREE.Material> }
type Box = { x: number; y: number; z: number; w: number; h: number; d: number; roll?: number; pitch?:number }

/** Depth-bearing masonry, open arched passage and a tiled guardroom roof. */
export function milestoneWatchtower(stone: THREE.MeshBasicMaterial|THREE.MeshLambertMaterial|THREE.MeshStandardMaterial, resources: Resources, level: number) {
  const group = new THREE.Group(), owned: THREE.Material[] = []
  const geo = <T extends THREE.BufferGeometry>(geometry: T) => { resources.geometries.add(geometry);return geometry }
  const mat = (color: string) => { const m = stone.clone();m.color.set(color);m.transparent=true;owned.push(m);resources.materials.add(m);return m }
  const masonry = mat('#dedbd2'), trim = mat('#e2dfd5'), roof = mat('#626b68'), tile = mat('#858a83'), dark = mat('#171d19')
  masonry.name='watchtower-masonry';trim.name='watchtower-trim';dark.name='watchtower-ceiling'
  roof.map=null;tile.map=null;dark.map=null
  const boxes = new Map<THREE.Material, Box[]>()
  const box = (material: THREE.Material, x: number, y: number, z: number, w: number, h: number, d: number, roll = 0,pitch=0) => {
    const list = boxes.get(material) ?? [];list.push({ x, y, z, w, h, d, roll,pitch });boxes.set(material, list)
  }
  function facade(w: number, h: number, openings: { x: number; bottom: number; top: number; r: number }[]) {
    const shape = new THREE.Shape();shape.moveTo(-w / 2, 0)
    const door=openings.find(opening=>opening.bottom===0)
    if(door){shape.lineTo(door.x-door.r,0);shape.lineTo(door.x-door.r,door.top-door.r);shape.absarc(door.x,door.top-door.r,door.r,Math.PI,0,true);shape.lineTo(door.x+door.r,0)}
    shape.lineTo(w / 2, 0);shape.lineTo(w / 2, h);shape.lineTo(-w / 2, h);shape.closePath()
    for (const opening of openings) {
      if(opening.bottom===0)continue
      const { x, bottom, top, r } = opening, hole = new THREE.Path()
      hole.moveTo(x-r,bottom);hole.lineTo(x-r,top-r);hole.absarc(x,top-r,r,Math.PI,0,true);hole.lineTo(x+r,bottom);hole.closePath();shape.holes.push(hole)
    }
    const result = geo(new THREE.ExtrudeGeometry(shape,{depth:.65,bevelEnabled:true,bevelSize:.025,bevelThickness:.025,bevelSegments:1,curveSegments:12}))
    const uv = result.getAttribute('uv');for(let i=0;i<uv.count;i++)uv.setXY(i,uv.getX(i)/3,uv.getY(i)/3)
    return result
  }
  const front = facade(11,6.2,[{x:0,bottom:0,top:5.1,r:1.5},{x:-3.6,bottom:2.1,top:4.2,r:.55},{x:3.6,bottom:2.1,top:4.2,r:.55}])
  const side = facade(7,6.2,[{x:-1.8,bottom:2.2,top:4.3,r:.55},{x:1.8,bottom:2.2,top:4.3,r:.55}])
  const entrance=new THREE.Mesh(front,masonry);entrance.name='watchtower-front';entrance.position.z=3.5;group.add(entrance)
  const interior=new THREE.MeshBasicMaterial({color:'#020302',side:THREE.DoubleSide,transparent:true,toneMapped:false,fog:false})
  interior.name='watchtower-black-interior';owned.push(interior);resources.materials.add(interior)
  const darkPortal=new THREE.Mesh(geo(new THREE.PlaneGeometry(10.98,6.22)),interior);darkPortal.name='watchtower-dark-interior';darkPortal.position.set(0,3.09,3.47);group.add(darkPortal)
  const darkUpper=new THREE.Mesh(geo(new THREE.PlaneGeometry(6.58,2.8)),interior);darkUpper.name='watchtower-dark-interior';darkUpper.position.set(0,7.85,1.42);group.add(darkUpper)
  for(const sign of [-1,1]) {
    const flank = new THREE.Mesh(side,masonry);flank.position.x=sign>0?5.5:-6.15;flank.rotation.y=Math.PI/2;group.add(flank)
    // Rear piers frame one broad open exit. A second arched facade creates a
    // false stone crossbar when viewed uphill through the front entrance.
    box(masonry,sign*4.25,3.1,-3.8,2.5,6.2,.65)
    // Carry the masonry down into the sloped approach instead of leaving the
    // facade's underside and side-wall wedges suspended over the last tread.
    box(masonry,sign*3.5,-1.7,3.82,4,3.4,.65)
    box(masonry,sign*5.65,-1.7,0,.95,3.4,7.8)
    const shade=new THREE.Mesh(geo(new THREE.PlaneGeometry(6.98,6.2)),interior);shade.name='watchtower-dark-interior';shade.position.set(sign*5.47,3.1,0);shade.rotation.y=Math.PI/2;group.add(shade)
    box(trim,0,6.25,sign*3.65,12.25,.32,.95)
    box(trim,sign*5.7,6.25,0,.95,.32,8.2)
    box(masonry,0,6.65,sign*3.65,12,.55,.65)
    box(masonry,sign*5.7,6.65,0,.65,.55,7.8)
    for(let i=-3;i<=3;i++)box(masonry,i*1.75,7.25,sign*3.65,1.05,.85,.8)
    for(let i=-1;i<=1;i++)box(masonry,sign*5.7,7.25,i*2.1,.8,.85,1.05)
  }
  // The lower level remains open across the road; no opaque cube blocks passage.
  box(dark,0,5.9,0,10,.12,7)
  const upper = facade(6.6,2.8,[{x:-2,bottom:.55,top:2,r:.38},{x:0,bottom:.25,top:2.1,r:.48},{x:2,bottom:.55,top:2,r:.38}])
  for(const sign of [-1,1]) {
    const face = new THREE.Mesh(upper,masonry);face.position.set(0,6.45,sign>0?1.45:-3.2);group.add(face)
    box(masonry,sign*3.2,7.85,-.55,.6,2.8,4.6)
  }
  const roofShape = new THREE.Shape()
  // The ridge runs across the facade, exposing the pitched tiles from the
  // climbing approach instead of a blank triangular gable.
  roofShape.moveTo(-2.7,0);roofShape.lineTo(-2.9,.18);roofShape.lineTo(-2.4,.14);roofShape.lineTo(0,3.2);roofShape.lineTo(2.4,.14);roofShape.lineTo(2.9,.18);roofShape.lineTo(2.7,0);roofShape.closePath()
  const roofGeometry=geo(new THREE.ExtrudeGeometry(roofShape,{depth:8.8,bevelEnabled:true,bevelSize:.035,bevelThickness:.035,bevelSegments:1}))
  roofGeometry.translate(0,0,-4.4)
  const roofMesh=new THREE.Mesh(roofGeometry,roof);roofMesh.rotation.y=Math.PI/2;roofMesh.position.set(0,9.1,-.6);group.add(roofMesh)
  for(let i=0;i<=20;i++)for(const sign of [-1,1])box(tile,-4.2+i*.42,10.8,-.6+sign*1.28,.1,.065,4.15,0,sign*Math.atan2(3.2,2.7))
  box(tile,0,12.37,-.6,9.3,.22,.22)
  for(const sign of [-1,1])box(tile,sign*4.45,12.53,-.6,.36,.4,.32)
  const boxGeometry=geo(new THREE.BoxGeometry(1,1,1)),object=new THREE.Object3D()
  for(const [material,entries] of boxes) {
    const batch=new THREE.InstancedMesh(boxGeometry,material,entries.length)
    entries.forEach((part,index)=>{object.position.set(part.x,part.y,part.z);object.rotation.set(part.pitch??0,0,part.roll??0);object.scale.set(part.w,part.h,part.d);object.updateMatrix();batch.setMatrixAt(index,object.matrix)})
    batch.castShadow=true;batch.receiveShadow=true;batch.computeBoundingSphere();group.add(batch)
  }
  const canvas=document.createElement('canvas');canvas.width=512;canvas.height=144
  const ctx=canvas.getContext('2d')!;ctx.fillStyle='#173f36';ctx.fillRect(0,0,512,144);ctx.strokeStyle='#d3b778';ctx.lineWidth=8;ctx.strokeRect(5,5,502,134);ctx.fillStyle='#fff5d9';ctx.font='600 80px "Noto Sans", sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(`HSK ${level}`,256,77)
  const labelTexture=new THREE.CanvasTexture(canvas);labelTexture.colorSpace=THREE.SRGBColorSpace
  const labelMaterial=mat('#ffffff');labelMaterial.map=labelTexture
  const plaque=new THREE.Mesh(geo(new THREE.PlaneGeometry(2.1,.59)),labelMaterial);plaque.position.set(0,5.65,4.19);group.add(plaque)
  return { group, labelTexture, setReveal(opacity: number) {
    group.visible=opacity>.02
    for(const material of owned){material.opacity=opacity;material.depthWrite=opacity>=.999}
  } }
}
