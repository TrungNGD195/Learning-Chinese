import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { queryKeys } from '../../app/query/keys'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Dialog } from '../../components/ui/Dialog'
import { EmptyState, LoadingState } from '../../components/ui/PageState'
import { PageHeader } from '../../components/ui/PageHeader'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { Surface } from '../../components/ui/Surface'
import { adminErrorText } from './AdminPrimitives'
import { getAdminCurriculum, listAdminAssessments, listAdminLessons, listHskLevels, replaceAdminCurriculum, updateHskLevel } from './api'
import { invalidateCurriculumOrder, invalidateHskMetadata } from './invalidation'

type HskLevel = Awaited<ReturnType<typeof listHskLevels>>[number]
type UnitDraft = { unit_type: 'LESSON' | 'PERIODIC_TEST'; target_id: string; title: string; order_index: number }

function toDraft(units: Awaited<ReturnType<typeof getAdminCurriculum>>): UnitDraft[] {
  return units.flatMap((unit) => {
    const target = unit.unit_type === 'LESSON' ? unit.lesson_id : unit.assessment_id
    const title = unit.unit_type === 'LESSON' ? unit.lesson_title : unit.assessment_title
    return target ? [{ unit_type: unit.unit_type, target_id: target, title: title ?? "(Chưa có tiêu đề)", order_index: unit.order_index }] : []
  })
}

function HskMetadataEditor({ hsk }: { hsk: HskLevel }) {
  const queryClient = useQueryClient()
  const [title, setTitle] = useState(hsk.title ?? '')
  const [description, setDescription] = useState(hsk.description ?? '')
  const [dirty, setDirty] = useState(false)
  useEffect(() => {
    if (!dirty) { setTitle(hsk.title ?? ''); setDescription(hsk.description ?? '') }
  }, [hsk.title, hsk.description, dirty])
  const mutation = useMutation({
    mutationFn: () => updateHskLevel(hsk.id, { title, description: description || null }),
    retry: false,
    onSuccess: async (saved) => {
      queryClient.setQueryData<HskLevel[]>(queryKeys.adminHskLevels, (levels) =>
        levels?.map((level) => level.id === saved.id ? saved : level))
      setTitle(saved.title ?? '')
      setDescription(saved.description ?? '')
      setDirty(false)
      await invalidateHskMetadata(queryClient, hsk.id)
    },
  })
  const changed = title !== (hsk.title ?? '') || description !== (hsk.description ?? '')
  return <Surface as="section" className="admin-editor-section admin-editor-card admin-hsk-metadata" aria-labelledby="hsk-metadata-title">
    <div className="admin-page-header"><div><h2 id="hsk-metadata-title">Thông tin HSK {hsk.level_number}</h2><p>Số cấp độ và thứ tự trong danh mục được cố định.</p></div>{changed && <StatusBadge tone="warning">Thông tin chưa được lưu</StatusBadge>}</div>
    <form className="admin-form-grid" onSubmit={(event) => { event.preventDefault(); if (!mutation.isPending && changed) mutation.mutate() }}>
      <label>Tiêu đề<input value={title} disabled={mutation.isPending} onChange={(event) => { setTitle(event.target.value); setDirty(true) }} /></label>
      <label>Mô tả<textarea value={description} disabled={mutation.isPending} onChange={(event) => { setDescription(event.target.value); setDirty(true) }} /></label>
      {mutation.isError && <Alert role="alert" tone="error">{adminErrorText(mutation.error, "Không thể lưu thông tin cấp độ HSK.")}</Alert>}
      <div className="admin-form-actions"><Button type="submit" variant="primary" className="admin-primary-action" disabled={!changed || mutation.isPending}>{mutation.isPending ? "Đang lưu…" : "Lưu thông tin HSK"}</Button></div>
    </form>
  </Surface>
}

function useHskRecord() {
  const levels = useQuery({ queryKey: queryKeys.adminHskLevels, queryFn: listHskLevels })
  const [selected, setSelected] = useState('')
  useEffect(() => {
    if (!selected && levels.data?.length) setSelected(levels.data[0].id)
  }, [levels.data, selected])
  return { levels, selected, setSelected, hsk: levels.data?.find((item) => item.id === selected) }
}

