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
