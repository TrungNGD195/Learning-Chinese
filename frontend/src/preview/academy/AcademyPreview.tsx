import {useCallback,useEffect,useRef,useState} from 'react'
import {Link,useNavigate,useSearchParams} from 'react-router'
import {AcademyIcon} from '../../components/academy/AcademyIcon'
import {Companion,VocabularyIllustration} from '../../components/academy/Companion'
import {PreviewReview,PreviewStudy} from './PreviewStudy'
import {AcademyWallMap as PreviewMap} from './AcademyWallMap'
import {initialPreview,lessonState,lessonTitles,levels,previewStorageKey,previewUrl,readPreview,words,type PreviewPatch,type PreviewState} from './previewData'

const navigation=[['home','Học tập','home'],['curriculum','Giáo trình','book'],['review','Ôn tập','history'],['profile','Hồ sơ','profile']] as const
function Brand(){return <Link className="ap-brand" to={previewUrl({view:'home'})}><span className="ap-brand-mark" lang="zh-Hans">中</span><span>Chinese Learning<small>Học viện cùng Bo</small></span></Link>}
export function AcademyPreview(){
 const [params]=useSearchParams(),navigate=useNavigate(),main=useRef<HTMLElement>(null)
 const [state,setState]=useState(readPreview),[storageAvailable,setStorageAvailable]=useState(true),[resetDone,setResetDone]=useState(false)
 const view=['home','curriculum','lesson','review','profile'].includes(params.get('view')??'')?params.get('view')!:'home'
 const level=[1,2,3].includes(Number(params.get('level')))?Number(params.get('level')):1
 const part=['vocabulary','grammar','reading','practice'].includes(params.get('part')??'')?params.get('part')!:'vocabulary'
 const rawWord=Number(params.get('word')??0),wordIndex=Number.isInteger(rawWord)?Math.max(0,Math.min(words.length-1,rawWord)):0
 const active=view==='lesson'?'curriculum':view
 const update:PreviewPatch=useCallback(value=>setState(current=>({...current,...(typeof value==='function'?value(current):value)})),[])
 const go=useCallback((next:string,extra:Record<string,string|number>={})=>{void navigate(previewUrl({view:next,...extra}))},[navigate])
 useEffect(()=>{try{localStorage.setItem(previewStorageKey,JSON.stringify(state))}catch{const timer=setTimeout(()=>setStorageAvailable(false),0);return()=>clearTimeout(timer)}},[state])
 useEffect(()=>{document.title=({home:'Góc học tập',curriculum:'Giáo trình',lesson:'Bài học mẫu',review:'Ôn tập',profile:'Hồ sơ mẫu'}[view]??'Học viện')+' · Cùng Bo';main.current?.focus({preventScroll:true});window.scrollTo(0,0)},[view])
 useEffect(()=>{if(!resetDone)return;const timer=setTimeout(()=>setResetDone(false),2000);return()=>clearTimeout(timer)},[resetDone])
 const reset=()=>{setState({...initialPreview});setResetDone(true);go('home')}
 return <div className="ap-preview" data-reduced={state.reduced}>
  <a className="ap-skip-link" href="#preview-main">Chuyển đến nội dung</a>
  <div className="ap-preview-banner"><div><strong>Bản trải nghiệm</strong><span>Dữ liệu minh họa · Tiến độ thử độc lập với tài khoản thật</span></div><button onClick={reset}>{resetDone?'Đã đặt lại':'Đặt lại bản thử'}</button><a href="/dashboard">Web hiện tại<AcademyIcon name="arrow" size={14}/></a></div>
  <aside className="ap-sidebar"><Brand/><nav aria-label="Điều hướng học viện">{navigation.map(([key,label,icon])=><Link key={key} to={previewUrl({view:key})} aria-current={active===key?'page':undefined}><AcademyIcon name={icon}/><span>{label}</span>{key==='review'&&state.reviewed.length<6&&<small>{6-state.reviewed.length}</small>}</Link>)}</nav><div className="ap-sidebar-message"><span lang="zh-Hans">学而时习之</span><p>Học, rồi ôn lại.<br/>Từng chút thành quen.</p></div><div className="ap-sidebar-user"><span>{state.name.charAt(0).toUpperCase()}</span><div>{state.name}<small>Người học mẫu · HSK 1</small></div></div></aside>
  <header className="ap-mobile-header"><Brand/></header>
  <main ref={main} id="preview-main" className="ap-main" tabIndex={-1}>
   {view==='home'&&<PreviewHome state={state}/>}
   {view==='curriculum'&&<PreviewCurriculum state={state} level={level} mode={params.get('mode')==='map'?'map':'list'} go={go}/>}
   {view==='lesson'&&<PreviewStudy state={state} update={update} part={part} wordIndex={wordIndex} go={go}/>}
   {view==='review'&&<PreviewReview state={state} update={update}/>}
   {view==='profile'&&<PreviewProfile state={state} update={update} storageAvailable={storageAvailable}/>}
   <footer className="ap-page-footer"><span>Cùng Bo học tiếng Trung</span><span>Học rõ ràng. Tiến bộ từng ngày.</span></footer>
  </main>
  <nav className="ap-bottom-nav" aria-label="Điều hướng trên điện thoại">{navigation.map(([key,label,icon])=><Link key={key} to={previewUrl({view:key})} aria-current={active===key?'page':undefined}><AcademyIcon name={icon}/><span>{label}</span></Link>)}</nav>
 </div>
}

