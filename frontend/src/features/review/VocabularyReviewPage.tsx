import { useEffect, useId, useLayoutEffect, useRef, useState, type PointerEvent } from 'react'
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router'
import { Alert, Button, LoadingState } from '../../components/ui'
import { Companion, VocabularyIllustration } from '../../components/academy/Companion'
import { AcademyIcon } from '../../components/academy/AcademyIcon'
import { getReviewDeck, getReviewLessons } from './api'
import { useFlashcardProgress, type ReviewPosition } from './useFlashcardProgress'
import '../../styles/vocabulary-review.css'

type Selection = { level: number; lessonId: string; title: string }
const deckKey = (level: number, lessonId: string, page: number, seed: string | null) => ['vocabulary-review', level, lessonId, page, seed]
const loadDeck = (level: number, lessonId: string, page: number, seed: string | null) => seed
  ? getReviewDeck(page, level || undefined, lessonId || undefined, seed)
  : getReviewDeck(page, level || undefined, lessonId || undefined)

export function VocabularyReviewPage() {
  const [level, setLevel] = useState(0)
  const [lessonId, setLessonId] = useState('')
  const [selection, setSelection] = useState<Selection | null>(null)
  const startArea = useRef<HTMLDivElement>(null)
  const lessons = useQuery({ queryKey: ['vocabulary-review', 'lessons'], queryFn: getReviewLessons })
  const preview = useQuery({ queryKey: deckKey(level, lessonId, 1, null), queryFn: () => loadDeck(level, lessonId, 1, null), enabled: !selection })
  const availableLessons = (lessons.data ?? []).filter(lesson => !level || lesson.hsk_level === level)
  const total = preview.data?.total ?? 0
  const filtered = Boolean(level || lessonId)
  const selectedLesson = availableLessons.find(lesson => lesson.lesson_id === lessonId)
  const title = selectedLesson ? `HSK ${selectedLesson.hsk_level} · Bài ${selectedLesson.lesson_number}: ${selectedLesson.title}` : level ? `Tất cả bài đã hoàn thành · HSK ${level}` : 'Tất cả bài đã hoàn thành'
  const resetFilters = () => { setLevel(0); setLessonId('') }
  return <section className="learner-page vocabulary-review-page screen" aria-labelledby="page-title">
    <header className="review-heading"><div><h1 id="page-title">Ôn từ vựng</h1><p>{selection ? 'Nhìn chữ, tự nhớ nghĩa, rồi lật thẻ để đối chiếu.' : 'Chọn những bài bạn muốn ôn. Từ các bài đã hoàn thành sẽ xuất hiện ở đây.'}</p></div><Companion pose="but" decorative/></header>
    {selection ? <ReviewSession selection={selection} onExit={() => { setSelection(null); requestAnimationFrame(() => startArea.current?.querySelector('button')?.focus({ preventScroll: true })) }}/>
      : <div className="review-setup">
        <div className="review-filter-panel">
          <h2>Hôm nay bạn muốn ôn bài nào?</h2>
          <div className="review-toolbar">
            <label>Cấp độ HSK<select aria-label="Cấp độ HSK" value={level} onChange={event => { setLevel(Number(event.target.value)); setLessonId('') }}><option value={0}>Tất cả HSK</option>{[1, 2, 3].map(n => <option key={n} value={n}>HSK {n}</option>)}</select></label>
            <label className="review-lesson-filter">Bài học<select aria-label="Bài học" value={lessonId} disabled={!availableLessons.length} onChange={event => setLessonId(event.target.value)}>
              <option value="">{lessons.isPending ? 'Đang tải bài học…' : availableLessons.length ? 'Tất cả bài đã hoàn thành' : 'Chưa có bài đã hoàn thành'}</option>
              {availableLessons.map(lesson => <option key={lesson.lesson_id} value={lesson.lesson_id}>HSK {lesson.hsk_level} · Bài {lesson.lesson_number}: {lesson.title}</option>)}
            </select></label>
          </div>
          <div className="review-filter-summary"><span role="status">{preview.isPending ? 'Đang lấy số thẻ…' : preview.isError ? 'Chưa tải được số thẻ' : <><strong>{total}</strong> thẻ trong bộ ôn</>}</span>{filtered && <Button onClick={resetFilters}>Xóa bộ lọc</Button>}</div>
          <div className="review-setup-start" ref={startArea}><p>Chữ Hán ở mặt trước. Hình ảnh, phiên âm và nghĩa ở mặt sau.</p><Button variant="primary" disabled={!preview.isSuccess || !total || preview.isFetching} onClick={() => setSelection({ level, lessonId, title })}>Bắt đầu ôn<AcademyIcon name="arrow" size={20}/></Button></div>
        </div>
        {lessons.isError && <Alert tone="warning" action={<Button onClick={() => void lessons.refetch()}>Tải lại danh sách bài</Button>}>Chưa tải được bộ lọc bài học. Bạn vẫn có thể ôn từ theo HSK.</Alert>}
        {preview.isError && <Alert tone="error" action={<Button onClick={() => void preview.refetch()}>Thử lại</Button>}>Chưa tải được bộ từ vựng.</Alert>}
        {preview.isSuccess && total === 0 && <div className="review-empty"><h2>{filtered ? 'Chưa có từ trong lựa chọn này' : 'Bắt đầu từ một bài học'}</h2><p>{filtered ? 'Từ vựng xuất hiện sau khi bạn hoàn thành bài học. Thử chọn bài khác hoặc xem tất cả từ đã học.' : 'Hoàn thành lý thuyết và đạt bài luyện tập để mở bộ từ của bài đó. Các nghĩa khác nhau của cùng một chữ được giữ thành thẻ riêng.'}</p>{filtered ? <Button onClick={resetFilters}>Xem tất cả từ đã học</Button> : <Link className="learner-link-action" to="/pronunciation">Về giáo trình</Link>}</div>}
        <KeyboardGuide/>
      </div>}
  </section>
}

