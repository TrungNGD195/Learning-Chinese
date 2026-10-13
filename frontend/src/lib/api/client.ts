import { ApiError, HTTP_ERROR_MESSAGE, INVALID_RESPONSE_MESSAGE, NETWORK_ERROR_MESSAGE } from './errors'
import { notifySessionInvalidated } from './sessionInvalidation'
import type { ScalarQuery } from './types'

type ApiRequestOptions<Body = never> = {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'
  path: string
  query?: ScalarQuery
  body?: Body
}

const apiPrefix = '/api/v1'

export function normalizeApiBaseUrl(value: string | undefined): string {
  const configured = value?.trim()
  if (!configured) {
    throw new Error('VITE_API_BASE_URL is required')
  }

  const normalized = configured.replace(/\/+$/, '')
  if (normalized.startsWith('/') && !normalized.startsWith('//')) {
    if (normalized !== apiPrefix && !normalized.endsWith(apiPrefix)) {
      throw new Error('VITE_API_BASE_URL must include the /api/v1 API prefix')
    }
    return normalized
  }

  let parsed: URL
  try {
    parsed = new URL(normalized)
  } catch {
    throw new Error('VITE_API_BASE_URL must be an absolute http(s) URL or a same-origin root-relative path')
  }

  if (!['http:', 'https:'].includes(parsed.protocol) || parsed.username || parsed.password) {
    throw new Error('VITE_API_BASE_URL must be an absolute http(s) URL or a same-origin root-relative path')
  }
  if (parsed.search || parsed.hash) {
    throw new Error('VITE_API_BASE_URL must not include a query string or fragment')
  }
  if (parsed.pathname !== apiPrefix && !parsed.pathname.endsWith(apiPrefix)) {
    throw new Error('VITE_API_BASE_URL must include the /api/v1 API prefix')
  }

  return `${parsed.origin}${parsed.pathname}`
}

function getConfiguredBaseUrl(): string {
  return normalizeApiBaseUrl(import.meta.env.VITE_API_BASE_URL)
}

function buildUrl(baseUrl: string, path: string, query?: ScalarQuery): string {
  if (!path.startsWith('/') || path.startsWith('//') || path.includes('?') || path.includes('#')) {
    throw new Error('API paths must be relative to the configured API root')
  }
  if (path === apiPrefix || path.startsWith(`${apiPrefix}/`)) {
    throw new Error('API feature paths must not repeat the /api/v1 prefix')
  }

  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== null && value !== undefined) {
      params.set(key, String(value))
    }
  }

  const queryString = params.toString()
  return `${baseUrl}${path}${queryString ? `?${queryString}` : ''}`
}

function normalizedHttpError(status: number): ApiError {
  return new ApiError({
    status,
    code: 'HTTP_ERROR',
    message: HTTP_ERROR_MESSAGE,
    details: null,
  })
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function backendError(responseBody: unknown, status: number): ApiError | undefined {
  if (!isRecord(responseBody) || !isRecord(responseBody.error)) {
    return undefined
  }
  const { code, message, details } = responseBody.error
  if (typeof code !== 'string' || !code.trim() || typeof message !== 'string' || !message.trim()) {
    return undefined
  }

  return new ApiError({
    status,
    code,
    message,
    details: details === undefined ? null : details,
  })
}

async function requestOnce<Result = unknown, Body = never>(
  options: ApiRequestOptions<Body>,
): Promise<Result | undefined> {
  const url = buildUrl(getConfiguredBaseUrl(), options.path, options.query)
  const body = options.body
  const hasBody = body !== undefined
  const isFormData = hasBody && body instanceof FormData
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (hasBody && !isFormData) {
    headers['Content-Type'] = 'application/json'
  }

  let response: globalThis.Response
  try {
    response = await fetch(url, {
      method: options.method ?? 'GET',
      credentials: 'include',
      headers,
      ...(hasBody ? { body: isFormData ? body : JSON.stringify(body) } : {}),
    })
  } catch {
    throw new ApiError({
      status: null,
      code: 'NETWORK_ERROR',
      message: NETWORK_ERROR_MESSAGE,
      details: null,
    })
  }

  let text: string | null
  try {
    text = await response.text()
  } catch {
    text = null
  }

  if (!response.ok) {
    if (text !== null && text.length > 0) {
      try {
        const error = backendError(JSON.parse(text), response.status)
        if (error) {
          throw error
        }
      } catch (error) {
        if (error instanceof ApiError) {
          throw error
        }
      }
    }
    throw normalizedHttpError(response.status)
  }

  if (text === '') {
    return undefined
  }

  try {
    return JSON.parse(text ?? '') as Result
  } catch {
    throw new ApiError({
      status: response.status,
      code: 'INVALID_RESPONSE',
      message: INVALID_RESPONSE_MESSAGE,
      details: null,
    })
  }
}

const publicAuthPaths = new Set([
  '/auth/refresh',
  '/auth/login',
  '/auth/register',
  '/auth/password-reset/request',
  '/auth/password-reset/confirm',
  '/auth/logout',
])

let refreshPromise: Promise<void> | null = null

function isDefinitiveSessionError(error: unknown) {
  return error instanceof ApiError && (error.status === 401 || error.code === 'ACCOUNT_DISABLED')
}

function invalidateIfAccountDisabled(error: unknown) {
  if (error instanceof ApiError && error.code === 'ACCOUNT_DISABLED') notifySessionInvalidated()
}

function refreshSessionOnce() {
  if (!refreshPromise) {
    refreshPromise = requestOnce({ method: 'POST', path: '/auth/refresh' })
      .then(() => undefined)
      .catch((error: unknown) => {
        if (isDefinitiveSessionError(error)) notifySessionInvalidated()
        throw error
      })
      .finally(() => { refreshPromise = null })
  }
  return refreshPromise
}

export async function apiClient<Result = unknown, Body = never>(
  options: ApiRequestOptions<Body>,
): Promise<Result | undefined> {
  try {
    return await requestOnce<Result, Body>(options)
  } catch (error) {
    invalidateIfAccountDisabled(error)
    if (!(error instanceof ApiError) || error.status !== 401 || publicAuthPaths.has(options.path)) throw error

    await refreshSessionOnce()
    try {
      return await requestOnce<Result, Body>(options)
    } catch (replayError) {
      if (replayError instanceof ApiError && replayError.status === 401) notifySessionInvalidated()
      invalidateIfAccountDisabled(replayError)
      throw replayError
    }
  }
}
