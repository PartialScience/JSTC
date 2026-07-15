/**
 * The on-disk coil/session file format, and lenient (never-throwing on
 * missing fields) import.
 *
 * A file is a small envelope around the coil the store already holds, plus
 * the last computed outputs so a reloaded coil shows results without paying
 * the FEM solve again:
 *
 *     {
 *       "format": "jstc-coil",
 *       "version": 1,
 *       "coil":     { ...CoilSchema... },      // the inputs
 *       "analysis": { ...AnalysisResponse... }, // the outputs (with the matrix bundle), or null
 *       "stale":    false                       // were the outputs stale vs. the coil when saved?
 *     }
 *
 * Backwards-compatibility contract: every file ever exported must import into
 * every future build. Two mechanisms uphold it:
 *
 *   1. Leniency. Import merges the payload over factory defaults, so a missing
 *      or partial field is filled in rather than failing. This absorbs every
 *      *additive* schema change (a new field with a default) for free — no
 *      version bump needed.
 *   2. Migrations. For genuinely *breaking* changes (a renamed field, changed
 *      units, a restructured shape), bump FILE_VERSION and append a migration
 *      to MIGRATIONS. Migrations are append-only: never edit or reorder an
 *      existing one, so an old file always has a path up to the current version.
 *
 * The only thing that ever fails is a file we can't recognize as a coil at all
 * (not JSON, or no coil-shaped object inside); missing *fields* never fail.
 */
import type {
  AnalysisResponse,
  GroundSchema,
  MatrixBundle,
  PrimarySchema,
  SecondarySchema,
  ToploadSchema,
} from '../api/client';
import { blankCoil, clampToRightHalfPlane, type Coil } from '../domain/coil';
import { normalizeUnitPrefs, type UnitPrefs } from '../units/units';

/** Magic string identifying our files; import rejects anything else. */
export const FILE_FORMAT = 'jstc-coil';
/** Current envelope version. Bump only on a breaking coil-schema change and
 *  add a matching entry to MIGRATIONS.
 *  v2: geometry stored in SI metres (was "coil units" scaled by unit_scale). */
export const FILE_VERSION = 2;
/** Extension used for exports. Import also accepts plain `.json`. */
export const FILE_EXTENSION = '.jstc';

/** A persisted editor session. */
export interface CoilFile {
  format: typeof FILE_FORMAT;
  version: number;
  coil: Coil;
  analysis: AnalysisResponse | null;
  stale: boolean;
  /** Display-unit preferences, so units don't reset across a round-trip. */
  unitPrefs: UnitPrefs;
}

/** The pieces the store needs to restore a session, plus any non-fatal notes
 *  to surface to the user (e.g. a newer file version). */
export interface LoadedSession {
  coil: Coil;
  analysis: AnalysisResponse | null;
  stale: boolean;
  unitPrefs: UnitPrefs;
  warnings: string[];
}

/** Thrown only when a file cannot be recognized as a coil at all. Missing
 *  fields within a recognizable file never throw. */
export class CoilFileError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'CoilFileError';
  }
}

// ---------------------------------------------------------------------------
// Export
// ---------------------------------------------------------------------------

/** Serialize the current session to the file format (pretty-printed so files
 *  stay human-readable and diffable). */
export function serializeSession(session: {
  coil: Coil;
  analysis: AnalysisResponse | null;
  stale: boolean;
  unitPrefs: UnitPrefs;
}): string {
  const file: CoilFile = {
    format: FILE_FORMAT,
    version: FILE_VERSION,
    coil: session.coil,
    analysis: session.analysis,
    stale: session.stale,
    unitPrefs: session.unitPrefs,
  };
  return JSON.stringify(file, null, 2);
}

// ---------------------------------------------------------------------------
// Migrations (append-only)
// ---------------------------------------------------------------------------

/** Default metres-per-unit for a v1 file that somehow lacks unit_scale — the
 *  demo/blank coils shipped in inches, so inches is the safe assumption. */
const V1_DEFAULT_UNIT_SCALE = 0.0254;

