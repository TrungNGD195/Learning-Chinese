import * as THREE from 'three'
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js'
import { chapterRange, spatialCameraFrame, spatialFov, spatialGround, spatialHeading, spatialLayout, spatialPoint, spatialRoadHalfWidth, SPATIAL_GATE_SPAN, SPATIAL_TREAD } from './spatialWallPath'
import { terrainSample,validTerrainGrid,type TerrainGrid } from './spatialTerrain'
import { spatialGateReveal } from './spatialGateReveal'
import { milestoneWatchtower } from './milestoneWatchtower'
import { chapterEntryPose } from './chapterEntry'
import { loadJourneyTerrainAsset } from '../../lib/api/client'

export type GateProjection = { x:number; y:number; width:number; height:number; opacity:number; visible:boolean; transform?:string }
type RenderOptions={entry?:number;chapterEntry?:number;side?:number;moving?:boolean}
export type ForwardWallScene={
  ready:Promise<void>;resize:(w:number,h:number)=>void
  render:(p:number,options?:RenderOptions)=>{gates:GateProjection[];heading:number;stage:string;avatar:{x:number;y:number;height:number;elevation:number;opacity:number;brightness:number};world:{x:number;y:number;z:number;distance:number;fog:number;gateStages:{index:number;opacity:number;reveal:number;mist:number}[];graphics:{software:boolean;pixelRatio:number;calls:number;triangles:number};landmarks:{id:string;x:number;y:number;visible:boolean}[]}}
  dispose:()=>void
}
type Point={x:number;y:number;z:number}

