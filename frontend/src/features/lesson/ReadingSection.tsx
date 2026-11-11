import { useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Alert, Button, EmptyState, StatusBadge, Surface } from '../../components/ui'
import { SectionIcon } from '../../components/academy/AcademyArtwork'
import { queryKeys } from '../../app/query/keys'
import { ApiError } from '../../lib/api/errors'
import { completeLessonReading } from './api'
import { ReadingText, type LessonReading } from './ReadingText'

export function ReadingSection({ lessonId, readings, completedIds }: { lessonId: string; readings: LessonReading[]; completedIds: Set<string> }) {
  const client = useQueryClient()
  const pendingIds = useRef(new Set<string>())
  const [pending, setPending] = useState<Record<string, boolean>>({})
  const [errors, setErrors] = useState<Record<string, string>>({})
  const mutation = useMutation({ mutationFn: (reading: LessonReading) => completeLessonReading(lessonId, reading.id, reading.version), retry: false })
  const complete = async (reading: LessonReading) => {
    if (pendingIds.current.has(reading.id) || completedIds.has(reading.id)) return
    pendingIds.current.add(reading.id)
    setPending(current => ({ ...current, [reading.id]: true }))
    setErrors(current => ({ ...current, [reading.id]: '' }))
    try {
      await mutation.mutateAsync(reading)
      await Promise.all([
        queryKeys.lessonProgress(lessonId), queryKeys.dashboard, queryKeys.progressOverview,
        queryKeys.curriculumLevels, queryKeys.curriculumHskRoot, queryKeys.progressHskRoot,
      ].map(queryKey => client.invalidateQueries({ queryKey })))
    } catch (error) {
      const changed = error instanceof ApiError && error.code === 'READING_VERSION_CHANGED'
      setErrors(current => ({ ...current, [reading.id]: changed ? 'Bài khóa vừa được cập nhật. Hãy đọc lại nội dung mới rồi bấm hoàn thành.' : 'Chưa thể lưu trạng thái hoàn thành. Vui lòng thử lại.' }))
      if (changed) await Promise.all([client.invalidateQueries({ queryKey: queryKeys.lesson(lessonId) }), client.invalidateQueries({ queryKey: queryKeys.lessonProgress(lessonId) })])
    } finally {
      pendingIds.current.delete(reading.id)
      setPending(current => ({ ...current, [reading.id]: false }))
    }
  }
  return <section className="lesson-section lesson-reading-section" id="readings" aria-labelledby="readings-title">
    <div className="lesson-section__heading"><div><SectionIcon kind="library"/><h2 id="readings-title">Bài khóa <span lang="zh-Hans" className="academy-section-chinese" aria-hidden="true">课文</span></h2></div><span className="lesson-section__eyebrow">{completedIds.size} / {readings.length} đã hoàn thành</span></div>
    {readings.length === 0 ? <EmptyState title="Chưa có bài khóa">Bài học này chưa có bài khóa cần hoàn thành.</EmptyState> : <>
      <p className="lesson-reading-intro">Đọc từng bài khóa, sau đó bấm hoàn thành để lưu tiến độ của bạn.</p>
      <div className="lesson-reading-list">{readings.map(reading => {
        const done = completedIds.has(reading.id)
        return <Surface as="article" className="learner-surface lesson-reading-card" key={reading.id} aria-labelledby={'reading-' + reading.id}>
          <div className="lesson-reading-card__heading"><h3 id={'reading-' + reading.id}>{reading.title}</h3><StatusBadge tone={done ? 'success' : 'neutral'}>{done ? 'Đã hoàn thành' : 'Chưa hoàn thành'}</StatusBadge></div>
          <ReadingText reading={reading}/>
          {errors[reading.id] && <Alert role="alert" tone="error">{errors[reading.id]}</Alert>}
          <div className="lesson-reading-card__actions"><Button variant={done ? 'secondary' : 'primary'} disabled={done || pending[reading.id]} aria-label={done ? `Đã hoàn thành bài khóa: ${reading.title}` : `Hoàn thành bài khóa: ${reading.title}`} onClick={() => void complete(reading)}>{pending[reading.id] ? 'Đang lưu…' : done ? 'Đã hoàn thành' : 'Hoàn thành bài khóa'}</Button></div>
        </Surface>
      })}</div>
    </>}
  </section>
}
