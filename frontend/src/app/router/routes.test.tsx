import { fireEvent, render, screen, within } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it } from 'vitest'
import { queryKeys } from '../query/keys'
import { createAppRoutes } from './routes'

function renderAt(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  queryClient.setQueryDefaults(queryKeys.authMe, { staleTime: Infinity })
  const publicOnly = ['/', '/login', '/register', '/forgot-password'].includes(path)
  queryClient.setQueryData(queryKeys.authMe, publicOnly ? null : { id: 'user-1', email: 'user@example.test', full_name: 'Test User', role: path.startsWith('/admin') ? 'ADMIN' : 'LEARNER' })
  const router = createMemoryRouter(createAppRoutes(), { initialEntries: [path] })
  return render(<QueryClientProvider client={queryClient}><RouterProvider router={router} /></QueryClientProvider>)
}

describe('production route tree', () => {
  it.each([
    ['/login', "Đăng nhập", 'public'],
    ['/register', "Tạo tài khoản", 'public'],
    ['/forgot-password', "Quên mật khẩu", 'public'],
    ['/reset-password', "Đặt lại mật khẩu", 'public'],
    ['/pronunciation', "Giáo trình của bạn", 'learner'],
    ['/pronunciation', 'Giáo trình của bạn', 'learner'],
    ['/pronunciation/lesson', 'Bài học phát âm', 'learner'],
    ['/pronunciation/lesson/thanh-mau', 'Thanh mẫu', 'learner'],
    ['/pronunciation/lesson/van-mau', 'Vận mẫu', 'learner'],
    ['/pronunciation/lesson/thanh-dieu', 'Thanh điệu', 'learner'],
    ['/pronunciation/lesson/bien-dieu', 'Biến điệu', 'learner'],
    ['/hsk/1', "Giáo trình của bạn", 'learner'],
    ['/lessons/lesson-1', "Bài học", 'learner'],
    ['/lessons/lesson-1/vocabulary/word-1', 'Bài học', 'learner'],
    ['/lessons/lesson-1/vocabulary', 'Bài học', 'learner'],
    ['/lessons/lesson-1/grammar', 'Bài học', 'learner'],
    ['/lessons/lesson-1/readings', 'Bài học', 'learner'],
    ['/lessons/lesson-1/practice', 'Bài học', 'learner'],
    ['/assessments/assessment-1', "Luyện tập", 'learner'],
    ['/assessment-attempts/attempt-1/result', "Kết quả luyện tập", 'learner'],
    ['/measure-words', 'Lượng từ', 'learner'],
    ['/profile', "Hồ sơ", 'learner'],
    ['/admin', 'Quản trị học liệu', 'admin'],
    ['/admin/lessons?view=curriculum', 'Sắp xếp HSK', 'admin'],
    ['/admin/lessons', 'Bài học', 'admin'],
    ['/admin/lessons/lesson-1', 'Biên soạn bài học', 'admin'],
    ['/admin/assessments', 'Kiểm tra định kỳ', 'admin'],
    ['/admin/assessments/assessment-1', 'Biên soạn bài luyện tập', 'admin'],
    ['/admin/documents', 'Thư viện tài liệu', 'admin'],
    ['/admin/documents/document-1', 'Thông tin tài liệu', 'admin'],
  ])('%s renders %s within the %s layout', (path, heading, layout) => {
    renderAt(path)
    expect(screen.getByRole('heading', { name: heading })).toBeInTheDocument()
    expect(document.querySelector(`[data-layout="${layout}"]`)).toBeInTheDocument()
  })

  it('redirects / to /login when no session is present', async () => {
    renderAt('/')
    expect(await screen.findByRole('heading', { name: "Đăng nhập" })).toBeInTheDocument()
  })

  it.each(['/unknown', '/learn', '/chat', '/design-lab', '/design-lab/preview', '/journey-test.html'])('%s renders NotFoundPage outside product layouts', (path) => {
    renderAt(path)
    expect(screen.getByTestId('not-found')).toBeInTheDocument()
    expect(document.querySelector('[data-layout]')).not.toBeInTheDocument()
  })

  it('maps Learn to /pronunciation and keeps top navigation minimal', () => {
    renderAt('/pronunciation')
    const nav = screen.getByRole('navigation', { name: "Điều hướng học viên" })
    expect(within(nav).getByRole('link', { name: 'Giáo trình' })).toHaveAttribute('href', '/pronunciation')
    expect(within(nav).getAllByRole('link').map((link) => link.textContent)).toEqual([
      'Giáo trình', 'Hồ sơ',
    ])
    expect(within(nav).getAllByRole('link').map((link) => link.getAttribute('href'))).toEqual([
      '/pronunciation', '/profile',
    ])
    expect(within(nav).getByRole('link', { name: 'Giáo trình' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: "Chuyển đến nội dung" })).toHaveAttribute('href', '#main-content')
    expect(document.querySelector('#main-content[data-layout="learner"]')).toBeInTheDocument()
  })

  it('redirects the old Progress URL to the combined learning page', async () => {
    const { unmount } = renderAt('/progress')
    expect(await screen.findByRole('heading', { name: 'Giáo trình của bạn' })).toBeInTheDocument()
    unmount()
  })
  it('opens the real journey from the earlier prototype URL', async () => {
    renderAt('/preview/great-wall')
    expect(await screen.findByRole('heading', { name: 'Giáo trình của bạn' })).toBeInTheDocument()
    expect(screen.queryByText(/Bản thử giao diện/)).not.toBeInTheDocument()
  })
  it('keeps detailed Admin Stats on its own screen', async () => {
    renderAt('/admin/stats')
    expect(await screen.findByRole('heading', { name: 'Thống kê' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '← Quản trị học liệu' })).toHaveAttribute('href','/admin')
  })
  it('redirects the retired History URL to the learning journey', async () => {
    renderAt('/history')
    expect(await screen.findByRole('heading', { name: 'Giáo trình của bạn' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Lịch sử' })).not.toBeInTheDocument()
  })

  it('collapses and expands student navigation while retaining accessible links and logout', () => {
    renderAt('/pronunciation')
    const toggle = screen.getByRole('button', { name: 'Thu gọn thanh bên' })
    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    fireEvent.click(toggle)
    expect(screen.getByRole('button', { name: 'Mở rộng thanh bên' })).toHaveAttribute('aria-expanded', 'false')
    expect(document.querySelector('.bo-shell')).toHaveAttribute('data-sidebar-collapsed', 'true')
    expect(screen.getByRole('button', { name: 'Đăng xuất' })).toBeInTheDocument()
    const nav = screen.getByRole('navigation', { name: 'Điều hướng học viên' })
    expect(within(nav).getAllByRole('link')).toHaveLength(2)
    expect(within(nav).getByRole('link', { name: 'Giáo trình' })).toHaveAttribute('href', '/pronunciation')
    fireEvent.click(screen.getByRole('button', { name: 'Mở rộng thanh bên' }))
    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    expect(document.querySelector('.bo-shell')).toHaveAttribute('data-sidebar-collapsed', 'false')
  })

  it('keeps Assessment and Assessment Result as distinct routes', () => {
    const { unmount } = renderAt('/assessments/assessment-1')
    expect(screen.getByRole('heading', { name: "Luyện tập" })).toBeInTheDocument()
    unmount()

    renderAt('/assessment-attempts/attempt-1/result')
    expect(screen.getByRole('heading', { name: "Kết quả luyện tập" })).toBeInTheDocument()
  })

  it('adds the Curriculum navigation entry and keeps /admin a small dashboard', () => {
    renderAt('/admin')
    const nav = screen.getByRole('navigation', { name: 'Điều hướng quản trị' })
    expect(within(nav).getAllByRole('link').map((link) => link.textContent)).toEqual(['Tổng quan', 'Bài học', 'Kiểm tra định kỳ', 'Tài liệu', 'Hồ sơ'])
    expect(within(nav).getAllByRole('link').map((link) => link.getAttribute('href'))).toEqual([
      '/admin', '/admin/lessons', '/admin/assessments', '/admin/documents', '/admin/profile',
    ])
    expect(within(nav).queryByRole('link', { name: 'Lộ trình' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Sắp xếp bài học' })).toHaveAttribute('href', '/admin/lessons?view=curriculum')
    expect(nav.closest('.admin-sidebar')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Chuyển đến nội dung' })).toHaveAttribute('href', '#main-content')
    expect(document.querySelector('#main-content[data-layout="admin"]')).toBeInTheDocument()
  })

  it('keeps old curriculum links working under lesson management', async () => {
    renderAt('/admin/curriculum')
    expect(await screen.findByRole('heading', { name: 'Sắp xếp HSK' })).toBeInTheDocument()
    const nav = screen.getByRole('navigation', { name: 'Điều hướng quản trị' })
    expect(within(nav).getByRole('link', { name: 'Bài học' })).toHaveAttribute('aria-current', 'page')
    expect(within(nav).queryByRole('link', { name: 'Lộ trình' })).not.toBeInTheDocument()
  })

  it('keeps the public shell skip link and main content target', () => {
    renderAt('/login')
    expect(screen.getByRole('link', { name: "Chuyển đến nội dung" })).toHaveAttribute('href', '#main-content')
    expect(document.querySelector('#main-content[data-layout="public"]')).toBeInTheDocument()
  })
})
