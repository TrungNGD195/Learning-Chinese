import {useEffect,useRef,useState} from 'react'
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query'
import {Link,useBeforeUnload,useBlocker,useNavigate,useParams} from 'react-router'
import {Alert,Button,Dialog,LoadingState} from '../../components/ui'
import {Companion,VocabularyIllustration} from '../../components/academy/Companion'
import {AcademyIcon} from '../../components/academy/AcademyIcon'
import {CurriculumCover} from '../curriculum/CurriculumCover'
import {useMandarinAudio} from '../../lib/audio/mandarinAudio'
import {ApiError} from '../../lib/api/errors'
import {getExamInfo,getExamHistory,startExam,getExamSession,saveExamAnswer,finishExamSection,selfReviewExam,type ExamSession,type ExamQuestion} from './api'
import '../../styles/hsk-exam.css'

export function HskMockExamPage(){
 const {hskLevel,examAttemptId}=useParams()
 return examAttemptId?<ExamAttemptPage key={examAttemptId} id={examAttemptId}/>:<ExamOverview key={hskLevel} level={Number(hskLevel)}/>
}

function ExamOverview({level}:{level:number}){
 const navigate=useNavigate()
 const info=useQuery({queryKey:['hsk-exam-info',level],queryFn:()=>getExamInfo(level),enabled:[1,2,3].includes(level)})
 const history=useQuery({queryKey:['hsk-exam-history',level],queryFn:()=>getExamHistory(level),enabled:[1,2,3].includes(level)})
 const start=useMutation({mutationFn:()=>startExam(level),onSuccess:data=>navigate(`/hsk-exam-attempts/${data.id}`)})
 if(![1,2,3].includes(level))return <Alert tone="error">Không có bài thi cho cấp độ này.</Alert>
 if(info.isPending)return <LoadingState>Đang chuẩn bị phòng thi…</LoadingState>
 if(info.isError)return <Alert tone="error" action={<Button onClick={()=>void info.refetch()}>Thử lại</Button>}>Chưa tải được thông tin bài thi.</Alert>
 const paper=info.data
 const active=history.data?.find(a=>a.status==='IN_PROGRESS')
 const unlocked=paper.access?.unlocked===true
 return <section className="hsk-exam-page screen" aria-labelledby="page-title">
  <Link className="learner-link-action" to={`/hsk/${level}`}>← HSK {level}</Link>
  <header className="exam-heading"><div><h1 id="page-title">{paper.title}</h1><p>Một lượt thi trọn vẹn, để biết bạn đã đi được bao xa.</p></div><Companion pose="but" decorative/></header>
  {!unlocked&&<section className="exam-locked" aria-labelledby="exam-locked-title"><AcademyIcon name="lock" size={28}/><div><h2 id="exam-locked-title">Bài thi chưa mở</h2><p>Hoàn thành tất cả bài học HSK {level}, gồm lý thuyết và luyện tập đạt từ 80%, để mở bài thi.</p><p>{paper.access?.completed_lessons??0}/{paper.access?.total_lessons??0} bài đã hoàn thành.</p><Link className="learner-link-action" to={`/hsk/${level}`}>Tiếp tục học HSK {level}</Link></div></section>}
  <div className="exam-introduction"><div><h2>Sẵn sàng thử sức?</h2><p><strong>{paper.total_questions} câu</strong> · {paper.sections.reduce((sum,s)=>sum+s.duration_seconds,0)/60} phút · Tối đa {paper.max_score} điểm</p><p>Ngưỡng tham khảo: {paper.pass_score}/{paper.max_score}. Điểm mô phỏng được quy đổi theo từng kỹ năng, không phải điểm chứng chỉ chính thức.</p><p>Thứ tự câu trong mỗi dạng bài và các lựa chọn sẽ đổi theo tài khoản, theo lượt làm. Các phần thi vẫn giữ đúng trình tự.</p>
  <p>{level<3?'Có pinyin hỗ trợ cho HSK 1–2.':'Không có pinyin hỗ trợ; riêng 5 câu viết chữ vẫn có gợi âm theo đề.'} Chỉ xem đáp án và giải thích sau khi nộp.</p>
  {level===3&&<p>Năm câu đặt câu theo tranh được đối chiếu với đáp án mẫu và <strong>tự đánh giá</strong>. Kết quả ghi rõ phần tự chấm.</p>}
  <p>Phần nghe dùng giọng tiếng Trung đang có trên thiết bị, cùng hệ thống nghe của bài học. Kiểm tra âm lượng trước khi bắt đầu.</p>
  <ExamSoundCheck/>
  <p>Thời gian vẫn chạy khi rời trang. Câu trả lời đã lưu và đề của lượt đang làm được giữ khi quay lại.</p>
  {start.isError&&<Alert tone="error">Chưa mở được lượt thi. Bạn hãy thử lại.</Alert>}
  <Button variant="primary" disabled={!unlocked||start.isPending} onClick={()=>start.mutate()}>{!unlocked?'Hoàn thành HSK để mở bài thi':start.isPending?'Đang mở đề…':active?'Tiếp tục lượt đang làm':'Bắt đầu thi thử'}</Button></div>
  <ol className="exam-section-summary">{paper.sections.map((s,i)=><li key={s.id}><span>{i+1}</span><div><h3>{s.label}</h3><p>{s.question_count} câu · {s.duration_seconds/60} phút{s.id==='listening'?' (gồm thời gian kiểm tra đáp án)':''}</p></div></li>)}</ol></div>
  <section className="exam-history" aria-labelledby="exam-history-title"><h2 id="exam-history-title">Các lượt thi của bạn</h2>{history.isPending?<LoadingState>Đang tải các lượt thi…</LoadingState>:history.isError?<Alert tone="error" action={<Button onClick={()=>void history.refetch()}>Thử lại</Button>}>Chưa tải được lượt thi.</Alert>:!history.data.length?<p>Chưa có lượt thi. Bạn có thể làm lại nhiều lần để theo dõi tiến bộ.</p>:<ol>{history.data.map(row=><li key={row.id}><Link to={`/hsk-exam-attempts/${row.id}`}><strong>Lượt {row.attempt_number}</strong><span>{row.status==='IN_PROGRESS'?'Đang làm':row.score===null?'Còn phần tự đánh giá':`${row.score}/${row.max_score} điểm`}{row.includes_self_assessment?' · Có phần tự chấm':''}</span><AcademyIcon name="arrow" size={20}/></Link></li>)}</ol>}</section>
 </section>
}

