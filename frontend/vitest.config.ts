import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    // Konva needs canvas; jsdom lacks it. Components that render Konva are
    // covered by Playwright e2e; unit tests target pure logic + DOM UI.
    exclude: ['**/node_modules/**', 'e2e/**'],
  },
});
