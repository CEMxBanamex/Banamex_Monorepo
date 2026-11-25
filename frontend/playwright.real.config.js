import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e-real',
  timeout: 30000,
  workers: 1,
  retries: 0,
  reporter: 'list',
  use: {
    browserName: 'chromium',
    baseURL: 'http://127.0.0.1:5189',
    serviceWorkers: 'block',
    trace: 'retain-on-failure',
  },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 5189 --strictPort',
    url: 'http://127.0.0.1:5189',
    reuseExistingServer: false,
    env: { VITE_CHAT_REAL: 'true', VITE_API_URL: 'http://127.0.0.1:8022' },
  },
})
