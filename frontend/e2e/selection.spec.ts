import { expect, test, type Page } from '@playwright/test';

import { installMockApi } from './mock';

// The transform API the canvas exposes for coordinate-based interaction.
declare global {
  interface Window {
    __editor?: {
      worldToScreen: (x: number, z: number) => { x: number; y: number };
      viewport: { scale: number; tx: number; ty: number };
    };
    __store?: {
      getState: () => {
        addGround: (center: [number, number], radius: number) => void;
        select: (ref: unknown) => void;
        setSelection: (refs: unknown[]) => void;
      };
    };
  }
}

test.beforeEach(async ({ page }) => {
  await installMockApi(page);
});

/** Screen coordinates (relative to the page) of a world (r, z) point. */
async function atWorld(page: Page, r: number, z: number) {
  const box = (await page.getByTestId('coil-canvas').boundingBox())!;
  const s = await page.evaluate(
    // Specs author coords in the inch display unit; the coil's world is metres.
    ([x, y]) => window.__editor!.worldToScreen(x * 0.0254, y * 0.0254),
    [r, z] as [number, number],
  );
  return { x: box.x + s.x, y: box.y + s.y };
}

const activeSections = (page: Page) => page.locator('.sidebar-section.active');
const armSelect = (page: Page) => page.getByTestId('tool-select').click();

async function clickWorld(page: Page, r: number, z: number) {
  const p = await atWorld(page, r, z);
  await page.mouse.click(p.x, p.y);
}

test('clicking a component selects it — no tool needed (pan default)', async ({ page }) => {
  await page.goto('/');

  // Start from a clean slate, then a plain click on the topload selects it.
  await clickWorld(page, -1, 15); // click empty → clear
  await expect(activeSections(page)).toHaveCount(0);

  await clickWorld(page, 7.375, 48.8); // the topload body
  await expect(activeSections(page).getByText('Topload #1')).toBeVisible();
});

test('clicking empty space clears the selection', async ({ page }) => {
  await page.goto('/');

  await clickWorld(page, 7.375, 48.8);
  await expect(activeSections(page).getByText('Topload #1')).toBeVisible();

  await clickWorld(page, -1, 15); // empty
  await expect(activeSections(page)).toHaveCount(0);
});

test('clicking the sub-pixel-thin secondary selects it (fat hit region)', async ({ page }) => {
  await page.goto('/');

  await clickWorld(page, -1, 15); // clear
  await clickWorld(page, 2.27, 33.9); // right on the thin secondary centerline
  await expect(activeSections(page).getByText('Secondary')).toBeVisible();
});

test('Delete removes the clicked component', async ({ page }) => {
  await page.goto('/');

  await clickWorld(page, 7.375, 48.8);
  await expect(activeSections(page).getByText('Topload #1')).toBeVisible();

  await page.keyboard.press('Delete');
  await expect(page.getByText('Topload #1')).toHaveCount(0);
});

test('the Select tool box-selects every component the drag covers', async ({ page }) => {
  await page.goto('/');

  await clickWorld(page, -1, 15); // clear
  await armSelect(page);
  await expect(page.getByTestId('tool-select')).toHaveClass(/active/);

  // Drag a box over the lower coil: the secondary and primary, but not the
  // topload (which sits above z≈45).
  const start = await atWorld(page, -1, 20);
  const end = await atWorld(page, 9, 44);
  await page.mouse.move(start.x, start.y);
  await page.mouse.down();
  await page.mouse.move(end.x, end.y, { steps: 10 });
  await page.mouse.up();

  await expect(activeSections(page)).toHaveCount(2);
  await expect(activeSections(page).getByText('Secondary')).toBeVisible();
  await expect(activeSections(page).getByText('Primary')).toBeVisible();
  // One-shot: after a box-select it drops back to pan so the group can be dragged.
  await expect(page.getByTestId('tool-select')).not.toHaveClass(/active/);
});

