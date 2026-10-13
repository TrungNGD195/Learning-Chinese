import { apiClient } from '../../lib/api/client'
import type { RequestBodyOf, ResponseBodyOf } from '../../lib/api/types'

const registerPath = '/api/v1/auth/register'
const loginPath = '/api/v1/auth/login'
const mePath = '/api/v1/auth/me'
const refreshPath = '/api/v1/auth/refresh'
const logoutPath = '/api/v1/auth/logout'
const logoutAllPath = '/api/v1/auth/logout-all'
const changePasswordPath = '/api/v1/auth/change-password'
const passwordResetRequestPath = '/api/v1/auth/password-reset/request'
const passwordResetConfirmPath = '/api/v1/auth/password-reset/confirm'

type RegisterRequest = RequestBodyOf<typeof registerPath, 'post'>
type LoginRequest = RequestBodyOf<typeof loginPath, 'post'>
type ChangePasswordRequest = RequestBodyOf<typeof changePasswordPath, 'post'>
type PasswordResetRequest = RequestBodyOf<typeof passwordResetRequestPath, 'post'>
type PasswordResetConfirmRequest = RequestBodyOf<typeof passwordResetConfirmPath, 'post'>

export function register(body: RegisterRequest) {
  return apiClient<ResponseBodyOf<typeof registerPath, 'post'>, RegisterRequest>({
    method: 'POST', path: '/auth/register', body,
  })
}

export function login(body: LoginRequest) {
  return apiClient<ResponseBodyOf<typeof loginPath, 'post'>, LoginRequest>({
    method: 'POST', path: '/auth/login', body,
  })
}

export function getMe() {
  return apiClient<ResponseBodyOf<typeof mePath, 'get'>>({ method: 'GET', path: '/auth/me' })
}

export async function refresh(): Promise<void> {
  await apiClient<ResponseBodyOf<typeof refreshPath, 'post'>>({ method: 'POST', path: '/auth/refresh' })
}

export async function logout(): Promise<void> {
  await apiClient<ResponseBodyOf<typeof logoutPath, 'post'>>({ method: 'POST', path: '/auth/logout' })
}

export async function logoutAll(): Promise<void> {
  await apiClient<ResponseBodyOf<typeof logoutAllPath, 'post'>>({ method: 'POST', path: '/auth/logout-all' })
}

export async function changePassword(body: ChangePasswordRequest): Promise<void> {
  await apiClient<ResponseBodyOf<typeof changePasswordPath, 'post'>, ChangePasswordRequest>({
    method: 'POST', path: '/auth/change-password', body,
  })
}

export async function requestPasswordReset(body: PasswordResetRequest): Promise<void> {
  await apiClient<ResponseBodyOf<typeof passwordResetRequestPath, 'post'>, PasswordResetRequest>({
    method: 'POST', path: '/auth/password-reset/request', body,
  })
}

export async function confirmPasswordReset(body: PasswordResetConfirmRequest): Promise<void> {
  await apiClient<ResponseBodyOf<typeof passwordResetConfirmPath, 'post'>, PasswordResetConfirmRequest>({
    method: 'POST', path: '/auth/password-reset/confirm', body,
  })
}

export const authApi = {
  register,
  login,
  getMe,
  refresh,
  logout,
  logoutAll,
  changePassword,
  requestPasswordReset,
  confirmPasswordReset,
}
