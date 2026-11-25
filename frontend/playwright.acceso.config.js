import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e-acceso',
  timeout: 30000,
  expect: { timeout: 10000 },
  workers: 1,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    browserName: 'chromium',
    baseURL: 'http://127.0.0.1:5197',
    serviceWorkers: 'allow',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 5197 --strictPort',
    url: 'http://127.0.0.1:5197',
    reuseExistingServer: false,
    env: { VITE_API_URL: '', VITE_CHAT_REAL: 'false', VITE_ACCESO_DEMO: 'true' },
  },
})
