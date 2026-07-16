import { expect, test } from '@playwright/test';

import { installMockApi } from './mock';

// The transform API the canvas exposes for coordinate-based interaction.
declare global {
  interface Window {
    __editor?: {
      worldToScreen: (x: number, z: number) => { x: number; y: number };
      screenToWorld: (sx: number, sy: number) => { x: number; z: number };
    };
  }
}

test.beforeEach(async ({ page }) => {
  await installMockApi(page);
});

/** Set a QuantityField value robustly. The field carries the unit inline while
 *  focused ("0.02 in"), so a bare fill() races the focus-reformat and appends;
 *  select-all then type replaces cleanly, and blur settles it to the number. */
async function setQuantity(
  page: import('@playwright/test').Page,
  testId: string,
  value: string,
) {
  const field = page.getByTestId(testId);
  await field.click();
  await field.press('ControlOrMeta+a');
  // Insert the whole value as ONE input event (not per keystroke), so it is a
  // single committed edit — otherwise each character is its own undo step.
  await page.keyboard.insertText(value);
  await field.blur();
}

test('loads the editor with sidebar, toolbar and canvas', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByTestId('sidebar')).toBeVisible();
  await expect(page.getByTestId('coil-canvas')).toBeVisible();
  await expect(page.getByTestId('tool-topload')).toBeVisible();
  await expect(page.getByTestId('run')).toBeVisible();
  await expect(page.getByTestId('sec-wire-dia')).toBeVisible();
});

test('all output labels are shown before running, with no values', async ({ page }) => {
  await page.goto('/');
  // The full spec sheet is visible immediately...
  await expect(page.getByText('Resonant frequency').first()).toBeVisible();
  await expect(page.getByText('k (coupling)')).toBeVisible();
  await expect(page.getByText('Lower mode')).toBeVisible();
  await expect(page.getByText('Q factor')).toBeVisible();
  // ...but values are placeholders until the calculation runs.
  await expect(page.getByTestId('res-fres')).toHaveText('—');
  await expect(page.getByTestId('res-k')).toHaveText('—');
  await expect(page.getByTestId('results-status')).toHaveText('not run yet');
});

test('Run button computes the results and clears the dirty state', async ({ page }) => {
  await page.goto('/');
  await page.getByTestId('run').click();
  await expect(page.getByTestId('res-fres')).toHaveText('231 kHz');
  await expect(page.getByTestId('res-k')).toHaveText('0.130');
  await expect(page.getByTestId('res-split-lower')).not.toHaveText('—');
  await expect(page.getByTestId('results-status')).toHaveText('up to date');
});

test('editing after a run marks results stale until re-run', async ({ page }) => {
  await page.goto('/');
  await page.getByTestId('run').click();
  await expect(page.getByTestId('results-status')).toHaveText('up to date');

  await setQuantity(page, 'sec-wire-dia', '0.05');
  await expect(page.getByTestId('results-status')).toHaveText('stale — geometry changed');

  await page.getByTestId('run').click();
  await expect(page.getByTestId('results-status')).toHaveText('up to date');
});

test('placing a topload adds it to the sidebar and canvas', async ({ page }) => {
  await page.goto('/');
  // Clicking the button opens its geometry menu; picking a shape arms placement.
  await page.getByTestId('tool-topload').click();
  await page.getByTestId('shape-topload-circle').click();
  const box = (await page.getByTestId('coil-canvas').boundingBox())!;
  await page.mouse.click(box.x + box.width * 0.7, box.y + box.height * 0.25);
  await expect(page.getByText('Topload #2')).toBeVisible();
});

test('the placement geometry menu picks the shape that gets placed', async ({ page }) => {
  await page.goto('/');
  // The geometry menu lives in the button and only opens on click — no second
  // control appears in the toolbar.
  await expect(page.getByTestId('shape-menu-ground')).toBeHidden();
  await page.getByTestId('tool-ground').click();
  await expect(page.getByTestId('shape-menu-ground')).toBeVisible();
  await page.getByTestId('shape-ground-rectangle').click();
  // Choosing closes the menu and arms the tool.
  await expect(page.getByTestId('shape-menu-ground')).toBeHidden();

  const box = (await page.getByTestId('coil-canvas').boundingBox())!;
  await page.mouse.click(box.x + box.width * 0.6, box.y + box.height * 0.7);

  // The new ground is a rectangle (4 vertices), not the old default circle.
  await expect(page.getByText('rectangle — 4 vertices')).toBeVisible();
});

