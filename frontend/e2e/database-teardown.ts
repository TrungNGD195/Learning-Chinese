import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'

export default async function resetStep81DatabaseAfterRun() {
  const backendDirectory = resolve(process.cwd(), '..', 'backend')
  execFileSync('uv', ['run', 'python', '-m', 'tests.step81.reset_test_database', '--confirm-test-database-reset'], {
    cwd: backendDirectory,
    env: { ...process.env, APP_ENV: 'test', DEBUG: 'false' },
    stdio: 'inherit',
  })
}
