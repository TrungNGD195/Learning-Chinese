import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { Alert, Button, LoadingState, PageHeader, StatusBadge, Surface } from '../../components/ui'
import { queryKeys } from '../../app/query/keys'
import { advancePronunciation, completeSection, finishPronunciationLesson, getPronunciationLesson } from './api'
import { invalidatePronunciationCompletion } from './invalidation'
import { pronunciationContent, useMandarinSpeech, type PronunciationCode } from './pronunciationData'
import { pronunciationCodeForSlug, pronunciationSectionPath, pronunciationSections } from './sectionRoutes'
import { Companion } from '../../components/academy/Companion'
import { StudyAdvice } from '../../components/academy/StudyAdvice'
import { AcademyIcon } from '../../components/academy/AcademyIcon'
import { pronunciationTip } from './pronunciationTips'
import { ToneDiagram } from './ToneDiagram'
import { SandhiExample } from './SandhiExample'
import { useLessonStudyPosition } from '../lesson/useLessonStudyPosition'
import { PronunciationSectionNav, PronunciationStudyHeader } from './PronunciationStudyLayout'

const sectionNames: Record<PronunciationCode, string> = { INITIALS: 'thanh mẫu', FINALS: 'vận mẫu', TONES: 'thanh điệu', SANDHI: 'biến điệu' }

export function PronunciationLessonPage() {
  const client = useQueryClient()
  const navigate = useNavigate()
  const lesson = useQuery({ queryKey: queryKeys.pronunciationLesson, queryFn: getPronunciationLesson })
  const finish = useMutation({
    mutationFn: finishPronunciationLesson,
    retry: false,
    onSuccess: async () => { await invalidatePronunciationCompletion(client); await navigate('/pronunciation') },
    onError: () => client.invalidateQueries({ queryKey: queryKeys.pronunciationLesson }),
  })
  const state = lesson.data
  const root = useLessonStudyPosition(Boolean(state), 'pronunciation-overview')
  return <section ref={root} className="learner-page pronunciation-page pronunciation-session lesson-study-workspace pronunciation-study-workspace pronunciation-study-overview screen" aria-labelledby="page-title">
    <PronunciationStudyHeader state={state}/>
    {lesson.isPending && <LoadingState>Đang tải bài học…</LoadingState>}
    {lesson.isError && !state && <Alert role="alert" tone="error" action={<Button onClick={() => void lesson.refetch()}>Thử lại</Button>}>Không thể tải bài học phát âm.</Alert>}
    {finish.isError && <Alert role="alert" tone="error">Không thể lưu kết quả hoàn thành. Vui lòng thử lại.</Alert>}
    {state && <>
      <div id="lesson-study-content"><ol className="pronunciation-section-grid" aria-label="Các phần của bài học">{state.sections.map((section, index) => {
        const meta = pronunciationSections[section.code]
        const completed = Boolean(section.completed_at)
        const current = state.current_section === section.code
        const available = completed || current
        const content = <>
          <div className="pronunciation-section-block__heading"><h2>{index + 1}. {meta.title}</h2><StatusBadge tone={completed ? 'success' : current ? 'info' : 'neutral'}>{completed ? 'Đã xong' : current ? 'Đang học' : 'Đã khóa'}</StatusBadge></div>
          <span className="pronunciation-section-block__preview" aria-hidden="true">{meta.preview}</span>
          <p>{meta.description}</p>
          <span className="pronunciation-section-block__action">{completed ? 'Ôn tập' : current ? 'Vào học' : 'Hoàn thành phần trước để mở'}{available && <AcademyIcon name="arrow" size={20}/>}</span>
        </>
        return <li key={section.code}>{available ? <Link className="pronunciation-section-block" data-state={completed ? 'completed' : 'current'} to={pronunciationSectionPath(section.code)} aria-label={`${completed ? 'Ôn' : 'Học'} ${sectionNames[section.code]}`}>{content}</Link> : <div className="pronunciation-section-block" data-state="locked" aria-disabled="true">{content}</div>}</li>
      })}</ol>
      {state.can_finish && !(state.completed_at && !state.current_section) && <Surface as="section" className="pronunciation-finish">
        <div><h2>Đã hoàn thành bốn phần</h2><p>Hoàn thành bài học để lưu kết quả và mở HSK 1.</p></div>
        <Button variant="primary" disabled={finish.isPending} onClick={() => finish.mutate()}>{finish.isPending ? 'Đang lưu…' : 'Hoàn thành bài học'}</Button>
      </Surface>}
      <StudyAdvice topic="pronunciation"/></div>
    </>}
  </section>
}

