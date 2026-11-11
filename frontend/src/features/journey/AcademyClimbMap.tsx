import {useCallback,useEffect,useRef} from 'react'
import {Link} from 'react-router'
import {AcademyIcon} from '../../components/academy/AcademyIcon'
import {Companion} from '../../components/academy/Companion'
import {LessonEntryLink} from './LessonEntryLink'
import type {JourneyStop} from './journeyData'

const artwork='/academy/great-wall/academy-2d-v1/'
// Measured centers of the five actual landings in the 1024 × 1536 plate.
// Bottom to top; percentages preserve alignment at every viewport width.
const landings=[{x:47,y:80},{x:70,y:60},{x:50,y:43},{x:28,y:26},{x:50,y:13}]

type Props={stops:JourneyStop[];currentId?:string;level:number;nextLevel?:{number:number;destination:string};onExplain:(stop:JourneyStop)=>void}
export function AcademyClimbMap({stops,currentId,level,nextLevel,onExplain}:Props){
 const total=stops.length
 const viewport=useRef<HTMLDivElement>(null),board=useRef<HTMLDivElement>(null)
 const segments=Math.max(1,Math.ceil(total/5))
 const nodes=Array.from({length:total},(_,index)=>{
  const point=landings[index%5],segment=segments-1-Math.floor(index/5)
  return{...stops[index],x:point.x,y:(segment*100+point.y)/segments}
 })
 const focus=Math.max(0,nodes.findIndex(stop=>stop.id===currentId))
 const currentY=nodes[focus]?.y??80
 const locate=useCallback(()=>{
  if(!viewport.current||!board.current)return
  viewport.current.scrollTo({top:board.current.offsetTop+board.current.clientHeight*currentY/100-viewport.current.clientHeight*.65,behavior:'instant'})
 },[currentY])
 useEffect(()=>{
  locate()
  if(!board.current)return
  const observer=new ResizeObserver(locate)
  observer.observe(board.current)
  return()=>observer.disconnect()
 },[locate])
 return <section className="lc-map-section lc-wall-map" aria-label={`Bản đồ Trường Thành 2D HSK ${level}`}>

  <div className="lc-map-legend"><button className="lc-map-locate" onClick={locate}><AcademyIcon name="path" size={16}/>Về vị trí của bạn</button><span><i data-state="completed"/>Đã hoàn thành</span><span><i data-state="current"/>Đang học</span><span><i/>Chưa học</span></div>
  <div ref={viewport} className="lc-map-scroll" tabIndex={0} aria-label="Bản đồ leo Trường Thành từ dưới lên">
    <div className="lc-wall-summit"><img src={artwork+'watchtower.png'} alt="Tháp canh ở đỉnh chặng Trường Thành"/><span>Đỉnh chặng HSK {level}</span>{nextLevel?<Link className="lc-inline-button" to={nextLevel.destination}>Tiếp chặng HSK {nextLevel.number}<AcademyIcon name="arrow" size={15}/></Link>:<span>Cùng Bo vươn xa hơn</span>}</div>
   <div ref={board} className="lc-map-board" style={{aspectRatio:`1024 / ${1536*segments}`}}>
    {Array.from({length:segments},(_,index)=><img className="lc-wall-plate" key={index} src={artwork+'ascent-map.png'} alt="" draggable={false} style={{top:`${index*100/segments}%`,height:`${100/segments}%`}}/>)}
    {Array.from({length:segments-1},(_,index)=><div className="lc-wall-mist" key={index} style={{top:`${(index+1)*100/segments}%`}} aria-hidden="true"><img src="/academy/great-wall/journey-cloud-v1.webp" alt=""/><img src="/academy/great-wall/journey-cloud-v1.webp" alt=""/></div>)}
    {nodes.map(node=>{
     const isCurrent=node.id===currentId
     const content=<><img src="/academy/great-wall/painted-v2/gate.webp" alt="" draggable={false}/><strong>{node.shortName}</strong><span>{isCurrent?'Bạn đang ở đây':node.planned||node.unpublished?'Sắp có nội dung':node.state==='COMPLETED'?'Đã hoàn thành':node.destination?'Có thể học':'Chưa mở'}</span></>
     return <div key={node.id} className="lc-map-node" data-state={node.state==='COMPLETED'?'completed':isCurrent?'current':'planned'} style={{left:`${node.x}%`,top:`${node.y}%`}}>
      {isCurrent&&<Companion pose="guide" decorative/>}
      {node.destination?<LessonEntryLink to={node.destination} aria-label={`${node.state==='COMPLETED'?'Ôn':'Học'} ${node.name}`}>{content}</LessonEntryLink>:<button type="button" aria-label={`${node.shortName}: ${node.planned||node.unpublished?'Đang chuẩn bị':'Chưa mở'}`} data-locked="true" onClick={()=>onExplain(node)}>{content}</button>}
     </div>
    })}

   </div>
  </div>
  <p className="lc-map-mobile-hint">Cuộn lên để leo cao hơn. Chọn cổng để vào bài học.</p>
 </section>
}