function ExamAttemptPage({id}:{id:string}){
 const queryClient=useQueryClient()
 const key=['hsk-exam-session',id]
 const session=useQuery({queryKey:key,queryFn:()=>getExamSession(id),refetchInterval:query=>query.state.data?.status==='IN_PROGRESS'?15000:false})
 const [error,setError]=useState<string|null>(null)
 const advance=useMutation({mutationFn:(index:number)=>finishExamSection(id,index),onSuccess:data=>{queryClient.setQueryData(key,data);void queryClient.invalidateQueries({queryKey:['hsk-exam-history',data.level]})},onError:()=>setError('Chưa chuyển được phần thi. Câu trả lời đã lưu vẫn được giữ; hãy thử lại.')})
 const active=session.data?.status==='IN_PROGRESS'
 const blocker=useBlocker(!!active)
 useBeforeUnload(event=>{if(active){event.preventDefault();event.returnValue=''}})
 if(session.isPending)return <LoadingState>Đang tải đề và câu trả lời đã lưu…</LoadingState>
 if(session.error instanceof ApiError&&session.error.code==='HSK_EXAM_LOCKED')return <section className="hsk-exam-page screen"><h1>Bài thi chưa mở</h1><p>Hoàn thành tất cả bài học của cấp độ HSK này trước khi tiếp tục bài thi.</p><Link className="learner-link-action" to="/pronunciation">Về giáo trình</Link></section>
 if(session.isError&&!session.data)return <Alert tone="error" action={<Button onClick={()=>void session.refetch()}>Thử lại</Button>}>Chưa tải được lượt thi.</Alert>
 const data=session.data!
 return <section className="hsk-exam-page screen" aria-labelledby="page-title"><Link className="learner-link-action" to={`/hsk/${data.level}/exam`}>← Phòng thi HSK {data.level}</Link><header className="exam-heading"><div><h1 id="page-title">{data.info.title}</h1><p>Lượt {data.attempt_number}{data.status==='GRADED'?' · Đã nộp bài':''}</p></div></header>
  {(error||session.isError)&&<Alert tone="error" action={<Button onClick={()=>{setError(null);void session.refetch()}}>Thử lại</Button>}>{error??'Kết nối bị gián đoạn. Thời gian trên server vẫn tiếp tục chạy.'}</Alert>}
  {data.status==='GRADED'?<ExamResult session={data} onUpdate={next=>queryClient.setQueryData(key,next)}/>:<ExamSection key={`${data.id}:${data.section_index}`} session={data} receivedAt={session.dataUpdatedAt} pending={advance.isPending} refresh={()=>void session.refetch()} onUpdate={next=>queryClient.setQueryData(key,next)} onFinish={()=>{setError(null);advance.mutate(data.section_index)}} onError={setError}/>}
  <Dialog open={blocker.state==='blocked'} title="Rời phòng thi?" cancelLabel="Tiếp tục làm" confirmLabel="Rời trang" onCancel={()=>blocker.reset?.()} onConfirm={()=>blocker.proceed?.()}><p>Những câu đã lưu được giữ lại. Thời gian vẫn chạy và các phần hết giờ sẽ tự đóng.</p></Dialog>
 </section>
}

