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
import { PronunciationPage } from '../../features/pronunciation/PronunciationPage'
import { PronunciationLessonPage, PronunciationSectionPage } from '../../features/pronunciation/PronunciationLessonPage'
import {MeasureWordsPage} from '../../features/curriculum/MeasureWordsPage'
import { HskCurriculumPage } from '../../features/curriculum/HskCurriculumPage'
import { LessonPage } from '../../features/lesson/LessonPage'
import { VocabularyPage } from '../../features/lesson/VocabularyPage'
import { AssessmentPage } from '../../features/assessment/AssessmentPage'
import { AssessmentResultPage } from '../../features/assessment/AssessmentResultPage'
import { ProfilePage } from '../../features/profile/ProfilePage'
import { AdminDocumentsPage } from '../../features/admin/documents/AdminDocumentsPage'
import { AdminDocumentDetailPage } from '../../features/admin/documents/AdminDocumentDetailPage'
import { AdminDashboardPage } from '../../features/admin/AdminDashboardPage'
import { AdminStatsPage } from '../../features/admin/AdminStatsPage'
import { AdminProfilePage } from '../../features/admin/AdminProfilePage'
import { AdminLessonsPage } from '../../features/admin/AdminLessonsPage'
import { AdminLessonEditorPage } from '../../features/admin/AdminLessonEditorPage'
import { AdminAssessmentsPage, AdminAssessmentEditorPage } from '../../features/admin/AdminAssessmentsPage'
import { AdminRoute, ProtectedRoute, PublicAuthRoute } from './RouteGuards'
import { RouteErrorBoundary } from '../RouteErrorBoundary'

export function createAppRoutes(): RouteObject[] {
  return [
    { element: <Outlet />, errorElement: <RouteErrorBoundary />, children: [
    { path: '/', loader: () => redirect('/login') },
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
        { path: '/dashboard', loader: () => redirect('/pronunciation') },
        { path: '/pronunciation', element: <PronunciationPage /> },
        { path: '/pronunciation/lesson', element: <PronunciationLessonPage /> },
        { path: '/pronunciation/lesson/:sectionSlug', element: <PronunciationSectionPage /> },
        { path: '/hsk/:hskLevel', element: <HskCurriculumPage /> },
        { path: '/measure-words', element: <MeasureWordsPage /> },
        { path: '/preview/great-wall/*', loader: () => redirect('/pronunciation') },
        { path: '/lessons/:lessonId', element: <LessonPage /> },
        { path: '/lessons/:lessonId/vocabulary', element: <LessonPage /> },
        { path: '/lessons/:lessonId/vocabulary/:vocabularyId', element: <VocabularyPage /> },
        { path: '/lessons/:lessonId/grammar', element: <LessonPage part="grammar"/> },
        { path: '/lessons/:lessonId/readings', element: <LessonPage part="readings"/> },
        { path: '/lessons/:lessonId/practice', element: <LessonPage part="practice"/> },
        { path: '/assessments/:assessmentId', element: <AssessmentPage /> },
        {
          path: '/assessment-attempts/:attemptId/result',
          element: <AssessmentResultPage />,
        },
        { path: '/progress', loader: () => redirect('/pronunciation') },
        { path: '/history', loader: () => redirect('/pronunciation') },
        { path: '/profile', element: <ProfilePage /> },
        { path: '/companions', loader: () => redirect('/profile#companions') },
        ] },
      ],
    },
    {
      element: <AdminRoute />,
      children: [
        { path: '/admin', element: <AdminLayout />, children: [
        { index: true, element: <AdminDashboardPage /> },
        { path: 'curriculum', loader: () => redirect('/admin/lessons?view=curriculum') },
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
        { path: 'profile', element: <AdminProfilePage /> },
        ] },
      ],
    },
    { path: '*', element: <NotFoundPage /> },
    ] },
  ]
}
