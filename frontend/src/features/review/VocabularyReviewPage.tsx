import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { Alert, Button, LoadingState } from '../../components/ui'
import { Companion } from '../../components/academy/Companion'
import { getReviewDeck, getReviewLessons } from './api'
import '../../styles/vocabulary-review.css'

export function VocabularyReviewPage() {
  const [level, setLevel] = useState(0)
  const [lessonId, setLessonId] = useState('')
  const [page, setPage] = useState(1)
  const [position, setPosition] = useState(0)
  const [revealed, setRevealed] = useState(false)
  const lessons = useQuery({ queryKey: ['vocabulary-review', 'lessons'], queryFn: getReviewLessons })
  const deck = useQuery({ queryKey: ['vocabulary-review', level, lessonId, page], queryFn: () => getReviewDeck(page, level || undefined, lessonId || undefined) })
  const availableLessons = (lessons.data ?? []).filter(lesson => !level || lesson.hsk_level === level)
  const cards = deck.data?.items ?? []
  const index = Math.min(position, Math.max(0, cards.length - 1))
  const card = cards[index]
  const change = (index: number) => { setPosition(index); setRevealed(false) }
  const changePage = (number: number) => { setPage(number); change(0) }
  const total = deck.data?.total ?? 0
  const pages = Math.ceil(total / 50)
  const filtered = Boolean(level || lessonId)
  const resetFilters = () => { setLevel(0); setLessonId(''); changePage(1) }
  return <section className="learner-page vocabulary-review-page screen" aria-labelledby="page-title">
    <header className="review-heading"><div><h1 id="page-title">Ôn từ vựng</h1><p>Từ các bài bạn đã hoàn thành sẽ tự xuất hiện ở đây.</p></div><Companion pose="but" decorative/></header>
    <div className="review-filter-panel">
      <div className="review-toolbar">
        <label>Cấp độ HSK<select aria-label="Cấp độ HSK" value={level} onChange={event => { setLevel(Number(event.target.value)); setLessonId(''); changePage(1) }}><option value={0}>Tất cả HSK</option>{[1, 2, 3].map(n => <option key={n} value={n}>HSK {n}</option>)}</select></label>
        <label className="review-lesson-filter">Bài học<select aria-label="Bài học" value={lessonId} disabled={!availableLessons.length} onChange={event => { setLessonId(event.target.value); changePage(1) }}>
          <option value="">{lessons.isPending ? 'Đang tải bài học…' : availableLessons.length ? 'Tất cả bài đã hoàn thành' : 'Chưa có bài đã hoàn thành'}</option>
          {availableLessons.map(lesson => <option key={lesson.lesson_id} value={lesson.lesson_id}>HSK {lesson.hsk_level} · Bài {lesson.lesson_number}: {lesson.title}</option>)}
        </select></label>
      </div>
      <div className="review-filter-summary"><span role="status">{deck.isPending ? 'Đang lấy bộ thẻ…' : deck.isError ? 'Chưa tải được số thẻ' : <><strong>{total}</strong> thẻ ôn tập</>}</span>{filtered ? <Button onClick={resetFilters}>Xóa bộ lọc</Button> : <span>Chọn một bài để ôn tập trung hơn.</span>}</div>
    </div>
    {lessons.isError && <Alert tone="warning" action={<Button onClick={() => void lessons.refetch()}>Tải lại danh sách bài</Button>}>Chưa tải được bộ lọc bài học. Bạn vẫn có thể ôn từ theo HSK.</Alert>}
    {deck.isPending && <LoadingState>Đang lấy từ đã học…</LoadingState>}
    {deck.isError && <Alert tone="error" action={<Button onClick={() => void deck.refetch()}>Thử lại</Button>}>Chưa tải được bộ từ vựng.</Alert>}
    {deck.isSuccess && total === 0 && <div className="review-empty"><Companion pose="guide" decorative/><h2>{filtered ? 'Chưa có từ trong lựa chọn này' : 'Bắt đầu từ một bài học'}</h2><p>{filtered ? 'Từ vựng chỉ xuất hiện sau khi bạn hoàn thành bài học. Thử chọn một bài khác hoặc xem tất cả từ đã học.' : 'Hoàn thành lý thuyết và đạt bài luyện tập để mở bộ từ của bài đó. Các nghĩa khác nhau của cùng một chữ được giữ thành thẻ riêng.'}</p>{filtered ? <Button onClick={resetFilters}>Xem tất cả từ đã học</Button> : <Link className="learner-link-action" to="/pronunciation">Về giáo trình</Link>}</div>}
    {card && <>
      <div className="review-position" role="status">Thẻ {(page - 1) * 50 + index + 1} / {total}</div>
      <button className="review-flashcard" type="button" aria-expanded={revealed} aria-label={revealed ? `Ẩn phiên âm và nghĩa của ${card.hanzi}` : `Lật thẻ ${card.hanzi} để xem phiên âm và nghĩa`} onClick={() => setRevealed(value => !value)}>
        <strong lang="zh-Hans">{card.hanzi}</strong>
        {revealed ? <span className="review-flashcard__answer"><span className="review-flashcard__pinyin">{card.pinyin}</span>{card.part_of_speech && <small>{card.part_of_speech}</small>}<span>{card.vietnamese_meaning}</span></span> : <span className="review-flashcard__hint">Thử nhớ cách đọc và nghĩa, rồi chạm để lật thẻ</span>}
        <span className="review-flashcard__action">{revealed ? 'Ẩn đáp án' : 'Xem phiên âm và nghĩa'}</span>
      </button>
      {revealed && card.lessons.some(lesson => lesson.note) && <aside className="review-usage"><h2>Lưu ý khi dùng</h2>{[...new Set(card.lessons.flatMap(lesson => lesson.note ? [lesson.note] : []))].map(note => <p key={note}>{note}</p>)}</aside>}
      <nav className="review-navigation" aria-label="Chuyển thẻ"><Button disabled={index === 0 && page === 1} onClick={() => { if (index) change(index - 1); else { setPage(page - 1); change(49) } }}>← Quay lại</Button><Button variant="primary" disabled={index === cards.length - 1 && page >= pages} onClick={() => index < cards.length - 1 ? change(index + 1) : changePage(page + 1)}>Tiếp theo →</Button></nav>
      <p className="review-origin">Từ bài đã hoàn thành: {card.lessons.map(lesson => `HSK ${lesson.hsk_level} · Bài ${lesson.lesson_number}`).join(', ')}</p>
      {pages > 1 && <nav className="review-batches" aria-label="Chọn bộ thẻ"><Button disabled={page <= 1} onClick={() => changePage(page - 1)}>Bộ trước</Button><span>Bộ {page} / {pages} · tối đa 50 thẻ mỗi bộ</span><Button disabled={page >= pages} onClick={() => changePage(page + 1)}>Bộ sau</Button></nav>}
    </>}
  </section>
}
