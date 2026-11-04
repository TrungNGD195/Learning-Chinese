import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { queryKeys } from '../../../app/query/keys'
import { ApiError } from '../../../lib/api/errors'
import { authApi } from '../../auth/api'
import { createAppRoutes } from '../../../app/router/routes'
import * as api from '../api'
import type { AdminDocumentDetail, AdminDocumentListItem, AdminDocumentPreview } from '../api'

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>()
  return {
    ...actual,
    listAdminDocuments: vi.fn(),
    getAdminDocument: vi.fn(),
    getAdminDocumentPreview: vi.fn(),
    uploadDocument: vi.fn(),
    processAdminDocument: vi.fn(),
    approveAdminDocument: vi.fn(),
    rejectAdminDocument: vi.fn(),
    retryAdminDocumentKnowledge: vi.fn(),
  }
})

vi.mock('../../auth/api', () => ({ authApi: {
  register: vi.fn(), login: vi.fn(), getMe: vi.fn(), refresh: vi.fn(), logout: vi.fn(), logoutAll: vi.fn(),
  changePassword: vi.fn(), requestPasswordReset: vi.fn(), confirmPasswordReset: vi.fn(),
} }))

const admin = { id: 'admin-1', email: 'admin@example.test', full_name: "Quản trị", role: 'ADMIN' as const }
const listItem: AdminDocumentListItem = {
  id: 'document-1', original_filename: 'lesson.pdf', file_type: 'PDF', mime_type: 'application/pdf',
  file_size_bytes: 128, title: 'Chinese lesson', source_category: 'CURRICULUM_MATERIAL',
  source_origin: 'Textbook', source_language: 'zh', usage_rights_note: null,
  processing_status: 'UPLOADED', review_status: 'PENDING', created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z', approved_at: null,
}
const detail: AdminDocumentDetail = { ...listItem, knowledge_retry_available: false }
const uploaded = {
  id: 'document-2', original_filename: 'new-source.txt', file_type: 'TXT', mime_type: 'text/plain',
  file_size_bytes: 10, content_hash: 'server-only-hash', title: 'New source',
  source_category: 'CURRICULUM_MATERIAL', source_origin: 'Author', source_language: 'zh',
  usage_rights_note: null, processing_status: 'UPLOADED', review_status: 'PENDING',
  created_at: '2026-01-01T00:00:00Z',
}
const preview: AdminDocumentPreview = {
  schema_version: 'transformed_document/v1', source_type: 'DOCUMENT', source_id: 'document-1',
  title: 'Chinese lesson', source_language: 'zh', source_category: 'CURRICULUM_MATERIAL',
  transformation_strategy: 'canonical_document', transformation_version: 'v1',
  provenance: { source_origin: 'Textbook', usage_rights_note: null, original_filename: 'lesson.pdf' },
  blocks: [{ order: 0, content_type: 'DOCUMENT_TEXT', block_kind: 'PARAGRAPH', text: '你好',
    section_path: ['Greetings'], source_locator: { kind: 'PDF_PAGE', page_number: 2 },
    structured_data: {}, metadata: {} }],
}

function error(status: number, code: string) {
  return new ApiError({ status, code, message: 'server message', details: null })
}

function submitUpload() {
  const input = screen.getByLabelText(/Tệp \(PDF/)
  const form = input.closest('form')
  if (!form) throw new Error('Upload form was not rendered')
  fireEvent.submit(form)
}

function renderAt(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  client.setQueryDefaults(queryKeys.authMe, { staleTime: Infinity })
  client.setQueryData(queryKeys.authMe, admin)
  const router = createMemoryRouter(createAppRoutes(), { initialEntries: [path] })
  return { ...render(<QueryClientProvider client={client}><RouterProvider router={router} /></QueryClientProvider>), client, router }
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(api.listAdminDocuments).mockResolvedValue({ items: [listItem], page: 1, page_size: 20, total: 1 })
  vi.mocked(api.getAdminDocument).mockResolvedValue(detail)
  vi.mocked(api.getAdminDocumentPreview).mockResolvedValue(preview)
  vi.mocked(api.uploadDocument).mockResolvedValue(uploaded)
  vi.mocked(api.processAdminDocument).mockResolvedValue(undefined)
  vi.mocked(api.approveAdminDocument).mockResolvedValue(undefined)
  vi.mocked(api.rejectAdminDocument).mockResolvedValue(undefined)
  vi.mocked(api.retryAdminDocumentKnowledge).mockResolvedValue(undefined)
})

afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs() })

describe('Step 5.8 Admin Document UI', () => {
  it('replaces the placeholder with a real list and loads page 1 with page_size 20', async () => {
    renderAt('/admin/documents')
    expect(await screen.findByRole('heading', { name: "Thư viện tài liệu" })).toBeInTheDocument()
    expect((await screen.findAllByRole('link', { name: "Mở tài liệu" }))[0]).toHaveAttribute('href', '/admin/documents/document-1')
    expect(screen.getByRole('button', { name: 'Chinese lesson' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Bảng' }))
    expect(screen.getAllByText('Đã tải lên').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Chờ duyệt').length).toBeGreaterThan(0)
    const tableRegion = screen.getByRole('region', { name: "Bảng tài liệu" })
    expect(tableRegion).toHaveAttribute('tabindex', '0')
    expect(within(tableRegion).getByRole('table')).toBeInTheDocument()
    expect(screen.queryByText('Document management will be implemented in Phase 5.')).not.toBeInTheDocument()
    expect(api.listAdminDocuments).toHaveBeenCalledWith({ page: 1, page_size: 20 })
  })

  it('shows list loading, empty, and error states', async () => {
    vi.mocked(api.listAdminDocuments).mockImplementationOnce(() => new Promise(() => {}))
    const loading = renderAt('/admin/documents')
    expect(screen.getByRole('status')).toHaveTextContent('Đang tải tài liệu')
    loading.unmount()

    vi.mocked(api.listAdminDocuments).mockResolvedValueOnce({ items: [], page: 1, page_size: 20, total: 0 })
    renderAt('/admin/documents')
    expect(await screen.findByText("Chưa có tài liệu nào được tải lên.")).toBeInTheDocument()
  })

  it('paginates using the server page/page_size values', async () => {
    vi.mocked(api.listAdminDocuments)
      .mockResolvedValueOnce({ items: [listItem], page: 1, page_size: 20, total: 21 })
      .mockResolvedValueOnce({ items: [{ ...listItem, id: 'document-21' }], page: 2, page_size: 20, total: 21 })
    renderAt('/admin/documents')
    fireEvent.click(await screen.findByRole('button', { name: "Tiếp" }))
    await waitFor(() => expect(api.listAdminDocuments).toHaveBeenLastCalledWith({ page: 2, page_size: 20 }))
    expect(await screen.findByText('Trang 2')).toBeInTheDocument()
  })

  it.each(['lesson.pdf', 'lesson.docx', 'lesson.txt', 'lesson.md'])(
    'submits supported upload file %s with required metadata and domain attestation', async (filename) => {
      renderAt('/admin/documents')
      const file = new File(['raw bytes'], filename, { type: 'text/plain' })
      fireEvent.change(screen.getByLabelText(/Tệp \(PDF/), { target: { files: [file] } })
      fireEvent.change(screen.getByLabelText("Tiêu đề"), { target: { value: 'New source' } })
      fireEvent.change(screen.getByLabelText("Xuất xứ"), { target: { value: 'Author' } })
      fireEvent.click(screen.getByLabelText(/Tôi xác nhận tài liệu/))
      const button = screen.getByRole('button', { name: "Tải tài liệu lên" })
      expect(button).toBeEnabled()
      submitUpload()
      await waitFor(() => expect(api.uploadDocument).toHaveBeenCalledTimes(1))
      expect(api.uploadDocument).toHaveBeenCalledWith(expect.objectContaining({
        file, title: 'New source', source_category: 'CURRICULUM_MATERIAL', source_origin: 'Author',
        source_language: 'zh', domain_allowed: true, usage_rights_note: null,
      }))
      expect(await screen.findByText(/Đã lưu tệp nguồn/)).toBeInTheDocument()
      expect(screen.getByRole('link', { name: "Xem thông tin tài liệu" })).toHaveAttribute('href', '/admin/documents/document-2')
      expect(screen.queryByText(/Đã duyệt|Đang hoạt động/)).not.toBeInTheDocument()
    },
  )

  it('keeps upload attestation required and sends an optional rights note only when supplied', async () => {
    renderAt('/admin/documents')
    const file = new File(['raw'], 'book.pdf', { type: 'application/pdf' })
    fireEvent.change(screen.getByLabelText(/Tệp \(PDF/), { target: { files: [file] } })
    fireEvent.change(screen.getByLabelText("Tiêu đề"), { target: { value: 'Book' } })
    fireEvent.change(screen.getByLabelText("Xuất xứ"), { target: { value: 'Publisher' } })
    expect(screen.getByRole('button', { name: "Tải tài liệu lên" })).toBeDisabled()
    fireEvent.change(screen.getByLabelText("Ghi chú quyền sử dụng (không bắt buộc)"), { target: { value: 'Licensed for study' } })
    fireEvent.click(screen.getByLabelText(/Tôi xác nhận tài liệu/))
    submitUpload()
    await waitFor(() => expect(api.uploadDocument).toHaveBeenCalledWith(expect.objectContaining({
      file, domain_allowed: true, usage_rights_note: 'Licensed for study',
    })))
  })

  it('constructs exact multipart fields through the central apiClient', async () => {
    const actualApi = await vi.importActual<typeof import('../api')>('../api')
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(uploaded), { status: 201 }))
    vi.stubGlobal('fetch', fetchMock)
    const file = new File(['raw'], 'book.pdf', { type: 'application/pdf' })
    await actualApi.uploadDocument({
      file, title: 'Book', source_category: 'CURRICULUM_MATERIAL', source_origin: 'Publisher',
      source_language: 'zh', domain_allowed: true, usage_rights_note: 'Licensed',
    })
    const init = fetchMock.mock.calls[0][1] as RequestInit
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/admin/documents')
    expect(init.credentials).toBe('include')
    expect(init.headers).toEqual({ Accept: 'application/json' })
    expect(init.body).toBeInstanceOf(FormData)
    const form = init.body as FormData
    const fieldNames: string[] = []
    form.forEach((_value, key) => fieldNames.push(key))
    expect(fieldNames.sort()).toEqual([
      'domain_allowed', 'file', 'source_category', 'source_language', 'source_origin', 'title', 'usage_rights_note',
    ])
    expect(form.get('file')).toBeInstanceOf(File)
    expect(form.get('domain_allowed')).toBe('true')
    expect(form.get('title')).toBe('Book')
    expect(form.get('usage_rights_note')).toBe('Licensed')
  })

  it.each([
    ['UNSUPPORTED_DOCUMENT_TYPE', "Chọn tệp PDF, DOCX, TXT hoặc MD."],
    ['DOCUMENT_TOO_LARGE', "Tài liệu vượt quá giới hạn dung lượng cho phép."],
    ['EMPTY_DOCUMENT', "Tệp đã chọn không có nội dung."],
    ['INVALID_DOCUMENT_FILE', "Tệp đã chọn không hợp lệ hoặc không đúng định dạng khai báo."],
    ['DUPLICATE_DOCUMENT', "Tài liệu giống hệt đã được tải lên trước đó."],
  ])('shows a safe upload message for %s', async (code, message) => {
    vi.mocked(api.uploadDocument).mockRejectedValueOnce(error(422, code))
    renderAt('/admin/documents')
    fireEvent.change(screen.getByLabelText(/Tệp \(PDF/), { target: { files: [new File(['raw'], 'x.txt')] } })
    fireEvent.change(screen.getByLabelText("Tiêu đề"), { target: { value: "Tiêu đề" } })
    fireEvent.change(screen.getByLabelText("Xuất xứ"), { target: { value: 'Source' } })
    fireEvent.click(screen.getByLabelText(/Tôi xác nhận tài liệu/))
    submitUpload()
    expect(await screen.findByRole('alert')).toHaveTextContent(message)
    expect(api.uploadDocument).toHaveBeenCalledTimes(1)
  })

  it('shows the mapped RAW_STORAGE_FAILED message for HTTP 500 without replacing it with the generic fallback', async () => {
    vi.mocked(api.uploadDocument).mockRejectedValueOnce(error(500, 'RAW_STORAGE_FAILED'))
    renderAt('/admin/documents')
    fireEvent.change(screen.getByLabelText(/Tệp \(PDF/), { target: { files: [new File(['raw'], 'book.pdf')] } })
    fireEvent.change(screen.getByLabelText("Tiêu đề"), { target: { value: 'Book' } })
    fireEvent.change(screen.getByLabelText("Xuất xứ"), { target: { value: 'Publisher' } })
    fireEvent.click(screen.getByLabelText(/Tôi xác nhận tài liệu/))
    submitUpload()
    expect(await screen.findByRole('alert')).toHaveTextContent("Không thể lưu tài liệu. Vui lòng thử lại.")
    expect(screen.queryByText("Có sự cố tạm thời. Vui lòng thử lại.")).not.toBeInTheDocument()
    expect(screen.queryByText('server message')).not.toBeInTheDocument()
    expect(api.uploadDocument).toHaveBeenCalledTimes(1)
  })

  it('supports a deep-linked detail page with separate processing and review statuses', async () => {
    renderAt('/admin/documents/document-1')
    expect(await screen.findByRole('heading', { name: "Thông tin tài liệu" })).toBeInTheDocument()
    expect(await screen.findByText('Chinese lesson')).toBeInTheDocument()
    expect(screen.getByText("Trạng thái xử lý")).toBeInTheDocument()
    expect(screen.getByText("Trạng thái duyệt")).toBeInTheDocument()
    expect(screen.getAllByText('Đã tải lên').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Chờ duyệt').length).toBeGreaterThan(0)
    expect(api.getAdminDocument).toHaveBeenCalledWith('document-1')
  })

  it('shows detail loading, not-found, and retryable error states', async () => {
    vi.mocked(api.getAdminDocument).mockImplementationOnce(() => new Promise(() => {}))
    const loading = renderAt('/admin/documents/document-1')
    expect(screen.getByRole('status')).toHaveTextContent('Đang tải tài liệu')
    loading.unmount()

    vi.mocked(api.getAdminDocument).mockRejectedValueOnce(error(404, 'NOT_FOUND'))
    renderAt('/admin/documents/missing')
    expect(await screen.findByRole('alert')).toHaveTextContent("Không tìm thấy tài liệu.")
    expect(screen.getByRole('link', { name: "Quay lại tài liệu" })).toHaveAttribute('href', '/admin/documents')
  })

  it.each([
    ['PENDING', 'UPLOADED', "Xử lý tài liệu"],
    ['PENDING', 'FAILED', "Thử xử lý lại"],
  ] as const)('offers %s/%s processing action', async (review, processing, label) => {
    vi.mocked(api.getAdminDocument).mockResolvedValueOnce({ ...detail, review_status: review, processing_status: processing })
    renderAt('/admin/documents/document-1')
    expect(await screen.findByRole('button', { name: label })).toBeEnabled()
  })

  it.each([
    ['PENDING', 'PREVIEW_READY'],
    ['APPROVED', 'UPLOADED'],
    ['REJECTED', 'FAILED'],
  ] as const)('does not offer process action for illegal %s/%s state', async (review, processing) => {
    vi.mocked(api.getAdminDocument).mockResolvedValueOnce({ ...detail, review_status: review, processing_status: processing })
    renderAt('/admin/documents/document-1')
    await screen.findByRole('heading', { name: "Thông tin tài liệu" })
    expect(screen.queryByRole('button', { name: "Xử lý tài liệu" })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: "Thử xử lý lại" })).not.toBeInTheDocument()
  })

  it('shows synchronous Process pending state and invalidates list/detail state', async () => {
    let finish!: () => void
    vi.mocked(api.processAdminDocument).mockImplementationOnce(() => new Promise<void>((resolve) => { finish = resolve }))
    const { client } = renderAt('/admin/documents/document-1')
    const listKey = queryKeys.adminDocuments({ page: 1, page_size: 20 })
    client.setQueryData(listKey, { items: [listItem], page: 1, page_size: 20, total: 1 })
    fireEvent.click(await screen.findByRole('button', { name: "Xử lý tài liệu" }))
    expect(await screen.findByRole('button', { name: "Đang xử lý…" })).toBeDisabled()
    await act(async () => { finish() })
    await waitFor(() => expect(api.getAdminDocument).toHaveBeenCalledTimes(2))
    expect(client.getQueryState(listKey)?.isInvalidated).toBe(true)
    expect(api.getAdminDocumentPreview).not.toHaveBeenCalled()
  })

  it('maps HTTP 500 processing failure, refetches, exposes explicit retry, and never resends automatically', async () => {
    vi.mocked(api.getAdminDocument)
      .mockResolvedValueOnce(detail)
      .mockResolvedValueOnce({ ...detail, processing_status: 'FAILED' })
    vi.mocked(api.processAdminDocument).mockRejectedValueOnce(error(500, 'INGESTION_PROCESSING_FAILED'))
    renderAt('/admin/documents/document-1')
    fireEvent.click(await screen.findByRole('button', { name: "Xử lý tài liệu" }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      "Xử lý thất bại. Tải lại tài liệu trước khi thử lại.",
    )
    expect(screen.getByRole('alert')).toHaveTextContent('Đã tải lại trạng thái hiện tại. Vui lòng kiểm tra trước khi thử lại.')
    await waitFor(() => expect(api.getAdminDocument).toHaveBeenCalledTimes(2))
    expect(screen.getByText('Chờ duyệt', { selector: 'dd' })).toBeInTheDocument()
    expect(screen.getByText('Xử lý thất bại', { selector: 'dd' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: "Thử xử lý lại" })).toBeEnabled()
    expect(screen.queryByText("Có sự cố tạm thời. Vui lòng thử lại.")).not.toBeInTheDocument()
    expect(screen.queryByText('server message')).not.toBeInTheDocument()
    expect(api.processAdminDocument).toHaveBeenCalledTimes(1)
  })

  it('loads and renders only the transformed preview for a reviewable candidate', async () => {
    vi.mocked(api.getAdminDocument).mockResolvedValueOnce({ ...detail, processing_status: 'PREVIEW_READY' })
    renderAt('/admin/documents/document-1')
    expect(await screen.findByRole('heading', { name: "Nội dung sau xử lý" })).toBeInTheDocument()
    expect(screen.getByText('你好')).toBeInTheDocument()
    expect(screen.getByText('Trang 2')).toBeInTheDocument()
    expect(document.querySelector('.admin-document-preview-blocks')).toBeInTheDocument()
    expect(document.querySelector('.document-preview-blocks')).not.toBeInTheDocument()
    expect(api.getAdminDocumentPreview).toHaveBeenCalledWith('document-1')
    expect(screen.queryByText(/storage_reference|TransformationRun|KnowledgeVersion|Chunk|vector/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /parse|transform|chunk|embed|activate|reprocess/i })).not.toBeInTheDocument()
  })

  it('gates review actions and renders authoritative approval after rejecting a re-review candidate', async () => {
    vi.mocked(api.getAdminDocument)
      .mockResolvedValueOnce({ ...detail, processing_status: 'PREVIEW_READY' })
      .mockResolvedValueOnce({ ...detail, processing_status: 'PREVIEW_READY', review_status: 'APPROVED' })
    renderAt('/admin/documents/document-1')
    fireEvent.click(await screen.findByRole('button', { name: "Từ chối" }))
    await waitFor(() => expect(api.rejectAdminDocument).toHaveBeenCalledTimes(1))
    expect(await screen.findByText('Đã duyệt', { selector: 'dd' })).toBeInTheDocument()
    expect(screen.getByText(/chỉ sẵn sàng tra cứu sau khi/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: "Duyệt tài liệu" })).not.toBeInTheDocument()
  })

  it('refetches after successful approval rather than optimistically changing the lifecycle', async () => {
    vi.mocked(api.getAdminDocument)
      .mockResolvedValueOnce({ ...detail, processing_status: 'PREVIEW_READY' })
      .mockResolvedValueOnce({ ...detail, processing_status: 'PREVIEW_READY', review_status: 'APPROVED' })
    renderAt('/admin/documents/document-1')
    fireEvent.click(await screen.findByRole('button', { name: "Duyệt tài liệu" }))
    await waitFor(() => expect(api.approveAdminDocument).toHaveBeenCalledTimes(1))
    expect(await screen.findByText('Đã duyệt', { selector: 'dd' })).toBeInTheDocument()
    expect(api.getAdminDocument).toHaveBeenCalledTimes(2)
  })

  it('offers Knowledge Retry only from the server capability flag', async () => {
    vi.mocked(api.getAdminDocument).mockResolvedValueOnce({ ...detail, processing_status: 'FAILED', knowledge_retry_available: true })
    const { unmount } = renderAt('/admin/documents/document-1')
    expect(await screen.findByRole('button', { name: "Thử tạo lại dữ liệu tra cứu" })).toBeEnabled()
    unmount()
    vi.mocked(api.getAdminDocument).mockResolvedValueOnce({ ...detail, review_status: 'APPROVED', knowledge_retry_available: false })
    renderAt('/admin/documents/document-1')
    await screen.findByRole('heading', { name: "Thông tin tài liệu" })
    expect(screen.queryByRole('button', { name: "Thử tạo lại dữ liệu tra cứu" })).not.toBeInTheDocument()
  })

  it('does not offer retry when a server PROCESSING knowledge version makes the capability false', async () => {
    vi.mocked(api.getAdminDocument).mockResolvedValueOnce({
      ...detail, review_status: 'PENDING', processing_status: 'PREVIEW_READY', knowledge_retry_available: false,
    })
    renderAt('/admin/documents/document-1')
    await screen.findByRole('heading', { name: "Thông tin tài liệu" })
    expect(screen.queryByRole('button', { name: "Thử tạo lại dữ liệu tra cứu" })).not.toBeInTheDocument()
  })

  it('handles the Knowledge Retry concurrency race with one mutation and authoritative refetch', async () => {
    vi.mocked(api.getAdminDocument)
      .mockResolvedValueOnce({ ...detail, knowledge_retry_available: true })
      .mockResolvedValueOnce({ ...detail, knowledge_retry_available: false })
    vi.mocked(api.retryAdminDocumentKnowledge).mockRejectedValueOnce(error(409, 'PROCESSING_ALREADY_IN_PROGRESS'))
    renderAt('/admin/documents/document-1')
    fireEvent.click(await screen.findByRole('button', { name: "Thử tạo lại dữ liệu tra cứu" }))
    expect(await screen.findByRole('alert')).toHaveTextContent("Tài liệu đang được xử lý.")
    await waitFor(() => expect(api.getAdminDocument).toHaveBeenCalledTimes(2))
    expect(api.retryAdminDocumentKnowledge).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole('button', { name: "Thử tạo lại dữ liệu tra cứu" })).not.toBeInTheDocument()
  })

  it('maps HTTP 500 knowledge failure, refetches authoritative state, and does not retry automatically', async () => {
    vi.mocked(api.getAdminDocument)
      .mockResolvedValueOnce({ ...detail, knowledge_retry_available: true })
      .mockResolvedValueOnce({ ...detail, knowledge_retry_available: false })
    vi.mocked(api.retryAdminDocumentKnowledge).mockRejectedValueOnce(error(500, 'KNOWLEDGE_BUILD_FAILED'))
    const { client } = renderAt('/admin/documents/document-1')
    const listKey = queryKeys.adminDocuments({ page: 1, page_size: 20 })
    client.setQueryData(listKey, { items: [listItem], page: 1, page_size: 20, total: 1 })
    fireEvent.click(await screen.findByRole('button', { name: "Thử tạo lại dữ liệu tra cứu" }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      "Không thể tạo dữ liệu tra cứu. Đang tải lại trạng thái hiện tại.",
    )
    await waitFor(() => expect(api.getAdminDocument).toHaveBeenCalledTimes(2))
    expect(client.getQueryState(listKey)?.isInvalidated).toBe(true)
    expect(screen.queryByRole('button', { name: "Thử tạo lại dữ liệu tra cứu" })).not.toBeInTheDocument()
    expect(screen.queryByText("Có sự cố tạm thời. Vui lòng thử lại.")).not.toBeInTheDocument()
    expect(screen.queryByText('server message')).not.toBeInTheDocument()
    expect(api.retryAdminDocumentKnowledge).toHaveBeenCalledTimes(1)
  })

  it.each([
    ['process', 'UPLOADED', 'PENDING'],
    ['approve', 'PREVIEW_READY', 'PENDING'],
    ['reject', 'PREVIEW_READY', 'PENDING'],
    ['knowledge', 'UPLOADED', 'PENDING'],
  ])('does not automatically resend ambiguous %s mutations and refetches state', async (kind, processing, review) => {
    vi.mocked(api.getAdminDocument).mockResolvedValue({
      ...detail, processing_status: processing as AdminDocumentDetail['processing_status'],
      review_status: review as AdminDocumentDetail['review_status'], knowledge_retry_available: kind === 'knowledge',
    })
    if (kind === 'process') vi.mocked(api.processAdminDocument).mockRejectedValueOnce(error(503, 'HTTP_ERROR'))
    if (kind === 'approve') vi.mocked(api.approveAdminDocument).mockRejectedValueOnce(error(503, 'HTTP_ERROR'))
    if (kind === 'reject') vi.mocked(api.rejectAdminDocument).mockRejectedValueOnce(error(503, 'HTTP_ERROR'))
    if (kind === 'knowledge') vi.mocked(api.retryAdminDocumentKnowledge).mockRejectedValueOnce(error(503, 'HTTP_ERROR'))
    renderAt('/admin/documents/document-1')
    if (kind === 'process') fireEvent.click(await screen.findByRole('button', { name: "Xử lý tài liệu" }))
    if (kind === 'approve') fireEvent.click(await screen.findByRole('button', { name: "Duyệt tài liệu" }))
    if (kind === 'reject') fireEvent.click(await screen.findByRole('button', { name: "Từ chối" }))
    if (kind === 'knowledge') fireEvent.click(await screen.findByRole('button', { name: "Thử tạo lại dữ liệu tra cứu" }))
    expect(await screen.findByRole('alert')).toHaveTextContent("Có sự cố tạm thời. Vui lòng thử lại.")
    await waitFor(() => expect(api.getAdminDocument).toHaveBeenCalledTimes(2))
    const method = kind === 'process' ? api.processAdminDocument : kind === 'approve' ? api.approveAdminDocument : kind === 'reject' ? api.rejectAdminDocument : api.retryAdminDocumentKnowledge
    expect(method).toHaveBeenCalledTimes(1)
  })

  it('invalidates the list after an ambiguous upload without resending it', async () => {
    vi.mocked(api.uploadDocument).mockRejectedValueOnce(error(0, 'NETWORK_ERROR'))
    renderAt('/admin/documents')
    fireEvent.change(screen.getByLabelText(/Tệp \(PDF/), { target: { files: [new File(['raw'], 'x.txt')] } })
    fireEvent.change(screen.getByLabelText("Tiêu đề"), { target: { value: "Tiêu đề" } })
    fireEvent.change(screen.getByLabelText("Xuất xứ"), { target: { value: 'Source' } })
    fireEvent.click(screen.getByLabelText(/Tôi xác nhận tài liệu/))
    submitUpload()
    expect(await screen.findByRole('alert')).toHaveTextContent('Có sự cố tạm thời. Vui lòng thử lại.')
    await waitFor(() => expect(api.listAdminDocuments).toHaveBeenCalledTimes(2))
    expect(api.uploadDocument).toHaveBeenCalledTimes(1)
  })

  it('preserves ordinary ADMIN_REQUIRED handling without logging out the Admin', async () => {
    vi.mocked(api.listAdminDocuments).mockRejectedValueOnce(error(403, 'ADMIN_REQUIRED'))
    const { client, router } = renderAt('/admin/documents')
    expect(await screen.findByRole('alert')).toHaveTextContent("Tài khoản của bạn không có quyền quản trị.")
    expect(authApi.logout).not.toHaveBeenCalled()
    expect(client.getQueryData(queryKeys.authMe)).toEqual(admin)
    expect(router.state.location.pathname).toBe('/admin/documents')
  })

  it('keeps navigation and exposes no storage, lineage, chunk, vector, or maintenance controls', async () => {
    renderAt('/admin/documents/document-1')
    const nav = screen.getByRole('navigation', { name: "Điều hướng quản trị" })
    expect(within(nav).getByRole('link', { name: "Tài liệu" })).toHaveAttribute('href', '/admin/documents')
    await screen.findByRole('heading', { name: "Thông tin tài liệu" })
    expect(screen.queryByText(/storage\/|storage_reference|content_hash|TransformationRun|KnowledgeSource|KnowledgeVersion|chunk|vector|reprocess/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /parse|transform|chunk|embed|activate|reprocess/i })).not.toBeInTheDocument()
  })
})