function CurriculumOrderEditor({ hskId }: { hskId: string }) {
  const queryClient = useQueryClient()
  const query = useQuery({ queryKey: queryKeys.adminCurriculum(hskId), queryFn: () => getAdminCurriculum(hskId) })
  const [draft, setDraft] = useState<UnitDraft[]>([])
  const [baseline, setBaseline] = useState('')
  const [lessonPage, setLessonPage] = useState(1)
  const [assessmentPage, setAssessmentPage] = useState(1)
  const [saveOpen, setSaveOpen] = useState(false)
  const current = JSON.stringify(draft.map(({ unit_type, target_id }) => ({ unit_type, target_id })))
  const dirty = baseline !== '' && current !== baseline
  const lessonFilters = { page: lessonPage, page_size: 20, status: 'PUBLISHED', hsk_level_id: hskId }
  const assessmentFilters = { page: assessmentPage, page_size: 20, status: 'PUBLISHED', assessment_type: 'PERIODIC_TEST' }
  const lessonCandidates = useQuery({ queryKey: queryKeys.adminLessons(lessonFilters), queryFn: () => listAdminLessons(lessonFilters) })
  const assessmentCandidates = useQuery({ queryKey: queryKeys.adminAssessments(assessmentFilters), queryFn: () => listAdminAssessments(assessmentFilters) })
  useEffect(() => {
    if (query.data && !dirty) {
      const next = toDraft(query.data)
      setDraft(next)
      setBaseline(JSON.stringify(next.map(({ unit_type, target_id }) => ({ unit_type, target_id }))))
    }
  }, [query.data, dirty])
  const mutation = useMutation({
    mutationFn: (units: UnitDraft[]) => replaceAdminCurriculum(hskId, { units: units.map(({ unit_type, target_id }, index) => ({ unit_type, target_id, order_index: index + 1 })) }),
    retry: false,
    onSuccess: async (result) => {
      queryClient.setQueryData(queryKeys.adminCurriculum(hskId), result)
      await invalidateCurriculumOrder(queryClient, hskId)
      const canonical = queryClient.getQueryData(queryKeys.adminCurriculum(hskId)) ?? result
      if (canonical) {
        const next = toDraft(canonical as Awaited<ReturnType<typeof getAdminCurriculum>>)
        setDraft(next)
        setBaseline(JSON.stringify(next.map(({ unit_type, target_id }) => ({ unit_type, target_id }))))
      }
    },
  })
  const move = (index: number, offset: number) => setDraft((items) => {
    const target = index + offset
    if (target < 0 || target >= items.length) return items
    const next = [...items]
    ;[next[index], next[target]] = [next[target], next[index]]
    return next.map((item, position) => ({ ...item, order_index: position + 1 }))
  })
  const addUnit = (unit: UnitDraft) => setDraft((items) => {
    if (items.some((item) => item.unit_type === unit.unit_type && item.target_id === unit.target_id)) return items
    return [...items, { ...unit, order_index: items.length + 1 }]
  })
  const removeUnit = (unit: UnitDraft) => setDraft((items) => items
    .filter((item) => item.unit_type !== unit.unit_type || item.target_id !== unit.target_id)
    .map((item, index) => ({ ...item, order_index: index + 1 })))
  if (query.isPending && !query.data) return <Surface as="section"><h2>Bài học và thứ tự trong lộ trình</h2><LoadingState>Đang tải lộ trình…</LoadingState></Surface>
  if (query.isError && !query.data) return <Surface as="section"><h2>Bài học và thứ tự trong lộ trình</h2><Alert role="alert" tone="error" action={<Button onClick={() => void query.refetch()}>Thử lại</Button>}>{adminErrorText(query.error, "Không thể tải lộ trình.")}</Alert></Surface>
  return <section className="admin-editor-section" aria-labelledby="curriculum-workspace-title">
    <h2 id="curriculum-workspace-title">Sắp xếp lộ trình</h2>
    {query.isError && <Alert tone="warning">Chưa cập nhật được lộ trình. Các thay đổi đang soạn vẫn được giữ lại.</Alert>}
    <div className="admin-curriculum-workspace">
      <Surface as="section" className="admin-curriculum-list" aria-labelledby="current-curriculum-title">
        <h3 id="current-curriculum-title">Lộ trình hiện tại</h3>
        <p>Chọn nội dung và sắp xếp thứ tự. Thay đổi chỉ được áp dụng sau khi lưu.</p>
        {draft.length === 0 ? <EmptyState title="Lộ trình chưa có nội dung">Chưa chọn bài học hoặc bài kiểm tra cho cấp độ HSK này.</EmptyState> : <ol aria-label="Nội dung lộ trình đang sắp xếp">
          {draft.map((unit, index) => <li key={`${unit.unit_type}:${unit.target_id}`}>
            <span>{unit.order_index}. {unit.unit_type === 'LESSON' ? "Bài học" : "Kiểm tra định kỳ"}: {unit.title}</span>
            <Button aria-label={`Đưa ${unit.title} lên`} disabled={mutation.isPending || index === 0} onClick={() => move(index, -1)}>Đưa lên</Button>
            <Button aria-label={`Đưa ${unit.title} xuống`} disabled={mutation.isPending || index === draft.length - 1} onClick={() => move(index, 1)}>Đưa xuống</Button>
            <Button variant="secondary" aria-label={`Gỡ ${unit.title} khỏi lộ trình`} disabled={mutation.isPending} onClick={() => removeUnit(unit)}>Gỡ khỏi lộ trình</Button>
          </li>)}
        </ol>}
      </Surface>
      <Surface as="section" className="admin-candidate-group" aria-labelledby="candidate-library-title">
        <h3 id="candidate-library-title">Nội dung có thể thêm</h3>
        <fieldset>
          <legend>Bài học đã xuất bản</legend>
          {lessonCandidates.isPending && <LoadingState>Đang tải bài học đã xuất bản…</LoadingState>}
          {lessonCandidates.isError && <Alert role="alert" tone="error" action={<Button onClick={() => void lessonCandidates.refetch()}>Thử tải lại bài học</Button>}>{adminErrorText(lessonCandidates.error, "Không thể tải bài học đã xuất bản.")}</Alert>}
          {lessonCandidates.data && <>
            <ul>{lessonCandidates.data.items.filter((item) => item.status === 'PUBLISHED').map((item) => {
              const included = draft.some((unit) => unit.unit_type === 'LESSON' && unit.target_id === item.id)
              return <li key={item.id}><span>{item.title}</span>{included ? <StatusBadge>Đã có trong lộ trình</StatusBadge> : <Button disabled={mutation.isPending} onClick={() => addUnit({ unit_type: 'LESSON', target_id: item.id, title: item.title, order_index: draft.length + 1 })}>Thêm {item.title} vào lộ trình</Button>}</li>
            })}</ul>
            <div className="admin-page-controls"><Button disabled={lessonPage <= 1} onClick={() => setLessonPage((page) => page - 1)}>Trang bài học trước</Button><span>Trang bài học {lessonCandidates.data.page}</span><Button disabled={lessonPage * lessonCandidates.data.page_size >= lessonCandidates.data.total} onClick={() => setLessonPage((page) => page + 1)}>Trang bài học tiếp</Button></div>
          </>}
        </fieldset>
        <fieldset>
          <legend>Bài kiểm tra định kỳ đã xuất bản</legend>
          {assessmentCandidates.isPending && <LoadingState>Đang tải bài kiểm tra định kỳ đã xuất bản…</LoadingState>}
          {assessmentCandidates.isError && <Alert role="alert" tone="error" action={<Button onClick={() => void assessmentCandidates.refetch()}>Thử tải lại bài kiểm tra</Button>}>{adminErrorText(assessmentCandidates.error, "Không thể tải bài kiểm tra định kỳ đã xuất bản.")}</Alert>}
          {assessmentCandidates.data && <>
            <ul>{assessmentCandidates.data.items.filter((item) => item.status === 'PUBLISHED' && item.type === 'PERIODIC_TEST').map((item) => {
              const included = draft.some((unit) => unit.unit_type === 'PERIODIC_TEST' && unit.target_id === item.id)
              return <li key={item.id}><span>{item.title}</span>{included ? <StatusBadge>Đã có trong lộ trình</StatusBadge> : <Button disabled={mutation.isPending} onClick={() => addUnit({ unit_type: 'PERIODIC_TEST', target_id: item.id, title: item.title, order_index: draft.length + 1 })}>Thêm {item.title} vào lộ trình</Button>}</li>
            })}</ul>
            <div className="admin-page-controls"><Button disabled={assessmentPage <= 1} onClick={() => setAssessmentPage((page) => page - 1)}>Trang bài kiểm tra trước</Button><span>Trang bài kiểm tra {assessmentCandidates.data.page}</span><Button disabled={assessmentPage * assessmentCandidates.data.page_size >= assessmentCandidates.data.total} onClick={() => setAssessmentPage((page) => page + 1)}>Trang bài kiểm tra tiếp</Button></div>
          </>}
        </fieldset>
      </Surface>
    </div>
    {mutation.isError && <Alert role="alert" tone="error">{adminErrorText(mutation.error, "Không thể lưu lộ trình. Các thay đổi chưa lưu vẫn được giữ lại.")}</Alert>}
    {query.isFetching && <LoadingState>Đang cập nhật lộ trình…</LoadingState>}
    <div className={`admin-save-bar${dirty ? ' admin-save-bar--dirty' : ''}`}>
      {dirty ? <p>Lộ trình có thay đổi chưa lưu</p> : <p>Lộ trình đã được cập nhật.</p>}
      <Button variant="primary" className="admin-primary-action" disabled={!dirty || mutation.isPending} onClick={() => setSaveOpen(true)}>{mutation.isPending ? "Đang lưu lộ trình…" : "Lưu lộ trình"}</Button>
    </div>
    <Dialog cancelLabel="Hủy" open={saveOpen} title="Lưu thay đổi lộ trình?" confirmLabel="Lưu lộ trình" busy={mutation.isPending}
      onCancel={() => setSaveOpen(false)} onClose={() => setSaveOpen(false)}
      onConfirm={() => { mutation.mutate(draft); setSaveOpen(false) }}>
      Toàn bộ nội dung và thứ tự đang sắp xếp sẽ được lưu cho cấp độ HSK đã chọn.
    </Dialog>
  </section>
}

