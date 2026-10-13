import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { components } from '../../types/api.generated'
import { ApiError } from '../../lib/api/errors'
import { getHskLevels } from '../curriculum/api'
import { getLesson } from '../lesson/api'
import { getLessonProgress } from '../progress/api'
import {
  createConversation,
  deleteConversation,
  getConversation,
  getMessages,
  listConversations,
  renameConversation,
  retryAssistantMessage,
  sendMessage,
} from './api'
import { AssistantMarkdown } from './AssistantMarkdown'
import { LessonPage } from '../lesson/LessonPage'

vi.mock('./api', () => ({
  createConversation: vi.fn(),
  deleteConversation: vi.fn(),
  getConversation: vi.fn(),
  getMessages: vi.fn(),
  listConversations: vi.fn(),
  renameConversation: vi.fn(),
  retryAssistantMessage: vi.fn(),
  sendMessage: vi.fn(),
}))
vi.mock('../lesson/api', () => ({ getLesson: vi.fn(), markGrammarViewed: vi.fn(), markVocabularyViewed: vi.fn() }))
vi.mock('../progress/api', () => ({ getLessonProgress: vi.fn(), getHskProgress: vi.fn(), getProgressOverview: vi.fn() }))
vi.mock('../curriculum/api', () => ({ getCurriculum: vi.fn(), getHskLevels: vi.fn() }))

type Conversation = components['schemas']['ConversationResponse']
type Message = components['schemas']['MessageResponse']
type Lesson = components['schemas']['LessonResponse']
type LessonProgress = components['schemas']['LessonProgressResponse']
type ConversationPage = components['schemas']['ConversationPage']
type MessagePage = components['schemas']['MessagePage']

const timestamp = '2026-09-27T10:00:00Z'

function conversation(id: string, title: string | null = id, updated = timestamp): Conversation {
  return { id, scope: 'LESSON', lesson_id: 'lesson-1', title, created_at: timestamp, updated_at: updated }
}

function conversationPage(items: Conversation[], page = 1, pageSize = 20, total = items.length): ConversationPage {
  return { items, page, page_size: pageSize, total }
}

function message(id: string, sequence: number, role: Message['role'] = 'USER', content: string | null = `Message ${sequence}`, status: Message['status'] = 'COMPLETED', replyTo: string | null = null): Message {
  return { id, conversation_id: 'conversation-a', sequence_number: sequence, role, content, status, reply_to_message_id: replyTo, created_at: sequence % 2 ? '2026-01-01T00:00:00Z' : '2026-12-31T23:59:59Z', citations: [] }
}

function messagePage(items: Message[], page = 1, pageSize = 50, total = items.length): MessagePage {
  return { items, page, page_size: pageSize, total }
}

function mockChatScrollMetrics() {
  const previousHeight = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'scrollHeight')
  const previousClientHeight = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'clientHeight')
  Object.defineProperty(HTMLElement.prototype, 'scrollHeight', {
    configurable: true,
    get() { return this.classList?.contains('chat-message-scroll') ? this.querySelectorAll('[data-sequence]').length * 100 : 0 },
  })
  Object.defineProperty(HTMLElement.prototype, 'clientHeight', { configurable: true, value: 50 })
  return () => {
    if (previousHeight) Object.defineProperty(HTMLElement.prototype, 'scrollHeight', previousHeight)
    else Reflect.deleteProperty(HTMLElement.prototype, 'scrollHeight')
    if (previousClientHeight) Object.defineProperty(HTMLElement.prototype, 'clientHeight', previousClientHeight)
    else Reflect.deleteProperty(HTMLElement.prototype, 'clientHeight')
  }
}

function lessonFixture(): Lesson {
  return { id: 'lesson-1', hsk_level_id: 'hsk-1', lesson_number: 3, title: 'Greetings', description: null, vocabulary: [], grammar: [], assessment_ids: ['exercise-1'] }
}

function progressFixture(): LessonProgress {
  return { lesson_id: 'lesson-1', started_at: timestamp, theory_completed_at: null, completed_at: null, vocabulary: [], grammar: [] }
}

function renderLesson() {
  const router = createMemoryRouter([
    { path: '/lessons/:lessonId', element: <LessonPage /> },
    { path: '*', element: <p>Not found</p> },
  ], { initialEntries: ['/lessons/lesson-1'] })
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={queryClient}><RouterProvider router={router} /></QueryClientProvider>)
}

async function openChat() {
  fireEvent.click(await screen.findByRole('button', { name: 'Open AI chat' }))
  return screen.findByRole('dialog', { name: 'AI Tutor Chat' })
}

async function openExistingConversation(items = [conversation('conversation-a', 'First')], useConfiguredList = false) {
  if (!useConfiguredList) vi.mocked(listConversations).mockResolvedValue(conversationPage(items))
  renderLesson()
  const panel = await openChat()
  await screen.findByRole('heading', { name: items[0].title ?? 'Untitled conversation', level: 2 })
  return panel
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(getLesson).mockResolvedValue(lessonFixture())
  vi.mocked(getLessonProgress).mockResolvedValue(progressFixture())
  vi.mocked(getHskLevels).mockResolvedValue([{ id: 'hsk-1', level_number: 1, title: 'HSK 1', description: null, state: 'AVAILABLE' }])
  vi.mocked(listConversations).mockResolvedValue(conversationPage([]))
  vi.mocked(getConversation).mockImplementation(async (id) => conversation(id))
  vi.mocked(getMessages).mockResolvedValue(messagePage([]))
  vi.mocked(createConversation).mockResolvedValue(conversation('conversation-new', 'New chat'))
  vi.mocked(renameConversation).mockImplementation(async (id, body) => conversation(id, body.title))
  vi.mocked(deleteConversation).mockResolvedValue(undefined)
  vi.mocked(sendMessage).mockResolvedValue({
    user_message: message('server-user', 1, 'USER', 'Hello'),
    assistant_message: message('server-assistant', 2, 'ASSISTANT', '你好', 'COMPLETED', 'server-user'),
  })
  vi.mocked(retryAssistantMessage).mockResolvedValue(message('retry-assistant', 4, 'ASSISTANT', 'A second attempt', 'COMPLETED', 'user-1'))
})