test('the primary and secondary buttons gray out once one exists', async ({ page }) => {
  await page.goto('/');
  // The default coil already has both a secondary and a primary, and only one
  // of each is allowed, so both placement buttons start disabled — the same
  // behavior for both singletons.
  await expect(page.getByTestId('tool-secondary')).toBeDisabled();
  await expect(page.getByTestId('tool-primary')).toBeDisabled();
});

test('dragging the secondary end handle updates the sidebar value', async ({ page }) => {
  await page.goto('/');
  const endZBefore = Number(await page.getByTestId('sec-end-z').inputValue());
  const endR = Number(await page.getByTestId('sec-end-r').inputValue());

  const box = (await page.getByTestId('coil-canvas').boundingBox())!;
  const screen = await page.evaluate(
    ([r, z]) => window.__editor!.worldToScreen(r * 0.0254, z * 0.0254),
    [endR, endZBefore] as [number, number],
  );
  await page.mouse.move(box.x + screen.x, box.y + screen.y);
  await page.mouse.down();
  await page.mouse.move(box.x + screen.x, box.y + screen.y - 60, { steps: 8 });
  await page.mouse.up();

  const endZAfter = Number(await page.getByTestId('sec-end-z').inputValue());
  expect(endZAfter).toBeGreaterThan(endZBefore);
});

test('undo reverts an edit (button and Ctrl+Z)', async ({ page }) => {
  await page.goto('/');
  const wire = page.getByTestId('sec-wire-dia');
  const original = await wire.inputValue();

  await setQuantity(page, 'sec-wire-dia', '0.09');
  await expect(wire).toHaveValue('0.09');

  // Undo button reverts.
  await page.getByTestId('undo').click();
  await expect(wire).toHaveValue(original);

  // Redo re-applies.
  await page.getByTestId('redo').click();
  await expect(wire).toHaveValue('0.09');

  // Ctrl+Z from outside an input also undoes (focus the canvas first).
  await page.getByTestId('coil-canvas').click({ position: { x: 20, y: 20 } });
  await page.keyboard.press('Control+z');
  await expect(wire).toHaveValue(original);
});

test('right-click opens a context menu; Edit selects the component', async ({ page }) => {
  await page.goto('/');
  const box = (await page.getByTestId('coil-canvas').boundingBox())!;
  const screen = await page.evaluate(
    ([r, z]) => window.__editor!.worldToScreen(r * 0.0254, z * 0.0254),
    [7.375, 48.8] as [number, number],
  );
  await page.mouse.click(box.x + screen.x, box.y + screen.y, { button: 'right' });
  await expect(page.getByTestId('context-menu')).toBeVisible();
  await page.getByTestId('ctx-edit').click();
  await expect(page.locator('.sidebar-section.active').getByText('Topload #1')).toBeVisible();
});

test('full shape editing: convert a topload to a polygon and edit vertices', async ({
  page,
}) => {
  await page.goto('/');
  await page.getByTestId('sidebar').getByText('Topload #1').click();
  await page.getByTestId('topload-0-kind').selectOption('polygon');
  await expect(page.getByTestId('topload-0-vertices')).toBeVisible();
  await expect(page.getByTestId('topload-0-v0-r')).toBeVisible();

  const before = await page.getByTestId('topload-0-v0-r').inputValue();
  await setQuantity(page, 'topload-0-v0-r', '42');
  await expect(page.getByTestId('topload-0-v0-r')).toHaveValue('42');
  expect(before).not.toBe('42');

  await page.getByTestId('topload-0-add-vertex').click();
  await expect(page.getByTestId('topload-0-v16-r')).toBeVisible();
  await page.getByTestId('topload-0-v16-del').click();
  await expect(page.getByTestId('topload-0-v16-r')).toHaveCount(0);
});

test('dragging a polygon vertex handle updates the sidebar', async ({ page }) => {
  await page.goto('/');
  await page.getByTestId('sidebar').getByText('Topload #1').click();
  await page.getByTestId('topload-0-kind').selectOption('rectangle');

  const r0Before = Number(await page.getByTestId('topload-0-v0-r').inputValue());
  const z0 = Number(await page.getByTestId('topload-0-v0-z').inputValue());
  const box = (await page.getByTestId('coil-canvas').boundingBox())!;
  const screen = await page.evaluate(
    ([r, z]) => window.__editor!.worldToScreen(r * 0.0254, z * 0.0254),
    [r0Before, z0] as [number, number],
  );
  await page.mouse.move(box.x + screen.x, box.y + screen.y);
  await page.mouse.down();
  await page.mouse.move(box.x + screen.x + 40, box.y + screen.y, { steps: 6 });
  await page.mouse.up();

  const r0After = Number(await page.getByTestId('topload-0-v0-r').inputValue());
  expect(r0After).not.toBe(r0Before);
});

