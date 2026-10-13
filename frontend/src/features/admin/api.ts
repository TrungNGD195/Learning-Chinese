import { apiClient } from '../../lib/api/client'
import type {
  MultipartRequestBodyOf,
  QueryParametersOf,
  RequestBodyOf,
  ResponseBodyOf,
} from '../../lib/api/types'

const hskLevelsPath = '/api/v1/admin/hsk-levels'
const hskLevelPath = '/api/v1/admin/hsk-levels/{hsk_id}'
const curriculumPath = '/api/v1/admin/hsk-levels/{hsk_id}/curriculum'
const lessonsPath = '/api/v1/admin/lessons'
const lessonPath = '/api/v1/admin/lessons/{lesson_id}'
const publishLessonPath = '/api/v1/admin/lessons/{lesson_id}/publish'
const archiveLessonPath = '/api/v1/admin/lessons/{lesson_id}/archive'
const vocabularyPath = '/api/v1/admin/lessons/{lesson_id}/vocabulary'
const vocabularyItemPath = '/api/v1/admin/lessons/{lesson_id}/vocabulary/{item_id}'
const grammarPath = '/api/v1/admin/lessons/{lesson_id}/grammar'
const grammarItemPath = '/api/v1/admin/lessons/{lesson_id}/grammar/{item_id}'
const assessmentsPath = '/api/v1/admin/assessments'
const generateAssessmentDraftPath = '/api/v1/admin/assessments/generate-draft'
const assessmentPath = '/api/v1/admin/assessments/{assessment_id}'
const questionsPath = '/api/v1/admin/assessments/{assessment_id}/questions'
const questionPath = '/api/v1/admin/assessments/{assessment_id}/questions/{question_id}'
const reviewPath = '/api/v1/admin/assessments/{assessment_id}/submit-review'
const publishAssessmentPath = '/api/v1/admin/assessments/{assessment_id}/publish'
const archiveAssessmentPath = '/api/v1/admin/assessments/{assessment_id}/archive'
const statsPath = '/api/v1/admin/stats'
const documentsPath = '/api/v1/admin/documents'
const documentPath = '/api/v1/admin/documents/{document_id}'
const documentProcessPath = '/api/v1/admin/documents/{document_id}/process'
const documentPreviewPath = '/api/v1/admin/documents/{document_id}/preview'
const documentApprovePath = '/api/v1/admin/documents/{document_id}/approve'
const documentRejectPath = '/api/v1/admin/documents/{document_id}/reject'
const documentKnowledgeRetryPath = '/api/v1/admin/documents/{document_id}/knowledge/retry'

type HskPatch = RequestBodyOf<typeof hskLevelPath, 'patch'>
type CurriculumReplace = RequestBodyOf<typeof curriculumPath, 'put'>
type LessonCreate = RequestBodyOf<typeof lessonsPath, 'post'>
type LessonPatch = RequestBodyOf<typeof lessonPath, 'patch'>
type VocabularyAttach = RequestBodyOf<typeof vocabularyPath, 'post'>
type VocabularyPatch = RequestBodyOf<typeof vocabularyItemPath, 'patch'>
type GrammarAttach = RequestBodyOf<typeof grammarPath, 'post'>
type GrammarPatch = RequestBodyOf<typeof grammarItemPath, 'patch'>
type AssessmentCreate = RequestBodyOf<typeof assessmentsPath, 'post'>
type AssessmentPatch = RequestBodyOf<typeof assessmentPath, 'patch'>
type QuestionCreate = RequestBodyOf<typeof questionsPath, 'post'>
type QuestionPatch = RequestBodyOf<typeof questionPath, 'patch'>

export type AdminLessonFilters = QueryParametersOf<typeof lessonsPath, 'get'>
export type AdminAssessmentFilters = QueryParametersOf<typeof assessmentsPath, 'get'>
export type AssessmentGenerationRequest = RequestBodyOf<typeof generateAssessmentDraftPath, 'post'>
export type AssessmentGenerationDraft = ResponseBodyOf<typeof generateAssessmentDraftPath, 'post'>
export type AdminDocumentFilters = QueryParametersOf<typeof documentsPath, 'get'>
export type AdminDocumentPage = ResponseBodyOf<typeof documentsPath, 'get'>
export type AdminDocumentListItem = AdminDocumentPage['items'][number]
export type AdminDocumentDetail = ResponseBodyOf<typeof documentPath, 'get'>
export type AdminDocumentPreview = ResponseBodyOf<typeof documentPreviewPath, 'get'>

type GeneratedDocumentUpload = MultipartRequestBodyOf<typeof documentsPath, 'post'>
export type DocumentUploadInput = Omit<GeneratedDocumentUpload, 'file'> & { file: File }

const id = (value: string) => encodeURIComponent(value)

export function listHskLevels() {
  return apiClient<ResponseBodyOf<typeof hskLevelsPath, 'get'>>({ method: 'GET', path: '/admin/hsk-levels' })
}

