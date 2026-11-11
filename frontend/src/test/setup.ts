import '@testing-library/jest-dom/vitest'
import { cleanup, configure } from '@testing-library/react'
import { afterEach } from 'vitest'

afterEach(cleanup)

// Router/query transitions share CI CPU with jsdom workers and Vite transforms.
configure({ asyncUtilTimeout: 3000 })
