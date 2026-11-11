import { useEffect, useRef } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { queryKeys } from '../../app/query/keys'
import { AcademyIcon } from '../../components/academy/AcademyIcon'
import { Alert, Button } from '../../components/ui'
import { markVocabularyViewed } from './api'
import { VocabularyStudyCard } from './VocabularyStudyCard'
import { vocabularyPath } from './vocabularyRoutes'
import { lessonPartPath } from './lessonRoutes'
import type { components } from '../../types/api.generated'

type Lesson = components['schemas']['LessonResponse']
type Progress = components['schemas']['LessonProgressResponse']

export function VocabularyStudy({ lesson, progress, words, index }: { lesson: Lesson; progress: Progress; words: Lesson['vocabulary']; index: number }) {
  const client = useQueryClient()
  const navigate = useNavigate()
  const entry = words[index]
  const requested = useRef(false)
  const savedOnServer = progress.vocabulary.some(row => row.id === entry.id && row.viewed)
  const mark = useMutation({
    mutationFn: async () => {
      const result = await markVocabularyViewed(lesson.id, entry.id)
      if (!result?.viewed_at) throw new Error('VIEW_NOT_CONFIRMED')
      return result
    },
    retry: false,
    onSuccess: () => {
      client.setQueryData<Progress>(queryKeys.lessonProgress(lesson.id), current => current ? {
        ...current,
        vocabulary: current.vocabulary.map(row => row.id === entry.id ? { ...row, viewed: true } : row),
      } : current)
      void Promise.all([queryKeys.lessonProgress(lesson.id), queryKeys.dashboard, queryKeys.progressOverview, queryKeys.curriculumLevels, queryKeys.curriculumHskRoot, queryKeys.progressHskRoot].map(queryKey => client.invalidateQueries({ queryKey })))
    },
  })
  const { mutate } = mark
  useEffect(() => {
    if (savedOnServer) return
    const recordView = () => {
      if (document.visibilityState === 'hidden' || requested.current) return
      requested.current = true
      mutate()
    }
    recordView()
    document.addEventListener('visibilitychange', recordView)
    return () => document.removeEventListener('visibilitychange', recordView)
  }, [savedOnServer, mutate])
  const viewed = savedOnServer || mark.isSuccess
  const viewedCount = words.filter(word => word.id === entry.id ? viewed : progress.vocabulary.some(row => row.id === word.id && row.viewed)).length
  const last = index === words.length - 1
  return <section className="vocabulary-page" aria-labelledby="vocabulary-title">
    <div className="lesson-part-heading"><h2 id="vocabulary-title">Từ vựng</h2><div className="vocabulary-page__progress"><span>{viewedCount} / {words.length} từ đã xem</span></div></div>
    <VocabularyStudyCard word={entry.item} example={entry.example} note={entry.note} collapsibleWriting/>
    {mark.isError && !viewed && <Alert role="alert" tone="error" action={<Button onClick={() => mutate()}>Thử lưu lại</Button>}>Chưa thể lưu từ đang xem. Hãy thử lại trước khi chuyển sang từ tiếp theo.</Alert>}
    <nav className="vocabulary-page__navigation" aria-label="Chuyển từ vựng">
      <Button variant="secondary" disabled={index === 0} onClick={() => void navigate(vocabularyPath(lesson.id, words[index - 1].id))}><AcademyIcon name="arrow" size={18}/>Quay lại</Button>
      <span className="vocabulary-page__position">Từ {index + 1} / {words.length}<small role="status">{mark.isPending ? 'Đang lưu…' : viewed ? 'Đã xem' : 'Chưa lưu'}</small></span>
      <Button variant="primary" title={last ? 'Chuyển sang ngữ pháp' : undefined} disabled={!viewed || mark.isPending} onClick={() => void navigate(last ? lessonPartPath(lesson.id, 'grammar') : vocabularyPath(lesson.id, words[index + 1].id))}>Tiếp theo<AcademyIcon name="arrow" size={18}/></Button>
    </nav>
  </section>
}