export function updateHskLevel(hskId: string, body: HskPatch) {
  return apiClient<ResponseBodyOf<typeof hskLevelPath, 'patch'>, HskPatch>({
    method: 'PATCH', path: `/admin/hsk-levels/${id(hskId)}`, body,
  })
}

export function getAdminCurriculum(hskId: string) {
  return apiClient<ResponseBodyOf<typeof curriculumPath, 'get'>>({
    method: 'GET', path: `/admin/hsk-levels/${id(hskId)}/curriculum`,
  })
}

export function replaceAdminCurriculum(hskId: string, body: CurriculumReplace) {
  return apiClient<ResponseBodyOf<typeof curriculumPath, 'put'>, CurriculumReplace>({
    method: 'PUT', path: `/admin/hsk-levels/${id(hskId)}/curriculum`, body,
  })
}

export function listAdminLessons(filters: AdminLessonFilters = {}) {
  return apiClient<ResponseBodyOf<typeof lessonsPath, 'get'>>({
    method: 'GET', path: '/admin/lessons', query: filters,
  })
}

export function getAdminLesson(lessonId: string) {
  return apiClient<ResponseBodyOf<typeof lessonPath, 'get'>>({
    method: 'GET', path: `/admin/lessons/${id(lessonId)}`,
  })
}

export function createAdminLesson(body: LessonCreate) {
  return apiClient<ResponseBodyOf<typeof lessonsPath, 'post'>, LessonCreate>({
    method: 'POST', path: '/admin/lessons', body,
  })
}

export function updateAdminLesson(lessonId: string, body: LessonPatch) {
  return apiClient<ResponseBodyOf<typeof lessonPath, 'patch'>, LessonPatch>({
    method: 'PATCH', path: `/admin/lessons/${id(lessonId)}`, body,
  })
}

export function publishAdminLesson(lessonId: string) {
  return apiClient<ResponseBodyOf<typeof publishLessonPath, 'post'>>({
    method: 'POST', path: `/admin/lessons/${id(lessonId)}/publish`,
  })
}

export function archiveAdminLesson(lessonId: string) {
  return apiClient<ResponseBodyOf<typeof archiveLessonPath, 'post'>>({
    method: 'POST', path: `/admin/lessons/${id(lessonId)}/archive`,
  })
}

export function listLessonVocabulary(lessonId: string) {
  return apiClient<ResponseBodyOf<typeof vocabularyPath, 'get'>>({
    method: 'GET', path: `/admin/lessons/${id(lessonId)}/vocabulary`,
  })
}

export function attachVocabulary(lessonId: string, body: VocabularyAttach) {
  return apiClient<ResponseBodyOf<typeof vocabularyPath, 'post'>, VocabularyAttach>({
    method: 'POST', path: `/admin/lessons/${id(lessonId)}/vocabulary`, body,
  })
}

export function updateLessonVocabulary(lessonId: string, itemId: string, body: VocabularyPatch) {
  return apiClient<ResponseBodyOf<typeof vocabularyItemPath, 'patch'>, VocabularyPatch>({
    method: 'PATCH', path: `/admin/lessons/${id(lessonId)}/vocabulary/${id(itemId)}`, body,
  })
}

export function detachVocabulary(lessonId: string, itemId: string) {
  return apiClient<ResponseBodyOf<typeof vocabularyItemPath, 'delete'>>({
    method: 'DELETE', path: `/admin/lessons/${id(lessonId)}/vocabulary/${id(itemId)}`,
  })
}

export function listLessonGrammar(lessonId: string) {
  return apiClient<ResponseBodyOf<typeof grammarPath, 'get'>>({
    method: 'GET', path: `/admin/lessons/${id(lessonId)}/grammar`,
  })
}

export function attachGrammar(lessonId: string, body: GrammarAttach) {
  return apiClient<ResponseBodyOf<typeof grammarPath, 'post'>, GrammarAttach>({
    method: 'POST', path: `/admin/lessons/${id(lessonId)}/grammar`, body,
  })
}

export function updateLessonGrammar(lessonId: string, itemId: string, body: GrammarPatch) {
  return apiClient<ResponseBodyOf<typeof grammarItemPath, 'patch'>, GrammarPatch>({
    method: 'PATCH', path: `/admin/lessons/${id(lessonId)}/grammar/${id(itemId)}`, body,
  })
}

export function detachGrammar(lessonId: string, itemId: string) {
  return apiClient<ResponseBodyOf<typeof grammarItemPath, 'delete'>>({
    method: 'DELETE', path: `/admin/lessons/${id(lessonId)}/grammar/${id(itemId)}`,
  })
}

export function listAdminAssessments(filters: AdminAssessmentFilters = {}) {
  return apiClient<ResponseBodyOf<typeof assessmentsPath, 'get'>>({
    method: 'GET', path: '/admin/assessments', query: filters,
  })
}

export function getAdminAssessment(assessmentId: string) {
  return apiClient<ResponseBodyOf<typeof assessmentPath, 'get'>>({
    method: 'GET', path: `/admin/assessments/${id(assessmentId)}`,
  })
}

