import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { Alert, Button, LoadingState } from '../../components/ui'
import { Companion } from '../../components/academy/Companion'
import { getReviewDeck } from './api'
import '../../styles/vocabulary-review.css'

export function VocabularyReviewPage() {
  const [level, setLevel] = useState(0)
  const [page, setPage] = useState(1)
  const [position, setPosition] = useState(0)
  const [revealed, setRevealed] = useState(false)
  const deck = useQuery({ queryKey: ['vocabulary-review', level, page], queryFn: () => getReviewDeck(page, level || undefined) })
  const cards = deck.data?.items ?? []
  const index = Math.min(position, Math.max(0, cards.length - 1))
  const card = cards[index]
  const change = (index: number) => { setPosition(index); setRevealed(false) }
  const changePage = (number: number) => { setPage(number); change(0) }
  const total = deck.data?.total ?? 0
  const pages = Math.ceil(total / 50)
  return <section className="learner-page vocabulary-review-page screen" aria-labelledby="page-title">
    <header className="review-heading"><div><h1 id="page-title">Ôn từ vựng</h1><p>Từ các bài bạn đã hoàn thành sẽ tự xuất hiện ở đây.</p></div><Companion pose="but" decorative/></header>
    <div className="review-toolbar"><label>Cấp độ <select value={level} onChange={event => { setLevel(Number(event.target.value)); changePage(1) }}><option value={0}>Tất cả HSK</option>{[1, 2, 3].map(n => <option key={n} value={n}>HSK {n}</option>)}</select></label><span>{total} thẻ ôn tập</span></div>
    {deck.isPending && <LoadingState>Đang lấy từ đã học…</LoadingState>}
    {deck.isError && <Alert tone="error" action={<Button onClick={() => void deck.refetch()}>Thử lại</Button>}>Chưa tải được bộ từ vựng.</Alert>}
    {deck.isSuccess && total === 0 && <div className="review-empty"><Companion pose="guide" decorative/><h2>Bắt đầu từ một bài học</h2><p>Hoàn thành lý thuyết và đạt bài luyện tập để mở bộ từ của lesson đó. Các nghĩa khác nhau của cùng một chữ được giữ thành thẻ riêng.</p><Link className="learner-link-action" to="/pronunciation">Về giáo trình</Link></div>}
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
