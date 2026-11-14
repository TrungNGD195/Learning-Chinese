import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, expect, it, vi } from 'vitest'
import { AdminUsersPage, AdminUserDetailPage } from './AdminUsersPage'
import { getAdminUser, listAdminUsers } from './api'

vi.mock('./api', () => ({ getAdminUser: vi.fn(), listAdminUsers: vi.fn() }))
const account = { id: 'learner-1', full_name: 'Nguyễn An', email: 'an@example.invalid', role: 'LEARNER' as const, is_active: true, created_at: '2026-11-14T00:00:00Z', completed_lessons: 2 }
function setup(path = '/admin/users') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}><Routes><Route path="/admin/users" element={<AdminUsersPage/>}/><Route path="/admin/users/:userId" element={<AdminUserDetailPage/>}/></Routes></MemoryRouter></QueryClientProvider>)
}
beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(listAdminUsers).mockResolvedValue({ items: [account], page: 1, page_size: 20, total: 1 })
  vi.mocked(getAdminUser).mockResolvedValue({ ...account, pronunciation_completed: true, graded_attempts: 3, average_score: 85, lesson_activity: [] })
})
it('lists names and email, searches only on submit, filters and opens a read-only detail', async () => {
  setup()
  expect(await screen.findByText('Nguyễn An')).toBeVisible()
  expect(screen.getByText('an@example.invalid')).toBeVisible()
  fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'An' } })
  expect(listAdminUsers).toHaveBeenCalledTimes(1)
  fireEvent.click(screen.getByRole('button', { name: 'Tìm kiếm' }))
  await waitFor(() => expect(listAdminUsers).toHaveBeenLastCalledWith(expect.objectContaining({ search: 'An', page: 1 })))
  fireEvent.change(screen.getByRole('combobox'), { target: { value: 'LEARNER' } })
  await waitFor(() => expect(listAdminUsers).toHaveBeenLastCalledWith(expect.objectContaining({ role: 'LEARNER' })))
  fireEvent.click(screen.getByRole('link', { name: 'Xem Nguyễn An' }))
  expect(await screen.findByText('85.0%')).toBeVisible()
  expect(screen.getByText('Chưa có hoạt động bài học.')).toBeVisible()
  expect(screen.queryByRole('button', { name: /Xóa|Lưu|Đổi mật khẩu/ })).not.toBeInTheDocument()
})
it('uses server pagination and shows an empty result', async () => {
  vi.mocked(listAdminUsers).mockResolvedValueOnce({ items: [account], page: 1, page_size: 20, total: 21 }).mockResolvedValue({ items: [], page: 2, page_size: 20, total: 21 })
  setup()
  fireEvent.click(await screen.findByRole('button', { name: 'Trang sau' }))
  expect(await screen.findByText('Không có tài khoản phù hợp')).toBeVisible()
  expect(listAdminUsers).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2 }))
})
it('offers a retry on directory failure', async () => {
  vi.mocked(listAdminUsers).mockRejectedValueOnce(new Error('private error'))
  setup()
  expect(await screen.findByRole('alert')).toHaveTextContent('Không thể tải danh sách')
  fireEvent.click(screen.getByRole('button', { name: 'Thử lại' }))
  expect(await screen.findByText('Nguyễn An')).toBeVisible()
  expect(screen.queryByText('private error')).not.toBeInTheDocument()
})