function ExamSection({session,receivedAt,pending,refresh,onUpdate,onFinish,onError}:{session:ExamSession;receivedAt:number;pending:boolean;refresh:()=>void;onUpdate:(data:ExamSession)=>void;onFinish:()=>void;onError:(value:string|null)=>void}){
 const [index,setIndex]=useState(0),[drafts,setDrafts]=useState<Record<string,string>>({}),[saving,setSaving]=useState(false),[confirm,setConfirm]=useState(false),[clock,setClock]=useState(()=>Date.now()),[unsavedCount,setUnsavedCount]=useState(0)
 const queue=useRef<Promise<void>>(Promise.resolve()),expired=useRef(false),unsaved=useRef<Record<string,string>>({})
 const textTimer=useRef<ReturnType<typeof setTimeout>|undefined>(undefined)
 useEffect(()=>()=>clearTimeout(textTimer.current),[])
 const section=session.info.sections[session.section_index],q=session.questions[index]
 const remaining=Math.max(0,Math.ceil((Date.parse(session.section_deadline!)-Date.parse(session.server_time)-(clock-receivedAt))/1000))
 useEffect(()=>{const timer=setInterval(()=>setClock(Date.now()),1000);return()=>clearInterval(timer)},[])
 useEffect(()=>{if(remaining===0&&!expired.current){expired.current=true;refresh()}},[remaining,refresh])
 const value=(question:ExamQuestion)=>drafts[question.id]??session.answers[question.id]??''
 function save(question:ExamQuestion,answer:string){
  clearTimeout(textTimer.current)
  setDrafts(current=>({...current,[question.id]:answer}));unsaved.current[question.id]=answer
  setUnsavedCount(Object.keys(unsaved.current).length)
  setSaving(true)
  queue.current=queue.current.then(async()=>{
   try{
    const next=await saveExamAnswer(session.id,{section_index:session.section_index,question_id:question.id,answer})
    if(unsaved.current[question.id]===answer)delete unsaved.current[question.id]
    onUpdate(next);onError(null)
   }catch{onError('Có câu trả lời chưa lưu được. Nội dung vẫn ở trên màn hình; bấm “Lưu lại” khi có kết nối.');throw new Error('SAVE_FAILED')}
  }).catch(()=>{}).finally(()=>{setSaving(Object.keys(unsaved.current).length>0);setUnsavedCount(Object.keys(unsaved.current).length)})
 }
 function editText(question:ExamQuestion,answer:string){
  setDrafts(current=>({...current,[question.id]:answer}));setSaving(true)
  clearTimeout(textTimer.current);textTimer.current=setTimeout(()=>save(question,answer),700)
 }
 async function leaveQuestion(next:number){if(q.type!=='choice'&&value(q)!==(session.answers[q.id]??''))save(q,value(q));await queue.current;setIndex(next)}
 async function finishSection(){
  if(q.type!=='choice'&&value(q)!==(session.answers[q.id]??''))save(q,value(q))
  await queue.current
  if(Object.keys(unsaved.current).length){onError('Hãy lưu lại câu trả lời trước khi kết thúc phần thi.');setConfirm(false);return}
  setConfirm(false);onFinish()
 }
 const offset=session.info.sections.slice(0,session.section_index).reduce((sum,s)=>sum+s.question_count,0)
 const answered=session.questions.filter(question=>value(question).trim()).length
 return <><div className="exam-toolbar"><ol aria-label="Các phần thi">{session.info.sections.map((s,i)=><li key={s.id} aria-current={i===session.section_index?'step':undefined} data-finished={i<session.section_index}>{s.label}</li>)}</ol><div className="exam-timer" role="timer" aria-label="Thời gian còn lại" data-urgent={remaining<60}>{String(Math.floor(remaining/60)).padStart(2,'0')}:{String(remaining%60).padStart(2,'0')}</div></div>
 <div className="exam-workspace"><aside className="exam-question-nav"><h2>{section.label}</h2><p>{answered}/{session.questions.length} câu đã trả lời</p><div>{session.questions.map((question,i)=><button type="button" key={question.id} aria-label={`Câu ${offset+i+1}${value(question)?', đã trả lời':''}`} aria-current={index===i?'step':undefined} data-answered={!!value(question)} disabled={pending} onClick={()=>void leaveQuestion(i)}>{offset+i+1}</button>)}</div><p role="status">{saving?'Đang lưu hoặc có thay đổi chưa lưu…':'Các câu đã trả lời được lưu trên server.'}</p>{unsavedCount>0&&<Button onClick={()=>{for(const [id,text] of Object.entries(unsaved.current)){const question=session.questions.find(item=>item.id===id);if(question)save(question,text)}}}>Lưu lại</Button>}</aside>
 <article className="exam-question-panel"><div className="exam-question-meta"><span>Câu {offset+index+1} / {session.info.total_questions}</span><span>Phần {q.part} · {section.label}</span></div>
 <ExamQuestionBody key={q.id} question={q} answer={value(q)} disabled={pending||remaining===0} onChange={answer=>q.type==='choice'?save(q,answer):editText(q,answer)} onBlur={()=>{if(q.type!=='choice'&&value(q)!==(session.answers[q.id]??''))save(q,value(q))}}/>
 <div className="exam-question-actions"><Button disabled={index===0||pending} onClick={()=>void leaveQuestion(index-1)}>Quay lại</Button>{index<session.questions.length-1?<Button variant="primary" disabled={pending} onClick={()=>void leaveQuestion(index+1)}>Tiếp theo</Button>:<Button variant="primary" disabled={pending} onClick={()=>setConfirm(true)}>{session.section_index===session.info.sections.length-1?'Nộp bài thi':'Kết thúc phần này'}</Button>}</div>
 <p className="exam-rule-note">Bạn có thể sửa câu trả lời trong phần đang làm. Phần đã kết thúc sẽ đóng; đáp án chỉ hiện sau khi nộp toàn bộ bài.</p></article></div>
 <Dialog open={confirm} title={session.section_index===session.info.sections.length-1?'Nộp bài thi?':'Kết thúc phần thi?'} cancelLabel="Kiểm tra lại" confirmLabel={session.section_index===session.info.sections.length-1?'Nộp bài':'Sang phần tiếp theo'} onCancel={()=>setConfirm(false)} onConfirm={()=>void finishSection()}><p>Đã trả lời {answered}/{session.questions.length} câu. Câu bỏ trống nhận 0 điểm. Bạn sẽ không thể quay lại sửa phần này.</p></Dialog></>
}

