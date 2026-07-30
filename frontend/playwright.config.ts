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
    // Konva renders to a real <canvas>, and BOTH chromium headless builds
    // (chrome-headless-shell and full chromium --headless) hang or crash the
    // renderer on this canvas under software rasterization in this container.
    // A HEADED chromium under a virtual X display is the configuration that
    // works, so the canonical entry point is `npm run test:e2e`, which wraps
    // `playwright test --headed` in xvfb-run. A bare `npx playwright test`
    // (headless) is NOT supported here — it hangs on app boot.
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
