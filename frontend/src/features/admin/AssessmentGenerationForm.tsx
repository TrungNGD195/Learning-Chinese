import { useMemo, useState } from 'react'
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { queryKeys } from '../../app/query/keys'
import type { components } from '../../types/api.generated'
import { ApiError } from '../../lib/api/errors'
import { adminErrorText } from './AdminPrimitives'
import {
  generateAssessmentDraft, listAdminLessons, listHskLevels,
  listLessonGrammar, listLessonVocabulary,
  type AssessmentGenerationRequest,
} from './api'
import { invalidateAssessmentList } from './invalidation'

type GenerationKind = AssessmentGenerationRequest['type']
type QuestionType = components['schemas']['LessonExerciseGenerationRequest']['allowed_types'][number]
type Difficulty = components['schemas']['LessonExerciseGenerationRequest']['difficulty']
type LessonChoice = Awaited<ReturnType<typeof listAdminLessons>>['items'][number]
type VocabularyChoice = Awaited<ReturnType<typeof listLessonVocabulary>>[number]
type GrammarChoice = Awaited<ReturnType<typeof listLessonGrammar>>[number]

const questionTypeOptions = [
  ['multiple_choice', 'Multiple Choice'],
  ['fill_blank', 'Fill in the Blank'],
  ['matching', 'Matching'],
  ['reorder_sentence', 'Reorder Sentence'],
  ['translate_vi_zh', 'Translate Vietnamese → Chinese'],
  ['translate_zh_vi', 'Translate Chinese → Vietnamese'],
  ['sentence_writing', 'Sentence Writing'],
] as const satisfies readonly (readonly [QuestionType, string])[]

function generationErrorText(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case 'INVALID_REQUEST': return 'Check the generation settings and try again.'
      case 'INVALID_GENERATION_SCOPE': return 'Review the selected Lessons, Vocabulary, and Grammar, then try again.'
      case 'AI_GENERATION_INPUT_TOO_LARGE': return 'The selected generation scope is too large. Reduce the selected Lessons or content items.'
      case 'AI_GENERATION_INVALID_OUTPUT': return 'AI generation returned an invalid result. Review the settings and explicitly retry.'
      case 'AI_GENERATION_UNAVAILABLE': return 'AI generation is temporarily unavailable. You can explicitly retry.'
      case 'AI_GENERATION_PERSISTENCE_FAILED': return 'The generated draft could not be saved. No draft was created; you can explicitly retry.'
      default: return adminErrorText(error, 'Could not generate the assessment draft.')
    }
  }
  return adminErrorText(error, 'Could not generate the assessment draft.')
}

function lessonLabel(lesson: LessonChoice, levelNumber?: number) {
  return `HSK ${levelNumber ?? '—'} · Lesson ${lesson.lesson_number} · ${lesson.title}`
}

