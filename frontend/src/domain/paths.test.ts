/**
 * Unit tests for the TS path evaluation layer. The heavy cross-language
 * correctness pin is the golden ring fixture (editor/primaryRings.test.ts);
 * these cover the local invariants: unit-speed parameterization, the arc
 * sign convention, turn-profile inversion, and normalizePath repairs.
 */
import { describe, expect, it } from 'vitest';

import {
  arcFromThreePoints,
  arcMidFromRadiusForm,
  evaluatePath,
  evaluateTurns,
  junctionBefore,
  pathEndpoints,
  normalizePath,
  pathControlPoints,
  translatePath,
  withControlPoint,
} from './paths';

const close = (a: number, b: number, tol = 1e-9) => Math.abs(a - b) <= tol;

describe('unit-speed parameterization', () => {
  const paths = [
    { kind: 'line' as const, start: [1, 2] as [number, number], end: [4, 6] as [number, number] },
    { kind: 'arc' as const, start: [2, 0] as [number, number], mid: [4.2, 1.6] as [number, number], end: [6, 2] as [number, number] },
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

describe('three-point arc', () => {
  it('passes through all three points, in order', () => {
    const p = evaluatePath({ kind: 'arc', start: [2, 0], mid: [4, 1.5], end: [6, 0] });
    const near = (q: [number, number]) => {
      let best = Infinity;
      for (let i = 0; i <= 400; i++) {
        const pt = p.pointAt((p.length * i) / 400);
        best = Math.min(best, Math.hypot(pt[0] - q[0], pt[1] - q[1]));
      }
      return best;
    };
    expect(p.pointAt(0)[0]).toBeCloseTo(2, 12);
    expect(p.pointAt(0)[1]).toBeCloseTo(0, 12);
    expect(near([4, 1.5])).toBeLessThan(1e-3);
    expect(p.pointAt(p.length)[0]).toBeCloseTo(6, 9);
  });

  it('the through point picks the bend direction', () => {
    const up = evaluatePath({ kind: 'arc', start: [0, 0], mid: [1, 0.4], end: [2, 0] });
    const down = evaluatePath({ kind: 'arc', start: [0, 0], mid: [1, -0.4], end: [2, 0] });
    // Bulge up => center below => clockwise => negative curvature
    expect(up.curvatureAt(0)).toBeLessThan(0);
    expect(down.curvatureAt(0)).toBeGreaterThan(0);
  });

  it('supports major arcs (sweep beyond a semicircle)', () => {
    // Points on the unit circle: start 0°, through 180°, end 270° -> 270° sweep
    const g = arcFromThreePoints([1, 0], [-1, 0], [0, -1]);
    expect(g.radius).toBeCloseTo(1, 12);
    expect(Math.abs(g.angleEnd - g.angleStart)).toBeCloseTo((3 * Math.PI) / 2, 9);
  });

  it('rejects collinear points', () => {
    expect(() => arcFromThreePoints([0, 0], [1, 1], [2, 2])).toThrow(/collinear/);
  });

  it('legacy radius-form arcs convert via their through point', () => {
    // Old form: minor arc, positive radius = center left of travel
    const mid = arcMidFromRadiusForm([0, 0], [2, 0], 5);
    const g = arcFromThreePoints([0, 0], mid, [2, 0]);
    expect(g.radius).toBeCloseTo(5, 9);
    // Same bend as the old convention: center on the left (+z), bulge below
    expect(mid[1]).toBeLessThan(0);
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
  it('drops consecutive duplicate spline points', () => {
    const fixed = normalizePath({
      kind: 'spline',
      points: [[0, 0], [1, 1], [1, 1], [2, 0]],
    });
    expect(fixed.kind === 'spline' && fixed.points).toEqual([[0, 0], [1, 1], [2, 0]]);
  });

  it('returns the identical object when nothing needs fixing', () => {
    const path = {
      kind: 'arc' as const,
      start: [0, 0] as [number, number],
      mid: [2, 1] as [number, number],
      end: [4, 0] as [number, number],
    };
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

describe('piecewise paths', () => {
  const chain = {
    kind: 'piecewise' as const,
    first: { kind: 'line' as const, start: [2, 0] as Point, end: [2, 5] as Point },
    rest: [
      { kind: 'arc-from' as const, end: [4, 7] as Point },
      { kind: 'line-from' as const, length: 2 },
      { kind: 'spline-from' as const, points: [[7, 8], [8, 6]] as Point[] },
    ],
  };
  type Point = [number, number];

  it('is tangent-continuous across every junction', () => {
    const p = evaluatePath(chain);
    // junction arclengths: accumulate piece lengths by probing tangents densely
    const n = 2000;
    for (let i = 1; i < n; i++) {
      const s = (p.length * i) / n;
      const a = p.tangentAt(s - p.length / (4 * n));
      const b = p.tangentAt(s + p.length / (4 * n));
      const dot = a[0] * b[0] + a[1] * b[1];
      expect(dot).toBeGreaterThan(0.99);
    }
  });

  it('control points are the stored absolute coordinates', () => {
    const pts = pathControlPoints(chain);
    // first: 2 points; arc-from: 1; line-from: 0; spline-from: 2
    expect(pts).toHaveLength(5);
    expect(pts[2]).toEqual([4, 7]);
    expect(pts[3]).toEqual([7, 8]);
  });

  it('withControlPoint edits the owning segment', () => {
    const moved = withControlPoint(chain, 2, [4.5, 7.5]);
    expect(moved.kind === 'piecewise' && moved.rest[0]).toEqual({
      kind: 'arc-from',
      end: [4.5, 7.5],
    });
  });

  it('translatePath moves stored points and leaves lengths alone', () => {
    const t = translatePath(chain, 1, -1);
    if (t.kind !== 'piecewise') throw new Error('kind changed');
    expect(t.first.kind === 'line' && t.first.start).toEqual([3, -1]);
    expect(t.rest[1]).toEqual({ kind: 'line-from', length: 2 });
    // Translation commutes with evaluation
    const p0 = evaluatePath(chain);
    const p1 = evaluatePath(t);
    const q0 = p0.pointAt(p0.length * 0.77);
    const q1 = p1.pointAt(p1.length * 0.77);
    expect(q1[0]).toBeCloseTo(q0[0] + 1, 9);
    expect(q1[1]).toBeCloseTo(q0[1] - 1, 9);
  });

  it('pathEndpoints evaluates a trailing line-from', () => {
    const lineEnd = {
      kind: 'piecewise' as const,
      first: { kind: 'line' as const, start: [1, 0] as Point, end: [1, 2] as Point },
      rest: [{ kind: 'line-from' as const, length: 3 }],
    };
    const { end } = pathEndpoints(lineEnd);
    expect(end[0]).toBeCloseTo(1, 12);
    expect(end[1]).toBeCloseTo(5, 12);
  });

  it('junctionBefore reports the inherited state and null when degenerate', () => {
    const j = junctionBefore(chain, 1);
    expect(j).not.toBeNull();
    // After the arc the tangent is unit length
    expect(Math.hypot(j!.tangent[0], j!.tangent[1])).toBeCloseTo(1, 9);
    const broken = {
      ...chain,
      first: { kind: 'line' as const, start: [2, 0] as Point, end: [2, 0] as Point },
    };
    expect(junctionBefore(broken, 1)).toBeNull();
  });

  it('degenerate arc-from (straight ahead) throws for render guards to catch', () => {
    const bad = {
      kind: 'piecewise' as const,
      first: { kind: 'line' as const, start: [1, 0] as Point, end: [1, 2] as Point },
      rest: [{ kind: 'arc-from' as const, end: [1, 5] as Point }],
    };
    expect(() => evaluatePath(bad)).toThrow(/line-from/);
  });
});
