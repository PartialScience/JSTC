/**
 * Unit tests for the TS path evaluation layer. The heavy cross-language
 * correctness pin is the golden ring fixture (editor/primaryRings.test.ts);
 * these cover the local invariants: unit-speed parameterization, the arc
 * sign convention, turn-profile inversion, and normalizePath repairs.
 */
import { describe, expect, it } from 'vitest';

import {
  arcFromEndpoints,
  evaluatePath,
  evaluateTurns,
  normalizePath,
  pathControlPoints,
  translatePath,
  withControlPoint,
} from './paths';

const close = (a: number, b: number, tol = 1e-9) => Math.abs(a - b) <= tol;

describe('unit-speed parameterization', () => {
  const paths = [
    { kind: 'line' as const, start: [1, 2] as [number, number], end: [4, 6] as [number, number] },
    { kind: 'arc' as const, start: [2, 0] as [number, number], end: [6, 2] as [number, number], radius: 5 },
    {
      kind: 'spline' as const,
      points: [[0, 0], [1, 2], [3, 3], [5, 1]] as [number, number][],
    },
  ];

  it.each(paths)('$kind: |tangent| == 1 and chords sum to length', (path) => {
    const p = evaluatePath(path);
    const n = 200;
    let chordSum = 0;
    let prev = p.pointAt(0);
    for (let i = 1; i <= n; i++) {
      const s = (p.length * i) / n;
      const [tx, tz] = p.tangentAt(s);
      expect(close(Math.hypot(tx, tz), 1, 1e-7)).toBe(true);
      const pt = p.pointAt(s);
      chordSum += Math.hypot(pt[0] - prev[0], pt[1] - prev[1]);
      prev = pt;
    }
    expect(chordSum).toBeLessThanOrEqual(p.length * (1 + 1e-9));
    expect(chordSum).toBeGreaterThan(p.length * 0.999);
  });
});

describe('arc sign convention', () => {
  it('positive radius bends left of travel (CCW, positive curvature)', () => {
    const p = evaluatePath({ kind: 'arc', start: [0, 0], end: [2, 0], radius: 5 });
    expect(p.curvatureAt(0)).toBeCloseTo(0.2, 12);
    // Bulges away from the center (which sits on the left, +z): mid dips -z
    expect(p.pointAt(p.length / 2)[1]).toBeLessThan(0);
  });

  it('negative radius bends right (CW, negative curvature)', () => {
    const p = evaluatePath({ kind: 'arc', start: [0, 0], end: [2, 0], radius: -5 });
    expect(p.curvatureAt(0)).toBeCloseTo(-0.2, 12);
    expect(p.pointAt(p.length / 2)[1]).toBeGreaterThan(0);
  });

  it('interpolates the endpoints exactly', () => {
    const g = arcFromEndpoints([3, 1], [1, 4], -2.5);
    const a0 = [g.center[0] + g.radius * Math.cos(g.angleStart), g.center[1] + g.radius * Math.sin(g.angleStart)];
    expect(a0[0]).toBeCloseTo(3, 12);
    expect(a0[1]).toBeCloseTo(1, 12);
  });

  it('rejects a radius smaller than half the chord', () => {
    expect(() => arcFromEndpoints([0, 0], [4, 0], 1)).toThrow();
  });
});

describe('turn profiles', () => {
  it('uniform: inverse round-trips', () => {
    const t = evaluateTurns({ kind: 'uniform', total_turns: 50 }, 10);
    expect(t.at(t.inverse(23.5))).toBeCloseTo(23.5, 12);
  });

  it('graded: piecewise-linear with exact inversion', () => {
    const t = evaluateTurns(
      { kind: 'graded', points: [[0, 0], [0.2, 80], [1, 100]] },
      10,
    );
    expect(t.totalTurns).toBe(100);
    expect(t.at(2)).toBeCloseTo(80, 12); // u = 0.2 -> s = 2
    expect(t.inverse(80)).toBeCloseTo(2, 12);
    expect(t.at(6)).toBeCloseTo(90, 12); // halfway through the sparse band
  });
});

describe('normalizePath', () => {
  it('bumps an arc radius up to half the chord, preserving the sign', () => {
    const fixed = normalizePath({ kind: 'arc', start: [0, 0], end: [4, 0], radius: -1 });
    expect(fixed.kind === 'arc' && fixed.radius).toBeCloseTo(-2, 12);
  });

  it('drops consecutive duplicate spline points', () => {
    const fixed = normalizePath({
      kind: 'spline',
      points: [[0, 0], [1, 1], [1, 1], [2, 0]],
    });
    expect(fixed.kind === 'spline' && fixed.points).toEqual([[0, 0], [1, 1], [2, 0]]);
  });

  it('returns the identical object when nothing needs fixing', () => {
    const path = { kind: 'arc' as const, start: [0, 0] as [number, number], end: [4, 0] as [number, number], radius: 3 };
    expect(normalizePath(path)).toBe(path);
  });
});

describe('control-point helpers', () => {
  it('spline points are editable and translatable', () => {
    const path = { kind: 'spline' as const, points: [[0, 0], [1, 2], [3, 3]] as [number, number][] };
    expect(pathControlPoints(path)).toHaveLength(3);
    const moved = withControlPoint(path, 1, [1.5, 2.5]);
    expect(moved.kind === 'spline' && moved.points[1]).toEqual([1.5, 2.5]);
    const shifted = translatePath(path, 1, -1);
    expect(shifted.kind === 'spline' && shifted.points[0]).toEqual([1, -1]);
  });
});
