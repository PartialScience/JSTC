/**
 * Client-side field math over the backend's complex grid.
 *
 * The API returns a complex scalar on a regular (r, z) grid, row-major
 * (z outer, r inner): for E it's the potential phi [V]; for B the azimuthal
 * vector potential A_phi [T*m]. Here we derive the quantities the viz shows:
 * the magnitude map, the field-intensity map (|E| = |grad phi|, |B| =
 * |curl(A_phi phi_hat)|), iso-contours, and a sparse normalized vector field.
 *
 * All derivatives use the grid spacing in METRES (world spacing * unit_scale)
 * so intensities come out in SI (V/m, T). Cells flagged out-of-domain in the
 * mask are NaN and propagate NaN into any derivative that touches them.
 */

import type { FieldResponse } from '../api/client';

export interface FieldData {
  nr: number;
  nz: number;
  /** Re/Im of the complex field, length nr*nz, row-major (z outer). */
  real: number[];
  imag: number[];
  mask: boolean[];
  rMin: number;
  rMax: number;
  zMin: number;
  zMax: number;
  /** Metres per world unit, for SI derivatives. */
  unitScale: number;
}

/** Adapt an API field response to the client-side grid view. */
export function fieldDataFromResponse(resp: FieldResponse): FieldData {
  return {
    nr: resp.nr,
    nz: resp.nz,
    real: resp.real,
    imag: resp.imag,
    mask: resp.mask,
    rMin: resp.r_min,
    rMax: resp.r_max,
    zMin: resp.z_min,
    zMax: resp.z_max,
    unitScale: resp.unit_scale,
  };
}

const idx = (nr: number, iz: number, ir: number) => iz * nr + ir;

/** Row-major flat index into an nr×nz grid (z outer, r inner). */
export const idxOf = idx;

/** Complex magnitude |field| per cell (NaN where masked). */
export function magnitudeMap(f: FieldData): Float64Array {
  const out = new Float64Array(f.nr * f.nz);
  for (let i = 0; i < out.length; i++) {
    out[i] = f.mask[i] ? Math.hypot(f.real[i]!, f.imag[i]!) : NaN;
  }
  return out;
}

/** Metre spacings of the grid (world spacing * unitScale). */
export function spacings(f: FieldData): { dr: number; dz: number } {
  return {
    dr: ((f.rMax - f.rMin) / (f.nr - 1)) * f.unitScale,
    dz: ((f.zMax - f.zMin) / (f.nz - 1)) * f.unitScale,
  };
}

/** Central-difference complex partial derivatives at (iz, ir). Returns the
 *  four scalars d/dr and d/dz of the real and imaginary parts, or null if
 *  any needed neighbor is out of range or masked. */
export function complexGrads(
  f: FieldData,
  iz: number,
  ir: number,
  dr: number,
  dz: number,
): { drRe: number; drIm: number; dzRe: number; dzIm: number } | null {
  if (ir <= 0 || ir >= f.nr - 1 || iz <= 0 || iz >= f.nz - 1) return null;
  const c = idx(f.nr, iz, ir);
  const e = idx(f.nr, iz, ir + 1);
  const w = idx(f.nr, iz, ir - 1);
  const n = idx(f.nr, iz + 1, ir);
  const s = idx(f.nr, iz - 1, ir);
  if (!(f.mask[c] && f.mask[e] && f.mask[w] && f.mask[n] && f.mask[s])) return null;
  return {
    drRe: (f.real[e]! - f.real[w]!) / (2 * dr),
    drIm: (f.imag[e]! - f.imag[w]!) / (2 * dr),
    dzRe: (f.real[n]! - f.real[s]!) / (2 * dz),
    dzIm: (f.imag[n]! - f.imag[s]!) / (2 * dz),
  };
}

/** |E| = |grad phi| [V/m] from a complex potential grid. */
export function eIntensityMap(f: FieldData): Float64Array {
  const { dr, dz } = spacings(f);
  const out = new Float64Array(f.nr * f.nz).fill(NaN);
  for (let iz = 0; iz < f.nz; iz++) {
    for (let ir = 0; ir < f.nr; ir++) {
      const g = complexGrads(f, iz, ir, dr, dz);
      if (!g) continue;
      // |E_r|^2 + |E_z|^2 with complex components.
      const er2 = g.drRe * g.drRe + g.drIm * g.drIm;
      const ez2 = g.dzRe * g.dzRe + g.dzIm * g.dzIm;
      out[idx(f.nr, iz, ir)] = Math.sqrt(er2 + ez2);
    }
  }
  return out;
}

/** |B| = |curl(A_phi phi_hat)| [T] from a complex A_phi grid.
 *  B_r = -dA/dz, B_z = (1/r) d(r A)/dr = dA/dr + A/r. */
