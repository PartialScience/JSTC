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

// ---------------------------------------------------------------------------
// Domain-invariant display scaling (the blown-out-map regression).
// ---------------------------------------------------------------------------

import { compressIntensity, compressSigned, INTENSITY_DECADES } from './colormap';
import { robustPeak } from './fieldMath';

/** |E| ~ E0·(r0/d)² around a coil-scale source, sampled at the app's fixed
 *  120×180 grid over a given domain — the same physical field regardless of
 *  how much empty far-field the domain includes. */
function sampleField(Lr: number, Lz: number): { v: Float64Array; nearCoil: number[] } {
  const nr = 120;
  const nz = 180;
  const r0 = 0.08;
  const E0 = 3e6;
  const src = [0.2, 1.2];
  const v = new Float64Array(nr * nz);
  const nearCoil: number[] = [];
  for (let iz = 0; iz < nz; iz++) {
    for (let ir = 0; ir < nr; ir++) {
      const r = (Lr * ir) / (nr - 1);
      const z = (Lz * iz) / (nz - 1);
      const d = Math.max(Math.hypot(r - src[0]!, z - src[1]!), r0);
      v[iz * nr + ir] = E0 * (r0 / d) ** 2;
      if (d < 4 * r0) nearCoil.push(iz * nr + ir);
    }
  }
  return { v, nearCoil };
}

describe('display scaling is domain-invariant (the blown-out-map regression)', () => {
  const small = sampleField(2.54, 3.81); // the default domain
  const large = sampleField(7.62, 11.43); // 3× expanded

  it('documents the old bug: a percentile scale collapses as the domain grows', () => {
    const pct99 = (vals: Float64Array) => {
      const s = [...vals].sort((a, b) => a - b);
      return s[Math.floor(0.99 * s.length)]!;
    };
    // The 99th percentile drops by an order of magnitude on the big domain
    // (far-field cells flood the distribution), which used to clip the top
    // ~60× of the field into one saturated color.
    expect(pct99(small.v) / pct99(large.v)).toBeGreaterThan(5);
  });

  it('robustPeak stays anchored to the field peak across domain sizes', () => {
    const a = robustPeak(small.v);
    const b = robustPeak(large.v);
    // Same physical field ⇒ same scale, up to grid-sampling of the hottest
    // cells (the big domain samples the peak more coarsely).
    expect(Math.max(a, b) / Math.min(a, b)).toBeLessThan(2);
  });

  it('the compressed map resolves near-coil structure on BOTH domains', () => {
    for (const { v, nearCoil } of [small, large]) {
      const t = compressIntensity(v, robustPeak(v));
      // No saturated ball: only a whisker of cells at the ramp top.
      let sat = 0;
      for (const x of t) if (x > 0.98) sat++;
      expect(sat / t.length).toBeLessThan(0.005);
      // Structure at the coil scale: the near-coil region spans several
      // distinct deciles of the ramp instead of rendering as one flat color.
      const deciles = new Set(nearCoil.map((i) => Math.min(9, Math.floor(t[i]! * 10))));
      expect(deciles.size).toBeGreaterThanOrEqual(4);
    }
  });

  it('compression maps the window edges correctly and preserves NaN holes', () => {
    const vmax = 1000;
    const vals = new Float64Array([vmax, vmax / INTENSITY_DECADES, 0, NaN, vmax * 10]);
    const t = compressIntensity(vals, vmax);
    expect(t[0]).toBeCloseTo(1, 6);
    expect(t[1]!).toBeGreaterThan(0.05); // floor of the window: dark but alive
    expect(t[1]!).toBeLessThan(0.2);
    expect(t[2]).toBe(0);
    expect(Number.isNaN(t[3]!)).toBe(true);
    expect(t[4]).toBe(1); // above-peak outliers clamp to the ramp top
  });

  it('signed compression is symmetric and bounded', () => {
    const t = compressSigned(new Float64Array([-500, -5, 0, 5, 500]), 500);
    expect(t[0]).toBeCloseTo(-1, 6);
    expect(t[4]).toBeCloseTo(1, 6);
    expect(t[2]).toBe(0);
    expect(t[1]!).toBeCloseTo(-t[3]!, 9);
  });
});
