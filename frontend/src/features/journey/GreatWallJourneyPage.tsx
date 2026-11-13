import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'
import { queryKeys } from '../../app/query/keys'
import { AcademyIcon } from '../../components/academy/AcademyIcon'
import { Alert, Button, LoadingState } from '../../components/ui'
import { getCurriculum, getHskLevels } from '../curriculum/api'
import { getProgressOverview } from '../progress/api'
import { getPronunciationLesson } from '../pronunciation/api'
import {LessonEntryLink} from './LessonEntryLink'
import { CurriculumCover } from '../curriculum/CurriculumCover'
import { curriculumCoverTopic } from '../curriculum/curriculumCoverData'
import {Companion} from '../../components/academy/Companion'
import {getDashboard} from '../dashboard/api'
import {ResumeLearningLink} from '../curriculum/ResumeLearningLink'
import { FoundationCards } from '../curriculum/FoundationCards'
import { LearningFlow } from '../curriculum/LearningFlow'
import '../../styles/academy-curriculum.css'
import { continuousJourneyStops, plannedLessonCounts, orderedJourneyUnits, type JourneyStop } from './journeyData'

export function GreatWallJourneyPage({ requestedLevel }: { requestedLevel?: string }) {
  const [notice,setNotice]=useState(''),[search,setSearch]=useState(''),[filter,setFilter]=useState('all')
  const resume=useQuery({queryKey:queryKeys.dashboard,queryFn:getDashboard})
  const target=resume.data?.continue_learning
  const levels = useQuery({ queryKey: queryKeys.curriculumLevels, queryFn: getHskLevels })
  const pronunciation = useQuery({ queryKey: queryKeys.pronunciationLesson, queryFn: getPronunciationLesson })
  const overview = useQuery({ queryKey: queryKeys.progressOverview, queryFn: getProgressOverview })
  const allLevels = [...(levels.data ?? [])].sort((a, b) => a.level_number - b.level_number)
  const level = requestedLevel ? allLevels.find(row => String(row.level_number) === requestedLevel) : allLevels.find(row => row.level_number === overview.data?.current_hsk) ?? allLevels.find(row => row.state === 'AVAILABLE') ?? [...allLevels].reverse().find(row => row.state === 'COMPLETED') ?? allLevels[0]
  const selectionReady = Boolean(requestedLevel) || !overview.isPending
  const curriculum = useQuery({ queryKey: queryKeys.curriculumHsk(level?.id ?? requestedLevel ?? ''), queryFn: () => getCurriculum(level!.id), enabled: !!level && selectionReady })
  const foundationDone = Boolean(pronunciation.data?.completed_at)
  const foundationRequired = !level || level.level_number === 1
  const foundationReady = !foundationRequired || foundationDone
  const levelNumber = level?.level_number ?? 1
  const units = orderedJourneyUnits(curriculum.data?.units ?? [])
  const unlocked = foundationReady && (!foundationRequired || level?.state !== 'LOCKED')
  const allStops = continuousJourneyStops(units, levelNumber, unlocked)
  const activeIndex = allStops.findIndex(stop => stop.state === 'AVAILABLE' && stop.destination)
  const active = activeIndex >= 0 ? allStops[activeIndex] : [...allStops].reverse().find(stop => stop.state === 'COMPLETED')
  const ready = (!foundationRequired || !!pronunciation.data) && !levels.isPending && (!level || (selectionReady && !!curriculum.data))
  const failed = (levels.isError && !levels.data) || (foundationRequired && pronunciation.isError && !pronunciation.data) || (!!level && curriculum.isError && !curriculum.data)
  const stale = (levels.isError && !!levels.data) || (foundationRequired && pronunciation.isError && !!pronunciation.data) || (curriculum.isError && !!curriculum.data)
  const completedLessons = allStops.filter(stop => stop.kind === 'lesson' && stop.state === 'COMPLETED').length
  const totalLessons = Math.max(plannedLessonCounts[level?.level_number ?? 1] ?? 0, allStops.filter(stop => stop.kind === 'lesson').length)
  const normalize=(text:string)=>text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\u0111/g,'d').toLowerCase()
  const visible=allStops.filter(stop=>(!search||normalize(stop.name).includes(normalize(search)))&&(filter==='all'||(filter==='COMPLETED'?stop.state==='COMPLETED':filter==='AVAILABLE'?!!stop.destination&&stop.state!=='COMPLETED':!stop.destination)))
  const explain=(stop:JourneyStop)=>setNotice(stop.planned||stop.unpublished?`${stop.shortName} đang được chuẩn bị.`:!foundationReady?'Hoàn thành bài phát âm để mở HSK 1.':`${stop.shortName} chưa mở. Hoàn thành bài trước và đạt từ 80% luyện tập để tiếp tục.`)
  const retry = () => { if (levels.isError) void levels.refetch(); if (pronunciation.isError) void pronunciation.refetch(); if (level && curriculum.isError) void curriculum.refetch() }

  return <section className="learning-curriculum screen" aria-labelledby="page-title">
    <header className="lc-heading"><div><h1 id="page-title">Giáo trình của bạn</h1><p>Học cùng Bo, vững vàng từng bước.</p></div><div className="lc-heading-actions">{foundationRequired&&pronunciation.data&&!foundationDone?<LessonEntryLink className="lc-inline-button lc-resume" to="/pronunciation/lesson">Học phát âm nền tảng<AcademyIcon name="arrow" size={17}/></LessonEntryLink>:target&&<ResumeLearningLink target={target}/>}<Companion pose="guide" decorative/></div></header>
    <LearningFlow completed={foundationDone} loading={pronunciation.isPending}/>
    <FoundationCards completed={foundationDone} loading={pronunciation.isPending} unavailable={pronunciation.isError&&!pronunciation.data}/>
    {allLevels.length>0&&<div className="lc-controls"><nav className="lc-level-tabs" aria-label="Chặng HSK">{allLevels.map(item=><Link key={item.id} to={`/hsk/${item.level_number}`} aria-current={item.id===level?.id?'page':undefined}>HSK {item.level_number}<small>{plannedLessonCounts[item.level_number]??0} bài</small></Link>)}</nav></div>}
    {notice&&<p className="lc-notice" role="status">{notice}</p>}
    {failed?<Alert tone="error" role="alert" action={<Button onClick={retry}>Thử lại</Button>}>Không thể tải giáo trình học này. Vui lòng thử lại.</Alert>:!ready&&<LoadingState>Đang tải giáo trình học…</LoadingState>}
    {stale&&<Alert tone="warning" role="status" action={<Button onClick={retry}>Thử lại</Button>}>Chưa cập nhật được giáo trình. Đang hiển thị thông tin đã tải.</Alert>}
    {requestedLevel&&!levels.isPending&&!levels.isError&&!level&&<Alert tone="error" role="alert">Không tìm thấy cấp độ HSK này.</Alert>}
    {ready&&!failed&&(!requestedLevel||level)&&<>
        <section className="lc-course-meta"><div><h2>Các bài học {level?.title??`HSK ${levelNumber}`}</h2><p>{completedLessons}/{totalLessons} bài đã hoàn thành</p></div><progress aria-label="Tiến độ cấp độ" value={completedLessons} max={totalLessons||1}/></section>
        <div className="lc-list-tools"><label><AcademyIcon name="book" size={17}/><span className="lc-accessible-title">Tìm bài học</span><input type="search" placeholder="Tìm tên hoặc số bài…" value={search} onChange={event=>setSearch(event.target.value)}/></label><select aria-label="Lọc trạng thái bài học" value={filter} onChange={event=>setFilter(event.target.value)}><option value="all">Tất cả bài học</option><option value="AVAILABLE">Có thể học</option><option value="COMPLETED">Đã hoàn thành</option><option value="LOCKED">Chưa mở</option></select></div>
        <ol className="lc-lesson-grid" aria-label="Các bài trong cấp độ HSK">{visible.map(stop=><CurriculumCard key={stop.id} stop={stop} current={stop.id===active?.id} onExplain={explain}/>)}</ol>
        {!visible.length&&<div className="lc-empty"><Companion pose="think" decorative/><h2>Chưa tìm thấy bài phù hợp</h2><p>Thử tên ngắn hơn hoặc xem lại toàn bộ bài học.</p><button type="button" className="lc-inline-button" onClick={()=>{setSearch('');setFilter('all')}}>Xóa bộ lọc</button></div>}
    </>}
  </section>
}

