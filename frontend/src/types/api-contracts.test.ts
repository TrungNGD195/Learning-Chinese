import { expect, expectTypeOf, it } from 'vitest'
import type { paths } from './api.generated'

const requiredPaths = [
  '/api/v1/auth/login',
  '/api/v1/me/dashboard',
  '/api/v1/assessments/{assessment_id}',
  '/api/v1/conversations',
  '/api/v1/conversations/{conversation_id}/messages',
  '/api/v1/admin/lessons',
  '/api/v1/admin/assessments/{assessment_id}/questions',
] as const satisfies readonly (keyof paths)[]

it('contains representative generated paths from accepted backend API groups', () => {
  expectTypeOf(requiredPaths).toMatchTypeOf<readonly (keyof paths)[]>()
  expect(requiredPaths).toHaveLength(7)
})
