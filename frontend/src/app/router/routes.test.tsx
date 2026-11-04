import { render, screen, within } from '@testing-library/react'
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
    ['/login', 'Login', 'public'],
    ['/register', 'Create an account', 'public'],
    ['/forgot-password', 'Forgot password', 'public'],
    ['/reset-password', 'Reset password', 'public'],
    ['/dashboard', 'Dashboard', 'learner'],
    ['/pronunciation', 'Hành trình học', 'learner'],
    ['/pronunciation/lesson', 'Bài học phát âm', 'learner'],
    ['/hsk/1', 'HSK 1 Curriculum', 'learner'],
    ['/lessons/lesson-1', 'Lesson', 'learner'],
    ['/assessments/assessment-1', 'Assessment', 'learner'],
    ['/assessment-attempts/attempt-1/result', 'Assessment Result', 'learner'],
    ['/history', 'History', 'learner'],
    ['/profile', 'Profile', 'learner'],
    ['/admin', 'Quản trị học liệu', 'admin'],
    ['/admin/curriculum', 'Lộ trình HSK', 'admin'],
    ['/admin/lessons', 'Bài học', 'admin'],
    ['/admin/lessons/lesson-1', 'Biên soạn bài học', 'admin'],
    ['/admin/assessments', 'Luyện tập', 'admin'],
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
    expect(await screen.findByRole('heading', { name: 'Login' })).toBeInTheDocument()
  })

  it.each(['/unknown', '/learn', '/chat', '/design-lab', '/design-lab/preview', '/journey-test.html'])('%s renders NotFoundPage outside product layouts', (path) => {
    renderAt(path)
    expect(screen.getByTestId('not-found')).toBeInTheDocument()
    expect(document.querySelector('[data-layout]')).not.toBeInTheDocument()
  })

  it('maps Learn to /pronunciation and keeps top navigation minimal', () => {
    renderAt('/dashboard')
    const nav = screen.getByRole('navigation', { name: 'Learner navigation' })
    expect(within(nav).getByRole('link', { name: 'Hành trình' })).toHaveAttribute('href', '/pronunciation')
    expect(within(nav).getAllByRole('link').map((link) => link.textContent)).toEqual([
      'Góc học tập', 'Hành trình', 'Lịch sử', 'Hồ sơ',
    ])
    expect(within(nav).getAllByRole('link').map((link) => link.getAttribute('href'))).toEqual([
      '/dashboard', '/pronunciation', '/history', '/profile',
    ])
    expect(within(nav).getByRole('link', { name: 'Góc học tập' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: 'Skip to content' })).toHaveAttribute('href', '#main-content')
    expect(document.querySelector('#main-content[data-layout="learner"]')).toBeInTheDocument()
  })

  it('redirects the old Progress URL to the combined learning page', async () => {
    const { unmount } = renderAt('/progress')
    expect(await screen.findByRole('heading', { name: 'Hành trình học' })).toBeInTheDocument()
    unmount()
  })
  it('keeps detailed Admin Stats on its own screen', async () => {
    renderAt('/admin/stats')
    expect(await screen.findByRole('heading', { name: 'Thống kê' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '← Quản trị học liệu' })).toHaveAttribute('href','/admin')
  })
  it('keeps History as a distinct screen', () => {
    renderAt('/history')
    expect(screen.getByRole('heading', { name: 'History', level: 1 })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'History is not available yet', level: 2 })).toBeInTheDocument()
    expect(screen.getByText('Historical assessment attempts and results will be shown here.')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('keeps Assessment and Assessment Result as distinct routes', () => {
    const { unmount } = renderAt('/assessments/assessment-1')
    expect(screen.getByRole('heading', { name: 'Assessment' })).toBeInTheDocument()
    unmount()

    renderAt('/assessment-attempts/attempt-1/result')
    expect(screen.getByRole('heading', { name: 'Assessment Result' })).toBeInTheDocument()
  })

  it('adds the Curriculum navigation entry and keeps /admin a small dashboard', () => {
    renderAt('/admin')
    const nav = screen.getByRole('navigation', { name: 'Điều hướng quản trị' })
    expect(within(nav).getAllByRole('link').map((link) => link.textContent)).toEqual(['Tổng quan', 'Lộ trình', 'Bài học', 'Luyện tập', 'Tài liệu'])
    expect(within(nav).getAllByRole('link').map((link) => link.getAttribute('href'))).toEqual([
      '/admin', '/admin/curriculum', '/admin/lessons', '/admin/assessments', '/admin/documents',
    ])
    expect(within(nav).getByRole('link', { name: 'Lộ trình' })).toHaveAttribute('href', '/admin/curriculum')
    expect(screen.getByRole('link', { name: 'Quản lý lộ trình' })).toHaveAttribute('href', '/admin/curriculum')
    expect(nav.closest('.admin-sidebar')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Chuyển đến nội dung' })).toHaveAttribute('href', '#main-content')
    expect(document.querySelector('#main-content[data-layout="admin"]')).toBeInTheDocument()
  })

  it('keeps the public shell skip link and main content target', () => {
    renderAt('/login')
    expect(screen.getByRole('link', { name: 'Skip to content' })).toHaveAttribute('href', '#main-content')
    expect(document.querySelector('#main-content[data-layout="public"]')).toBeInTheDocument()
  })
})
