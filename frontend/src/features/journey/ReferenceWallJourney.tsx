import {useCallback,useEffect,useRef,useState,type MouseEvent} from 'react'
import {Link,useLocation,useNavigate} from 'react-router'
import {AcademyIcon} from '../../components/academy/AcademyIcon'
import {IllustratedClimb} from './IllustratedClimb'
import {ROUTE_STEPS_PER_GATE as STEPS,ROUTE_TOWER_STEPS} from './firstPersonRoute'
import {useJourneyCloud} from './journeyCloudContext'
import type {JourneyStop} from './journeyData'
import '../../styles/reference-journey.css'

type Props={stops:JourneyStop[];currentId?:string;focusId?:string;finished:boolean;levelNumber:number;locateSignal?:number;overview:boolean;onOverviewChange:(value:boolean)=>void;nextLevel?:{number:number;destination:string}}
type Scene='hero'|'climb'|'bend'|'gate'|'tower'
const reduced=()=>window.matchMedia?.('(prefers-reduced-motion: reduce)').matches??false
const sceneAt=(step:number):Scene=>{const part=(((step%STEPS)+STEPS)%STEPS)/STEPS;return part===0?'hero':part<=1/3?'climb':part<=2/3?'bend':'gate'}

export function ReferenceWallJourney({stops,currentId,focusId,finished,levelNumber,locateSignal=0,overview,onOverviewChange,nextLevel}:Props){
  const focus=Math.max(0,stops.findIndex(stop=>stop.id===(focusId??currentId)))
  const gateEnd=Math.max(0,stops.length*STEPS),maximum=gateEnd+(nextLevel?ROUTE_TOWER_STEPS:0),key=`bo-reference-journey-v1-hsk-${levelNumber}`
  const [step,setStep]=useState(()=>{
    try{const raw=sessionStorage.getItem(`bo-reference-arrival-${levelNumber}`);if(raw==='first')return 0;const saved=JSON.parse(sessionStorage.getItem(key)??'null');if(saved?.ids===stops.map(s=>s.id).join('|')&&Number.isInteger(saved.step))return Math.max(0,Math.min(gateEnd,Math.round(saved.step*STEPS/(saved.stepsPerGate??10))))}catch{/* Optional visual resume only. */}
    return focus*STEPS
  })
  const [departing,setDeparting]=useState(false),[notice,setNotice]=useState('')
  const [resetSequence,setResetSequence]=useState(0)
  const [viewProgress,setViewProgress]=useState(step/STEPS)
  const latest=useRef(step),view=useRef<HTMLDivElement>(null),lastLocate=useRef(locateSignal)
  const navigate=useNavigate(),location=useLocation(),cloud=useJourneyCloud()
  const atEnd=viewProgress>=stops.length,index=Math.min(stops.length-1,Math.floor(viewProgress)),stop=stops[Math.max(0,index)]
  const scene:Scene=atEnd?'tower':sceneAt(step)
  const name=atEnd?(nextLevel?`Tháp · HSK ${nextLevel.number}`:`HSK ${levelNumber}`):stop?.shortName??'Bài học'
  const go=useCallback((value:number,teleport=false)=>{if(departing)return;const next=Math.max(0,Math.min(maximum,Math.round(value)));const relocate=()=>{try{sessionStorage.removeItem(`bo-reference-arrival-${levelNumber}`)}catch{/* Optional visual marker. */}latest.current=next;setStep(next);setNotice('');if(teleport){setViewProgress(next/STEPS);setResetSequence(v=>v+1)}};if(teleport&&cloud&&!reduced()){cloud.travel({destination:location.pathname,returning:true,relocate})}else relocate()},[departing,maximum,cloud,location.pathname,levelNumber])
  const enterTower=useCallback(()=>{
    if(!nextLevel||departing)return
    try{sessionStorage.setItem(`bo-reference-arrival-${nextLevel.number}`,'first')}catch{/* Visual arrival only. */}
    const cancel=()=>{
      setDeparting(false)
      try{sessionStorage.removeItem(`bo-reference-arrival-${nextLevel.number}`)}catch{/* Optional storage. */}
      const safe=maximum-1;latest.current=safe;setStep(safe);setViewProgress(safe/STEPS);setResetSequence(value=>value+1)
    }
    if(cloud&&!reduced()){
      const accepted=cloud.travel({destination:nextLevel.destination,returning:true,coverDelay:180,depart:()=>setDeparting(true),cancelled:cancel})
      if(!accepted)cancel()
    }else{setDeparting(true);void navigate(nextLevel.destination)}
  },[nextLevel,departing,maximum,cloud,navigate])
  useEffect(()=>{const reset=()=>{setDeparting(false);cloud?.cancel()};window.addEventListener('popstate',reset);return()=>window.removeEventListener('popstate',reset)},[cloud])
  useEffect(()=>{latest.current=step;try{sessionStorage.setItem(key,JSON.stringify({step,stepsPerGate:STEPS,ids:stops.map(s=>s.id).join('|')}))}catch{/* Optional tab-local view only. */}},[step,key,stops])
  useEffect(()=>{
    if(overview)return
    const target=view.current;if(!target)return
    const keydown=(event:KeyboardEvent)=>{if(target.closest('[inert]')||!['ArrowUp','ArrowDown'].includes(event.key)||event.altKey||event.ctrlKey||event.metaKey||event.shiftKey)return;if(event.target instanceof Element&&event.target.closest('input,textarea,select,[contenteditable=true]'))return;event.preventDefault();if(!event.repeat)go(latest.current+(event.key==='ArrowUp'?1:-1))}
    window.addEventListener('keydown',keydown)
    return()=>window.removeEventListener('keydown',keydown)
  },[overview,go])
  useEffect(()=>{if(!locateSignal||locateSignal===lastLocate.current)return;lastLocate.current=locateSignal;cloud?.cancel();setDeparting(false);onOverviewChange(false);const relocate=()=>{try{sessionStorage.removeItem(`bo-reference-arrival-${levelNumber}`)}catch{/* Explicit location replaces arrival. */}latest.current=focus*STEPS;setStep(focus*STEPS);setViewProgress(focus);setNotice('');setResetSequence(v=>v+1)};if(cloud&&!reduced())cloud.travel({destination:location.pathname,relocate,returning:true});else relocate()},[locateSignal,focus,cloud,location.pathname,onOverviewChange,levelNumber])
  function explain(item:JourneyStop){setNotice(item.planned?`${item.shortName} đang được chuẩn bị.`:`${item.shortName} chưa mở. Hoàn thành phần học và đạt từ 80% luyện tập ở bài trước để tiếp tục.`)}
  function openLesson(event:MouseEvent<HTMLAnchorElement>,item:JourneyStop){
    if(event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey||!item.destination)return
    if(reduced())return
    event.preventDefault();if(departing)return
    if(cloud){if(cloud.travel({destination:item.destination,short:true,depart:()=>setDeparting(true),cancelled:()=>setDeparting(false)}))setDeparting(true)}else void navigate(item.destination)
  }
  function nextChapter(event:MouseEvent<HTMLAnchorElement>){
    if(!nextLevel||event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return
    event.preventDefault();enterTower()
  }
  const enterLabel=atEnd?`Tiếp đến HSK ${nextLevel?.number??levelNumber}`:stop?`${stop.state==='COMPLETED'?'Ôn':'Học'} ${stop.name}`:'Chọn bài học'
  function gateControl(className:string){
    if(atEnd&&nextLevel)return <Link className={className} to={nextLevel.destination} aria-label={enterLabel} onClick={nextChapter}><span className="reference-accessible">{enterLabel}</span></Link>
    if(stop?.destination)return <Link className={className} to={stop.destination} aria-label={enterLabel} onClick={event=>openLesson(event,stop)}><span className="reference-accessible">{enterLabel}</span></Link>
    return <button type="button" className={className} aria-label={name} aria-disabled="true" onClick={()=>{if(stop)explain(stop)}}><span className="reference-accessible">{name}</span></button>
  }
  return <div className="reference-journey" data-scene={scene} data-level={levelNumber}>
    {overview?<>
      <ol className="reference-overview" aria-label="Các bài trong cấp độ HSK">{stops.map((item,i)=><li key={item.id} data-state={item.state.toLowerCase()}>
        {item.destination?<Link to={item.destination} onClick={event=>openLesson(event,item)}><strong>{item.shortName}</strong><span>{item.name.replace(/^Bài học \d+:\s*/,'')}</span><small>{item.state==='COMPLETED'?'Đã hoàn thành':'Có thể học'}</small></Link>:<button type="button" aria-disabled="true" onClick={()=>explain(item)}><strong>{item.shortName}</strong><span>{item.planned?'Sắp có nội dung':item.name}</span><small>{item.planned?'Đang chuẩn bị':'Chưa mở'}</small></button>}
        <button type="button" className="reference-locate-card" aria-label={`Định vị ${item.shortName}`} onClick={()=>{onOverviewChange(false);go(i*STEPS,true)}}><AcademyIcon name="path" size={18}/></button>
      </li>)}</ol>
      <button className="reference-marker-button" type="button" onClick={()=>{onOverviewChange(false);go(gateEnd,true)}}>Đến mốc HSK {levelNumber}<AcademyIcon name="arrow" size={18}/></button>
    </>:<>
      <div ref={view} className="reference-stage reference-stage--motion" data-progress={step/STEPS} data-scene={scene} data-departing={departing||undefined} role="region" aria-label={`Trường Thành HSK ${levelNumber}, ${name}`}>
        <IllustratedClimb progress={step/STEPS} total={stops.length} name={name} names={stops.map(item=>item.shortName)} levelNumber={levelNumber} nextLevelNumber={nextLevel?.number} onTowerEntered={enterTower} onViewProgress={setViewProgress} gateControl={gateControl} departing={departing} resetSequence={resetSequence}/>
        <nav className="reference-step-nav reference-step-nav--motion" aria-label="Di chuyển từng bậc">
          <span className="reference-keyboard-hint" aria-label="Dùng phím mũi tên lên và xuống để di chuyển"><kbd>↑</kbd><kbd>↓</kbd></span>
          <div className="reference-current-name"><strong>{name}</strong>{gateControl('reference-caption-hit')}</div>
        </nav>
        {notice&&<div className="reference-notice" role="status"><p>{notice}</p><button type="button" onClick={()=>setNotice('')} aria-label="Đóng hướng dẫn">×</button></div>}
      </div>
    </>}
    {overview&&notice&&<p className="reference-overview-notice" role="status">{notice}</p>}
    <span className="reference-accessible">{finished?'Đã hoàn thành chặng học. Có thể chọn các bài để ôn tập.':`${stops.length} cổng trong chặng học.`}</span>
  </div>
}
