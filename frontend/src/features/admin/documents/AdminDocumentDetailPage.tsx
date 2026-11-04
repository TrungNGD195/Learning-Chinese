import { adminLabel, adminDate } from '../labels'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'
import { queryKeys } from '../../../app/query/keys'
import { Alert, Button, LoadingState, PageHeader, StatusBadge, Surface } from '../../../components/ui'
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

function AdminDocumentDetail({ documentId }: { documentId: string }) {
  const client = useQueryClient()
  const detail = useQuery({ queryKey: queryKeys.adminDocument(documentId), queryFn: () => getAdminDocument(documentId) })
  const isReviewable = detail.data?.review_status === 'PENDING' && detail.data.processing_status === 'PREVIEW_READY'
  const preview = useQuery({ queryKey: queryKeys.adminDocumentPreview(documentId), queryFn: () => getAdminDocumentPreview(documentId), enabled: Boolean(isReviewable) })
  const process = useMutation({
    mutationFn: () => processAdminDocument(documentId), retry: false,
    onSuccess: async () => { await invalidateDocumentProcess(client, documentId) },
    onError: async () => { await invalidateDocumentProcess(client, documentId) },
  })
  const approve = useMutation({
    mutationFn: () => approveAdminDocument(documentId), retry: false,
    onSuccess: async () => { await invalidateDocumentReview(client, documentId) },
    onError: async () => { await invalidateDocumentReview(client, documentId) },
  })
  const reject = useMutation({
    mutationFn: () => rejectAdminDocument(documentId), retry: false,
    onSuccess: async () => { await invalidateDocumentReview(client, documentId) },
    onError: async () => { await invalidateDocumentReview(client, documentId) },
  })
  const knowledgeRetry = useMutation({
    mutationFn: () => retryAdminDocumentKnowledge(documentId), retry: false,
    onSuccess: async () => { await invalidateDocumentKnowledgeRetry(client, documentId) },
    onError: async () => { await invalidateDocumentKnowledgeRetry(client, documentId) },
  })

  if (detail.isPending && !detail.data) return <section className="screen admin-document-detail-page"><div className="admin-document-detail-intro"><PageHeader title="Thông tin tài liệu" /></div><LoadingState>Đang tải tài liệu…</LoadingState></section>
  if (detail.isError && !detail.data) return <section className="screen admin-document-detail-page">
    <div className="admin-document-detail-intro"><PageHeader title="Thông tin tài liệu" back={<Link to="/admin/documents">Quay lại tài liệu</Link>} /></div>
    <Alert role="alert" tone="error">{isNotFound(detail.error) ? "Không tìm thấy tài liệu." : adminErrorText(detail.error, "Không thể tải tài liệu.")}</Alert>
    <Button className="secondary-action" onClick={() => void detail.refetch()}>Thử lại</Button>
  </section>
  if (!detail.data) return null

  const document = detail.data
  const canProcess = document.review_status === 'PENDING' && ['UPLOADED', 'FAILED'].includes(document.processing_status)
  const canReview = document.review_status === 'PENDING' && document.processing_status === 'PREVIEW_READY'
  const mutationError = (error: unknown, fallback: string) => {
    if (error instanceof ApiError && (error.code === 'NETWORK_ERROR' || (error.status !== null && error.status >= 500))) {
      return `${adminErrorText(error, fallback)} Đã tải lại trạng thái hiện tại. Vui lòng kiểm tra trước khi thử lại.`
    }
    return adminErrorText(error, fallback)
  }

  return <section className="screen admin-document-detail-page" aria-labelledby="page-title">
    <div className="admin-document-detail-intro">
      <PageHeader
        title="Thông tin tài liệu"
        titleId="page-title"
        back={<Link to="/admin/documents">Quay lại tài liệu</Link>}
        description={document.title || document.original_filename}
        actions={<div className="admin-document-statuses" aria-label="Trạng thái tài liệu">
          <StatusBadge tone={processingTone(document.processing_status)}>Xử lý: {adminLabel(document.processing_status)}</StatusBadge>
          <StatusBadge tone={reviewTone(document.review_status)}>Duyệt: {adminLabel(document.review_status)}</StatusBadge>
        </div>}
      />
    </div>
    {detail.isError && <Alert role="status" tone="warning">Chưa cập nhật được tài liệu. Đang hiển thị dữ liệu đã tải.</Alert>}
    {detail.isFetching && <p role="status">Đang cập nhật tài liệu…</p>}
    <Surface as="section" className="admin-document-metadata" aria-labelledby="document-metadata-heading">
      <h2 id="document-metadata-heading">Thông tin tài liệu</h2>
      <dl className="admin-document-metadata-grid">
        <dt>Tên tệp</dt><dd>{document.original_filename}</dd>
        <dt>Định dạng</dt><dd>{document.file_type}</dd>
        <dt>Dung lượng</dt><dd>{document.file_size_bytes === null ? "Chưa xác định" : `${document.file_size_bytes} bytes`}</dd>
        <dt>Loại nguồn</dt><dd>{adminLabel(document.source_category)}</dd>
        <dt>Xuất xứ</dt><dd>{document.source_origin ?? '—'}</dd>
        <dt>Ngôn ngữ nguồn</dt><dd>{adminLabel(document.source_language)}</dd>
        <dt>Ghi chú quyền sử dụng</dt><dd>{document.usage_rights_note ?? '—'}</dd>
        <dt>Trạng thái xử lý</dt><dd>{adminLabel(document.processing_status)}</dd>
        <dt>Trạng thái duyệt</dt><dd>{adminLabel(document.review_status)}</dd>
        <dt>Ngày tạo</dt><dd><time dateTime={document.created_at}>{adminDate(document.created_at)}</time></dd>
        <dt>Cập nhật gần nhất</dt><dd><time dateTime={document.updated_at}>{adminDate(document.updated_at)}</time></dd>
      </dl>
    </Surface>

    <Surface as="section" className="admin-document-workflow" aria-labelledby="document-workflow-heading">
      <h2 id="document-workflow-heading">Thao tác khả dụng</h2>
      {canProcess && <div className="admin-document-actions admin-document-processing-actions">
        <Button variant="primary" disabled={process.isPending} onClick={() => process.mutate()}>
          {process.isPending ? "Đang xử lý…" : document.processing_status === 'FAILED' ? "Thử xử lý lại" : "Xử lý tài liệu"}
        </Button>
      </div>}
      {isReviewable && <>
        {preview.isPending && <LoadingState>Đang tải bản xem trước…</LoadingState>}
        {preview.isError && <Alert role="alert" tone="error">{adminErrorText(preview.error, "Không thể tải nội dung đã xử lý.")}</Alert>}
        <div className="admin-document-actions admin-document-review-actions">
          <Button variant="primary" disabled={!canReview || approve.isPending} onClick={() => approve.mutate()}>{approve.isPending ? "Đang duyệt…" : "Duyệt tài liệu"}</Button>
          <Button variant="danger" disabled={!canReview || reject.isPending} onClick={() => reject.mutate()}>{reject.isPending ? "Đang từ chối…" : "Từ chối"}</Button>
        </div>
      </>}
      {document.review_status === 'APPROVED' && <Alert className="admin-document-approved-note" tone="info">Tài liệu đã được duyệt. Nội dung chỉ sẵn sàng tra cứu sau khi hoàn tất tạo dữ liệu tri thức.</Alert>}
      {document.knowledge_retry_available && <div className="admin-document-actions admin-document-knowledge-actions">
        <Button variant="secondary" disabled={knowledgeRetry.isPending} onClick={() => knowledgeRetry.mutate()}>{knowledgeRetry.isPending ? "Đang tạo lại dữ liệu tra cứu…" : "Thử tạo lại dữ liệu tra cứu"}</Button>
      </div>}
      {process.isError && <Alert role="alert" tone="error">{mutationError(process.error, "Xử lý tài liệu thất bại.")}</Alert>}
      {approve.isError && <Alert role="alert" tone="error">{mutationError(approve.error, "Không thể duyệt tài liệu.")}</Alert>}
      {reject.isError && <Alert role="alert" tone="error">{mutationError(reject.error, "Không thể từ chối tài liệu.")}</Alert>}
      {knowledgeRetry.isError && <Alert role="alert" tone="error">{mutationError(knowledgeRetry.error, "Không thể tạo lại dữ liệu tra cứu.")}</Alert>}
    </Surface>
    {isReviewable && preview.data && <DocumentPreview preview={preview.data} />}
  </section>
}

export function AdminDocumentDetailPage() {
  const { documentId } = useParams()
  if (!documentId) return <section className="screen admin-document-detail-page"><div className="admin-document-detail-intro"><PageHeader title="Thông tin tài liệu" /></div><Alert role="alert" tone="error">Không tìm thấy tài liệu.</Alert></section>
  return <AdminDocumentDetail key={documentId} documentId={documentId} />
}