function PreviewHome({state}:{state:PreviewState}){
 const nextWord=words.findIndex((_,i)=>!state.seen.includes(i)),part=nextWord>=0?'vocabulary':!state.grammarDone?'grammar':!state.readingDone?'reading':'practice'
 const resume=previewUrl({view:'lesson',part:state.completed?'vocabulary':part,word:state.completed?0:Math.max(0,nextWord)})
 const complete=2+Number(state.completed),reviewDone=state.reviewed.length===words.length
 return <>
  <header className="ap-page-heading"><div><h1>Góc học tập</h1><p>Chào {state.name}, hôm nay mình học thêm một chút nhé.</p></div><Link className="ap-header-link" to={previewUrl({view:'profile'})}><AcademyIcon name="leaf" size={17}/><span>Mục tiêu {state.goal} phút / ngày</span></Link></header>
  <div className="ap-home-top"><section className="ap-resume"><div className="ap-resume-copy"><div className="ap-resume-location"><span>HSK 1</span><span>Bài 3 / 15</span></div><h2>Bạn là ai?</h2><p className="ap-resume-chinese" lang="zh-Hans">你是谁？</p><p>{state.completed?'Bạn đã hoàn thành bài mẫu. Cùng đọc lại và dùng những từ đã học.':'Giới thiệu bản thân, hỏi về người khác và bắt đầu một cuộc trò chuyện.'}</p><Link className="ap-button" to={resume}>{state.completed?'Ôn lại bài này':'Tiếp tục học'}<AcademyIcon name="arrow" size={18}/></Link><div className="ap-resume-progress"><progress max={9} value={state.seen.length+Number(state.grammarDone)+Number(state.readingDone)+Number(state.completed)}/><span>{state.completed?'Đã hoàn thành bài mẫu':`${state.seen.length}/6 từ vựng mẫu đã xem`}</span></div></div><div className="ap-resume-art"><Companion pose={state.completed?'celebrate':'guide'} decorative/><p>Bo học cùng bạn.</p></div></section>
   <section className="ap-home-review"><div className="ap-section-line"><h2>{reviewDone?'Bạn đã ôn xong':'Nhớ lại một chút'}</h2><AcademyIcon name="history"/></div><p>{reviewDone?'Một lần nhắc lại, thêm một lần quen. Bạn có thể ôn lại bất cứ lúc nào.':'Ôn 6 từ đã gặp, rồi thử dùng chúng trong một câu của riêng bạn.'}</p><div className="ap-review-word-preview" aria-hidden="true"><span lang="zh-Hans">老师</span><span lang="zh-Hans">朋友</span><span lang="zh-Hans">的</span></div><Link className="ap-button ap-button-secondary" to={previewUrl({view:'review'})}>{reviewDone?'Ôn lại bộ từ':'Bắt đầu ôn nhanh'}<AcademyIcon name="arrow" size={17}/></Link><small>{reviewDone?'6/6 từ đã ôn trong bản thử':'Gợi nhớ trước, xem đáp án sau.'}</small></section>
  </div>
  <section className="ap-today"><div><AcademyIcon name="exercise"/><h2>Một bước nhỏ hôm nay</h2></div><Link to={resume}><span className="ap-task-dot" data-done={state.completed}/><span>{state.completed?'Đã hoàn thành bài học mẫu':'Tiếp tục bài đang học'}</span><AcademyIcon name="arrow" size={16}/></Link><Link to={previewUrl({view:'review'})}><span className="ap-task-dot" data-done={reviewDone}/><span>{reviewDone?'Đã ôn 6 từ quen thuộc':'Ôn lại 6 từ quen thuộc'}</span><AcademyIcon name="arrow" size={16}/></Link></section>
  <section className="ap-home-courses"><div className="ap-section-heading"><div><h2>Giáo trình của bạn</h2><p>Học theo từng bài, tiến bộ theo cách của mình.</p></div><Link className="ap-inline-button" to={previewUrl({view:'curriculum',level:1})}>Xem giáo trình<AcademyIcon name="arrow" size={16}/></Link></div><div className="ap-course-grid">{levels.map(item=><Link className="ap-course" key={item.number} to={previewUrl({view:'curriculum',level:item.number})} data-active={item.number===1}><div className="ap-course-heading"><span>HSK {item.number}</span><span lang="zh-Hans">{item.hanzi}</span></div><h3>{item.title}</h3><p>{item.description}</p><progress max={item.total} value={item.number===1?complete:0}/><div><span>{item.number===1?complete:0}/{item.total} bài hoàn thành</span><AcademyIcon name="arrow" size={18}/></div></Link>)}</div></section>
  <section className="ap-daily-sentence"><span className="ap-sentence-icon" lang="zh-Hans">问</span><div><h2>Một câu có thể dùng hôm nay</h2><p lang="zh-Hans">请问，你是老师吗？</p><p>Xin hỏi, bạn là giáo viên phải không?</p></div><Link className="ap-inline-button" to={previewUrl({view:'lesson',part:'reading'})}>Đọc trong hội thoại<AcademyIcon name="arrow" size={16}/></Link></section>
 </>
}

