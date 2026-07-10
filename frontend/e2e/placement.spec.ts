import { expect, test } from '@playwright/test';

import { installMockApi } from './mock';

test.beforeEach(async ({ page }) => {
  await installMockApi(page);
});

test('Escape cancels an armed placement, dropping back to pan', async ({ page }) => {
  await page.goto('/');

  // Arm topload placement via the geometry dropdown.
  await page.getByTestId('tool-topload').click();
  await page.getByTestId('shape-topload-circle').click();
  await expect(page.getByTestId('tool-topload')).toHaveClass(/active/);

  // Escape backs out to the pan default.
  await page.keyboard.press('Escape');
  await expect(page.getByTestId('tool-topload')).not.toHaveClass(/active/);

  // A subsequent canvas click therefore pans rather than placing: the topload
  // count stays at one (no "Topload #2").
  const box = (await page.getByTestId('coil-canvas').boundingBox())!;
  await page.mouse.click(box.x + box.width * 0.6, box.y + box.height * 0.3);
  await expect(page.getByText('Topload #2')).toHaveCount(0);
});
