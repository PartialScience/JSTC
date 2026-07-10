/**
 * Cross-language contract: the TypeScript primary ring spacing must match the
 * Python solver's `PrimarySpec.ring_centers()` exactly.
 *
 * Both sides are pinned to the SAME golden fixture, generated from the solver
 * (see api/tests/models/test_primary_ring_fixture.py). If the solver's spacing
 * changes, the Python test forces a fixture regen, which then fails this test
 * until `primaryRingCenters` is updated to match — neither side drifts silently.
 */
import { describe, expect, it } from 'vitest';

import type { PrimarySchema } from '../api/client';
import { primaryRingCenters } from './primaryRings';
import fixture from './__fixtures__/primaryRings.json';

interface RingCase {
  name: string;
  start: [number, number];
  end: [number, number];
  total_turns: number;
  t_min?: number;
  t_max?: number;
  ring_centers: [number, number][];
}

/** A minimal primary carrying only the fields `primaryRingCenters` reads. */
function primaryFromCase(c: RingCase): PrimarySchema {
  return {
    start: c.start,
    end: c.end,
    turn_fxn: {
      kind: 'uniform',
      total_turns: c.total_turns,
      t_min: c.t_min ?? 0,
      t_max: c.t_max ?? 1,
    },
    cross_section: { kind: 'circular', diameter: 0.25 },
  } as PrimarySchema;
}

describe('primaryRingCenters matches the solver fixture', () => {
  const cases = fixture.cases as RingCase[];

  it('covers every fixture case', () => {
    expect(cases.length).toBeGreaterThan(0);
  });

  it.each(cases)('$name', (c) => {
    const centers = primaryRingCenters(primaryFromCase(c));
    expect(centers).toHaveLength(c.ring_centers.length);
    centers.forEach(([r, z], i) => {
      const [er, ez] = c.ring_centers[i]!;
      expect(r).toBeCloseTo(er, 9);
      expect(z).toBeCloseTo(ez, 9);
    });
  });
});