function PreviewCurriculum({state,level,mode,go}:{state:PreviewState;level:number;mode:'list'|'map';go:(view:string,extra?:Record<string,string|number>)=>void}){
 const [search,setSearch]=useState(''),[filter,setFilter]=useState('all')
 const current=levels.find(item=>item.number===level)!,complete=level===1?2+Number(state.completed):0
 const rows=Array.from({length:current.total},(_,i)=>({number:i+1,title:level===1?lessonTitles[i]:`Chủ đề ${i+1}`,state:lessonState(level,i+1,state)}))
 const normalize=(value:string)=>value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d').toLowerCase()
 const visible=rows.filter(row=>(filter==='all'||row.state===filter)&&normalize(`${row.number} ${row.title}`).includes(normalize(search)))
 return <>
  {mode==='list'&&<>  <header className="ap-page-heading"><div><h1>Giáo trình</h1><p>Từng bài nhỏ, một nền tảng vững vàng.</p></div><Link className="ap-button ap-button-secondary" to={previewUrl({view:'lesson',part:'vocabulary',word:2})}>Vào bài mẫu<AcademyIcon name="arrow" size={17}/></Link></header></>}
  <div className="ap-curriculum-controls"><div className="ap-level-tabs" aria-label="Chọn cấp độ HSK">{levels.map(item=><button key={item.number} aria-pressed={level===item.number} onClick={()=>{setSearch('');setFilter('all');go('curriculum',{level:item.number,mode})}}>HSK {item.number}<span>{item.total} bài</span></button>)}</div><div className="ap-view-switch" aria-label="Cách xem giáo trình"><button aria-pressed={mode==='list'} onClick={()=>go('curriculum',{level,mode:'list'})}><AcademyIcon name="book" size={17}/>Danh sách</button><button aria-pressed={mode==='map'} onClick={()=>go('curriculum',{level,mode:'map'})}><AcademyIcon name="path" size={17}/>Bản đồ 2D</button></div></div>
  {mode==='list'&&<>  <section className="ap-course-summary"><div><h2>HSK {level} <span>· {current.title}</span></h2><p>{complete}/{current.total} bài đã hoàn thành</p></div><progress aria-label={`Tiến độ HSK ${level}`} max={current.total} value={complete}/></section>
  <p className="ap-demo-content-note">Bản thử có thể học trọn Bài 3 của HSK 1. Các bài còn lại minh họa cấu trúc giáo trình.</p>
</>}
  {mode==='list'?<><div className="ap-list-tools"><label><AcademyIcon name="book" size={17}/><span className="ap-sr-only">Tìm bài học</span><input type="search" placeholder="Tìm tên hoặc số bài…" value={search} onChange={e=>setSearch(e.target.value)}/></label><select aria-label="Lọc trạng thái bài học" value={filter} onChange={e=>setFilter(e.target.value)}><option value="all">Tất cả bài học</option><option value="current">Đang học</option><option value="completed">Đã hoàn thành</option><option value="planned">Chưa học</option></select></div><ol className="ap-lesson-list ap-lesson-card-grid">{visible.map(row=>{
   const coverWords=['你好','叫','老师','家','星期','你好','工作','鸡蛋','山','喜欢','饺子','学生','喝','书','山']
   const art=coverWords[row.number-1],isSample=level===1&&row.number===3
   const content=<><div className="ap-lesson-cover" data-tone={row.number%4} aria-hidden="true"><VocabularyIllustration hanzi={art}/><span>Bài {row.number}</span></div><div className="ap-lesson-card-body"><h2>{row.title}</h2><p>{isSample?'6 từ mẫu · Ngữ pháp · Bài khóa':'Bài minh họa trong giáo trình'}</p><div className="ap-lesson-card-footer"><span>{row.state==='completed'?'Đã hoàn thành':row.state==='current'?'Đang học':'Chưa học'}</span>{isSample?<AcademyIcon name="arrow" size={19}/>:<AcademyIcon name={row.state==='completed'?'exercise':'book'} size={18}/>}</div></div></>
   return <li key={row.number} data-state={row.state}>{isSample?<Link className="ap-lesson-card" to={previewUrl({view:'lesson',part:'vocabulary',word:2})}>{content}</Link>:<div className="ap-lesson-card">{content}</div>}</li>
  })}</ol>{!visible.length&&<section className="ap-empty"><h2>Chưa tìm thấy bài phù hợp</h2><p>Thử tên ngắn hơn hoặc xem lại toàn bộ bài học.</p><button className="ap-button ap-button-secondary" onClick={()=>{setSearch('');setFilter('all')}}>Xóa bộ lọc</button></section>}</>:<PreviewMap state={state} level={level} total={current.total}/>}
 </>
}

