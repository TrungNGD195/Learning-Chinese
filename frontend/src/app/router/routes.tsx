import type { RouteObject } from 'react-router'
import { Outlet, redirect } from 'react-router'
import { AdminLayout } from '../layouts/AdminLayout'
import { LearnerLayout } from '../layouts/LearnerLayout'
import { PublicLayout } from '../layouts/PublicLayout'
import { NotFoundPage } from '../NotFoundPage'
import {
  ForgotPasswordPage,
  LoginPage,
  RegisterPage,
  ResetPasswordPage,
} from '../../features/auth/PublicPages'
import { DashboardPage } from '../../features/dashboard/DashboardPage'
import { PronunciationPage } from '../../features/pronunciation/PronunciationPage'
import { HskCurriculumPage } from '../../features/curriculum/HskCurriculumPage'
import { LessonPage } from '../../features/lesson/LessonPage'
import { AssessmentPage } from '../../features/assessment/AssessmentPage'
import { AssessmentResultPage } from '../../features/assessment/AssessmentResultPage'
import { ProgressPage } from '../../features/progress/ProgressPage'
import { HistoryPage } from '../../features/history/HistoryPage'
import { ProfilePage } from '../../features/profile/ProfilePage'
import { AdminDocumentsPage } from '../../features/admin/documents/AdminDocumentsPage'
import { AdminDocumentDetailPage } from '../../features/admin/documents/AdminDocumentDetailPage'
import { AdminDashboardPage } from '../../features/admin/AdminDashboardPage'
import { AdminCurriculumPage } from '../../features/admin/AdminCurriculumPage'
import { AdminLessonsPage } from '../../features/admin/AdminLessonsPage'
import { AdminLessonEditorPage } from '../../features/admin/AdminLessonEditorPage'
import { AdminAssessmentsPage, AdminAssessmentEditorPage } from '../../features/admin/AdminAssessmentsPage'
import { AdminStatsPage } from '../../features/admin/AdminStatsPage'
import { AdminRoute, ProtectedRoute, PublicAuthRoute } from './RouteGuards'
import { RouteErrorBoundary } from '../RouteErrorBoundary'

export function createAppRoutes(): RouteObject[] {
  return [
    { element: <Outlet />, errorElement: <RouteErrorBoundary />, children: [
    { path: '/', loader: () => redirect('/dashboard') },
    {
      element: <PublicLayout />,
      children: [
        { element: <PublicAuthRoute />, children: [
        { path: '/login', element: <LoginPage /> },
        { path: '/register', element: <RegisterPage /> },
        { path: '/forgot-password', element: <ForgotPasswordPage /> },
        { path: '/reset-password', element: <ResetPasswordPage /> },
        ] },
      ],
    },
    {
      element: <ProtectedRoute />,
      children: [
        { element: <LearnerLayout />, children: [
        { path: '/dashboard', element: <DashboardPage /> },
        { path: '/pronunciation', element: <PronunciationPage /> },
        { path: '/hsk/:hskLevel', element: <HskCurriculumPage /> },
        { path: '/lessons/:lessonId', element: <LessonPage /> },
        { path: '/assessments/:assessmentId', element: <AssessmentPage /> },
        {
          path: '/assessment-attempts/:attemptId/result',
          element: <AssessmentResultPage />,
        },
        { path: '/progress', element: <ProgressPage /> },
        { path: '/history', element: <HistoryPage /> },
        { path: '/profile', element: <ProfilePage /> },
        ] },
      ],
    },
    {
      element: <AdminRoute />,
      children: [
        { path: '/admin', element: <AdminLayout />, children: [
        { index: true, element: <AdminDashboardPage /> },
        { path: 'curriculum', element: <AdminCurriculumPage /> },
        { path: 'lessons', element: <AdminLessonsPage /> },
        { path: 'lessons/:lessonId', element: <AdminLessonEditorPage /> },
        { path: 'assessments', element: <AdminAssessmentsPage /> },
        {
          path: 'assessments/:assessmentId',
          element: <AdminAssessmentEditorPage />,
        },
        { path: 'documents', element: <AdminDocumentsPage /> },
        { path: 'documents/:documentId', element: <AdminDocumentDetailPage /> },
        { path: 'stats', element: <AdminStatsPage /> },
        ] },
      ],
    },
    { path: '*', element: <NotFoundPage /> },
    ] },
  ]
}
