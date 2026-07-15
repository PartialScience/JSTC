import { describe, expect, it } from 'vitest';

import {
  DEFAULT_INPUT_UNIT,
  defaultUnitPrefs,
  formatInput,
  fromBase,
  normalizeUnitPrefs,
  outputParts,
  outputUnitChoices,
  parseQuantity,
  resolveOutputPref,
  unitSymbol,
} from './units';

describe('parseQuantity', () => {
  it('interprets a bare number in the current unit', () => {
    const r = parseQuantity('10', 'length', 'in');
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.value).toBeCloseTo(0.254, 9); // 10 in → m
      expect(r.unit).toBe('in');
    }
  });

  it('parses a typed unit suffix and switches the field unit', () => {
    const r = parseQuantity('120mm', 'length', 'in');
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.value).toBeCloseTo(0.12, 9);
      expect(r.unit).toBe('mm');
    }
  });

  it('parses capacitance with an SI prefix', () => {
    const r = parseQuantity('18.8 nF', 'capacitance', 'nF');
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.value).toBeCloseTo(1.88e-8, 12);
  });

  it('accepts the µ sign for micro', () => {
    const r = parseQuantity('0.5µF', 'capacitance', 'nF');
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.value).toBeCloseTo(5e-7, 12);
  });

  it('rejects an unrecognised unit', () => {
    const r = parseQuantity('10 blah', 'length', 'in');
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.error).toBe('invalid unit');
  });

  it('rejects a wrong-dimension unit', () => {
    const r = parseQuantity('10 F', 'length', 'in');
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.error).toMatch(/expected a length/);
  });

  it('flags an empty entry', () => {
    expect(parseQuantity('', 'length', 'in').ok).toBe(false);
  });
});

describe('fromBase / formatInput', () => {
  it('converts SI to a display unit', () => {
    expect(fromBase(0.0254, 'in', 'length')).toBeCloseTo(1, 9);
  });

  it('formats without float noise', () => {
    expect(formatInput(0.0254, 'in', 'length')).toBe('1');
    expect(formatInput(1.88e-8, 'nF', 'capacitance')).toBe('18.8');
  });
});

describe('outputParts', () => {
  it('auto SI uses an engineering prefix', () => {
    expect(outputParts(1.88e-8, 'capacitance', 'auto')).toEqual({ value: '18.8', unit: 'nF' });
    expect(outputParts(150000, 'frequency', 'auto')).toEqual({ value: '150', unit: 'kHz' });
  });

  it('imperial length picks in / ft / mil by magnitude', () => {
    expect(outputParts(0.3048, 'length', 'imperial').unit).toBe('ft'); // 1 ft
    expect(outputParts(0.0254, 'length', 'imperial').unit).toBe('in'); // 1 in
    expect(outputParts(0.0000254, 'length', 'imperial').unit).toBe('mil'); // 1 mil
  });

  it('imperial mass uses pounds', () => {
    expect(outputParts(0.45359237, 'mass', 'imperial')).toEqual({ value: '1', unit: 'lb' });
  });

  it('pins a specific unit', () => {
    expect(outputParts(1.88e-8, 'capacitance', 'pF')).toEqual({ value: '18800', unit: 'pF' });
  });

  it('shows a dash but keeps the unit for a non-finite value', () => {
    expect(outputParts(NaN, 'inductance', 'auto').value).toBe('—');
  });
});

describe('unit choices & per-value resolution', () => {
  it('offers Imperial only for kinds that have an imperial form', () => {
    expect(outputUnitChoices('length').some((c) => c.value === 'imperial')).toBe(true);
    expect(outputUnitChoices('capacitance').some((c) => c.value === 'imperial')).toBe(false);
  });

  it('a per-value pin overrides the system baseline', () => {
    const prefs = { ...defaultUnitPrefs(), outputs: { 'Secondary.Ces (shunt C)': 'pF' } };
    expect(resolveOutputPref(prefs, 'Secondary.Ces (shunt C)', 'capacitance')).toBe('pF');
    // A different value of the same kind is unaffected (independent per value).
    expect(resolveOutputPref(prefs, 'Secondary.Cee (energy C)', 'capacitance')).toBe('auto');
  });

  it('imperial system re-units unpinned length/mass, leaves electrical on auto', () => {
    const prefs = { ...defaultUnitPrefs(), system: 'imperial' as const };
    expect(resolveOutputPref(prefs, 'Secondary.Winding length', 'length')).toBe('imperial');
    expect(resolveOutputPref(prefs, 'Secondary.Wire weight', 'mass')).toBe('imperial');
    expect(resolveOutputPref(prefs, 'Secondary.Ces (shunt C)', 'capacitance')).toBe('auto');
  });

  it('SI system leaves every unpinned value on auto', () => {
    const prefs = defaultUnitPrefs();
    expect(resolveOutputPref(prefs, 'Secondary.Winding length', 'length')).toBe('auto');
  });
});

describe('unitSymbol', () => {
  it('prettifies micro and ohm', () => {
    expect(unitSymbol('uF')).toBe('µF');
    expect(unitSymbol('kohm')).toBe('kΩ');
    expect(unitSymbol('mm')).toBe('mm');
  });
});

describe('normalizeUnitPrefs', () => {
  it('fills defaults for a missing or partial object', () => {
    expect(normalizeUnitPrefs(undefined)).toEqual(defaultUnitPrefs());
    const merged = normalizeUnitPrefs({ inputs: { 'sec-wire-dia': 'mm' } });
    expect(merged.inputs).toEqual({ 'sec-wire-dia': 'mm' });
    expect(merged.outputs).toEqual({});
    expect(merged.system).toBe('SI');
  });

  it('has inch and nF input defaults', () => {
    expect(DEFAULT_INPUT_UNIT.length).toBe('in');
    expect(DEFAULT_INPUT_UNIT.capacitance).toBe('nF');
  });
});