test('SPICE export is enabled after a run and downloads a netlist', async ({ page }) => {
  await page.goto('/');
  // Disabled before the first run (no bundle yet).
  await expect(page.getByTestId('spice-export')).toBeDisabled();

  await page.getByTestId('run').click();
  await expect(page.getByTestId('res-fres')).not.toHaveText('—');

  const downloadPromise = page.waitForEvent('download');
  await page.getByTestId('spice-export').click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe('teslacoil.cir');
});

test('impedance sweep controls (fmin/fmax/points) drive the request', async ({ page }) => {
  const stats = await installMockApi(page);
  await page.goto('/');
  await page.getByTestId('run').click();

  // Controls appear with the sweep once results are in; default 1000 points.
  await expect(page.getByTestId('impedance-controls')).toBeVisible();
  await expect(page.getByTestId('imp-points')).toHaveValue('1000');
  await expect.poll(() => stats.lastImpedance?.count).toBe(1000);

  // The sweep renders as a Bode plot: magnitude and phase panels.
  await expect(page.getByTestId('bode-magnitude')).toBeVisible();
  await expect(page.getByTestId('bode-phase')).toBeVisible();

  // Changing the point count re-requests the sweep with that many points.
  await page.getByTestId('imp-points').fill('25');
  await expect.poll(() => stats.lastImpedance?.count).toBe(25);

  // Widening f max re-requests with the new upper endpoint (Hz).
  await page.getByTestId('imp-fmax').fill('500');
  await expect.poll(() => stats.lastImpedance?.fmaxHz).toBe(500e3);

  // Auto resets the range back to the resonance window (1000 points).
  await page.getByTestId('imp-auto').click();
  await expect(page.getByTestId('imp-points')).toHaveValue('1000');

  // An inverted range shows a validation message instead of a chart.
  await page.getByTestId('imp-fmin').fill('9999');
  await expect(page.getByTestId('imp-invalid')).toBeVisible();
});

test('eigenmode pane: plots modes, selector + normalize, CSV export', async ({ page }) => {
  await page.goto('/');
  await page.getByTestId('run').click();
  await expect(page.getByTestId('res-fres')).not.toHaveText('—');

  // Both stacked panels render, with a legend beside them.
  await expect(page.getByTestId('eigen-voltage')).toBeVisible();
  await expect(page.getByTestId('eigen-current')).toBeVisible();
  const legend = page.getByTestId('eigen-legend');
  // Default: fundamental + two overtones -> 3 legend rows.
  await expect(legend.getByText(/^Mode /)).toHaveCount(3);

  // The selector chips toggle a mode in/out of the legend.
  const selector = page.getByTestId('eigen-selector');
  await selector.getByRole('button').nth(2).click(); // drop mode 3
  await expect(legend.getByText(/^Mode /)).toHaveCount(2);
  await page.getByTestId('eigen-none').click();
  await expect(page.getByText('Select a mode to plot.')).toBeVisible();
  await page.getByTestId('eigen-all').click();
  await expect(legend.getByText(/^Mode /)).toHaveCount(3);

  // Normalize toggles without error.
  await page.getByTestId('eigen-normalize').check();
  await expect(page.getByTestId('eigen-normalize')).toBeChecked();

  // Export writes a CSV.
  const downloadPromise = page.waitForEvent('download');
  await page.getByTestId('eigen-csv').click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe('eigenmodes.csv');
});

test('matrix pane: steps through matrices in a grid and exports CSV', async ({ page }) => {
  await page.goto('/');
  // Before a run there is a placeholder, not a grid.
  await expect(page.getByTestId('matrix-viewer')).toHaveCount(0);

  await page.getByTestId('run').click();
  await expect(page.getByTestId('res-fres')).not.toHaveText('—');

  // The mock bundle populates all four matrices; the grid renders with the
  // first (capacitance) shown.
  await expect(page.getByTestId('matrix-viewer')).toBeVisible();
  await expect(page.getByTestId('matrix-grid')).toBeVisible();
  const title = page.getByTestId('matrix-title');
  await expect(title).toContainText('Capacitance');
  await expect(title).toContainText('1/4');

  // Arrows step through, wrapping around at the ends.
  await page.getByTestId('matrix-next').click();
  await expect(title).toContainText('Inductance');
  await expect(title).toContainText('2/4');
  await page.getByTestId('matrix-prev').click();
  await page.getByTestId('matrix-prev').click(); // wrap back past 1/4
  await expect(title).toContainText('4/4');

  // Export writes a CSV named after the current matrix.
  const downloadPromise = page.waitForEvent('download');
  await page.getByTestId('matrix-csv').click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe('topload_charge_geometric.csv');
});

