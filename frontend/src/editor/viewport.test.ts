import { describe, expect, it } from 'vitest';

import {
  domainBounds,
  fitBounds,
  pan,
  screenToWorld,
  worldToScreen,
  zoomAbout,
  type Viewport,
} from './viewport';

const vp: Viewport = { scale: 10, tx: 100, ty: 200 };

describe('worldToScreen / screenToWorld', () => {
  it('maps the world origin to (tx, ty)', () => {
    expect(worldToScreen(vp, 0, 0)).toEqual({ x: 100, y: 200 });
  });

  it('flips z (up in world, down in screen)', () => {
    // +z world should decrease screen y
    expect(worldToScreen(vp, 0, 5).y).toBe(150);
    expect(worldToScreen(vp, 3, 0).x).toBe(130);
  });

  it('is a round-trip inverse', () => {
    for (const [wx, wz] of [
      [0, 0],
      [2.27, 44.8],
      [-7.5, 10],
      [100, -5],
    ] as const) {
      const s = worldToScreen(vp, wx, wz);
      const w = screenToWorld(vp, s.x, s.y);
      expect(w.x).toBeCloseTo(wx, 9);
      expect(w.z).toBeCloseTo(wz, 9);
    }
  });
});

describe('fitBounds', () => {
  it('centers and scales the domain into the canvas', () => {
    const bounds = domainBounds(100, 150); // x in [-100, 100], z in [0, 150]
    const out = fitBounds(bounds, { width: 800, height: 600 }, 40);
    // The domain center (x=0, z=75) should land at the canvas center.
    const center = worldToScreen(out, 0, 75);
    expect(center.x).toBeCloseTo(400, 6);
    expect(center.y).toBeCloseTo(300, 6);
    // Everything must fit within the padded canvas.
    const corner = worldToScreen(out, 100, 150);
    expect(corner.x).toBeLessThanOrEqual(800 - 40 + 1e-6);
  });
});

describe('zoomAbout', () => {
  it('keeps the world point under the cursor fixed', () => {
    const cursor = { x: 250, y: 130 };
    const before = screenToWorld(vp, cursor.x, cursor.y);
    const zoomed = zoomAbout(vp, cursor.x, cursor.y, 1.5);
    const after = screenToWorld(zoomed, cursor.x, cursor.y);
    expect(after.x).toBeCloseTo(before.x, 9);
    expect(after.z).toBeCloseTo(before.z, 9);
    expect(zoomed.scale).toBeCloseTo(15, 9);
  });

  it('clamps to the scale bounds', () => {
    expect(zoomAbout(vp, 0, 0, 1e12, 1e-4, 100).scale).toBe(100);
    expect(zoomAbout(vp, 0, 0, 1e-12, 0.5, 1e9).scale).toBe(0.5);
  });
});

describe('pan', () => {
  it('shifts translation by the screen delta', () => {
    const out = pan(vp, 15, -20);
    expect(out.tx).toBe(115);
    expect(out.ty).toBe(180);
    expect(out.scale).toBe(vp.scale);
  });
});