function KeyboardGuide() {
  return <div className="review-keyboard-guide" aria-label="Phím tắt ôn tập">
    <span><kbd>↑</kbd><kbd>↓</kbd> Lật thẻ</span><span><kbd>←</kbd> Chưa nhớ</span><span><kbd>→</kbd> Đã nhớ</span>
  </div>
}

function ReviewSession({ selection: { level, lessonId, title }, onExit }: { selection: Selection; onExit: () => void }) {
  const answerId = useId()
  const client = useQueryClient()
  const [page, setPage] = useState(1)
  const [position, setPosition] = useState(0)
  const [revealed, setRevealed] = useState(false)
  const [shuffleSeed, setShuffleSeed] = useState<string | null>(null)
  const [finished, setFinished] = useState(false)
  const [moving, setMoving] = useState(false)
  const [feedback, setFeedback] = useState('')
  const [departure, setDeparture] = useState<'KNOWN' | 'LEARNING' | null>(null)
  const cardElement = useRef<HTMLButtonElement>(null)
  const summaryElement = useRef<HTMLDivElement>(null)
  const animation = useRef<Animation | null>(null)
  const pendingExit = useRef<Promise<void> | null>(null)
  const entrance = useRef<'next' | 'undo' | null>(null)
  const moveLock = useRef(false)
  const direction = useRef<-1 | 1>(1)
  const gesture = useRef<{ x: number; y: number; pointerId: number } | null>(null)
  const suppressFlip = useRef(false)
  const deck = useQuery({ queryKey: deckKey(level, lessonId, page, shuffleSeed), queryFn: () => loadDeck(level, lessonId, page, shuffleSeed), placeholderData: keepPreviousData })
  const cards = deck.data?.items ?? []
  const index = Math.min(position, Math.max(0, cards.length - 1))
  const card = deck.isPlaceholderData ? undefined : cards[index]
  const total = deck.data?.total ?? 0
  const pages = Math.ceil(total / 50)
  const reducedMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
  const change = (index: number) => { setPosition(index); setRevealed(false); setFinished(false); setDeparture(null) }
  const changePage = (number: number) => { setPage(number); change(0) }

  async function leaveCard(undo = false) {
    const element = cardElement.current
    if (!element?.animate) return
    animation.current?.cancel()
    const minimal = reducedMotion()
    const distance = Math.min(element.clientWidth * .4, 260)
    const rise = Math.min(element.clientHeight * .42, 160)
    const drop = Math.min(element.clientHeight * .36, 140)
    const vertical = direction.current === 1 ? -rise : drop
    const frames = minimal ? [{ opacity: 1 }, { opacity: .35 }] : [
      { transform: 'translate3d(0,0,0) rotate(0deg)', opacity: 1 },
      { transform: `translate3d(${undo ? 0 : direction.current * distance}px,${undo ? 12 : vertical}px,0) rotate(${undo ? 0 : direction.current * 9}deg) scale(${undo ? .97 : .96})`, opacity: 0 },
    ]
    const effect = element.animate(frames, { duration: minimal ? 55 : 150, easing: 'cubic-bezier(.22,.7,.45,1)', fill: 'forwards' })
    animation.current = effect
    try { await effect.finished } catch { /* Navigation can cancel a visual transition. */ }
  }
  async function recoverCard() {
    const element = cardElement.current
    if (!element?.animate) return
    const { transform, opacity } = getComputedStyle(element)
    animation.current?.cancel()
    const minimal = reducedMotion()
    const frames = minimal ? [{ opacity }, { opacity: 1 }] : [
      { transform, opacity }, { transform: 'translate3d(0,0,0) rotate(0deg) scale(1)', opacity: 1 },
    ]
    const effect = element.animate(frames, { duration: minimal ? 60 : 160, easing: 'cubic-bezier(.16,1,.3,1)' })
    animation.current = effect
    try { await effect.finished } catch { /* Navigation can cancel recovery. */ }
  }
  async function advance(rated = false) {
    entrance.current = 'next'
    if (rated) setDeparture(direction.current === 1 ? 'KNOWN' : 'LEARNING')
    await (pendingExit.current ?? leaveCard())
    if (index < cards.length - 1) change(index + 1)
    else if (page < pages) changePage(page + 1)
    else { setFinished(true); setRevealed(false); setDeparture(null) }
  }
  const progress = useFlashcardProgress(level, lessonId, () => advance(true), async (saved: ReviewPosition) => {
    entrance.current = 'undo'
    await leaveCard(true)
    setPage(saved.page); setPosition(saved.index); setRevealed(true); setFinished(false); setDeparture(null); setFeedback('Đã hoàn tác đánh giá')
  })
  const busy = progress.busy || moving
  const canInteract = Boolean(card) && !finished && !busy && !deck.isFetching
  const currentRating = progress.query.data?.cards.find(state => state.card_id === card?.id)?.status

  useLayoutEffect(() => {
    if (finished) { summaryElement.current?.focus({ preventScroll: true }); return }
    const element = cardElement.current
    if (!element) return
    animation.current?.cancel()
    element.focus({ preventScroll: true })
    if (entrance.current && element.animate) {
      const minimal = reducedMotion()
      const frames = minimal ? [{ opacity: .4 }, { opacity: 1 }] : [
        { transform: entrance.current === 'undo' ? 'translate3d(-48px,0,0) rotate(-2deg)' : 'translate3d(0,16px,0) scale(.975)', opacity: .45 },
        { transform: 'translate3d(0,0,0) rotate(0deg) scale(1)', opacity: 1 },
      ]
      animation.current = element.animate(frames, { duration: minimal ? 65 : 180, easing: 'cubic-bezier(.16,1,.3,1)' })
    }
    entrance.current = null
  }, [card?.id, page, finished])
  useEffect(() => () => { animation.current?.cancel() }, [])
  useEffect(() => {
    if (!busy && !finished && document.activeElement === document.body) cardElement.current?.focus({ preventScroll: true })
  }, [busy, finished, card?.id, page])
  useEffect(() => {
    if (index >= cards.length - 3 && page < pages && !deck.isPlaceholderData) {
      void client.prefetchQuery({ queryKey: deckKey(level, lessonId, page + 1, shuffleSeed), queryFn: () => loadDeck(level, lessonId, page + 1, shuffleSeed) })
    }
  }, [index, cards.length, page, pages, deck.isPlaceholderData, client, level, lessonId, shuffleSeed])

  async function move(value: -1 | 1) {
    if (!canInteract || !progress.ready || moveLock.current || !card) return
    moveLock.current = true
    setMoving(true)
    direction.current = value
    try {
      if (progress.enabled) {
        setDeparture(value === 1 ? 'KNOWN' : 'LEARNING')
        pendingExit.current = leaveCard()
        const saved = await progress.rate(card.id, value === 1 ? 'KNOWN' : 'LEARNING', { page, index })
        if (saved) setFeedback(`${value === 1 ? 'Đã nhớ' : 'Chưa nhớ'}: ${card.hanzi}`)
        else await recoverCard()
      } else {
        if (value === -1 && index === 0 && page === 1) return
        setMoving(true)
        if (value === 1) await advance()
        else {
          entrance.current = 'undo'
          await leaveCard(true)
          if (index > 0) change(index - 1)
          else { setPage(page - 1); change(49) }
        }
        setFeedback('')
      }
    } finally { pendingExit.current = null; moveLock.current = false; setMoving(false); setDeparture(null) }
  }
  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || !['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key) || finished || (!card && !deck.isFetching)) return
      if (event.target instanceof Element && (event.target.closest('select,input,textarea,[contenteditable=true]') || (event.target !== document.body && !event.target.closest('.review-card-session')))) return
      event.preventDefault()
      if (event.repeat || !canInteract) return
      if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') void move(event.key === 'ArrowRight' ? 1 : -1)
      else setRevealed(value => !value)
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  })
  const endGesture = (event: PointerEvent<HTMLButtonElement>) => {
    const start = gesture.current
    gesture.current = null
    if (!start || start.pointerId !== event.pointerId) return
    const dx = event.clientX - start.x, dy = event.clientY - start.y
    if (Math.abs(dx) < 64 || Math.abs(dx) < Math.abs(dy) * 1.5) return
    suppressFlip.current = true
    window.setTimeout(() => { suppressFlip.current = false }, 0)
    void move(dx > 0 ? 1 : -1)
  }
  const restart = () => { progress.clearHistory(); setFeedback(''); entrance.current = 'next'; changePage(1) }
  const toggleShuffle = () => { progress.clearHistory(); setFeedback(''); setShuffleSeed(seed => seed ? null : crypto.randomUUID()); entrance.current = 'next'; changePage(1) }

  if (deck.isSuccess && !deck.isPlaceholderData && total === 0) return <div className="review-empty"><h2>Bộ thẻ chưa có từ khả dụng</h2><p>Chọn lại bài học để tiếp tục ôn.</p><Button onClick={onExit}>Đổi bài ôn</Button></div>

  return <div className="review-card-session">
    <div className="review-session-heading"><p>{title}</p><Button disabled={busy} onClick={onExit}>Đổi bài ôn</Button></div>
    {deck.isError && <Alert tone="error" action={<Button onClick={() => void deck.refetch()}>Thử lại</Button>}>Chưa tải được bộ từ vựng.</Alert>}
    <div className="review-card-toolbar"><div className="review-position" role="status">{finished ? 'Kết thúc lượt ôn' : `Thẻ ${(page - 1) * 50 + index + 1} / ${total}`}</div><p className="review-flip-hint"><AcademyIcon name="history" size={18}/>{finished ? 'Mỗi lượt ôn giúp bạn nhớ lâu hơn' : 'Bấm vào thẻ để lật'}</p></div>
    {progress.enabled && progress.query.data && <div className="review-tracking-summary" aria-label="Tiến độ ôn tập">
      <p><span>Đã nhớ <strong>{progress.query.data.known}</strong></span><span>Chưa nhớ <strong>{progress.query.data.learning}</strong></span><span>Chưa ôn <strong>{progress.query.data.unseen}</strong></span></p>
      <progress aria-label="Số từ đã nhớ" max={progress.query.data.total || 1} value={progress.query.data.known}/>
    </div>}
    <div className="review-card-stage">
      {finished ? <div className="review-round-end" role="region" aria-labelledby="review-round-title" tabIndex={-1} ref={summaryElement}>
        <Companion pose="but-happy" decorative/><h2 id="review-round-title">Bạn đã đi hết bộ thẻ!</h2>
        <p>{progress.enabled ? 'Xem lại tiến độ ở trên và tiếp tục ôn để ghi nhớ vững hơn.' : 'Bạn đã xem hết các thẻ trong lựa chọn này.'}</p>
        <Button variant="primary" disabled={busy} onClick={restart}>Học lại bộ thẻ</Button>
      </div> : card ? <button ref={cardElement} key={`${page}:${card.id}`} className="review-flashcard" type="button" data-flipped={revealed} data-departure={departure} disabled={busy} aria-pressed={revealed} aria-describedby={revealed ? answerId : undefined} aria-label={revealed ? 'Lật về mặt chữ Hán' : `Lật thẻ ${card.hanzi} để xem phiên âm và nghĩa`}
        onPointerDown={event => { if (event.button !== 0 || !canInteract) return; gesture.current = { x: event.clientX, y: event.clientY, pointerId: event.pointerId }; event.currentTarget.setPointerCapture?.(event.pointerId) }}
        onPointerUp={endGesture} onPointerCancel={() => { gesture.current = null }}
        onClick={() => { if (!suppressFlip.current) setRevealed(value => !value) }}>
        <span className="review-flashcard__rotor">
          <span className="review-flashcard__face review-flashcard__face--front" aria-hidden={revealed} inert={revealed}><strong lang="zh-Hans">{card.hanzi}</strong></span>
          <span className="review-flashcard__face review-flashcard__face--back" aria-hidden={!revealed} inert={!revealed}>
            <span className="review-flashcard__back-content"><span className="review-flashcard__art" aria-hidden="true"><VocabularyIllustration hanzi={card.hanzi} partOfSpeech={card.part_of_speech} inline/></span>
              <span id={answerId} className="review-flashcard__answer"><span className="review-flashcard__pinyin" lang="zh-Latn-pinyin">{card.pinyin}</span>{' '}<span>{card.vietnamese_meaning}</span></span>
            </span>
          </span>
        </span>
        <span className="review-departure-mark" aria-hidden="true"><AcademyIcon name={departure === 'KNOWN' ? 'check' : 'close'} size={24}/>{departure === 'KNOWN' ? 'Đã nhớ' : 'Chưa nhớ'}</span>
      </button> : <div className="review-card-loading"><LoadingState>Đang lấy thẻ…</LoadingState></div>}
    </div>
    <div className="review-actions" role="group" aria-label="Điều khiển ôn tập" aria-busy={busy}>
      <button className="review-track-toggle" type="button" role="switch" aria-checked={progress.enabled} disabled={!progress.ready || busy} onClick={() => void progress.toggle()}><span>Theo dõi tiến độ</span><span className="review-switch-track" aria-hidden="true"><span/></span></button>
      {progress.enabled && !finished && <div className="review-rating-actions">
        <button className="review-rate review-rate--learning" type="button" disabled={!progress.ready || !canInteract} aria-pressed={currentRating === 'LEARNING'} onClick={() => void move(-1)}><AcademyIcon name="close" size={22}/>Chưa nhớ<kbd aria-hidden="true">←</kbd></button>
        <button className="review-rate review-rate--known" type="button" disabled={!progress.ready || !canInteract} aria-pressed={currentRating === 'KNOWN'} onClick={() => void move(1)}><AcademyIcon name="check" size={22}/>Đã nhớ<kbd aria-hidden="true">→</kbd></button>
      </div>}
      {!progress.enabled && !finished && <div className="review-browse-actions" role="group" aria-label="Xem thẻ không ghi đánh giá">
        <button className="review-tool-button review-tool-button--previous" type="button" aria-label="Thẻ trước" disabled={!canInteract || !progress.ready || (index === 0 && page === 1)} onClick={() => void move(-1)}><AcademyIcon name="arrow" size={22}/></button>
        <button className="review-tool-button" type="button" aria-label="Thẻ kế" disabled={!canInteract || !progress.ready} onClick={() => void move(1)}><AcademyIcon name="arrow" size={22}/></button>
      </div>}
      <div className="review-session-tools">
        <button className="review-tool-button" type="button" aria-label="Hoàn tác đánh giá vừa rồi" title="Hoàn tác đánh giá vừa rồi" disabled={!progress.canUndo || busy || deck.isFetching} onClick={() => void progress.undo()}><AcademyIcon name="undo" size={22}/></button>
        <button className="review-tool-button" type="button" aria-label={shuffleSeed ? 'Tắt trộn thẻ' : 'Trộn thẻ'} title={shuffleSeed ? 'Tắt trộn thẻ' : 'Trộn thẻ'} aria-pressed={!!shuffleSeed} disabled={busy || deck.isFetching || total < 2} onClick={toggleShuffle}><AcademyIcon name="shuffle" size={22}/></button>
      </div>
    </div>
    <p className="review-action-status review-feedback" role="status">{progress.error ? '' : progress.busy ? 'Đang lưu tiến độ…' : feedback}</p>
    {progress.query.isPending && <p className="review-action-status" role="status">Đang tải tiến độ ôn tập…</p>}
    {progress.query.isError && <Alert tone="warning" action={<Button onClick={() => void progress.query.refetch()}>Tải lại tiến độ</Button>}>Chưa tải được tiến độ ôn tập. Bạn vẫn có thể lật thẻ.</Alert>}
    {progress.error && <Alert tone="error">{progress.error}</Alert>}
    {!finished && (progress.enabled ? <KeyboardGuide/> : <p className="review-gesture-hint">Đang tắt theo dõi: vuốt hoặc dùng phím ← / → để xem thẻ, không ghi đánh giá. Phím ↑ / ↓ để lật.</p>)}
    {!finished && progress.enabled && <p className="review-gesture-hint review-touch-hint">Trên điện thoại: chạm để lật · vuốt trái: chưa nhớ · vuốt phải: đã nhớ.</p>}
    {revealed && !finished && card?.lessons.some(lesson => lesson.note) && <aside className="review-usage"><h2>Lưu ý khi dùng</h2>{[...new Set(card.lessons.flatMap(lesson => lesson.note ? [lesson.note] : []))].map(note => <p key={note}>{note}</p>)}</aside>}
    {!finished && card && <p className="review-origin">Từ bài đã hoàn thành: {card.lessons.map(lesson => `HSK ${lesson.hsk_level} · Bài ${lesson.lesson_number}`).join(', ')}</p>}
  </div>
}
