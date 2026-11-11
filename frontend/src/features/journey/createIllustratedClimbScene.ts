import * as THREE from 'three'
import {RoundedBoxGeometry} from 'three/addons/geometries/RoundedBoxGeometry.js'
import {ROUTE_BO_LEAD,ROUTE_END,ROUTE_SPAN,ROUTE_TREAD,routeGateVisibility,routeHalfWidth,routeHeading,routeHeight,routeLevelStart,routePoint,routeTowerDistance,routeTowerEntry} from './firstPersonRoute'
import {milestoneWatchtower} from './milestoneWatchtower'

export type ClimbProjection={x:number;y:number;width:number;height:number;opacity:number}
export type ClimbFrame={action:string;progress:number;gateIndex:number;avatar:{x:number;y:number;frame:number;pose:string;bounds:ClimbProjection;world:{x:number;y:number;z:number;distance:number}};camera:{x:number;y:number;z:number;yaw:number;pitch:number;zoom:number};gate:ClimbProjection;plaque:ClimbProjection;landmarks:{id:string;x:number;y:number;z:number;world:{x:number;y:number;z:number}}[];world:{distance:number;gateDistance:number;mist:number;passedGates:number;roadStrips:number;triangles:number;towerDistance:number|null;towerEntered:boolean}}
export type IllustratedScene={ready:Promise<void>;resize:(w:number,h:number)=>void;render:(progress:number,direction:1|-1,moving:boolean)=>ClimbFrame;dispose:()=>void}
type Options={level:number;names:string[];nextLevel?:number}
type Point={x:number;y:number;z:number}
const GATE_WIDTH=12.4,GATE_HEIGHT=GATE_WIDTH*974/1615

/** One continuous world-space road. The camera walks on it behind Bo; no
 * normalized scene phase, painted-road backdrop or gate-to-gate teleport. */
