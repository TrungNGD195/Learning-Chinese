import { useCallback, useEffect, useMemo, useRef, useState, type MouseEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router'
import { useQueryClient } from '@tanstack/react-query'
import { AcademyIcon } from '../../components/academy/AcademyIcon'
import { Companion } from '../../components/academy/Companion'
import type { ForwardWallScene } from './createForwardWallScene'
import { clampJourneyProgress, forwardProgressAt, forwardScrollAt } from './forwardGeometry'
import { advanceAscentCamera } from './paintedAscent'
import { spatialLayout, SPATIAL_TREAD } from './spatialWallPath'
import { createWheelStepIntent, nextSpatialStep, snapSpatialStep } from './spatialStepInput'
import { chapterArrivalWaypoint, CHAPTER_ENTRY_MS, CHAPTER_COVER_DELAY_MS } from './chapterEntry'
import type { JourneyStop } from './journeyData'
import { WallLock } from './GreatWallMap'
import { createBoMotion, updateBoMotion } from './boMotion'
import { useJourneyCloud } from './journeyCloudContext'
import { queryKeys } from '../../app/query/keys'
import { getLesson } from '../lesson/api'
import { getLessonProgress } from '../progress/api'

type JourneyProps = { stops: JourneyStop[]; currentId?: string; focusId?: string; finished: boolean; levelNumber: number; locateSignal?: number; nextLevel?: { number: number; destination: string } }
const prefersReducedMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
const titleOf = (stop: JourneyStop) => stop.planned ? 'Sắp có nội dung' : stop.name.replace(/^Bài học \d+:\s*/, '').replace(/^Kiểm tra định kỳ \d+:\s*/, '')
const statusOf = (stop: JourneyStop, current: boolean) => stop.planned ? 'Sắp có nội dung' : stop.state === 'COMPLETED' ? 'Đã hoàn thành' : stop.state === 'LOCKED' ? 'Đã khóa' : current ? 'Bạn đang ở đây' : 'Có thể học'

export function ForwardWallJourney({ stops: inputStops, currentId, focusId, finished, levelNumber, locateSignal = 0, nextLevel }: JourneyProps) {
  const snapshot = JSON.stringify(inputStops)
  const stops = useMemo<JourneyStop[]>(() => JSON.parse(snapshot), [snapshot])
  const [mode, setMode] = useState<'walk' | 'overview'>(() => prefersReducedMotion() ? 'overview' : 'walk')
  const focusIndex = Math.max(0, stops.findIndex(stop => stop.id === (focusId ?? currentId)))
  const layout=useMemo(()=>spatialLayout(levelNumber,stops.length),[levelNumber,stops.length])
  const pathCount=layout.maxProgress+1
  const [focusedWaypoint,setFocusedWaypoint]=useState(levelNumber>1?0:focusIndex)
  const [focusedIndex, setFocusedIndex] = useState(focusIndex)
  const [stepEdges, setStepEdges] = useState({ start: true, end: false })
  const [loading, setLoading] = useState(true)
  const [notice, setNotice] = useState('')
  const [unavailable, setUnavailable] = useState(false)
  const [entering, setEntering] = useState(false)
  const [avatarFallback, setAvatarFallback] = useState(false)
  const [helperOpen, setHelperOpen] = useState(false)
  const track = useRef<HTMLDivElement>(null), viewport = useRef<HTMLDivElement>(null), canvas = useRef<HTMLCanvasElement>(null)
  const backdrop = useRef<HTMLImageElement>(null)
  const avatar = useRef<HTMLDivElement>(null), shadow = useRef<HTMLDivElement>(null)
  const entry = useRef<{ at: number; index: number } | null>(null)
  const entryStarter = useRef<(index: number) => void>(() => {})
  const chapterEntry = useRef<{at:number}|null>(null)
  const chapterStarter = useRef<()=>void>(()=>{})
  const chapterCancel = useRef<()=>void>(()=>{})
  const progressNow = useRef(focusIndex)
  const nodes = useRef<(HTMLLIElement | null)[]>([])
  const locator = useRef<(index: number, instant?: boolean) => void>(() => {})
  const waypointLocator=useRef<(index:number,instant?:boolean)=>void>(()=>{})
  const stepper = useRef<(direction: number) => void>(() => {})
  const pendingWaypoint=useRef<number|null>(null)
  const pendingIndex = useRef<number | null>(null)
  const enterTimer = useRef(0)
  const lastLocateSignal = useRef(locateSignal)
  const navigate = useNavigate()
  const location = useLocation()
  const travel = useJourneyCloud(), queryClient = useQueryClient()
  const storageKey = `bo-spatial-wall-v2-hsk-${levelNumber}`
  const identity = stops.map(stop => stop.id).join('|')

  useEffect(() => () => window.clearTimeout(enterTimer.current), [])
  useEffect(()=>{
    const interrupt=()=>{window.clearTimeout(enterTimer.current);entry.current=null;chapterCancel.current();setEntering(false);travel?.cancel()}
    window.addEventListener('popstate',interrupt)
    return()=>window.removeEventListener('popstate',interrupt)
  },[travel])
  useEffect(() => {
    const preference = window.matchMedia?.('(prefers-reduced-motion: reduce)')
    const change = () => { if (preference?.matches) setMode('overview') }
    preference?.addEventListener?.('change', change)
    return () => preference?.removeEventListener?.('change', change)
  }, [])
  useEffect(() => {
    if (mode !== 'walk' || !track.current || !viewport.current || !canvas.current) return
    const route = track.current, view = viewport.current, surface = canvas.current
    let scene: ForwardWallScene | null = null, disposed = false, frame = 0, saveTimer = 0
    let progress = levelNumber>1?0:focusIndex, target = progress, start = 0, step = 420, lastTime = 0, dirty = true, lastFocus = -1
    const reduced = prefersReducedMotion()
    const save = () => { try { sessionStorage.setItem(storageKey, JSON.stringify({ progress: target, identity })) } catch { /* Optional tab-local position. */ } }
    try {
      const saved = JSON.parse(sessionStorage.getItem(storageKey) || 'null')
      if (saved?.identity === identity && Number.isFinite(saved.progress)) progress = clampJourneyProgress(saved.progress, pathCount)
    } catch { /* First visit or unavailable storage. */ }
    try {const arrival=`bo-spatial-marker-arrival-${levelNumber}`,position=chapterArrivalWaypoint(sessionStorage.getItem(arrival),layout.start,layout.leadIn);if(position!==null){progress=position;sessionStorage.removeItem(arrival)}}catch{/* Navigation remains usable without storage. */}
    if (pendingIndex.current !== null) { progress = pendingIndex.current+layout.leadIn;pendingIndex.current = null }
    if (pendingWaypoint.current !== null) {progress=pendingWaypoint.current;pendingWaypoint.current=null}
    progress = snapSpatialStep(progress, layout.interval, layout.maxProgress)
    target = progress
    const updateEdges = () => setStepEdges(previous => {
      const next = { start: target <= .00001, end: target >= layout.maxProgress - .00001 }
      return previous.start === next.start && previous.end === next.end ? previous : next
    })
    updateEdges()
    const camera = {position:progress,velocity:0}
    const motion = createBoMotion(progress)
    let settleTimer = 0, celebrationTimer = 0, celebrationUntil = 0, celebrateReturn = finished
    try {
      const last = JSON.parse(sessionStorage.getItem('bo-journey-last-entry') || 'null')
      if (last?.level === levelNumber && !last.completed && stops.find(stop => stop.id === last.unit)?.state === 'COMPLETED') {
        celebrateReturn = true;sessionStorage.removeItem('bo-journey-last-entry')
      }
    } catch { /* Celebration is optional and never changes learning progress. */ }
    let side = 0
    const away = avatar.current?.querySelector<HTMLElement>('.bo-sprite--away')
    const toward = avatar.current?.querySelector<HTMLElement>('.bo-sprite--toward')
    const stop = () => { cancelAnimationFrame(frame);frame = 0;lastTime = 0;delete view.dataset.cameraMoving }
    const draw = (time = performance.now(), elapsed = 16) => {
      if (!scene) return
      const entryAmount = entry.current ? Math.max(0, Math.min(1, (time - entry.current.at) / 480)) : 0
      const chapterAmount=chapterEntry.current?Math.max(0,Math.min(1,(time-chapterEntry.current.at)/CHAPTER_ENTRY_MS)):undefined
      const movement = updateBoMotion(motion, progress + entryAmount * (3.2/layout.interval)+(chapterAmount??0)*3.1/layout.interval, elapsed, time,{span:layout.interval,length:SPATIAL_TREAD*2})
      const pose = !movement.walking && !entry.current && !chapterEntry.current
      side += ((pose ? 1 : 0) - side) * (1 - Math.exp(-elapsed / 240))
      const result = scene.render(progress, { entry: entryAmount, chapterEntry:chapterAmount, side: side * (1 - entryAmount), moving: movement.walking || !!entry.current || !!chapterEntry.current || progress !== target })
      progressNow.current = progress
      result.gates.forEach((gate, index) => {
        const node = nodes.current[index]
        if (!node) return
        node.hidden = !gate.visible
        if (!gate.visible) return
        node.style.transform = gate.transform??`translate3d(${gate.x}px,${gate.y}px,0)`
        node.style.transformOrigin=gate.transform?'0 0':'center'
        node.style.width = `${gate.width}px`;node.style.height = `${gate.height}px`
        node.style.opacity = String(gate.opacity);node.style.zIndex = String(stops.length - index)
        const near = Math.abs(index+layout.leadIn - progress) < .8
        node.dataset.near = String(near);node.inert = gate.opacity < .15
        node.style.pointerEvents = gate.opacity < .15 ? 'none' : ''
        node.style.setProperty('--painted-plaque-font', `${gate.transform?62:Math.max(17, Math.min(28, gate.width * .062))}px`)
      })
      if (avatar.current) {
        const cellHeight = result.avatar.height * 1.5
        avatar.current.style.width = `${cellHeight * .8}px`;avatar.current.style.height = `${cellHeight}px`
        avatar.current.style.transform = `translate3d(${result.avatar.x}px,${result.avatar.y}px,0) translate(-50%,-97.5%)`
        avatar.current.style.opacity=String(result.avatar.opacity)
        avatar.current.style.filter=`brightness(${result.avatar.brightness})`
        avatar.current.dataset.motion = !reduced && (movement.walking || entry.current || chapterEntry.current) ? 'walking' : 'idle'
        avatar.current.dataset.facing = movement.direction < 0 && !entry.current && !chapterEntry.current ? 'toward' : 'away'
        avatar.current.dataset.frame = String(movement.frame)
        avatar.current.dataset.celebrating = String(pose && time < celebrationUntil)
        const position = `${movement.frame % 4 * 100 / 3}% ${Math.floor(movement.frame / 4) * 100}%`
        if (away) away.style.backgroundPosition = position
        if (toward) toward.style.backgroundPosition = position
        avatar.current.style.setProperty('--bo-pose', String(pose ? 1 : 0))
      }
      if (movement.walking && !entry.current && !chapterEntry.current) {
        window.clearTimeout(settleTimer)
        if (progress === target) settleTimer = window.setTimeout(() => draw(performance.now(), 240), 220)
      }
      if (shadow.current) {
        shadow.current.style.transform = `translate3d(${result.avatar.x}px,${result.avatar.y}px,0) translate(-50%,-50%)`
        shadow.current.style.width = `${result.avatar.height * .5}px`;shadow.current.style.height = `${result.avatar.height * .09}px`
        shadow.current.style.opacity=String(result.avatar.opacity)
      }
      view.dataset.progress = String(progress)
      view.dataset.elevation = String(result.avatar.elevation)
      view.dataset.heading = String(result.heading)
      view.dataset.scene = result.stage
      view.dataset.entryProgress = String(entryAmount)
      if(chapterAmount!==undefined)view.dataset.chapterEntry=String(chapterAmount)
      else delete view.dataset.chapterEntry
      view.dataset.worldPosition=JSON.stringify({x:result.world.x,y:result.world.y,z:result.world.z})
      view.dataset.worldDistance=String(result.world.distance)
      view.dataset.fog=String(result.world.fog)
      view.dataset.gateStages=JSON.stringify(result.world.gateStages)
      view.dataset.landmarks=JSON.stringify(result.world.landmarks)
      view.dataset.graphics=JSON.stringify(result.world.graphics)
      const nearest = progress < .00001 ? 0 : progress > layout.maxProgress - .00001 ? layout.maxProgress : Math.max(layout.leadIn, Math.min(layout.maxProgress - 1, Math.round(progress)))
      if (nearest !== lastFocus) { lastFocus = nearest;setFocusedWaypoint(nearest);setFocusedIndex(Math.max(0,Math.min(stops.length-1,nearest-layout.leadIn))) }
    }
    const paint = (time: number) => {
      frame = 0
      if (disposed || document.hidden) return
      if (dirty) { target=snapSpatialStep(forwardProgressAt(window.scrollY,start,step,pathCount),layout.interval,layout.maxProgress);updateEdges();dirty = false }
      const elapsed = lastTime ? Math.min(250, Math.max(0, time - lastTime)) : 1000 / 60
      if(reduced)progress=target
      else {for(let remaining=elapsed;remaining>0;remaining-=16)advanceAscentCamera(camera,target,Math.min(16,remaining),3.4/layout.interval);progress=camera.position}
      lastTime = time;draw(time, elapsed)
      if ((progress !== target || entry.current || chapterEntry.current&&time-chapterEntry.current.at<CHAPTER_ENTRY_MS) && scene) { view.dataset.cameraMoving = 'true';frame = requestAnimationFrame(paint) }
      else stop()
    }
    const schedule = () => { if (!frame && !disposed && !document.hidden) frame = requestAnimationFrame(paint) }
    const scroll = () => {
      if(chapterEntry.current){const fixed=forwardScrollAt(target,start,step,pathCount);if(Math.abs(window.scrollY-fixed)>1)window.scrollTo({top:fixed,behavior:'instant'});return}
      dirty = true;schedule();window.clearTimeout(saveTimer);saveTimer = window.setTimeout(save, 200)
    }
    const measure = () => {
      if (!view.clientWidth || !view.clientHeight) return
      step = view.clientWidth < 700 ? 360 : 420
      const stickyTop = Number.parseFloat(getComputedStyle(view).top) || 0
      start = route.getBoundingClientRect().top + window.scrollY - stickyTop
      route.style.height = `${view.clientHeight + layout.maxProgress * step}px`
      scene?.resize(view.clientWidth, view.clientHeight)
      window.scrollTo({ top: forwardScrollAt(target, start, step, pathCount), behavior: 'instant' })
      progress = target;camera.position=target;camera.velocity=0;dirty = false;draw()
    }
    const go = (index: number, instant = false) => {
      const next = snapSpatialStep(clampJourneyProgress(index, pathCount),layout.interval,layout.maxProgress)
      target=next;updateEdges()
      window.scrollTo({ top: forwardScrollAt(next, start, step, pathCount), behavior: 'instant' })
      if (instant || reduced) { stop();window.clearTimeout(settleTimer);Object.assign(motion,createBoMotion(next));target = next;progress = next;camera.position=next;camera.velocity=0;dirty = false;draw() }
      else { dirty = true;schedule() }
    }
    locator.current = (index,instant)=>go(index+layout.leadIn,instant)
    waypointLocator.current=go
    stepper.current = direction => { if (!entry.current&&!chapterEntry.current) go(nextSpatialStep(target,direction,layout.interval,layout.maxProgress)) }
    const wheelIntent=createWheelStepIntent()
    const wheel = (event: WheelEvent) => {
      if(event.ctrlKey||event.metaKey||event.shiftKey||Math.abs(event.deltaX)>Math.abs(event.deltaY)||!event.deltaY)return
      event.preventDefault()
      const direction=wheelIntent(event.deltaY,performance.now(),event.deltaMode)
      if(direction)stepper.current(direction)
    }
    const key = (event: KeyboardEvent) => {
      if(event.key!=='ArrowUp'&&event.key!=='ArrowDown')return
      if(event.ctrlKey||event.metaKey||event.altKey||event.shiftKey)return
      if(event.target instanceof Element&&event.target.closest('input,textarea,select,[contenteditable="true"],[role="textbox"],[role="listbox"]'))return
      event.preventDefault()
      if(!event.repeat)stepper.current(event.key==='ArrowUp'?1:-1)
    }
    entryStarter.current = (index) => {
      go(index+layout.leadIn)
      entry.current = { at: performance.now() + 140, index }
      schedule()
    }
    chapterStarter.current=()=>{window.clearTimeout(settleTimer);chapterEntry.current={at:performance.now()};schedule()}
    chapterCancel.current=()=>{chapterEntry.current=null;Object.assign(motion,createBoMotion(progress));stop();draw()}
    const fallback = () => {
      if (disposed) return
      setUnavailable(true);setMode('overview');setLoading(false)
      setNotice('Bạn có thể tiếp tục chọn bài trong toàn bộ lộ trình bên dưới.')
    }
    const lost = (event: Event) => { event.preventDefault();fallback() }
    const visibility = () => {
      view.dataset.paused = String(document.hidden)
      if (document.hidden) { stop();save() } else { dirty = true;schedule() }
    }
    const resize = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(measure) : null
    measure();resize?.observe(view)
    window.addEventListener('scroll', scroll, { passive: true });window.addEventListener('resize', measure, { passive: true })
    view.addEventListener('wheel',wheel,{passive:false});window.addEventListener('keydown',key)
    window.addEventListener('pagehide', save);document.addEventListener('visibilitychange', visibility)
    surface.addEventListener('webglcontextlost', lost)
    const colors = stops.map(stop => stop.id === currentId && !finished ? '#b73c34' : stop.state === 'COMPLETED' ? '#296747' : '#738364')
    void import('./createForwardWallScene').then(async ({ createForwardWallScene }) => {
      if (disposed) return
      scene = createForwardWallScene(surface, colors, schedule,levelNumber)
      scene.resize(view.clientWidth, view.clientHeight)
      await scene.ready
      if (disposed) return
      if (celebrateReturn) { celebrationUntil = performance.now() + 1300;celebrationTimer = window.setTimeout(() => draw(), 1400) }
      draw();setLoading(false);view.dataset.ready = 'true'
    }).catch(fallback)
    return () => {
      save();disposed = true;stop();resize?.disconnect();window.clearTimeout(saveTimer);window.clearTimeout(settleTimer);window.clearTimeout(celebrationTimer);scene?.dispose();entry.current = null;chapterEntry.current=null;chapterStarter.current=()=>{};chapterCancel.current=()=>{}
      window.removeEventListener('scroll', scroll);window.removeEventListener('resize', measure);window.removeEventListener('pagehide', save)
      view.removeEventListener('wheel',wheel);window.removeEventListener('keydown',key);stepper.current=()=>{}
      document.removeEventListener('visibilitychange', visibility);surface.removeEventListener('webglcontextlost', lost);locator.current = () => {};waypointLocator.current=()=>{};entryStarter.current = () => {}
    }
  }, [mode, focusIndex, identity, storageKey, stops, currentId, finished, levelNumber,layout,pathCount])

  useEffect(() => {
    if (!locateSignal || locateSignal === lastLocateSignal.current) return
    lastLocateSignal.current = locateSignal
    travel?.cancel();window.clearTimeout(enterTimer.current);entry.current = null;setEntering(false)
    const relocate = () => {
      if (mode === 'walk') locator.current(focusIndex,true)
      else document.getElementById(`forward-overview-${focusId}`)?.scrollIntoView({ block: 'center', behavior: 'instant' })
    }
    if(travel&&!prefersReducedMotion())travel.travel({destination:location.pathname,relocate,short:true,returning:true})
    else relocate()
  }, [locateSignal, focusIndex, focusId, mode, travel,location.pathname])

  const prefetch = useCallback((destination: string) => {
    const lessonId = destination.match(/^\/lessons\/([^/]+)/)?.[1]
    if (!lessonId) return undefined
    const id = decodeURIComponent(lessonId)
    return Promise.all([
      queryClient.prefetchQuery({ queryKey: queryKeys.lesson(id), queryFn: () => getLesson(id), staleTime: 30_000 }),
      queryClient.prefetchQuery({ queryKey: queryKeys.lessonProgress(id), queryFn: () => getLessonProgress(id), staleTime: 10_000 }),
    ])
  }, [queryClient])
  useEffect(() => {
    if (mode !== 'walk') return
    const destination = stops[focusedIndex]?.destination
    if (destination) void prefetch(destination)
  }, [mode, focusedIndex, stops, prefetch])
  function openLesson(event: MouseEvent<HTMLAnchorElement>, destination: string, index?: number) {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || prefersReducedMotion()) return
    event.preventDefault()
    if (entering) return
    const far = mode !== 'walk' || Math.abs((index ?? focusedIndex)+layout.leadIn - progressNow.current) > 1.1
    const depart = () => {
      const stop = stops[index ?? focusedIndex]
      if (stop) try { sessionStorage.setItem('bo-journey-last-entry', JSON.stringify({ level: levelNumber, unit: stop.id, completed: stop.state === 'COMPLETED' })) } catch { /* Optional return gesture. */ }
      if (!far && !prefersReducedMotion()) { setEntering(true);entryStarter.current(index ?? focusedIndex) }
    }
    if (travel) {
      if (travel.travel({ destination, depart, prepare: prefetch(destination), short: far, returning: far, cancelled: () => { entry.current = null;setEntering(false) } })) setEntering(true)
      return
    }
    depart()
    enterTimer.current = window.setTimeout(() => { void Promise.resolve(navigate(destination)).catch(() => setEntering(false)) }, far ? 200 : 760)
  }
  function explain(stop: JourneyStop) {
    setNotice(stop.planned ? `${stop.shortName} đang được chuẩn bị. Bạn có thể tiếp tục những bài đã mở.` : `${stop.shortName} chưa mở. ${stops.find(item => item.id === currentId)?.kind === 'foundation' ? 'Hoàn thành bài phát âm để bắt đầu HSK 1.' : 'Hoàn thành bài trước và đạt từ 80% phần luyện tập để tiếp tục.'}`)
  }
  function showWalk(index?: number) {
    window.clearTimeout(enterTimer.current)
    if (index !== undefined) pendingIndex.current = index
    setLoading(true);setNotice('');setEntering(false);setMode('walk')
  }
  const focused = stops[focusedIndex] ?? stops[focusIndex]
  const atStart=layout.leadIn>0&&focusedWaypoint===0
  const atEnd=focusedWaypoint>=layout.maxProgress
  const markerLevel=atStart?levelNumber-1:levelNumber
  function showWaypoint(index:number){
    travel?.cancel();entry.current=null;setEntering(false)
    if(mode==='walk')waypointLocator.current(index)
    else {pendingWaypoint.current=index;showWalk()}
  }
  function openChapter(event: MouseEvent<HTMLAnchorElement>, destination: string) {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
    event.preventDefault()
    if(entering)return
    const target=destination.match(/^\/hsk\/(\d+)$/)?.[1],arrival=target?`bo-spatial-marker-arrival-${target}`:null
    try {if(arrival)sessionStorage.setItem(arrival,JSON.stringify({marker:layout.end,firstLesson:true}))}catch{/* Optional first-lesson arrival. */}
    const clearArrival=()=>{try{if(arrival)sessionStorage.removeItem(arrival)}catch{/* Optional storage. */}}
    const cancelled=()=>{clearArrival();chapterCancel.current();setEntering(false)}
    if(prefersReducedMotion()){void navigate(destination);return}
    const walkIn=mode==='walk'&&atEnd
    if (travel) {
      const accepted=travel.travel({destination,short:true,returning:true,coverDelay:walkIn?CHAPTER_COVER_DELAY_MS:undefined,depart:()=>{if(walkIn)chapterStarter.current()},cancelled})
      if(accepted)setEntering(true)
      else clearArrival()
    } else {
      if(walkIn){setEntering(true);chapterStarter.current();enterTimer.current=window.setTimeout(()=>{void navigate(destination)},CHAPTER_COVER_DELAY_MS)}
      else void navigate(destination)
    }
  }
  function label(stop: JourneyStop) {
    const current = stop.id === currentId
    return <><span className="forward-gate-number">{stop.state === 'COMPLETED' ? <AcademyIcon name="check" size={20}/> : stop.state === 'LOCKED' && !stop.planned ? <WallLock/> : <AcademyIcon name={stop.kind === 'foundation' ? 'sound' : 'book'} size={20}/>} {stop.shortName}</span><span role="heading" aria-level={2} className="forward-gate-title">{titleOf(stop)}</span><span className="forward-gate-status">{statusOf(stop, current)}</span></>
  }
  return <>
    <div className="wall-view-controls forward-view-controls"><span><AcademyIcon name="path" size={18}/>{mode === 'walk' ? 'Cuộn hoặc ↑/↓ · mỗi nhịp một bậc' : 'Toàn bộ lộ trình · Chọn bài bạn muốn học'}</span><button type="button" aria-pressed={mode === 'overview'} onClick={() => { travel?.cancel();window.clearTimeout(enterTimer.current);entry.current = null;setEntering(false);setNotice('');if (mode === 'walk') setMode('overview');else showWalk() }} disabled={mode === 'overview' && unavailable}>{mode === 'walk' ? 'Xem toàn bộ lộ trình' : 'Trở lại Trường Thành'}</button></div>
    {notice && <div className="wall-stop-notice" role="status"><p>{notice}</p><button type="button" aria-label="Đóng hướng dẫn bài học" onClick={() => setNotice('')}>Đóng</button></div>}
    {mode === 'walk' ? <div ref={track} className="forward-track" style={{ height: `calc(100svh + ${layout.maxProgress * 420}px)` }}>
      <div ref={viewport} className="forward-viewport" data-level={levelNumber} data-path-count={pathCount} data-lead-in={layout.leadIn} data-waypoint={focusedWaypoint} data-entering={entering || undefined} role="region" aria-label={`Trường Thành HSK ${levelNumber}, góc nhìn theo Bo`}>
        <div className="forward-world forward-world--painted forward-world--spatial">
          <img ref={backdrop} className="forward-mountains" src="/academy/great-wall/painted-v2/landing-desktop.webp" alt="" fetchPriority="high"/>
          <canvas ref={canvas} className="forward-canvas" aria-hidden="true"/>
          <ol className="forward-gates" aria-label="Các cổng bài học">{stops.map((stop, index) => <li ref={node => { nodes.current[index] = node }} key={stop.id} className="forward-gate" hidden data-state={stop.planned ? 'planned' : stop.id === currentId && !finished ? 'current' : stop.state.toLowerCase()} data-unit-id={stop.id} data-kind={stop.kind}>
            {stop.destination ? <Link className="forward-gate-link" to={stop.destination} onClick={event => openLesson(event, stop.destination!, index)} onPointerEnter={() => { void prefetch(stop.destination!) }} onFocus={() => { if (document.activeElement?.matches(':focus-visible')) locator.current(index, true);void prefetch(stop.destination!) }} aria-label={`${stop.state === 'COMPLETED' ? 'Ôn' : 'Học'} ${stop.name}`} aria-current={stop.id === currentId && !finished ? 'step' : undefined}>{label(stop)}</Link> : <button type="button" className="forward-gate-link" aria-disabled="true" aria-label={`${stop.name}, ${statusOf(stop, false)}`} onFocus={() => { if (document.activeElement?.matches(':focus-visible')) locator.current(index, true) }} onClick={() => explain(stop)}>{label(stop)}</button>}
          </li>)}</ol>
          <div ref={shadow} className="bo-foot-shadow" aria-hidden="true"/>
          <div ref={avatar} className="bo-journey-avatar" data-motion="idle" data-facing="away" aria-hidden="true">{avatarFallback ? <Companion pose="guide" decorative/> : <><span className="bo-sprite bo-sprite--away"/><span className="bo-sprite bo-sprite--toward"/><span className="bo-sprite bo-sprite--pose"/></>}</div>
          <div hidden aria-hidden="true">{['bo-walk-away-v1.webp','bo-walk-toward-v1.webp','bo-journey-poses-v1.webp'].map(file => <img key={file} data-bo-preload src={`/academy/great-wall/${file}`} alt="" onError={() => setAvatarFallback(true)}/>)}</div>
        </div>
        {loading && <p className="forward-loading" role="status">Đang mở Trường Thành…</p>}
        {atEnd && nextLevel && <Link className="painted-next-chapter" to={nextLevel.destination} onClick={event => openChapter(event, nextLevel.destination)}><AcademyIcon name="path" size={20}/><span>Tiếp đến HSK {nextLevel.number}</span><AcademyIcon name="arrow" size={20}/></Link>}
        <div className="forward-navigation" aria-label="Di chuyển từng bậc trên Trường Thành">
          <button type="button" aria-label="Lùi một bậc" disabled={stepEdges.start || loading} onClick={() => stepper.current(-1)}><span className="forward-arrow-down"><AcademyIcon name="arrow"/></span></button>
          <div className="forward-current-caption">{atStart||atEnd?<><strong>Mốc HSK {markerLevel}</strong><span>{atStart?`Từ đây, cùng Bo lên chặng HSK ${levelNumber}`:nextLevel?`Đường thành tiếp tục lên HSK ${nextLevel.number}`:'Tháp canh trên hành trình cùng Bo'}</span><small>Tháp canh · Mốc hành trình</small></>:<><strong>{focused?.shortName} <span>· {focusedIndex+1}/{stops.length} cổng</span></strong><span>{focused ? titleOf(focused) : ''}</span><small>{focused ? statusOf(focused, focused.id === currentId) : ''}</small></>}</div>
          {atEnd&&nextLevel?<Link className="forward-next-level-button" to={nextLevel.destination} aria-label={`Đi đến HSK ${nextLevel.number}`} onClick={event=>openChapter(event,nextLevel.destination)}><AcademyIcon name="arrow"/></Link>:<button type="button" aria-label="Lên một bậc" disabled={stepEdges.end||loading} onClick={()=>stepper.current(1)}><span className="forward-arrow-up"><AcademyIcon name="arrow"/></span></button>}
        </div>
        {!atStart&&!atEnd&&!!focused?.lessonNumber && focused.lessonNumber % 5 === 0 && <div className="journey-rest-friend"><button type="button" aria-label="Nghe lời nhắc học tập" aria-expanded={helperOpen} onClick={() => setHelperOpen(value => !value)}><Companion pose={focused.lessonNumber % 10 === 0 ? 'truc' : 'but'} decorative/></button>{helperOpen && <p>Thử nhớ nghĩa của từ trước khi nhìn lại ví dụ, rồi đọc cả câu thành tiếng.</p>}</div>}
      </div>
    </div> : <ol className="forward-overview" aria-label="Các bài trong cấp độ HSK">{stops.map((stop, index) => <li key={stop.id} id={`forward-overview-${stop.id}`} data-state={stop.planned ? 'planned' : stop.id === currentId && !finished ? 'current' : stop.state.toLowerCase()} data-kind={stop.kind}>
      {stop.destination ? <Link className="forward-overview-link" to={stop.destination} aria-label={`${stop.state === 'COMPLETED' ? 'Ôn' : 'Học'} ${stop.name}`} onClick={event => openLesson(event, stop.destination!, index)}>{label(stop)}</Link> : <button type="button" className="forward-overview-link" aria-disabled="true" onClick={() => explain(stop)}>{label(stop)}</button>}
      {!unavailable && <button className="forward-overview-locate" type="button" aria-label={`Định vị ${stop.shortName} trên Trường Thành`} onClick={() => showWalk(index)}><AcademyIcon name="path" size={18}/></button>}
    </li>)}</ol>}
    {mode==='overview'&&<nav className="spatial-milestone-navigation" aria-label="Mốc các chặng HSK">{!unavailable&&<>{layout.leadIn>0&&<button type="button" onClick={()=>showWaypoint(0)}>Từ mốc HSK {levelNumber-1}</button>}<button type="button" onClick={()=>showWaypoint(layout.maxProgress)}>Đến tháp canh HSK {levelNumber}</button></>}{nextLevel&&<Link to={nextLevel.destination} onClick={event=>openChapter(event,nextLevel.destination)}>Tiếp đến HSK {nextLevel.number}<AcademyIcon name="arrow" size={18}/></Link>}</nav>}
  </>
}
