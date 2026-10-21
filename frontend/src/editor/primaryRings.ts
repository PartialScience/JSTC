/**
 * Primary ring geometry — the editor/3-D view's copy of the solver's
 * `PrimarySpec.ring_centers()` / `ring_turn_fractions()`.
 *
 * The physics reduces the primary to one coaxial ring per turn, spaced at
 * the turn-space midpoints along the winding centerline (any path kind:
 * line, arc, spline) and weighted by the fractional final turn. That exact
 * spacing feeds the coupling vector, the primary self-inductance, and the
 * electrostatic grounded-ring solve, so the drawn rings must land in the
 * SAME places or the picture misrepresents what was solved. A shared golden
 * fixture (`__fixtures__/primaryRings.json`, generated from the Python
 * solver) pins the two implementations together — see
 * `primaryRings.test.ts` and the backend's `test_primary_ring_fixture.py`.
 */
import type { PrimarySchema } from '../api/client';
import type { Point } from '../domain/coil';
import { evaluatePath, evaluateTurns } from '../domain/paths';

export interface PrimaryRings {
  /** Centerline (r, z) of each turn's equivalent coaxial ring. */
  centers: Point[];
  /** Fraction of a full turn each ring represents (1 except possibly the
   *  final ring — the physics weights its flux linkage by this, and the
   *  viewer fades it accordingly). */
  fractions: number[];
}

/** Ring centers + turn fractions, identical to the solver's. */
export function primaryRings(primary: PrimarySchema): PrimaryRings {
  let path;
  try {
    path = evaluatePath(primary.path);
  } catch {
    return { centers: [], fractions: [] }; // transiently degenerate
  }
  const turns = evaluateTurns(primary.turn_fxn, path.length);
  const total = turns.totalTurns;
  if (!(total > 0)) return { centers: [], fractions: [] };

  const nRings = Math.ceil(total);
  const centers: Point[] = [];
  const fractions: number[] = [];
  for (let k = 0; k < nRings; k++) {
    const midTurn = (k + Math.min(k + 1, total)) / 2;
    centers.push(path.pointAt(turns.inverse(midTurn)));
    fractions.push(Math.min(k + 1, total) - k);
  }
  return { centers, fractions };
}

/** Centerline (r, z) of each primary turn's ring (see primaryRings). */
export function primaryRingCenters(primary: PrimarySchema): Point[] {
  return primaryRings(primary).centers;
}

/**
 * Half-extents (r, z) of the primary conductor's cross-section, i.e. how far
 * each ring's conductor reaches from its center in the (r, z) plane. Circular
 * wire is a disc of radius diameter/2; ribbon is a width×height rectangle.
 * Used to draw the ring cross-sections at the right size.
 */
export function primaryCrossSectionHalfExtent(primary: PrimarySchema): {
  r: number;
  z: number;
  circular: boolean;
} {
  const cs = primary.cross_section;
  if (cs.kind === 'circular') {
    const half = cs.diameter / 2;
    return { r: half, z: half, circular: true };
  }
  return { r: cs.width / 2, z: cs.height / 2, circular: false };
}