export function bIntensityMap(f: FieldData): Float64Array {
  const { dr, dz } = spacings(f);
  const out = new Float64Array(f.nr * f.nz).fill(NaN);
  const rCoords = new Float64Array(f.nr);
  for (let ir = 0; ir < f.nr; ir++) {
    rCoords[ir] = (f.rMin + ((f.rMax - f.rMin) * ir) / (f.nr - 1)) * f.unitScale;
  }
  for (let iz = 0; iz < f.nz; iz++) {
    for (let ir = 0; ir < f.nr; ir++) {
      const g = complexGrads(f, iz, ir, dr, dz);
      if (!g) continue;
      const c = idx(f.nr, iz, ir);
      const r = rCoords[ir]!;
      // B_r = -dA/dz ; B_z = dA/dr + A/r  (A complex; near-axis r>0 here)
      const brRe = -g.dzRe;
      const brIm = -g.dzIm;
      const invr = r > 1e-12 ? 1 / r : 0;
      const bzRe = g.drRe + f.real[c]! * invr;
      const bzIm = g.drIm + f.imag[c]! * invr;
      out[c] = Math.sqrt(brRe * brRe + brIm * brIm + bzRe * bzRe + bzIm * bzIm);
    }
  }
  return out;
}

/** A robust color-scale max: a high percentile of the finite values, so a
 *  single hot cell near a conductor doesn't wash out the whole map. */
export function robustMax(values: Float64Array, percentile = 0.99): number {
  const finite: number[] = [];
  for (const v of values) if (Number.isFinite(v)) finite.push(v);
  if (finite.length === 0) return 1;
  finite.sort((a, b) => a - b);
  const i = Math.min(finite.length - 1, Math.floor(percentile * finite.length));
  return finite[i]! || 1;
}

export interface Segment {
  x1: number;
  z1: number;
  x2: number;
  z2: number;
}

/**
 * Marching squares over a scalar map, returning iso-line segments in WORLD
 * (r, z) coordinates. Cells touching NaN are skipped.
 */
export function contourSegments(
  values: Float64Array,
  f: FieldData,
  levels: number[],
): Segment[] {
  const segs: Segment[] = [];
  const worldR = (ir: number) => f.rMin + ((f.rMax - f.rMin) * ir) / (f.nr - 1);
  const worldZ = (iz: number) => f.zMin + ((f.zMax - f.zMin) * iz) / (f.nz - 1);

  for (const level of levels) {
    for (let iz = 0; iz < f.nz - 1; iz++) {
      for (let ir = 0; ir < f.nr - 1; ir++) {
        const v00 = values[idx(f.nr, iz, ir)]!;
        const v10 = values[idx(f.nr, iz, ir + 1)]!;
        const v11 = values[idx(f.nr, iz + 1, ir + 1)]!;
        const v01 = values[idx(f.nr, iz + 1, ir)]!;
        if (!(Number.isFinite(v00) && Number.isFinite(v10) && Number.isFinite(v11) && Number.isFinite(v01)))
          continue;

        // Interpolated crossing point on each edge, or null.
        const interp = (a: number, b: number, pa: [number, number], pb: [number, number]) => {
          if ((a > level) === (b > level)) return null;
          const t = (level - a) / (b - a);
          return [pa[0] + t * (pb[0] - pa[0]), pa[1] + t * (pb[1] - pa[1])] as [number, number];
        };
        const p00: [number, number] = [worldR(ir), worldZ(iz)];
        const p10: [number, number] = [worldR(ir + 1), worldZ(iz)];
        const p11: [number, number] = [worldR(ir + 1), worldZ(iz + 1)];
        const p01: [number, number] = [worldR(ir), worldZ(iz + 1)];
        const crossings = [
          interp(v00, v10, p00, p10), // bottom
          interp(v10, v11, p10, p11), // right
          interp(v11, v01, p11, p01), // top
          interp(v01, v00, p01, p00), // left
        ].filter((c): c is [number, number] => c !== null);
        // Connect crossings pairwise (two for the common cases).
        for (let k = 0; k + 1 < crossings.length; k += 2) {
          const a = crossings[k]!;
          const b = crossings[k + 1]!;
          segs.push({ x1: a[0], z1: a[1], x2: b[0], z2: b[1] });
        }
      }
    }
  }
  return segs;
}

export interface Arrow {
  /** World position and a unit direction (instantaneous field at phase 0). */
  x: number;
  z: number;
  dx: number;
  dz: number;
}

/**
 * A sparse grid of normalized field-direction arrows, using the real part
 * (the instantaneous field at t=0). `kind` selects E (-grad phi) or B
 * (curl A_phi). `step` samples every `step`-th cell.
 */
export function sampleArrows(f: FieldData, kind: 'E' | 'B', step: number): Arrow[] {
  const { dr, dz } = spacings(f);
  const arrows: Arrow[] = [];
  const worldR = (ir: number) => f.rMin + ((f.rMax - f.rMin) * ir) / (f.nr - 1);
  const worldZ = (iz: number) => f.zMin + ((f.zMax - f.zMin) * iz) / (f.nz - 1);
  for (let iz = step; iz < f.nz - step; iz += step) {
    for (let ir = step; ir < f.nr - step; ir += step) {
      const g = complexGrads(f, iz, ir, dr, dz);
      if (!g) continue;
      let vr: number;
      let vz: number;
      if (kind === 'E') {
        vr = -g.drRe;
        vz = -g.dzRe;
      } else {
        const c = idx(f.nr, iz, ir);
        const r = worldR(ir) * f.unitScale;
        vr = -g.dzRe;
        vz = g.drRe + (r > 1e-12 ? f.real[c]! / r : 0);
      }
      const mag = Math.hypot(vr, vz);
      if (mag < 1e-30) continue;
      arrows.push({ x: worldR(ir), z: worldZ(iz), dx: vr / mag, dz: vz / mag });
    }
  }
  return arrows;
}