export function AdminCurriculumPage() {
  const { levels, selected, setSelected, hsk } = useHskRecord()
  if (levels.isPending && !levels.data) return <section className="screen admin-screen admin-curriculum-page"><PageHeader title="Sắp xếp HSK" titleId="page-title" description="Quản lý cấp độ HSK, nội dung và thứ tự học." /><LoadingState>Đang tải cấp độ HSK…</LoadingState></section>
  if (levels.isError && !levels.data) return <section className="screen admin-screen admin-curriculum-page"><PageHeader title="Sắp xếp HSK" titleId="page-title" description="Quản lý cấp độ HSK, nội dung và thứ tự học." /><Alert role="alert" tone="error" action={<Button onClick={() => void levels.refetch()}>Thử lại</Button>}>{adminErrorText(levels.error, "Không thể tải cấp độ HSK.")}</Alert></section>
  return <section className="screen admin-screen admin-curriculum-page" aria-labelledby="page-title">
    <PageHeader title="Sắp xếp HSK" titleId="page-title" back={<Link to="/admin/lessons">Quay lại bài học</Link>} description="Sắp xếp bài học và bài kiểm tra trong từng cấp độ HSK." />
    {levels.isError && <Alert tone="warning">Chưa cập nhật được cấp độ HSK.</Alert>}
    <Surface as="section" aria-label="Chọn cấp độ HSK"><label>Chọn HSK<select value={selected} onChange={(event) => setSelected(event.target.value)}>
      {(levels.data ?? []).map((item) => <option key={item.id} value={item.id}>HSK {item.level_number}{item.title ? ` — ${item.title}` : ''}</option>)}
    </select></label></Surface>
    {levels.data?.length === 0 && <EmptyState title="Chưa có cấp độ HSK">Hiện chưa có cấp độ HSK khả dụng.</EmptyState>}
    {hsk && <><HskMetadataEditor key={`metadata:${hsk.id}`} hsk={hsk} /><CurriculumOrderEditor key={`curriculum:${hsk.id}`} hskId={hsk.id} /></>}
  </section>
}
