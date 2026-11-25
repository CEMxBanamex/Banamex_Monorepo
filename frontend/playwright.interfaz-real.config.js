import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e-mcp',
  timeout: 60000,
  expect: { timeout: 20000 },
  workers: 1,
  retries: 0,
  reporter: 'list',
  use: {
    browserName: 'chromium',
    baseURL: 'http://127.0.0.1:5193',
    serviceWorkers: 'block',
    trace: 'retain-on-failure',
  },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 5193 --strictPort',
    url: 'http://127.0.0.1:5193',
    reuseExistingServer: false,
    env: {
      VITE_CHAT_REAL: 'true',
      VITE_API_URL: '',
      CHAT_PROXY_TARGET: 'http://127.0.0.1:8026',
    },
  },
})
