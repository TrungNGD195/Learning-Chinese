import {useQuery} from '@tanstack/react-query'
import {queryKeys} from '../../app/query/keys'
import {AcademyIcon} from '../../components/academy/AcademyIcon'
import {LessonEntryLink} from '../journey/LessonEntryLink'
import {continueLearningPath,type ContinueLearningTarget} from '../dashboard/continueLearning'
import {getLesson} from '../lesson/api'
import {getLessonProgress} from '../progress/api'
import {vocabularyPath} from '../lesson/vocabularyRoutes'
import {lessonPartPath} from '../lesson/lessonRoutes'

export function ResumeLearningLink({target}:{target:ContinueLearningTarget}){
 const id=target.type==='LESSON'?target.lesson_id:''
 const lesson=useQuery({queryKey:queryKeys.lesson(id),queryFn:()=>getLesson(id),enabled:!!id})
 const progress=useQuery({queryKey:queryKeys.lessonProgress(id),queryFn:()=>getLessonProgress(id),enabled:!!id&&!!lesson.data})
 let destination=continueLearningPath(target)
 if(id&&lesson.data&&progress.data){
  const word=[...lesson.data.vocabulary].sort((a,b)=>a.order_index-b.order_index).find(item=>!progress.data.vocabulary.some(row=>row.id===item.id&&row.viewed))
  if(word)destination=vocabularyPath(id,word.id)
  else if(lesson.data.grammar.some(item=>!progress.data.grammar.some(row=>row.id===item.id&&row.viewed)))destination=lessonPartPath(id,'grammar')
  else if((lesson.data.readings??[]).some(item=>!(progress.data.readings??[]).some(row=>row.id===item.id&&row.completed)))destination=lessonPartPath(id,'readings')
  else destination=lessonPartPath(id,'practice')
 }
 return <LessonEntryLink className="lc-inline-button lc-resume" to={destination}>Tiếp tục bài đang học<AcademyIcon name="arrow" size={17}/></LessonEntryLink>
}
