import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/database-lifecycle.ts',
  globalTeardown: './e2e/database-teardown.ts',
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:4173',
    trace: 'retain-on-failure',
    ...devices['Desktop Chrome'],
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: 'uv run python -m tests.step81.run_e2e_server',
      cwd: '../backend',
      url: 'http://127.0.0.1:8000/health',
      reuseExistingServer: false,
      timeout: 30_000,
      env: {
        APP_ENV: 'test',
        DEBUG: 'false',
        CORS_ORIGINS: 'http://127.0.0.1:4173',
      },
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 4173 --strictPort',
      url: 'http://127.0.0.1:4173',
      reuseExistingServer: false,
      timeout: 30_000,
      env: { VITE_API_BASE_URL: 'http://127.0.0.1:8000/api/v1' },
    },
  ],
})
