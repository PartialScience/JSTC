/**
 * Primary ring geometry — the editor/3-D view's copy of the solver's
 * `PrimarySpec.ring_centers()`.
 *
 * The physics reduces the primary to one coaxial ring per turn, spaced at the
 * turn-space midpoints along the winding centerline. That exact spacing feeds
 * the coupling vector, the primary self-inductance, and the electrostatic
 * grounded-ring solve, so the drawn rings must land in the SAME places or the
 * picture misrepresents what was solved. This function reproduces that
 * algorithm for the `LinearPrimarySpec` + `UniformTurnProfile` the editor can
 * build (a straight centerline, uniformly wound); a shared golden fixture
 * (`__fixtures__/primaryRings.json`, generated from the Python solver) pins the
 * two implementations together — see `primaryRings.test.ts` and the backend's
 * `test_primary_ring_fixture.py`.
 */
import type { PrimarySchema } from '../api/client';
import type { Point } from '../domain/coil';

/**
 * Centerline (r, z) of each primary turn's equivalent coaxial ring, in the
 * coil's geometry units — identical to `PrimarySpec.ring_centers()`.
 *
 * Turn k occupies [k, k+1] in turn-space (the last turn possibly fractional)
 * and its ring sits at that interval's midpoint, located on the straight
 * centerline by inverting the (linear) turn function. Returns one point per
 * turn: `ceil(total_turns)` of them.
 */
export function primaryRingCenters(primary: PrimarySchema): Point[] {
  const { total_turns, t_min, t_max } = primary.turn_fxn;
  const tMin = t_min ?? 0;
  const tMax = t_max ?? 1;
  const [sr, sz] = primary.start;
  const [er, ez] = primary.end;

  // Uniform winding: cumulative turns are linear in the curve parameter t,
  // turns(t) = total_turns * (t - tMin) / (tMax - tMin). The curve (a line
  // segment) runs over t ∈ [0, 1], so the winding's total turn count is
  // turns(1). (Equals total_turns for the editor's default [0, 1] window.)
  const turnsAt = (t: number) => (total_turns * (t - tMin)) / (tMax - tMin);
  const total = turnsAt(1);
  if (!(total > 0)) return [];

  const nRings = Math.ceil(total);
  const centers: Point[] = [];
  for (let k = 0; k < nRings; k++) {
    const midTurn = (k + Math.min(k + 1, total)) / 2;
    // Invert turns(t) = midTurn for the curve parameter, then evaluate the
    // straight centerline there (LineSegment.point_at is linear in t).
    const t = tMin + (midTurn / total_turns) * (tMax - tMin);
    centers.push([sr + t * (er - sr), sz + t * (ez - sz)]);
  }
  return centers;
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
