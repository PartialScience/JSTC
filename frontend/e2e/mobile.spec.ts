import { devices, expect, test, type Page } from '@playwright/test';

import { installMockApi } from './mock';

// Run this file as a touch phone (Android/Chromium descriptor: hasTouch,
// isMobile). The canvas gesture handlers key off real touch events.
test.use({ ...devices['Pixel 5'] });

declare global {
  interface Window {
    __editor?: {
      worldToScreen: (x: number, z: number) => { x: number; y: number };
      viewport: { scale: number; tx: number; ty: number };
    };
  }
}

test.beforeEach(async ({ page }) => {
  await installMockApi(page);
});

async function pagePoint(page: Page, r: number, z: number) {
  const box = (await page.getByTestId('coil-canvas').boundingBox())!;
  const s = await page.evaluate(
    // Specs author coords in the inch display unit; the coil's world is metres.
    ([x, y]) => window.__editor!.worldToScreen(x * 0.0254, y * 0.0254),
    [r, z] as [number, number],
  );
  return { x: box.x + s.x, y: box.y + s.y };
}

const activeSections = (page: Page) => page.locator('.sidebar-section.active');

test('tapping a component selects it — no tool needed (touch)', async ({ page }) => {
  await page.goto('/');
  await page.getByTestId('coil-canvas').waitFor();

  const p = await pagePoint(page, 7.375, 48.8); // the topload body
  await page.touchscreen.tap(p.x, p.y);
  await expect(activeSections(page).getByText('Topload #1')).toBeVisible();
});

test('one-finger drag pans the viewport (touch)', async ({ page }) => {
  await page.goto('/');
  await page.getByTestId('coil-canvas').waitFor();

  const before = await page.evaluate(() => window.__editor!.viewport.tx);

  // Dispatch a real one-finger drag over empty space via CDP.
  const from = await pagePoint(page, -5, 60);
  const to = await pagePoint(page, -25, 60);
  const client = await page.context().newCDPSession(page);
  await client.send('Input.dispatchTouchEvent', {
    type: 'touchStart',
    touchPoints: [{ x: from.x, y: from.y }],
  });
  for (let i = 1; i <= 8; i++) {
    const x = from.x + ((to.x - from.x) * i) / 8;
    const y = from.y + ((to.y - from.y) * i) / 8;
    await client.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x, y }] });
  }
  await client.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });

  const after = await page.evaluate(() => window.__editor!.viewport.tx);
  expect(Math.abs(after - before)).toBeGreaterThan(20);
});

test('the Select tool box-selects via a one-finger drag (touch)', async ({ page }) => {
  await page.goto('/');
  await page.getByTestId('coil-canvas').waitFor();

  await page.getByTestId('tool-select').tap();
  await expect(page.getByTestId('tool-select')).toHaveClass(/active/);

  // Drag a box over the secondary + primary (below the topload) via CDP touch.
  const from = await pagePoint(page, -1, 20);
  const to = await pagePoint(page, 9, 44);
  const client = await page.context().newCDPSession(page);
  await client.send('Input.dispatchTouchEvent', {
    type: 'touchStart',
    touchPoints: [{ x: from.x, y: from.y }],
  });
  for (let i = 1; i <= 8; i++) {
    const x = from.x + ((to.x - from.x) * i) / 8;
    const y = from.y + ((to.y - from.y) * i) / 8;
    await client.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x, y }] });
  }
  await client.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });

  await expect(activeSections(page)).toHaveCount(2);
});

test('tap empty clears the selection (touch)', async ({ page }) => {
  await page.goto('/');
  await page.getByTestId('coil-canvas').waitFor();
  const box = (await page.getByTestId('coil-canvas').boundingBox())!;

  // Select a component first (nothing is selected by default).
  const tl = await pagePoint(page, 7.375, 48.8); // the topload body
  await page.touchscreen.tap(tl.x, tl.y);
  await expect(activeSections(page)).toHaveCount(1);

  // A tap on clearly-empty canvas clears the selection.
  await page.touchscreen.tap(box.x + box.width * 0.12, box.y + box.height * 0.12);
  await expect(activeSections(page)).toHaveCount(0);
});
