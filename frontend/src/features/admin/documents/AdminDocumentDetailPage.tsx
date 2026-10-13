import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'
import { queryKeys } from '../../../app/query/keys'
import { ApiError } from '../../../lib/api/errors'
import { adminErrorText, isNotFound } from '../AdminPrimitives'
import {
  approveAdminDocument,
  getAdminDocument,
  getAdminDocumentPreview,
  processAdminDocument,
  rejectAdminDocument,
  retryAdminDocumentKnowledge,
} from '../api'
import {
  invalidateDocumentKnowledgeRetry,
  invalidateDocumentProcess,
  invalidateDocumentReview,
} from '../invalidation'
import { DocumentPreview } from './DocumentPreview'

function AdminDocumentDetail({ documentId }: { documentId: string }) {
  const client = useQueryClient()
  const detail = useQuery({
    queryKey: queryKeys.adminDocument(documentId),
    queryFn: () => getAdminDocument(documentId),
  })
  const isReviewable = detail.data?.review_status === 'PENDING' && detail.data.processing_status === 'PREVIEW_READY'
  const preview = useQuery({
    queryKey: queryKeys.adminDocumentPreview(documentId),
    queryFn: () => getAdminDocumentPreview(documentId),
    enabled: Boolean(isReviewable),
  })
  const process = useMutation({
    mutationFn: () => processAdminDocument(documentId),
    retry: false,
    onSuccess: async () => { await invalidateDocumentProcess(client, documentId) },
    onError: async () => { await invalidateDocumentProcess(client, documentId) },
  })
  const approve = useMutation({
    mutationFn: () => approveAdminDocument(documentId),
    retry: false,
    onSuccess: async () => { await invalidateDocumentReview(client, documentId) },
    onError: async () => { await invalidateDocumentReview(client, documentId) },
  })
  const reject = useMutation({
    mutationFn: () => rejectAdminDocument(documentId),
    retry: false,
    onSuccess: async () => { await invalidateDocumentReview(client, documentId) },
    onError: async () => { await invalidateDocumentReview(client, documentId) },
  })
  const knowledgeRetry = useMutation({
    mutationFn: () => retryAdminDocumentKnowledge(documentId),
    retry: false,
    onSuccess: async () => { await invalidateDocumentKnowledgeRetry(client, documentId) },
    onError: async () => { await invalidateDocumentKnowledgeRetry(client, documentId) },
  })

  if (detail.isPending && !detail.data) return <section className="screen"><h1>Admin Document</h1><p role="status">Loading document…</p></section>
  if (detail.isError && !detail.data) return <section className="screen"><h1>Admin Document</h1><p role="alert">{isNotFound(detail.error) ? 'Document not found.' : adminErrorText(detail.error, 'Could not load the document.')}</p><button type="button" onClick={() => void detail.refetch()}>Retry</button><Link to="/admin/documents">Back to Documents</Link></section>
  if (!detail.data) return null

  const document = detail.data
  const canProcess = document.review_status === 'PENDING' && ['UPLOADED', 'FAILED'].includes(document.processing_status)
  const canReview = document.review_status === 'PENDING' && document.processing_status === 'PREVIEW_READY'
  const mutationError = (error: unknown, fallback: string) => {
    if (error instanceof ApiError && (error.code === 'NETWORK_ERROR' || (error.status !== null && error.status >= 500))) {
      return `${adminErrorText(error, fallback)} Current server state was reloaded; review it before retrying.`
    }
    return adminErrorText(error, fallback)
  }

  return (
    <section className="screen" aria-labelledby="page-title">
      <p><Link to="/admin/documents">Back to Documents</Link></p>
      <h1 id="page-title">Admin Document</h1>
      {detail.isError && <p role="alert">Document refresh failed. The last server response remains visible.</p>}
      {detail.isFetching && <p role="status">Refreshing document…</p>}
      <section className="learning-card" aria-label="Document metadata">
        <h2>{document.title || document.original_filename}</h2>
        <dl>
          <dt>Filename</dt><dd>{document.original_filename}</dd>
          <dt>File type</dt><dd>{document.file_type}</dd>
          <dt>Size</dt><dd>{document.file_size_bytes === null ? 'Unknown' : `${document.file_size_bytes} bytes`}</dd>
          <dt>Source category</dt><dd>{document.source_category ?? '—'}</dd>
          <dt>Source origin</dt><dd>{document.source_origin ?? '—'}</dd>
          <dt>Source language</dt><dd>{document.source_language ?? '—'}</dd>
          <dt>Usage rights note</dt><dd>{document.usage_rights_note ?? '—'}</dd>
          <dt>Processing status</dt><dd>{document.processing_status}</dd>
          <dt>Review status</dt><dd>{document.review_status}</dd>
          <dt>Created</dt><dd>{new Date(document.created_at).toLocaleString()}</dd>
          <dt>Last updated</dt><dd>{new Date(document.updated_at).toLocaleString()}</dd>
        </dl>
      </section>

      {canProcess && <>
        <button type="button" disabled={process.isPending} onClick={() => process.mutate()}>
          {process.isPending ? 'Processing…' : document.processing_status === 'FAILED' ? 'Retry Processing' : 'Process'}
        </button>
        {process.isError && <p role="alert">{mutationError(process.error, 'Document processing failed.')}</p>}
      </>}

      {isReviewable && <>
        {preview.isPending && <p role="status">Loading preview…</p>}
        {preview.isError && <p role="alert">{adminErrorText(preview.error, 'Could not load the transformed preview.')}</p>}
        {preview.data && <DocumentPreview preview={preview.data} />}
        <div className="admin-filter-row">
          <button type="button" disabled={!canReview || approve.isPending} onClick={() => approve.mutate()}>{approve.isPending ? 'Approving…' : 'Approve'}</button>
          <button type="button" disabled={!canReview || reject.isPending} onClick={() => reject.mutate()}>{reject.isPending ? 'Rejecting…' : 'Reject'}</button>
        </div>
        {approve.isError && <p role="alert">{mutationError(approve.error, 'Could not approve the document.')}</p>}
        {reject.isError && <p role="alert">{mutationError(reject.error, 'Could not reject the document.')}</p>}
      </>}

      {document.review_status === 'APPROVED' && <p>Human review is approved. This does not mean the knowledge is active for retrieval.</p>}
      {document.knowledge_retry_available && <>
        <button type="button" disabled={knowledgeRetry.isPending} onClick={() => knowledgeRetry.mutate()}>
          {knowledgeRetry.isPending ? 'Retrying knowledge build…' : 'Retry Knowledge Build'}
        </button>
      </>}
      {knowledgeRetry.isError && <p role="alert">{mutationError(knowledgeRetry.error, 'Could not retry the knowledge build.')}</p>}
    </section>
  )
}

export function AdminDocumentDetailPage() {
  const { documentId } = useParams()
  if (!documentId) return <section className="screen"><h1>Admin Document</h1><p role="alert">Document not found.</p></section>
  return <AdminDocumentDetail key={documentId} documentId={documentId} />
}
