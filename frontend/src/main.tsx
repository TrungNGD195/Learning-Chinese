import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router'
import { router } from './app/router/router'
import { QueryProvider } from './app/query/QueryProvider'
import { TabSessionBoundary } from './features/auth/TabSessionBoundary'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <TabSessionBoundary><QueryProvider><RouterProvider router={router} /></QueryProvider></TabSessionBoundary>
  </StrictMode>,
)
