import { describe, expect, it } from 'vitest';

import { measure, measureLength, pair } from './fieldFormat';

describe('measure', () => {
  it('shows 3 significant figures but copies full precision', () => {
    const m = measure(12345.678, 'V/m');
    expect(m.text).toBe('12.3 kV/m');
    expect(m.copy).toBe('12.345678 kV/m');
  });

  it('rescales the SI prefix instead of collapsing to 0.000', () => {
    // 0.00047 V would round to "0.000 V"; the prefix pushes it to µV.
    expect(measure(0.00047, 'V').text).toBe('470 µV');
    expect(measure(2.3e-9, 'V').text).toBe('2.30 nV');
  });

  it('renders an em dash for a missing value', () => {
    expect(measure(null, 'V')).toEqual({ text: '—', copy: '' });
    expect(measure(undefined, 'V').text).toBe('—');
  });
});

describe('pair', () => {
  it('joins two measures; copy carries both full-precision components', () => {
    const p = pair(measure(1200, 'V/m'), measure(-3400, 'V/m'));
    expect(p.text).toBe('(1.20 kV/m, -3.40 kV/m)');
    expect(p.copy).toBe('1.2 kV/m, -3.4 kV/m');
  });

  it('is a dash when either component is missing', () => {
    expect(pair(measure(1, 'V/m'), measure(null, 'V/m')).text).toBe('—');
  });
});

describe('measureLength', () => {
  it('formats SI lengths with a rescaled prefix (auto)', () => {
    const m = measureLength(0.0123, 'auto');
    expect(m.text).toBe('12.3 mm');
    expect(m.copy).toBe('12.3 mm');
  });

  it('honours a pinned unit', () => {
    expect(measureLength(0.0254, 'mm').text).toBe('25.4 mm');
  });

  it('dashes a missing coordinate', () => {
    expect(measureLength(null, 'auto').text).toBe('—');
  });
});
