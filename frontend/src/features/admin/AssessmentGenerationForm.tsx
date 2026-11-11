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
import { Alert, Button, Surface } from '../../components/ui'

type GenerationKind = AssessmentGenerationRequest['type']
type QuestionType = components['schemas']['LessonExerciseGenerationRequest']['allowed_types'][number]
type Difficulty = components['schemas']['LessonExerciseGenerationRequest']['difficulty']
type LessonChoice = Awaited<ReturnType<typeof listAdminLessons>>['items'][number]
type VocabularyChoice = Awaited<ReturnType<typeof listLessonVocabulary>>[number]
type GrammarChoice = Awaited<ReturnType<typeof listLessonGrammar>>[number]

const questionTypeOptions = [
  ['multiple_choice', "Chọn đáp án"],
  ['fill_blank', "Điền vào chỗ trống"],
  ['matching', "Nối cặp"],
  ['reorder_sentence', "Sắp xếp câu"],
  ['translate_vi_zh', "Dịch Việt → Trung"],
  ['translate_zh_vi', "Dịch Trung → Việt"],
  ['sentence_writing', "Viết câu"],
] as const satisfies readonly (readonly [QuestionType, string])[]

function generationErrorText(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case 'INVALID_REQUEST': return "Kiểm tra thiết lập tạo đề và thử lại."
      case 'INVALID_GENERATION_SCOPE': return "Kiểm tra bài học, từ vựng và ngữ pháp đã chọn rồi thử lại."
      case 'AI_GENERATION_INPUT_TOO_LARGE': return "Phạm vi tạo đề quá lớn. Hãy giảm số bài học hoặc mục nội dung đã chọn."
      case 'AI_GENERATION_INVALID_OUTPUT': return "AI trả về nội dung chưa hợp lệ. Kiểm tra thiết lập rồi thử tạo lại."
      case 'AI_GENERATION_UNAVAILABLE': return "Tính năng tạo đề bằng AI tạm thời không khả dụng. Bạn có thể thử lại."
      case 'AI_GENERATION_PERSISTENCE_FAILED': return "Không thể lưu đề vừa tạo. Chưa có bản nháp mới; bạn có thể thử lại."
      default: return adminErrorText(error, "Không thể tạo bản nháp bài luyện tập.")
    }
  }
  return adminErrorText(error, "Không thể tạo bản nháp bài luyện tập.")
}

function lessonLabel(lesson: LessonChoice, levelNumber?: number) {
  return `HSK ${levelNumber ?? '—'} · Bài ${lesson.lesson_number} · ${lesson.title}`
}