/* eslint-disable @typescript-eslint/no-explicit-any */
function scalePoint(p: unknown, s: number): unknown {
  return Array.isArray(p) && p.length === 2 && typeof p[0] === 'number' && typeof p[1] === 'number'
    ? [p[0] * s, p[1] * s]
    : p;
}

function scaleShape(shape: any, s: number): void {
  if (!shape || typeof shape !== 'object') return;
  if (shape.kind === 'circle') {
    if (Array.isArray(shape.center)) shape.center = scalePoint(shape.center, s);
    if (typeof shape.radius === 'number') shape.radius *= s;
  } else if (Array.isArray(shape.vertices)) {
    shape.vertices = shape.vertices.map((v: unknown) => scalePoint(v, s));
  }
}

/** Scale every length in a coil-like object by `s` (metres per old unit) and
 *  fix unit_scale at 1. Non-length fields (tank_capacitance, turns, order,
 *  materials, boundary conditions) are left untouched. */
function scalePointField(obj: any, key: string, s: number): void {
  if (Array.isArray(obj[key])) obj[key] = scalePoint(obj[key], s);
}

function scaleCoilLengths(coil: any, s: number): void {
  if (!coil || typeof coil !== 'object') return;
  if (typeof coil.r_max === 'number') coil.r_max *= s;
  if (typeof coil.z_max === 'number') coil.z_max *= s;
  const sec = coil.secondary;
  if (sec && typeof sec === 'object') {
    scalePointField(sec, 'start', s);
    scalePointField(sec, 'end', s);
    if (typeof sec.wire_dia === 'number') sec.wire_dia *= s;
  }
  const prim = coil.primary;
  if (prim && typeof prim === 'object') {
    scalePointField(prim, 'start', s);
    scalePointField(prim, 'end', s);
    if (typeof prim.lead_length === 'number') prim.lead_length *= s;
    if (typeof prim.lead_dia === 'number') prim.lead_dia *= s;
    const xs = prim.cross_section;
    if (xs && typeof xs === 'object') {
      if (typeof xs.diameter === 'number') xs.diameter *= s;
      if (typeof xs.width === 'number') xs.width *= s;
      if (typeof xs.height === 'number') xs.height *= s;
    }
  }
  for (const arr of [coil.toploads, coil.grounds]) {
    if (Array.isArray(arr)) for (const c of arr) if (c && typeof c === 'object') scaleShape(c.shape, s);
  }
  coil.unit_scale = 1;
}

/** v1 → v2: geometry moved from "coil units" (metres = value × unit_scale) to
 *  SI metres. Scale all lengths by the file's unit_scale. The cached bundle and
 *  outputs were geometric in the old units and no longer match the rescaled
 *  geometry, so drop them (mark stale) — a re-run recomputes them correctly. */
function migrateV1toV2(file: Record<string, unknown>): Record<string, unknown> {
  const coilHost: any = isObject(file.coil) ? file.coil : file;
  const s = typeof coilHost.unit_scale === 'number' ? coilHost.unit_scale : V1_DEFAULT_UNIT_SCALE;
  scaleCoilLengths(coilHost, s);
  if (isObject(file.coil)) {
    file.analysis = null;
    file.stale = true;
  }
  return file;
}
/* eslint-enable @typescript-eslint/no-explicit-any */

/** Migrations that bring an older envelope up to FILE_VERSION. Entry at index
 *  i migrates a v(i+1) file to v(i+2). Append only — never edit or reorder an
 *  existing entry, or old files stop importing. */
const MIGRATIONS: ((file: Record<string, unknown>) => Record<string, unknown>)[] = [migrateV1toV2];

function migrate(file: Record<string, unknown>, fromVersion: number): Record<string, unknown> {
  let out = file;
  for (let v = fromVersion; v < FILE_VERSION; v++) {
    const step = MIGRATIONS[v - 1];
    if (step) out = step(out);
  }
  return out;
}

// ---------------------------------------------------------------------------
// Import (lenient)
// ---------------------------------------------------------------------------

const isObject = (v: unknown): v is Record<string, unknown> =>
  typeof v === 'object' && v !== null && !Array.isArray(v);

