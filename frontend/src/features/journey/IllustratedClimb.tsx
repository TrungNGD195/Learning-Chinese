import {useEffect,useRef,useState,type ReactNode} from 'react'
import {advanceAscentCamera} from './paintedAscent'
import {ROUTE_SPAN} from './firstPersonRoute'
import type {ClimbFrame,IllustratedScene} from './createIllustratedClimbScene'
import '../../styles/illustrated-climb.css'

type Props={progress:number;total:number;name:string;names:string[];levelNumber:number;nextLevelNumber?:number;onTowerEntered:()=>void;onViewProgress:(progress:number)=>void;gateControl:(className:string)=>ReactNode;departing:boolean;resetSequence:number}
export function IllustratedClimb({progress,name,names,levelNumber,nextLevelNumber,onTowerEntered,onViewProgress,gateControl,departing,resetSequence}:Props){
  const canvas=useRef<HTMLCanvasElement>(null),root=useRef<HTMLDivElement>(null),gate=useRef<HTMLDivElement>(null),plaque=useRef<HTMLDivElement>(null)
  const target=useRef(progress),schedule=useRef(()=>{}),sceneRef=useRef<IllustratedScene|null>(null)
  const relocated=useRef(false),onView=useRef(onViewProgress),viewIndex=useRef(Math.floor(progress))
  const onEnter=useRef(onTowerEntered),entered=useRef(false)
  const namesKey=JSON.stringify(names)
  useEffect(()=>{onView.current=onViewProgress},[onViewProgress])
  useEffect(()=>{onEnter.current=onTowerEntered},[onTowerEntered])
  const reset=useRef(resetSequence)
  const [unavailable,setUnavailable]=useState(false)
  useEffect(()=>{if(reset.current!==resetSequence){reset.current=resetSequence;relocated.current=true}target.current=progress;schedule.current()},[progress,resetSequence])
  useEffect(()=>{
    const surface=canvas.current,view=root.current;if(!surface||!view)return
    let disposed=false,ready=false,visible=true,raf=0,last=0,direction:1|-1=1
    const position={position:target.current,velocity:0}
    const reduced=window.matchMedia('(prefers-reduced-motion: reduce)')
    const place=(element:HTMLElement|null,box:ClimbFrame['gate'])=>{if(!element)return;element.style.transform=`translate3d(${box.x}px,${box.y}px,0)`;element.style.width=`${box.width}px`;element.style.height=`${box.height}px`;element.style.opacity=String(box.opacity);element.style.pointerEvents=box.opacity>.8?'auto':'none'}
    const draw=(now:number)=>{
      raf=0;if(disposed||!ready||document.hidden||!visible)return
      const before=position.position,elapsed=last?Math.min(50,now-last):16;last=now
      if(reduced.matches||relocated.current){position.position=target.current;position.velocity=0;relocated.current=false}
      else advanceAscentCamera(position,target.current,elapsed,4.86/ROUTE_SPAN)
      const moving=Math.abs(position.position-target.current)>.0002||Math.abs(position.velocity)>.001
      if(Math.abs(position.position-before)>.0000001)direction=position.position>before?1:-1
      const frame=sceneRef.current!.render(position.position,direction,moving)
      if(frame.world.towerEntered&&!entered.current){entered.current=true;onEnter.current()}
      else if(!frame.world.towerEntered)entered.current=false
      if(viewIndex.current!==Math.floor(position.position)||relocated.current){viewIndex.current=Math.floor(position.position);onView.current(position.position)}
      place(gate.current,frame.gate);place(plaque.current,frame.plaque)
      view.dataset.action=frame.action;view.dataset.moving=String(moving);view.dataset.frame=String(frame.avatar.frame);view.dataset.motion=JSON.stringify(frame)
      if(moving)raf=requestAnimationFrame(draw);else last=0
    }
    const request=()=>{if(!raf&&!disposed)raf=requestAnimationFrame(draw)};schedule.current=request
    const resize=()=>{if(!ready)return;sceneRef.current!.resize(view.clientWidth,view.clientHeight);request()}
    const pause=()=>{if(document.hidden){cancelAnimationFrame(raf);raf=0;last=0}else request()}
    const observer=new ResizeObserver(resize);observer.observe(view)
    const intersection=new IntersectionObserver(([entry])=>{visible=entry.isIntersecting;if(visible)request();else{cancelAnimationFrame(raf);raf=0;last=0}});intersection.observe(view)
    const fallback=()=>{if(!disposed){ready=false;cancelAnimationFrame(raf);raf=0;view.dataset.ready='fallback';setUnavailable(true)}}
    surface.addEventListener('webglcontextlost',fallback);document.addEventListener('visibilitychange',pause);reduced.addEventListener('change',request)
    void import('./createIllustratedClimbScene').then(async({createIllustratedClimbScene})=>{
      if(disposed)return;const scene=createIllustratedClimbScene(surface,{level:levelNumber,names:JSON.parse(namesKey) as string[],nextLevel:nextLevelNumber});sceneRef.current=scene;await scene.ready
      if(disposed)return;ready=true;view.dataset.ready='true';resize()
    }).catch(fallback)
    return()=>{disposed=true;cancelAnimationFrame(raf);schedule.current=()=>{};observer.disconnect();intersection.disconnect();sceneRef.current?.dispose();sceneRef.current=null;surface.removeEventListener('webglcontextlost',fallback);document.removeEventListener('visibilitychange',pause);reduced.removeEventListener('change',request)}
  },[levelNumber,namesKey,nextLevelNumber])
  return <div ref={root} className="illustrated-climb" data-departing={departing||undefined}>
    {unavailable?<div className="illustrated-fallback"><p>Chế độ minh họa tĩnh. Bạn vẫn có thể mở bài bằng tên bài bên dưới hoặc xem toàn lộ trình.</p></div>:<canvas ref={canvas} aria-hidden="true"/>}
    <div ref={gate} className="illustrated-gate-control">{gateControl('illustrated-gate-hit')}</div>
    <div ref={plaque} className="illustrated-gate-plaque" aria-hidden="true">{name}</div>
  </div>
}