export function createForwardWallScene(canvas:HTMLCanvasElement,gateColors:string[],invalidate:()=>void,level=1):ForwardWallScene {
  if(typeof WebGL2RenderingContext==='undefined')throw new Error('WebGL unavailable')
  const context=canvas.getContext('webgl2',{alpha:false,antialias:true,powerPreference:'high-performance'})
  if(!context)throw new Error('WebGL unavailable')
  const renderer=new THREE.WebGLRenderer({canvas,context,antialias:true,alpha:false})
  const debug=context.getExtension('WEBGL_debug_renderer_info')
  const software=debug&&/swiftshader|llvmpipe|software/i.test(String(context.getParameter(debug.UNMASKED_RENDERER_WEBGL)))
  const stillRatio=software?.7:Math.min(window.devicePixelRatio||1,1.5),movingRatio=software?.4:stillRatio
  let drawingRatio=stillRatio
  renderer.setPixelRatio(drawingRatio)
  renderer.outputColorSpace=THREE.SRGBColorSpace
  renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.05
  renderer.shadowMap.enabled=!software;renderer.shadowMap.type=THREE.PCFSoftShadowMap
  const scene=new THREE.Scene(),fog=new THREE.FogExp2('#c3ceca',.0038)
  scene.fog=fog;scene.background=new THREE.Color('#b7cbd3')
  const camera=new THREE.PerspectiveCamera(54,1,.15,1800)
  scene.add(new THREE.HemisphereLight('#f1f5f6','#717b70',1.65))
  const sun=new THREE.DirectionalLight('#fff8ed',2.4);sun.castShadow=!software
  sun.shadow.mapSize.set(1024,1024);sun.shadow.camera.left=-28;sun.shadow.camera.right=28;sun.shadow.camera.top=28;sun.shadow.camera.bottom=-28;sun.shadow.camera.near=1;sun.shadow.camera.far=150;sun.shadow.normalBias=.05;sun.shadow.bias=-.0003
  sun.position.set(-25,50,30);scene.add(sun,sun.target)
  const layout=spatialLayout(level,gateColors.length)
  const end=chapterRange(3).end+100
  const geometries=new Set<THREE.BufferGeometry>(),materials=new Set<THREE.Material>(),textures=new Set<THREE.Texture>()
  const gateMeshes:{s:number;previousS:number;mesh:THREE.Mesh;material:THREE.MeshBasicMaterial;index?:number}[]=[]
  const mistBanks:{s:number;previousS:number;group:THREE.Group;material:THREE.MeshBasicMaterial;parts:THREE.Mesh[]}[]=[]
  const watchtowers:{s:number;previousS:number;tower:ReturnType<typeof milestoneWatchtower>}[]=[]
  const landmarks:{id:string;point:THREE.Vector3}[]=[]
  let width=1,height=1,disposed=false,chapterFrameRendered=false
  let boShadow:THREE.Mesh|null=null
  let sky:THREE.Mesh|null=null
  let dem:TerrainGrid|null=null
  let updateDetail:((distance:number)=>void)=()=>{}
  const pending=new Set<()=>void>()
  const images=new Map<string,HTMLImageElement>()
  const image=(name:string,path:string)=>new Promise<void>((resolve,reject)=>{
    const img=new Image();images.set(name,img);pending.add(resolve)
    img.onload=()=>{pending.delete(resolve);resolve()};img.onerror=()=>{pending.delete(resolve);reject(new Error(`World artwork unavailable: ${name}`))};img.src=path
  })
  const texture=(img:HTMLImageElement|HTMLCanvasElement,repeat=true)=>{
    const t=img instanceof HTMLCanvasElement?new THREE.CanvasTexture(img):new THREE.Texture(img)
    t.colorSpace=THREE.SRGBColorSpace;t.wrapS=t.wrapT=repeat?THREE.RepeatWrapping:THREE.ClampToEdgeWrapping
    t.anisotropy=Math.min(4,renderer.capabilities.getMaxAnisotropy());t.needsUpdate=true;textures.add(t);return t
  }
  const material=(parameters:THREE.MeshStandardMaterialParameters)=>{const m=new THREE.MeshStandardMaterial({roughness:.95,metalness:0,...parameters});materials.add(m);return m}
  const unlit=(parameters:THREE.MeshBasicMaterialParameters)=>{const m=new THREE.MeshBasicMaterial(parameters);materials.add(m);return m}
  const geometry=<T extends THREE.BufferGeometry>(g:T)=>{geometries.add(g);return g}
  const rounded=geometry(new RoundedBoxGeometry(1,1,1,1,.035))
  const object=new THREE.Object3D()
  function batch(entries:{point:Point;w:number;h:number;d:number;angle?:number;color?:string}[],mat:THREE.Material){
    const mesh=new THREE.InstancedMesh(rounded,mat,entries.length)
    entries.forEach((e,i)=>{object.position.set(e.point.x,e.point.y,e.point.z);object.rotation.set(0,e.angle??0,0);object.scale.set(e.w,e.h,e.d);object.updateMatrix();mesh.setMatrixAt(i,object.matrix);if(e.color)mesh.setColorAt(i,new THREE.Color(e.color))})
    mesh.computeBoundingSphere();scene.add(mesh);return mesh
  }
  function mesh(g:THREE.BufferGeometry,m:THREE.Material,p?:Point){const result=new THREE.Mesh(g,m);if(m instanceof THREE.MeshStandardMaterial){result.castShadow=true;result.receiveShadow=true};if(p)result.position.set(p.x,p.y,p.z);scene.add(result);return result}
  function surface(quads:{p:Point[];uv:number[]}[],mat:THREE.Material){
    const p:number[]=[],uv:number[]=[],indices:number[]=[]
    for(const q of quads){const n=p.length/3;for(const v of q.p)p.push(v.x,v.y,v.z);uv.push(...q.uv);indices.push(n,n+2,n+1,n+1,n+2,n+3)}
    const g=geometry(new THREE.BufferGeometry());g.setAttribute('position',new THREE.Float32BufferAttribute(p,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));g.setIndex(indices);g.computeVertexNormals();return mesh(g,mat)
  }
  const terrainSamples=Array.from({length:Math.ceil((end+80)/8)},(_,i)=>{const s=i*8-40;return {...spatialPoint(s),s}})
  const terrainBounds={minX:Math.min(...terrainSamples.map(p=>p.x))-400,maxX:Math.max(...terrainSamples.map(p=>p.x))+400,minZ:Math.min(...terrainSamples.map(p=>p.z))-400,maxZ:250}
  function terrainHeight(x:number,z:number){
    let closest=terrainSamples[0],best=Infinity
    for(const p of terrainSamples){const d=(x-p.x)**2+(z-p.z)**2;if(d<best){best=d;closest=p}}
    const d=Math.sqrt(best)
    const u=(x-terrainBounds.minX)/(terrainBounds.maxX-terrainBounds.minX),v=(z-terrainBounds.minZ)/(terrainBounds.maxZ-terrainBounds.minZ)
    const relief=dem?(terrainSample(dem,u,v)-dem.minimum)/(dem.maximum-dem.minimum):0
    const distant=-65+220*relief+closest.y*.28
    const cliff=closest.y-5-Math.max(0,d-8)*.85+Math.min(1,Math.max(0,(d-10)/18))*7*Math.sin(x*.13+z*.12)
    const t=Math.max(0,Math.min(1,(d-35)/95)),blend=t*t*(3-2*t)
    return cliff*(1-blend)+distant*blend
  }
  function build(){
    const treadMap=texture(images.get('paving')!),treadMat=material({map:treadMap,bumpMap:treadMap,bumpScale:.055,color:'#e0e1db',side:THREE.DoubleSide})
    const wallTex=texture(images.get('wall')!),wallBump=wallTex.clone();wallBump.colorSpace=THREE.NoColorSpace;textures.add(wallBump)
    const wall=material({map:wallTex,bumpMap:wallBump,bumpScale:.075,color:'#e3e1d8',side:THREE.DoubleSide})
    const faceMat=material({map:treadMap,bumpMap:treadMap,bumpScale:.055,color:'#c5c8c1',side:THREE.DoubleSide})
    const block=material({map:wallTex,bumpMap:wallBump,bumpScale:.04,color:'#d8d8cd'})
    const cap=material({map:wallTex,bumpMap:wallBump,bumpScale:.04,color:'#ddded7'})
    const rockTex=texture(images.get('rock')!),rock=material({map:rockTex,bumpMap:rockTex,bumpScale:.22,color:'#b3c0bc',vertexColors:true,side:THREE.DoubleSide})
    const treads:{p:Point[];uv:number[]}[]=[],faces:typeof treads=[]
    for(let s=-48;s<end;s+=SPATIAL_TREAD){
      const next=s+SPATIAL_TREAD,y=spatialGround(s+.001,true),ny=spatialGround(next+.001,true)
      const a=spatialPoint(s,-spatialRoadHalfWidth(s)),b=spatialPoint(s,spatialRoadHalfWidth(s)),c=spatialPoint(next,-spatialRoadHalfWidth(next)),d=spatialPoint(next,spatialRoadHalfWidth(next))
      treads.push({p:[{...a,y},{...b,y},{...c,y},{...d,y}],uv:[-spatialRoadHalfWidth(s)/8,s/4,spatialRoadHalfWidth(s)/8,s/4,-spatialRoadHalfWidth(next)/8,next/4,spatialRoadHalfWidth(next)/8,next/4]})
      if(ny>y+.001)faces.push({p:[{...c,y},{...d,y},{...c,y:ny},{...d,y:ny}],uv:[-spatialRoadHalfWidth(next)/8,y/4,spatialRoadHalfWidth(next)/8,y/4,-spatialRoadHalfWidth(next)/8,ny/4,spatialRoadHalfWidth(next)/8,ny/4]})
    }
    surface(treads,treadMat);surface(faces,faceMat)
    const verticals:typeof treads=[],caps:typeof treads=[]
    const merlons:{point:Point;w:number;h:number;d:number;angle:number;color:string;distance:number}[]=[]
    for(let s=-48;s<end;s+=1.2){
      const next=s+1.2
      for(const sign of [-1,1]){
        for(const outer of [0,.75]){
          const a=spatialPoint(s,sign*(spatialRoadHalfWidth(s)+outer)),b=spatialPoint(next,sign*(spatialRoadHalfWidth(next)+outer))
          verticals.push({p:[{...a,y:a.y-7},{...a,y:a.y+1.35},{...b,y:b.y-7},{...b,y:b.y+1.35}],uv:[s/8,-7/8,s/8,1.35/8,next/8,-7/8,next/8,1.35/8]})
        }
        const a=spatialPoint(s,sign*spatialRoadHalfWidth(s)),b=spatialPoint(s,sign*(spatialRoadHalfWidth(s)+.75)),c=spatialPoint(next,sign*spatialRoadHalfWidth(next)),d=spatialPoint(next,sign*(spatialRoadHalfWidth(next)+.75))
        caps.push({p:[{...a,y:a.y+1.37},{...b,y:b.y+1.37},{...c,y:c.y+1.37},{...d,y:d.y+1.37}],uv:[0,s/8,.1,s/8,0,next/8,.1,next/8]})
      }
    }
    surface(verticals,wall);surface(caps,cap)
    for(let s=-48;s<end;s+=2.4)for(const sign of [-1,1]){
      const p=spatialPoint(s,sign*(spatialRoadHalfWidth(s)+.38));p.y+=1.49
      merlons.push({point:p,w:.79,h:.75,d:1.30,angle:-spatialHeading(s),color:Math.sin(s*7)>0?'#ffffff':'#e2e0d3',distance:s})
    }
    const nearBlocks=new THREE.InstancedMesh(rounded,block,merlons.length),farBlocks=new THREE.InstancedMesh(geometry(new THREE.BoxGeometry(1,1,1)),block,merlons.length)
    nearBlocks.instanceMatrix.setUsage(THREE.DynamicDrawUsage);farBlocks.instanceMatrix.setUsage(THREE.DynamicDrawUsage);scene.add(nearBlocks,farBlocks)
    let detailAt=Infinity
    updateDetail=distance=>{
      if(Math.abs(distance-detailAt)<3)return
      detailAt=distance;let near=0,far=0
      for(const e of merlons){
        const close=Math.abs(e.distance-distance)<55,target=close?nearBlocks:farBlocks,index=close?near++:far++
        object.position.set(e.point.x,e.point.y,e.point.z);object.rotation.set(0,e.angle,0);object.scale.set(e.w,e.h,e.d);object.updateMatrix();target.setMatrixAt(index,object.matrix);target.setColorAt(index,new THREE.Color(e.color))
      }
      for(const [target,count] of [[nearBlocks,near],[farBlocks,far]] as const){target.count=count;target.visible=count>0;target.instanceMatrix.needsUpdate=true;if(target.instanceColor)target.instanceColor.needsUpdate=true;if(count)target.computeBoundingSphere()}
    }
    // One smooth, textured mountain field; no screen-aligned scenery plate.
    const {minX,maxX,minZ,maxZ}=terrainBounds,cols=software?80:216,rows=software?116:286
    const positions:number[]=[],uv:number[]=[],indices:number[]=[]
    for(let r=0;r<=rows;r++)for(let c=0;c<=cols;c++){
      const x=minX+(maxX-minX)*c/cols,z=minZ+(maxZ-minZ)*r/rows
      positions.push(x,terrainHeight(x,z),z);uv.push(x/35,z/35)
      if(r&&c){const a=(r-1)*(cols+1)+c-1,b=a+1,d=a+cols+1;indices.push(a,d,b,b,d,d+1)}
    }
    const terrain=geometry(new THREE.BufferGeometry());terrain.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));terrain.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));terrain.setIndex(indices);terrain.computeVertexNormals()
    const normals=terrain.getAttribute('normal'),colors:number[]=[]
    for(let i=0;i<positions.length/3;i++){
      const steep=1-Math.abs(normals.getY(i)),green=new THREE.Color('#728775'),stone=new THREE.Color('#b0b3a6')
      green.lerp(stone,Math.min(1,steep*1.8));green.multiplyScalar(.88+.10*Math.sin(positions[i*3]*.04+positions[i*3+2]*.025));colors.push(green.r,green.g,green.b)
    }
    terrain.setAttribute('color',new THREE.Float32BufferAttribute(colors,3));mesh(terrain,rock)
    const surfaceY=(x:number,z:number)=>{
      const fx=Math.max(0,Math.min(cols-.001,(x-minX)/(maxX-minX)*cols)),fz=Math.max(0,Math.min(rows-.001,(z-minZ)/(maxZ-minZ)*rows))
      const c=Math.floor(fx),r=Math.floor(fz),tx=fx-c,tz=fz-r,a=r*(cols+1)+c
      const y00=positions[a*3+1],y10=positions[(a+1)*3+1],y01=positions[(a+cols+1)*3+1],y11=positions[(a+cols+2)*3+1]
      return tx+tz<=1?y00+(y10-y00)*tx+(y01-y00)*tz:y11+(y01-y11)*(1-tx)+(y10-y11)*(1-tz)
    }
    const pineImage=images.get('pines')!,treeGeo=geometry(new THREE.PlaneGeometry(1,1))
    const pineMats=Array.from({length:3},(_,i)=>{const t=texture(pineImage,false);t.repeat.set(1/3,1);t.offset.set(i/3,0);return unlit({map:t,side:THREE.DoubleSide,alphaTest:.08,transparent:false,color:'#ffffff'})})
    const roots=[.349,.453,.510]
    const treeEntries:{x:number;y:number;z:number;h:number;angle:number;variant:number}[]=[]
    for(let i=0;i<(software?300:1100);i++){
      const s=(i*.61803398875%1)*end,side=i%2?1:-1,offset=side*(14+(Math.sin(i*31.7)*.5+.5)*100),p=spatialPoint(s,offset)
      p.y=surfaceY(p.x,p.z)-.2
      const variant=i%3,h=9+(Math.sin(i*12.3)*.5+.5)*14,angle=i*2.39996
      treeEntries.push({...p,h,angle,variant})
      if(i%24===0)landmarks.push({id:`pine-${i}`,point:new THREE.Vector3(p.x,p.y+h*.65,p.z)})
    }
    for(let i=0;i<16;i++){
      const s=50+i*70,p=spatialPoint(s,(i%2?1:-1)*16),h=27+4*Math.sin(i*5)
      p.y=surfaceY(p.x,p.z)-.15;treeEntries.push({...p,h,angle:-spatialHeading(s)+.4,variant:i%2})
      landmarks.push({id:`overlook-pine-${i}`,point:new THREE.Vector3(p.x,p.y+h*.65,p.z)})
    }
    for(let variant=0;variant<3;variant++){
      const entries=treeEntries.filter(e=>e.variant===variant),trees=new THREE.InstancedMesh(treeGeo,pineMats[variant],entries.length*2)
      entries.forEach((e,i)=>{for(let n=0;n<2;n++){
        const angle=e.angle+n*Math.PI/2,shift=(.5-roots[variant])*e.h
        object.position.set(e.x+shift*Math.cos(angle),e.y+e.h*.45,e.z-shift*Math.sin(angle));object.rotation.set(0,angle,0);object.scale.set(e.h,e.h,1);object.updateMatrix();trees.setMatrixAt(i*2+n,object.matrix)
      }});trees.castShadow=true;trees.computeBoundingSphere();scene.add(trees)
    }
    // Stone watchtowers are actual depth-bearing structures on adjacent ridges.
    const towerEntries:{point:Point;w:number;h:number;d:number;angle?:number}[]=[]
    const towerFace=(w:number)=>{
      const shape=new THREE.Shape();shape.moveTo(-w/2,0);shape.lineTo(w/2,0);shape.lineTo(w/2,8);shape.lineTo(-w/2,8);shape.closePath()
      const arch=(center:number,r:number,bottom:number,top:number)=>{const hole=new THREE.Path();hole.moveTo(center-r,bottom);hole.lineTo(center-r,top-r);hole.absarc(center,top-r,r,Math.PI,0,true);hole.lineTo(center+r,bottom);hole.closePath();shape.holes.push(hole)}
      arch(0,1.45,0,4.9);arch(-w*.32,.64,3.1,5.8);arch(w*.32,.64,3.1,5.8)
      const g=geometry(new THREE.ExtrudeGeometry(shape,{depth:.65,bevelEnabled:true,bevelSize:.035,bevelThickness:.035,bevelSegments:1,curveSegments:10}))
      const uv=g.getAttribute('uv');for(let i=0;i<uv.count;i++)uv.setXY(i,uv.getX(i)/8,uv.getY(i)/8);return g
    }
    const frontFace=towerFace(12),sideFace=towerFace(10),towerRoof=geometry(new RoundedBoxGeometry(11.5,.4,9.5,2,.06))
    for(const s of [130,305,525,740,930,1080]){
      const p=spatialPoint(s,24),y=surfaceY(p.x,p.z)
      const group=new THREE.Group();group.position.set(p.x,y,p.z);group.rotation.y=-spatialHeading(s);scene.add(group)
      for(const sign of [-1,1]){
        const front=new THREE.Mesh(frontFace,wall);front.position.z=sign*4.5;group.add(front)
        const side=new THREE.Mesh(sideFace,wall);side.position.x=sign*5.5;side.rotation.y=Math.PI/2;group.add(side)
      }
      const ceiling=new THREE.Mesh(towerRoof,cap);ceiling.position.y=7.45;group.add(ceiling)
      const angle=-spatialHeading(s),c=Math.cos(angle),sn=Math.sin(angle)
      const crown=(x:number,z:number)=>({x:p.x+x*c+z*sn,y:y+8.6,z:p.z-x*sn+z*c})
      for(const side of [-1,1])for(let i=0;i<5;i++){
        towerEntries.push({point:crown((i-2)*2.3,side*4.5),w:1.5,h:1.2,d:1.0,angle})
        towerEntries.push({point:crown(side*5.5,(i-2)*1.9),w:1,h:1.2,d:1.2,angle})
      }
      landmarks.push({id:`tower-${s}`,point:new THREE.Vector3(p.x,y+8,p.z)})
    }
    batch(towerEntries,wall)
    const gateTexture=texture(images.get('gate')!,false),gateMat=unlit({map:gateTexture,side:THREE.DoubleSide,transparent:true,alphaTest:.025,depthWrite:true})
    const gateW=8.5,gateH=gateW*974/1615,gateGeo=geometry(new THREE.PlaneGeometry(gateW,gateH))
    const mistTexture=texture(images.get('cloud')!,false),mistGeo=geometry(new THREE.PlaneGeometry(14,14/3))
    const addMist=(s:number,previousS:number)=>{
      const p=spatialPoint(s-.8),group=new THREE.Group();group.position.set(p.x,p.y,p.z);group.rotation.y=-spatialHeading(s);scene.add(group)
      const material=unlit({map:mistTexture,side:THREE.DoubleSide,transparent:true,depthWrite:false,opacity:0})
      const parts=[new THREE.Mesh(mistGeo,material),new THREE.Mesh(mistGeo,material)]
      parts.forEach(part=>group.add(part));mistBanks.push({s,previousS,group,material,parts})
    }
    const addGate=(s:number,index?:number,previousS=s-SPATIAL_GATE_SPAN)=>{
      const gateMaterial=gateMat.clone();materials.add(gateMaterial)
      const p=spatialPoint(s),g=mesh(gateGeo,gateMaterial,{...p,y:spatialGround(s,true)+gateH*(.5-.027721)})
      g.rotation.y=-spatialHeading(s);g.updateMatrixWorld();gateMeshes.push({s,previousS,mesh:g,material:gateMaterial,index});addMist(s,previousS)
    }
    for(let l=1;l<=3;l++){
      const range=chapterRange(l),count=l===1?16:l===2?10:15,lead=l>1?1:0
      if(l===level)for(let i=0;i<gateColors.length;i++)addGate(layout.start+(i+layout.leadIn)*layout.interval,i,layout.start+(i+layout.leadIn-1)*layout.interval)
      else for(let i=0;i<count;i++)addGate(range.start+(i+lead)*SPATIAL_GATE_SPAN)
    }
    for(const l of [1,2,3]){
      const s=chapterRange(l).end,p=spatialPoint(s),previousS=s-(l===level?layout.interval:SPATIAL_GATE_SPAN)
      const tower=milestoneWatchtower(wall,{geometries,materials},l);textures.add(tower.labelTexture)
      tower.group.position.set(p.x,p.y,p.z);tower.group.rotation.y=-spatialHeading(s);scene.add(tower.group)
      watchtowers.push({s,previousS,tower});addMist(s,previousS)
      landmarks.push({id:`milestone-hsk-${l}`,point:new THREE.Vector3(p.x,p.y+5,p.z)})
    }
    const cloudMat=material({map:texture(images.get('cloud')!,false),transparent:true,depthWrite:false,side:THREE.DoubleSide,opacity:.45})
    for(let i=0;i<12;i++){
      const p=spatialPoint(i*87+30,(i%2?1:-1)*140);p.y-=35
      const cloud=mesh(geometry(new THREE.PlaneGeometry(180,60)),cloudMat,p);cloud.rotation.y=-spatialHeading(i*87+30)
    }
    const skyGeo=geometry(new THREE.SphereGeometry(800,40,24))
    const skyMat=new THREE.ShaderMaterial({side:THREE.BackSide,depthWrite:false,uniforms:{top:{value:new THREE.Color('#93aeba')},bottom:{value:new THREE.Color('#dde1dc')}},vertexShader:'varying vec3 vWorld;void main(){vec4 p=modelMatrix*vec4(position,1.0);vWorld=p.xyz;gl_Position=projectionMatrix*viewMatrix*p;}',fragmentShader:'uniform vec3 top;uniform vec3 bottom;varying vec3 vWorld;void main(){float h=normalize(vWorld-cameraPosition).y;gl_FragColor=vec4(mix(bottom,top,smoothstep(-.08,.6,h)),1.);\n#include <colorspace_fragment>\n}'})
    materials.add(skyMat);sky=mesh(skyGeo,skyMat);sky.renderOrder=-1000;sky.frustumCulled=false
    const shadowCanvas=document.createElement('canvas');shadowCanvas.width=128;shadowCanvas.height=128
    const sc=shadowCanvas.getContext('2d')!,gradient=sc.createRadialGradient(64,64,5,64,64,62);gradient.addColorStop(0,'rgba(35,40,28,.30)');gradient.addColorStop(1,'rgba(35,40,28,0)');sc.fillStyle=gradient;sc.fillRect(0,0,128,128)
    const sm=new THREE.MeshBasicMaterial({map:texture(shadowCanvas,false),transparent:true,depthWrite:false});materials.add(sm)
    boShadow=mesh(geometry(new THREE.PlaneGeometry(2.3,1.65)),sm);boShadow.rotation.x=-Math.PI/2
  }
  const ready=Promise.all([
    image('paving','/academy/great-wall/realistic-v1/paving.webp'),image('wall','/academy/great-wall/realistic-v1/masonry.webp'),
    image('rock','/academy/great-wall/uphill-rock-v1.webp'),image('gate','/academy/great-wall/painted-v2/gate.webp'),
    image('pines','/academy/great-wall/realistic-v1/pines.webp'),
    image('cloud','/academy/great-wall/journey-cloud-v1.webp'),document.fonts?.load('600 60px "Noto Sans"')??Promise.resolve(),
    loadJourneyTerrainAsset().then(data=>{if(!validTerrainGrid(data))throw new Error('Terrain invalid');dem=data}),
  ]).then(()=>{if(disposed)return;build();invalidate()})
  const viewMatrix=new THREE.Matrix4(),v=new THREE.Vector3()
  function project(p:THREE.Vector3){v.copy(p).project(camera);return{x:(v.x*.5+.5)*width,y:(-.5*v.y+.5)*height,visible:v.z>-1&&v.z<1&&Math.abs(v.x)<1.3&&Math.abs(v.y)<1.3}}
  function gateProjection(g:THREE.Mesh):GateProjection{
    const w=8.5,h=w*974/1615,baseW=1000,baseH=baseW*h/w
    const points=[new THREE.Vector4(-w/2,h/2,0,1),new THREE.Vector4(w/2,h/2,0,1),new THREE.Vector4(-w/2,-h/2,0,1)]
    viewMatrix.multiplyMatrices(camera.projectionMatrix,camera.matrixWorldInverse).multiply(g.matrixWorld)
    for(const p of points)p.applyMatrix4(viewMatrix)
    const [o,px,py]=points,u=px.clone().sub(o),t=py.clone().sub(o),n=o.w
    if(points.some(p=>p.w<.25))return{x:0,y:0,width:baseW,height:baseH,visible:false,opacity:0}
    const matrix=[width/2*(u.x+u.w)/baseW,height/2*(-u.y+u.w)/baseW,0,u.w/baseW,
      width/2*(t.x+t.w)/baseH,height/2*(-t.y+t.w)/baseH,0,t.w/baseH,0,0,1,0,width/2*(o.x+o.w),height/2*(-o.y+o.w),0,o.w].map(value=>value/n)
    const point=project(g.position),scale=(width/2*Math.abs(px.x/px.w-o.x/o.w))/baseW
    return{x:0,y:0,width:baseW,height:baseH,transform:`matrix3d(${matrix.join(',')})`,visible:point.visible&&scale>.12,opacity:1}
  }
  return {
    ready,
    resize(w,h){chapterFrameRendered=false;width=Math.max(1,w);height=Math.max(1,h);renderer.setSize(width,height,false);camera.aspect=width/height;camera.fov=spatialFov(width,height);camera.updateProjectionMatrix()},
    render(progress,options={}){
      const ratio=options.moving?movingRatio:stillRatio;if(ratio!==drawingRatio){drawingRatio=ratio;renderer.setPixelRatio(ratio)}
      const s=layout.start+progress*layout.interval,frame=spatialCameraFrame(s,height,camera.fov,options.entry??0)
      const chapter=options.chapterEntry===undefined?null:chapterEntryPose(s,options.chapterEntry)
      if(chapter){Object.assign(frame.bo,chapter.point);frame.boDistance=chapter.distance}
      updateDetail(s)
      camera.position.set(frame.eye.x,frame.eye.y,frame.eye.z);camera.lookAt(frame.look.x,frame.look.y,frame.look.z);camera.updateMatrixWorld()
      fog.density=.0025-Math.min(.001,Math.max(0,frame.eye.y)*.000004)
      sky?.position.copy(camera.position)
      sun.target.position.set(frame.look.x,spatialGround(s),frame.look.z);sun.position.copy(sun.target.position).add(new THREE.Vector3(-25,50,30));sun.target.updateMatrixWorld()
      if(boShadow){boShadow.visible=!chapter;boShadow.position.set(frame.bo.x,spatialGround(frame.boDistance,true)+.025,frame.bo.z)}
      const gates:GateProjection[]=Array.from({length:gateColors.length},()=>({x:0,y:0,width:0,height:0,opacity:0,visible:false}))
      const gateStages:{index:number;opacity:number;reveal:number;mist:number}[]=[]
      for(const g of gateMeshes){
        const state=spatialGateReveal(frame.boDistance,g.s,g.previousS),{opacity}=state
        if(g.index!==undefined)gateStages.push({index:g.index,...state})
        g.material.opacity=opacity
        g.material.depthWrite=opacity>=.999
        g.mesh.visible=Math.abs(g.s-s)<180&&opacity>.02
        if(g.index!==undefined&&g.mesh.visible&&Math.abs(g.s-s)<layout.interval*.49)
          gates[g.index]={...gateProjection(g.mesh),opacity}
      }
      for(const bank of mistBanks){
        const {reveal,mist}=spatialGateReveal(frame.boDistance,bank.s,bank.previousS)
        bank.group.visible=mist>.01&&bank.s-frame.boDistance>0&&bank.s-frame.boDistance<SPATIAL_GATE_SPAN*2.2
        bank.material.opacity=mist*.85
        bank.parts.forEach((part,index)=>{part.position.set((index?1:-1)*(1.7+reveal*3.5),2.6+index*1.8+reveal*.8,index*.1)})
      }
      for(const marker of watchtowers)marker.tower.setReveal(spatialGateReveal(frame.boDistance,marker.s,marker.previousS).opacity)
      // The tower/camera stay still during the short portal walk. Project the
      // actor every frame, while keeping that expensive world render cached.
      if(!chapter||!chapterFrameRendered)renderer.render(scene,camera)
      chapterFrameRendered=!!chapter
      const feet=project(new THREE.Vector3(frame.bo.x,frame.bo.y,frame.bo.z)),head=project(new THREE.Vector3(frame.bo.x,frame.bo.y+2.25,frame.bo.z))
      return{gates,heading:frame.heading,stage:'spatial',avatar:{x:feet.x,y:feet.y,height:Math.max(80,feet.y-head.y),elevation:frame.bo.y,opacity:chapter?.opacity??1,brightness:chapter?.brightness??1},
        world:{x:frame.eye.x,y:frame.eye.y,z:frame.eye.z,distance:s,fog:fog.density,gateStages,graphics:{software:!!software,pixelRatio:drawingRatio,calls:renderer.info.render.calls,triangles:renderer.info.render.triangles},landmarks:landmarks.map(l=>({id:l.id,...project(l.point)}))}}
    },
    dispose(){disposed=true;for(const finish of pending)finish();pending.clear();for(const img of images.values()){img.onload=null;img.onerror=null};images.clear();scene.traverse(object=>{if(object instanceof THREE.InstancedMesh)object.dispose()});geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());textures.forEach(t=>t.dispose());renderer.dispose();renderer.forceContextLoss()},
  }
}
