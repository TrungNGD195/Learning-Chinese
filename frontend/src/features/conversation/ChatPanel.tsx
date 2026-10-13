import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import type { KeyboardEvent as ReactKeyboardEvent } from 'react'
import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { InfiniteData } from '@tanstack/react-query'
import type { components } from '../../types/api.generated'
import { ApiError } from '../../lib/api/errors'
import { queryKeys } from '../../app/query/keys'
import { createConversation, deleteConversation, getConversation, getMessages, listConversations, renameConversation, retryAssistantMessage, sendMessage } from './api'
import type { ConversationFilters, MessagePageFilters } from './api'
import { AssistantMarkdown } from './AssistantMarkdown'

type Conversation = components['schemas']['ConversationResponse']
type Message = components['schemas']['MessageResponse']
type ConversationPage = NonNullable<Awaited<ReturnType<typeof listConversations>>>
type MessagePage = NonNullable<Awaited<ReturnType<typeof getMessages>>>
type ChatDisabledAction = { type: 'SEND'; conversationId: string; content: string } | { type: 'RETRY'; conversationId: string; assistantMessageId: string }
type UncertainSend = { conversationId: string; content: string }

const CONVERSATION_PAGE_SIZE = 20
const MESSAGE_PAGE_SIZE = 50
const NEAR_BOTTOM_THRESHOLD = 80

function uniqueConversations(items: Conversation[]) {
  const seen = new Set<string>()
  return items.filter((item) => { if (seen.has(item.id)) return false; seen.add(item.id); return true })
}
function mergeMessages(current: Message[], incoming: Message[]) {
  const byId = new Map(current.map((message) => [message.id, message]))
  for (const message of incoming) byId.set(message.id, message)
  return [...byId.values()].sort((left, right) => left.sequence_number - right.sequence_number)
}
function isAmbiguousTechnicalFailure(error: unknown) {
  return !(error instanceof ApiError) || error.code === 'NETWORK_ERROR' || error.code === 'INVALID_RESPONSE' || (error.status !== null && error.status >= 500)
}
function ConversationMessage({ message, onRetry, retryPending, disabled }: { message: Message; onRetry: (messageId: string) => void; retryPending: boolean; disabled: boolean }) {
  const isAssistant = message.role === 'ASSISTANT'
  return <article className={`chat-message ${isAssistant ? 'chat-message-assistant' : 'chat-message-user'}`} data-sequence={message.sequence_number}>
    <p className="chat-message-role">{isAssistant ? 'AI Tutor' : 'You'}</p>
    {message.status === 'PENDING' && isAssistant ? <p role="status">AI is thinking…</p>
      : message.status === 'FAILED' && isAssistant ? <><p role="status">The AI response could not be completed.</p><button className="secondary-action" type="button" disabled={retryPending || disabled} onClick={() => onRetry(message.id)}>Retry</button></>
        : isAssistant ? message.content !== null && <AssistantMarkdown content={message.content} /> : <p className="chat-user-content">{message.content ?? ''}</p>}
  </article>
}

