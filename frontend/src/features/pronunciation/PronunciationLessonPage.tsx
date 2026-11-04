import { pronunciationSourcePage } from './pronunciationSourceMetadata'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { Alert, Button, LoadingState, PageHeader, StatusBadge, Surface } from '../../components/ui'
import { queryKeys } from '../../app/query/keys'
import { advancePronunciation, completeSection, finishPronunciationLesson, getPronunciationLesson } from './api'
import { invalidatePronunciationCompletion } from './invalidation'
import { pronunciationContent, useMandarinSpeech, type PronunciationCode } from './pronunciationData'
import { Companion } from '../../components/academy/Companion'
import { AcademyIcon } from '../../components/academy/AcademyIcon'
import { PronunciationSource } from './PronunciationSource'
import { ToneDiagram } from './ToneDiagram'

const sectionNames: Record<PronunciationCode, string> = { INITIALS: 'thanh mẫu', FINALS: 'vận mẫu', TONES: 'thanh điệu' }

export function PronunciationLessonPage() {
  const [review, setReview] = useState<{ index: number; step: number } | null>(null)
  const [viewedStep, setViewedStep] = useState<{ code: PronunciationCode; step: number } | null>(null)
  const client = useQueryClient()
  const navigate = useNavigate()
  const { voiceAvailable, speak } = useMandarinSpeech()
  const lesson = useQuery({ queryKey: queryKeys.pronunciationLesson, queryFn: getPronunciationLesson })
  const refresh = () => client.invalidateQueries({ queryKey: queryKeys.pronunciationLesson })
  const advance = useMutation({
    mutationFn: ({ code, step }: { code: PronunciationCode; step: number }) => advancePronunciation(code, step),
    retry: false,
    onSuccess: (state) => { if (state) client.setQueryData(queryKeys.pronunciationLesson, state) },
    onError: refresh,
  })
  const completeSectionMutation = useMutation({
    mutationFn: completeSection,
    retry: false,
    onSuccess: () => invalidatePronunciationCompletion(client),
    onError: refresh,
  })
  const finish = useMutation({
    mutationFn: finishPronunciationLesson,
    retry: false,
    onSuccess: async () => { await invalidatePronunciationCompletion(client); await navigate('/pronunciation') },
    onError: refresh,
  })
  const pending = advance.isPending || completeSectionMutation.isPending || finish.isPending
  const failedAction = advance.isError || completeSectionMutation.isError || finish.isError

  return <section className="learner-page pronunciation-page pronunciation-session screen" aria-labelledby="page-title">
    <PageHeader title="Bài học phát âm" titleId="page-title" back={<Link to="/pronunciation">← Trở về lộ trình học</Link>}
      description="Cùng Bo học thanh mẫu, vận mẫu và thanh điệu từ giáo trình HSK1. Tiến độ được lưu theo tài khoản sau mỗi bước." />
    {lesson.isPending && <LoadingState>Đang tải bài học…</LoadingState>}
    {lesson.isError && !lesson.data && <Alert role="alert" tone="error" action={<Button onClick={() => void lesson.refetch()}>Thử lại</Button>}>Không thể tải bài học phát âm.</Alert>}
    {failedAction && <Alert role="alert" tone="error">Không thể lưu bước học. Tiến độ mới nhất đang được tải lại; vui lòng thử lại.</Alert>}
    {lesson.data && <>
      <ol className="pronunciation-session__sections" aria-label="Các phần của bài học">{lesson.data.sections.map((section, index) => <li key={section.code}>
        <span>{index + 1}. {sectionNames[section.code]}</span>
        <span className="pronunciation-session__section-actions"><StatusBadge tone={section.completed_at ? 'success' : section.code === lesson.data?.current_section ? 'info' : 'neutral'}>{section.completed_at ? 'Đã xong' : section.code === lesson.data?.current_section ? 'Đang học' : 'Chưa học'}</StatusBadge>
          {section.completed_at && <button type="button" className="pronunciation-session__review-link" onClick={() => setReview({ index, step: 0 })}>Ôn {sectionNames[section.code]}</button>}</span>
      </li>)}</ol>

      {review && lesson.data.sections[review.index] ? <>
        <p role="status" className="pronunciation-session__review-note">Đang ôn tập · Tiến độ đã hoàn thành được giữ nguyên. <button type="button" className="pronunciation-session__review-link" onClick={() => setReview(null)}>Kết thúc ôn tập</button></p>
        <PronunciationStep code={lesson.data.sections[review.index].code} step={review.step} total={lesson.data.sections[review.index].total_steps}
          sectionId={lesson.data.sections[review.index].id} pending={false} voiceAvailable={voiceAvailable} speak={speak}
          onBack={() => setReview((current) => current ? { ...current, step: Math.max(0, current.step - 1) } : null)}
          onNext={() => setReview((current) => current ? { ...current, step: current.step + 1 } : null)}
          onComplete={() => setReview((current) => current && lesson.data?.sections[current.index + 1]?.completed_at ? { index: current.index + 1, step: 0 } : null)} />
      </> : lesson.data.completed_at ? <Surface as="section" className="pronunciation-session__card">
        <Companion pose="celebrate" className="academy-pronunciation-celebrate"/><h2>Bài học đã hoàn thành</h2><p>Bo chúc mừng bạn! Bạn có thể ôn lại bất cứ lúc nào mà không làm thay đổi tiến độ đã lưu.</p>
        <Button variant="primary" onClick={() => setReview({ index: 0, step: 0 })}>Học lại từ đầu</Button>{' '}
        <Link className="learner-link-action" to="/pronunciation">Trở về lộ trình học</Link>
      </Surface> : lesson.data.can_finish ? <Surface as="section" className="pronunciation-session__card">
        <Companion pose="celebrate" className="academy-pronunciation-celebrate"/><h2>Đã hoàn thành ba phần</h2><p>Hoàn thành bài học để lưu kết quả và mở HSK 1.</p>
        <Button variant="primary" disabled={pending} onClick={() => finish.mutate()}>{finish.isPending ? 'Đang lưu…' : 'Hoàn thành bài học'}</Button>
      </Surface> : lesson.data.current_section && <PronunciationStep
        code={lesson.data.current_section}
        step={viewedStep?.code === lesson.data.current_section ? Math.min(viewedStep.step, lesson.data.step_index) : lesson.data.step_index}
        savedStep={lesson.data.step_index}
        total={lesson.data.total_steps}
        sectionId={lesson.data.sections.find((section) => section.code === lesson.data?.current_section)?.id}
        pending={pending}
        voiceAvailable={voiceAvailable}
        speak={speak}
        onBack={(code, step) => setViewedStep({ code, step: step - 1 })}
        onNext={(code, step) => {
          if (step < lesson.data!.step_index) setViewedStep({ code, step: step + 1 })
          else { setViewedStep(null); advance.mutate({ code, step }) }
        }}
        onComplete={(id) => completeSectionMutation.mutate(id)}
      />}
    </>}
  </section>
}

