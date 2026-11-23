import { useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError } from '../../lib/api/errors'
import { getReviewProgress, setReviewPreference, setReviewState, type ReviewRating } from './api'

export type ReviewPosition = { page: number; index: number }
type UndoEntry = ReviewPosition & { cardId: string; before: ReviewRating; expectedVersion: number }
type Progress = Awaited<ReturnType<typeof getReviewProgress>>
const root = ['vocabulary-review', 'progress'] as const

export function useFlashcardProgress(level: number, lessonId: string, advance: () => void | Promise<void>, restore: (position: ReviewPosition) => void | Promise<void>) {
  const client = useQueryClient()
  const key = [...root, level, lessonId]
  const query = useQuery({ queryKey: key, queryFn: () => getReviewProgress(level || undefined, lessonId || undefined) })
  const [history, setHistory] = useState<UndoEntry[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const writing = useRef(false)
  const enabled = query.data?.tracking_enabled === true
  const ready = query.isSuccess && !query.isError && !busy

  async function run(operation: () => Promise<void>) {
    if (writing.current) return
    writing.current = true
    setBusy(true)
    setError(null)
    try { await operation(); return true }
    catch (failure) {
      if (failure instanceof ApiError && ['REVIEW_VERSION_CONFLICT', 'REVIEW_TRACKING_DISABLED'].includes(failure.code)) {
        setHistory([])
        setError('Tiến độ đã thay đổi ở phiên khác. Đã tải lại; hãy kiểm tra rồi thử lại.')
      } else setError('Chưa xác nhận được thay đổi. Hãy kiểm tra kết nối rồi thử lại.')
      // Reconcile uncertain writes, without retrying a mutation or fabricating an undo entry.
      await client.invalidateQueries({ queryKey: root })
      return false
    } finally { writing.current = false; setBusy(false) }
  }

  function apply(row: Awaited<ReturnType<typeof setReviewState>>) {
    client.setQueryData<Progress>(key, previous => {
      if (!previous) return previous
      const old = previous.cards.find(card => card.card_id === row.card_id)?.status ?? null
      const known = previous.known + Number(row.status === 'KNOWN') - Number(old === 'KNOWN')
      const learning = previous.learning + Number(row.status === 'LEARNING') - Number(old === 'LEARNING')
      return { ...previous, known, learning, unseen: previous.total-known-learning,
        cards: [...previous.cards.filter(card => card.card_id !== row.card_id), row] }
    })
  }

  function rate(cardId: string, status: Exclude<ReviewRating, null>, position: ReviewPosition) {
    if (!ready || !enabled) return
    const previous = query.data?.cards.find(card => card.card_id === cardId)
    return run(async () => {
      const saved = await setReviewState(cardId, status, previous?.version ?? 0)
      apply(saved)
      setHistory(current => [...current.slice(-199), { ...position, cardId, before: previous?.status ?? null, expectedVersion: saved.version }])
      // The write receipt is authoritative for this card. Refresh other views when
      // revisited instead of putting a second round trip in every card transition.
      void client.invalidateQueries({ queryKey: root, refetchType: 'none' })
      await advance()
    })
  }

  function undo() {
    const entry = history.at(-1)
    if (!entry || !ready || !enabled) return
    return run(async () => {
      const saved = await setReviewState(entry.cardId, entry.before, entry.expectedVersion)
      apply(saved)
      setHistory(current => {
        const remaining = current.slice(0, -1)
        // An undo is itself a new revision; earlier actions on this card must follow it.
        for (let i = remaining.length-1; i >= 0; i--) if (remaining[i].cardId === entry.cardId) {
          remaining[i] = { ...remaining[i], expectedVersion: saved.version }; break
        }
        return remaining
      })
      void client.invalidateQueries({ queryKey: root, refetchType: 'none' })
      await restore(entry)
    })
  }

  function toggle() {
    if (!ready) return
    return run(async () => {
      const saved = await setReviewPreference(!enabled)
      client.setQueriesData<Progress>({ queryKey: root }, previous => previous ? { ...previous, ...saved } : previous)
      await client.invalidateQueries({ queryKey: root })
    })
  }

  return { query, enabled, ready, busy, error, rate, undo, toggle,
    canUndo: ready && enabled && history.length > 0,
    clearHistory: () => { setHistory([]); setError(null) },
  }
}
