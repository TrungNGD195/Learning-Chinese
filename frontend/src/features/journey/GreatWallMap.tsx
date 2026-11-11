import { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react'
import { Link } from 'react-router'
import { AcademyIcon } from '../../components/academy/AcademyIcon'
import { Companion } from '../../components/academy/Companion'
import type { JourneyStop } from './journeyData'
import { WALL_WIDTH, dampWallCamera, wallCameraX, wallStopPositions, wallRegion } from './wallGeometry'

export function WallLock() {
  return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3"/></svg>
}
function TowerIcon() {
  return <svg width="28" height="28" viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M6 27V12H4V5h5v4h5V5h5v4h5V5h4v7h-2v15M4 27h24M12 27v-7a4 4 0 0 1 8 0v7M10 13v2m12-2v2"/></svg>
}
function SealFrame() {
  return <svg className="wall-stop__seal-frame" viewBox="0 0 120 120" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M28 9H15a6 6 0 0 0-6 6v13m83-19h13a6 6 0 0 1 6 6v13M9 92v13a6 6 0 0 0 6 6h13m64 0h13a6 6 0 0 0 6-6V92M35 10h50m25 25v50m-25 25H35M10 85V35"/><path d="M28 17H17v11m75-11h11v11M17 92v11h11m64 0h11V92"/></svg>
}
const regionArt = ['foothills', 'ridges', 'summit']
function stopStatus(stop: JourneyStop, current: boolean) {
  return stop.planned ? 'Sắp có nội dung' : stop.state === 'COMPLETED' ? 'Đã hoàn thành' : stop.state === 'LOCKED' ? 'Đã khóa' : current ? 'Bạn đang ở đây' : 'Có thể học'
}
function lessonTitle(stop: JourneyStop) {
  if (stop.planned) return 'Sắp có nội dung'
  return stop.name.replace(/^Bài học \d+:\s*/, '').replace(/^Kiểm tra định kỳ \d+:\s*/, '')
}

export function GreatWallMap({ stops: inputStops, currentId, focusId, finished, levelNumber, locateSignal = 0 }: {
  stops: JourneyStop[]; currentId?: string; focusId?: string; finished: boolean; levelNumber: number; locateSignal?: number
}) {
  const scene = useRef<HTMLDivElement>(null)
  const world = useRef<HTMLDivElement>(null)
  // Keep the imperative camera alive across unrelated parent rerenders.
  const stopSnapshot = JSON.stringify(inputStops)
  const stops = useMemo<JourneyStop[]>(() => JSON.parse(stopSnapshot), [stopSnapshot])
  const [narrow, setNarrow] = useState(() => window.matchMedia?.('(max-width: 700px)').matches ?? false)
  const [scale, setScale] = useState(1)
  const geometry = useMemo(() => wallStopPositions(stops.length, (narrow ? 215 : 250) / scale, (narrow ? 160 : 180) / scale, (narrow ? 260 : 300) / scale), [stops.length, narrow, scale])
  const [listMode, setListMode] = useState(() => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false)
  const [notice, setNotice] = useState('')
  const locator = useRef<(id?: string) => void>(() => {})
  const storageKey = `bo-wall-position-v5-hsk-${levelNumber}`
  const focusIndex = Math.max(0, stops.findIndex(stop => stop.id === (focusId ?? currentId)))
  const identity = stops.map(stop => stop.id).join('|')
  useEffect(() => {
    const viewport = window.matchMedia?.('(max-width: 700px)')
    const resized = () => setNarrow(viewport?.matches ?? false)
    viewport?.addEventListener?.('change', resized)
    return () => viewport?.removeEventListener?.('change', resized)
  }, [])
  useEffect(() => {
    const preference = window.matchMedia?.('(prefers-reduced-motion: reduce)')
    const changed = () => { if (preference?.matches) setListMode(true) }
    preference?.addEventListener?.('change', changed)
    return () => preference?.removeEventListener?.('change', changed)
  }, [])
  useEffect(() => {
    if (listMode || !scene.current || !world.current) return
    const container = scene.current, canvas = world.current
    let frame = 0, initialFrame = 0, scaleNow = 1, initialized = false
    let previousWidth = 0, lastY = 0, targetX = 0, cameraX = 0, lastFrameTime = 0
    let dirty = true, saveTimer = 0
    const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
    const save = () => { if (initialized) try { sessionStorage.setItem(storageKey, JSON.stringify({ y: lastY, height: geometry.height, identity })) } catch { /* persistence is optional */ } }
    const sceneTop = () => container.getBoundingClientRect().top + window.scrollY
    const viewportMiddle = () => Math.min(window.innerHeight * .53, 540)
    const readTarget = () => {
      const y = Math.max(0, Math.min(geometry.height, (window.scrollY + viewportMiddle() - sceneTop()) / scaleNow))
      // Short end caps no longer provide half a viewport of empty roadway.
      // Ease the camera toward each endpoint when native scrolling reaches it.
      const scrollEnd = Math.max(0, document.documentElement.scrollHeight - window.innerHeight)
      const smoothstep = (value: number) => value * value * (3 - 2 * value)
      const bottomBlend = smoothstep(Math.max(0, Math.min(1, 1 - (scrollEnd - window.scrollY) / 96)))
      const topBlend = smoothstep(Math.max(0, Math.min(1, 1 - window.scrollY / 96)))
      let cameraY = y
      if (bottomBlend) cameraY += ((geometry.points[0]?.y ?? y) - cameraY) * bottomBlend
      if (topBlend) cameraY += ((geometry.points.at(-1)?.y ?? y) - cameraY) * topBlend
      targetX = wallCameraX(cameraY * geometry.imageScaleY, geometry.sections, container.clientWidth, scaleNow, false)
      container.dataset.worldY = String(Math.round(y))
      lastY = y
    }
    const draw = () => {
      canvas.style.transform = `translate3d(${cameraX}px,0,0) scale(${scaleNow})`
      container.dataset.cameraX = String(cameraX)
    }
    const stop = () => {
      cancelAnimationFrame(frame);frame = 0;lastFrameTime = 0
      canvas.style.willChange = ''
      delete container.dataset.cameraMoving
    }
    const paint = (time: number) => {
      frame = 0
      // Read layout only after new scroll input, not throughout the easing tail.
      if (dirty) { readTarget();dirty = false }
      cameraX = reducedMotion ? targetX : dampWallCamera(cameraX, targetX, lastFrameTime ? Math.min(64, time - lastFrameTime) : 1000 / 60)
      lastFrameTime = time
      draw()
      if (cameraX !== targetX && !document.hidden) frame = requestAnimationFrame(paint)
      else stop()
    }
    const snap = () => {
      stop();readTarget();dirty = false;cameraX = targetX;draw()
    }
    const scroll = () => {
      dirty = true
      if (!frame && !document.hidden) {
        canvas.style.willChange = 'transform'
        container.dataset.cameraMoving = 'true'
        frame = requestAnimationFrame(paint)
      }
      // Defer synchronous storage work until wheel/touch input has paused.
      window.clearTimeout(saveTimer)
      saveTimer = window.setTimeout(save, 180)
    }
    const go = (index: number) => {
      const point = geometry.points[index]
      if (!point) return
      window.scrollTo({ top: Math.max(0, sceneTop() + point.y * scaleNow - viewportMiddle()), behavior: 'instant' })
      snap()
    }
    locator.current = (id) => go(Math.max(0, stops.findIndex(stop => stop.id === (id ?? currentId ?? focusId))))
    const measure = () => {
      const width = container.clientWidth
      if (!width || width === previousWidth) return
      const priorY = (window.scrollY + viewportMiddle() - sceneTop()) / scaleNow
      previousWidth = width
      scaleNow = Math.min(1.7, Math.max(.78, width / 820))
      setScale(scaleNow)
      container.style.height = `${geometry.height * scaleNow}px`
      canvas.style.width = `${WALL_WIDTH}px`
      canvas.style.setProperty('--wall-inverse-scale', String(1 / scaleNow))
      snap()
      if (!initialized) {
        initialFrame = requestAnimationFrame(() => {
          let savedY: number | null = null
          try {
            const saved = JSON.parse(sessionStorage.getItem(storageKey) || 'null')
            if (saved?.identity === identity && Number.isFinite(saved.y) && Number.isFinite(saved.height) && saved.height > 0 && saved.y >= 0 && saved.y <= saved.height) savedY = saved.y / saved.height * geometry.height
          } catch { /* first visit or blocked storage */ }
          if (savedY !== null) window.scrollTo({ top: Math.max(0, sceneTop() + savedY * scaleNow - viewportMiddle()), behavior: 'instant' })
          else go(focusIndex)
          initialized = true
          snap()
        })
      } else {
        window.scrollTo({ top: Math.max(0, sceneTop() + priorY * scaleNow - viewportMiddle()), behavior: 'instant' })
        snap()
      }
    }
    const resize = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(measure) : null
    const visibility = () => { if (document.hidden) { stop();save() } else snap() }
    resize?.observe(container)
    window.addEventListener('scroll', scroll, { passive: true })
    window.addEventListener('resize', measure, { passive: true })
    window.addEventListener('pagehide', save)
    document.addEventListener('visibilitychange', visibility)
    measure()
    return () => {
      save();resize?.disconnect();stop();cancelAnimationFrame(initialFrame);window.clearTimeout(saveTimer)
      window.removeEventListener('scroll', scroll);window.removeEventListener('resize', measure);window.removeEventListener('pagehide', save)
      document.removeEventListener('visibilitychange', visibility)
      locator.current = () => {}
    }
  }, [identity, listMode, levelNumber, currentId, focusId, geometry, storageKey, stops, focusIndex, narrow])
  useEffect(() => {
    if (!locateSignal) return
    if (listMode) document.getElementById(`journey-stop-${focusId}`)?.scrollIntoView({ block: 'center', behavior: 'instant' })
    else locator.current(focusId)
  }, [locateSignal, focusId, listMode])

  return <>
    <div className="wall-view-controls"><span><AcademyIcon name="path" size={18}/>{listMode ? 'Danh sách từ bài đầu đến bài cuối' : 'Cuộn lên để chinh phục · Đường thành dẫn lối'}</span><button type="button" aria-pressed={listMode} onClick={() => { setNotice('');setListMode(!listMode) }}>{listMode ? 'Xem Trường Thành' : 'Xem danh sách'}</button></div>
    {notice && <div className="wall-stop-notice" role="status"><p>{notice}</p><button type="button" aria-label="Đóng hướng dẫn bài học" onClick={() => setNotice('')}>Đóng</button></div>}
    <div ref={scene} className={`wall-camera-scene${listMode ? ' is-list' : ''}`} role="region" aria-label="Đường thành của bạn" style={listMode ? undefined : { height: geometry.height * scale }}>
      <div ref={world} className="wall-camera-world" style={listMode ? undefined : { height: geometry.height, width: WALL_WIDTH, '--wall-inverse-scale': 1 / scale } as CSSProperties}>
        {!listMode && <div className="wall-painted-sections" aria-hidden="true">{Array.from({ length: geometry.sections }, (_, topIndex) => {
          const region = wallRegion(topIndex, geometry.sections)
          const focusTile = Math.floor((geometry.points[focusIndex]?.y ?? 0) / geometry.sectionHeight)
          return <div key={topIndex} className="wall-painted-section" style={{ top: topIndex * geometry.sectionHeight, height: geometry.sectionHeight }}><img src={`/academy/great-wall/continuous-${regionArt[region]}-v1.webp`} width="1024" height="1536" alt="" loading={Math.abs(topIndex - focusTile) <= 1 ? 'eager' : 'lazy'} fetchPriority={topIndex === focusTile ? 'high' : 'auto'}/></div>
        })}</div>}
        <ol className="wall-continuous-stops" aria-label="Các bài trong cấp độ HSK">{stops.map((stop, index) => {
          const current = stop.id === currentId
          const state = stop.planned ? 'planned' : stop.state === 'COMPLETED' ? 'completed' : stop.state === 'LOCKED' ? 'locked' : current ? 'current' : 'available'
          const point = geometry.points[index]
          const milestone = stop.kind === 'lesson' && !!stop.lessonNumber && stop.lessonNumber % 5 === 0
          const content = <><span className="wall-seal" aria-hidden="true"><SealFrame/><span className="wall-seal-content">{stop.state === 'COMPLETED' ? <AcademyIcon name="check" size={30}/> : stop.planned ? <AcademyIcon name="book" size={28}/> : stop.state === 'LOCKED' ? <WallLock/> : stop.kind === 'test' || milestone ? <TowerIcon/> : <AcademyIcon name={stop.kind === 'foundation' ? 'sound' : 'book'} size={28}/>}<span>{stop.shortName}</span></span></span><span role="heading" aria-level={2} className="wall-lesson-name">{lessonTitle(stop)}</span><span className="wall-lesson-status">{stopStatus(stop, current)}</span></>
          return <li key={stop.id} id={`journey-stop-${stop.id}`} className="wall-lesson-stop" data-state={state} data-kind={stop.kind} data-unit-id={stop.id} data-milestone={milestone || undefined} style={listMode ? undefined : { left: point.x, top: point.y }}>
            {current && !listMode && <span className="wall-current-bo" aria-hidden="true"><Companion pose={finished ? 'celebrate' : 'guide'} decorative/></span>}
            {stop.destination ? <Link className="wall-lesson-target" to={stop.destination} aria-current={current && !finished ? 'step' : undefined} aria-label={`${stop.state === 'COMPLETED' ? 'Ôn' : 'Học'} ${stop.name}`} onFocus={() => { if (!listMode && document.activeElement?.matches(':focus-visible')) locator.current(stop.id) }}>{content}</Link> : <button type="button" className="wall-lesson-target" aria-label={`${stop.name}, ${stopStatus(stop, current)}`} aria-disabled="true" onFocus={() => { if (!listMode && document.activeElement?.matches(':focus-visible')) locator.current(stop.id) }} onClick={() => setNotice(stop.planned ? `${stop.shortName} đang được chuẩn bị. Bạn có thể tiếp tục những bài đã mở.` : `${stop.shortName} chưa mở. ${stops.find(item => item.id === currentId)?.kind === 'foundation' ? 'Hoàn thành bài phát âm trước khi bắt đầu HSK 1.' : 'Hoàn thành bài trước và đạt từ 80% phần luyện tập để tiếp tục.'}`)}>{content}</button>}
          </li>
        })}</ol>
      </div>
    </div>
  </>
}