function PronunciationStep({ code, step, savedStep, total, sectionId, pending, voiceAvailable, speak, onBack, onNext, onComplete }: {
  code: PronunciationCode; step: number; total: number; sectionId: string | undefined; pending: boolean
  savedStep?: number
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
      <span>{Math.min(step + 1, total)} / {total}</span></div>
    <progress aria-label={`Tiến độ ${sectionNames[code]}`} max={total} value={savedStep ?? step} />
    {current ? <>
      <p>{lesson.intro}</p>
      <p className="pronunciation-session__group">{current.group.title}</p>
      <div className="pronunciation-session__sound academy-sound-stage" aria-live="polite">
        <div className="academy-phonetic-identity">
        <strong className="pronunciation-session__symbol">{current.sound.symbol}</strong>
        <span className="academy-sound-label">{code==='TONES'?'Đường đi của giọng':'Âm đang học'}</span>
        {code==='TONES'&&<ToneDiagram tone={step}/>}
        </div><div className="academy-sound-example"><span className="academy-sound-hanzi" lang="zh-Hans">{current.sound.hanzi}</span><span className="academy-sound-pinyin">{current.sound.pinyin}</span><Button variant="secondary" disabled={!voiceAvailable} onClick={() => speak(current.sound)}><AcademyIcon name="sound" size={19}/>Nghe phát âm</Button><small>Giọng đọc của thiết bị</small></div>
      </div>
      <div className="academy-articulation-note"><Companion pose="truc" decorative/><div><h3>Trúc nhắc nhỏ</h3><p>{current.group.tip}</p></div></div>
      {!voiceAvailable && <p role="status">Thiết bị chưa có giọng đọc tiếng Trung phù hợp. Bạn vẫn có thể xem chữ và Pinyin.</p>}
    </> : <>
      <h3>Đã xem hết {sectionNames[code]}</h3>
      <ul>{lesson.notes.map((note) => <li key={note}>{note}</li>)}</ul>
    </>}
    <PronunciationSource code={code} symbol={current?.sound.symbol}/>
    <div className="pronunciation-session__navigation">
      <Button variant="secondary" disabled={pending || step === 0} onClick={() => onBack(code, step)}>Quay lại</Button>
      {current ? <Button variant="primary" disabled={pending} onClick={() => onNext(code, step)}>{pending ? 'Đang lưu…' : 'Tiếp theo'}</Button>
        : <Button variant="primary" disabled={pending} onClick={() => onComplete(sectionId)}>{pending ? 'Đang lưu…' : `Hoàn thành ${sectionNames[code]}`}</Button>}
    </div>
  </Surface><aside className="academy-pronunciation-companion"><Companion pose={pending?'think':current?'guide':'celebrate'}/><h2>{current?'Bo đi cùng bạn.':'Thêm một bước vững vàng.'}</h2><p>{current?'Quan sát chữ, đọc pinyin, rồi tự luyện lại theo hướng dẫn. Mỗi bước nhỏ đều đáng ghi nhận.':'Bạn đã xem hết phần này. Đọc lại các lưu ý rồi xác nhận hoàn thành để chuyển sang phần tiếp theo.'}</p><div className="academy-pronunciation-reference"><AcademyIcon name="book" size={18}/><span>Giáo trình HSK1<br/>{pronunciationSourcePage(code,current?.sound.symbol)}</span></div><Companion pose="but" decorative className="academy-pronunciation-but"/><p className="academy-small-note">Bạn có thể quay lại những âm đã học mà không làm mất tiến độ đã lưu.</p></aside></div>
}