function ExamSoundCheck(){
 const audio=useMandarinAudio()
 return <div className="exam-sound-check"><Button disabled={!audio.voiceAvailable||audio.isSpeaking} onClick={()=>audio.speak({hanzi:'你好。祝你考试顺利。',rate:1})}><AcademyIcon name="sound" size={20}/>{audio.isSpeaking?'Đang nghe thử…':'Kiểm tra âm thanh'}</Button>{!audio.voiceAvailable&&<p>Thiết bị chưa có giọng tiếng Trung. Hãy bật giọng Mandarin để làm phần nghe.</p>}{audio.speechError&&<p role="status">{audio.speechError}</p>}</div>
}

function ExamListening({text}:{text:string}){
 const audio=useMandarinAudio(),[plays,setPlays]=useState(0)
 return <div className="exam-listening"><AcademyIcon name="sound" size={28}/><div><strong>Nghe câu hỏi</strong><p>Nghe tối đa hai lượt trước khi chọn đáp án.</p></div><Button disabled={!audio.voiceAvailable||audio.isSpeaking||plays>=2} onClick={()=>{setPlays(n=>n+1);audio.speak({hanzi:text,rate:1})}}>{audio.isSpeaking?'Đang phát…':`Nghe ${plays}/2`}</Button>{(!audio.voiceAvailable||audio.speechError)&&<p role="status">{audio.speechError??'Thiết bị chưa có giọng tiếng Trung. Hãy kiểm tra cài đặt giọng nói.'}</p>}</div>
}