export function createIllustratedClimbScene(canvas:HTMLCanvasElement,{level,names,nextLevel}:Options):IllustratedScene{
  const renderer=new THREE.WebGLRenderer({canvas,alpha:false,antialias:true,powerPreference:'high-performance'})
  renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,1.5));renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.NoToneMapping
  const scene=new THREE.Scene();scene.background=new THREE.Color('#bfd9e6');scene.fog=new THREE.FogExp2('#dbe7dd',.0035)
  const camera=new THREE.PerspectiveCamera(54,1,.12,2200)
  const geometries:THREE.BufferGeometry[]=[],materials:THREE.Material[]=[],textures:THREE.Texture[]=[]
  const instances:THREE.InstancedMesh[]=[]
  const start=routeLevelStart(level),loader=new THREE.TextureLoader(),landmarks:{id:string;point:THREE.Vector3}[]=[]
  const paintedTrees:{mesh:THREE.InstancedMesh;roots:{x:number;y:number;z:number;h:number;anchor:number}[]}[]=[]
  let width=1,height=1,disposed=false,away:THREE.Texture,toward:THREE.Texture
  const load=async(path:string)=>{const t=await loader.loadAsync(path);t.colorSpace=THREE.SRGBColorSpace;t.anisotropy=Math.min(4,renderer.capabilities.getMaxAnisotropy());if(disposed)t.dispose();else textures.push(t);return t}
  const material=(p:THREE.MeshBasicMaterialParameters)=>{const m=new THREE.MeshBasicMaterial(p);materials.push(m);return m}
  const geometry=<T extends THREE.BufferGeometry>(g:T)=>{geometries.push(g);return g}
  const gates:{s:number;mesh:THREE.Mesh;material:THREE.MeshBasicMaterial;label:THREE.Mesh;clouds:THREE.Sprite[];cloudMaterial:THREE.SpriteMaterial}[]=[]
  const bo=new THREE.Mesh(),shadow=new THREE.Mesh()
  const towerS=routeTowerDistance(level,names.length)
  let tower:ReturnType<typeof milestoneWatchtower>|undefined
  const font=document.fonts?.load('700 64px "Noto Serif"').catch(()=>[])??Promise.resolve([])
  function quads(data:{points:Point[];uv:number[]}[],mat:THREE.Material){
    const verts:number[]=[],uv:number[]=[],index:number[]=[]
    for(const q of data){const n=verts.length/3;for(const p of q.points)verts.push(p.x,p.y,p.z);uv.push(...q.uv);index.push(n,n+2,n+1,n+1,n+2,n+3)}
    const g=geometry(new THREE.BufferGeometry());g.setAttribute('position',new THREE.Float32BufferAttribute(verts,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));g.setIndex(index);g.computeVertexNormals();const mesh=new THREE.Mesh(g,mat);scene.add(mesh);return mesh
  }
  const ready=Promise.all([load('/academy/great-wall/painted-v2/ascent-stone-atlas.webp'),load('/academy/great-wall/uphill-rock-v1.webp'),load('/academy/great-wall/spatial-v1/pines.webp'),load('/academy/great-wall/forward-mountains-v1.webp'),load('/academy/great-wall/painted-v2/gate.webp'),load('/academy/great-wall/mountain-mist-v1.webp'),load('/academy/great-wall/bo-walk-away-v1.webp'),load('/academy/great-wall/bo-walk-toward-v1.webp'),font]).then(([stone,rock,pines,mountains,gateImage,cloud,back,front])=>{
    if(disposed)return;away=back;toward=front;away.repeat.set(.25,.5);toward.repeat.set(.25,.5)
    stone.wrapS=stone.wrapT=THREE.RepeatWrapping;rock.wrapS=rock.wrapT=THREE.RepeatWrapping
    const top=material({map:stone,color:'#f9efda',side:THREE.DoubleSide}),face=material({map:stone,color:'#d5c2a0',side:THREE.DoubleSide}),wall=material({map:stone,color:'#e6d7ba',side:THREE.DoubleSide}),cap=material({map:stone,color:'#f4e6c9'})
    const tops:{points:Point[];uv:number[]}[]=[],risers:typeof tops=[],walls:typeof tops=[],caps:typeof tops=[]
    const near=-54,end=ROUTE_END
    for(let s=near;s<end;s+=ROUTE_TREAD){
      const next=s+ROUTE_TREAD,y=routeHeight(s+.001),ny=routeHeight(next+.001),wa=routeHalfWidth(s),wb=routeHalfWidth(next),a=routePoint(s,-wa),b=routePoint(s,wa),c=routePoint(next,-wb),d=routePoint(next,wb)
      tops.push({points:[{...a,y},{...b,y},{...c,y},{...d,y}],uv:[-wa/8,s/8,wa/8,s/8,-wb/8,next/8,wb/8,next/8]})
      if(ny>y+.01)risers.push({points:[{...c,y},{...d,y},{...c,y:ny},{...d,y:ny}],uv:[-wb/8,y/8,wb/8,y/8,-wb/8,ny/8,wb/8,ny/8]})
      for(const side of [-1,1]){
        const left=routePoint(s,side*wa),right=routePoint(next,side*wb)
        walls.push({points:[{...left,y:y-.35},{...right,y:y-.35},{...left,y:y+1.12},{...right,y:y+1.12}],uv:[s/8,0,next/8,0,s/8,1.47/8,next/8,1.47/8]})
        const outerA=routePoint(s,side*(wa+.62)),outerB=routePoint(next,side*(wb+.62))
        walls.push({points:[{...outerA,y:y-8},{...outerB,y:y-8},{...outerA,y:y+1.12},{...outerB,y:y+1.12}],uv:[s/8,0,next/8,0,s/8,9.12/8,next/8,9.12/8]})
        caps.push({points:[{...left,y:y+1.12},{...outerA,y:y+1.12},{...right,y:y+1.12},{...outerB,y:y+1.12}],uv:[0,s/8,.62/8,s/8,0,next/8,.62/8,next/8]})
      }
    }
    quads(tops,top);quads(risers,face);quads(walls,wall);quads(caps,cap)
    const merlonGeometry=geometry(new RoundedBoxGeometry(.68,.67,1.18,1,.045)),object=new THREE.Object3D()
    const merlonUV=merlonGeometry.getAttribute('uv');for(let i=0;i<merlonUV.count;i++)merlonUV.setXY(i,merlonUV.getX(i)*.25,merlonUV.getY(i)*.125)
    const entries:{s:number;side:number}[]=[];for(let s=near;s<end;s+=ROUTE_TREAD)for(const side of [-1,1])entries.push({s,side})
    const merlons=new THREE.InstancedMesh(merlonGeometry,cap,entries.length);instances.push(merlons)
    entries.forEach(({s,side},i)=>{const at=s+ROUTE_TREAD*.5,p=routePoint(at,side*(routeHalfWidth(at)+.31));object.position.set(p.x,routeHeight(s+.001)+1.455,p.z);object.rotation.set(0,-routeHeading(s),0);object.scale.set(1,1,1);object.updateMatrix();merlons.setMatrixAt(i,object.matrix)});merlons.computeBoundingSphere();scene.add(merlons)
    // Painted rock and foliage live at fixed world positions outside the one road.
    const samples=Array.from({length:Math.ceil(end/5)+1},(_,i)=>({s:i*5,...routePoint(i*5)}))
    const minX=Math.min(...samples.map(p=>p.x))-150,maxX=Math.max(...samples.map(p=>p.x))+150,minZ=Math.min(...samples.map(p=>p.z))-160,maxZ=80
    function terrainY(x:number,z:number){let nearest=samples[0],best=Infinity;for(const p of samples){const d=(x-p.x)**2+(z-p.z)**2;if(d<best){best=d;nearest=p}}const distance=Math.sqrt(best),t=Math.max(0,Math.min(1,(distance-4)/14)),blend=t*t*(3-2*t);return nearest.y-1.8-distance*.65+(Math.sin(x*.045+z*.027)*Math.min(16,distance*.25)+Math.sin(z*.061)*5)*blend}
    const vertices:number[]=[],uv:number[]=[],idx:number[]=[],colors:number[]=[],cols=76,rows=180
    for(let r=0;r<=rows;r++)for(let c=0;c<=cols;c++){
      const x=minX+(maxX-minX)*c/cols,z=minZ+(maxZ-minZ)*r/rows,y=terrainY(x,z)
      vertices.push(x,y,z);uv.push(x/24,z/24)
      const steep=Math.min(1,Math.abs(terrainY(x+1,z)-terrainY(x-1,z))/4),color=new THREE.Color('#6c8a55').lerp(new THREE.Color('#c2ac7f'),steep);color.multiplyScalar(.88+.12*Math.sin(x*.12+z*.07));colors.push(color.r,color.g,color.b)
      if(r&&c){const a=(r-1)*(cols+1)+c-1,b=a+1,d=a+cols+1;idx.push(a,d,b,b,d,d+1)}
    }
    const terrain=geometry(new THREE.BufferGeometry());terrain.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));terrain.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));terrain.setAttribute('color',new THREE.Float32BufferAttribute(colors,3));terrain.setIndex(idx);scene.add(new THREE.Mesh(terrain,material({map:rock,vertexColors:true,side:THREE.DoubleSide})))
    mountains.wrapS=THREE.MirroredRepeatWrapping;mountains.repeat.set(4,1);mountains.offset.x=.5
    const sky=new THREE.ShaderMaterial({side:THREE.BackSide,depthWrite:false,uniforms:{paintedSky:{value:mountains},skyColour:{value:new THREE.Color('#bfd9e6')}},vertexShader:'varying vec2 skyUV;void main(){skyUV=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',fragmentShader:'uniform sampler2D paintedSky;uniform vec3 skyColour;varying vec2 skyUV;void main(){vec3 paint=texture2D(paintedSky,vec2(skyUV.x*4.0+.5,skyUV.y)).rgb;gl_FragColor=vec4(mix(paint,skyColour,smoothstep(.82,1.0,skyUV.y)),1.0);\n#include <colorspace_fragment>\n}'})
    materials.push(sky);const backdrop=new THREE.Mesh(geometry(new THREE.CylinderGeometry(1750,1750,1800,64,1,true)),sky);backdrop.position.set(50,400,-350);scene.add(backdrop)
    const treeGeometry=geometry(new THREE.PlaneGeometry(1,1)),roots=[.349,.453,.510]
    const pineMaterials:THREE.MeshBasicMaterial[]=[]
    for(let variant=0;variant<3;variant++){
      const map=pines.clone();map.repeat.set(1/3,1);map.offset.set(variant/3,0);map.needsUpdate=true;textures.push(map)
      const m=material({map,side:THREE.DoubleSide,alphaTest:.12}),trees=new THREE.InstancedMesh(treeGeometry,m,120);pineMaterials.push(m);instances.push(trees)
      const anchors:{x:number;y:number;z:number;h:number;anchor:number}[]=[]
      for(let i=0;i<120;i++){
        const s=(i*6.55+variant*2.1)%end,side=i%2?1:-1,offset=side*(12+(Math.sin(i*17.1+variant)*.5+.5)*65),p=routePoint(s,offset),h=11+(Math.sin(i*9.7)*.5+.5)*10
        p.y=terrainY(p.x,p.z)
        anchors.push({...p,h,anchor:roots[variant]})
        object.position.set(p.x,p.y+h*.405,p.z);object.rotation.set(0,0,0);object.scale.set(h,h,1);object.updateMatrix();trees.setMatrixAt(i,object.matrix)
        if(i<9)landmarks.push({id:`pine-${variant}-${i}`,point:new THREE.Vector3(p.x,p.y+h*.7,p.z)})
      }
      trees.computeBoundingSphere();scene.add(trees);paintedTrees.push({mesh:trees,roots:anchors})
    }
    for(let i=0,s=10;s<end;s+=ROUTE_SPAN,i++){
      const side=i%2?1:-1,variant=i%3,p=routePoint(s,side*16),h=17+2*Math.sin(i*2.1),tree=new THREE.InstancedMesh(treeGeometry,pineMaterials[variant],1);p.y=terrainY(p.x,p.z);object.position.set(p.x,p.y+h*.405,p.z);object.rotation.set(0,0,0);object.scale.set(h,h,1);object.updateMatrix();tree.setMatrixAt(0,object.matrix);tree.computeBoundingSphere();instances.push(tree);scene.add(tree);paintedTrees.push({mesh:tree,roots:[{...p,h,anchor:roots[variant]}]});landmarks.push({id:`near-pine-${i}`,point:new THREE.Vector3(p.x,p.y+h*.7,p.z)})
    }
    const gateWidth=GATE_WIDTH,gateHeight=GATE_HEIGHT,gateGeometry=geometry(new THREE.PlaneGeometry(gateWidth,gateHeight))
    for(let i=0;i<names.length;i++){
      const s=start+(i+1)*ROUTE_SPAN,p=routePoint(s),m=material({map:gateImage,transparent:true,alphaTest:.025,side:THREE.DoubleSide,depthWrite:true}),mesh=new THREE.Mesh(gateGeometry,m)
      mesh.position.set(p.x,p.y+gateHeight*(.972279-.5),p.z);mesh.rotation.y=-routeHeading(s);scene.add(mesh)
      const text=document.createElement('canvas');text.width=512;text.height=128;const ctx=text.getContext('2d')!;ctx.fillStyle='#fff6dc';ctx.textAlign='center';ctx.textBaseline='middle';ctx.font='700 74px "Noto Serif"';ctx.fillText(names[i],256,67,490)
      const labelTexture=new THREE.CanvasTexture(text);labelTexture.colorSpace=THREE.SRGBColorSpace;textures.push(labelTexture)
      const label=new THREE.Mesh(geometry(new THREE.PlaneGeometry(gateWidth*.371517,gateHeight*.132444)),material({map:labelTexture,transparent:true,depthWrite:false,side:THREE.DoubleSide}))
      label.position.set(gateWidth*(.314551+.371517/2-.5),gateHeight*(.5-.277207-.132444/2),.025);label.renderOrder=3;mesh.add(label)
      const cloudMaterial=new THREE.SpriteMaterial({map:cloud,transparent:true,depthWrite:false,fog:true});materials.push(cloudMaterial)
      // Dissipate the ends of each cloud volume instead of exposing the
      // rectangular edge of a mist tile as the camera turns around it.
      cloudMaterial.onBeforeCompile=shader=>{shader.fragmentShader=shader.fragmentShader.replace('#include <alphamap_fragment>','#include <alphamap_fragment>\n diffuseColor.a *= smoothstep(0.0,0.14,vMapUv.x)*(1.0-smoothstep(0.86,1.0,vMapUv.x));')}
      const clouds=Array.from({length:2},(_,j)=>{const sprite=new THREE.Sprite(cloudMaterial);sprite.scale.set(16,4.8,1);sprite.position.set(p.x+(j?2:-2),p.y+1.6+j*.6,p.z+(j?1.5:3));scene.add(sprite);return sprite})
      gates.push({s,mesh,material:m,label,clouds,cloudMaterial})
    }
    if(nextLevel){
      const owned={geometries:new Set<THREE.BufferGeometry>(),materials:new Set<THREE.Material>()}
      tower=milestoneWatchtower(wall,owned,nextLevel)
      const p=routePoint(towerS),heading=routeHeading(towerS)
      // Align the black entrance, rather than the guardroom centre, to the
      // landing. The masonry continues down into the steps on both sides.
      tower.group.position.set(p.x+Math.sin(heading)*3.47,p.y,p.z-Math.cos(heading)*3.47);tower.group.rotation.y=-heading
      tower.group.scale.y=.6
      tower.group.traverse(object=>{if(object instanceof THREE.InstancedMesh)instances.push(object)})
      geometries.push(...owned.geometries);materials.push(...owned.materials);textures.push(tower.labelTexture);scene.add(tower.group)
      landmarks.push({id:'chapter-tower',point:new THREE.Vector3(p.x,p.y+5,p.z)})
    }
    const bodyH=1.8,bodyGeometry=geometry(new THREE.PlaneGeometry(bodyH*256/212,bodyH*320/212));bodyGeometry.translate(0,(312/320-.5)*bodyH*320/212,0)
    bo.geometry.dispose();(bo.material as THREE.Material).dispose();bo.geometry=bodyGeometry;bo.material=material({map:away,transparent:true,alphaTest:.035,side:THREE.DoubleSide});scene.add(bo)
    const paper=document.createElement('canvas');paper.width=128;paper.height=64;const ctx=paper.getContext('2d')!,gradient=ctx.createRadialGradient(64,32,0,64,32,60);gradient.addColorStop(0,'rgba(43,35,20,.35)');gradient.addColorStop(1,'rgba(43,35,20,0)');ctx.fillStyle=gradient;ctx.fillRect(0,0,128,64)
    const shadowTexture=new THREE.CanvasTexture(paper);textures.push(shadowTexture);shadow.geometry.dispose();(shadow.material as THREE.Material).dispose();shadow.geometry=geometry(new THREE.PlaneGeometry(1.8,.8));shadow.material=material({map:shadowTexture,transparent:true,depthWrite:false,polygonOffset:true,polygonOffsetFactor:-1});shadow.rotation.x=-Math.PI/2;scene.add(shadow)
  })
  const project=(p:THREE.Vector3)=>{const v=p.clone().project(camera);return{x:(v.x*.5+.5)*width,y:(.5-v.y*.5)*height,z:v.z}}
  function box(mesh:THREE.Mesh,w:number,h:number,opacity:number):ClimbProjection{
    const corners=[[-w/2,-h/2],[-w/2,h/2],[w/2,-h/2],[w/2,h/2]].map(([x,y])=>project(mesh.localToWorld(new THREE.Vector3(x,y,0))))
    const x=Math.min(...corners.map(p=>p.x)),y=Math.min(...corners.map(p=>p.y));return{x:Math.max(-width,x),y:Math.max(-height,y),width:Math.min(width*3,Math.max(...corners.map(p=>p.x))-x),height:Math.min(height*3,Math.max(...corners.map(p=>p.y))-y),opacity}
  }
  return{ready,
    resize(w,h){width=Math.max(1,w);height=Math.max(1,h);renderer.setSize(width,height,false);camera.aspect=width/height;camera.fov=width/height<1?64:54;camera.updateProjectionMatrix()},
    render(progress,direction,moving){
      const s=start+Math.max(0,progress)*ROUTE_SPAN,eye=routePoint(s,0,'eye'),look=routePoint(s+9,0,'eye'),boS=s+ROUTE_BO_LEAD,point=routePoint(boS,-.4,'foot')
      camera.position.set(eye.x,eye.y+2.75,eye.z);camera.lookAt(look.x,look.y+1.15,look.z);camera.updateMatrixWorld()
      // Keep one painted silhouette facing the eye around its fixed trunk,
      // instead of revealing the razor-thin edge of intersecting cards.
      const treePose=new THREE.Object3D()
      for(const batch of paintedTrees){
        batch.roots.forEach((root,i)=>{
          const angle=Math.atan2(camera.position.x-root.x,camera.position.z-root.z),shift=(.5-root.anchor)*root.h
          treePose.position.set(root.x+shift*Math.cos(angle),root.y+root.h*.405,root.z-shift*Math.sin(angle));treePose.rotation.set(0,angle,0);treePose.scale.set(root.h,root.h,1);treePose.updateMatrix();batch.mesh.setMatrixAt(i,treePose.matrix)
        })
        batch.mesh.instanceMatrix.needsUpdate=true
      }
      const cycles=boS/ROUTE_TREAD,phase=Math.abs(cycles-Math.round(cycles))<.000001?Math.round(cycles):cycles,frame=(Math.floor(phase*4+.000001)%8+8)%8,map=direction===1?away:toward
      map.offset.set((frame%4)*.25,frame<4?.5:0);(bo.material as THREE.MeshBasicMaterial).map=map;bo.position.set(point.x,point.y,point.z);bo.rotation.y=-routeHeading(boS)
      shadow.position.set(point.x,routeHeight(boS)+.02,point.z)
      const entrance=tower?routeTowerEntry(boS,towerS):{opacity:1,entered:false}
      ;(bo.material as THREE.MeshBasicMaterial).opacity=entrance.opacity
      ;(shadow.material as THREE.MeshBasicMaterial).opacity=entrance.opacity
      if(tower){const t=Math.max(0,Math.min(1,(towerS-s-ROUTE_SPAN*2)/(ROUTE_SPAN*2)));tower.setReveal(1-t*t*(3-2*t))}
      for(let i=0;i<gates.length;i++){
        const g=gates[i],state=routeGateVisibility(s,g.s)
        g.mesh.visible=state.available&&state.distance>-3&&state.distance<75;g.material.opacity=state.opacity;(g.label.material as THREE.MeshBasicMaterial).opacity=state.opacity*(1-state.mist)
        g.cloudMaterial.opacity=state.mist*.55
        g.clouds.forEach((cloud,j)=>{const side=j?1:-1,spread=(1-state.mist)*6,p=routePoint(g.s,side*(2+spread));cloud.visible=state.available&&state.distance>3&&state.distance<ROUTE_SPAN+1;cloud.position.set(p.x,p.y+1.6+j*.6+(1-state.mist),p.z+2)})
      }
      renderer.render(scene,camera)
      const gateIndex=Math.min(gates.length-1,Math.floor(progress)),g=gates[Math.max(0,gateIndex)],state=routeGateVisibility(s,g.s)
      const visible=state.distance>.75?state.opacity*(1-state.mist):0,gateBox=box(g.mesh,GATE_WIDTH,GATE_HEIGHT,visible),foot=project(bo.position),head=project(bo.position.clone().add(new THREE.Vector3(0,1.8,0))),bodyHeight=Math.abs(foot.y-head.y)
      return{action:tower&&progress>=names.length?'tower':state.distance<7?'gate':Math.abs(routeHeading(s+8)-routeHeading(s))>.12?'bend':'climb',progress,gateIndex,avatar:{x:foot.x,y:foot.y,frame,pose:!moving?'idle':direction===1?'walk-up':'walk-down',world:{...point,distance:boS},bounds:{x:foot.x-bodyHeight*.7,y:head.y,width:bodyHeight*1.4,height:bodyHeight,opacity:entrance.opacity}},camera:{x:camera.position.x,y:camera.position.y,z:camera.position.z,yaw:Math.atan2(look.x-eye.x,eye.z-look.z),pitch:camera.rotation.x,zoom:1},gate:gateBox,plaque:{...gateBox,opacity:0},landmarks:landmarks.map(l=>({id:l.id,...project(l.point),world:{x:l.point.x,y:l.point.y,z:l.point.z}})),world:{distance:s,gateDistance:state.distance,mist:state.mist,passedGates:Math.floor((s-start)/ROUTE_SPAN),roadStrips:1,triangles:renderer.info.render.triangles,towerDistance:tower?towerS-s:null,towerEntered:entrance.entered}}
    },
    dispose(){disposed=true;instances.forEach(mesh=>mesh.dispose());geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());textures.forEach(t=>t.dispose());renderer.dispose()},
  }
}
