/**
 * Unit handling for the editor. The store holds every physical value in SI
 * base units (metres, farads, henries, ohms, hertz, seconds, kilograms); this
 * module is the single place that converts between those base values and what
 * the user sees or types.
 *
 * Three jobs:
 *   1. Inputs  — parse free text like "10in" / "120 mm" / "18.8nF" into an SI
 *      value, rejecting an unrecognised or wrong-dimension unit.
 *   2. Outputs — format an SI value for display, either with an automatic SI
 *      engineering prefix (µF / pF / kHz…), an imperial unit (mil / in / ft,
 *      lb), or a specific pinned unit.
 *   3. Matrices — the same SI→unit conversion for the (converted) matrix cells.
 *
 * js-quantities does the parsing and conversion; we keep a curated unit list
 * per quantity so the UI only ever offers units that make sense.
 */
import Qty from 'js-quantities';

import { eng } from '../ui/format';

/** The physical quantities the UI attaches units to. Everything else (turns,
 *  Q, coupling k, aspect ratio, °, %) is dimensionless/bespoke and unit-less. */
export type QuantityKind =
  | 'length'
  | 'capacitance'
  | 'inductance'
  | 'resistance'
  | 'frequency'
  | 'time'
  | 'mass'
  | 'current';

/** Canonical SI base unit (js-quantities form) the store stores each kind in. */
const BASE: Record<QuantityKind, string> = {
  length: 'm',
  capacitance: 'F',
  inductance: 'H',
  resistance: 'ohm',
  frequency: 'Hz',
  time: 's',
  mass: 'kg',
  current: 'A',
};

/** The unit symbol eng() prefixes for the automatic-SI display of each kind.
 *  Mass uses grams as the base so the prefix lands as "g"/"kg" not "kkg". */
const ENG_SYMBOL: Record<QuantityKind, string> = {
  length: 'm',
  capacitance: 'F',
  inductance: 'H',
  resistance: 'Ω',
  frequency: 'Hz',
  time: 's',
  mass: 'g',
  current: 'A',
};

/** Units offered in the dropdowns / accepted as pinned units, per kind
 *  (js-quantities form; `u` = micro, `ohm` = Ω — see `unitSymbol`). */
export const UNIT_OPTIONS: Record<QuantityKind, string[]> = {
  length: ['m', 'cm', 'mm', 'um', 'in', 'ft', 'mil'],
  capacitance: ['F', 'mF', 'uF', 'nF', 'pF'],
  inductance: ['H', 'mH', 'uH', 'nH'],
  resistance: ['ohm', 'kohm', 'Mohm', 'mohm'],
  frequency: ['Hz', 'kHz', 'MHz'],
  time: ['s', 'ms', 'us', 'ns'],
  mass: ['kg', 'g', 'lb', 'oz'],
  current: ['A', 'mA', 'uA', 'kA'],
};

/** Kinds that have a meaningful imperial rendering (the rest have no imperial
 *  form, so Imperial mode leaves them on automatic SI). */
export const HAS_IMPERIAL: Partial<Record<QuantityKind, boolean>> = {
  length: true,
  mass: true,
};

const KIND_NOUN: Record<QuantityKind, string> = {
  length: 'a length',
  capacitance: 'a capacitance',
  inductance: 'an inductance',
  resistance: 'a resistance',
  frequency: 'a frequency',
  time: 'a time',
  mass: 'a mass',
  current: 'a current',
};

/** Default display unit for an *input* field of a given kind (used when the
 *  user has not pinned one by typing). Lengths default to inches (JavaTC
 *  heritage); tank capacitance overrides to nF at the call site. */
export const DEFAULT_INPUT_UNIT: Record<QuantityKind, string> = {
  length: 'in',
  capacitance: 'nF',
  inductance: 'uH',
  resistance: 'ohm',
  frequency: 'kHz',
  time: 'us',
  mass: 'g',
  current: 'A',
};

/** Pretty unit symbol for display: `u`→`µ`, `ohm`→`Ω` (so `uF`→`µF`,
 *  `kohm`→`kΩ`). Everything else is already display-ready. */
export function unitSymbol(unit: string): string {
  return unit.replace(/^u/, 'µ').replace(/ohm/i, 'Ω');
}

