/**
 * Display + clipboard formatting for the cursor readouts. Two rules the user
 * asked for run through everything here:
 *   - On screen, 3 significant figures; on the clipboard, full precision. Every
 *     value therefore comes as { text, copy }.
 *   - Never show "0.000": the SI-prefix scaling in `eng` keeps the mantissa in
 *     1–999, so a small value re-scales (kV → V → mV → µV …) instead of
 *     collapsing to zeros. It only reads "0" when the value is genuinely below
 *     the smallest prefix (or exactly zero).
 *
 * Field quantities (V, V/m, T, T·m) aren't in the unit-preference system, so
 * they use `eng`/`engFull` directly — the same primitive the results table uses
 * for off-enum units like Ω. Lengths (the r, z coordinates) DO go through the
 * unit system, honouring the SI/Imperial choice like every other length.
 */
import type { FieldKind } from './sampleField';
import { eng, engFull } from '../ui/format';
import { fromBase, unitSymbol, type OutputUnitPref } from '../units/units';

/** A value formatted for display and (separately) for the clipboard. */
export interface Measure {
  /** Rounded, unit-suffixed, for the UI (e.g. "1.23 kV/m"). "—" when absent. */
  text: string;
  /** Full precision, same unit, for copy (e.g. "1.23456 kV/m"). "" when absent. */
  copy: string;
}

const EMPTY: Measure = { text: '—', copy: '' };

const sig3 = (v: number): string => String(Number(v.toPrecision(3)));
const full = (v: number): string => String(Number(v.toPrecision(12)));

/** Format a field quantity (potential, |E|, a vector component, …) in `unit`. */
export function measure(si: number | null | undefined, unit: string): Measure {
  if (si == null || !Number.isFinite(si)) return EMPTY;
  return { text: eng(si, unit, 3), copy: engFull(si, unit) };
}

/** Format a length (an r or z coordinate) under the length unit preference,
 *  mirroring the app's output formatting so coordinates read like every other
 *  length. The SI/auto path re-scales the prefix (never "0.000 m"). */
export function measureLength(si: number | null | undefined, pref: OutputUnitPref): Measure {
  if (si == null || !Number.isFinite(si)) return EMPTY;
  if (pref === 'imperial') {
    const inches = si / 0.0254;
    const a = Math.abs(inches);
    const [value, unit] =
      a >= 12 ? [inches / 12, 'ft'] : a >= 0.1 || a === 0 ? [inches, 'in'] : [inches * 1000, 'mil'];
    return { text: `${sig3(value)} ${unit}`, copy: `${full(value)} ${unit}` };
  }
  if (pref !== 'auto') {
    const value = fromBase(si, pref, 'length');
    const unit = unitSymbol(pref);
    return { text: `${sig3(value)} ${unit}`, copy: `${full(value)} ${unit}` };
  }
  return { text: eng(si, 'm', 3), copy: engFull(si, 'm') };
}

/** Combine two measures into a parenthesised pair, e.g. an (r, z) position or a
 *  field vector's (radial, axial) components. Copy joins the two full-precision
 *  forms so a click yields the whole vector, not one component. */
export function pair(a: Measure, b: Measure): Measure {
  if (!a.copy || !b.copy) return EMPTY;
  return { text: `(${a.text}, ${b.text})`, copy: `${a.copy}, ${b.copy}` };
}

/** The one-line hover readout: "(r, z) = (…, …)". */
export function coordReadout(r: number, z: number, pref: OutputUnitPref): string {
  return `(r, z) = ${pair(measureLength(r, pref), measureLength(z, pref)).text}`;
}

/** Row labels and units for a field view, so the E and B panes read correctly
 *  (each pane shows the quantities of the field it displays). */
export interface FieldQuantityLabels {
  potentialLabel: string;
  potentialUnit: string;
  fieldLabel: string;
  vectorUnit: string;
  intensityUnit: string;
}

export function fieldQuantityLabels(kind: FieldKind): FieldQuantityLabels {
  return kind === 'E'
    ? {
        potentialLabel: 'Potential',
        potentialUnit: 'V',
        fieldLabel: 'E-field',
        vectorUnit: 'V/m',
        intensityUnit: 'V/m',
      }
    : {
        potentialLabel: 'Vector potential',
        potentialUnit: 'T·m',
        fieldLabel: 'B-field',
        vectorUnit: 'T',
        intensityUnit: 'T',
      };
}
