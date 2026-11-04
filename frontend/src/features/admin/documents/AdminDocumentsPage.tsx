import { adminLabel } from '../labels'
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router'
import { queryKeys } from '../../../app/query/keys'
import { adminErrorText } from '../AdminPrimitives'
import { listAdminDocuments, uploadDocument } from '../api'
import type { DocumentUploadInput } from '../api'
import { invalidateDocumentList } from '../invalidation'
import { DocumentUploadForm } from './DocumentUploadForm'
import { Alert, Button, EmptyState, PageHeader, StatusBadge, Surface } from '../../../components/ui'

import { AdminLibrary } from '../AdminLibrary'

const pageSize = 20

function processingTone(status: string) {
  if (status === 'PROCESSING') return 'info' as const
  if (status === 'PREVIEW_READY') return 'success' as const
  if (status === 'FAILED') return 'danger' as const
  return 'neutral' as const
}

function reviewTone(status: string) {
  if (status === 'PENDING') return 'warning' as const
  if (status === 'APPROVED') return 'success' as const
  return 'neutral' as const
}

export function AdminDocumentsPage() {
  const client = useQueryClient()
  const [page, setPage] = useState(1)
  const filters = { page, page_size: pageSize }
  const documents = useQuery({ queryKey: queryKeys.adminDocuments(filters), queryFn: () => listAdminDocuments(filters) })
  const upload = useMutation({
    mutationFn: (input: DocumentUploadInput) => uploadDocument(input),
    retry: false,
    onSuccess: async () => { await invalidateDocumentList(client) },
    onError: async () => { await invalidateDocumentList(client) },
  })

  return <section className="screen admin-documents-page" aria-labelledby="page-title">
    <div className="admin-documents-intro">
      <PageHeader title="Thư viện tài liệu" titleId="page-title" description="Tải lên giáo trình, xử lý nội dung và duyệt bản xem trước." />
    </div>
    <div className="admin-documents-inventory-column">
      {documents.isPending && !documents.data && <Surface as="section" className="admin-documents-list-surface"><h2 className="admin-documents-section-title">Tài liệu</h2><p role="status">Đang tải tài liệu…</p></Surface>}
      {documents.isError && !documents.data && <>
        <Alert role="alert" tone="error" className="admin-documents-load-error">{adminErrorText(documents.error, "Không thể tải tài liệu.")}</Alert>
        <Button className="secondary-action" onClick={() => void documents.refetch()}>Thử tải lại tài liệu</Button>
      </>}
      {documents.data && <>
        {documents.isError && <Alert role="status" tone="warning" className="admin-documents-refresh-note">Chưa cập nhật được danh sách tài liệu. Đang hiển thị dữ liệu đã tải.</Alert>}
        <Surface as="section" className="admin-documents-list-surface">
          <h2 className="admin-documents-section-title">Tài liệu</h2>
          {documents.data.items.length === 0 ? <EmptyState title="Chưa có tài liệu nào được tải lên." /> : (
            <AdminLibrary label="tài liệu" kind="documents" total={documents.data.total} records={documents.data.items.map((document) => ({
              id: document.id, title: document.title || document.original_filename,
              context: `${adminLabel(document.source_category)} · ${adminLabel(document.source_language)}`,
              status: <><StatusBadge tone={processingTone(document.processing_status)}>{adminLabel(document.processing_status)}</StatusBadge><StatusBadge tone={reviewTone(document.review_status)}>{adminLabel(document.review_status)}</StatusBadge></>,
              detail: document.original_filename, href: `/admin/documents/${document.id}`, action: "Mở tài liệu",
            }))} />
          )}
          <nav className="admin-documents-pagination" aria-label="Các trang tài liệu">
            <Button className="secondary-action" disabled={page <= 1 || documents.isFetching} onClick={() => setPage((value) => Math.max(1, value - 1))}>Trước</Button>
            <span>Trang {documents.data.page}</span>
            <Button className="secondary-action" disabled={page * documents.data.page_size >= documents.data.total || documents.isFetching} onClick={() => setPage((value) => value + 1)}>Tiếp</Button>
          </nav>
          {documents.isFetching && <p role="status">Đang cập nhật tài liệu…</p>}
        </Surface>
      </>}
    </div>
    <div className="admin-documents-upload-column">
      <Surface as="section" className="admin-documents-upload-surface">
        <DocumentUploadForm
          onSubmit={(input) => upload.mutate(input)}
          pending={upload.isPending}
          error={upload.isError ? adminErrorText(upload.error, "Không thể tải tài liệu lên.") : null}
        />
      </Surface>
      {upload.data && <Alert role="status" tone="success" className="admin-documents-upload-result">
        Đã lưu tệp nguồn. Tài liệu chưa được xử lý và duyệt.{' '}
        <Link to={`/admin/documents/${upload.data.id}`}>Xem thông tin tài liệu</Link>
      </Alert>}
    </div>
  </section>
}