export function AssessmentGenerationForm() {
  const client = useQueryClient()
  const navigate = useNavigate()
  const [generationKind, setGenerationKind] = useState<GenerationKind>('LESSON_EXERCISE')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [passThreshold, setPassThreshold] = useState('90')
  const [questionCount, setQuestionCount] = useState('1')
  const [difficulty, setDifficulty] = useState<Difficulty | ''>('')
  const [allowedTypes, setAllowedTypes] = useState<QuestionType[]>(['multiple_choice'])
  const [lessonId, setLessonId] = useState('')
  const [selectedLessonIds, setSelectedLessonIds] = useState<string[]>([])
  const [selectedLessons, setSelectedLessons] = useState<Record<string, LessonChoice>>({})
  const [selectedVocabularyIds, setSelectedVocabularyIds] = useState<string[]>([])
  const [selectedGrammarIds, setSelectedGrammarIds] = useState<string[]>([])
  const [lessonPage, setLessonPage] = useState(1)
  const [hskFilter, setHskFilter] = useState('')

  const hskQuery = useQuery({ queryKey: queryKeys.adminHskLevels, queryFn: listHskLevels })
  const lessonFilters = { page: lessonPage, page_size: 50, ...(hskFilter ? { hsk_level_id: hskFilter } : {}) }
  const lessonsQuery = useQuery({
    queryKey: queryKeys.adminLessons(lessonFilters),
    queryFn: () => listAdminLessons(lessonFilters),
  })
  const discoveryLessonIds = useMemo(
    () => generationKind === 'PERIODIC_TEST' ? selectedLessonIds : [],
    [generationKind, selectedLessonIds],
  )
  const vocabularyQueries = useQueries({ queries: discoveryLessonIds.map((id) => ({
    queryKey: queryKeys.adminLessonVocabulary(id), queryFn: () => listLessonVocabulary(id),
  })) })
  const grammarQueries = useQueries({ queries: discoveryLessonIds.map((id) => ({
    queryKey: queryKeys.adminLessonGrammar(id), queryFn: () => listLessonGrammar(id),
  })) })

  const discoveredVocabulary = useMemo(() => {
    const items = new Map<string, { item: VocabularyChoice; lessonIds: string[] }>()
    vocabularyQueries.forEach((query, index) => {
      const lesson = discoveryLessonIds[index]
      for (const item of query.data ?? []) {
        const canonicalId = item.vocabulary_id
        if (!canonicalId) continue
        const existing = items.get(canonicalId)
        if (existing) existing.lessonIds.push(lesson)
        else items.set(canonicalId, { item, lessonIds: [lesson] })
      }
    })
    return items
  }, [discoveryLessonIds, vocabularyQueries])

  const discoveredGrammar = useMemo(() => {
    const items = new Map<string, { item: GrammarChoice; lessonIds: string[] }>()
    grammarQueries.forEach((query, index) => {
      const lesson = discoveryLessonIds[index]
      for (const item of query.data ?? []) {
        const canonicalId = item.grammar_id
        if (!canonicalId) continue
        const existing = items.get(canonicalId)
        if (existing) existing.lessonIds.push(lesson)
        else items.set(canonicalId, { item, lessonIds: [lesson] })
      }
    })
    return items
  }, [discoveryLessonIds, grammarQueries])

  const discoveryQueries = [...vocabularyQueries, ...grammarQueries]
  const discoveryLoading = discoveryQueries.some((query) => query.isPending || query.isFetching)
  const discoveryFailed = discoveryQueries.some((query) => query.isError)
  const thresholdValue = Number(passThreshold)
  const countValue = Number(questionCount)
  const validCommon = Number.isInteger(thresholdValue) && thresholdValue >= 0 && thresholdValue <= 100
    && Number.isInteger(countValue) && countValue >= 1 && countValue <= 10
    && difficulty !== '' && allowedTypes.length > 0
  const mutation = useMutation({
    mutationFn: (request: AssessmentGenerationRequest) => generateAssessmentDraft(request),
    retry: false,
    onSuccess: async (result) => {
      await invalidateAssessmentList(client)
      await navigate(`/admin/assessments/${encodeURIComponent(result.assessment.id)}`)
    },
  })
  const validScope = generationKind === 'LESSON_EXERCISE'
    ? Boolean(!lessonsQuery.isPending && !lessonsQuery.isError && lessonId
      && lessonsQuery.data?.items.some((lesson) => lesson.id === lessonId && lesson.status !== 'ARCHIVED'))
    : selectedLessonIds.length > 0 && !lessonsQuery.isPending && !lessonsQuery.isError
      && !discoveryLoading && !discoveryFailed
      && (selectedVocabularyIds.some((id) => discoveredVocabulary.has(id))
        || selectedGrammarIds.some((id) => discoveredGrammar.has(id)))
  const canGenerate = validCommon && validScope && !mutation.isPending

  const currentLessons = (lessonsQuery.data?.items ?? []).filter((lesson) => lesson.status !== 'ARCHIVED')
  const levelNumberFor = (lesson: LessonChoice) => hskQuery.data?.find((level) => level.id === lesson.hsk_level_id)?.level_number

  function toggleQuestionType(value: QuestionType) {
    setAllowedTypes((current) => current.includes(value) ? current.filter((item) => item !== value) : [...current, value])
  }

  function togglePeriodicLesson(lesson: LessonChoice) {
    const removing = selectedLessonIds.includes(lesson.id)
    const nextIds = removing ? selectedLessonIds.filter((id) => id !== lesson.id) : [...selectedLessonIds, lesson.id]
    setSelectedLessonIds(nextIds)
    setSelectedLessons((current) => {
      const next = { ...current }
      if (removing) delete next[lesson.id]
      else next[lesson.id] = lesson
      return next
    })
    if (removing) {
      const remainingVocabulary = new Set<string>()
      const remainingGrammar = new Set<string>()
      vocabularyQueries.forEach((query, index) => {
        if (!nextIds.includes(discoveryLessonIds[index])) return
        for (const item of query.data ?? []) if (item.vocabulary_id) remainingVocabulary.add(item.vocabulary_id)
      })
      grammarQueries.forEach((query, index) => {
        if (!nextIds.includes(discoveryLessonIds[index])) return
        for (const item of query.data ?? []) if (item.grammar_id) remainingGrammar.add(item.grammar_id)
      })
      setSelectedVocabularyIds((current) => current.filter((id) => remainingVocabulary.has(id)))
      setSelectedGrammarIds((current) => current.filter((id) => remainingGrammar.has(id)))
    }
  }

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canGenerate) return
    const common = {
      ...(title.trim() ? { title: title.trim() } : {}),
      ...(description.trim() ? { description: description.trim() } : {}),
      pass_threshold: thresholdValue,
      question_count: countValue,
      allowed_types: allowedTypes,
      difficulty: difficulty as Difficulty,
    }
    const request: AssessmentGenerationRequest = generationKind === 'LESSON_EXERCISE'
      ? { type: 'LESSON_EXERCISE', lesson_id: lessonId, ...common }
      : {
        type: 'PERIODIC_TEST',
        lesson_ids: selectedLessonIds,
        vocabulary_ids: selectedVocabularyIds.filter((id) => discoveredVocabulary.has(id)),
        grammar_ids: selectedGrammarIds.filter((id) => discoveredGrammar.has(id)),
        ...common,
      }
    mutation.mutate(request)
  }

  return <form className="learning-card" onSubmit={submit} aria-labelledby="generate-assessment-title">
    <h2 id="generate-assessment-title">Generate AI Draft</h2>
    <p>Generated assessments are saved as drafts for Admin review.</p>
    <div className="admin-edit-fields">
      <label>Assessment type<select value={generationKind} disabled={mutation.isPending} onChange={(event) => setGenerationKind(event.target.value as GenerationKind)}>
        <option value="LESSON_EXERCISE">Lesson Exercise</option><option value="PERIODIC_TEST">Periodic Test</option>
      </select></label>
      <label>Title (optional)<input value={title} disabled={mutation.isPending} onChange={(event) => setTitle(event.target.value)} /></label>
      <label>Description (optional)<textarea value={description} disabled={mutation.isPending} onChange={(event) => setDescription(event.target.value)} /></label>
      <label>Pass threshold<input type="number" min="0" max="100" step="1" value={passThreshold} disabled={mutation.isPending} onChange={(event) => setPassThreshold(event.target.value)} /></label>
      <label>Question count<input type="number" min="1" max="10" step="1" value={questionCount} disabled={mutation.isPending} onChange={(event) => setQuestionCount(event.target.value)} /></label>
      <label>Difficulty<select required value={difficulty} disabled={mutation.isPending} onChange={(event) => setDifficulty(event.target.value as Difficulty | '')}>
        <option value="">Select difficulty</option><option value="EASY">Easy</option><option value="MEDIUM">Medium</option><option value="HARD">Hard</option>
      </select></label>
      <fieldset disabled={mutation.isPending}>
        <legend>Allowed question types</legend>
        {questionTypeOptions.map(([value, label]) => <label key={value}>
          <input type="checkbox" checked={allowedTypes.includes(value)} onChange={() => toggleQuestionType(value)} />{label}
        </label>)}
      </fieldset>

      {generationKind === 'LESSON_EXERCISE' ? <section aria-label="Lesson generation scope">
        <h3>Lesson scope</h3>
        <label>Filter lessons by HSK<select value={hskFilter} disabled={mutation.isPending} onChange={(event) => { setHskFilter(event.target.value); setLessonPage(1) }}>
          <option value="">All HSK levels</option>{(hskQuery.data ?? []).map((level) => <option key={level.id} value={level.id}>HSK {level.level_number}{level.title ? ` · ${level.title}` : ''}</option>)}
        </select></label>
        {hskQuery.isError && <p role="alert">{adminErrorText(hskQuery.error, 'Could not load HSK levels.')}</p>}
        {lessonsQuery.isPending && <p role="status">Loading lesson choices…</p>}
        {lessonsQuery.isError && <><p role="alert">{adminErrorText(lessonsQuery.error, 'Could not load lesson choices.')}</p><button type="button" onClick={() => void lessonsQuery.refetch()}>Retry lessons</button></>}
        {lessonsQuery.data && <>
          <label>Lesson<select required value={lessonId} disabled={mutation.isPending} onChange={(event) => setLessonId(event.target.value)}>
            <option value="">Select a lesson</option>{currentLessons.map((lesson) => <option key={lesson.id} value={lesson.id}>{lessonLabel(lesson, levelNumberFor(lesson))}</option>)}
          </select></label>
          <div className="admin-page-controls"><button type="button" disabled={lessonPage <= 1 || lessonsQuery.isFetching} onClick={() => setLessonPage((page) => Math.max(1, page - 1))}>Previous lessons</button><span>Page {lessonsQuery.data.page}</span><button type="button" disabled={lessonPage * lessonsQuery.data.page_size >= lessonsQuery.data.total || lessonsQuery.isFetching} onClick={() => setLessonPage((page) => page + 1)}>Next lessons</button></div>
        </>}
      </section> : <section aria-label="Periodic Test generation scope">
        <h3>Periodic Test scope</h3>
        <label>Filter lessons by HSK<select value={hskFilter} disabled={mutation.isPending} onChange={(event) => { setHskFilter(event.target.value); setLessonPage(1) }}>
          <option value="">All HSK levels</option>{(hskQuery.data ?? []).map((level) => <option key={level.id} value={level.id}>HSK {level.level_number}{level.title ? ` · ${level.title}` : ''}</option>)}
        </select></label>
        {hskQuery.isError && <p role="alert">{adminErrorText(hskQuery.error, 'Could not load HSK levels.')}</p>}
        {lessonsQuery.isPending && <p role="status">Loading lesson choices…</p>}
        {lessonsQuery.isError && <><p role="alert">{adminErrorText(lessonsQuery.error, 'Could not load lesson choices.')}</p><button type="button" onClick={() => void lessonsQuery.refetch()}>Retry lessons</button></>}
        {lessonsQuery.data && <>
          <fieldset disabled={mutation.isPending}>
            <legend>Select Lessons</legend>
            {currentLessons.map((lesson) => <label key={lesson.id}>
              <input type="checkbox" checked={selectedLessonIds.includes(lesson.id)} onChange={() => togglePeriodicLesson(lesson)} />{lessonLabel(lesson, levelNumberFor(lesson))}
            </label>)}
          </fieldset>
          <div className="admin-page-controls"><button type="button" disabled={lessonPage <= 1 || lessonsQuery.isFetching} onClick={() => setLessonPage((page) => Math.max(1, page - 1))}>Previous lessons</button><span>Page {lessonsQuery.data.page}</span><button type="button" disabled={lessonPage * lessonsQuery.data.page_size >= lessonsQuery.data.total || lessonsQuery.isFetching} onClick={() => setLessonPage((page) => page + 1)}>Next lessons</button></div>
        </>}
        {selectedLessonIds.map((id, index) => <div key={id}>
          {vocabularyQueries[index]?.isPending && <p role="status">Loading Vocabulary for {selectedLessons[id] ? lessonLabel(selectedLessons[id], levelNumberFor(selectedLessons[id])) : 'selected Lesson'}…</p>}
          {grammarQueries[index]?.isPending && <p role="status">Loading Grammar for {selectedLessons[id] ? lessonLabel(selectedLessons[id], levelNumberFor(selectedLessons[id])) : 'selected Lesson'}…</p>}
          {vocabularyQueries[index]?.isError && <><p role="alert">Could not load Vocabulary for the selected Lesson.</p><button type="button" onClick={() => void vocabularyQueries[index]?.refetch()}>Retry Vocabulary</button></>}
          {grammarQueries[index]?.isError && <><p role="alert">Could not load Grammar for the selected Lesson.</p><button type="button" onClick={() => void grammarQueries[index]?.refetch()}>Retry Grammar</button></>}
        </div>)}
        {selectedLessonIds.length > 0 && !discoveryLoading && !discoveryFailed && <>
          <fieldset disabled={mutation.isPending}><legend>Vocabulary</legend>
            {[...discoveredVocabulary.entries()].map(([id, { item, lessonIds: members }]) => <label key={id}>
              <input type="checkbox" checked={selectedVocabularyIds.includes(id)} onChange={() => setSelectedVocabularyIds((current) => current.includes(id) ? current.filter((value) => value !== id) : [...current, id])} />
              {item.hanzi} ({item.pinyin}) — {item.vietnamese_meaning}{members.length > 1 ? ` · ${members.length} selected Lessons` : ''}
            </label>)}
            {discoveredVocabulary.size === 0 && <p>No Vocabulary was found in the selected Lessons.</p>}
          </fieldset>
          <fieldset disabled={mutation.isPending}><legend>Grammar</legend>
            {[...discoveredGrammar.entries()].map(([id, { item, lessonIds: members }]) => <label key={id}>
              <input type="checkbox" checked={selectedGrammarIds.includes(id)} onChange={() => setSelectedGrammarIds((current) => current.includes(id) ? current.filter((value) => value !== id) : [...current, id])} />
              {item.name}{item.structure ? ` · ${item.structure}` : ''} — {item.explanation}{members.length > 1 ? ` · ${members.length} selected Lessons` : ''}
            </label>)}
            {discoveredGrammar.size === 0 && <p>No Grammar was found in the selected Lessons.</p>}
          </fieldset>
        </>}
        {discoveryLoading && <p role="status">Loading selected Lesson content…</p>}
      </section>}
      {mutation.isError && <p role="alert">{generationErrorText(mutation.error)}</p>}
      <button type="submit" disabled={!canGenerate || mutation.isPending}>{mutation.isPending ? 'Generating draft…' : 'Generate Draft'}</button>
    </div>
  </form>
}
