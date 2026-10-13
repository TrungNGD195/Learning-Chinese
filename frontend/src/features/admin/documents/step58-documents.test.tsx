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

const admin = { id: 'admin-1', email: 'admin@example.test', full_name: 'Admin', role: 'ADMIN' as const }
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
  const input = screen.getByLabelText(/File \(PDF/)
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
    expect(await screen.findByRole('heading', { name: 'Admin Documents' })).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: 'Open document' })).toHaveAttribute('href', '/admin/documents/document-1')
    expect(screen.getByText('Chinese lesson')).toBeInTheDocument()
    expect(screen.getByText('UPLOADED')).toBeInTheDocument()
    expect(screen.getByText('PENDING')).toBeInTheDocument()
    expect(screen.queryByText('Document management will be implemented in Phase 5.')).not.toBeInTheDocument()
    expect(api.listAdminDocuments).toHaveBeenCalledWith({ page: 1, page_size: 20 })
  })

  it('shows list loading, empty, and error states', async () => {
    vi.mocked(api.listAdminDocuments).mockImplementationOnce(() => new Promise(() => {}))
    const loading = renderAt('/admin/documents')
    expect(screen.getByRole('status')).toHaveTextContent('Loading documents')
    loading.unmount()

    vi.mocked(api.listAdminDocuments).mockResolvedValueOnce({ items: [], page: 1, page_size: 20, total: 0 })
    renderAt('/admin/documents')
    expect(await screen.findByText('No documents have been uploaded.')).toBeInTheDocument()
  })

  it('paginates using the server page/page_size values', async () => {
    vi.mocked(api.listAdminDocuments)
      .mockResolvedValueOnce({ items: [listItem], page: 1, page_size: 20, total: 21 })
      .mockResolvedValueOnce({ items: [{ ...listItem, id: 'document-21' }], page: 2, page_size: 20, total: 21 })
    renderAt('/admin/documents')
    fireEvent.click(await screen.findByRole('button', { name: 'Next' }))
    await waitFor(() => expect(api.listAdminDocuments).toHaveBeenLastCalledWith({ page: 2, page_size: 20 }))
    expect(await screen.findByText('Page 2')).toBeInTheDocument()
  })

  it.each(['lesson.pdf', 'lesson.docx', 'lesson.txt', 'lesson.md'])(
    'submits supported upload file %s with required metadata and domain attestation', async (filename) => {
      renderAt('/admin/documents')
      const file = new File(['raw bytes'], filename, { type: 'text/plain' })
      fireEvent.change(screen.getByLabelText(/File \(PDF/), { target: { files: [file] } })
      fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'New source' } })
      fireEvent.change(screen.getByLabelText('Source origin'), { target: { value: 'Author' } })
      fireEvent.click(screen.getByLabelText(/I confirm this source/))
      const button = screen.getByRole('button', { name: 'Upload document' })
      expect(button).toBeEnabled()
      submitUpload()
      await waitFor(() => expect(api.uploadDocument).toHaveBeenCalledTimes(1))
      expect(api.uploadDocument).toHaveBeenCalledWith(expect.objectContaining({
        file, title: 'New source', source_category: 'CURRICULUM_MATERIAL', source_origin: 'Author',
        source_language: 'zh', domain_allowed: true, usage_rights_note: null,
      }))
      expect(await screen.findByText(/Raw source stored/)).toBeInTheDocument()
      expect(screen.getByRole('link', { name: 'Open document detail' })).toHaveAttribute('href', '/admin/documents/document-2')
      expect(screen.queryByText(/APPROVED|ACTIVE/)).not.toBeInTheDocument()
    },
  )

  it('keeps upload attestation required and sends an optional rights note only when supplied', async () => {
    renderAt('/admin/documents')
    const file = new File(['raw'], 'book.pdf', { type: 'application/pdf' })
    fireEvent.change(screen.getByLabelText(/File \(PDF/), { target: { files: [file] } })
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Book' } })
    fireEvent.change(screen.getByLabelText('Source origin'), { target: { value: 'Publisher' } })
    expect(screen.getByRole('button', { name: 'Upload document' })).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Usage rights note (optional)'), { target: { value: 'Licensed for study' } })
    fireEvent.click(screen.getByLabelText(/I confirm this source/))
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
    ['UNSUPPORTED_DOCUMENT_TYPE', 'Upload a PDF, DOCX, TXT, or MD file.'],
    ['DOCUMENT_TOO_LARGE', "The document exceeds the server's configured upload limit."],
    ['EMPTY_DOCUMENT', 'The selected document is empty.'],
    ['INVALID_DOCUMENT_FILE', 'The selected file is invalid or does not match its declared format.'],
    ['DUPLICATE_DOCUMENT', 'An identical document has already been uploaded.'],
  ])('shows a safe upload message for %s', async (code, message) => {
    vi.mocked(api.uploadDocument).mockRejectedValueOnce(error(422, code))
    renderAt('/admin/documents')
    fireEvent.change(screen.getByLabelText(/File \(PDF/), { target: { files: [new File(['raw'], 'x.txt')] } })
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Title' } })
    fireEvent.change(screen.getByLabelText('Source origin'), { target: { value: 'Source' } })
    fireEvent.click(screen.getByLabelText(/I confirm this source/))
    submitUpload()
    expect(await screen.findByRole('alert')).toHaveTextContent(message)
    expect(api.uploadDocument).toHaveBeenCalledTimes(1)
  })

  it('shows the mapped RAW_STORAGE_FAILED message for HTTP 500 without replacing it with the generic fallback', async () => {
    vi.mocked(api.uploadDocument).mockRejectedValueOnce(error(500, 'RAW_STORAGE_FAILED'))
    renderAt('/admin/documents')
    fireEvent.change(screen.getByLabelText(/File \(PDF/), { target: { files: [new File(['raw'], 'book.pdf')] } })
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Book' } })
    fireEvent.change(screen.getByLabelText('Source origin'), { target: { value: 'Publisher' } })
    fireEvent.click(screen.getByLabelText(/I confirm this source/))
    submitUpload()
    expect(await screen.findByRole('alert')).toHaveTextContent('The document could not be stored. Retry when safe.')
    expect(screen.queryByText('A temporary problem prevented this action. Please retry.')).not.toBeInTheDocument()
    expect(screen.queryByText('server message')).not.toBeInTheDocument()
    expect(api.uploadDocument).toHaveBeenCalledTimes(1)
  })

  it('supports a deep-linked detail page with separate processing and review statuses', async () => {
    renderAt('/admin/documents/document-1')
    expect(await screen.findByRole('heading', { name: 'Admin Document' })).toBeInTheDocument()
    expect(await screen.findByText('Chinese lesson')).toBeInTheDocument()
    expect(screen.getByText('Processing status')).toBeInTheDocument()
    expect(screen.getByText('Review status')).toBeInTheDocument()
    expect(screen.getByText('UPLOADED')).toBeInTheDocument()
    expect(screen.getByText('PENDING')).toBeInTheDocument()
    expect(api.getAdminDocument).toHaveBeenCalledWith('document-1')
  })

  it('shows detail loading, not-found, and retryable error states', async () => {
    vi.mocked(api.getAdminDocument).mockImplementationOnce(() => new Promise(() => {}))
    const loading = renderAt('/admin/documents/document-1')
    expect(screen.getByRole('status')).toHaveTextContent('Loading document')
    loading.unmount()

    vi.mocked(api.getAdminDocument).mockRejectedValueOnce(error(404, 'NOT_FOUND'))
    renderAt('/admin/documents/missing')
    expect(await screen.findByRole('alert')).toHaveTextContent('Document not found.')
    expect(screen.getByRole('link', { name: 'Back to Documents' })).toHaveAttribute('href', '/admin/documents')
  })

  it.each([
    ['PENDING', 'UPLOADED', 'Process'],
    ['PENDING', 'FAILED', 'Retry Processing'],
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
    await screen.findByRole('heading', { name: 'Admin Document' })
    expect(screen.queryByRole('button', { name: 'Process' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Retry Processing' })).not.toBeInTheDocument()
  })

  it('shows synchronous Process pending state and invalidates list/detail state', async () => {
    let finish!: () => void
    vi.mocked(api.processAdminDocument).mockImplementationOnce(() => new Promise<void>((resolve) => { finish = resolve }))
    const { client } = renderAt('/admin/documents/document-1')
    const listKey = queryKeys.adminDocuments({ page: 1, page_size: 20 })
    client.setQueryData(listKey, { items: [listItem], page: 1, page_size: 20, total: 1 })
    fireEvent.click(await screen.findByRole('button', { name: 'Process' }))
    expect(await screen.findByRole('button', { name: 'Processing…' })).toBeDisabled()
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
    fireEvent.click(await screen.findByRole('button', { name: 'Process' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Processing failed. Reload the document before deciding whether to retry.',
    )
    await waitFor(() => expect(api.getAdminDocument).toHaveBeenCalledTimes(2))
    expect(screen.getByText('PENDING', { selector: 'dd' })).toBeInTheDocument()
    expect(screen.getByText('FAILED', { selector: 'dd' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retry Processing' })).toBeEnabled()
    expect(screen.queryByText('A temporary problem prevented this action. Please retry.')).not.toBeInTheDocument()
    expect(screen.queryByText('server message')).not.toBeInTheDocument()
    expect(api.processAdminDocument).toHaveBeenCalledTimes(1)
  })

  it('loads and renders only the transformed preview for a reviewable candidate', async () => {
    vi.mocked(api.getAdminDocument).mockResolvedValueOnce({ ...detail, processing_status: 'PREVIEW_READY' })
    renderAt('/admin/documents/document-1')
    expect(await screen.findByRole('heading', { name: 'Transformed preview' })).toBeInTheDocument()
    expect(screen.getByText('你好')).toBeInTheDocument()
    expect(screen.getByText('Page 2')).toBeInTheDocument()
    expect(api.getAdminDocumentPreview).toHaveBeenCalledWith('document-1')
    expect(screen.queryByText(/storage_reference|TransformationRun|KnowledgeVersion|Chunk|vector/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /parse|transform|chunk|embed|activate|reprocess/i })).not.toBeInTheDocument()
  })

  it('gates review actions and renders authoritative approval after rejecting a re-review candidate', async () => {
    vi.mocked(api.getAdminDocument)
      .mockResolvedValueOnce({ ...detail, processing_status: 'PREVIEW_READY' })
      .mockResolvedValueOnce({ ...detail, processing_status: 'PREVIEW_READY', review_status: 'APPROVED' })
    renderAt('/admin/documents/document-1')
    fireEvent.click(await screen.findByRole('button', { name: 'Reject' }))
    await waitFor(() => expect(api.rejectAdminDocument).toHaveBeenCalledTimes(1))
    expect(await screen.findByText('APPROVED', { selector: 'dd' })).toBeInTheDocument()
    expect(screen.getByText(/does not mean the knowledge is active for retrieval/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Approve' })).not.toBeInTheDocument()
  })

  it('refetches after successful approval rather than optimistically changing the lifecycle', async () => {
    vi.mocked(api.getAdminDocument)
      .mockResolvedValueOnce({ ...detail, processing_status: 'PREVIEW_READY' })
      .mockResolvedValueOnce({ ...detail, processing_status: 'PREVIEW_READY', review_status: 'APPROVED' })
    renderAt('/admin/documents/document-1')
    fireEvent.click(await screen.findByRole('button', { name: 'Approve' }))
    await waitFor(() => expect(api.approveAdminDocument).toHaveBeenCalledTimes(1))
    expect(await screen.findByText('APPROVED', { selector: 'dd' })).toBeInTheDocument()
    expect(api.getAdminDocument).toHaveBeenCalledTimes(2)
  })

  it('offers Knowledge Retry only from the server capability flag', async () => {
    vi.mocked(api.getAdminDocument).mockResolvedValueOnce({ ...detail, processing_status: 'FAILED', knowledge_retry_available: true })
    const { unmount } = renderAt('/admin/documents/document-1')
    expect(await screen.findByRole('button', { name: 'Retry Knowledge Build' })).toBeEnabled()
    unmount()
    vi.mocked(api.getAdminDocument).mockResolvedValueOnce({ ...detail, review_status: 'APPROVED', knowledge_retry_available: false })
    renderAt('/admin/documents/document-1')
    await screen.findByRole('heading', { name: 'Admin Document' })
    expect(screen.queryByRole('button', { name: 'Retry Knowledge Build' })).not.toBeInTheDocument()
  })

  it('does not offer retry when a server PROCESSING knowledge version makes the capability false', async () => {
    vi.mocked(api.getAdminDocument).mockResolvedValueOnce({
      ...detail, review_status: 'PENDING', processing_status: 'PREVIEW_READY', knowledge_retry_available: false,
    })
    renderAt('/admin/documents/document-1')
    await screen.findByRole('heading', { name: 'Admin Document' })
    expect(screen.queryByRole('button', { name: 'Retry Knowledge Build' })).not.toBeInTheDocument()
  })

  it('handles the Knowledge Retry concurrency race with one mutation and authoritative refetch', async () => {
    vi.mocked(api.getAdminDocument)
      .mockResolvedValueOnce({ ...detail, knowledge_retry_available: true })
      .mockResolvedValueOnce({ ...detail, knowledge_retry_available: false })
    vi.mocked(api.retryAdminDocumentKnowledge).mockRejectedValueOnce(error(409, 'PROCESSING_ALREADY_IN_PROGRESS'))
    renderAt('/admin/documents/document-1')
    fireEvent.click(await screen.findByRole('button', { name: 'Retry Knowledge Build' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('This document is already being processed.')
    await waitFor(() => expect(api.getAdminDocument).toHaveBeenCalledTimes(2))
    expect(api.retryAdminDocumentKnowledge).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole('button', { name: 'Retry Knowledge Build' })).not.toBeInTheDocument()
  })

  it('maps HTTP 500 knowledge failure, refetches authoritative state, and does not retry automatically', async () => {
    vi.mocked(api.getAdminDocument)
      .mockResolvedValueOnce({ ...detail, knowledge_retry_available: true })
      .mockResolvedValueOnce({ ...detail, knowledge_retry_available: false })
    vi.mocked(api.retryAdminDocumentKnowledge).mockRejectedValueOnce(error(500, 'KNOWLEDGE_BUILD_FAILED'))
    const { client } = renderAt('/admin/documents/document-1')
    const listKey = queryKeys.adminDocuments({ page: 1, page_size: 20 })
    client.setQueryData(listKey, { items: [listItem], page: 1, page_size: 20, total: 1 })
    fireEvent.click(await screen.findByRole('button', { name: 'Retry Knowledge Build' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The knowledge build could not be started or completed; current state is reloading.',
    )
    await waitFor(() => expect(api.getAdminDocument).toHaveBeenCalledTimes(2))
    expect(client.getQueryState(listKey)?.isInvalidated).toBe(true)
    expect(screen.queryByRole('button', { name: 'Retry Knowledge Build' })).not.toBeInTheDocument()
    expect(screen.queryByText('A temporary problem prevented this action. Please retry.')).not.toBeInTheDocument()
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
    if (kind === 'process') fireEvent.click(await screen.findByRole('button', { name: 'Process' }))
    if (kind === 'approve') fireEvent.click(await screen.findByRole('button', { name: 'Approve' }))
    if (kind === 'reject') fireEvent.click(await screen.findByRole('button', { name: 'Reject' }))
    if (kind === 'knowledge') fireEvent.click(await screen.findByRole('button', { name: 'Retry Knowledge Build' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('A temporary problem prevented this action. Please retry.')
    await waitFor(() => expect(api.getAdminDocument).toHaveBeenCalledTimes(2))
    const method = kind === 'process' ? api.processAdminDocument : kind === 'approve' ? api.approveAdminDocument : kind === 'reject' ? api.rejectAdminDocument : api.retryAdminDocumentKnowledge
    expect(method).toHaveBeenCalledTimes(1)
  })

  it('invalidates the list after an ambiguous upload without resending it', async () => {
    vi.mocked(api.uploadDocument).mockRejectedValueOnce(error(0, 'NETWORK_ERROR'))
    renderAt('/admin/documents')
    fireEvent.change(screen.getByLabelText(/File \(PDF/), { target: { files: [new File(['raw'], 'x.txt')] } })
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Title' } })
    fireEvent.change(screen.getByLabelText('Source origin'), { target: { value: 'Source' } })
    fireEvent.click(screen.getByLabelText(/I confirm this source/))
    submitUpload()
    expect(await screen.findByRole('alert')).toHaveTextContent('A temporary problem prevented this action.')
    await waitFor(() => expect(api.listAdminDocuments).toHaveBeenCalledTimes(2))
    expect(api.uploadDocument).toHaveBeenCalledTimes(1)
  })

  it('preserves ordinary ADMIN_REQUIRED handling without logging out the Admin', async () => {
    vi.mocked(api.listAdminDocuments).mockRejectedValueOnce(error(403, 'ADMIN_REQUIRED'))
    const { client, router } = renderAt('/admin/documents')
    expect(await screen.findByRole('alert')).toHaveTextContent('Your account does not have Admin access.')
    expect(authApi.logout).not.toHaveBeenCalled()
    expect(client.getQueryData(queryKeys.authMe)).toEqual(admin)
    expect(router.state.location.pathname).toBe('/admin/documents')
  })

  it('keeps navigation and exposes no storage, lineage, chunk, vector, or maintenance controls', async () => {
    renderAt('/admin/documents/document-1')
    const nav = screen.getByRole('navigation', { name: 'Admin navigation' })
    expect(within(nav).getByRole('link', { name: 'Documents' })).toHaveAttribute('href', '/admin/documents')
    await screen.findByRole('heading', { name: 'Admin Document' })
    expect(screen.queryByText(/storage\/|storage_reference|content_hash|TransformationRun|KnowledgeSource|KnowledgeVersion|chunk|vector|reprocess/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /parse|transform|chunk|embed|activate|reprocess/i })).not.toBeInTheDocument()
  })
})
