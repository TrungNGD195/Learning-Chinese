import { useEffect, useId, useRef, useState, useSyncExternalStore } from 'react'
import { AcademyIcon } from '../academy/AcademyIcon'
import { hanziCharacters, loadStrokeData, type StrokeData } from './strokeData'

const motionQuery = '(prefers-reduced-motion: reduce)'
const subscribeMotion = (callback: () => void) => {
  if (typeof window.matchMedia !== 'function') return () => {}
  const query = window.matchMedia(motionQuery)
  query.addEventListener('change', callback)
  return () => query.removeEventListener('change', callback)
}
const getMotionPreference = () => typeof window.matchMedia === 'function' && window.matchMedia(motionQuery).matches

export function StrokeOrder({ hanzi }: { hanzi: string }) {
  return <StrokeWord key={hanzi} hanzi={hanzi}/>
}

function StrokeWord({ hanzi }: { hanzi: string }) {
  const characters = hanziCharacters(hanzi)
  const [selected, setSelected] = useState(0)
  if (!characters.length) return null
  return <div className="hanzi-stroke-word" aria-label={'Tập viết ' + hanzi}>
    {characters.length > 1 && <div className="hanzi-character-tabs" role="group" aria-label="Chọn chữ để xem thứ tự nét">{characters.map((character, index) => <button type="button" key={index} lang="zh-Hans" aria-pressed={selected === index} aria-label={`Chữ ${character}, vị trí ${index + 1}`} onClick={() => setSelected(index)}>{character}</button>)}</div>}
    <StrokePlayer key={selected} character={characters[selected]}/>
  </div>
}