function CurriculumCard({stop,current,onExplain}:{stop:JourneyStop;current:boolean;onExplain:(stop:JourneyStop)=>void}){
 const status=stop.planned||stop.unpublished?'Sắp có nội dung':stop.state==='COMPLETED'?'Đã hoàn thành':current?'Đang học':stop.destination?'Có thể học':'Chưa mở'
 const content=<><div className="lc-lesson-cover" data-tone={(stop.lessonNumber??stop.slot)%4} aria-hidden="true"><CurriculumCover topic={curriculumCoverTopic(stop.name,!!(stop.planned||stop.unpublished||stop.kind==='test'))}/><span>{stop.shortName}</span></div><div className="lc-lesson-body"><h3>{stop.planned?'Bài học đang được chuẩn bị':stop.name.replace(/^Bài học \d+:\s*/,'')}</h3><div className="lc-lesson-footer"><span>{status}</span><AcademyIcon name={stop.destination?'arrow':stop.state==='COMPLETED'?'exercise':'book'} size={18}/></div></div></>
 return <li data-state={stop.planned?'planned':current?'current':stop.state.toLowerCase()}>{stop.destination?<LessonEntryLink className="lc-lesson-card" to={stop.destination} aria-label={`${stop.state==='COMPLETED'?'Ôn':'Học'} ${stop.name}`}>{content}</LessonEntryLink>:<button type="button" className="lc-lesson-card" aria-label={`${stop.shortName}: ${status}`} data-locked="true" onClick={()=>onExplain(stop)}>{content}</button>}</li>
}
