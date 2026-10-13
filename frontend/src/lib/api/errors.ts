export type ApiErrorCode = 'NETWORK_ERROR' | 'HTTP_ERROR' | 'INVALID_RESPONSE' | string

export class ApiError extends Error {
  readonly status: number | null
  readonly code: ApiErrorCode
  readonly details: unknown

  constructor({
    status,
    code,
    message,
    details,
  }: {
    status: number | null
    code: ApiErrorCode
    message: string
    details: unknown
  }) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

export const NETWORK_ERROR_MESSAGE = 'Network request failed'
export const HTTP_ERROR_MESSAGE = 'The request failed'
export const INVALID_RESPONSE_MESSAGE = 'The server returned an invalid response'