function StrokePlayer({ character }: { character: string }) {
  const root = useRef<HTMLDivElement>(null)
  const trace = useRef<SVGPathElement>(null)
  const animation = useRef<Animation | null>(null)
  const [visible, setVisible] = useState(() => !('IntersectionObserver' in window))
  const [entered, setEntered] = useState(() => !('IntersectionObserver' in window))
  const [data, setData] = useState<StrokeData | null>(null)
  const [error, setError] = useState('')
  const [request, setRequest] = useState(0)
  const [stroke, setStroke] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [run, setRun] = useState(0)
  const [speed, setSpeed] = useState(1)
  const reduced = useSyncExternalStore(subscribeMotion, getMotionPreference, () => true)
  const animationSupported = typeof Element.prototype.animate === 'function'
  const maskId = 'stroke-' + useId().replace(/[^a-zA-Z0-9-]/g, '')

  useEffect(() => {
    const element = root.current
    if (!element) return
    if (!('IntersectionObserver' in window)) return
    const observer = new IntersectionObserver(entries => {
      // Fast scrolling can queue several transitions for this one target.
      const entry = entries.at(-1)
      if (!entry) return
      setVisible(entry.isIntersecting)
      if (entry.isIntersecting) setEntered(true)
    }, { threshold: 0.15 })
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    if (!entered) return
    let current = true
    loadStrokeData(character).then(value => {
      if (!current) return
      setData(value); setError(''); setPlaying(!getMotionPreference() && typeof Element.prototype.animate === 'function')
    }).catch(reason => { if (current) setError(reason instanceof Error && reason.message === 'UNSUPPORTED_CHARACTER' ? 'missing' : 'network') })
    return () => { current = false }
  }, [character, entered, request])

  useEffect(() => {
    if (!data || stroke >= data.strokes.length || !trace.current || typeof trace.current.animate !== 'function') return
    const player = trace.current.animate([{ strokeDashoffset: 1 }, { strokeDashoffset: 0 }], { duration: 1000 / speed, fill: 'both', easing: 'linear' })
    player.pause()
    animation.current = player
    player.onfinish = () => {
      setStroke(index => index + 1)
      if (stroke + 1 >= data.strokes.length) setPlaying(false)
    }
    return () => { player.onfinish = null; player.cancel(); if (animation.current === player) animation.current = null }
  }, [data, stroke, run, speed])

  useEffect(() => {
    if (playing && visible && !reduced) animation.current?.play()
    else animation.current?.pause()
  }, [playing, visible, reduced, stroke, run, speed, data])

  const total = data?.strokes.length ?? 0
  const complete = total > 0 && stroke === total
  const progress = data?.medians[stroke]
  const path = progress?.map(([x, y], index) => (index ? 'L' : 'M') + x + ' ' + y).join(' ')
  const restart = () => { setStroke(0); setRun(value => value + 1); setPlaying(!reduced) }
  const next = () => { setPlaying(false); setStroke(value => Math.min(total, value + 1)) }
  const toggle = () => { if (complete) restart(); else setPlaying(value => !value) }

  return <div ref={root} className="hanzi-stroke-player" data-character={character} data-written-strokes={stroke} data-total-strokes={total}>
    <svg className="hanzi-writing-square" viewBox="0 0 1024 1024" role="img" aria-label={`Thứ tự nét chữ ${character}${total ? `, đã viết ${stroke} trên ${total} nét` : ''}`}>
      <g className="hanzi-writing-guides" aria-hidden="true"><path d="M0 0L1024 1024M1024 0L0 1024M512 0V1024M0 512H1024"/></g>
      {data ? <g transform="translate(64 852) scale(.875 -.875)" aria-hidden="true">
        <g className="hanzi-stroke-outline">{data.strokes.map((outline, index) => <path key={index} d={outline}/>)}</g>
        {data.strokes.slice(0, stroke).map((outline, index) => <path key={index} className={index === stroke - 1 && !playing ? 'hanzi-stroke-active' : 'hanzi-stroke-ink'} d={outline}/>)}
        {path && <><defs><mask id={maskId} maskUnits="userSpaceOnUse" x="-128" y="-128" width="1280" height="1280"><path key={stroke + '-' + run} ref={trace} d={path} fill="none" stroke="#fff" strokeWidth="160" strokeLinecap="round" strokeLinejoin="round" pathLength={1} strokeDasharray="1 1" strokeDashoffset="1"/></mask></defs><path className="hanzi-stroke-active" d={data.strokes[stroke]} mask={`url(#${maskId})`}/></>}
      </g> : <text className="hanzi-writing-fallback" x="512" y="520" textAnchor="middle" dominantBaseline="central" lang="zh-Hans">{character}</text>}
    </svg>
    {data ? <>
      <div className="hanzi-stroke-status"><span>{complete ? 'Đã viết đủ' : 'Đã viết'} {stroke} / {total} nét</span><label>Tốc độ<select aria-label={'Tốc độ viết chữ ' + character} value={speed} onChange={event => { setSpeed(Number(event.target.value)); setPlaying(false) }}><option value={0.65}>Chậm</option><option value={1}>Vừa</option><option value={1.6}>Nhanh</option></select></label></div>
      <div className="hanzi-stroke-controls">
        {!reduced && animationSupported && <button type="button" className="hanzi-stroke-play" aria-label={`${playing ? 'Tạm dừng' : complete ? 'Viết lại' : 'Viết từng nét'} chữ ${character}`} onClick={toggle}>{playing ? <svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true"><path d="M6 4V16M14 4V16" stroke="currentColor" strokeWidth="2"/></svg> : <svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true"><path d="m6 3 10 7-10 7Z" fill="currentColor"/></svg>}{playing ? 'Tạm dừng' : complete ? 'Viết lại' : 'Xem cách viết'}</button>}
        <button type="button" aria-label={'Nét trước của chữ ' + character} disabled={stroke === 0} onClick={() => { setPlaying(false); setStroke(value => Math.max(0, value - 1)) }}>Nét trước</button>
        <button type="button" aria-label={'Nét tiếp theo của chữ ' + character} disabled={complete} onClick={next}>Nét tiếp</button>
        <button type="button" aria-label={'Bắt đầu lại chữ ' + character} title="Bắt đầu lại" onClick={restart}><AcademyIcon name="history" size={17}/></button>
      </div>
      {(reduced || !animationSupported) && <p className="hanzi-stroke-hint">Dùng “Nét tiếp” để xem từng bước không có chuyển động tự động.</p>}
    </> : error ? <div className="hanzi-stroke-hint" role="status">{error === 'missing' ? 'Chưa có dữ liệu thứ tự nét cho chữ này.' : <>Chưa tải được thứ tự nét. <button type="button" onClick={() => { setError(''); setRequest(value => value + 1) }}>Thử lại</button></>}</div> : entered ? <p className="hanzi-stroke-hint" role="status">Đang tải thứ tự nét…</p> : null}
  </div>
}