test('the Select tool box-selects instead of panning', async ({ page }) => {
  await page.goto('/');

  await armSelect(page);
  const before = await page.evaluate(() => window.__editor!.viewport.tx);

  // Drag across empty space with Select armed: it draws a (empty) box, it does
  // NOT pan the viewport.
  const from = await atWorld(page, -5, 60);
  const to = await atWorld(page, -20, 60);
  await page.mouse.move(from.x, from.y);
  await page.mouse.down();
  await page.mouse.move(to.x, to.y, { steps: 10 });
  await page.mouse.up();

  expect(await page.evaluate(() => window.__editor!.viewport.tx)).toBe(before);
});

test('dragging empty space pans the viewport (the default gesture)', async ({ page }) => {
  await page.goto('/');

  const before = await page.evaluate(() => window.__editor!.viewport.tx);
  const from = await atWorld(page, -5, 60);
  const to = await atWorld(page, -20, 60);
  await page.mouse.move(from.x, from.y);
  await page.mouse.down();
  await page.mouse.move(to.x, to.y, { steps: 10 });
  await page.mouse.up();
  const after = await page.evaluate(() => window.__editor!.viewport.tx);

  expect(Math.abs(after - before)).toBeGreaterThan(20);
});

test('single selection scrolls its section into view; bulk selection does not', async ({
  page,
}) => {
  await page.goto('/');

  // Seed enough grounds that reaching the last one requires scrolling, then
  // park the scroll at the top by selecting the secondary (near the top).
  await page.evaluate(() => {
    const store = window.__store!.getState();
    for (let i = 0; i < 15; i++) store.addGround([10 + i, 5], 1);
    store.select({ kind: 'secondary' });
  });

  const sidebar = page.getByTestId('sidebar');
  const lastGround = page.locator('[data-ref-key="ground:14"]');

  // Wait for the (smooth) scroll animation to come to rest.
  const settle = async () => {
    let prev = Number.NaN;
    await expect
      .poll(async () => {
        const cur = await sidebar.evaluate((el) => el.scrollTop);
        const stable = cur === prev;
        prev = cur;
        return stable;
      })
      .toBe(true);
    return sidebar.evaluate((el) => el.scrollTop);
  };

  // Initially out of view (sidebar is scrolled to the top).
  await expect(lastGround).not.toBeInViewport();

  // Single-selecting the last ground scrolls its section into view.
  await page.evaluate(() =>
    window.__store!.getState().select({ kind: 'ground', index: 14 }),
  );
  await expect(lastGround).toBeInViewport();
  const settled = await settle();

  // From that settled position, a bulk (multi) selection must leave the scroll
  // untouched — there's no single section to reveal.
  await page.evaluate(() =>
    window.__store!.getState().setSelection([
      { kind: 'ground', index: 0 },
      { kind: 'ground', index: 14 },
    ]),
  );
  // Give any (unwanted) scroll a chance to start, then confirm none did.
  await page.waitForTimeout(300);
  await expect(lastGround).toBeInViewport();
  expect(await sidebar.evaluate((el) => el.scrollTop)).toBe(settled);
});

test('stacked (mobile) layout does not auto-scroll on selection', async ({ page }) => {
  // A narrow viewport triggers the stacked layout (sidebar below the editor,
  // sharing the page scroll). Auto-scrolling there would yank the whole page
  // down past the canvas, so selection must leave the page scroll alone.
  await page.setViewportSize({ width: 500, height: 800 });
  await page.goto('/');

  await page.evaluate(() => {
    const store = window.__store!.getState();
    for (let i = 0; i < 15; i++) store.addGround([10 + i, 5], 1);
    store.select({ kind: 'secondary' });
  });

  const lastGround = page.locator('[data-ref-key="ground:14"]');
  await expect(lastGround).not.toBeInViewport();

  const before = await page.evaluate(() => window.scrollY);
  await page.evaluate(() =>
    window.__store!.getState().select({ kind: 'ground', index: 14 }),
  );
  // Give any (unwanted) scroll a chance to start, then confirm none did: the
  // section stays out of view and the page scroll is unchanged.
  await page.waitForTimeout(300);
  await expect(lastGround).not.toBeInViewport();
  expect(await page.evaluate(() => window.scrollY)).toBe(before);
});