describe('Step 4.4 placement and explicit Conversation lifecycle', () => {
  it('shows a Conversation list error and retries the list query', async () => {
    vi.mocked(listConversations).mockRejectedValueOnce(new Error('temporary list failure')).mockResolvedValue(conversationPage([conversation('conversation-a', 'Recovered')]))
    renderLesson()
    const panel = await openChat()
    expect(await within(panel).findByRole('alert')).toHaveTextContent('Could not load conversations')
    fireEvent.click(within(panel).getByRole('button', { name: 'Retry' }))
    expect(await within(panel).findByRole('heading', { name: 'Recovered', level: 2 })).toBeInTheDocument()
  })

  it('keeps AI Chat inside Lesson and panel opening only loads the current Lesson list', async () => {
    renderLesson()
    const lessonHeading = await screen.findByRole('heading', { name: 'Lesson 3: Greetings' })
    const lessonScreen = lessonHeading.closest('section') as HTMLElement
    expect(within(lessonScreen).getByRole('heading', { name: 'AI Chat' })).toBeInTheDocument()
    const panel = await openChat()
    expect(panel).toHaveTextContent('HSK 1 · Lesson 3')
    expect(listConversations).toHaveBeenCalledWith({ lesson_id: 'lesson-1', page: 1, page_size: 20 })
    expect(createConversation).not.toHaveBeenCalled()
    expect(sendMessage).not.toHaveBeenCalled()
    expect(screen.queryByRole('link', { name: /open exercise/i })).toBeInTheDocument()
  })

  it('creates only after explicit Start with exactly lesson_id and does not send a Message', async () => {
    vi.mocked(createConversation).mockResolvedValue(conversation('conversation-new', null))
    vi.mocked(listConversations).mockResolvedValueOnce(conversationPage([])).mockResolvedValue(conversationPage([conversation('conversation-new', null)]))
    renderLesson()
    const panel = await openChat()
    expect(await within(panel).findByText('Ask AI about this lesson')).toBeInTheDocument()
    expect(within(panel).getByRole('button', { name: 'Start a conversation' })).toBeInTheDocument()
    expect(createConversation).not.toHaveBeenCalled()
    fireEvent.click(within(panel).getByRole('button', { name: 'Start a conversation' }))
    expect(await within(panel).findByRole('heading', { name: 'Untitled conversation', level: 2 })).toBeInTheDocument()
    expect(createConversation).toHaveBeenCalledExactlyOnceWith({ lesson_id: 'lesson-1' })
    expect(listConversations).toHaveBeenCalledTimes(2)
    expect(getMessages).toHaveBeenCalledWith('conversation-new', { page: 1, page_size: 50 })
    expect(sendMessage).not.toHaveBeenCalled()
    expect(within(panel).getByRole('textbox', { name: 'Message' })).toHaveValue('')
  })

  it('supports New conversation while another thread exists', async () => {
    vi.mocked(createConversation).mockResolvedValue(conversation('conversation-b', 'Second'))
    vi.mocked(listConversations).mockResolvedValueOnce(conversationPage([conversation('conversation-a', 'First')]))
      .mockResolvedValue(conversationPage([conversation('conversation-b', 'Second'), conversation('conversation-a', 'First')]))
    const panel = await openExistingConversation(undefined, true)
    fireEvent.click(within(panel).getByRole('button', { name: 'New conversation' }))
    expect(await within(panel).findByRole('heading', { name: 'Second', level: 2 })).toBeInTheDocument()
    expect(createConversation).toHaveBeenCalledExactlyOnceWith({ lesson_id: 'lesson-1' })
    expect(sendMessage).not.toHaveBeenCalled()
  })

  it('selects the first backend-ordered Conversation and loads only the selected history', async () => {
    const items = [conversation('conversation-b', 'Backend first'), conversation('conversation-a', 'Backend second')]
    vi.mocked(listConversations).mockResolvedValue(conversationPage(items))
    const panel = await openExistingConversation(items, true)
    expect(Array.from(within(panel).getByRole('list').querySelectorAll('.chat-conversation-select')).map((item) => item.textContent)).toEqual([
      expect.stringContaining('Backend first'), expect.stringContaining('Backend second'),
    ])
    await waitFor(() => expect(getMessages).toHaveBeenCalledWith('conversation-b', { page: 1, page_size: 50 }))
    expect(getMessages).not.toHaveBeenCalledWith('conversation-a', expect.anything())
    fireEvent.click(within(panel).getByRole('list').querySelectorAll('.chat-conversation-select')[1])
    await waitFor(() => expect(getMessages).toHaveBeenCalledWith('conversation-a', { page: 1, page_size: 50 }))
    expect(getMessages).toHaveBeenCalledTimes(2)
    expect(sendMessage).not.toHaveBeenCalled()
  })

  it('loads bounded Conversation pages in backend order and deduplicates IDs', async () => {
    vi.mocked(listConversations).mockResolvedValueOnce(conversationPage([conversation('a', 'Alpha'), conversation('b', 'Beta')], 1, 2, 3))
      .mockResolvedValueOnce(conversationPage([conversation('b', 'Beta newer'), conversation('c', 'Gamma')], 2, 2, 3))
    const panel = await openExistingConversation([conversation('a', 'Alpha'), conversation('b', 'Beta')], true)
    fireEvent.click(within(panel).getByRole('button', { name: 'Load more conversations' }))
    const list = within(panel).getByRole('list')
    await within(list).findByRole('button', { name: /^Gamma/ })
    expect(listConversations).toHaveBeenNthCalledWith(1, { lesson_id: 'lesson-1', page: 1, page_size: 20 })
    expect(listConversations).toHaveBeenNthCalledWith(2, { lesson_id: 'lesson-1', page: 2, page_size: 20 })
    expect(within(panel).getAllByRole('listitem')).toHaveLength(3)
    expect(Array.from(list.querySelectorAll('.chat-conversation-select')).map((button) => button.querySelector('strong')?.textContent)).toEqual(['Alpha', 'Beta', 'Gamma'])
  })

  it('uses a presentation-only title fallback for null Conversation titles', async () => {
    const panel = await openExistingConversation([conversation('conversation-a', null)])
    expect(within(panel).getByRole('heading', { name: 'Untitled conversation', level: 2 })).toBeInTheDocument()
    expect(renameConversation).not.toHaveBeenCalled()
  })

  it('ignores stale history results after the learner selects another Conversation', async () => {
    let resolveFirst: ((page: MessagePage) => void) | undefined
    vi.mocked(listConversations).mockResolvedValue(conversationPage([conversation('conversation-a', 'First'), conversation('conversation-b', 'Second')]))
    vi.mocked(getMessages).mockImplementation((id) => id === 'conversation-a'
      ? new Promise((resolve) => { resolveFirst = resolve })
      : Promise.resolve(messagePage([message('message-b', 1, 'ASSISTANT', 'Second thread history')])))
    const panel = await openExistingConversation([conversation('conversation-a', 'First'), conversation('conversation-b', 'Second')])
    fireEvent.click(within(panel).getByRole('button', { name: /^Second/ }))
    expect(await within(panel).findByText('Second thread history')).toBeInTheDocument()
    await act(async () => { resolveFirst?.(messagePage([message('message-a', 1, 'ASSISTANT', 'Stale first history')])) })
    expect(within(panel).queryByText('Stale first history')).not.toBeInTheDocument()
    expect(within(panel).getByText('Second thread history')).toBeInTheDocument()
  })
})