test('a backend error shows a helpful banner, not a silent failure', async ({ page }) => {
  await installMockApi(page);
  // Override analyze to simulate the backend being down (500).
  await page.route('**/simulation/analyze', (route) =>
    route.fulfill({ status: 500, body: 'Internal Server Error' }),
  );
  await page.goto('/');
  await page.getByTestId('run').click();
  await expect(page.getByTestId('error-banner')).toBeVisible();
  await expect(page.getByTestId('error-banner')).toContainText('server');
});

test('caching: a cheap edit reuses the bundle (no new matrices solve)', async ({ page }) => {
  const stats = await installMockApi(page);
  await page.goto('/');

  await page.getByTestId('run').click();
  await expect(page.getByTestId('results-status')).toHaveText('up to date');

  // Changing the material is not a geometry change (excluded from the mock's
  // fingerprint), so the bundle is reused: analyze runs again but no matrices
  // solve is triggered.
  await page.getByTestId('sec-material').selectOption('aluminum');
  await page.getByTestId('run').click();
  await expect(page.getByTestId('results-status')).toHaveText('up to date');

  expect(stats.analyze).toBeGreaterThanOrEqual(2);
  expect(stats.matrices).toBe(0);
});

test('caching: revisiting a geometry (undo) reuses its cached bundle', async ({ page }) => {
  const stats = await installMockApi(page);
  await page.goto('/');

  // Solve geometry A.
  await page.getByTestId('run').click();
  await expect(page.getByTestId('results-status')).toHaveText('up to date');

  // Change geometry -> B, solve: a real geometry change fetches matrices.
  await setQuantity(page, 'sec-wire-dia', '0.05');
  await page.getByTestId('run').click();
  await expect(page.getByTestId('results-status')).toHaveText('up to date');
  const matricesAfterB = stats.matrices;
  expect(matricesAfterB).toBeGreaterThanOrEqual(1);

  // Undo back to geometry A and re-run: its bundle is cached, so NO new
  // matrices solve happens (without the cache this would 409 and refetch).
  await page.getByTestId('undo').click();
  await expect(page.getByTestId('sec-wire-dia')).not.toHaveValue('0.05');
  await page.getByTestId('run').click();
  await expect(page.getByTestId('results-status')).toHaveText('up to date');

  expect(stats.matrices).toBe(matricesAfterB);
});

test('field visualization: E/B modes render and drive the field endpoint', async ({ page }) => {
  const stats = await installMockApi(page);
  await page.goto('/');

  // Field modes are locked until the calculation has run (no bundle yet).
  await expect(page.getByTestId('mode-efield')).toBeDisabled();

  await page.getByTestId('run').click();
  await expect(page.getByTestId('results-status')).toHaveText('up to date');
  await expect(page.getByTestId('mode-efield')).toBeEnabled();

  // Switch to the E-field view: the drive panel replaces the parameter panel,
  // the editing tools hide, and a field request is made.
  await page.getByTestId('mode-efield').click();
  await expect(page.getByTestId('field-drive-panel')).toBeVisible();
  await expect(page.getByTestId('sidebar')).toHaveCount(0);
  await expect(page.getByTestId('tool-topload')).toBeHidden();
  await expect.poll(() => stats.lastFieldType).toBe('electric');

  // The drive panel offers the coupled-mode presets and a current field.
  await expect(page.getByTestId('drive-presets')).toBeVisible();
  await expect(page.getByTestId('drive-current')).toBeVisible();

  // Switch to the B-field view -> a magnetic request.
  await page.getByTestId('mode-bfield').click();
  await expect.poll(() => stats.lastFieldType).toBe('magnetic');
  // Reference controls are electric-only.
  await expect(page.getByTestId('drive-reference')).toHaveCount(0);

  // Back to edit: the parameter panel and tools return.
  await page.getByTestId('mode-edit').click();
  await expect(page.getByTestId('sidebar')).toBeVisible();
  await expect(page.getByTestId('tool-topload')).toBeVisible();
});

test('changing the drive frequency refetches the field', async ({ page }) => {
  const stats = await installMockApi(page);
  await page.goto('/');
  await page.getByTestId('run').click();
  await page.getByTestId('mode-efield').click();
  await expect.poll(() => stats.field).toBeGreaterThan(0);

  const before = stats.field;
  // Commit via the robust helper: a bare fill() races the field's focus-time
  // unit reformat and can fail to commit (see setQuantity's note).
  await setQuantity(page, 'drive-frequency', '250000');
  await expect.poll(() => stats.field).toBeGreaterThan(before);
});
