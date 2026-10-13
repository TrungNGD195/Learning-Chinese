import type { QueryClient, QueryKey } from '@tanstack/react-query'
import { queryKeys } from '../../app/query/keys'

async function invalidate(queryClient: QueryClient, keys: QueryKey[]) {
  await Promise.all(keys.map((queryKey) => queryClient.invalidateQueries({ queryKey })))
}

export function invalidateHskMetadata(queryClient: QueryClient, hskId: string) {
  return invalidate(queryClient, [
    queryKeys.adminHskLevels, queryKeys.adminCurriculum(hskId),
    queryKeys.curriculumLevels, queryKeys.curriculumHsk(hskId), queryKeys.progressOverview,
    queryKeys.progressHsk(hskId), queryKeys.dashboard,
  ])
}

export function invalidateCurriculumOrder(queryClient: QueryClient, hskId: string) {
  return invalidate(queryClient, [
    queryKeys.adminCurriculum(hskId), queryKeys.curriculumLevels, queryKeys.curriculumHsk(hskId),
    queryKeys.progressOverview, queryKeys.progressHsk(hskId), queryKeys.dashboard,
  ])
}

export function invalidateLessonList(queryClient: QueryClient) {
  return queryClient.invalidateQueries({ queryKey: queryKeys.adminLessonsRoot })
}

export function invalidateLessonMetadata(queryClient: QueryClient, lessonId: string, hskId: string) {
  return invalidate(queryClient, [
    queryKeys.adminLesson(lessonId), queryKeys.adminLessonsRoot, queryKeys.lesson(lessonId),
    queryKeys.curriculumHsk(hskId), queryKeys.progressHsk(hskId), queryKeys.dashboard,
  ])
}

export function invalidateLessonContent(queryClient: QueryClient, lessonId: string, hskId: string, kind: 'vocabulary' | 'grammar') {
  return invalidate(queryClient, [
    kind === 'vocabulary' ? queryKeys.adminLessonVocabulary(lessonId) : queryKeys.adminLessonGrammar(lessonId),
    queryKeys.adminLesson(lessonId), queryKeys.lesson(lessonId), queryKeys.lessonProgress(lessonId),
    queryKeys.curriculumHsk(hskId), queryKeys.progressHsk(hskId), queryKeys.dashboard,
  ])
}

export function invalidateLessonLifecycle(queryClient: QueryClient, lessonId: string, hskId: string) {
  return invalidate(queryClient, [
    queryKeys.adminLesson(lessonId), queryKeys.adminLessonsRoot, queryKeys.adminCurriculum(hskId),
    queryKeys.lesson(lessonId), queryKeys.curriculumLevels, queryKeys.curriculumHsk(hskId),
    queryKeys.progressOverview, queryKeys.progressHsk(hskId), queryKeys.dashboard,
  ])
}

export function invalidateAssessmentList(queryClient: QueryClient) {
  return queryClient.invalidateQueries({ queryKey: queryKeys.adminAssessmentsRoot })
}

export function invalidateAssessmentMetadata(queryClient: QueryClient, assessmentId: string) {
  return invalidate(queryClient, [
    queryKeys.adminAssessment(assessmentId), queryKeys.adminAssessmentsRoot, queryKeys.assessment(assessmentId),
  ])
}

export function invalidateAssessmentQuestions(queryClient: QueryClient, assessmentId: string) {
  return invalidate(queryClient, [
    queryKeys.adminQuestions(assessmentId), queryKeys.adminAssessment(assessmentId), queryKeys.assessment(assessmentId),
  ])
}

export function invalidateAssessmentLifecycle(
  queryClient: QueryClient,
  assessment: { id: string; type: 'LESSON_EXERCISE' | 'PERIODIC_TEST'; lesson_id: string | null },
) {
  const keys: QueryKey[] = [queryKeys.adminAssessment(assessment.id), queryKeys.adminAssessmentsRoot]
  if (assessment.type === 'LESSON_EXERCISE') {
    keys.push(queryKeys.assessment(assessment.id))
    if (assessment.lesson_id) keys.push(queryKeys.lesson(assessment.lesson_id))
  } else {
    keys.push(
      queryKeys.curriculumHskRoot, queryKeys.progressHskRoot, queryKeys.dashboard,
      queryKeys.progressOverview, queryKeys.curriculumLevels, queryKeys.assessment(assessment.id),
    )
  }
  return invalidate(queryClient, keys)
}

export function invalidateDocumentList(queryClient: QueryClient) {
  return queryClient.invalidateQueries({ queryKey: queryKeys.adminDocumentsRoot })
}

export function invalidateDocumentProcess(queryClient: QueryClient, documentId: string) {
  return invalidate(queryClient, [
    queryKeys.adminDocumentsRoot,
    queryKeys.adminDocument(documentId),
    queryKeys.adminDocumentPreview(documentId),
  ])
}

export function invalidateDocumentReview(queryClient: QueryClient, documentId: string) {
  return invalidate(queryClient, [
    queryKeys.adminDocumentsRoot,
    queryKeys.adminDocument(documentId),
    queryKeys.adminDocumentPreview(documentId),
  ])
}

export function invalidateDocumentKnowledgeRetry(queryClient: QueryClient, documentId: string) {
  return invalidate(queryClient, [
    queryKeys.adminDocumentsRoot,
    queryKeys.adminDocument(documentId),
  ])
}
