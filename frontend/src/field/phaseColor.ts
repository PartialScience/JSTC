/**
 * Phase colormap for complex phasors: arg(z) in (-pi, pi] -> color.
 *
 * The gradient is sampled from Mathematica's ComplexPlot phase shading (the
 * reference Collin supplied), NOT a raw HSV hue sweep - the raw hue wheel
 * reads badly (muddy cyans, glaring pure primaries); this table carries
 * Mathematica's tuned lightness/saturation. Like the original, it is almost
 * but not exactly cyclic: -pi is teal and +pi periwinkle, with the small
 * seam at the branch cut rendered as-is.
 *
 * 33 RGB stops, evenly spaced over [-pi, pi], linearly interpolated.
 */

export type RGB = [number, number, number];

const PHASE_STOPS: RGB[] = [
  [50, 188, 201],
  [55, 192, 180],
  [56, 197, 155],
  [50, 202, 129],
  [53, 205, 108],
  [71, 206, 86],
  [84, 207, 60],
  [91, 208, 28],
  [129, 210, 15],
  [165, 212, 11],
  [191, 213, 8],
  [216, 209, 10],
  [228, 194, 21],
  [238, 182, 26],
  [248, 166, 32],
  [246, 142, 44],
  [243, 121, 52],
  [237, 92, 58],
  [232, 67, 69],
  [230, 58, 85],
  [226, 47, 104],
  [222, 32, 122],
  [217, 29, 140],
  [209, 28, 164],
  [200, 28, 187],
  [190, 33, 205],
  [174, 50, 216],
  [156, 61, 227],
  [139, 69, 236],
  [124, 84, 240],
  [112, 101, 240],
  [100, 113, 240],
  [85, 128, 239],
];

const TWO_SEG = PHASE_STOPS.length - 1;

/** The color for a phase angle (radians). Angles are wrapped into (-pi, pi]
 *  first, so any real angle is accepted. */
export function phaseColor(phi: number): RGB {
  const pi = Math.PI;
  // Wrap into (-pi, pi]
  let p = ((((phi + pi) % (2 * pi)) + 2 * pi) % (2 * pi)) - pi;
  if (p === -pi) p = pi;
  const t = ((p + pi) / (2 * pi)) * TWO_SEG;
  const i = Math.min(Math.floor(t), TWO_SEG - 1);
  const f = t - i;
  const a = PHASE_STOPS[i]!;
  const b = PHASE_STOPS[i + 1]!;
  return [
    Math.round(a[0] + f * (b[0] - a[0])),
    Math.round(a[1] + f * (b[1] - a[1])),
    Math.round(a[2] + f * (b[2] - a[2])),
  ];
}

/** CSS color string for a phase angle. */
export function phaseColorCss(phi: number): string {
  const [r, g, b] = phaseColor(phi);
  return `rgb(${r}, ${g}, ${b})`;
}

/** Normalized [0,1] RGB, for three.js vertex colors. */
export function phaseColorUnit(phi: number): RGB {
  const [r, g, b] = phaseColor(phi);
  return [r / 255, g / 255, b / 255];
}

/** The raw stop table (for rendering the colorbar gradient). */
export function phaseStops(): readonly RGB[] {
  return PHASE_STOPS;
}