/** Normalise user text so js-quantities understands it: µ→u, Ω→ohm. */
function normalizeUnitText(text: string): string {
  return text.replace(/µ/g, 'u').replace(/Ω/g, 'ohm');
}

const BARE_NUMBER = /^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/;

export interface ParseOk {
  ok: true;
  /** The value in SI base units for the kind. */
  value: number;
  /** The unit the entry was in (js-quantities form) — the field's current unit
   *  for a bare number, or the unit the user typed. */
  unit: string;
}
export interface ParseErr {
  ok: false;
  error: string;
}
export type ParseResult = ParseOk | ParseErr;

/**
 * Parse a field entry for `kind`, where `currentUnit` is the unit a bare number
 * is interpreted in. A bare number stays in `currentUnit`; a number with a unit
 * suffix is parsed and, if dimensionally compatible, converted — its unit
 * becomes the field's new unit. Unrecognised or wrong-dimension units fail.
 */
export function parseQuantity(
  text: string,
  kind: QuantityKind,
  currentUnit: string,
): ParseResult {
  const trimmed = text.trim();
  if (trimmed === '') return { ok: false, error: 'enter a value' };
  const normalized = normalizeUnitText(trimmed);

  if (BARE_NUMBER.test(normalized)) {
    const n = Number(normalized);
    if (!Number.isFinite(n)) return { ok: false, error: 'invalid number' };
    return { ok: true, value: toBase(n, currentUnit, kind), unit: currentUnit };
  }

  let q: Qty;
  try {
    q = Qty(normalized);
  } catch {
    return { ok: false, error: 'invalid unit' };
  }
  if (!q.isCompatible(BASE[kind])) {
    return { ok: false, error: `expected ${KIND_NOUN[kind]}` };
  }
  return { ok: true, value: q.to(BASE[kind]).scalar, unit: q.units() };
}

/** Convert a scalar in `unit` to the kind's SI base value. */
function toBase(value: number, unit: string, kind: QuantityKind): number {
  if (value === 0) return 0;
  return Qty(value, unit).to(BASE[kind]).scalar;
}

/** Convert an SI base value to a scalar in `unit`. */
export function fromBase(si: number, unit: string, kind: QuantityKind): number {
  if (si === 0) return 0;
  return Qty(si, BASE[kind]).to(unit).scalar;
}

/** Compact number for an editable input: ~`sig` significant figures with
 *  trailing-zero and float-noise stripped (0.0254 not 0.025400000001). */
export function formatInput(si: number, unit: string, kind: QuantityKind, sig = 6): string {
  if (!Number.isFinite(si)) return '';
  const v = fromBase(si, unit, kind);
  if (v === 0) return '0';
  return String(Number(v.toPrecision(sig)));
}

// ---------------------------------------------------------------------------
// Output display
// ---------------------------------------------------------------------------

/** How an output kind is displayed: automatic SI prefix, imperial, or a
 *  specific pinned unit (a `UNIT_OPTIONS` string). */
export type OutputUnitPref = 'auto' | 'imperial' | string;

/** A formatted output split into its number and its (clickable) unit label. */
export interface DisplayParts {
  value: string;
  unit: string;
}

const sig3 = (v: number): string => String(Number(v.toPrecision(3)));

/** Split a "12.3 kΩ" style string into { value, unit } on the first space. */
function split(text: string): DisplayParts {
  const i = text.indexOf(' ');
  return i < 0 ? { value: text, unit: '' } : { value: text.slice(0, i), unit: text.slice(i + 1) };
}

function autoParts(si: number, kind: QuantityKind): DisplayParts {
  if (kind === 'mass') return split(eng(si * 1000, ENG_SYMBOL.mass));
  return split(eng(si, ENG_SYMBOL[kind]));
}

function imperialParts(si: number, kind: QuantityKind): DisplayParts {
  if (kind === 'length') {
    const inches = si / 0.0254;
    const a = Math.abs(inches);
    if (a >= 12) return { value: sig3(inches / 12), unit: 'ft' };
    if (a >= 0.1 || a === 0) return { value: sig3(inches), unit: 'in' };
    return { value: sig3(inches * 1000), unit: 'mil' };
  }
  if (kind === 'mass') {
    const lb = si / 0.45359237;
    if (Math.abs(lb) >= 1 || lb === 0) return { value: sig3(lb), unit: 'lb' };
    return { value: sig3(lb * 16), unit: 'oz' };
  }
  return autoParts(si, kind); // no imperial form → automatic SI
}

