/**
 * Cross-language contract: the TypeScript primary ring spacing must match the
 * Python solver's `PrimarySpec.ring_centers()` exactly — for every path kind
 * (line, arc, spline) and turn-profile kind (uniform, graded).
 *
 * Both sides are pinned to the SAME golden fixture, generated from the solver
 * (see api/tests/models/test_primary_ring_fixture.py). If the solver's spacing
 * changes, the Python test forces a fixture regen, which then fails this test
 * until the TypeScript path/turn evaluation is updated to match — neither
 * side drifts silently.
 */
import { describe, expect, it } from 'vitest';

import type { PathSchema, PrimarySchema, TurnProfileSchema } from '../api/client';
import { primaryRings } from './primaryRings';
import fixture from './__fixtures__/primaryRings.json';

interface RingCase {
  name: string;
  path: PathSchema;
  turn_fxn: TurnProfileSchema;
  ring_centers: [number, number][];
  ring_fractions: number[];
}

/** A minimal primary carrying only the fields `primaryRings` reads. */
function primaryFromCase(c: RingCase): PrimarySchema {
  return {
    path: c.path,
    turn_fxn: c.turn_fxn,
    cross_section: { kind: 'circular', diameter: 0.25 },
  } as PrimarySchema;
}

describe('primaryRings matches the solver fixture', () => {
  const cases = fixture.cases as unknown as RingCase[];

  it('covers every path and turn-profile kind', () => {
    const pathKinds = new Set(cases.map((c) => c.path.kind));
    const turnKinds = new Set(cases.map((c) => c.turn_fxn.kind));
    expect(pathKinds).toEqual(new Set(['line', 'arc', 'spline', 'piecewise']));
    expect(turnKinds).toEqual(new Set(['uniform', 'graded']));
  });

  it.each(cases)('$name', (c) => {
    const { centers, fractions } = primaryRings(primaryFromCase(c));
    expect(centers).toHaveLength(c.ring_centers.length);
    centers.forEach(([r, z], i) => {
      const [er, ez] = c.ring_centers[i]!;
      expect(r).toBeCloseTo(er, 9);
      expect(z).toBeCloseTo(ez, 9);
    });
    fractions.forEach((f, i) => {
      expect(f).toBeCloseTo(c.ring_fractions[i]!, 9);
    });
  });
});
