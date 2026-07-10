import { expect, test, type Page } from '@playwright/test';

import { installMockApi } from './mock';

declare global {
  interface Window {
    __editor?: { worldToScreen: (x: number, z: number) => { x: number; y: number } };
  }
}

test.beforeEach(async ({ page }) => {
  await installMockApi(page);
});

/** Page coordinates of a world (r, z) point. */
async function atWorld(page: Page, r: number, z: number) {
  const box = (await page.getByTestId('coil-canvas').boundingBox())!;
  const s = await page.evaluate(
    ([x, y]) => window.__editor!.worldToScreen(x, y),
    [r, z] as [number, number],
  );
  return { x: box.x + s.x, y: box.y + s.y };
}

async function dragBody(page: Page, from: { x: number; y: number }, to: { x: number; y: number }) {
  await page.mouse.move(from.x, from.y);
  await page.mouse.down();
  await page.mouse.move(to.x, to.y, { steps: 12 });
  await page.mouse.up();
}

const num = (page: Page, id: string) => page.getByTestId(id).inputValue().then(Number);
const armSelect = (page: Page) => page.getByTestId('tool-select').click();
const activeSections = (page: Page) => page.locator('.sidebar-section.active');

test('dragging a component body moves it (pan default), without resizing', async ({ page }) => {
  await page.goto('/');

  const rBefore = await num(page, 'topload-0-cr');
  const zBefore = await num(page, 'topload-0-cz');
  const radiusBefore = await num(page, 'topload-0-radius');

  // In the pan default, a press-drag on the topload body selects and moves it
  // in one gesture — no tool needed.
  await dragBody(page, await atWorld(page, 7.375, 48.8), await atWorld(page, 11, 40));

  expect(await num(page, 'topload-0-cr')).toBeGreaterThan(rBefore);
  expect(await num(page, 'topload-0-cz')).toBeLessThan(zBefore);
  // A move must not change the radius.
  expect(await num(page, 'topload-0-radius')).toBeCloseTo(radiusBefore, 5);
});

test('a body-drag cannot push a component to negative r', async ({ page }) => {
  await page.goto('/');

  // Grab the secondary body off its midpoint (the wire handle sits at the
  // midpoint), then drag far past the r = 0 axis.
  await dragBody(page, await atWorld(page, 2.27, 30), await atWorld(page, -8, 30));

  const startR = await num(page, 'sec-start-r');
  const endR = await num(page, 'sec-end-r');
  expect(startR).toBeGreaterThanOrEqual(0);
  expect(endR).toBeGreaterThanOrEqual(0);
  // It should have travelled all the way to the axis, not stopped short.
  expect(startR).toBeCloseTo(0, 5);
});

test('box-selecting a group then dragging one member moves them all together', async ({
  page,
}) => {
  await page.goto('/');

  // Box-select the secondary + topload with the Select tool...
  await armSelect(page);
  const boxStart = await atWorld(page, 0, 30);
  const boxEnd = await atWorld(page, 12, 52);
  await page.mouse.move(boxStart.x, boxStart.y);
  await page.mouse.down();
  await page.mouse.move(boxEnd.x, boxEnd.y, { steps: 10 });
  await page.mouse.up();
  await expect(activeSections(page)).toHaveCount(2);
  // A box-select drops straight back to pan, so we can drag right away.
  await expect(page.getByTestId('tool-select')).not.toHaveClass(/active/);

  // Drag one member: the whole group follows.
  const secBefore = await num(page, 'sec-start-r');
  const topBefore = await num(page, 'topload-0-cr');
  await dragBody(page, await atWorld(page, 7.375, 48.8), await atWorld(page, 12.375, 48.8));

  const secAfter = await num(page, 'sec-start-r');
  const topAfter = await num(page, 'topload-0-cr');
  expect(topAfter).toBeGreaterThan(topBefore);
  expect(secAfter).toBeGreaterThan(secBefore);
  // Same rigid delta for both members.
  expect(secAfter - secBefore).toBeCloseTo(topAfter - topBefore, 1);
});
