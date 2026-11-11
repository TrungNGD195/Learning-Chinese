import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClientProvider } from '@tanstack/react-query'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { beforeEach, afterEach, expect, it, vi } from 'vitest'
import { queryClient } from '../../app/query/queryClient'
import { queryKeys } from '../../app/query/keys'
import { authApi } from '../auth/api'
import { ApiError } from '../../lib/api/errors'
import { AdminProfilePage } from './AdminProfilePage'

vi.mock('../auth/api', () => ({ authApi: { getMe: vi.fn(), updateProfile: vi.fn(), changePassword: vi.fn(), logoutAll: vi.fn() } }))
const user = { id: 'admin', full_name: 'Nguyễn An', email: 'admin@example.invalid', role: 'ADMIN' }
function setup() {
  queryClient.setQueryData(queryKeys.authMe, user)
  const router = createMemoryRouter([{ path: '/admin/profile', element: <AdminProfilePage/> }, { path: '/login', element: <h1>Đăng nhập lại</h1> }], { initialEntries: ['/admin/profile'] })
  render(<QueryClientProvider client={queryClient}><RouterProvider router={router}/></QueryClientProvider>)
  return router
}
beforeEach(() => { queryClient.clear(); vi.resetAllMocks(); vi.mocked(authApi.getMe).mockResolvedValue(user) })
afterEach(() => queryClient.clear())
it('saves only the name, updates the session and keeps email read-only', async () => {
  vi.mocked(authApi.updateProfile).mockResolvedValue({ ...user, full_name: 'Trần Bình' })
  setup()
  expect(screen.getByLabelText('Email')).toHaveAttribute('readonly')
  fireEvent.change(screen.getByLabelText('Họ và tên'), { target: { value: ' Trần Bình ' } })
  fireEvent.click(screen.getByRole('button', { name: 'Lưu thông tin' }))
  await screen.findByText('Đã cập nhật thông tin tài khoản.')
  expect(authApi.updateProfile).toHaveBeenCalledWith({ full_name: 'Trần Bình' }, expect.anything())
  expect(queryClient.getQueryData(queryKeys.authMe)).toMatchObject({ full_name: 'Trần Bình', role: 'ADMIN' })
})
function fillPasswords(current: string, next: string, confirm = next) {
  fireEvent.change(screen.getByLabelText('Mật khẩu hiện tại', { exact: true }), { target: { value: current } })
  fireEvent.change(screen.getByLabelText('Mật khẩu mới', { exact: true }), { target: { value: next } })
  fireEvent.change(screen.getByLabelText('Xác nhận mật khẩu mới', { exact: true }), { target: { value: confirm } })
}
it('validates password reuse/confirmation, supports reveal and shows server field errors', async () => {
  setup()
  fillPasswords('old-password', 'old-password')
  fireEvent.click(screen.getByRole('button', { name: 'Đổi mật khẩu' }))
  expect(await screen.findByText('Mật khẩu mới phải khác mật khẩu hiện tại.')).toBeInTheDocument()
  expect(authApi.changePassword).not.toHaveBeenCalled()
  fillPasswords('old-password', 'new-password', 'different-password')
  fireEvent.click(screen.getByRole('button', { name: 'Đổi mật khẩu' }))
  expect(await screen.findByText('Mật khẩu xác nhận chưa khớp.')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Hiện mật khẩu hiện tại' }))
  expect(screen.getByLabelText('Mật khẩu hiện tại', { exact: true })).toHaveAttribute('type', 'text')
  vi.mocked(authApi.changePassword).mockRejectedValue(new ApiError({ status: 400, code: 'INVALID_CURRENT_PASSWORD', message: 'error', details: null }))
  fillPasswords('old-password', 'new-password')
  fireEvent.click(screen.getByRole('button', { name: 'Đổi mật khẩu' }))
  expect(await screen.findByText('Mật khẩu hiện tại chưa chính xác.')).toBeInTheDocument()
  expect(screen.getByLabelText('Mật khẩu hiện tại', { exact: true })).toHaveAttribute('aria-invalid', 'true')
})
it('clears session after a successful password change and redirects to login', async () => {
  vi.mocked(authApi.changePassword).mockResolvedValue(undefined)
  const router = setup()
  fillPasswords('old-password', 'new-password')
  fireEvent.click(screen.getByRole('button', { name: 'Đổi mật khẩu' }))
  await screen.findByRole('heading', { name: 'Đăng nhập lại' })
  expect(router.state.location.state).toEqual({ notice: 'password-changed' })
  expect(queryClient.getQueryData(queryKeys.authMe)).toBeNull()
})
it('requires confirmation for logout-all, supports retry and redirects on success', async () => {
  vi.mocked(authApi.logoutAll).mockRejectedValueOnce(new Error('network')).mockResolvedValueOnce(undefined)
  setup()
  fireEvent.click(screen.getByRole('button', { name: 'Đăng xuất tất cả thiết bị' }))
  expect(authApi.logoutAll).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Hủy' }))
  expect(authApi.logoutAll).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Đăng xuất tất cả thiết bị' }))
  fireEvent.click(screen.getByRole('button', { name: 'Đăng xuất tất cả' }))
  await screen.findByText('Chưa thể đăng xuất tất cả thiết bị. Vui lòng thử lại.')
  fireEvent.click(screen.getByRole('button', { name: 'Đăng xuất tất cả thiết bị' }))
  fireEvent.click(screen.getByRole('button', { name: 'Đăng xuất tất cả' }))
  await waitFor(() => expect(screen.getByRole('heading', { name: 'Đăng nhập lại' })).toBeInTheDocument())
})
