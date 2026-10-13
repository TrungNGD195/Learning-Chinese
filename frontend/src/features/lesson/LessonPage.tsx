import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router'
import { queryKeys } from '../../app/query/keys'
import { getHskLevels } from '../curriculum/api'
import { getLessonProgress } from '../progress/api'
import { markGrammarViewed, markVocabularyViewed, getLesson } from './api'
import { ExerciseSection } from './ExerciseSection'
import { LessonHeader } from './LessonHeader'
import { GrammarSection, VocabularySection } from './TheorySections'
import { LessonChatRegion } from '../conversation/LessonChatRegion'

export function LessonPage() {
  const { lessonId } = useParams()
  const queryClient = useQueryClient()
  const [vocabularyExpanded, setVocabularyExpanded] = useState<Record<string, boolean>>({})
  const [grammarExpanded, setGrammarExpanded] = useState<Record<string, boolean>>({})
  const [actionErrors, setActionErrors] = useState<Record<string, string | undefined>>({})
  const vocabularyPendingIds = useRef(new Set<string>())
  const grammarPendingIds = useRef(new Set<string>())
  const [vocabularyPending, setVocabularyPending] = useState<Record<string, boolean>>({})
  const [grammarPending, setGrammarPending] = useState<Record<string, boolean>>({})
  const lessonQuery = useQuery({ queryKey: queryKeys.lesson(lessonId ?? ''), queryFn: () => getLesson(lessonId!), enabled: !!lessonId })
  const progressQuery = useQuery({ queryKey: queryKeys.lessonProgress(lessonId ?? ''), queryFn: () => getLessonProgress(lessonId!), enabled: !!lessonQuery.data })
  const levelsQuery = useQuery({ queryKey: queryKeys.curriculumLevels, queryFn: getHskLevels, enabled: !!lessonQuery.data })
  const lesson = lessonQuery.data
  const progress = progressQuery.data
  const hskLevel = levelsQuery.data?.find((item) => item.id === lesson?.hsk_level_id)
  const hskLabel = hskLevel ? hskLevel.title ?? `HSK ${hskLevel.level_number}` : null
  const vocabularyViewed = Object.fromEntries(progress?.vocabulary.map((row) => [row.id, row.viewed]) ?? [])
  const grammarViewed = Object.fromEntries(progress?.grammar.map((row) => [row.id, row.viewed]) ?? [])

  const vocabularyMutation = useMutation({
    mutationFn: (linkId: string) => markVocabularyViewed(lessonId!, linkId),
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

  const onVocabularyToggle = (linkId: string, wasOpen: boolean) => {
    setVocabularyExpanded((current) => ({ ...current, [linkId]: !wasOpen }))
    if (wasOpen || vocabularyViewed[linkId] || vocabularyPendingIds.current.has(linkId) || !lessonId) return
    vocabularyPendingIds.current.add(linkId)
    setVocabularyPending((current) => ({ ...current, [linkId]: true }))
    setActionErrors((current) => ({ ...current, [`v:${linkId}`]: undefined }))
    void vocabularyMutation.mutateAsync(linkId)
      .catch(() => setActionErrors((current) => ({ ...current, [`v:${linkId}`]: 'Could not save viewed state or refresh progress. Close and open the item to try again.' })))
      .finally(() => {
        vocabularyPendingIds.current.delete(linkId)
        setVocabularyPending((current) => { const { [linkId]: _, ...remaining } = current; return remaining })
      })
  }
  const onGrammarToggle = (linkId: string, wasOpen: boolean) => {
    setGrammarExpanded((current) => ({ ...current, [linkId]: !wasOpen }))
    if (wasOpen || grammarViewed[linkId] || grammarPendingIds.current.has(linkId) || !lessonId) return
    grammarPendingIds.current.add(linkId)
    setGrammarPending((current) => ({ ...current, [linkId]: true }))
    setActionErrors((current) => ({ ...current, [`g:${linkId}`]: undefined }))
    void grammarMutation.mutateAsync(linkId)
      .catch(() => setActionErrors((current) => ({ ...current, [`g:${linkId}`]: 'Could not save viewed state or refresh progress. Close and open the item to try again.' })))
      .finally(() => {
        grammarPendingIds.current.delete(linkId)
        setGrammarPending((current) => { const { [linkId]: _, ...remaining } = current; return remaining })
      })
  }

  if (!lessonId) return <section className="screen"><h1 id="page-title">Lesson</h1><p role="alert">Lesson was not found.</p></section>
  if (lessonQuery.isPending || (lesson && progressQuery.isPending)) return <section className="screen"><h1 id="page-title">Lesson</h1><p role="status">Loading lesson…</p></section>
  if ((lessonQuery.isError && !lesson) || (progressQuery.isError && !progress) || !lesson || !progress) return <section className="screen"><h1 id="page-title">Lesson</h1><p role="alert">Could not load lesson content.</p>
    <button className="secondary-action" type="button" onClick={() => void (lessonQuery.isError ? lessonQuery.refetch() : progressQuery.refetch())}>Retry</button></section>

  return <section className="screen lesson-screen" aria-labelledby="page-title">
    {(lessonQuery.isFetching || progressQuery.isFetching) && <p role="status">Refreshing lesson…</p>}
    {(lessonQuery.isError || progressQuery.isError) && <p role="status">Could not refresh lesson information. Showing the last loaded information.</p>}
    <LessonHeader lesson={lesson} progress={progress} hskLabel={hskLabel} />
    <VocabularySection items={lesson.vocabulary} viewed={vocabularyViewed} expanded={vocabularyExpanded}
      pending={vocabularyPending}
      errors={Object.fromEntries(lesson.vocabulary.map((item) => [item.id, actionErrors[`v:${item.id}`]]))} onToggle={onVocabularyToggle} />
    <GrammarSection items={lesson.grammar} viewed={grammarViewed} expanded={grammarExpanded}
      pending={grammarPending}
      errors={Object.fromEntries(lesson.grammar.map((item) => [item.id, actionErrors[`g:${item.id}`]]))} onToggle={onGrammarToggle} />
    <ExerciseSection assessmentIds={lesson.assessment_ids} />
    <LessonChatRegion lessonId={lesson.id} lessonNumber={lesson.lesson_number} hskLabel={hskLabel} />
  </section>
}
