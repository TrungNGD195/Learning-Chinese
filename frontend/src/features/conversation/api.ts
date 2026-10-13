import { apiClient } from '../../lib/api/client'
import type { QueryParametersOf, RequestBodyOf, ResponseBodyOf } from '../../lib/api/types'

const createPath = '/api/v1/conversations'
const listPath = '/api/v1/me/conversations'
const conversationPath = '/api/v1/conversations/{conversation_id}'
const messagesPath = '/api/v1/conversations/{conversation_id}/messages'
const retryPath = '/api/v1/messages/{assistant_message_id}/retry'

type CreateConversationRequest = RequestBodyOf<typeof createPath, 'post'>
type RenameConversationRequest = RequestBodyOf<typeof conversationPath, 'patch'>
type SendMessageRequest = RequestBodyOf<typeof messagesPath, 'post'>
export type ConversationFilters = QueryParametersOf<typeof listPath, 'get'>
export type MessagePageFilters = QueryParametersOf<typeof messagesPath, 'get'>

export function createConversation(body: CreateConversationRequest) {
  return apiClient<ResponseBodyOf<typeof createPath, 'post'>, CreateConversationRequest>({
    method: 'POST', path: '/conversations', body,
  })
}

export function listConversations(filters: ConversationFilters = {}) {
  return apiClient<ResponseBodyOf<typeof listPath, 'get'>>({
    method: 'GET', path: '/me/conversations', query: filters,
  })
}

export function getConversation(conversationId: string) {
  return apiClient<ResponseBodyOf<typeof conversationPath, 'get'>>({
    method: 'GET', path: `/conversations/${encodeURIComponent(conversationId)}`,
  })
}

export function renameConversation(conversationId: string, body: RenameConversationRequest) {
  return apiClient<ResponseBodyOf<typeof conversationPath, 'patch'>, RenameConversationRequest>({
    method: 'PATCH', path: `/conversations/${encodeURIComponent(conversationId)}`, body,
  })
}

export async function deleteConversation(conversationId: string): Promise<void> {
  await apiClient<ResponseBodyOf<typeof conversationPath, 'delete'>>({
    method: 'DELETE', path: `/conversations/${encodeURIComponent(conversationId)}`,
  })
}

export function getMessages(conversationId: string, filters: MessagePageFilters = {}) {
  return apiClient<ResponseBodyOf<typeof messagesPath, 'get'>>({
    method: 'GET', path: `/conversations/${encodeURIComponent(conversationId)}/messages`, query: filters,
  })
}

export function sendMessage(conversationId: string, body: SendMessageRequest) {
  return apiClient<ResponseBodyOf<typeof messagesPath, 'post'>, SendMessageRequest>({
    method: 'POST', path: `/conversations/${encodeURIComponent(conversationId)}/messages`, body,
  })
}

export function retryAssistantMessage(assistantMessageId: string) {
  return apiClient<ResponseBodyOf<typeof retryPath, 'post'>>({
    method: 'POST', path: `/messages/${encodeURIComponent(assistantMessageId)}/retry`,
  })
}
