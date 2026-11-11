import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from 'react'
import { useLocation, useNavigate } from 'react-router'
import { JourneyCloudContext, type CloudTravel } from './journeyCloudContext'
import { CLOUD_ENTER_MS, CLOUD_HOLD_MS, CLOUD_EXIT_MS } from './journeyCloudTiming'
const reduced = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false

export function JourneyCloudProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate(), location = useLocation()
  const [phase, setPhase] = useState<'idle' | 'cover' | 'reveal'>('idle')
  const busy = useRef(false), timers = useRef<ReturnType<typeof setTimeout>[]>([]), generation = useRef(0)
  const cancelDeparture = useRef<(() => void) | undefined>(undefined)
  const destination = useRef<string | null>(null), navigationStarted = useRef(false)
  const previous = useRef(location.pathname)
  const schedule = useCallback((callback: () => void, ms: number) => {
    const id = setTimeout(() => { timers.current = timers.current.filter(timer => timer !== id);callback() }, ms)
    timers.current.push(id);return id
  }, [])
  const clear = useCallback(() => { timers.current.forEach(clearTimeout);timers.current = [];generation.current++;busy.current = false;destination.current = null;navigationStarted.current = false }, [])
  const cancel = useCallback(() => {
    clear();cancelDeparture.current?.();cancelDeparture.current = undefined;setPhase('idle')
  }, [clear])
  const reveal = useCallback(() => {
    setPhase('reveal')
    schedule(() => { setPhase('idle');busy.current = false }, reduced() ? 80 : CLOUD_EXIT_MS)
  }, [schedule])
  const travel = useCallback<CloudTravel>((trip) => {
    if (busy.current) return false
    busy.current = true
    destination.current = trip.destination;navigationStarted.current = false
    cancelDeparture.current = trip.cancelled
    const token = ++generation.current
    trip.depart?.()
    const coverAt = reduced() ? 0 : trip.coverDelay ?? (trip.returning ? 0 : trip.short ? 130 : 280)
    schedule(() => setPhase('cover'), coverAt)
    const navigateAt = coverAt + (reduced() ? 30 : CLOUD_ENTER_MS)
    schedule(() => {
      if (generation.current !== token) return
      const waitForData = trip.prepare ? Promise.race([trip.prepare.catch(() => undefined), new Promise(resolve => schedule(() => resolve(undefined), 1100))]) : Promise.resolve()
      void waitForData.then(async () => {
        if (generation.current !== token) return
        if (trip.relocate) trip.relocate()
        else {
          navigationStarted.current = true
          await navigate(trip.destination)
        }
        if (generation.current !== token) return
        schedule(reveal, reduced() ? 40 : CLOUD_HOLD_MS)
      }).catch(() => { if (generation.current === token) reveal() })
    }, navigateAt)
    schedule(() => {
      if (generation.current !== token || !busy.current) return
      const handedToRouter=navigationStarted.current,cancelPendingDeparture=cancelDeparture.current
      clear();cancelDeparture.current = undefined
      if(!handedToRouter)cancelPendingDeparture?.()
      reveal()
    }, navigateAt + 2600)
    return true
  }, [navigate, reveal, schedule, clear])
  useLayoutEffect(() => {
    const previousPath = previous.current
    const fromLesson = /^(?:\/(?:lessons|assessments)\/|\/pronunciation\/lesson(?:\/|$)|\/measure-words\/?$)/.test(previousPath)
    const toJourney = /^\/(hsk\/\d+|pronunciation)\/?$/.test(location.pathname)
    previous.current = location.pathname
    if (previousPath !== location.pathname && busy.current) {
      const targetPath=destination.current?.split(/[?#]/,1)[0]
      const expected = navigationStarted.current && targetPath && (location.pathname === targetPath || location.pathname.startsWith(targetPath + '/'))
      if (!expected) { cancel();return }
      // The destination is committed. A slow scene may still keep the veil
      // busy; its watchdog must not undo the previous page's arrival marker.
      cancelDeparture.current = undefined
    }
    if (fromLesson && toJourney && !busy.current) {
      clear()
      busy.current = true;destination.current = location.pathname;setPhase('cover');schedule(reveal, reduced() ? 40 : CLOUD_ENTER_MS+CLOUD_HOLD_MS)
    }
  }, [location.pathname, reveal, schedule, cancel, clear])
  useEffect(() => clear, [clear])
  useEffect(() => {
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape' && busy.current) cancel() }
    window.addEventListener('keydown', escape);return () => window.removeEventListener('keydown', escape)
  }, [cancel])
  const value = useMemo(() => ({ travel, cancel }), [travel, cancel])
  return <JourneyCloudContext value={value}>{children}<div className="journey-cloud-transition" data-phase={phase} style={{'--journey-cloud-enter':`${CLOUD_ENTER_MS}ms`,'--journey-cloud-exit':`${CLOUD_EXIT_MS}ms`} as CSSProperties} aria-hidden="true"><div className="journey-cloud-curtain journey-cloud-curtain--left"/><div className="journey-cloud-curtain journey-cloud-curtain--right"/></div></JourneyCloudContext>
}
