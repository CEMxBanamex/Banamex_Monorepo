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
    baseURL: process.env.CHAT_E2E_URL || 'http://127.0.0.1:5190',
    serviceWorkers: 'block',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
})
