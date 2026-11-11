import {StrictMode} from 'react'
import {createRoot} from 'react-dom/client'
import {BrowserRouter} from 'react-router'
import {AcademyPreview} from './AcademyPreview'
import '../../index.css'
import './academy-preview.css'

// Independent preview entry: no authentication/session initialization or API
// query provider. Trying the concept cannot log out or mutate a real account.
createRoot(document.getElementById('root')!).render(
  <StrictMode><BrowserRouter><AcademyPreview/></BrowserRouter></StrictMode>,
)
