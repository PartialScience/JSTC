/**
 * The phase colormap: Mathematica's ComplexPlot shading over (-pi, pi].
 */
import { describe, expect, it } from 'vitest';

import { phaseColor, phaseColorCss, phaseColorUnit, phaseStops } from './phaseColor';

describe('phaseColor', () => {
  it('hits the reference endpoints at the branch cut', () => {
    expect(phaseColor(-Math.PI + 1e-12)).toEqual([50, 188, 201]); // teal at -pi
    expect(phaseColor(Math.PI)).toEqual([85, 128, 239]); // periwinkle at +pi
  });

  it('interpolates smoothly between stops', () => {
    const stops = phaseStops();
    // Halfway between stop 0 and stop 1
    const phi = -Math.PI + (Math.PI / (stops.length - 1)) * 1 * 0.5 * 2;
    const c = phaseColor(-Math.PI + ((2 * Math.PI) / (stops.length - 1)) * 0.5);
    for (let k = 0; k < 3; k++) {
      const lo = Math.min(stops[0]![k]!, stops[1]![k]!);
      const hi = Math.max(stops[0]![k]!, stops[1]![k]!);
      expect(c[k]).toBeGreaterThanOrEqual(lo - 1);
      expect(c[k]).toBeLessThanOrEqual(hi + 1);
    }
    void phi;
  });

  it('wraps any real angle into the branch cut', () => {
    expect(phaseColor(0)).toEqual(phaseColor(2 * Math.PI));
    expect(phaseColor(Math.PI / 3)).toEqual(phaseColor(Math.PI / 3 - 2 * Math.PI));
  });

  it('phase 0 sits mid-table (the warm band)', () => {
    const [r, g, b] = phaseColor(0);
    expect(r).toBeGreaterThan(200); // orange/red region
    expect(b).toBeLessThan(100);
    void g;
  });

  it('css and unit variants agree with the rgb values', () => {
    const [r, g, b] = phaseColor(1.0);
    expect(phaseColorCss(1.0)).toBe(`rgb(${r}, ${g}, ${b})`);
    const u = phaseColorUnit(1.0);
    expect(u[0]).toBeCloseTo(r / 255, 12);
  });
});
