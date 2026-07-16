/**
 * Point sampling of the operating field: given a world position, return the
 * scalar potential, the field magnitude, and the (real-part) field vector at
 * that point. The heatmap and arrow overlay work per grid node; a probe cursor
 * sits at an arbitrary position, so we bilinearly interpolate the same derived
 * quantities the visualisation uses — the readout always agrees with the colour
 * (and arrow) under the point.
 *
 * Two deliberate conventions, matching the existing overlays:
 *   - `intensity` is the COMPLEX magnitude (|E| / |B|), exactly what the
 *     intensity colour map shows.
 *   - the `(vr, vz)` vector is the INSTANTANEOUS real part (the field at phase
 *     0), exactly the direction `sampleArrows` draws. So |(vr, vz)| is the
 *     instantaneous magnitude and need not equal `intensity` under an AC drive.
 *
 * Points outside the grid, or whose interpolation stencil touches a masked
 * (conductor / off-domain) node, sample to null — an honest "—", the same holes
 * the heatmap leaves.
 */
import {
  bIntensityMap,
  complexGrads,
  eIntensityMap,
  idxOf,
  spacings,
  type FieldData,
} from './fieldMath';

export type FieldKind = 'E' | 'B';

export interface FieldSample {
  /** Signed instantaneous scalar: potential φ [V] (E) or vector potential
   *  A_φ [T·m] (B). null out of domain / over a conductor. */
  potential: number | null;
  /** Field magnitude (complex): |E| [V/m] or |B| [T]. null out of domain. */
  intensity: number | null;
  /** Instantaneous physical field components (radial, axial): E = (E_r, E_z)
   *  or B = (B_r, B_z). null out of domain. */
  vr: number | null;
  vz: number | null;
}

const NULL_SAMPLE: FieldSample = { potential: null, intensity: null, vr: null, vz: null };

/** Per-node instantaneous (real-part) field components, NaN where a central
 *  difference isn't available (edge or masked stencil). Mirrors `sampleArrows`
 *  but keeps every node and does not normalise. */
function vectorComponents(f: FieldData, kind: FieldKind): { vr: Float64Array; vz: Float64Array } {
  const { dr, dz } = spacings(f);
  const vr = new Float64Array(f.nr * f.nz).fill(NaN);
  const vz = new Float64Array(f.nr * f.nz).fill(NaN);
  for (let iz = 0; iz < f.nz; iz++) {
    for (let ir = 0; ir < f.nr; ir++) {
      const g = complexGrads(f, iz, ir, dr, dz);
      if (!g) continue;
      const c = idxOf(f.nr, iz, ir);
      if (kind === 'E') {
        vr[c] = -g.drRe;
        vz[c] = -g.dzRe;
      } else {
        const r = (f.rMin + ((f.rMax - f.rMin) * ir) / (f.nr - 1)) * f.unitScale;
        vr[c] = -g.dzRe;
        vz[c] = g.drRe + (r > 1e-12 ? f.real[c]! / r : 0);
      }
    }
  }
  return { vr, vz };
}

/** Bilinear interpolation of a per-node map at fractional indices, or null if
 *  any of the four surrounding nodes is non-finite (masked / edge). */
function bilinear(map: Float64Array, nr: number, nz: number, fr: number, fz: number): number | null {
  if (fr < 0 || fr > nr - 1 || fz < 0 || fz > nz - 1) return null;
  const ir0 = Math.floor(fr);
  const iz0 = Math.floor(fz);
  const ir1 = Math.min(nr - 1, ir0 + 1);
  const iz1 = Math.min(nz - 1, iz0 + 1);
  const tr = fr - ir0;
  const tz = fz - iz0;
  const v00 = map[iz0 * nr + ir0]!;
  const v10 = map[iz0 * nr + ir1]!;
  const v01 = map[iz1 * nr + ir0]!;
  const v11 = map[iz1 * nr + ir1]!;
  if (!(Number.isFinite(v00) && Number.isFinite(v10) && Number.isFinite(v01) && Number.isFinite(v11)))
    return null;
  const a = v00 * (1 - tr) + v10 * tr;
  const b = v01 * (1 - tr) + v11 * tr;
  return a * (1 - tz) + b * tz;
}

export interface FieldSampler {
  /** Sample at a WORLD position (SI metres). The physical radius is |x|, so a
   *  point mirrored to the left half samples the same field as its +x twin. */
  sampleAt(x: number, z: number): FieldSample;
}

/**
 * Precompute the derived node maps once (they are O(nr·nz)) and return a
 * sampler that interpolates them cheaply per point — so many cursors over one
 * field response share the same maps.
 */
export function buildFieldSampler(f: FieldData, kind: FieldKind): FieldSampler {
  // Potential is the real (instantaneous) part; masked nodes are holes.
  const pot = new Float64Array(f.nr * f.nz);
  for (let i = 0; i < pot.length; i++) pot[i] = f.mask[i] ? f.real[i]! : NaN;
  const intensity = kind === 'E' ? eIntensityMap(f) : bIntensityMap(f);
  const { vr, vz } = vectorComponents(f, kind);

  const spanR = f.rMax - f.rMin;
  const spanZ = f.zMax - f.zMin;

  return {
    sampleAt(x, z) {
      const r = Math.abs(x);
      const fr = spanR === 0 ? 0 : ((r - f.rMin) / spanR) * (f.nr - 1);
      const fz = spanZ === 0 ? 0 : ((z - f.zMin) / spanZ) * (f.nz - 1);
      if (fr < 0 || fr > f.nr - 1 || fz < 0 || fz > f.nz - 1) return NULL_SAMPLE;
      return {
        potential: bilinear(pot, f.nr, f.nz, fr, fz),
        intensity: bilinear(intensity, f.nr, f.nz, fr, fz),
        vr: bilinear(vr, f.nr, f.nz, fr, fz),
        vz: bilinear(vz, f.nr, f.nz, fr, fz),
      };
    },
  };
}