describe('Step 4.4 Conversation rename and delete', () => {
  it('renames title only, consumes the backend response, and refreshes page 1', async () => {
    const original = conversation('conversation-a', 'Original')
    const renamed = conversation('conversation-a', 'New title', '2026-09-27T11:00:00Z')
    vi.mocked(listConversations).mockResolvedValueOnce(conversationPage([original])).mockResolvedValue(conversationPage([renamed]))
    vi.mocked(renameConversation).mockResolvedValue(renamed)
    const panel = await openExistingConversation([original], true)
    fireEvent.click(within(panel).getByRole('button', { name: 'Rename Original' }))
    fireEvent.change(within(panel).getByRole('textbox', { name: 'Conversation title' }), { target: { value: 'New title' } })
    fireEvent.click(within(panel).getByRole('button', { name: 'Save title' }))
    expect(await within(panel).findByRole('heading', { name: 'New title', level: 2 })).toBeInTheDocument()
    expect(renameConversation).toHaveBeenCalledExactlyOnceWith('conversation-a', { title: 'New title' })
    expect(listConversations).toHaveBeenCalledTimes(2)
    expect(within(panel).getByText(`Updated: ${renamed.updated_at}`)).toBeInTheDocument()
  })

  it('requires confirmation and selects the first remaining backend-ordered Conversation after deleting the selected one', async () => {
    vi.mocked(listConversations).mockResolvedValueOnce(conversationPage([conversation('a', 'Alpha'), conversation('b', 'Beta')]))
      .mockResolvedValue(conversationPage([conversation('b', 'Beta')]))
    const panel = await openExistingConversation([conversation('a', 'Alpha'), conversation('b', 'Beta')], true)
    fireEvent.click(within(panel).getByRole('button', { name: 'Delete Alpha' }))
    expect(deleteConversation).not.toHaveBeenCalled()
    fireEvent.click(within(panel).getByRole('button', { name: 'Confirm delete' }))
    expect(await within(panel).findByRole('heading', { name: 'Beta', level: 2 })).toBeInTheDocument()
    expect(deleteConversation).toHaveBeenCalledExactlyOnceWith('a')
    await waitFor(() => expect(getMessages).toHaveBeenCalledWith('b', { page: 1, page_size: 50 }))
    expect(within(panel).queryByRole('button', { name: 'Delete message' })).not.toBeInTheDocument()
  })

  it('returns to the explicit empty state after deleting the last Conversation', async () => {
    vi.mocked(listConversations).mockResolvedValueOnce(conversationPage([conversation('a', 'Only')])).mockResolvedValue(conversationPage([]))
    const panel = await openExistingConversation([conversation('a', 'Only')], true)
    fireEvent.click(within(panel).getByRole('button', { name: 'Delete Only' }))
    fireEvent.click(within(panel).getByRole('button', { name: 'Confirm delete' }))
    expect(await within(panel).findByText('Ask AI about this lesson')).toBeInTheDocument()
    expect(within(panel).getByRole('button', { name: 'Start a conversation' })).toBeInTheDocument()
    expect(getMessages).toHaveBeenCalledTimes(1)
  })
})