/** Format an SI value for output display under a unit preference, returning the
 *  number and unit separately so the UI can make the unit a click target. */
export function outputParts(si: number, kind: QuantityKind, pref: OutputUnitPref): DisplayParts {
  if (!Number.isFinite(si)) return { value: '—', unit: unitForPref(kind, pref) };
  if (pref === 'auto') return autoParts(si, kind);
  if (pref === 'imperial') return imperialParts(si, kind);
  return { value: sig3(fromBase(si, pref, kind)), unit: unitSymbol(pref) };
}

/** The unit label to show for a preference when there is no value (— case). */
function unitForPref(kind: QuantityKind, pref: OutputUnitPref): string {
  if (pref === 'auto') return ENG_SYMBOL[kind];
  if (pref === 'imperial') return HAS_IMPERIAL[kind] ? (kind === 'mass' ? 'lb' : 'in') : ENG_SYMBOL[kind];
  return unitSymbol(pref);
}

/** The choices offered when clicking an output unit: Auto, Imperial (where it
 *  applies), then the specific units. Value is the stored pref, label is shown. */
export function outputUnitChoices(kind: QuantityKind): { value: OutputUnitPref; label: string }[] {
  const choices: { value: OutputUnitPref; label: string }[] = [{ value: 'auto', label: 'Auto (SI)' }];
  if (HAS_IMPERIAL[kind]) choices.push({ value: 'imperial', label: 'Imperial' });
  for (const u of UNIT_OPTIONS[kind]) choices.push({ value: u, label: unitSymbol(u) });
  return choices;
}

// ---------------------------------------------------------------------------
// Unit preferences (persisted, round-tripped)
// ---------------------------------------------------------------------------

export type UnitSystem = 'SI' | 'imperial';

/** The whole-session unit preferences. All are cosmetic and survive
 *  import/export.
 *   - `inputs`: per-field display unit (keyed by a stable field id).
 *   - `outputs`: per-*value* display unit (keyed by a stable output-field id) —
 *     each result value is independently unit-able; absent = follow `system`.
 *   - `system`: the baseline the global SI / Imperial buttons set, used for any
 *     output value without its own pin.
 *   - `matrices`: per matrix key ('geometric' or a physical unit). */
export interface UnitPrefs {
  inputs: Record<string, string>;
  outputs: Record<string, OutputUnitPref>;
  system: UnitSystem;
  matrices: Record<string, string>;
}

export function defaultUnitPrefs(): UnitPrefs {
  return { inputs: {}, outputs: {}, system: 'SI', matrices: {} };
}

/** The display preference for one output value: its own pin if set, else the
 *  system baseline (Imperial only re-units kinds that have an imperial form). */
export function resolveOutputPref(
  prefs: UnitPrefs,
  fieldId: string,
  kind: QuantityKind,
): OutputUnitPref {
  const pinned = prefs.outputs[fieldId];
  if (pinned) return pinned;
  return prefs.system === 'imperial' && HAS_IMPERIAL[kind] ? 'imperial' : 'auto';
}

/** Merge a possibly-partial persisted prefs object over the defaults, so an old
 *  or hand-edited file (or a missing section) never leaves prefs undefined. */
export function normalizeUnitPrefs(raw: unknown): UnitPrefs {
  const base = defaultUnitPrefs();
  if (typeof raw !== 'object' || raw === null) return base;
  const r = raw as Partial<UnitPrefs>;
  return {
    inputs: isStringMap(r.inputs) ? { ...r.inputs } : base.inputs,
    outputs: isStringMap(r.outputs) ? { ...r.outputs } : base.outputs,
    system: r.system === 'imperial' ? 'imperial' : 'SI',
    matrices: isStringMap(r.matrices) ? { ...r.matrices } : base.matrices,
  };
}

function isStringMap(v: unknown): v is Record<string, string> {
  return (
    typeof v === 'object' &&
    v !== null &&
    !Array.isArray(v) &&
    Object.values(v).every((x) => typeof x === 'string')
  );
}