export function PronunciationSectionPage() {
  const { sectionSlug } = useParams()
  const code = pronunciationCodeForSlug(sectionSlug)
  return code ? <PronunciationSectionSession key={code} code={code}/> : <section className="learner-page screen">
    <PageHeader title="Không tìm thấy phần phát âm" back={<Link to="/pronunciation/lesson">← Các phần phát âm</Link>}/>
    <p>Hãy chọn một phần trong bài học phát âm để tiếp tục.</p>
  </section>
}

function PronunciationSectionSession({ code }: { code: PronunciationCode }) {
  const [viewedStep, setViewedStep] = useState<number | null>(null)
  const client = useQueryClient()
  const navigate = useNavigate()
  const { voiceAvailable, speak } = useMandarinSpeech()
  const lesson = useQuery({ queryKey: queryKeys.pronunciationLesson, queryFn: getPronunciationLesson })
  const refresh = () => client.invalidateQueries({ queryKey: queryKeys.pronunciationLesson })
  const advance = useMutation({
    mutationFn: ({ code, step }: { code: PronunciationCode; step: number }) => advancePronunciation(code, step),
    retry: false,
    onSuccess: state => { if (state) client.setQueryData(queryKeys.pronunciationLesson, state) },
    onError: refresh,
  })
  const complete = useMutation({
    mutationFn: completeSection,
    retry: false,
    onSuccess: async () => { await invalidatePronunciationCompletion(client); await navigate('/pronunciation/lesson') },
    onError: refresh,
  })
  const state = lesson.data
  const section = state?.sections.find(row => row.code === code)
  const reviewing = Boolean(section?.completed_at)
  const available = reviewing || state?.current_section === code
  const step = reviewing ? viewedStep ?? 0 : Math.min(viewedStep ?? state?.step_index ?? 0, state?.step_index ?? 0)
  const pending = advance.isPending || complete.isPending
  const root = useLessonStudyPosition(Boolean(state), `pronunciation:${code}:${step}`)
  return <section ref={root} className="learner-page pronunciation-page pronunciation-session lesson-study-workspace pronunciation-study-workspace screen" aria-labelledby="page-title">
    <PronunciationStudyHeader state={state} code={code}/>
    {lesson.isPending && <LoadingState>Đang tải phần phát âm…</LoadingState>}
    {lesson.isError && !state && <Alert role="alert" tone="error" action={<Button onClick={() => void lesson.refetch()}>Thử lại</Button>}>Không thể tải bài học phát âm.</Alert>}
    {state && <div className="lesson-manuscript__body">
      <PronunciationSectionNav state={state} active={code}/>
      <div id="lesson-study-content" className="lesson-manuscript__chapters">
      {(advance.isError || complete.isError) && <Alert role="alert" tone="error">Không thể lưu bước học. Tiến độ mới nhất đang được tải lại; vui lòng thử lại.</Alert>}
      {available && section ? <>
        <PronunciationStep code={code} step={step} savedStep={reviewing ? undefined : state.step_index} total={reviewing ? section.total_steps : state.total_steps}
          completionLabel={reviewing ? 'Về các phần phát âm' : undefined}
          sectionId={section.id} pending={pending} voiceAvailable={voiceAvailable} speak={speak}
          onBack={(_, value) => setViewedStep(Math.max(0, value - 1))}
          onNext={(_, value) => {
            if (reviewing || value < state.step_index) setViewedStep(value + 1)
            else { setViewedStep(null); advance.mutate({ code, step: value }) }
          }}
          onComplete={id => { if (reviewing) void navigate('/pronunciation/lesson'); else complete.mutate(id) }}/>
      </> : <Surface><h2>Phần học này chưa mở</h2><p>Hoàn thành các phần trước theo thứ tự để mở {sectionNames[code]}.</p><Link className="learner-link-action" to="/pronunciation/lesson">Chọn phần đang học</Link></Surface>}
      </div>
    </div>}
  </section>
}

