import { describe, expect, it } from 'vitest';

import type { FieldData } from './fieldMath';
import { buildFieldSampler } from './sampleField';

/**
 * A 5×5 grid over [0,4]×[0,4] metres carrying a linear potential φ = 2r + 3z
 * (imag 0). Then E = -∇φ = (-2, -3) everywhere and |E| = √13, so an interior
 * sample has an exact expected value. Central differences only exist on the
 * 3×3 interior, so we sample within it.
 */
function linearField(mask?: (ir: number, iz: number) => boolean): FieldData {
  const nr = 5;
  const nz = 5;
  const real: number[] = [];
  const imag: number[] = [];
  const m: boolean[] = [];
  for (let iz = 0; iz < nz; iz++) {
    for (let ir = 0; ir < nr; ir++) {
      real.push(2 * ir + 3 * iz);
      imag.push(0);
      m.push(mask ? mask(ir, iz) : true);
    }
  }
  return { nr, nz, real, imag, mask: m, rMin: 0, rMax: 4, zMin: 0, zMax: 4, unitScale: 1 };
}

describe('buildFieldSampler', () => {
  it('bilinearly samples potential, intensity and the field vector', () => {
    const s = buildFieldSampler(linearField(), 'E').sampleAt(2.5, 1.5);
    expect(s.potential).toBeCloseTo(2 * 2.5 + 3 * 1.5, 9); // 9.5
    expect(s.vr).toBeCloseTo(-2, 9);
    expect(s.vz).toBeCloseTo(-3, 9);
    expect(s.intensity).toBeCloseTo(Math.sqrt(13), 9);
  });

  it('uses |x| as the radius, so a mirrored point reads the same field', () => {
    const sampler = buildFieldSampler(linearField(), 'E');
    expect(sampler.sampleAt(-2.5, 1.5)).toEqual(sampler.sampleAt(2.5, 1.5));
  });

  it('returns nulls outside the grid', () => {
    const s = buildFieldSampler(linearField(), 'E').sampleAt(10, 10);
    expect(s).toEqual({ potential: null, intensity: null, vr: null, vz: null });
  });

  it('returns null potential when the interpolation stencil touches a masked node', () => {
    // Mask an interior node; a sample in a cell that includes it is a hole.
    const f = linearField((ir, iz) => !(ir === 2 && iz === 2));
    const s = buildFieldSampler(f, 'E').sampleAt(1.5, 1.5);
    expect(s.potential).toBeNull();
  });
});
