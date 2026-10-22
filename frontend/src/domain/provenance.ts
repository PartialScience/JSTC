/**
 * Experimental-validation provenance of the coil model.
 *
 * The JavaTC-comparable feature set has years of community validation behind
 * it; newer modeling features (parametric winding paths, graded turn
 * distributions) do not yet. This module is the single source of truth for
 * that distinction:
 *
 *  * `SCHEMA_PROVENANCE` classifies EVERY input-schema property reachable
 *    from the coil as 'trusted' or 'untrusted'. An exhaustiveness test walks
 *    the generated OpenAPI schema and fails when a property is missing, so
 *    future work is forced to answer "has this been experimentally verified
 *    yet?" before it can ship — provenance can never silently rot.
 *
 *  * `UNVALIDATED_FEATURES` is the declarative registry the UI renders from:
 *    each entry carries the user-facing wording and an `applies(coil)`
 *    predicate over the COIL STATE (never over what happens to be mounted,
 *    so a collapsed panel can't hide a warning). The Results banner lists
 *    the active entries; input controls show a badge via the same entry, so
 *    the two can never disagree.
 *
 * Lifecycle: a new unvalidated feature ships with its schema keys marked
 * 'untrusted' and one registry entry; once the community validates it, flip
 * the keys to 'trusted' and delete the entry.
 */
import type { Coil } from './coil';

export type Provenance = 'trusted' | 'untrusted';

/**
 * Classification of every input-schema property, keyed
 * "SchemaName.property". Checked for exhaustiveness against openapi.json by
 * domain/provenance.test.ts.
 */
export const SCHEMA_PROVENANCE: Record<string, Provenance> = {
  // --- the coil envelope -----------------------------------------------------
  'SimulatableTeslaCoilSchema.secondary': 'trusted',
  'SimulatableTeslaCoilSchema.primary': 'trusted',
  'SimulatableTeslaCoilSchema.toploads': 'trusted',
  'SimulatableTeslaCoilSchema.grounds': 'trusted',
  'SimulatableTeslaCoilSchema.r_max': 'trusted',
  'SimulatableTeslaCoilSchema.z_max': 'trusted',
  'SimulatableTeslaCoilSchema.unit_scale': 'trusted',
  'SimulatableTeslaCoilSchema.discretization_order': 'trusted',
  'SimulatableTeslaCoilSchema.bc_bottom': 'trusted',
  'SimulatableTeslaCoilSchema.bc_top': 'trusted',
  'SimulatableTeslaCoilSchema.bc_right': 'trusted',

  // --- windings ---------------------------------------------------------------
  'SecondaryConductorSchema.material': 'trusted',
  'SecondaryConductorSchema.turn_fxn': 'trusted',
  'SecondaryConductorSchema.path': 'trusted',
  'SecondaryConductorSchema.wire_dia': 'trusted',
  'PrimarySchema.material': 'trusted',
  'PrimarySchema.turn_fxn': 'trusted',
  'PrimarySchema.cross_section': 'trusted',
  'PrimarySchema.path': 'trusted',
  'PrimarySchema.tank_capacitance': 'trusted',
  'PrimarySchema.lead_length': 'trusted',
  'PrimarySchema.lead_dia': 'trusted',

  // --- winding paths ------------------------------------------------------------
  // The straight centerline is the JavaTC-validated baseline.
  'LinePathSchema.kind': 'trusted',
  'LinePathSchema.start': 'trusted',
  'LinePathSchema.end': 'trusted',
  // Arc and spline centerlines are new physics surface: not yet validated.
  'ArcPathSchema.kind': 'untrusted',
  'ArcPathSchema.start': 'untrusted',
  'ArcPathSchema.mid': 'untrusted',
  'ArcPathSchema.end': 'untrusted',
  'SplinePathSchema.kind': 'untrusted',
  'SplinePathSchema.points': 'untrusted',
  'PiecewisePathSchema.kind': 'untrusted',
  'PiecewisePathSchema.first': 'untrusted',
  'PiecewisePathSchema.rest': 'untrusted',
  'LineFromSchema.kind': 'untrusted',
  'LineFromSchema.length': 'untrusted',
  'ArcFromSchema.kind': 'untrusted',
  'ArcFromSchema.end': 'untrusted',
  'SplineFromSchema.kind': 'untrusted',
  'SplineFromSchema.points': 'untrusted',

  // --- turn profiles ------------------------------------------------------------
  'UniformTurnProfileSchema.kind': 'trusted',
  'UniformTurnProfileSchema.total_turns': 'trusted',
  'GradedTurnProfileSchema.kind': 'untrusted',
  'GradedTurnProfileSchema.points': 'untrusted',

  // --- conductor cross-sections ---------------------------------------------------
  'CircularCrossSectionSchema.kind': 'trusted',
  'CircularCrossSectionSchema.diameter': 'trusted',
  'RectangularCrossSectionSchema.kind': 'trusted',
  'RectangularCrossSectionSchema.width': 'trusted',
  'RectangularCrossSectionSchema.height': 'trusted',

  // --- component shapes -------------------------------------------------------------
  'ToploadSchema.material': 'trusted',
  'ToploadSchema.shape': 'trusted',
  'GroundedConductorSchema.material': 'trusted',
  'GroundedConductorSchema.shape': 'trusted',
  'CircleSchema.kind': 'trusted',
  'CircleSchema.center': 'trusted',
  'CircleSchema.radius': 'trusted',
  'RectangleSchema.kind': 'trusted',
  'RectangleSchema.vertices': 'trusted',
  'PolygonSchema.kind': 'trusted',
  'PolygonSchema.vertices': 'trusted',

  // --- boundary conditions ---------------------------------------------------------
  'BoundaryConditionSchema.bc_type': 'trusted',
  'BoundaryConditionSchema.value': 'trusted',
};

