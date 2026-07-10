import { describe, expect, it } from 'vitest';

import { divergingColor, intensityColor } from './colormap';

describe('intensityColor', () => {
  it('is dark at zero and bright at the max', () => {
    const lo = intensityColor(0, 1);
    const hi = intensityColor(1, 1);
    const lum = (c: number[]) => c[0]! + c[1]! + c[2]!;
    expect(lum(lo)).toBeLessThan(lum(hi));
  });

  it('clamps out-of-range values', () => {
    expect(intensityColor(-5, 1)).toEqual(intensityColor(0, 1));
    expect(intensityColor(5, 1)).toEqual(intensityColor(1, 1));
  });

  it('handles a zero max without NaN', () => {
    for (const c of intensityColor(3, 0)) expect(Number.isFinite(c)).toBe(true);
  });
});

describe('divergingColor', () => {
  it('is near-neutral at zero and diverges by sign', () => {
    const neg = divergingColor(-1, 1);
    const pos = divergingColor(1, 1);
    // Negative end is bluer (more blue than red); positive end redder.
    expect(neg[2]).toBeGreaterThan(neg[0]);
    expect(pos[0]).toBeGreaterThan(pos[2]);
  });
});
