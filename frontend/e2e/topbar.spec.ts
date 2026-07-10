import { readFileSync } from 'node:fs';

import { expect, test } from '@playwright/test';

import { installMockApi } from './mock';

// The store is exposed on window in dev builds (see state/store.ts).
declare global {
  interface Window {
    __store?: { getState: () => { coil: { primary: unknown; toploads: unknown[] } } };
  }
}

test.beforeEach(async ({ page }) => {
  await installMockApi(page);
});

test('New coil loads a blank secondary-only coil; Demo restores the example', async ({ page }) => {
  await page.goto('/');
  // The demo boots with a primary and a topload.
  const demoState = await page.evaluate(() => window.__store!.getState().coil);
  expect(demoState.primary).not.toBeNull();
  expect(demoState.toploads.length).toBeGreaterThan(0);

  await page.getByTestId('topbar-new').click();
  const blank = await page.evaluate(() => window.__store!.getState().coil);
  expect(blank.primary).toBeNull();
  expect(blank.toploads).toHaveLength(0);

  await page.getByTestId('topbar-demo').click();
  const demoAgain = await page.evaluate(() => window.__store!.getState().coil);
  expect(demoAgain.primary).not.toBeNull();
});

test('Export then import round-trips the session, restoring outputs without recomputing', async ({
  page,
}) => {
  await page.goto('/');

  // Run so there are outputs to persist.
  await page.getByTestId('run').click();
  await expect(page.getByTestId('res-fres')).toHaveText('231 kHz');
  await expect(page.getByTestId('results-status')).toHaveText('up to date');

  // Export the session to a file.
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByTestId('topbar-export').click(),
  ]);
  const path = await download.path();
  expect(download.suggestedFilename()).toMatch(/\.jstc$/);
  const saved = JSON.parse(readFileSync(path, 'utf8'));
  expect(saved.format).toBe('jstc-coil');
  expect(saved.analysis).not.toBeNull();

  // Load a blank coil to clear the outputs...
  await page.getByTestId('topbar-new').click();
  await expect(page.getByTestId('results-status')).toHaveText('not run yet');
  await expect(page.getByTestId('res-fres')).toHaveText('—');

  // ...then import the saved file: outputs come back with no re-run.
  await page.getByTestId('topbar-file-input').setInputFiles(path);
  await expect(page.getByTestId('res-fres')).toHaveText('231 kHz');
  await expect(page.getByTestId('results-status')).toHaveText('up to date');
});

test('importing an unreadable file shows a dismissible notice, not a crash', async ({ page }) => {
  await page.goto('/');
  await page.getByTestId('topbar-file-input').setInputFiles({
    name: 'junk.jstc',
    mimeType: 'application/json',
    buffer: Buffer.from('this is not json'),
  });
  const notice = page.getByTestId('topbar-notice');
  await expect(notice).toBeVisible();
  // The app is still alive and the editor still there.
  await expect(page.getByTestId('coil-canvas')).toBeVisible();
  await notice.getByRole('button', { name: 'Dismiss' }).click();
  await expect(notice).toHaveCount(0);
});