function PronunciationStep({ code, step, savedStep, total, sectionId, pending, voiceAvailable, speak, onBack, onNext, onComplete, completionLabel }: {
  code: PronunciationCode; step: number; total: number; sectionId: string | undefined; pending: boolean
  savedStep?: number
  completionLabel?: string
  voiceAvailable: boolean; speak: ReturnType<typeof useMandarinSpeech>['speak']
  onBack: (code: PronunciationCode, step: number) => void
  onNext: (code: PronunciationCode, step: number) => void; onComplete: (id: string) => void
}) {
  const lesson = pronunciationContent[code]
  const sounds = lesson.groups.flatMap((group) => group.sounds.map((sound) => ({ sound, group })))
  if (sounds.length !== total || step > total || !sectionId) return <Alert role="alert" tone="error">Nội dung bài học chưa đồng bộ với máy chủ. Vui lòng thử lại sau.</Alert>
  const current = sounds[step]
  return <div className="academy-pronunciation-layout"><Surface as="section" className="pronunciation-session__card" aria-labelledby="pronunciation-step-title">
    <div className="pronunciation-session__heading"><div><h2 id="pronunciation-step-title">{sectionNames[code]}</h2></div>
      {current && <span>{current.group.title}</span>}</div>
    <progress aria-label={`Tiến độ ${sectionNames[code]}`} max={total} value={savedStep ?? step} />
    {current ? <>
      {code === 'SANDHI' ? <SandhiExample sound={current.sound} voiceAvailable={voiceAvailable} onListen={() => speak(current.sound)}/> : <div className="pronunciation-session__sound academy-sound-stage" aria-live="polite">
        <div className="academy-phonetic-identity">
        <strong className="pronunciation-session__symbol">{current.sound.symbol}</strong>
        <span className="academy-sound-label">{code==='TONES'?'Đường đi của giọng':'Âm đang học'}</span>
        {code==='TONES'&&<ToneDiagram tone={step}/>}
        </div><div className="academy-sound-example"><span className="academy-sound-hanzi" lang="zh-Hans">{current.sound.hanzi}</span><span className="academy-sound-pinyin">{current.sound.pinyin}</span><Button variant="secondary" disabled={!voiceAvailable} onClick={() => speak(current.sound)}><AcademyIcon name="sound" size={19}/>Nghe phát âm</Button><small>Giọng đọc của thiết bị</small></div>
      </div>}
      <p className="pronunciation-study-intro">{lesson.intro}</p>
      <div className="academy-articulation-note"><Companion pose="truc" decorative/><div><h3>Trúc nhắc nhỏ</h3><p>{pronunciationTip(code, current.sound)}</p></div></div>
      {!voiceAvailable && <p role="status">Thiết bị chưa có giọng đọc tiếng Trung phù hợp. Bạn vẫn có thể xem chữ và Pinyin.</p>}
    </> : <>
      <h3>Đã xem hết {sectionNames[code]}</h3>
      <ul>{lesson.notes.map((note) => <li key={note}>{note}</li>)}</ul>
    </>}
    <div className="pronunciation-session__navigation lesson-part-navigation" data-completion={!current}>
      <Button variant="secondary" disabled={pending || step === 0} onClick={() => onBack(code, step)}>Quay lại</Button>
      <span className="pronunciation-study-position">{current ? `${code === 'SANDHI' ? 'Ví dụ' : 'Âm'} ${step + 1} / ${total}` : `${total} / ${total}`}<small>{completionLabel ? 'Ôn tập' : pending ? 'Đang lưu…' : 'Đang học'}</small></span>
      {current ? <Button variant="primary" disabled={pending} onClick={() => onNext(code, step)}>{pending ? 'Đang lưu…' : 'Tiếp theo'}</Button>
        : <Button variant="primary" disabled={pending} onClick={() => onComplete(sectionId)}>{pending ? 'Đang lưu…' : completionLabel ?? `Hoàn thành ${sectionNames[code]}`}</Button>}
    </div>
  </Surface><StudyAdvice topic={code}/></div>
}
