import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router'
import { router } from './app/router/router'
import { QueryProvider } from './app/query/QueryProvider'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryProvider><RouterProvider router={router} /></QueryProvider>
  </StrictMode>,
)
