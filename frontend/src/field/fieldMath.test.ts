import { describe, expect, it } from 'vitest';

import {
  contourSegments,
  eIntensityMap,
  magnitudeMap,
  referencePhase,
  robustMax,
  sampleArrows,
  type FieldData,
} from './fieldMath';

/** A field whose value at (iz, ir) is fn(r_world, z_world), real, unmasked. */
function ramp(
  nr: number,
  nz: number,
  fn: (r: number, z: number) => number,
  unitScale = 1,
): FieldData {
  const rMin = 0,
    rMax = 4,
    zMin = 0,
    zMax = 6;
  const real: number[] = [];
  const imag: number[] = [];
  const mask: boolean[] = [];
  for (let iz = 0; iz < nz; iz++) {
    for (let ir = 0; ir < nr; ir++) {
      const r = rMin + ((rMax - rMin) * ir) / (nr - 1);
      const z = zMin + ((zMax - zMin) * iz) / (nz - 1);
      real.push(fn(r, z));
      imag.push(0);
      mask.push(true);
    }
  }
  return { nr, nz, real, imag, mask, rMin, rMax, zMin, zMax, unitScale };
}

describe('magnitudeMap', () => {
  it('is the complex magnitude, NaN where masked', () => {
    const f = ramp(2, 2, () => 3);
    f.imag = [4, 4, 4, 4];
    f.mask = [true, false, true, true];
    const m = magnitudeMap(f);
    expect(m[0]).toBeCloseTo(5); // hypot(3,4)
    expect(Number.isNaN(m[1]!)).toBe(true);
  });
});

describe('eIntensityMap', () => {
  it('gives a constant |E| = slope/unitScale for a linear potential', () => {
    // phi = 2*r  ->  |grad phi| = 2 per world unit = 2/unitScale per metre.
    const unitScale = 0.5;
    const f = ramp(6, 6, (r) => 2 * r, unitScale);
    const e = eIntensityMap(f);
    // Interior cells (edges are NaN by central-difference).
    expect(e[6 * 2 + 2]!).toBeCloseTo(2 / unitScale, 6);
  });

  it('respects the z-direction gradient', () => {
    const f = ramp(6, 6, (_r, z) => 3 * z, 1);
    const e = eIntensityMap(f);
    expect(e[6 * 3 + 3]!).toBeCloseTo(3, 6);
  });
});

describe('contourSegments', () => {
  it('iso-lines of phi = z are horizontal at the level', () => {
    const f = ramp(8, 8, (_r, z) => z);
    const phi = new Float64Array(f.real);
    const segs = contourSegments(phi, f, [3]);
    expect(segs.length).toBeGreaterThan(0);
    for (const s of segs) {
      expect(s.z1).toBeCloseTo(3, 6);
      expect(s.z2).toBeCloseTo(3, 6);
    }
  });

  it('skips cells that touch NaN', () => {
    const f = ramp(4, 4, (_r, z) => z);
    const phi = new Float64Array(f.real);
    phi[5] = NaN;
    // Still returns finite segments elsewhere, none NaN.
    for (const s of contourSegments(phi, f, [2])) {
      expect(Number.isFinite(s.x1) && Number.isFinite(s.z1)).toBe(true);
    }
  });
});

describe('sampleArrows', () => {
  it('E arrows point down -z for phi = z (E = -grad phi)', () => {
    const f = ramp(10, 10, (_r, z) => z);
    const arrows = sampleArrows(f, 'E', 3);
    expect(arrows.length).toBeGreaterThan(0);
    for (const a of arrows) {
      expect(a.dz).toBeCloseTo(-1, 6);
      expect(Math.abs(a.dx)).toBeLessThan(1e-6);
      expect(Math.hypot(a.dx, a.dz)).toBeCloseTo(1, 6); // normalized
    }
  });
});

describe('referencePhase (display phase)', () => {
  it('is the identity for a purely real field', () => {
    const p = referencePhase(ramp(5, 5, (_r, z) => z));
    expect(p.cos).toBeCloseTo(1, 12);
    expect(p.sin).toBeCloseTo(0, 12);
  });

  it('recovers the physical field direction from a purely imaginary field', () => {
    // φ = i·z: every bit of the field is in the imaginary part. The display
    // phase must rotate it back so E = -∇φ points down (-z), exactly like φ = z
    // — proving direction is phase-reference-independent, not "phase 0".
    const nr = 10;
    const nz = 10;
    const real: number[] = [];
    const imag: number[] = [];
    const mask: boolean[] = [];
    for (let iz = 0; iz < nz; iz++) {
      for (let ir = 0; ir < nr; ir++) {
        real.push(0);
        imag.push((6 * iz) / (nz - 1));
        mask.push(true);
      }
    }
    const f: FieldData = { nr, nz, real, imag, mask, rMin: 0, rMax: 4, zMin: 0, zMax: 6, unitScale: 1 };
    const arrows = sampleArrows(f, 'E', 3);
    expect(arrows.length).toBeGreaterThan(0);
    for (const a of arrows) {
      expect(a.dz).toBeCloseTo(-1, 6);
      expect(Math.abs(a.dx)).toBeLessThan(1e-6);
    }
  });
});

describe('robustMax', () => {
  it('ignores NaN and picks a high percentile', () => {
    const v = new Float64Array([1, 2, 3, 4, 100, NaN]);
    const m = robustMax(v, 0.5);
    expect(m).toBeGreaterThanOrEqual(2);
    expect(m).toBeLessThan(100);
  });
});