describe('Step 4.4 Message history and ordering', () => {
  it('shows a Message history error and retries the current Query', async () => {
    vi.mocked(getMessages).mockRejectedValueOnce(new Error('temporary history failure')).mockResolvedValue(messagePage([message('recovered', 1, 'USER', 'history recovered')]))
    const panel = await openExistingConversation()
    expect(await within(panel).findByRole('alert')).toHaveTextContent('Could not load message history')
    fireEvent.click(within(panel).getByRole('button', { name: 'Refresh conversation' }))
    expect(await within(panel).findByText('history recovered')).toBeInTheDocument()
  })

  it('renders newest page in sequence order, loads older pages, deduplicates IDs, and retains retry attempts', async () => {
    const first = [
      message('m53', 53, 'ASSISTANT', 'newest'),
      message('m51', 51, 'USER', 'question'),
      message('m52', 52, 'ASSISTANT', null, 'FAILED', 'user-1'),
    ]
    const older = [message('m2', 2), message('m1', 1), message('m52', 52, 'ASSISTANT', null, 'FAILED', 'user-1'), message('m53b', 53, 'ASSISTANT', null, 'FAILED', 'user-1')]
    vi.mocked(getMessages).mockResolvedValueOnce(messagePage(first, 1, 50, 100)).mockResolvedValueOnce(messagePage(older, 2, 50, 100))
    const panel = await openExistingConversation()
    const scroll = within(panel).getByRole('region', { name: 'Message history' })
    await within(scroll).findByText('newest')
    expect(Array.from(scroll.querySelectorAll('[data-sequence]')).map((item) => Number(item.getAttribute('data-sequence')))).toEqual([51, 52, 53])
    fireEvent.click(within(panel).getByRole('button', { name: 'Load older messages' }))
    await within(scroll).findByText('Message 1')
    expect(getMessages).toHaveBeenNthCalledWith(1, 'conversation-a', { page: 1, page_size: 50 })
    expect(getMessages).toHaveBeenNthCalledWith(2, 'conversation-a', { page: 2, page_size: 50 })
    expect(Array.from(scroll.querySelectorAll('[data-sequence]')).map((item) => Number(item.getAttribute('data-sequence')))).toEqual([1, 2, 51, 52, 53, 53])
    expect(within(scroll).getAllByRole('button', { name: 'Retry' })).toHaveLength(2)
    expect(within(scroll).queryByText('duplicate')).not.toBeInTheDocument()
  })

  it('does not use created_at as the primary Message ordering field', async () => {
    const laterSequence = { ...message('late', 9, 'USER', 'sequence nine'), created_at: '2020-01-01T00:00:00Z' }
    const earlierSequence = { ...message('early', 3, 'USER', 'sequence three'), created_at: '2030-01-01T00:00:00Z' }
    vi.mocked(getMessages).mockResolvedValue(messagePage([laterSequence, earlierSequence]))
    const panel = await openExistingConversation()
    const scroll = within(panel).getByRole('region', { name: 'Message history' })
    await within(scroll).findByText('sequence three')
    expect(Array.from(scroll.querySelectorAll('[data-sequence]')).map((item) => Number(item.getAttribute('data-sequence')))).toEqual([3, 9])
  })

  it('opens the initial history and a successful retry at the newest position', async () => {
    const restoreMetrics = mockChatScrollMetrics()
    try {
      vi.mocked(getMessages).mockResolvedValue(messagePage([
        message('user-1', 1, 'USER', 'question'), message('failed-1', 2, 'ASSISTANT', null, 'FAILED', 'user-1'),
      ]))
      vi.mocked(retryAssistantMessage).mockResolvedValue(message('retry-1', 3, 'ASSISTANT', 'latest answer', 'COMPLETED', 'user-1'))
      vi.mocked(sendMessage).mockResolvedValueOnce({
        user_message: message('send-user', 4, 'USER', 'new question'),
        assistant_message: message('send-answer', 5, 'ASSISTANT', 'new answer'),
      })
      const panel = await openExistingConversation()
      const scroll = within(panel).getByRole('region', { name: 'Message history' }) as HTMLElement
      await within(scroll).findByRole('button', { name: 'Retry' })
      await waitFor(() => expect(scroll.scrollTop).toBe(scroll.scrollHeight))
      fireEvent.click(within(scroll).getByRole('button', { name: 'Retry' }))
      await within(scroll).findByText('latest answer')
      await waitFor(() => expect(scroll.scrollTop).toBe(scroll.scrollHeight))
      fireEvent.change(within(panel).getByRole('textbox', { name: 'Message' }), { target: { value: 'new question' } })
      fireEvent.click(within(panel).getByRole('button', { name: 'Send' }))
      await within(scroll).findByText('new answer')
      await waitFor(() => expect(scroll.scrollTop).toBe(scroll.scrollHeight))
    } finally {
      restoreMetrics()
    }
  })

  it('does not pull the learner to the bottom when refreshed history changes while reading older content', async () => {
    const restoreMetrics = mockChatScrollMetrics()
    try {
      vi.mocked(getMessages).mockResolvedValueOnce(messagePage([message('first', 1, 'ASSISTANT', 'First answer')]))
        .mockResolvedValueOnce(messagePage([
          message('first', 1, 'ASSISTANT', 'First answer'), message('second', 2, 'ASSISTANT', 'New answer'),
        ]))
      vi.mocked(sendMessage).mockRejectedValueOnce(new ApiError({ status: null, code: 'NETWORK_ERROR', message: 'network', details: null }))
      const panel = await openExistingConversation()
      const scroll = within(panel).getByRole('region', { name: 'Message history' }) as HTMLElement
      await within(scroll).findByText('First answer')
      Object.defineProperty(scroll, 'clientHeight', { configurable: true, value: 10 })
      scroll.scrollTop = 0
      fireEvent.scroll(scroll)
      fireEvent.change(within(panel).getByRole('textbox', { name: 'Message' }), { target: { value: 'uncertain send' } })
      fireEvent.click(within(panel).getByRole('button', { name: 'Send' }))
      await within(scroll).findByText('New answer')
      expect(scroll.scrollTop).toBe(0)
      expect(sendMessage).toHaveBeenCalledTimes(1)
    } finally {
      restoreMetrics()
    }
  })

  it('preserves the visible scroll position when older history is prepended', async () => {
    vi.mocked(getMessages).mockResolvedValueOnce(messagePage([message('m2', 2), message('m3', 3)], 1, 2, 4))
      .mockResolvedValueOnce(messagePage([message('m1', 1)], 2, 2, 4))
    const panel = await openExistingConversation()
    const scroll = within(panel).getByRole('region', { name: 'Message history' }) as HTMLElement
    await within(scroll).findByText('Message 2')
    Object.defineProperty(scroll, 'scrollHeight', { configurable: true, get: () => scroll.querySelectorAll('[data-sequence]').length * 100 })
    Object.defineProperty(scroll, 'clientHeight', { configurable: true, value: 50 })
    scroll.scrollTop = 20
    fireEvent.scroll(scroll)
    fireEvent.click(within(panel).getByRole('button', { name: 'Load older messages' }))
    await within(scroll).findByText('Message 1')
    expect(scroll.scrollTop).toBe(120)
  })

  it('does not let a failed Load Older snapshot override the newest scroll after a successful Send', async () => {
    const restoreMetrics = mockChatScrollMetrics()
    try {
      vi.mocked(getMessages).mockResolvedValueOnce(messagePage([
        message('user-1', 1, 'USER', 'question'), message('failed-1', 2, 'ASSISTANT', null, 'FAILED', 'user-1'),
      ], 1, 2, 4)).mockRejectedValueOnce(new Error('older page unavailable'))
      vi.mocked(sendMessage).mockResolvedValueOnce({
        user_message: message('send-user', 3, 'USER', 'new question'),
        assistant_message: message('send-answer', 4, 'ASSISTANT', 'new answer'),
      })
      const panel = await openExistingConversation()
      const scroll = within(panel).getByRole('region', { name: 'Message history' }) as HTMLElement
      await within(scroll).findByRole('button', { name: 'Retry' })
      scroll.scrollTop = 0
      fireEvent.scroll(scroll)
      fireEvent.click(within(panel).getByRole('button', { name: 'Load older messages' }))
      expect(await within(scroll).findByText('Could not load older messages.')).toBeInTheDocument()
      fireEvent.change(within(panel).getByRole('textbox', { name: 'Message' }), { target: { value: 'new question' } })
      fireEvent.click(within(panel).getByRole('button', { name: 'Send' }))
      await within(scroll).findByText('new answer')
      await waitFor(() => expect(scroll.scrollTop).toBe(scroll.scrollHeight))
    } finally {
      restoreMetrics()
    }
  })

  it('does not let a failed Load Older snapshot override the newest scroll after a successful Retry', async () => {
    const restoreMetrics = mockChatScrollMetrics()
    try {
      vi.mocked(getMessages).mockResolvedValueOnce(messagePage([
        message('user-1', 1, 'USER', 'question'), message('failed-1', 2, 'ASSISTANT', null, 'FAILED', 'user-1'),
      ], 1, 2, 4)).mockRejectedValueOnce(new Error('older page unavailable'))
      vi.mocked(retryAssistantMessage).mockResolvedValueOnce(message('retry-1', 3, 'ASSISTANT', 'retry answer', 'COMPLETED', 'user-1'))
      const panel = await openExistingConversation()
      const scroll = within(panel).getByRole('region', { name: 'Message history' }) as HTMLElement
      await within(scroll).findByRole('button', { name: 'Retry' })
      scroll.scrollTop = 0
      fireEvent.scroll(scroll)
      fireEvent.click(within(panel).getByRole('button', { name: 'Load older messages' }))
      expect(await within(scroll).findByText('Could not load older messages.')).toBeInTheDocument()
      fireEvent.click(within(scroll).getByRole('button', { name: 'Retry' }))
      await within(scroll).findByText('retry answer')
      await waitFor(() => expect(scroll.scrollTop).toBe(scroll.scrollHeight))
    } finally {
      restoreMetrics()
    }
  })

  it('isolates a stale Load Older response from the newly selected Conversation history', async () => {
    const restoreMetrics = mockChatScrollMetrics()
    try {
      const firstConversation = conversation('conversation-a', 'First')
      const secondConversation = conversation('conversation-b', 'Second')
      vi.mocked(listConversations).mockResolvedValue(conversationPage([firstConversation, secondConversation]))
      let resolveOldPage: ((page: MessagePage) => void) | undefined
      vi.mocked(getMessages).mockImplementation((id, params) => {
        if (id === 'conversation-a' && params?.page === 1) {
          return Promise.resolve(messagePage([
            message('a-user', 1, 'USER', 'A question'), message('a-answer', 2, 'ASSISTANT', 'A answer'),
          ], 1, 2, 4))
        }
        if (id === 'conversation-a') return new Promise((resolve) => { resolveOldPage = resolve })
        return Promise.resolve(messagePage([message('b-answer', 1, 'ASSISTANT', 'B history')]))
      })
      const panel = await openExistingConversation([firstConversation, secondConversation], true)
      const scroll = within(panel).getByRole('region', { name: 'Message history' }) as HTMLElement
      await within(scroll).findByText('A answer')
      scroll.scrollTop = 20
      fireEvent.scroll(scroll)
      fireEvent.click(within(panel).getByRole('button', { name: 'Load older messages' }))
      await waitFor(() => expect(getMessages).toHaveBeenCalledWith('conversation-a', { page: 2, page_size: 50 }))
      fireEvent.click(within(panel).getByRole('list').querySelectorAll('.chat-conversation-select')[1])
      await within(scroll).findByText('B history')
      await waitFor(() => expect(scroll.scrollTop).toBe(scroll.scrollHeight))
      await act(async () => {
        resolveOldPage?.(messagePage([message('a-old', 0, 'USER', 'stale A history')], 2, 2, 4))
      })
      expect(within(scroll).queryByText('stale A history')).not.toBeInTheDocument()
      expect(within(scroll).getByText('B history')).toBeInTheDocument()
      expect(scroll.scrollTop).toBe(scroll.scrollHeight)
    } finally {
      restoreMetrics()
    }
  })
})

