import { expect, test, type Page } from '@playwright/test';

import { installMockApi } from './mock';

// The dev build exposes the store for driving deterministic state.
declare global {
  interface Window {
    __store?: {
      getState: () => {
        fieldCursors: { id: string }[];
        moveFieldCursor: (id: string, x: number, z: number) => void;
      };
    };
  }
}

test.beforeEach(async ({ page }) => {
  await installMockApi(page);
});

/** Solve, then open the E-field view (field views unlock once a bundle exists). */
async function openEField(page: Page) {
  await page.goto('/');
  await page.getByTestId('run').click();
  await expect(page.getByTestId('mode-efield')).toBeEnabled();
  await page.getByTestId('mode-efield').click();
  await expect(page.getByTestId('field-drive-panel')).toBeVisible();
}

/** Move the first cursor into the interior of the mocked field grid so every
 *  quantity samples to a real value (the mock grid spans 0..100 × 0..150). */
async function centreFirstCursor(page: Page) {
  await page.evaluate(() => {
    const s = window.__store!.getState();
    s.moveFieldCursor(s.fieldCursors[0]!.id, 50, 75);
  });
}

test('shows a live (r, z) readout while hovering the view', async ({ page }) => {
  await openEField(page);
  const readout = page.locator('.coord-readout');
  const canvas = page.getByTestId('coil-canvas');
  const box = (await canvas.boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await expect(readout).toHaveText(/\(r, z\) =/);
  await expect(readout).toHaveCSS('opacity', '1');
});

test('adds a cursor and samples potential + intensity at it', async ({ page }) => {
  await openEField(page);
  await expect(page.getByText(/Add a point to read the field/)).toBeVisible();

  await page.getByTestId('cursor-add').click();
  const card = page.getByTestId('cursor-card');
  await expect(card).toHaveCount(1);
  await expect(card.getByText('Cursor 1')).toBeVisible();

  await centreFirstCursor(page);

  // Every row is present and reads a real value (not the em-dash placeholder).
  for (const label of ['Position (r, z)', 'E-field', 'Potential', 'Field intensity']) {
    const value = card.locator('.cursor-row', { hasText: label }).locator('.cursor-row-value');
    await expect(value).not.toHaveText('—');
    await expect(value).toContainText(/\d/);
  }
});

test('clicking a value copies its full-precision form to the clipboard', async ({
  page,
  context,
}) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await openEField(page);
  await page.getByTestId('cursor-add').click();
  await centreFirstCursor(page);

  const row = page.locator('.cursor-row', { hasText: 'Potential' });
  await row.click();
  await expect(row).toHaveClass(/copied/);
  const clip = await page.evaluate(() => navigator.clipboard.readText());
  expect(clip).toMatch(/^-?[\d.]+ ?[a-zµ]*V$/); // a potential value, in volts
  // (full-precision-vs-displayed formatting is covered by the fieldFormat unit test)
});

test('cursors persist across E/B views with field-appropriate labels', async ({ page }) => {
  await openEField(page);
  await page.getByTestId('cursor-add').click();
  const card = page.getByTestId('cursor-card');
  await expect(card).toHaveCount(1);
  await expect(card.locator('.cursor-row-label', { hasText: 'E-field' })).toBeVisible();

  await page.getByTestId('mode-bfield').click();
  // Same cursor, now labelled for the magnetic field.
  await expect(card).toHaveCount(1);
  await expect(card.locator('.cursor-row-label', { hasText: 'B-field' })).toBeVisible();
  await expect(card.locator('.cursor-row-label', { hasText: 'Vector potential' })).toBeVisible();
});

test('a cursor can be removed', async ({ page }) => {
  await openEField(page);
  await page.getByTestId('cursor-add').click();
  await expect(page.getByTestId('cursor-card')).toHaveCount(1);
  await page.getByTestId('cursor-remove').click();
  await expect(page.getByTestId('cursor-card')).toHaveCount(0);
  await expect(page.getByText(/Add a point to read the field/)).toBeVisible();
});
