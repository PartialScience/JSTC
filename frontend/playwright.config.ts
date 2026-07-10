import { defineConfig, devices } from '@playwright/test';

/**
 * E2E config. The dev server is started automatically; the backend is
 * mocked in-page via route interception (see e2e/mock.ts), so tests never
 * wait on the real FEM solve.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'list' : [['list']],
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    // Konva renders to a real <canvas>; chrome-headless-shell can crash on
    // canvas/GL in this container, so disable the GPU and force software
    // rendering. The suite runs under xvfb (see package.json test:e2e).
    launchOptions: {
      args: ['--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage'],
    },
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