export function createAdminAssessment(body: AssessmentCreate) {
  return apiClient<ResponseBodyOf<typeof assessmentsPath, 'post'>, AssessmentCreate>({
    method: 'POST', path: '/admin/assessments', body,
  })
}

export function generateAssessmentDraft(body: AssessmentGenerationRequest) {
  return apiClient<AssessmentGenerationDraft, AssessmentGenerationRequest>({
    method: 'POST', path: '/admin/assessments/generate-draft', body,
  })
}

export function updateAdminAssessment(assessmentId: string, body: AssessmentPatch) {
  return apiClient<ResponseBodyOf<typeof assessmentPath, 'patch'>, AssessmentPatch>({
    method: 'PATCH', path: `/admin/assessments/${id(assessmentId)}`, body,
  })
}

export function listAssessmentQuestions(assessmentId: string) {
  return apiClient<ResponseBodyOf<typeof questionsPath, 'get'>>({
    method: 'GET', path: `/admin/assessments/${id(assessmentId)}/questions`,
  })
}

export function createAssessmentQuestion(assessmentId: string, body: QuestionCreate) {
  return apiClient<ResponseBodyOf<typeof questionsPath, 'post'>, QuestionCreate>({
    method: 'POST', path: `/admin/assessments/${id(assessmentId)}/questions`, body,
  })
}

export function updateAssessmentQuestion(assessmentId: string, questionId: string, body: QuestionPatch) {
  return apiClient<ResponseBodyOf<typeof questionPath, 'patch'>, QuestionPatch>({
    method: 'PATCH', path: `/admin/assessments/${id(assessmentId)}/questions/${id(questionId)}`, body,
  })
}

export function deleteAssessmentQuestion(assessmentId: string, questionId: string) {
  return apiClient<ResponseBodyOf<typeof questionPath, 'delete'>>({
    method: 'DELETE', path: `/admin/assessments/${id(assessmentId)}/questions/${id(questionId)}`,
  })
}

export function submitAssessmentReview(assessmentId: string) {
  return apiClient<ResponseBodyOf<typeof reviewPath, 'post'>>({
    method: 'POST', path: `/admin/assessments/${id(assessmentId)}/submit-review`,
  })
}

export function publishAdminAssessment(assessmentId: string) {
  return apiClient<ResponseBodyOf<typeof publishAssessmentPath, 'post'>>({
    method: 'POST', path: `/admin/assessments/${id(assessmentId)}/publish`,
  })
}

export function archiveAdminAssessment(assessmentId: string) {
  return apiClient<ResponseBodyOf<typeof archiveAssessmentPath, 'post'>>({
    method: 'POST', path: `/admin/assessments/${id(assessmentId)}/archive`,
  })
}

export function getAdminStats() {
  return apiClient<ResponseBodyOf<typeof statsPath, 'get'>>({ method: 'GET', path: '/admin/stats' })
}

export function listAdminDocuments(filters: AdminDocumentFilters = {}) {
  return apiClient<AdminDocumentPage>({
    method: 'GET', path: '/admin/documents', query: filters,
  })
}

export function getAdminDocument(documentId: string) {
  return apiClient<AdminDocumentDetail>({
    method: 'GET', path: `/admin/documents/${id(documentId)}`,
  })
}

export function getAdminDocumentPreview(documentId: string) {
  return apiClient<AdminDocumentPreview>({
    method: 'GET', path: `/admin/documents/${id(documentId)}/preview`,
  })
}

export function uploadDocument(input: DocumentUploadInput) {
  const formData = new FormData()
  formData.append('file', input.file)
  formData.append('title', input.title)
  formData.append('source_category', input.source_category)
  formData.append('source_origin', input.source_origin)
  formData.append('source_language', input.source_language)
  formData.append('domain_allowed', String(input.domain_allowed))
  const rightsNote = input.usage_rights_note?.trim()
  if (rightsNote) formData.append('usage_rights_note', rightsNote)
  return apiClient<ResponseBodyOf<typeof documentsPath, 'post'>, FormData>({
    method: 'POST', path: '/admin/documents', body: formData,
  })
}

export async function processAdminDocument(documentId: string): Promise<void> {
  const path = documentProcessPath.replace('/api/v1', '').replace('{document_id}', id(documentId))
  await apiClient({ method: 'POST', path })
}

export async function approveAdminDocument(documentId: string): Promise<void> {
  const path = documentApprovePath.replace('/api/v1', '').replace('{document_id}', id(documentId))
  await apiClient({ method: 'POST', path })
}

export async function rejectAdminDocument(documentId: string): Promise<void> {
  const path = documentRejectPath.replace('/api/v1', '').replace('{document_id}', id(documentId))
  await apiClient({ method: 'POST', path })
}

export async function retryAdminDocumentKnowledge(documentId: string): Promise<void> {
  const path = documentKnowledgeRetryPath.replace('/api/v1', '').replace('{document_id}', id(documentId))
  await apiClient({
    method: 'POST', path,
  })
}
