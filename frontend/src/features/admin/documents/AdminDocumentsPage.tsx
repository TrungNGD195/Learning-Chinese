import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router'
import { queryKeys } from '../../../app/query/keys'
import { adminErrorText } from '../AdminPrimitives'
import { listAdminDocuments, uploadDocument } from '../api'
import type { DocumentUploadInput } from '../api'
import { invalidateDocumentList } from '../invalidation'
import { DocumentUploadForm } from './DocumentUploadForm'

const pageSize = 20

export function AdminDocumentsPage() {
  const client = useQueryClient()
  const [page, setPage] = useState(1)
  const filters = { page, page_size: pageSize }
  const documents = useQuery({
    queryKey: queryKeys.adminDocuments(filters),
    queryFn: () => listAdminDocuments(filters),
  })
  const upload = useMutation({
    mutationFn: (input: DocumentUploadInput) => uploadDocument(input),
    retry: false,
    onSuccess: async () => { await invalidateDocumentList(client) },
    onError: async () => { await invalidateDocumentList(client) },
  })

  return (
    <section className="screen" aria-labelledby="page-title">
      <h1 id="page-title">Admin Documents</h1>
      <p>Upload raw source documents, process them, and review the server-generated preview.</p>
      <DocumentUploadForm
        onSubmit={(input) => upload.mutate(input)}
        pending={upload.isPending}
        error={upload.isError ? adminErrorText(upload.error, 'The document upload could not be completed.') : null}
      />
      {upload.data && (
        <p role="status">
          Raw source stored. Processing and review have not been completed.{' '}
          <Link to={`/admin/documents/${upload.data.id}`}>Open document detail</Link>
        </p>
      )}
      {documents.isPending && !documents.data && <p role="status">Loading documents…</p>}
      {documents.isError && !documents.data && <>
        <p role="alert">{adminErrorText(documents.error, 'Could not load documents.')}</p>
        <button type="button" onClick={() => void documents.refetch()}>Retry loading documents</button>
      </>}
      {documents.data && <>
        {documents.isError && <p role="alert">The document list could not be refreshed; showing the last server response.</p>}
        {documents.data.items.length === 0 ? <p>No documents have been uploaded.</p> : (
          <table>
            <thead><tr><th scope="col">Document</th><th scope="col">Source</th><th scope="col">Processing</th><th scope="col">Review</th><th scope="col">Action</th></tr></thead>
            <tbody>{documents.data.items.map((document) => (
              <tr key={document.id}>
                <td>{document.title || document.original_filename}</td>
                <td>{document.source_category ?? '—'}{document.source_language ? ` · ${document.source_language}` : ''}</td>
                <td>{document.processing_status}</td>
                <td>{document.review_status}</td>
                <td><Link to={`/admin/documents/${document.id}`}>Open document</Link></td>
              </tr>
            ))}</tbody>
          </table>
        )}
        <div className="admin-page-controls">
          <button type="button" disabled={page <= 1 || documents.isFetching} onClick={() => setPage((value) => Math.max(1, value - 1))}>Previous</button>
          <span>Page {documents.data.page}</span>
          <button type="button" disabled={page * documents.data.page_size >= documents.data.total || documents.isFetching} onClick={() => setPage((value) => value + 1)}>Next</button>
        </div>
        {documents.isFetching && <p role="status">Refreshing documents…</p>}
      </>}
    </section>
  )
}
