import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, Navigate, useLocation, useParams } from 'react-router'
import { queryKeys } from '../../app/query/keys'
import { getHskLevels } from '../curriculum/api'
import { getLessonProgress } from '../progress/api'
import { markGrammarViewed, getLesson } from './api'
import { ExerciseSection } from './ExerciseSection'
import { LessonHeader } from './LessonHeader'
import { GrammarSection } from './TheorySections'
import { ReadingSection } from './ReadingSection'
import { Alert, Button, EmptyState, LoadingState, PageHeader } from '../../components/ui'
import { VocabularyStudy } from './VocabularyStudy'
import { vocabularyPath } from './vocabularyRoutes'
import { legacyLessonParts, lessonPartPath, type LessonPart } from './lessonRoutes'
import { useLessonStudyPosition } from './useLessonStudyPosition'

export function LessonPage({ part = 'vocabulary' }: { part?: LessonPart }) {
  const { lessonId, vocabularyId } = useParams()
  const { hash } = useLocation()
  const queryClient = useQueryClient()
  const [grammarExpanded, setGrammarExpanded] = useState<Record<string, boolean>>({})
  const [actionErrors, setActionErrors] = useState<Record<string, string | undefined>>({})
  const grammarPendingIds = useRef(new Set<string>())
  const [grammarPending, setGrammarPending] = useState<Record<string, boolean>>({})
  const lessonQuery = useQuery({ queryKey: queryKeys.lesson(lessonId ?? ''), queryFn: () => getLesson(lessonId!), enabled: !!lessonId })
  const progressQuery = useQuery({ queryKey: queryKeys.lessonProgress(lessonId ?? ''), queryFn: () => getLessonProgress(lessonId!), enabled: !!lessonQuery.data })
  const levelsQuery = useQuery({ queryKey: queryKeys.curriculumLevels, queryFn: getHskLevels, enabled: !!lessonQuery.data })
  const lesson = lessonQuery.data
  const progress = progressQuery.data
  const hskLevel = levelsQuery.data?.find((item) => item.id === lesson?.hsk_level_id)
  const hskLabel = hskLevel ? hskLevel.title ?? `HSK ${hskLevel.level_number}` : null
  const grammarViewed = Object.fromEntries(progress?.grammar.map((row) => [row.id, row.viewed]) ?? [])
  const words = [...(lesson?.vocabulary ?? [])].sort((a, b) => a.order_index - b.order_index)
  const wordIndex = vocabularyId ? words.findIndex(word => word.id === vocabularyId) : 0
  const theoryReady = Boolean(progress?.theory_completed_at) && (lesson?.readings ?? []).every(reading => (progress?.readings ?? []).some(row => row.id === reading.id && row.completed))
  const root = useLessonStudyPosition(Boolean(lesson?.id && progress?.lesson_id), `${lessonId}:${part}:${vocabularyId ?? ''}`)
  const sectionCounts = {
    vocabulary: `${progress?.vocabulary.filter(row => row.viewed).length ?? 0}/${words.length}`,
    grammar: `${progress?.grammar.filter(row => row.viewed).length ?? 0}/${lesson?.grammar.length ?? 0}`,
    readings: `${progress?.readings?.filter(row => row.completed).length ?? 0}/${lesson?.readings?.length ?? 0}`,
    practice: progress?.completed_at ? 'Đã đạt' : theoryReady ? 'Đã mở' : 'Chưa mở',
  }

  const grammarMutation = useMutation({
    mutationFn: (linkId: string) => markGrammarViewed(lessonId!, linkId),
    onSuccess: async () => Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.lessonProgress(lessonId ?? '') }),
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard }),
      queryClient.invalidateQueries({ queryKey: queryKeys.progressOverview }),
      queryClient.invalidateQueries({ queryKey: queryKeys.curriculumLevels }),
      queryClient.invalidateQueries({ queryKey: queryKeys.curriculumHsk(lesson?.hsk_level_id ?? '') }),
      queryClient.invalidateQueries({ queryKey: queryKeys.curriculumHskRoot }),
      queryClient.invalidateQueries({ queryKey: queryKeys.progressHsk(lesson?.hsk_level_id ?? '') }),
      queryClient.invalidateQueries({ queryKey: queryKeys.progressHskRoot }),
    ]),
  })

  const onGrammarToggle = (linkId: string, wasOpen: boolean) => {
    setGrammarExpanded((current) => ({ ...current, [linkId]: !wasOpen }))
    if (wasOpen || grammarViewed[linkId] || grammarPendingIds.current.has(linkId) || !lessonId) return
    grammarPendingIds.current.add(linkId)
    setGrammarPending((current) => ({ ...current, [linkId]: true }))
    setActionErrors((current) => ({ ...current, [`g:${linkId}`]: undefined }))
    void grammarMutation.mutateAsync(linkId)
      .catch(() => setActionErrors((current) => ({ ...current, [`g:${linkId}`]: "Không thể lưu trạng thái đã xem hoặc cập nhật tiến độ. Hãy đóng rồi mở lại nội dung để thử lại." })))
      .finally(() => {
        grammarPendingIds.current.delete(linkId)
        setGrammarPending((current) => { const { [linkId]: _, ...remaining } = current; return remaining })
      })
  }

  if (!lessonId) return <section className="learner-page lesson-page lesson-manuscript screen" aria-labelledby="page-title"><PageHeader title="Bài học" titleId="page-title" /><Alert role="alert" tone="error">Không tìm thấy bài học.</Alert></section>
  if (legacyLessonParts[hash]) return <Navigate replace to={lessonPartPath(lessonId, legacyLessonParts[hash])}/>
  if (lessonQuery.isPending || (lesson && progressQuery.isPending)) return <section className="learner-page lesson-page lesson-manuscript screen" aria-labelledby="page-title"><PageHeader title="Bài học" titleId="page-title" /><LoadingState>Đang tải bài học…</LoadingState></section>
  if ((lessonQuery.isError && !lesson) || (progressQuery.isError && !progress) || !lesson || !progress) return <section className="learner-page lesson-page lesson-manuscript screen" aria-labelledby="page-title"><PageHeader title="Bài học" titleId="page-title" />
    <Alert role="alert" tone="error" action={<Button variant="secondary" onClick={() => void (lessonQuery.isError ? lessonQuery.refetch() : progressQuery.refetch())}>Thử lại</Button>}>Không thể tải nội dung bài học.</Alert></section>

  return <section ref={root} className="learner-page lesson-page lesson-manuscript lesson-part-page screen lesson-study-workspace" data-lesson-part={part} aria-labelledby="page-title">
    {(lessonQuery.isError || progressQuery.isError) && <Alert role="status" tone="warning">Chưa cập nhật được bài học. Đang hiển thị thông tin đã tải.</Alert>}
    <LessonHeader lesson={lesson} progress={progress} hskLabel={hskLabel} refreshing={lessonQuery.isFetching || progressQuery.isFetching} />
    <div className="lesson-manuscript__body">
      <nav className="lesson-sequence-nav lesson-manuscript__index" aria-label="Các phần của bài học">
        {([['vocabulary', '生词', 'Từ vựng'], ['grammar', '语法', 'Ngữ pháp'], ['readings', '课文', 'Bài khóa'], ['practice', '练习', 'Luyện tập']] as const).map(([key, hanzi, label]) => <Link key={key} to={lessonPartPath(lesson.id, key)} aria-label={label} aria-current={part === key ? 'page' : undefined}><span lang="zh-Hans" aria-hidden="true">{hanzi}</span><span>{label}<small>{sectionCounts[key]}</small></span></Link>)}
      </nav>
      <div id="lesson-study-content" className="lesson-manuscript__chapters">
        {part === 'vocabulary' && (vocabularyId && wordIndex < 0 ? <Alert role="alert" tone="error">Không tìm thấy từ vựng này trong bài học. Hãy chọn Từ vựng để học lại từ đầu.</Alert> : words.length ? <VocabularyStudy key={`${lesson.id}:${words[wordIndex].id}`} lesson={lesson} progress={progress} words={words} index={wordIndex}/> : <section className="lesson-section"><h2>Từ vựng</h2><EmptyState title="Chưa có từ vựng">Bài học này chưa có từ vựng.</EmptyState><Link className="learner-link-action" to={lessonPartPath(lesson.id, 'grammar')}>Tiếp: Ngữ pháp</Link></section>)}
        {part === 'grammar' && <><GrammarSection items={lesson.grammar} viewed={grammarViewed} expanded={grammarExpanded}
          pending={grammarPending}
          errors={Object.fromEntries(lesson.grammar.map((item) => [item.id, actionErrors[`g:${item.id}`]]))} onToggle={onGrammarToggle} /><nav className="lesson-part-navigation" aria-label="Chuyển phần học"><Link to={words.length ? vocabularyPath(lesson.id, words.at(-1)!.id) : lessonPartPath(lesson.id, 'vocabulary')}>← Từ vựng</Link><Link className="learner-link-action" to={lessonPartPath(lesson.id, 'readings')}>Tiếp: Bài khóa</Link></nav></>}
        {part === 'readings' && <><ReadingSection key={lesson.id} lessonId={lesson.id} readings={lesson.readings ?? []} completedIds={new Set((progress.readings ?? []).filter(row => row.completed).map(row => row.id))}/><nav className="lesson-part-navigation" aria-label="Chuyển phần học"><Link to={lessonPartPath(lesson.id, 'grammar')}>← Ngữ pháp</Link><Link className="learner-link-action" to={lessonPartPath(lesson.id, 'practice')}>Đến luyện tập</Link></nav></>}
        {part === 'practice' && <ExerciseSection assessmentIds={lesson.assessment_ids} theoryCompleted={theoryReady} />}
      </div>
    </div>
  </section>
}
