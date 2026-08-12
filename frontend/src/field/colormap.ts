/**
 * Perceptual colormaps for the field heatmap, and rasterization of a scalar
 * grid to an ImageData (drawn as an image behind the geometry).
 *
 * Two ramps: 'intensity' (dark -> hot, an inferno-like ramp) for field
 * strength, and 'potential' (diverging blue-white-red) for signed potential.
 * NaN cells are transparent so conductors / off-domain read as holes.
 */
import type { FieldData } from './fieldMath';

export type Colormap = 'intensity' | 'potential';

type RGB = [number, number, number];

// Compact control points; we linearly interpolate between them.
const INFERNO: RGB[] = [
  [0, 0, 4],
  [40, 11, 84],
  [101, 21, 110],
  [159, 42, 99],
  [212, 72, 66],
  [245, 125, 21],
  [250, 193, 39],
  [252, 255, 164],
];

const DIVERGING: RGB[] = [
  [33, 102, 172],
  [103, 169, 207],
  [209, 229, 240],
  [247, 247, 247],
  [253, 219, 199],
  [239, 138, 98],
  [178, 24, 43],
];

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function sample(ramp: RGB[], t: number): RGB {
  const x = Math.min(1, Math.max(0, t)) * (ramp.length - 1);
  const i = Math.floor(x);
  const f = x - i;
  const c0 = ramp[i]!;
  const c1 = ramp[Math.min(ramp.length - 1, i + 1)]!;
  return [lerp(c0[0], c1[0], f), lerp(c0[1], c1[1], f), lerp(c0[2], c1[2], f)];
}

/** Map an intensity in [0, vmax] to an inferno color. */
export function intensityColor(value: number, vmax: number): RGB {
  return sample(INFERNO, vmax > 0 ? value / vmax : 0);
}

/** Map a signed value in [-vmax, vmax] to a diverging color. */
export function divergingColor(value: number, vmax: number): RGB {
  const t = vmax > 0 ? 0.5 + value / (2 * vmax) : 0.5;
  return sample(DIVERGING, t);
}

/** Decades of |field| the intensity ramp spans: values below vmax/DR read as
 *  ~black, vmax reads as the ramp top, and the decades between share the ramp
 *  evenly (log). Physical fields fall off over decades (|E| ~ 1/d² near a
 *  conductor), so a linear ramp can never show near-surface structure and
 *  far-field shape at once — this is what does. */
export const INTENSITY_DECADES = 1000;
/** Softer window for the signed potential (it falls off ~1/d). */
export const POTENTIAL_DECADES = 100;

/** Log-compress an unsigned field map into [0, 1] for the intensity ramp:
 *  t = log(1 + v/floor)/log(1 + DR) with floor = vmax/DR. NaN passes through
 *  (transparent holes). Together with a domain-invariant vmax this makes the
 *  display independent of how much empty far-field the domain contains. */
export function compressIntensity(
  values: Float64Array,
  vmax: number,
  decades = INTENSITY_DECADES,
): Float64Array {
  const out = new Float64Array(values.length).fill(NaN);
  if (!(vmax > 0)) return out;
  const floor = vmax / decades;
  const denom = Math.log1p(decades);
  for (let i = 0; i < values.length; i++) {
    const v = values[i]!;
    if (!Number.isFinite(v)) continue;
    out[i] = Math.min(Math.log1p(Math.max(v, 0) / floor) / denom, 1);
  }
  return out;
}

/** asinh-compress a SIGNED map into [-1, 1] for the diverging ramp (linear
 *  near zero, logarithmic in the tails, symmetric). */
export function compressSigned(
  values: Float64Array,
  vmax: number,
  decades = POTENTIAL_DECADES,
): Float64Array {
  const out = new Float64Array(values.length).fill(NaN);
  if (!(vmax > 0)) return out;
  const s0 = vmax / decades;
  const denom = Math.asinh(decades);
  for (let i = 0; i < values.length; i++) {
    const v = values[i]!;
    if (!Number.isFinite(v)) continue;
    out[i] = Math.max(-1, Math.min(1, Math.asinh(v / s0) / denom));
  }
  return out;
}

/**
 * Rasterize a scalar map to an ImageData sized (nr x nz). The image is
 * y-flipped so that increasing z is UP in world space (row 0 of ImageData is
 * the top of the picture = z_max).
 */
export function rasterize(
  values: Float64Array,
  f: FieldData,
  colormap: Colormap,
  vmax: number,
): ImageData {
  const img = new ImageData(f.nr, f.nz);
  const data = img.data;
  for (let iz = 0; iz < f.nz; iz++) {
    // Flip vertically: world z increases upward, image y increases downward.
    const imgRow = f.nz - 1 - iz;
    for (let ir = 0; ir < f.nr; ir++) {
      const v = values[iz * f.nr + ir]!;
      const o = (imgRow * f.nr + ir) * 4;
      if (!Number.isFinite(v)) {
        data[o + 3] = 0; // transparent
        continue;
      }
      const [r, g, b] =
        colormap === 'potential' ? divergingColor(v, vmax) : intensityColor(v, vmax);
      data[o] = r;
      data[o + 1] = g;
      data[o + 2] = b;
      data[o + 3] = 235;
    }
  }
  return img;
}
