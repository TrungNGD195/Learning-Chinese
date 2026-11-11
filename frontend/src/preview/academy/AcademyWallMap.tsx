import {useCallback,useEffect,useRef} from 'react'
import {Link} from 'react-router'
import {AcademyIcon} from '../../components/academy/AcademyIcon'
import {Companion} from '../../components/academy/Companion'
import {lessonState,previewUrl,type PreviewState} from './previewData'

const artwork='/academy/great-wall/academy-2d-v1/'
// Measured centers of the five actual landings in the 1024 × 1536 plate.
// Bottom to top; percentages preserve alignment at every viewport width.
const landings=[{x:47,y:80},{x:70,y:60},{x:50,y:43},{x:28,y:26},{x:50,y:13}]

export function AcademyWallMap({state,level,total}:{state:PreviewState;level:number;total:number}){
 const viewport=useRef<HTMLDivElement>(null),board=useRef<HTMLDivElement>(null)
 const segments=Math.ceil(total/5)
 const nodes=Array.from({length:total},(_,index)=>{
  const point=landings[index%5],segment=segments-1-Math.floor(index/5)
  return{number:index+1,x:point.x,y:(segment*100+point.y)/segments,state:lessonState(level,index+1,state)}
 })
 const currentY=nodes[level===1?2:0].y
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
 return <section className="ap-map-section ap-wall-map" aria-label={`Bản đồ Trường Thành 2D HSK ${level}`}>

  <div className="ap-map-legend"><button className="ap-map-locate" onClick={locate}><AcademyIcon name="path" size={16}/>Về vị trí của bạn</button><span><i data-state="completed"/>Đã hoàn thành</span><span><i data-state="current"/>Đang học</span><span><i/>Chưa học</span></div>
  <div ref={viewport} className="ap-map-scroll" tabIndex={0} aria-label="Bản đồ leo Trường Thành từ dưới lên">
    <div className="ap-wall-summit"><img src={artwork+'watchtower.png'} alt="Tháp canh ở đỉnh chặng Trường Thành"/><span>Đỉnh chặng HSK {level}</span>{level<3?<Link className="ap-inline-button" to={previewUrl({view:'curriculum',level:level+1,mode:'map'})}>Tiếp chặng HSK {level+1}<AcademyIcon name="arrow" size={15}/></Link>:<span>Cùng Bo vươn xa hơn</span>}</div>
   <div ref={board} className="ap-map-board" style={{aspectRatio:`1024 / ${1536*segments}`}}>
    {Array.from({length:segments},(_,index)=><img className="ap-wall-plate" key={index} src={artwork+'ascent-map.png'} alt="" draggable={false} style={{top:`${index*100/segments}%`,height:`${100/segments}%`}}/>)}
    {Array.from({length:segments-1},(_,index)=><div className="ap-wall-mist" key={index} style={{top:`${(index+1)*100/segments}%`}} aria-hidden="true"><img src="/academy/great-wall/journey-cloud-v1.webp" alt=""/><img src="/academy/great-wall/journey-cloud-v1.webp" alt=""/></div>)}
    {nodes.map(node=>{
     const content=<><img src="/academy/great-wall/painted-v2/gate.webp" alt="" draggable={false}/><strong>Bài {node.number}</strong><span>{node.state==='current'?'Bạn đang ở đây':node.state==='completed'?'Đã hoàn thành':'Chưa học'}</span></>
     return <div key={node.number} className="ap-map-node" data-state={node.state} style={{left:`${node.x}%`,top:`${node.y}%`}}>
      {level===1&&node.number===3?<><Companion pose="guide" decorative/><Link to={previewUrl({view:'lesson',part:'vocabulary',word:2})} aria-label="Mở bài mẫu 3 từ bản đồ">{content}</Link></>:<div>{content}</div>}
     </div>
    })}

   </div>
  </div>
  <p className="ap-map-mobile-hint">Cuộn lên để leo cao hơn. Bấm cổng Bài 3 để thử học; các cổng khác minh họa hành trình.</p>
 </section>
}
