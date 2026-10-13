import { render, screen, within } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it } from 'vitest'
import { queryKeys } from '../query/keys'
import { createAppRoutes } from './routes'

function renderAt(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  queryClient.setQueryDefaults(queryKeys.authMe, { staleTime: Infinity })
  const publicOnly = ['/login', '/register', '/forgot-password'].includes(path)
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
    ['/pronunciation', 'Pronunciation Foundations', 'learner'],
    ['/hsk/1', 'HSK 1 Curriculum', 'learner'],
    ['/lessons/lesson-1', 'Lesson', 'learner'],
    ['/assessments/assessment-1', 'Assessment', 'learner'],
    ['/assessment-attempts/attempt-1/result', 'Assessment Result', 'learner'],
    ['/progress', 'Progress', 'learner'],
    ['/history', 'History', 'learner'],
    ['/profile', 'Profile', 'learner'],
    ['/admin', 'Admin Dashboard', 'admin'],
    ['/admin/curriculum', 'Admin Curriculum', 'admin'],
    ['/admin/lessons', 'Admin Lessons', 'admin'],
    ['/admin/lessons/lesson-1', 'Admin Lesson Editor', 'admin'],
    ['/admin/assessments', 'Admin Assessments', 'admin'],
    ['/admin/assessments/assessment-1', 'Admin Assessment Editor', 'admin'],
    ['/admin/documents', 'Admin Documents', 'admin'],
    ['/admin/documents/document-1', 'Admin Document', 'admin'],
    ['/admin/stats', 'Admin Stats', 'admin'],
  ])('%s renders %s within the %s layout', (path, heading, layout) => {
    renderAt(path)
    expect(screen.getByRole('heading', { name: heading, level: 1 })).toBeInTheDocument()
    expect(document.querySelector(`[data-layout="${layout}"]`)).toBeInTheDocument()
  })

  it('redirects / to /dashboard', async () => {
    renderAt('/')
    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
  })

  it.each(['/unknown', '/learn', '/chat'])('%s renders NotFoundPage outside product layouts', (path) => {
    renderAt(path)
    expect(screen.getByTestId('not-found')).toBeInTheDocument()
    expect(document.querySelector('[data-layout]')).not.toBeInTheDocument()
  })

  it('maps Learn to /pronunciation and keeps top navigation minimal', () => {
    renderAt('/dashboard')
    const nav = screen.getByRole('navigation', { name: 'Learner navigation' })
    expect(within(nav).getByRole('link', { name: 'Learn' })).toHaveAttribute('href', '/pronunciation')
    expect(within(nav).getAllByRole('link').map((link) => link.textContent)).toEqual([
      'Dashboard', 'Learn', 'Progress', 'History', 'Profile',
    ])
  })

  it('keeps Progress and History as distinct screens', () => {
    const { unmount } = renderAt('/progress')
    expect(screen.getByRole('heading', { name: 'Progress' })).toBeInTheDocument()
    unmount()

    renderAt('/history')
    expect(screen.getByText('Historical assessment attempts and results will be shown here.')).toBeInTheDocument()
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
    const nav = screen.getByRole('navigation', { name: 'Admin navigation' })
    expect(within(nav).getAllByRole('link').map((link) => link.textContent)).toEqual(['Dashboard', 'Curriculum', 'Lessons', 'Assessments', 'Documents', 'Stats'])
    expect(within(nav).getByRole('link', { name: 'Curriculum' })).toHaveAttribute('href', '/admin/curriculum')
    expect(screen.getByRole('link', { name: /Edit HSK display metadata/ })).toHaveAttribute('href', '/admin/curriculum')
  })
})