function ExamQuestionBody({question:q,answer,disabled,onChange,onBlur}:{question:ExamQuestion;answer:string;disabled:boolean;onChange:(value:string)=>void;onBlur:()=>void}){
 return <><h2 className="exam-prompt" lang="zh-Hans">{q.prompt}</h2>{q.prompt_pinyin&&<p className="exam-pinyin">{q.prompt_pinyin}</p>}
 {q.audio_text&&<ExamListening text={q.audio_text}/>}
 {q.reading_text&&<div className="exam-reading">{q.reading_text_pinyin&&<p className="exam-pinyin">{q.reading_text_pinyin}</p>}<p lang="zh-Hans">{q.reading_text}</p></div>}
 {q.image_hanzi&&<div className="exam-picture"><VocabularyIllustration hanzi={q.image_hanzi}/></div>}
 {q.illustration_topic&&<div className="exam-writing-picture"><CurriculumCover topic={q.illustration_topic}/></div>}
 {q.phonetic_hint&&<p className="exam-phonetic-hint">Gợi âm của chữ cần điền: <strong>{q.phonetic_hint}</strong></p>}
 {q.type==='choice'?<fieldset className="exam-options" disabled={disabled}><legend className="sr-only">Chọn đáp án</legend>{q.options.map((option,i)=><label className="exam-option" key={option.id}><input type="radio" name={q.id} checked={answer===option.id} onChange={()=>onChange(option.id)}/><span className="exam-option-letter">{String.fromCharCode(65+i)}</span><span>{option.illustration_topic?<span className="exam-option-scene"><CurriculumCover topic={option.illustration_topic}/></span>:option.image_hanzi?<VocabularyIllustration hanzi={option.image_hanzi}/>:<>{option.pinyin&&<small className="exam-pinyin">{option.pinyin}</small>}<span lang="zh-Hans">{option.text}</span></>}</span></label>)}</fieldset>:<label className="exam-writing-input">{q.type==='fill'?'Điền chữ Hán còn thiếu':'Câu trả lời của bạn'}{q.type==='fill'?<input type="text" value={answer} disabled={disabled} maxLength={20} onChange={event=>onChange(event.target.value)} onBlur={onBlur}/>:<textarea value={answer} disabled={disabled} maxLength={500} rows={4} onChange={event=>onChange(event.target.value)} onBlur={onBlur}/>}<small>Dùng bàn phím tiếng Trung để nhập chữ Hán.</small></label>}</>
}

