import { describe, expect, it } from 'vitest';

import { blankCoil, defaultCoil } from '../domain/coil';
import type { AnalysisResponse } from '../api/client';
import {
  CoilFileError,
  FILE_FORMAT,
  FILE_VERSION,
  parseSession,
  serializeSession,
} from './coilFile';

// A minimal analysis payload: only the shape the loader checks for (a
// `secondary` block and a `bundle`) needs to be present.
const analysis = {
  secondary: { resonant_frequency: 231000 },
  bundle: { geometry_fingerprint: 'fp', discretization_order: 30 },
} as unknown as AnalysisResponse;

describe('coil file — export/import round-trip', () => {
  it('round-trips a fresh session (coil + outputs)', () => {
    const coil = defaultCoil();
    const text = serializeSession({ coil, analysis, stale: false });

    const parsed = JSON.parse(text);
    expect(parsed.format).toBe(FILE_FORMAT);
    expect(parsed.version).toBe(FILE_VERSION);

    const loaded = parseSession(text);
    expect(loaded.coil).toEqual(coil);
    expect(loaded.analysis).toEqual(analysis);
    expect(loaded.stale).toBe(false);
    expect(loaded.warnings).toEqual([]);
  });

  it('preserves the stale flag', () => {
    const text = serializeSession({ coil: defaultCoil(), analysis, stale: true });
    expect(parseSession(text).stale).toBe(true);
  });

  it('keeps a session with no outputs (analysis null)', () => {
    const text = serializeSession({ coil: blankCoil(), analysis: null, stale: false });
    const loaded = parseSession(text);
    expect(loaded.analysis).toBeNull();
    expect(loaded.coil).toEqual(blankCoil());
  });
});

describe('coil file — lenient import', () => {
  it('never fails on missing fields; fills them from blank defaults', () => {
    // Only a partial secondary is present — everything else is absent.
    const text = JSON.stringify({
      format: FILE_FORMAT,
      version: 1,
      coil: { secondary: { wire_dia: 0.03 } },
    });
    const loaded = parseSession(text);
    const base = blankCoil();
    // The provided field survives...
    expect(loaded.coil.secondary.wire_dia).toBe(0.03);
    // ...and missing secondary fields are filled from the factory default.
    expect(loaded.coil.secondary.turn_fxn).toEqual(base.secondary.turn_fxn);
    // Missing top-level fields fall back to defaults, not undefined.
    expect(loaded.coil.r_max).toBe(base.r_max);
    expect(loaded.coil.unit_scale).toBe(base.unit_scale);
    expect(loaded.coil.discretization_order).toBe(base.discretization_order);
    expect(loaded.coil.primary).toBeNull();
    expect(loaded.coil.toploads).toEqual([]);
  });

  it('drops outputs that lack a matrix bundle rather than half-loading them', () => {
    const text = JSON.stringify({
      format: FILE_FORMAT,
      version: 1,
      coil: blankCoil(),
      analysis: { secondary: { resonant_frequency: 1 } }, // no bundle
    });
    expect(parseSession(text).analysis).toBeNull();
  });

  it('imports a bare coil document (no envelope)', () => {
    const text = JSON.stringify(defaultCoil());
    const loaded = parseSession(text);
    expect(loaded.coil.secondary).toEqual(defaultCoil().secondary);
    expect(loaded.analysis).toBeNull();
  });

  it('folds an imported coil onto the physical half-plane (r >= 0)', () => {
    const text = JSON.stringify({
      coil: { ...blankCoil(), secondary: { ...blankCoil().secondary, start: [-5, 10] } },
    });
    expect(parseSession(text).coil.secondary.start).toEqual([0, 10]);
  });

  it('warns but still loads a file from a newer format version', () => {
    const text = JSON.stringify({
      format: FILE_FORMAT,
      version: FILE_VERSION + 5,
      coil: blankCoil(),
    });
    const loaded = parseSession(text);
    expect(loaded.warnings.length).toBeGreaterThan(0);
    expect(loaded.coil).toEqual(blankCoil());
  });
});

describe('coil file — unrecognizable input', () => {
  it('throws on non-JSON', () => {
    expect(() => parseSession('not json at all')).toThrow(CoilFileError);
  });

  it('throws on JSON with no coil-shaped object', () => {
    expect(() => parseSession(JSON.stringify({ foo: 1, bar: 2 }))).toThrow(CoilFileError);
  });

  it('throws on a JSON array', () => {
    expect(() => parseSession(JSON.stringify([1, 2, 3]))).toThrow(CoilFileError);
  });
});