export function AssessmentGenerationForm({ fixedLessonId, periodicOnly = false, onCreated }: { fixedLessonId?: string; periodicOnly?: boolean; onCreated?: (id: string) => void }) {
  const client = useQueryClient()
  const navigate = useNavigate()
  const [generationKind, setGenerationKind] = useState<GenerationKind>(periodicOnly ? 'PERIODIC_TEST' : 'LESSON_EXERCISE')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [passThreshold, setPassThreshold] = useState(periodicOnly ? '90' : '80')
  const [questionCount, setQuestionCount] = useState(periodicOnly ? '1' : '30')
  const [difficulty, setDifficulty] = useState<Difficulty | ''>('')
  const [allowedTypes, setAllowedTypes] = useState<QuestionType[]>(periodicOnly ? ['multiple_choice'] : ['multiple_choice', 'fill_blank', 'matching', 'reorder_sentence'])
  const [lessonId, setLessonId] = useState(fixedLessonId ?? '')
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
    enabled: !fixedLessonId,
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
    && Number.isInteger(countValue) && (generationKind === 'LESSON_EXERCISE' ? countValue === 30 : countValue >= 1 && countValue <= 10)
    && difficulty !== '' && allowedTypes.length >= (generationKind === 'LESSON_EXERCISE' ? 3 : 1)
  const mutation = useMutation({
    mutationFn: (request: AssessmentGenerationRequest) => generateAssessmentDraft(request),
    retry: false,
    onSuccess: async (result) => {
      await invalidateAssessmentList(client)
      const item = result.assessment
      if (onCreated) { onCreated(item.id); return }
      await navigate(item.lesson_id ? `/admin/lessons/${encodeURIComponent(item.lesson_id)}?section=exercises&exercise=${encodeURIComponent(item.id)}` : `/admin/assessments/${encodeURIComponent(item.id)}`)
    },
  })
  const validScope = generationKind === 'LESSON_EXERCISE'
    ? Boolean(fixedLessonId || (!lessonsQuery.isPending && !lessonsQuery.isError && lessonId
      && lessonsQuery.data?.items.some((lesson) => lesson.id === lessonId && lesson.status !== 'ARCHIVED')))
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

  return <Surface as="section" className="admin-ai-generation-surface">
    <form className="admin-ai-generation-form" onSubmit={submit} aria-labelledby="generate-assessment-title">
    <header className="admin-ai-generation-header"><div><h2 id="generate-assessment-title">Tạo bản nháp bằng AI</h2></div><p>Đề do AI tạo được lưu dưới dạng nháp. Quản trị viên cần duyệt và xuất bản trước khi học viên sử dụng.</p></header>
    <div className="admin-ai-generation-fields">
      {!fixedLessonId && !periodicOnly && <section className="admin-ai-generation-group" aria-labelledby="generation-type-heading"><h3 id="generation-type-heading">1. Loại bài luyện tập</h3>
      <label>Loại bài luyện tập<select value={generationKind} disabled={mutation.isPending} onChange={(event) => { setGenerationKind(event.target.value as GenerationKind); setPassThreshold(event.target.value === 'LESSON_EXERCISE' ? '80' : '90'); setQuestionCount(event.target.value === 'LESSON_EXERCISE' ? '30' : '1'); setAllowedTypes(event.target.value === 'LESSON_EXERCISE' ? ['multiple_choice', 'fill_blank', 'matching', 'reorder_sentence'] : ['multiple_choice']) }}>
        <option value="LESSON_EXERCISE">Luyện tập bài học</option><option value="PERIODIC_TEST">Kiểm tra định kỳ</option>
      </select></label>
      </section>}

      {fixedLessonId ? <section className="admin-ai-generation-group"><h3>Phạm vi tạo câu hỏi</h3><p>30 câu hỏi trọng tâm bài hiện tại, kết hợp ôn từ vựng và ngữ pháp các bài trước trong cùng cấp HSK. Bản nháp được mở ngay tại đây để chỉnh sửa và duyệt.</p></section> : generationKind === 'LESSON_EXERCISE' ? <section className="admin-ai-generation-group" aria-label="Phạm vi tạo luyện tập bài học">
        <h3>2. Phạm vi · Luyện tập bài học</h3>
        <label>Lọc bài học theo HSK<select value={hskFilter} disabled={mutation.isPending} onChange={(event) => { setHskFilter(event.target.value); setLessonPage(1) }}>
          <option value="">Tất cả cấp độ HSK</option>{(hskQuery.data ?? []).map((level) => <option key={level.id} value={level.id}>HSK {level.level_number}{level.title ? ` · ${level.title}` : ''}</option>)}
        </select></label>
        {hskQuery.isError && <p role="alert">{adminErrorText(hskQuery.error, "Không thể tải cấp độ HSK.")}</p>}
        {lessonsQuery.isPending && <p role="status">Đang tải danh sách bài học…</p>}
        {lessonsQuery.isError && <><p role="alert">{adminErrorText(lessonsQuery.error, "Không thể tải danh sách bài học.")}</p><button type="button" onClick={() => void lessonsQuery.refetch()}>Thử tải lại bài học</button></>}
        {lessonsQuery.data && <>
          <label>Bài học<select required value={lessonId} disabled={mutation.isPending} onChange={(event) => setLessonId(event.target.value)}>
            <option value="">Chọn một bài học</option>{currentLessons.map((lesson) => <option key={lesson.id} value={lesson.id}>{lessonLabel(lesson, levelNumberFor(lesson))}</option>)}
          </select></label>
          <div className="admin-page-controls"><button type="button" disabled={lessonPage <= 1 || lessonsQuery.isFetching} onClick={() => setLessonPage((page) => Math.max(1, page - 1))}>Bài học trước</button><span>Trang {lessonsQuery.data.page}</span><button type="button" disabled={lessonPage * lessonsQuery.data.page_size >= lessonsQuery.data.total || lessonsQuery.isFetching} onClick={() => setLessonPage((page) => page + 1)}>Bài học tiếp</button></div>
        </>}
      </section> : <section className="admin-ai-generation-group admin-ai-generation-periodic" aria-label="Phạm vi tạo bài kiểm tra định kỳ">
        <h3>2. Phạm vi · Kiểm tra định kỳ</h3>
        <label>Lọc bài học theo HSK<select value={hskFilter} disabled={mutation.isPending} onChange={(event) => { setHskFilter(event.target.value); setLessonPage(1) }}>
          <option value="">Tất cả cấp độ HSK</option>{(hskQuery.data ?? []).map((level) => <option key={level.id} value={level.id}>HSK {level.level_number}{level.title ? ` · ${level.title}` : ''}</option>)}
        </select></label>
        {hskQuery.isError && <p role="alert">{adminErrorText(hskQuery.error, "Không thể tải cấp độ HSK.")}</p>}
        {lessonsQuery.isPending && <p role="status">Đang tải danh sách bài học…</p>}
        {lessonsQuery.isError && <><p role="alert">{adminErrorText(lessonsQuery.error, "Không thể tải danh sách bài học.")}</p><button type="button" onClick={() => void lessonsQuery.refetch()}>Thử tải lại bài học</button></>}
        {lessonsQuery.data && <>
          <fieldset disabled={mutation.isPending}>
            <legend>Chọn bài học</legend>
            {currentLessons.map((lesson) => <label key={lesson.id}>
              <input type="checkbox" checked={selectedLessonIds.includes(lesson.id)} onChange={() => togglePeriodicLesson(lesson)} />{lessonLabel(lesson, levelNumberFor(lesson))}
            </label>)}
          </fieldset>
          <div className="admin-page-controls"><button type="button" disabled={lessonPage <= 1 || lessonsQuery.isFetching} onClick={() => setLessonPage((page) => Math.max(1, page - 1))}>Bài học trước</button><span>Trang {lessonsQuery.data.page}</span><button type="button" disabled={lessonPage * lessonsQuery.data.page_size >= lessonsQuery.data.total || lessonsQuery.isFetching} onClick={() => setLessonPage((page) => page + 1)}>Bài học tiếp</button></div>
        </>}
        {selectedLessonIds.map((id, index) => <div key={id}>
          {vocabularyQueries[index]?.isPending && <p role="status">Đang tải từ vựng của {selectedLessons[id] ? lessonLabel(selectedLessons[id], levelNumberFor(selectedLessons[id])) : "bài học đã chọn"}…</p>}
          {grammarQueries[index]?.isPending && <p role="status">Đang tải ngữ pháp của {selectedLessons[id] ? lessonLabel(selectedLessons[id], levelNumberFor(selectedLessons[id])) : "bài học đã chọn"}…</p>}
          {vocabularyQueries[index]?.isError && <><p role="alert">Không thể tải từ vựng của bài học đã chọn.</p><button type="button" onClick={() => void vocabularyQueries[index]?.refetch()}>Thử tải lại từ vựng</button></>}
          {grammarQueries[index]?.isError && <><p role="alert">Không thể tải ngữ pháp của bài học đã chọn.</p><button type="button" onClick={() => void grammarQueries[index]?.refetch()}>Thử tải lại ngữ pháp</button></>}
        </div>)}
        {selectedLessonIds.length > 0 && !discoveryLoading && !discoveryFailed && <>
          <fieldset disabled={mutation.isPending}><legend>Từ vựng</legend>
            {[...discoveredVocabulary.entries()].map(([id, { item, lessonIds: members }]) => <label key={id}>
              <input type="checkbox" checked={selectedVocabularyIds.includes(id)} onChange={() => setSelectedVocabularyIds((current) => current.includes(id) ? current.filter((value) => value !== id) : [...current, id])} />
              {item.hanzi} ({item.pinyin}) — {item.vietnamese_meaning}{members.length > 1 ? ` · ${members.length} bài học đã chọn` : ''}
            </label>)}
            {discoveredVocabulary.size === 0 && <p>Các bài học đã chọn chưa có từ vựng.</p>}
          </fieldset>
          <fieldset disabled={mutation.isPending}><legend>Ngữ pháp</legend>
            {[...discoveredGrammar.entries()].map(([id, { item, lessonIds: members }]) => <label key={id}>
              <input type="checkbox" checked={selectedGrammarIds.includes(id)} onChange={() => setSelectedGrammarIds((current) => current.includes(id) ? current.filter((value) => value !== id) : [...current, id])} />
              {item.name}{item.structure ? ` · ${item.structure}` : ''} — {item.explanation}{members.length > 1 ? ` · ${members.length} bài học đã chọn` : ''}
            </label>)}
            {discoveredGrammar.size === 0 && <p>Các bài học đã chọn chưa có ngữ pháp.</p>}
          </fieldset>
        </>}
        <dl className="admin-ai-generation-selection-summary" aria-label="Tóm tắt nội dung đã chọn">
          <div><dt>Bài học đã chọn</dt><dd>{selectedLessonIds.length}</dd></div>
          <div><dt>Từ vựng đã chọn</dt><dd>{selectedVocabularyIds.filter((id) => discoveredVocabulary.has(id)).length}</dd></div>
          <div><dt>Ngữ pháp đã chọn</dt><dd>{selectedGrammarIds.filter((id) => discoveredGrammar.has(id)).length}</dd></div>
        </dl>
        {discoveryLoading && <p role="status">Đang tải nội dung bài học đã chọn…</p>}
      </section>}
      <section className="admin-ai-generation-group" aria-labelledby="generation-config-heading"><h3 id="generation-config-heading">Thiết lập tạo đề</h3>
        <div className="admin-ai-generation-config">
          <label>Tiêu đề (không bắt buộc)<input value={title} disabled={mutation.isPending} onChange={(event) => setTitle(event.target.value)} /></label>
          <label>Mô tả (không bắt buộc)<textarea value={description} disabled={mutation.isPending} onChange={(event) => setDescription(event.target.value)} /></label>
          <label>Điểm đạt (%)<input type="number" min="0" max="100" step="1" value={passThreshold} disabled={mutation.isPending} onChange={(event) => setPassThreshold(event.target.value)} /></label>
          <label>Số câu hỏi<input type="number" min={generationKind === 'LESSON_EXERCISE' ? '30' : '1'} max={generationKind === 'LESSON_EXERCISE' ? '30' : '10'} step="1" value={questionCount} readOnly={generationKind === 'LESSON_EXERCISE'} disabled={mutation.isPending} onChange={(event) => setQuestionCount(event.target.value)} /></label>
          {generationKind === 'LESSON_EXERCISE' && <p>Bài luyện tập gồm 30 câu. Chọn ít nhất 3 dạng bài để ôn tập đa dạng.</p>}
          <label>Độ khó<select required value={difficulty} disabled={mutation.isPending} onChange={(event) => setDifficulty(event.target.value as Difficulty | '')}>
            <option value="">Chọn độ khó</option><option value="EASY">Dễ</option><option value="MEDIUM">Trung bình</option><option value="HARD">Khó</option>
          </select></label>
        </div>
      </section>
      <fieldset className="admin-ai-generation-group admin-ai-generation-question-types" disabled={mutation.isPending}>
        <legend>Dạng câu hỏi</legend>
        {questionTypeOptions.map(([value, label]) => <label key={value}><input type="checkbox" checked={allowedTypes.includes(value)} onChange={() => toggleQuestionType(value)} />{label}</label>)}
      </fieldset>
      {mutation.isError && <Alert role="alert" tone="error">{generationErrorText(mutation.error)}</Alert>}
      <div className="admin-ai-generation-submit"><p>Tạo bản nháp để quản trị viên duyệt.</p><Button variant="primary" type="submit" disabled={!canGenerate || mutation.isPending}>{mutation.isPending ? "Đang tạo bản nháp…" : "Tạo bản nháp"}</Button></div>
    </div>
    </form>
  </Surface>
}