function PreviewProfile({state,update,storageAvailable}:{state:PreviewState;update:PreviewPatch;storageAvailable:boolean}){
 const [name,setName]=useState(state.name),[goal,setGoal]=useState(state.goal),[reduced,setReduced]=useState(state.reduced),[saved,setSaved]=useState(false)
 return <><header className="ap-page-heading"><div><h1>Hồ sơ của bạn</h1><p>Chọn một nhịp học vừa với ngày của mình.</p></div></header><div className="ap-profile-layout"><section className="ap-profile-card"><div className="ap-profile-person"><span>{state.name.charAt(0).toUpperCase()}</span><div><h2>{state.name}</h2><p>Hồ sơ mẫu · HSK 1</p></div></div><form onSubmit={event=>{event.preventDefault();if(name.trim()){update({name:name.trim().slice(0,40),goal,reduced});setSaved(true)}}}><label className="ap-field">Tên hiển thị<input value={name} maxLength={40} required onChange={event=>{setName(event.target.value);setSaved(false)}}/></label><fieldset className="ap-goal-picker"><legend>Mục tiêu học mỗi ngày</legend>{[5,10,15].map(minutes=><label key={minutes} data-selected={goal===minutes}><input type="radio" name="preview-goal" checked={goal===minutes} onChange={()=>{setGoal(minutes);setSaved(false)}}/>{minutes} phút</label>)}</fieldset><label className="ap-motion-preference"><input type="checkbox" checked={reduced} onChange={event=>{setReduced(event.target.checked);setSaved(false)}}/><span>Giảm chuyển động<small>Giữ các chuyển đổi nhẹ và yên tĩnh.</small></span></label><button className="ap-button" type="submit">{saved?'Đã lưu thiết lập':'Lưu thiết lập'}</button>{saved&&<p className="ap-profile-saved" role="status">Đã lưu thiết lập của bản trải nghiệm.</p>}</form></section><aside className="ap-profile-progress"><h2>Nhìn lại tiến bộ</h2><dl><div><dt>Từ vựng mẫu đã xem</dt><dd>{state.seen.length}/6</dd></div><div><dt>Từ đã ôn</dt><dd>{state.reviewed.length}/6</dd></div><div><dt>Lần luyện tập mẫu</dt><dd>{state.attempts.length}</dd></div></dl>{state.attempts.length>0&&<div className="ap-attempts"><h3>Kết quả luyện tập mẫu</h3>{state.attempts.slice(-5).map((attempt,i)=><p key={i}><span>Lần {state.attempts.length-Math.min(5,state.attempts.length)+i+1}</span><strong>{attempt.score}/100</strong></p>)}</div>}<p className="ap-profile-note">{storageAvailable?'Tiến độ thử được lưu riêng trên trình duyệt này.':'Trình duyệt đang hạn chế lưu trữ. Tiến độ thử chỉ được giữ trong lần mở này.'} Không thay đổi hồ sơ hoặc kết quả học thật.</p></aside></div></>
}