export function ChatPanel({ lessonId, lessonNumber, hskLabel, onClose }: { lessonId: string; lessonNumber: number; hskLabel: string | null; onClose: () => void }) {
  const queryClient = useQueryClient()
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null)
  const [createPending, setCreatePending] = useState(false)
  const [composerText, setComposerText] = useState('')
  const [retryPendingId, setRetryPendingId] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [historyError, setHistoryError] = useState<string | null>(null)
  const [blockedAction, setBlockedAction] = useState<ChatDisabledAction | null>(null)
  const [uncertainSend, setUncertainSend] = useState<UncertainSend | null>(null)
  const [renameId, setRenameId] = useState<string | null>(null)
  const [renameDraft, setRenameDraft] = useState('')
  const [renamePending, setRenamePending] = useState(false)
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)
  const [deletePendingId, setDeletePendingId] = useState<string | null>(null)
  const selectedIdRef = useRef<string | null>(null)
  const sendPendingRef = useRef(false)
  const retryPendingRef = useRef(false)
  const messageScrollRef = useRef<HTMLDivElement>(null)
  const nearBottomRef = useRef(true)
  const scrollModeRef = useRef<'bottom' | 'near' | 'preserve'>('bottom')
  const prependRestoreRef = useRef<{ height: number; top: number } | null>(null)

  const conversationKey = queryKeys.conversationsByLesson(lessonId)
  const conversationsQuery = useInfiniteQuery({
    queryKey: conversationKey,
    queryFn: ({ pageParam }) => listConversations({ lesson_id: lessonId, page: pageParam, page_size: CONVERSATION_PAGE_SIZE } as ConversationFilters),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => lastPage.page * lastPage.page_size < lastPage.total ? lastPage.page + 1 : undefined,
    refetchOnWindowFocus: false,
  })
  const conversations = useMemo(() => uniqueConversations(conversationsQuery.data?.pages.flatMap((page) => page.items) ?? []), [conversationsQuery.data])
  const selectedConversation = conversations.find((item) => item.id === selectedConversationId) ?? null
  const messageKey = selectedConversationId ? queryKeys.messagesByConversation(selectedConversationId) : ['messages', 'conversation', ''] as const
  const messagesQuery = useInfiniteQuery({
    queryKey: messageKey,
    queryFn: ({ pageParam }) => getMessages(selectedConversationId!, { page: pageParam, page_size: MESSAGE_PAGE_SIZE } as MessagePageFilters),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => lastPage.page * lastPage.page_size < lastPage.total ? lastPage.page + 1 : undefined,
    enabled: !!selectedConversationId,
    refetchOnWindowFocus: false,
  })
  const messages = useMemo(() => mergeMessages([], messagesQuery.data?.pages.flatMap((page) => page.items) ?? []), [messagesQuery.data])
  const createMutation = useMutation({ mutationFn: () => createConversation({ lesson_id: lessonId }) })
  const renameMutation = useMutation({ mutationFn: ({ id, title }: { id: string; title: string }) => renameConversation(id, { title }) })
  const deleteMutation = useMutation({ mutationFn: (id: string) => deleteConversation(id) })
  const sendMutation = useMutation({ mutationFn: ({ id, content }: { id: string; content: string }) => sendMessage(id, { content }), onSuccess: (result, variables) => {
    queryClient.setQueryData<InfiniteData<MessagePage, number>>(queryKeys.messagesByConversation(variables.id), (current) => current && current.pages.length ? {
      ...current, pages: current.pages.map((page, index) => index === 0 ? { ...page, items: mergeMessages(page.items, [result.user_message, result.assistant_message]), total: page.total + 2 } : page),
    } : current)
    return queryClient.invalidateQueries({ queryKey: conversationKey })
  } })
  const retryMutation = useMutation({ mutationFn: (id: string) => retryAssistantMessage(id), onSuccess: (result, conversationId) => {
    queryClient.setQueryData<InfiniteData<MessagePage, number>>(queryKeys.messagesByConversation(conversationId), (current) => current && current.pages.length ? {
      ...current, pages: current.pages.map((page, index) => index === 0 ? { ...page, items: mergeMessages(page.items, [result]), total: page.total + 1 } : page),
    } : current)
    return queryClient.invalidateQueries({ queryKey: conversationKey })
  } })

  const selectConversation = useCallback((conversation: Conversation | null) => {
    const nextId = conversation?.id ?? null
    if (selectedIdRef.current === nextId) return
    selectedIdRef.current = nextId
    setSelectedConversationId(nextId)
    setComposerText('')
    setActionError(null)
    setHistoryError(null)
    setBlockedAction(null)
    setUncertainSend(null)
    setRenameId(null)
    setRenameDraft('')
    setDeleteConfirmId(null)
    sendPendingRef.current = false
    retryPendingRef.current = false
    nearBottomRef.current = true
    scrollModeRef.current = 'bottom'
    prependRestoreRef.current = null
  }, [])

  useEffect(() => {
    if (!conversationsQuery.isSuccess || selectedConversationId) return
    const first = conversations[0]
    if (first) selectConversation(first)
  }, [conversations, conversationsQuery.isSuccess, selectedConversationId, selectConversation])

  const refreshConversationList = useCallback(async (preferredId: string | null = selectedIdRef.current, removedId?: string) => {
    await queryClient.invalidateQueries({ queryKey: conversationKey })
    const current = queryClient.getQueryData<InfiniteData<ConversationPage, number>>(conversationKey)
    const ordered = uniqueConversations(current?.pages.flatMap((page) => page.items) ?? [])
    let candidate = preferredId && preferredId !== removedId ? ordered.find((item) => item.id === preferredId) ?? null : null
    if (preferredId && preferredId !== removedId && !candidate) {
      try {
        const detail = await getConversation(preferredId)
        if (detail.lesson_id === lessonId) candidate = detail
      } catch (error) {
        const status = error instanceof ApiError ? error.status : null
        if (status !== 404 && status !== 410) candidate = selectedIdRef.current === preferredId ? selectedConversation : null
      }
    }
    selectConversation(candidate ?? ordered[0] ?? null)
  }, [conversationKey, lessonId, queryClient, selectConversation, selectedConversation])

  const refreshNewestHistory = async (conversationId: string) => {
    if (nearBottomRef.current) scrollModeRef.current = 'bottom'
    try {
      await queryClient.invalidateQueries({ queryKey: queryKeys.messagesByConversation(conversationId), exact: true })
      setHistoryError(null)
    } catch { setHistoryError('Could not refresh message history. Try again.') }
  }

  const loadMoreConversations = async () => { if (conversationsQuery.hasNextPage && !conversationsQuery.isFetchingNextPage) await conversationsQuery.fetchNextPage() }
  const startConversation = async () => {
    if (createPending) return
    setCreatePending(true); setActionError(null)
    try { const created = await createMutation.mutateAsync(); selectConversation(created); await refreshConversationList(created.id) }
    catch { setActionError('Could not start a conversation. Try again.') }
    finally { setCreatePending(false) }
  }
  const loadOlderMessages = async () => {
    const conversationId = selectedConversationId
    const scrollElement = messageScrollRef.current
    if (!messagesQuery.hasNextPage || messagesQuery.isFetchingNextPage) return
    const restoreSnapshot = scrollElement ? { height: scrollElement.scrollHeight, top: scrollElement.scrollTop } : null
    try {
      const result = await messagesQuery.fetchNextPage()
      if (result.isError) setHistoryError('Could not load older messages.')
      else if (selectedIdRef.current === conversationId) { prependRestoreRef.current = restoreSnapshot; scrollModeRef.current = 'preserve'; setHistoryError(null) }
    } catch { setHistoryError('Could not load older messages.') }
  }

  const submitMessage = async (conversationId: string, content: string, explicitUncertainRetry = false, retryingBlockedSend = false) => {
    if (sendPendingRef.current || deletePendingId === conversationId || (!retryingBlockedSend && blockedAction?.conversationId === conversationId) || (!explicitUncertainRetry && uncertainSend?.conversationId === conversationId)) return
    if (!content.trim()) { setActionError('Enter a message before sending.'); return }
    sendPendingRef.current = true; setActionError(null)
    try {
      await sendMutation.mutateAsync({ id: conversationId, content })
      if (selectedIdRef.current === conversationId) { scrollModeRef.current = 'bottom'; prependRestoreRef.current = null; setHistoryError(null); setComposerText(''); setBlockedAction(null); setUncertainSend(null) }
    } catch (error) {
      if (selectedIdRef.current === conversationId) {
        if (error instanceof ApiError && error.code === 'AI_RESPONSE_FAILED') {
          setComposerText(''); setActionError('Your message was saved, but the AI response failed. The saved response and retry option will appear when history refreshes.')
          setBlockedAction(null); setUncertainSend(null)
          await refreshNewestHistory(conversationId)
          await queryClient.invalidateQueries({ queryKey: conversationKey })
        } else if (error instanceof ApiError && error.code === 'AI_CHAT_DISABLED_DURING_TEST') {
          setBlockedAction({ type: 'SEND', conversationId, content }); setActionError('AI Chat is temporarily disabled during an active Periodic Test. Your draft is preserved.')
        } else if (isAmbiguousTechnicalFailure(error)) {
          setBlockedAction(null); setComposerText(content); setActionError(null)
          await refreshNewestHistory(conversationId)
          setUncertainSend({ conversationId, content })
        } else { setBlockedAction(null); setActionError('Could not send this message. Your draft is preserved.') }
      } else if (error instanceof ApiError && error.code === 'AI_RESPONSE_FAILED') await queryClient.invalidateQueries({ queryKey: conversationKey })
    } finally { sendPendingRef.current = false }
  }
  const retryMessage = async (conversationId: string, assistantMessageId: string, retryingBlockedRetry = false) => {
    if (retryPendingRef.current || deletePendingId === conversationId || (!retryingBlockedRetry && blockedAction?.conversationId === conversationId)) return
    retryPendingRef.current = true; setRetryPendingId(assistantMessageId); setActionError(null)
    try {
      const result = await retryMutation.mutateAsync(assistantMessageId)
      queryClient.setQueryData<InfiniteData<MessagePage, number>>(queryKeys.messagesByConversation(conversationId), (current) => current && current.pages.length ? {
        ...current, pages: current.pages.map((page, index) => index === 0 ? { ...page, items: mergeMessages(page.items, [result]), total: Math.max(page.total, messages.length + 1) } : page),
      } : current)
      if (selectedIdRef.current === conversationId) { scrollModeRef.current = 'bottom'; prependRestoreRef.current = null; setHistoryError(null); setBlockedAction(null) }
    } catch (error) {
      if (selectedIdRef.current === conversationId) {
        if (error instanceof ApiError && error.code === 'AI_RESPONSE_FAILED') { setActionError('The retry failed. The persisted attempt will appear when history refreshes.'); setBlockedAction(null); await refreshNewestHistory(conversationId); await queryClient.invalidateQueries({ queryKey: conversationKey }) }
        else if (error instanceof ApiError && error.code === 'AI_CHAT_DISABLED_DURING_TEST') { setBlockedAction({ type: 'RETRY', conversationId, assistantMessageId }); setActionError('AI Chat is temporarily disabled during an active Periodic Test.') }
        else if (error instanceof ApiError && error.code === 'INVALID_MESSAGE_RETRY') { setBlockedAction(null); setActionError('This response can no longer be retried. Message history has been refreshed.'); await refreshNewestHistory(conversationId) }
        else if (isAmbiguousTechnicalFailure(error)) { setBlockedAction(null); setActionError('The retry result could not be confirmed. Message history has been refreshed.'); await refreshNewestHistory(conversationId) }
        else { setBlockedAction(null); setActionError('Could not retry this response.') }
      } else if (error instanceof ApiError && error.code === 'AI_RESPONSE_FAILED') await queryClient.invalidateQueries({ queryKey: conversationKey })
    } finally { retryPendingRef.current = false; setRetryPendingId(null) }
  }
  const onComposerKeyDown = (event: ReactKeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== 'Enter' || event.shiftKey || event.nativeEvent.isComposing) return
    event.preventDefault()
    if (selectedConversationId && !sendPendingRef.current) void submitMessage(selectedConversationId, composerText)
  }
  const saveRename = async () => {
    if (!renameId || renamePending) return
    const id = renameId; setRenamePending(true); setActionError(null)
    try { const updated = await renameMutation.mutateAsync({ id, title: renameDraft }); if (selectedIdRef.current === id) selectConversation(updated); setRenameId(null); setRenameDraft(''); await refreshConversationList(selectedIdRef.current) }
    catch { setActionError('Could not rename this conversation.') }
    finally { setRenamePending(false) }
  }
  const confirmDelete = async (conversationId: string) => {
    if (deletePendingId) return
    setDeletePendingId(conversationId); setActionError(null)
    try { await deleteMutation.mutateAsync(conversationId); queryClient.removeQueries({ queryKey: queryKeys.messagesByConversation(conversationId), exact: true }); setDeleteConfirmId(null); await refreshConversationList(selectedIdRef.current, conversationId) }
    catch { setActionError('Could not delete this conversation.') }
    finally { setDeletePendingId(null) }
  }

  useLayoutEffect(() => {
    const scrollElement = messageScrollRef.current
    if (!scrollElement) return
    const restore = prependRestoreRef.current
    if (restore) { scrollElement.scrollTop = restore.top + (scrollElement.scrollHeight - restore.height); prependRestoreRef.current = null; nearBottomRef.current = false; return }
    if (scrollModeRef.current === 'bottom' || (scrollModeRef.current === 'near' && nearBottomRef.current)) { scrollElement.scrollTop = scrollElement.scrollHeight; nearBottomRef.current = true }
    scrollModeRef.current = 'near'
  }, [messages])

  const hasMoreConversations = conversationsQuery.hasNextPage
  const hasOlderMessages = messagesQuery.hasNextPage
  const sendPending = sendMutation.isPending
  const retryPending = retryMutation.isPending
  const messageMutationBlocked = blockedAction?.conversationId === selectedConversationId
  const selectedDeleting = deletePendingId === selectedConversationId
  const currentBlocked = blockedAction?.conversationId === selectedConversationId ? blockedAction : null
  const currentUncertain = uncertainSend?.conversationId === selectedConversationId ? uncertainSend : null
  const selectedTitle = selectedConversation?.title?.trim() || 'Untitled conversation'

  return <section className="chat-panel" role="dialog" aria-modal="true" aria-label="AI Tutor Chat">
    <header className="chat-panel-header"><div><p className="chat-eyebrow">AI Tutor</p><p className="chat-context">{hskLabel ? `${hskLabel} · ` : ''}Lesson {lessonNumber}</p></div>
      <button className="icon-action" type="button" aria-label="Close chat" onClick={onClose}>Close</button></header>
    <div className="chat-panel-body"><aside className="chat-conversation-sidebar" aria-label="Conversations"><div className="chat-conversation-toolbar"><h2>Conversations</h2>
      <button className="secondary-action" type="button" disabled={createPending} onClick={() => void startConversation()}>New conversation</button></div>
      {conversationsQuery.isPending && <p role="status">Loading conversations…</p>}
      {conversationsQuery.isError && <><p role="alert">Could not load conversations.</p><button type="button" onClick={() => void conversationsQuery.refetch()}>Retry</button></>}
      <ul className="chat-conversation-list">{conversations.map((conversation) => <li key={conversation.id}>
        {renameId === conversation.id ? <div className="chat-rename-form"><label>Conversation title<input aria-label="Conversation title" value={renameDraft} onChange={(event) => setRenameDraft(event.target.value)} /></label>
          <button type="button" disabled={renamePending} onClick={() => void saveRename()}>Save title</button><button type="button" disabled={renamePending} onClick={() => { setRenameId(null); setRenameDraft('') }}>Cancel rename</button></div>
          : <button className="chat-conversation-select" type="button" aria-pressed={conversation.id === selectedConversationId} onClick={() => selectConversation(conversation)}><strong>{conversation.title?.trim() || 'Untitled conversation'}</strong><span>Updated: {conversation.updated_at}</span></button>}
        <div className="chat-conversation-actions">{renameId !== conversation.id && <button type="button" aria-label={`Rename ${conversation.title?.trim() || 'conversation'}`} onClick={() => { setRenameId(conversation.id); setRenameDraft(conversation.title ?? ''); setDeleteConfirmId(null) }}>Rename</button>}
          {deleteConfirmId === conversation.id ? <span className="chat-delete-confirmation" role="group" aria-label="Confirm conversation deletion"><span>Delete this conversation?</span>
            <button type="button" disabled={deletePendingId === conversation.id} onClick={() => void confirmDelete(conversation.id)}>Confirm delete</button><button type="button" onClick={() => setDeleteConfirmId(null)}>Cancel delete</button></span>
            : <button type="button" aria-label={`Delete ${conversation.title?.trim() || 'conversation'}`} onClick={() => { setDeleteConfirmId(conversation.id); setRenameId(null); setRenameDraft('') }}>Delete</button>}</div>
      </li>)}</ul>
      {hasMoreConversations && <button className="secondary-action" type="button" disabled={conversationsQuery.isFetchingNextPage} onClick={() => void loadMoreConversations()}>{conversationsQuery.isFetchingNextPage ? 'Loading…' : 'Load more conversations'}</button>}
    </aside>
    <section className="chat-thread" aria-label="Selected conversation">
      {!selectedConversationId ? conversations.length === 0 && !conversationsQuery.isPending && !conversationsQuery.isError
        ? <div className="chat-empty-state"><h2>Ask AI about this lesson</h2><button className="primary-action" type="button" disabled={createPending} onClick={() => void startConversation()}>{createPending ? 'Starting…' : 'Start a conversation'}</button></div>
        : !conversationsQuery.isPending && conversations.length > 0 && <p>Select a conversation to view its messages.</p>
        : <><header className="chat-thread-header"><div><h2>{selectedTitle}</h2><p>{hskLabel ? `${hskLabel} · ` : ''}Lesson {lessonNumber}</p></div></header>
          <div className="chat-message-scroll" role="region" ref={messageScrollRef} onScroll={(event) => { const element = event.currentTarget; nearBottomRef.current = element.scrollHeight - element.scrollTop - element.clientHeight <= NEAR_BOTTOM_THRESHOLD }} aria-label="Message history">
            {hasOlderMessages && <button className="secondary-action chat-load-older" type="button" disabled={messagesQuery.isFetchingNextPage} onClick={() => void loadOlderMessages()}>{messagesQuery.isFetchingNextPage ? 'Loading older messages…' : 'Load older messages'}</button>}
            {messagesQuery.isPending && <p role="status">Loading messages…</p>}{(historyError || messagesQuery.isError) && <p role="alert">{historyError ?? 'Could not load message history. Refresh the conversation to try again.'}</p>}
            {!messagesQuery.isPending && messages.length === 0 && !historyError && !messagesQuery.isError && <p className="chat-no-messages">No messages yet.</p>}
            {messages.map((message) => <ConversationMessage key={message.id} message={message} onRetry={(id) => void retryMessage(message.conversation_id, id)} retryPending={retryPendingId === message.id} disabled={selectedDeleting || messageMutationBlocked || currentUncertain !== null} />)}
            {sendPending && <p className="chat-action-pending" role="status">AI is thinking…</p>}
          </div>
          {currentBlocked && <div className="chat-disabled-notice" role="status"><p>AI Chat is temporarily disabled during an active Periodic Test.</p><button type="button" disabled={sendPending || retryPending} onClick={() => { if (currentBlocked.type === 'SEND') void submitMessage(currentBlocked.conversationId, currentBlocked.content, false, true); else void retryMessage(currentBlocked.conversationId, currentBlocked.assistantMessageId, true) }}>Try again</button></div>}
          {currentUncertain && <div className="chat-uncertain-send" role="status"><p>We couldn't confirm whether this message was saved. The conversation has been refreshed. Review it before sending again.</p>
            <button type="button" onClick={() => { setUncertainSend(null); setActionError(null) }}>Edit draft</button>
            <button type="button" disabled={sendPending} onClick={() => { setUncertainSend(null); void submitMessage(currentUncertain.conversationId, currentUncertain.content, true) }}>Send again</button></div>}
          {actionError && <p role="alert" className="chat-action-error">{actionError}</p>}
          {(historyError || actionError || messagesQuery.isError) && <button className="secondary-action" type="button" disabled={messagesQuery.isFetching} onClick={() => { if (selectedConversationId) void refreshNewestHistory(selectedConversationId); setActionError(null) }}>Refresh conversation</button>}
          <form className="chat-composer" onSubmit={(event) => { event.preventDefault(); if (selectedConversationId) void submitMessage(selectedConversationId, composerText) }}>
            <label htmlFor="chat-composer-input">Message</label><textarea id="chat-composer-input" aria-label="Message" value={composerText} rows={3} disabled={sendPending || messageMutationBlocked || selectedDeleting || currentUncertain !== null}
              onChange={(event) => { setComposerText(event.target.value); setActionError(null) }} onKeyDown={onComposerKeyDown} />
            <button className="primary-action" type="submit" disabled={!selectedConversationId || sendPending || messageMutationBlocked || selectedDeleting || currentUncertain !== null}>{sendPending ? 'Sending…' : 'Send'}</button>
          </form></>}
    </section></div>
    {actionError && !selectedConversationId && <p role="alert" className="chat-action-error">{actionError}</p>}
  </section>
}
