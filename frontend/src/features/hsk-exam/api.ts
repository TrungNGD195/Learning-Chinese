import {apiClient} from '../../lib/api/client'
import type {components} from '../../types/api.generated'
export type ExamInfo=components['schemas']['ExamInfo']
export type ExamSession=components['schemas']['ExamSession']
export type ExamQuestion=components['schemas']['ExamQuestion']
export type ExamHistoryItem=components['schemas']['ExamHistoryItem']
export const getExamInfo=(level:number)=>apiClient<ExamInfo>({path:`/hsk-mock-exams/${level}`})
export const getExamHistory=(level:number)=>apiClient<ExamHistoryItem[]>({path:`/hsk-mock-exams/${level}/attempts`})
export const startExam=(level:number)=>apiClient<ExamSession>({method:'POST',path:`/hsk-mock-exams/${level}/attempts`})
export const getExamSession=(id:string)=>apiClient<ExamSession>({path:`/hsk-mock-exam-attempts/${encodeURIComponent(id)}`})
export const saveExamAnswer=(id:string,body:components['schemas']['SaveAnswer'])=>apiClient<ExamSession,typeof body>({method:'PUT',path:`/hsk-mock-exam-attempts/${encodeURIComponent(id)}/answer`,body})
export const finishExamSection=(id:string,section_index:number)=>apiClient<ExamSession,{section_index:number}>({method:'POST',path:`/hsk-mock-exam-attempts/${encodeURIComponent(id)}/next-section`,body:{section_index}})
export const selfReviewExam=(id:string,body:components['schemas']['SelfReview'])=>apiClient<ExamSession,typeof body>({method:'POST',path:`/hsk-mock-exam-attempts/${encodeURIComponent(id)}/self-review`,body})
