/**
 * Pure helpers behind the matrix pane: turning a bundle into browsable
 * matrices, formatting cells, the heat-map color scale, and CSV export. Kept
 * out of the component file so both stay fast-refresh friendly and the logic
 * is unit-testable in isolation.
 *
 * The matrix bundle carries the raw solver artifacts in geometric units (the
 * facade applies ε₀/μ₀/unit_scale later): the nodal capacitance matrix, the
 * segment inductance matrix, and — when a primary is present — the
 * primary↔secondary coupling vector and the per-tent topload charge vector.
 */
import type { MatrixBundle } from '../api/client';

/** One browsable matrix: a name, a units/shape caption, and its rows. Vectors
 *  are carried as single-column matrices so the grid renderer is uniform. */
export interface NamedMatrix {
  key: string;
  name: string;
  /** Short description of what the entries are (shown under the title). */
  caption: string;
  /** Column index labels, or null for a vector (no column header). */
  columns: number[] | null;
  rows: number[][];
}

/** Build the list of viewable matrices from a bundle, skipping any that are
 *  empty (the coupling vector is empty when the coil has no primary). */
export function matricesFromBundle(bundle: MatrixBundle): NamedMatrix[] {
  const out: NamedMatrix[] = [];
  const asColumn = (v: number[]): number[][] => v.map((x) => [x]);

  const cap = bundle.nodal_capacitance ?? [];
  if (cap.length > 0) {
    out.push({
      key: 'capacitance',
      name: 'Capacitance (nodal C)',
      caption: `${cap.length}×${cap[0]?.length ?? 0} · geometric units (÷ 2π·ε₀·unit_scale)`,
      columns: cap[0]?.map((_, j) => j) ?? [],
      rows: cap,
    });
  }

  const ind = bundle.inductance ?? [];
  if (ind.length > 0) {
    out.push({
      key: 'inductance',
      name: 'Inductance (segment L)',
      caption: `${ind.length}×${ind[0]?.length ?? 0} · geometric units (÷ μ₀·unit_scale)`,
      columns: ind[0]?.map((_, j) => j) ?? [],
      rows: ind,
    });
  }

  const coupling = bundle.coupling ?? [];
  if (coupling.length > 0) {
    out.push({
      key: 'coupling',
      name: 'Coupling (primary → secondary m)',
      caption: `length ${coupling.length} · geometric mutual-inductance vector`,
      columns: null,
      rows: asColumn(coupling),
    });
  }

  const charge = bundle.topload_charge ?? [];
  if (charge.length > 0) {
    out.push({
      key: 'topload_charge',
      name: 'Topload charge (per tent)',
      caption: `length ${charge.length} · geometric induced-charge vector`,
      columns: null,
      rows: asColumn(charge),
    });
  }

  return out;
}

/** Compact cell text: small/large magnitudes go exponential to stay narrow,
 *  the mid range keeps 3 significant figures. */
export function formatCell(v: number): string {
  if (!Number.isFinite(v)) return '—';
  if (v === 0) return '0';
  const a = Math.abs(v);
  return a < 1e-3 || a >= 1e4 ? v.toExponential(2) : v.toPrecision(3);
}

export interface ColorScale {
  /** true when the data spans zero, so the map is diverging (blue↔red). */
  diverging: boolean;
  min: number;
  max: number;
  /** Symmetric magnitude used to normalize a diverging map. */
  magnitude: number;
}

/** Choose a scale for a matrix: diverging (symmetric about 0) when the values
 *  straddle zero, otherwise a sequential ramp over [min, max]. */
export function colorScale(rows: number[][]): ColorScale {
  let min = Infinity;
  let max = -Infinity;
  for (const row of rows) {
    for (const v of row) {
      if (!Number.isFinite(v)) continue;
      if (v < min) min = v;
      if (v > max) max = v;
    }
  }
  if (!Number.isFinite(min) || !Number.isFinite(max)) {
    return { diverging: false, min: 0, max: 0, magnitude: 0 };
  }
  const diverging = min < 0 && max > 0;
  return { diverging, min, max, magnitude: Math.max(Math.abs(min), Math.abs(max)) };
}

type RGB = [number, number, number];

function lerp(a: RGB, b: RGB, t: number): RGB {
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
}

// Endpoints tuned to read on both light and dark card backgrounds: a muted
// blue for the low/negative end, a near-neutral center, and a warm red for the
// high/positive end.
const LOW: RGB = [37, 99, 235]; // blue
const MID: RGB = [148, 163, 184]; // slate-neutral
const HIGH: RGB = [220, 38, 38]; // red

/** Map a value to an `rgb()` string under a scale. Diverging maps blue→neutral
 *  →red about zero; sequential maps neutral→red across [min, max]. Returns null
 *  for non-finite values (rendered without a background). */
export function cellColor(v: number, scale: ColorScale): string | null {
  if (!Number.isFinite(v)) return null;
  let rgb: RGB;
  if (scale.diverging) {
    const t = scale.magnitude === 0 ? 0 : Math.max(-1, Math.min(1, v / scale.magnitude));
    rgb = t < 0 ? lerp(MID, LOW, -t) : lerp(MID, HIGH, t);
  } else {
    const span = scale.max - scale.min;
    const t = span === 0 ? 0 : (v - scale.min) / span;
    rgb = lerp(MID, HIGH, t);
  }
  return `rgb(${Math.round(rgb[0])}, ${Math.round(rgb[1])}, ${Math.round(rgb[2])})`;
}

/** Pick black or white text for contrast against a cell's rgb background
 *  (Rec. 601 luma). */
export function textColorFor(rgb: string | null): string {
  if (!rgb) return 'inherit';
  const m = rgb.match(/(\d+)/g);
  if (!m) return 'inherit';
  const [r, g, b] = m.map(Number) as [number, number, number];
  const luma = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luma > 0.6 ? '#0b1120' : '#f8fafc';
}

/** Serialize a matrix as CSV (row-major, full precision). */
export function matrixToCsv(m: NamedMatrix): string {
  const header = m.columns ? ['', ...m.columns].join(',') : null;
  const body = m.rows.map((row, i) => [i, ...row].join(','));
  return (header ? [header, ...body] : body).join('\n');
}