describe('Step 4.4 Composer and send lifecycle', () => {
  it('blocks whitespace-only content locally and supports Enter versus Shift+Enter/IME', async () => {
    const panel = await openExistingConversation()
    const composer = within(panel).getByRole('textbox', { name: 'Message' })
    fireEvent.change(composer, { target: { value: '   \n ' } })
    fireEvent.click(within(panel).getByRole('button', { name: 'Send' }))
    expect(await within(panel).findByText('Enter a message before sending.')).toBeInTheDocument()
    expect(sendMessage).not.toHaveBeenCalled()

    fireEvent.change(composer, { target: { value: 'hello' } })
    fireEvent.keyDown(composer, { key: 'Enter', shiftKey: true })
    expect(sendMessage).not.toHaveBeenCalled()
    fireEvent.keyDown(composer, { key: 'Enter', isComposing: true })
    expect(sendMessage).not.toHaveBeenCalled()
    fireEvent.keyDown(composer, { key: 'Enter' })
    await waitFor(() => expect(sendMessage).toHaveBeenCalledExactlyOnceWith('conversation-a', { content: 'hello' }))
  })

  it('merges only server-returned USER and ASSISTANT Messages, clears the draft, and refreshes the list', async () => {
    const panel = await openExistingConversation()
    const composer = within(panel).getByRole('textbox', { name: 'Message' })
    fireEvent.change(composer, { target: { value: 'Hello tutor' } })
    fireEvent.click(within(panel).getByRole('button', { name: 'Send' }))
    const scroll = within(panel).getByRole('region', { name: 'Message history' })
    expect(await within(scroll).findByText('Hello')).toBeInTheDocument()
    expect(within(scroll).getByText('你好')).toBeInTheDocument()
    expect(within(panel).getByRole('textbox', { name: 'Message' })).toHaveValue('')
    expect(sendMessage).toHaveBeenCalledExactlyOnceWith('conversation-a', { content: 'Hello tutor' })
    expect(getMessages).toHaveBeenCalledTimes(1)
    expect(listConversations).toHaveBeenCalledTimes(2)
    expect(within(scroll).queryByText(/server-user|server-assistant/)).not.toBeInTheDocument()
  })

  it('ignores duplicate Send and Enter while a Send request is pending', async () => {
    let finishSend: ((value: Awaited<ReturnType<typeof sendMessage>>) => void) | undefined
    vi.mocked(sendMessage).mockImplementation(() => new Promise((resolve) => { finishSend = resolve }))
    const panel = await openExistingConversation()
    const composer = within(panel).getByRole('textbox', { name: 'Message' })
    fireEvent.change(composer, { target: { value: 'one send' } })
    fireEvent.click(within(panel).getByRole('button', { name: 'Send' }))
      fireEvent.click(within(panel).getByRole('button', { name: /Sending/ }))
    fireEvent.keyDown(composer, { key: 'Enter' })
    await waitFor(() => expect(sendMessage).toHaveBeenCalledExactlyOnceWith('conversation-a', { content: 'one send' }))
    await act(async () => { finishSend?.({ user_message: message('u', 1), assistant_message: message('a', 2, 'ASSISTANT', 'answer') }) })
    expect(within(panel).getByRole('textbox', { name: 'Message' })).toHaveValue('')
  })

  it('refreshes persisted USER and FAILED Assistant after AI_RESPONSE_FAILED without resending the draft', async () => {
    const persisted = [message('persisted-user', 1, 'USER', 'saved question'), message('persisted-failed', 2, 'ASSISTANT', null, 'FAILED', 'persisted-user')]
    vi.mocked(getMessages).mockResolvedValueOnce(messagePage([])).mockResolvedValueOnce(messagePage(persisted))
    vi.mocked(sendMessage).mockRejectedValueOnce(new ApiError({ status: 502, code: 'AI_RESPONSE_FAILED', message: 'failure', details: { user_message_id: 'persisted-user', assistant_message_id: 'persisted-failed' } }))
    const panel = await openExistingConversation()
    const composer = within(panel).getByRole('textbox', { name: 'Message' })
    fireEvent.change(composer, { target: { value: 'saved question' } })
    fireEvent.click(within(panel).getByRole('button', { name: 'Send' }))
    const scroll = within(panel).getByRole('region', { name: 'Message history' })
    expect(await within(scroll).findByText('saved question')).toBeInTheDocument()
    expect(within(scroll).getByText('The AI response could not be completed.')).toBeInTheDocument()
    expect(within(panel).getByRole('textbox', { name: 'Message' })).toHaveValue('')
    expect(sendMessage).toHaveBeenCalledTimes(1)
    expect(getMessages).toHaveBeenCalledTimes(2)
    expect(within(scroll).getByRole('button', { name: 'Retry' })).toBeInTheDocument()
  })

  it('preserves an uncertain Send draft, automatically refreshes history, and gates sending behind explicit choice', async () => {
    vi.mocked(sendMessage).mockRejectedValueOnce(new ApiError({ status: null, code: 'NETWORK_ERROR', message: 'Network request failed', details: null }))
    vi.mocked(getMessages).mockResolvedValueOnce(messagePage([])).mockResolvedValueOnce(messagePage([
      message('saved-u', 1, 'USER', 'keep this draft'), message('saved-a', 2, 'ASSISTANT', 'answer'),
    ]))
    const panel = await openExistingConversation()
    const composer = within(panel).getByRole('textbox', { name: 'Message' })
    fireEvent.change(composer, { target: { value: 'keep this draft' } })
    fireEvent.click(within(panel).getByRole('button', { name: 'Send' }))
    expect(await within(panel).findByText(/couldn't confirm whether this message was saved/)).toBeInTheDocument()
    expect(within(panel).getByRole('textbox', { name: 'Message' })).toHaveValue('keep this draft')
    expect(await within(panel).findByText('keep this draft', { selector: '.chat-user-content' })).toBeInTheDocument()
    await within(panel).findByText('answer')
    expect(within(panel).getByRole('button', { name: 'Edit draft' })).toBeInTheDocument()
    expect(within(panel).getByRole('button', { name: 'Send again' })).toBeInTheDocument()
    expect(within(panel).getByRole('button', { name: 'Send' })).toBeDisabled()
    expect(sendMessage).toHaveBeenCalledTimes(1)
    expect(getMessages).toHaveBeenCalledTimes(2)
  })

  it('allows Edit draft without sending and requires explicit Send again for an ambiguous result', async () => {
    vi.mocked(sendMessage).mockRejectedValueOnce(new ApiError({ status: null, code: 'NETWORK_ERROR', message: 'Network request failed', details: null }))
      .mockResolvedValueOnce({ user_message: message('sent-user', 2, 'USER', 'keep exactly'), assistant_message: message('sent-ai', 3, 'ASSISTANT', 'answer') })
    vi.mocked(getMessages).mockResolvedValue(messagePage([]))
    const panel = await openExistingConversation()
    fireEvent.change(within(panel).getByRole('textbox', { name: 'Message' }), { target: { value: 'keep exactly' } })
    fireEvent.click(within(panel).getByRole('button', { name: 'Send' }))
    await within(panel).findByRole('button', { name: 'Edit draft' })
    fireEvent.click(within(panel).getByRole('button', { name: 'Edit draft' }))
    expect(within(panel).getByRole('textbox', { name: 'Message' })).toBeEnabled()
    expect(within(panel).getByRole('button', { name: 'Send' })).toBeEnabled()
    expect(sendMessage).toHaveBeenCalledTimes(1)
    fireEvent.click(within(panel).getByRole('button', { name: 'Send' }))
    expect(await within(panel).findByText('answer')).toBeInTheDocument()
    expect(sendMessage).toHaveBeenNthCalledWith(2, 'conversation-a', { content: 'keep exactly' })
  })

  it('Send again submits the exact preserved text once after the automatic authoritative refetch', async () => {
    vi.mocked(sendMessage).mockRejectedValueOnce(new ApiError({ status: null, code: 'NETWORK_ERROR', message: 'Network request failed', details: null }))
      .mockResolvedValueOnce({ user_message: message('sent-u', 2, 'USER', 'reviewed text'), assistant_message: message('sent-a', 3, 'ASSISTANT', 'answer') })
    vi.mocked(getMessages).mockResolvedValue(messagePage([]))
    const panel = await openExistingConversation()
    fireEvent.change(within(panel).getByRole('textbox', { name: 'Message' }), { target: { value: 'reviewed text' } })
    fireEvent.click(within(panel).getByRole('button', { name: 'Send' }))
    fireEvent.click(await within(panel).findByRole('button', { name: 'Send again' }))
    await waitFor(() => expect(sendMessage).toHaveBeenNthCalledWith(2, 'conversation-a', { content: 'reviewed text' }))
    expect(sendMessage).toHaveBeenCalledTimes(2)
  })
})

describe('Step 4.4 message statuses and retry', () => {
  it('renders persisted PENDING without its content and keeps USER plus FAILED Assistant visible', async () => {
    const pending = message('pending', 2, 'ASSISTANT', 'must not leak as an answer', 'PENDING', 'user-id')
    const failed = message('failed', 4, 'ASSISTANT', null, 'FAILED', 'user-id')
    vi.mocked(getMessages).mockResolvedValue(messagePage([
      message('user-id', 1, 'USER', '<learner>\nsecond line'), pending,
      message('retry-failed', 3, 'ASSISTANT', null, 'FAILED', 'user-id'), failed,
    ], 1, 50, 4))
    const panel = await openExistingConversation()
    const scroll = within(panel).getByRole('region', { name: 'Message history' })
    expect(await within(scroll).findByText(/AI is thinking/)).toBeInTheDocument()
    expect(within(scroll).queryByText('must not leak as an answer')).not.toBeInTheDocument()
    expect(scroll.querySelector('.chat-user-content')?.textContent).toBe('<learner>\nsecond line')
    expect(within(scroll).getAllByRole('button', { name: 'Retry' })).toHaveLength(2)
    expect(within(scroll).getByText('You')).toBeInTheDocument()
    expect(within(scroll).getAllByText('AI Tutor')).toHaveLength(3)
  })

  it('retries by failed Assistant ID only, preserves prior attempts, and refreshes list ordering', async () => {
    const failed = [message('user-1', 1, 'USER', 'question'), message('failed-1', 2, 'ASSISTANT', null, 'FAILED', 'user-1')]
    vi.mocked(getMessages).mockResolvedValue(messagePage(failed, 1, 50, 2))
    vi.mocked(retryAssistantMessage).mockResolvedValue(message('retry-2', 3, 'ASSISTANT', 'new attempt', 'COMPLETED', 'user-1'))
    const panel = await openExistingConversation()
    fireEvent.click(await within(panel).findByRole('button', { name: 'Retry' }))
    const scroll = within(panel).getByRole('region', { name: 'Message history' })
    expect(await within(scroll).findByText('new attempt')).toBeInTheDocument()
    expect(within(scroll).getByText('The AI response could not be completed.')).toBeInTheDocument()
    expect(retryAssistantMessage).toHaveBeenCalledExactlyOnceWith('failed-1')
    expect(sendMessage).not.toHaveBeenCalled()
    expect(getMessages).toHaveBeenCalledTimes(1)
    expect(listConversations).toHaveBeenCalledTimes(2)
    expect(Array.from(scroll.querySelectorAll('[data-sequence]')).map((item) => Number(item.getAttribute('data-sequence')))).toEqual([1, 2, 3])
  })

  it('refreshes newly persisted retry failure and preserves the previous failed attempt', async () => {
    const firstPage = [message('user-1', 1, 'USER', 'question'), message('failed-1', 2, 'ASSISTANT', null, 'FAILED', 'user-1')]
    const afterRetry = [...firstPage, message('failed-2', 3, 'ASSISTANT', null, 'FAILED', 'user-1')]
    vi.mocked(getMessages).mockResolvedValueOnce(messagePage(firstPage, 1, 50, 2)).mockResolvedValueOnce(messagePage(afterRetry, 1, 50, 3))
    vi.mocked(retryAssistantMessage).mockRejectedValueOnce(new ApiError({ status: 502, code: 'AI_RESPONSE_FAILED', message: 'failure', details: { assistant_message_id: 'failed-2' } }))
    const panel = await openExistingConversation()
    fireEvent.click(await within(panel).findByRole('button', { name: 'Retry' }))
    const scroll = within(panel).getByRole('region', { name: 'Message history' })
    await waitFor(() => expect(within(scroll).getAllByText('The AI response could not be completed.')).toHaveLength(2))
    expect(retryAssistantMessage).toHaveBeenCalledExactlyOnceWith('failed-1')
    expect(sendMessage).not.toHaveBeenCalled()
    expect(getMessages).toHaveBeenCalledTimes(2)
    expect(listConversations).toHaveBeenCalledTimes(2)
  })

  it('presents INVALID_MESSAGE_RETRY as a local conflict and refreshes authoritative history', async () => {
    vi.mocked(getMessages).mockResolvedValue(messagePage([message('failed', 2, 'ASSISTANT', null, 'FAILED')]))
    vi.mocked(retryAssistantMessage).mockRejectedValueOnce(new ApiError({ status: 409, code: 'INVALID_MESSAGE_RETRY', message: 'conflict', details: null }))
    const panel = await openExistingConversation()
    fireEvent.click(await within(panel).findByRole('button', { name: 'Retry' }))
    expect(await within(panel).findByText(/can no longer be retried/)).toBeInTheDocument()
    expect(getMessages).toHaveBeenCalledTimes(2)
    expect(sendMessage).not.toHaveBeenCalled()
  })
})

describe('Step 4.4 backend-authoritative Chat availability', () => {
  it('preserves blocked Send draft and Try again repeats the same operation', async () => {
    vi.mocked(getMessages).mockResolvedValue(messagePage([
      message('user-1', 1, 'USER', 'original'), message('failed-1', 2, 'ASSISTANT', null, 'FAILED', 'user-1'),
    ]))
    vi.mocked(sendMessage).mockRejectedValueOnce(new ApiError({ status: 409, code: 'AI_CHAT_DISABLED_DURING_TEST', message: 'disabled', details: null }))
      .mockResolvedValueOnce({ user_message: message('u', 3, 'USER', 'try me'), assistant_message: message('a', 4, 'ASSISTANT', 'answer') })
    const panel = await openExistingConversation()
    const composer = within(panel).getByRole('textbox', { name: 'Message' })
    fireEvent.change(composer, { target: { value: 'try me' } })
    fireEvent.click(within(panel).getByRole('button', { name: 'Send' }))
    expect((await within(panel).findAllByText(/disabled during an active Periodic Test/)).length).toBeGreaterThan(0)
    expect(within(panel).getByRole('textbox', { name: 'Message' })).toHaveValue('try me')
    expect(within(panel).getByRole('button', { name: 'Try again' })).toBeInTheDocument()
    expect(within(panel).getByRole('button', { name: 'Send' })).toBeDisabled()
    const retryButton = within(panel).getByRole('button', { name: 'Retry' })
    expect(retryButton).toBeDisabled()
    fireEvent.click(retryButton)
    fireEvent.submit(within(panel).getByRole('textbox', { name: 'Message' }).closest('form')!)
    expect(retryAssistantMessage).not.toHaveBeenCalled()
    expect(sendMessage).toHaveBeenCalledTimes(1)
    fireEvent.click(within(panel).getByRole('button', { name: 'Try again' }))
    await within(panel).findByText('answer')
    expect(sendMessage).toHaveBeenNthCalledWith(1, 'conversation-a', { content: 'try me' })
    expect(sendMessage).toHaveBeenNthCalledWith(2, 'conversation-a', { content: 'try me' })
    expect(within(panel).getByRole('textbox', { name: 'Message' })).toHaveValue('')
    expect(within(panel).queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument()
    expect(within(panel).getByRole('button', { name: 'Send' })).toBeEnabled()
    expect(within(panel).getByRole('button', { name: 'Retry' })).toBeEnabled()
  })

  it('converts a blocked Send Try again technical failure into D-042 uncertainty, not blocked-action state', async () => {
    vi.mocked(sendMessage).mockRejectedValueOnce(new ApiError({ status: 409, code: 'AI_CHAT_DISABLED_DURING_TEST', message: 'disabled', details: null }))
      .mockRejectedValueOnce(new ApiError({ status: null, code: 'NETWORK_ERROR', message: 'network', details: null }))
    vi.mocked(getMessages).mockResolvedValue(messagePage([]))
    const panel = await openExistingConversation()
    fireEvent.change(within(panel).getByRole('textbox', { name: 'Message' }), { target: { value: 'keep me' } })
    fireEvent.click(within(panel).getByRole('button', { name: 'Send' }))
    fireEvent.click(await within(panel).findByRole('button', { name: 'Try again' }))
    expect(await within(panel).findByRole('button', { name: 'Edit draft' })).toBeInTheDocument()
    expect(within(panel).getByRole('button', { name: 'Send again' })).toBeInTheDocument()
    expect(within(panel).queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument()
    expect(within(panel).getByRole('textbox', { name: 'Message' })).toBeDisabled()
    expect(sendMessage).toHaveBeenCalledTimes(2)
  })

  it('retries a blocked failed Assistant with the same ID and never sends its USER content', async () => {
    vi.mocked(getMessages).mockResolvedValue(messagePage([
      message('user-1', 1, 'USER', 'original'),
      message('failed-1', 2, 'ASSISTANT', null, 'FAILED', 'user-1'),
      message('failed-2', 3, 'ASSISTANT', null, 'FAILED', 'user-1'),
    ]))
    vi.mocked(retryAssistantMessage).mockRejectedValueOnce(new ApiError({ status: 409, code: 'AI_CHAT_DISABLED_DURING_TEST', message: 'disabled', details: null }))
      .mockResolvedValueOnce(message('retried', 4, 'ASSISTANT', 'retry answer', 'COMPLETED', 'user-1'))
    const panel = await openExistingConversation()
    await waitFor(() => expect(within(panel).getAllByRole('button', { name: 'Retry' })).toHaveLength(2))
    fireEvent.click(within(panel).getAllByRole('button', { name: 'Retry' })[0])
    expect(await within(panel).findByRole('button', { name: 'Try again' })).toBeInTheDocument()
    expect(within(panel).getByRole('textbox', { name: 'Message' })).toBeDisabled()
    expect(within(panel).getByRole('button', { name: 'Send' })).toBeDisabled()
    const retries = within(panel).getAllByRole('button', { name: 'Retry' })
    expect(retries).toHaveLength(2)
    expect(retries.every((button) => (button as HTMLButtonElement).disabled)).toBe(true)
    fireEvent.click(retries[1])
    fireEvent.submit(within(panel).getByRole('textbox', { name: 'Message' }).closest('form')!)
    expect(retryAssistantMessage).toHaveBeenCalledExactlyOnceWith('failed-1')
    expect(sendMessage).not.toHaveBeenCalled()
    fireEvent.click(within(panel).getByRole('button', { name: 'Try again' }))
    expect(await within(panel).findByText('retry answer')).toBeInTheDocument()
    expect(retryAssistantMessage).toHaveBeenNthCalledWith(1, 'failed-1')
    expect(retryAssistantMessage).toHaveBeenNthCalledWith(2, 'failed-1')
    expect(within(panel).getByRole('textbox', { name: 'Message' })).toBeEnabled()
    expect(within(panel).getByRole('button', { name: 'Send' })).toBeEnabled()
    expect(within(panel).getAllByRole('button', { name: 'Retry' }).every((button) => (button as HTMLButtonElement).disabled)).toBe(false)
    expect(sendMessage).not.toHaveBeenCalled()
  })

  it('clears action-scoped Chat-disabled state on Conversation change and panel close', async () => {
    const panel = await openExistingConversation([conversation('conversation-a', 'First'), conversation('conversation-b', 'Second')])
    vi.mocked(sendMessage).mockRejectedValueOnce(new ApiError({ status: 409, code: 'AI_CHAT_DISABLED_DURING_TEST', message: 'disabled', details: null }))
    fireEvent.change(within(panel).getByRole('textbox', { name: 'Message' }), { target: { value: 'preserve' } })
    fireEvent.click(within(panel).getByRole('button', { name: 'Send' }))
    expect(await within(panel).findByRole('button', { name: 'Try again' })).toBeInTheDocument()
    fireEvent.click(within(panel).getByRole('button', { name: /^Second/ }))
    expect(await within(panel).findByRole('textbox', { name: 'Message' })).toBeEnabled()
    expect(within(panel).queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument()
    expect(within(panel).getByRole('textbox', { name: 'Message' })).toHaveValue('')

    vi.mocked(sendMessage).mockRejectedValueOnce(new ApiError({ status: 409, code: 'AI_CHAT_DISABLED_DURING_TEST', message: 'disabled', details: null }))
    fireEvent.change(within(panel).getByRole('textbox', { name: 'Message' }), { target: { value: 'close clears' } })
    fireEvent.click(within(panel).getByRole('button', { name: 'Send' }))
    expect(await within(panel).findByRole('button', { name: 'Try again' })).toBeInTheDocument()
    fireEvent.click(within(panel).getByRole('button', { name: 'Close chat' }))
    expect(screen.queryByRole('dialog', { name: 'AI Tutor Chat' })).not.toBeInTheDocument()
    const reopened = await openChat()
    expect(within(reopened).queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument()
  })

  it('does not locally block Chat because the Lesson has an Exercise', async () => {
    const panel = await openExistingConversation()
    expect(screen.getByRole('link', { name: 'Open Exercise 1' })).toBeInTheDocument()
    expect(within(panel).getByRole('textbox', { name: 'Message' })).toBeEnabled()
    expect(within(panel).getByRole('button', { name: 'Send' })).toBeEnabled()
  })
})

describe('Step 4.4 safe Assistant Markdown', () => {
  it('renders approved Markdown formatting and Chinese/Vietnamese text', () => {
    render(<AssistantMarkdown content={'\u7b2c\u4e00\u6bb5\u3002\n\n- \u4e00\u4e2a\n- Hai\n\n1. Ti\u1ebfng Vi\u1ec7t\n2. \u4e8c\n\n**\u0111\u1eadm** v\u00e0 *nghi\u00eang* v\u1edbi `m\u00e3`  \nng\u1eaft d\u00f2ng'} />)
    expect(screen.getByText('\u7b2c\u4e00\u6bb5\u3002')).toBeInTheDocument()
    expect(screen.getAllByRole('list')).toHaveLength(2)
    expect(screen.getAllByRole('listitem')).toHaveLength(4)
    expect(screen.getByText('\u0111\u1eadm')).toBeInTheDocument()
    expect(screen.getByText('nghi\u00eang')).toBeInTheDocument()
    expect(screen.getByText('m\u00e3')).toBeInTheDocument()
    expect(screen.getByText(/ng\u1eaft d\u00f2ng/)).toBeInTheDocument()
    expect(document.querySelector('br')).toBeInTheDocument()
    expect(document.querySelector('code')).toHaveTextContent('m\u00e3')
  })

  it('never activates raw script, image, iframe, link, or citation UI from Assistant text', () => {
    render(<AssistantMarkdown content={'<script>window.__pwned = true</script>\n\n<img src=x onerror="window.__pwned=true">\n<iframe src="https://example.invalid"></iframe>\n\n[grounding](https://example.invalid)'} />)
    expect(document.querySelector('script, img, iframe')).not.toBeInTheDocument()
    expect(document.querySelector('[onerror]')).not.toBeInTheDocument()
    expect(window).not.toHaveProperty('__pwned')
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: /sources|references/i })).not.toBeInTheDocument()
  })
})
