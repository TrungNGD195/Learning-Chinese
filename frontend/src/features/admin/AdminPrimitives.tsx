import { ApiError } from '../../lib/api/errors'

const knownErrors: Record<string, string> = {
  ADMIN_REQUIRED: 'Your account does not have Admin access.',
  NOT_FOUND: 'This resource could not be found.',
  INVALID_FIELDS: 'Check the submitted fields and try again.',
  INVALID_CURRICULUM: 'The curriculum order is invalid.',
  INVALID_CURRICULUM_TARGET: 'A curriculum item is no longer available.',
  INVALID_LESSON: 'The lesson fields are invalid.',
  LESSON_IMMUTABLE: 'This lesson can no longer be changed.',
  LESSON_CONTENT_IMMUTABLE: 'Content cannot be changed for an archived lesson.',
  LESSON_CONTENT_DETACH_DRAFT_ONLY: 'Content can only be detached from a draft lesson.',
  ITEM_HAS_LEARNER_HISTORY: 'This item has learner history and cannot be detached.',
  INVALID_ITEM_MODE: 'The selected content operation is invalid.',
  INVALID_ASSESSMENT: 'The assessment fields are invalid.',
  INVALID_ASSESSMENT_TARGET: 'Choose a valid lesson for this assessment.',
  INVALID_ASSESSMENT_SCOPE: 'The assessment scope is invalid.',
  ASSESSMENT_IMMUTABLE: 'This assessment can no longer be changed.',
  ASSESSMENT_HAS_NO_QUESTIONS: 'Add at least one question before submitting for review.',
  INVALID_LIFECYCLE_TRANSITION: 'The resource changed state. Its current state has been reloaded.',
  INVALID_QUESTION: 'Check the question fields and try again.',
  QUESTION_TYPE_IMMUTABLE: 'A question type cannot be changed after creation.',
  QUESTIONS_IMMUTABLE: 'Questions cannot be changed for this assessment.',
  QUESTION_HAS_HISTORY: 'This question has learner history and cannot be deleted.',
  INVALID_REQUEST: 'Check the document metadata and eligibility fields.',
  UNSUPPORTED_DOCUMENT_TYPE: 'Upload a PDF, DOCX, TXT, or MD file.',
  DOCUMENT_TOO_LARGE: "The document exceeds the server's configured upload limit.",
  EMPTY_DOCUMENT: 'The selected document is empty.',
  INVALID_DOCUMENT_FILE: 'The selected file is invalid or does not match its declared format.',
  DUPLICATE_DOCUMENT: 'An identical document has already been uploaded.',
  RAW_STORAGE_FAILED: 'The document could not be stored. Retry when safe.',
  PROCESSING_ALREADY_IN_PROGRESS: 'This document is already being processed.',
  INVALID_SOURCE_STATE: 'The document state changed. Reloaded server state must be used.',
  INGESTION_PROCESSING_FAILED: 'Processing failed. Reload the document before deciding whether to retry.',
  DOCUMENT_NOT_PREVIEW_READY: 'A reviewable preview is not currently available.',
  DOCUMENT_ALREADY_APPROVED: 'The document was already approved; refetching current state.',
  KNOWLEDGE_BUILD_FAILED: 'The knowledge build could not be started or completed; current state is reloading.',
}

export function adminErrorText(error: unknown, fallback: string) {
  if (!(error instanceof ApiError)) return fallback
  if (error.code === 'ADMIN_REQUIRED') return knownErrors.ADMIN_REQUIRED
  if (error.status === 404 || error.code === 'NOT_FOUND') return knownErrors.NOT_FOUND
  const mappedMessage = knownErrors[error.code]
  if (mappedMessage) return mappedMessage
  if (error.code === 'NETWORK_ERROR' || (error.status !== null && error.status >= 500)) return 'A temporary problem prevented this action. Please retry.'
  return fallback
}

export function isAdminRequired(error: unknown) {
  return error instanceof ApiError && error.code === 'ADMIN_REQUIRED'
}

export function isNotFound(error: unknown) {
  return error instanceof ApiError && (error.status === 404 || error.code === 'NOT_FOUND')
}
