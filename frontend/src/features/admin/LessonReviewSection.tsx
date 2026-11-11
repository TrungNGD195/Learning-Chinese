import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { queryKeys } from '../../app/query/keys'
import { Alert, Button, LoadingState, StatusBadge, Surface } from '../../components/ui'
import { listAssessmentQuestions, listLessonGrammar, listLessonVocabulary, publishAdminLessonPackage } from './api'
import { listLessonReadings } from './readingApi'
import { useLessonExercises } from './LessonExercisesSection'
import { useHasUnsavedDrafts } from './AuthoringSession'
import { invalidateAssessmentLifecycle, invalidateLessonLifecycle } from './invalidation'
import { adminErrorText } from './AdminPrimitives'
import { adminLabel } from './labels'
import { ApiError } from '../../lib/api/errors'

type Area = 'vocabulary' | 'grammar' | 'readings' | 'exercises'

export function LessonReviewSection({ lessonId, lessonStatus, onEdit }: { lessonId: string; lessonStatus: string; onEdit: (area: Area) => void }) {
  const client = useQueryClient()
  const unsaved = useHasUnsavedDrafts()
  const vocabulary = useQuery({ queryKey: queryKeys.adminLessonVocabulary(lessonId), queryFn: () => listLessonVocabulary(lessonId) })
  const grammar = useQuery({ queryKey: queryKeys.adminLessonGrammar(lessonId), queryFn: () => listLessonGrammar(lessonId) })
  const readings = useQuery({ queryKey: queryKeys.adminLessonReadings(lessonId), queryFn: () => listLessonReadings(lessonId) })
  const exercises = useLessonExercises(lessonId)
  const active = exercises.data?.filter((item) => item.status !== 'ARCHIVED') ?? []
  const questionQueries = useQueries({ queries: active.map((item) => ({ queryKey: queryKeys.adminQuestions(item.id), queryFn: () => listAssessmentQuestions(item.id) })) })
  const loading = [vocabulary, grammar, readings, exercises, ...questionQueries].some((query) => query.isPending)
  const failed = [vocabulary, grammar, readings, exercises, ...questionQueries].some((query) => query.isError)
  const ready = !loading && !failed && active.length > 0 && questionQueries.every((query) => query.data?.length === 30 && new Set(query.data.map((question) => question.type)).size >= 3)
  const published = lessonStatus === 'PUBLISHED' && active.length > 0 && active.every((item) => item.status === 'PUBLISHED')
  const publish = useMutation({
    mutationFn: () => publishAdminLessonPackage(lessonId), retry: false,
    onSuccess: async (lesson) => {
      await Promise.all([
        invalidateLessonLifecycle(client, lesson.id, lesson.hsk_level_id),
        ...active.map((item) => invalidateAssessmentLifecycle(client, item)),
      ])
    },
    onError: async (error) => {
      if (error instanceof ApiError && error.status === 409) await Promise.all([
        client.invalidateQueries({ queryKey: queryKeys.adminLesson(lessonId) }),
        exercises.refetch(), ...questionQueries.map((query) => query.refetch()),
      ])
    },
  })
  return <Surface as="section" className="admin-editor-section admin-lesson-review" aria-labelledby="lesson-review-title">
    <h2 id="lesson-review-title">Duyệt toàn bộ bài học</h2>
    <p>Kiểm tra lý thuyết và bài luyện tập. Khi xác nhận, cả hai phần được xuất bản cùng lúc cho học viên.</p>
    <div className="admin-lesson-review-theory">{([
      ['vocabulary', 'Từ vựng', vocabulary.data?.length], ['grammar', 'Ngữ pháp', grammar.data?.length], ['readings', 'Bài khóa', readings.data?.length],
    ] as const).map(([area, label, count]) => <div key={area}><span>{label}</span><strong>{count ?? '—'} mục</strong><Button variant="ghost" onClick={() => onEdit(area)}>Xem và sửa {label.toLowerCase()}</Button></div>)}</div>
    <div className="admin-lesson-review-practice"><div className="admin-page-header"><h3>Bài luyện tập</h3><Button variant="secondary" onClick={() => onEdit('exercises')}>Xem và sửa câu hỏi</Button></div>
      {active.length === 0 && !exercises.isPending && <p>Chưa có bài luyện tập. Thêm bài luyện tập trong mục Luyện tập trước khi xuất bản.</p>}
      {active.map((item, index) => {
        const questions = questionQueries[index].data
        const types = questions ? new Set(questions.map((question) => question.type)).size : undefined
        const valid = questions?.length === 30 && (types ?? 0) >= 3
        return <div className="admin-lesson-review-exercise" key={item.id}><div><h4>{item.title}</h4><p>{questions?.length ?? '—'}/30 câu · {types ?? '—'} dạng bài · Điểm đạt {item.pass_threshold}%</p></div><StatusBadge tone={valid ? 'success' : 'warning'}>{valid ? adminLabel(item.status) : 'Cần hoàn thiện'}</StatusBadge></div>
      })}
      <p>Mỗi bài luyện cần đủ 30 câu và ít nhất 3 dạng bài.</p>
    </div>
    {loading && <LoadingState>Đang kiểm tra nội dung bài học…</LoadingState>}
    {failed && <Alert role="alert" tone="error" action={<Button onClick={() => { void Promise.all([vocabulary.refetch(), grammar.refetch(), readings.refetch(), exercises.refetch(), ...questionQueries.map((query) => query.refetch())]) }}>Thử lại</Button>}>Chưa tải đủ nội dung để duyệt xuất bản.</Alert>}
    {unsaved && <Alert tone="warning">Lưu các thay đổi ở từng mục trước khi xuất bản.</Alert>}
    {publish.isError && <Alert role="alert" tone="error">{adminErrorText(publish.error, 'Không thể xuất bản bài học. Hãy kiểm tra và thử lại.')}</Alert>}
    <div className="admin-lesson-review-confirm"><p>{published ? 'Lý thuyết và các bài luyện tập đang hiển thị cho học viên.' : 'Xác nhận đã kiểm tra nội dung, câu hỏi và đáp án trước khi xuất bản.'}</p><Button variant="primary" disabled={lessonStatus === 'ARCHIVED' || published || unsaved || !ready || publish.isPending} onClick={() => publish.mutate()}>{publish.isPending ? 'Đang xuất bản…' : published ? 'Đã xuất bản toàn bộ' : 'Xác nhận xuất bản toàn bộ'}</Button></div>
  </Surface>
}