function ExamResult({session,onUpdate}:{session:ExamSession;onUpdate:(value:ExamSession)=>void}){
 const result=session.result!,[onlyWrong,setOnlyWrong]=useState(false)
 const review=useMutation({mutationFn:(body:Parameters<typeof selfReviewExam>[1])=>selfReviewExam(session.id,body),onSuccess:onUpdate})
 return <div className="exam-results"><section className="exam-score"><div><h2>Kết quả bài thi thử</h2><strong>{result.score===null?`${result.score_min}–${result.score_max}`:result.score}<small> / {result.max_score}</small></strong><p>{result.pending_self_reviews?`Còn ${result.pending_self_reviews} câu viết cần tự đánh giá.`:result.passed?'Đạt ngưỡng tham khảo':'Chưa đạt ngưỡng tham khảo'}</p><p>Ngưỡng tham khảo: {result.pass_score} điểm. Điểm mô phỏng, không phải kết quả thi chính thức.</p>{result.includes_self_assessment&&<p><strong>Có phần tự chấm:</strong> 5 câu đặt câu theo tranh được bạn đánh giá theo đáp án và tiêu chí, không được AI hoặc giáo viên xác nhận.</p>}<Link className="learner-link-action" to={`/hsk/${session.level}/exam`}>Về phòng thi / Làm lượt mới</Link></div><Companion pose={result.passed?'celebrate':'encourage'} decorative/></section>
 <div className="exam-section-results">{result.sections.map(s=><section key={s.id}><h3>{s.label}</h3><strong>{s.score===null?`${s.score_min}–${s.score_max}`:s.score}/100</strong><p>{s.correct}/{s.total} câu đạt điểm trọn vẹn</p></section>)}</div>
 <div className="exam-review-heading"><h2>Đáp án và giải thích</h2><Button aria-pressed={onlyWrong} onClick={()=>setOnlyWrong(value=>!value)}>{onlyWrong?'Xem tất cả câu':'Chỉ xem câu cần ôn'}</Button></div>
 {review.isError&&<Alert tone="error">Chưa lưu được tự đánh giá. Hãy thử lại.</Alert>}
 <ol className="exam-answer-review">{result.questions.map((q,index)=>onlyWrong&&q.is_correct===true?null:<li key={q.id} data-correct={q.is_correct}><header><h3>Câu {index+1} · {q.section_label}</h3><span>{q.earned_fraction===null?'Chờ tự đánh giá':q.is_correct?'Đúng':q.earned_fraction===0.5?'Đúng một phần':'Chưa đúng'}</span></header>{q.prompt_pinyin&&<p className="exam-pinyin">{q.prompt_pinyin}</p>}<p lang="zh-Hans">{q.prompt}</p>{q.reading_text&&<p lang="zh-Hans">{q.reading_text}</p>}{q.audio_text&&<details><summary>Bản chữ của phần nghe</summary><p lang="zh-Hans">{q.audio_text}</p></details>}{q.illustration_topic&&<div className="exam-review-picture"><CurriculumCover topic={q.illustration_topic}/></div>}<p>Bạn trả lời: <strong lang="zh-Hans">{q.answer_text||'Bỏ trống'}</strong></p><p className="exam-correct-answer">{q.type==='sentence'?'Đáp án mẫu':'Đáp án'}: <strong lang="zh-Hans">{q.reference_answer}</strong></p><p>{q.explanation}</p>{q.type==='sentence'&&q.answer&&<div className="exam-self-review"><p>Tự đánh giá: câu dùng đúng từ được cho, đúng ý tranh và có ngữ pháp hợp lý. Bạn không cần viết giống hệt đáp án mẫu.</p><div>{([[1,'Đúng ý và đúng ngữ pháp'],[0.5,'Đúng một phần'],[0,'Cần ôn lại']] as const).map(([rating,label])=><Button key={rating} disabled={review.isPending} aria-pressed={q.self_rating===rating} onClick={()=>review.mutate({question_id:q.id,rating})}>{label}</Button>)}</div></div>}</li>)}</ol></div>
}