export interface UnvalidatedFeature {
  id: string;
  /** Bullet text shown in the Results banner and in field badges. */
  wording: string;
  /** SCHEMA_PROVENANCE key prefixes this entry covers — the test asserts
   *  every 'untrusted' key is covered by at least one registry entry. */
  covers: string[];
  /** Whether the CURRENT coil engages this feature (evaluated on the coil
   *  state, never on mounted components). */
  applies(coil: Coil): boolean;
}

export const UNVALIDATED_FEATURES: UnvalidatedFeature[] = [
  {
    id: 'arc-secondary',
    wording: 'Arc secondary path',
    covers: ['ArcPathSchema'],
    applies: (coil) => coil.secondary.path.kind === 'arc',
  },
  {
    id: 'spline-secondary',
    wording: 'Spline secondary path',
    covers: ['SplinePathSchema'],
    applies: (coil) => coil.secondary.path.kind === 'spline',
  },
  {
    id: 'arc-primary',
    wording: 'Arc primary path',
    covers: ['ArcPathSchema'],
    applies: (coil) => coil.primary?.path.kind === 'arc',
  },
  {
    id: 'spline-primary',
    wording: 'Spline primary path',
    covers: ['SplinePathSchema'],
    applies: (coil) => coil.primary?.path.kind === 'spline',
  },
  {
    id: 'piecewise-secondary',
    wording: 'Piecewise secondary path',
    covers: ['PiecewisePathSchema', 'LineFromSchema', 'ArcFromSchema', 'SplineFromSchema'],
    applies: (coil) => coil.secondary.path.kind === 'piecewise',
  },
  {
    id: 'piecewise-primary',
    wording: 'Piecewise primary path',
    covers: ['PiecewisePathSchema', 'LineFromSchema', 'ArcFromSchema', 'SplineFromSchema'],
    applies: (coil) => coil.primary?.path.kind === 'piecewise',
  },
  {
    id: 'graded-secondary-turns',
    wording: 'Graded secondary winding density',
    covers: ['GradedTurnProfileSchema'],
    applies: (coil) => coil.secondary.turn_fxn.kind === 'graded',
  },
  {
    id: 'graded-primary-turns',
    wording: 'Graded primary winding density',
    covers: ['GradedTurnProfileSchema'],
    applies: (coil) => coil.primary?.turn_fxn.kind === 'graded',
  },
];

/** The registry entries the current coil engages (for the Results banner). */
export function activeUnvalidatedFeatures(coil: Coil): UnvalidatedFeature[] {
  return UNVALIDATED_FEATURES.filter((f) => f.applies(coil));
}

/** Look up a registry entry by id (for field badges). */
export function unvalidatedFeature(id: string): UnvalidatedFeature {
  const f = UNVALIDATED_FEATURES.find((e) => e.id === id);
  if (!f) throw new Error(`Unknown unvalidated feature id: ${id}`);
  return f;
}