const num = (v: unknown, fallback: number): number =>
  typeof v === 'number' && Number.isFinite(v) ? v : fallback;

/** Does this object look like a coil? Used to accept both a full session file
 *  and a bare coil JSON (so a hand-saved coil imports too). */
function looksLikeCoil(v: unknown): v is Record<string, unknown> {
  return (
    isObject(v) &&
    ('secondary' in v || 'r_max' in v || 'unit_scale' in v || 'discretization_order' in v)
  );
}

/** Merge a raw coil over blank defaults so every required field exists even
 *  when the file omits it, then fold onto the physical half-plane (r >= 0). */
function normalizeCoil(raw: Record<string, unknown>): Coil {
  const base = blankCoil();
  return clampToRightHalfPlane({
    // Merge the secondary so a partial one still has material/turns/wire_dia.
    secondary: isObject(raw.secondary)
      ? ({ ...base.secondary, ...(raw.secondary as object) } as SecondarySchema)
      : base.secondary,
    // Only install a primary if one is present; otherwise there is none.
    primary: isObject(raw.primary) ? (raw.primary as PrimarySchema) : null,
    toploads: Array.isArray(raw.toploads) ? (raw.toploads as ToploadSchema[]) : base.toploads,
    grounds: Array.isArray(raw.grounds) ? (raw.grounds as GroundSchema[]) : base.grounds,
    r_max: num(raw.r_max, base.r_max),
    z_max: num(raw.z_max, base.z_max),
    // Geometry is always metres now; the backend's length scale is fixed at 1
    // and no longer user-facing (migrations rescale any older, non-metre file).
    unit_scale: 1,
    discretization_order: num(raw.discretization_order, base.discretization_order),
    bc_bottom: (raw.bc_bottom as Coil['bc_bottom']) ?? base.bc_bottom,
    bc_top: (raw.bc_top as Coil['bc_top']) ?? base.bc_top,
    bc_right: (raw.bc_right as Coil['bc_right']) ?? base.bc_right,
  });
}

/** Keep the outputs only if they carry the shape the results panel reads. A
 *  bundle is required to reuse the matrices and drive the impedance/SPICE
 *  features, so drop outputs that lack one rather than half-load them. */
function extractAnalysis(raw: unknown): AnalysisResponse | null {
  if (!isObject(raw)) return null;
  if (!('secondary' in raw)) return null;
  if (!isObject(raw.bundle)) return null;
  return raw as unknown as AnalysisResponse;
}

/**
 * Parse a file's text into a session. Never throws on missing/partial fields —
 * absent inputs fall back to blank defaults and absent outputs simply don't
 * populate. Throws CoilFileError only when the text isn't a recognizable coil.
 */
export function parseSession(text: string): LoadedSession {
  let raw: unknown;
  try {
    raw = JSON.parse(text);
  } catch {
    throw new CoilFileError('This file is not valid JSON, so it could not be read as a JSTC coil.');
  }
  if (!isObject(raw)) {
    throw new CoilFileError('This file does not contain a JSTC coil.');
  }

  const warnings: string[] = [];
  const declaredVersion = typeof raw.version === 'number' ? raw.version : FILE_VERSION;
  if (declaredVersion > FILE_VERSION) {
    warnings.push(
      `This file was saved by a newer version of JSTC (format v${declaredVersion}); ` +
        'anything this build does not understand was skipped.',
    );
  }

  const file = migrate(raw, declaredVersion);

  // Accept a full session envelope ({ coil: ... }) or a bare coil document.
  const rawCoil = looksLikeCoil(file.coil) ? file.coil : looksLikeCoil(file) ? file : null;
  if (rawCoil === null) {
    throw new CoilFileError('This file does not contain a coil that JSTC can read.');
  }

  return {
    coil: normalizeCoil(rawCoil),
    analysis: extractAnalysis(file.analysis),
    stale: file.stale === true,
    unitPrefs: normalizeUnitPrefs(file.unitPrefs),
    warnings,
  };
}

/** The default filename for an export. */
export function exportFilename(): string {
  return `coil${FILE_EXTENSION}`;
}

// Re-export for callers that persist the bundle separately.
export type { MatrixBundle };
