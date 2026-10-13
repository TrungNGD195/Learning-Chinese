import { afterEach, describe, expect, it, vi } from 'vitest'
import { authApi, changePassword, login } from './auth/api'
import { getDashboard } from './dashboard/api'
import { completeSection } from './pronunciation/api'
import { getAttempts } from './assessment/api'
import { listConversations, getMessages, renameConversation } from './conversation/api'
import { listAdminLessons, updateHskLevel, listLessonVocabulary } from './admin/api'
import * as adminApiExports from './admin/api'

afterEach(() => {
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
})

function mockFetch(body: unknown, status = 200) {
  const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(
    status === 204 ? new Response(null, { status }) : new Response(JSON.stringify(body), { status }),
  ))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('feature API wrappers', () => {
  it('exports all accepted Auth operations and login delegates with the generated request body', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000/api/v1')
    const fetchMock = mockFetch({ id: 'user-id', email: 'learner@example.test' })

    await login({ email: 'learner@example.test', password: 'test-only-password' })

    expect(Object.keys(authApi)).toEqual([
      'register', 'login', 'getMe', 'refresh', 'logout', 'logoutAll',
      'changePassword', 'requestPasswordReset', 'confirmPasswordReset',
    ])
    expect(fetchMock.mock.calls[0][0]).toBe('http://localhost:8000/api/v1/auth/login')
    expect(JSON.parse((fetchMock.mock.calls[0][1] as RequestInit).body as string)).toEqual({
      email: 'learner@example.test', password: 'test-only-password',
    })
  })

  it('implements changePassword and an empty-success Auth wrapper', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    const fetchMock = mockFetch(null, 204)

    await expect(changePassword({ current_password: 'old-test-password', new_password: 'new-test-password' })).resolves.toBeUndefined()
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/auth/change-password')
    expect((fetchMock.mock.calls[0][1] as RequestInit).credentials).toBe('include')
  })

  it('maps learner reads and mutations through apiClient', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    const fetchMock = mockFetch({ status: 'COMPLETED' })

    await getDashboard()
    await completeSection('section-id')

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      '/api/v1/me/dashboard',
      '/api/v1/pronunciation/section-id/complete',
    ])
  })

  it('serializes accepted assessment history filters', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    const fetchMock = mockFetch({ items: [], page: 2, page_size: 10, total: 0 })

    await getAttempts({
      page: 2,
      page_size: 10,
      assessment_id: '11111111-1111-1111-1111-111111111111',
      lesson_id: '22222222-2222-2222-2222-222222222222',
      assessment_type: 'PERIODIC_TEST',
    })

    expect(fetchMock.mock.calls[0][0]).toBe(
      '/api/v1/me/assessment-attempts?page=2&page_size=10&assessment_id=11111111-1111-1111-1111-111111111111&lesson_id=22222222-2222-2222-2222-222222222222&assessment_type=PERIODIC_TEST',
    )
  })

  it('preserves Conversation list and message pagination/filter semantics', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    const fetchMock = mockFetch({ items: [], page: 1, page_size: 20, total: 0 })

    await listConversations({ page: 3, page_size: 12, lesson_id: 'lesson-id', scope: 'LESSON' })
    await getMessages('conversation-id', { page: 2, page_size: 25 })

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      '/api/v1/me/conversations?page=3&page_size=12&lesson_id=lesson-id&scope=LESSON',
      '/api/v1/conversations/conversation-id/messages?page=2&page_size=25',
    ])
  })

  it('maps Conversation rename as a JSON mutation', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    const fetchMock = mockFetch({ id: 'conversation-id', title: 'New title' })

    await renameConversation('conversation-id', { title: 'New title' })

    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/conversations/conversation-id')
    expect((fetchMock.mock.calls[0][1] as RequestInit).method).toBe('PATCH')
    expect((fetchMock.mock.calls[0][1] as RequestInit).body).toBe('{"title":"New title"}')
  })

  it('maps Admin list, mutation, and lesson-content operations', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '/api/v1')
    const fetchMock = mockFetch([])

    await listAdminLessons({ status: 'DRAFT', page: 2, page_size: 15 })
    await updateHskLevel('hsk-id', {})
    await listLessonVocabulary('lesson-id')

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      '/api/v1/admin/lessons?status=DRAFT&page=2&page_size=15',
      '/api/v1/admin/hsk-levels/hsk-id',
      '/api/v1/admin/lessons/lesson-id/vocabulary',
    ])
    expect((fetchMock.mock.calls[1][1] as RequestInit).method).toBe('PATCH')
    expect((fetchMock.mock.calls[1][1] as RequestInit).body).toBe('{}')
  })

  it('exposes the frozen Document Admin wrappers without pipeline internals', () => {
    const names = Object.keys(adminApiExports)
    expect(names).toEqual(expect.arrayContaining([
      'listAdminDocuments', 'getAdminDocument', 'getAdminDocumentPreview', 'uploadDocument',
      'processAdminDocument', 'approveAdminDocument', 'rejectAdminDocument', 'retryAdminDocumentKnowledge',
    ]))
    expect(names.some((name) => /ingestion|chunk|embedding|reprocess|lineage/i.test(name))).toBe(false)
  })
})
