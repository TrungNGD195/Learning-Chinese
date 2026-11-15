import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { CultureLessonPreview } from './CultureLessonPreview'
import '../../index.css'

createRoot(document.getElementById('root')!).render(<StrictMode><CultureLessonPreview/></StrictMode>)
