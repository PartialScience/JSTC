import { describe, expect, it } from 'vitest';

import { eng, hz } from './format';

describe('eng', () => {
  it('picks the right SI prefix', () => {
    expect(eng(231213, 'Hz')).toBe('231 kHz');
    expect(eng(2.79e-11, 'F')).toBe('27.9 pF');
    expect(eng(0.017, 'H')).toBe('17.0 mH');
    expect(eng(86.5e-6, 'H')).toBe('86.5 µH');
    expect(eng(280, 'Ω')).toBe('280 Ω');
  });

  it('handles zero and non-finite', () => {
    expect(eng(0, 'F')).toBe('0 F');
    expect(eng(Infinity, 'Ω')).toBe('— Ω');
  });

  it('hz helper', () => {
    expect(hz(225170)).toBe('225 kHz');
  });
});
