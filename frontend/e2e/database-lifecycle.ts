import { execFileSync } from 'node:child_process'
import { randomBytes } from 'node:crypto'
import { resolve } from 'node:path'
import type { FullConfig } from '@playwright/test'

const backendDirectory = resolve(process.cwd(), '..', 'backend')

function invoke(module: string, confirmation: string) {
  execFileSync('uv', ['run', 'python', '-m', module, confirmation], {
    cwd: backendDirectory,
    env: { ...process.env, APP_ENV: 'test', DEBUG: 'false' },
    stdio: 'inherit',
  })
}

export default async function databaseLifecycle(_config: FullConfig) {
  // The reset command revalidates APP_ENV, the dedicated DB identity, distinct
  // normal/test targets, PostgreSQL, pgvector and the migration head itself.
  process.env.STEP81_TEST_PASSWORD = randomBytes(32).toString('base64url')
  invoke('tests.step81.reset_test_database', '--confirm-test-database-reset')
  invoke('tests.step81.seed_e2e_fixture', '--confirm-step81-seed')
}

