/**
 * Domain helpers over the coil schema: a default coil, factories for new
 * components, and the selection-reference types the editor uses to address
 * components inside the schema's arrays.
 */
import type {
  CoilSchema,
  GeometrySchema,
  GroundSchema,
  PrimarySchema,
  SecondarySchema,
  ToploadSchema,
} from '../api/client';

export type Point = [number, number];

/**
 * Internal coil model. Identical to the API's CoilSchema but with the
 * component arrays guaranteed present (the schema marks them optional
 * because the backend defaults them). Our store always initializes and
 * preserves them, so the app works with the stricter type and stays
 * assignable to CoilSchema for requests.
 */
export type Coil = Omit<CoilSchema, 'toploads' | 'grounds'> & {
  toploads: ToploadSchema[];
  grounds: GroundSchema[];
};

/** A stable way to address one component inside the coil. */
export type ComponentRef =
  | { kind: 'secondary' }
  | { kind: 'primary' }
  | { kind: 'topload'; index: number }
  | { kind: 'ground'; index: number };

/**
 * The editor supports selecting several components at once (e.g. via the
 * marquee), so a selection is a list of refs. An empty list means nothing is
 * selected. A single-component selection is just a one-element list.
 */
export type Selection = ComponentRef[];

/**
 * Canvas interaction modes. `pan` is the resting default (drag pans, and
 * dragging a selected component moves it). `select` is a one-shot pick: it
 * selects the next component clicked, then reverts to `pan`. The rest place a
 * component and likewise revert to `pan`.
 */
export type Tool = 'pan' | 'select' | 'secondary' | 'primary' | 'topload' | 'ground';

export function refKey(ref: ComponentRef): string {
  return ref.kind === 'topload' || ref.kind === 'ground'
    ? `${ref.kind}:${ref.index}`
    : ref.kind;
}

export function refEquals(a: ComponentRef, b: ComponentRef): boolean {
  return refKey(a) === refKey(b);
}

/** Whether `ref` is part of the current selection. */
export function isSelected(selection: Selection, ref: ComponentRef): boolean {
  return selection.some((s) => refEquals(s, ref));
}

/** Toggle `ref`'s membership in a selection (immutably). */
export function toggleRef(selection: Selection, ref: ComponentRef): Selection {
  return isSelected(selection, ref)
    ? selection.filter((s) => !refEquals(s, ref))
    : [...selection, ref];
}

// ---------------------------------------------------------------------------
// Factories
// ---------------------------------------------------------------------------

export function newSecondary(start: Point, end: Point): SecondarySchema {
  return {
    material: 'copper',
    turn_fxn: { kind: 'uniform', total_turns: 800, t_min: 0, t_max: 1 },
    start,
    end,
    wire_dia: 0.000508, // 0.02 in
  };
}

export function newPrimary(start: Point, end: Point): PrimarySchema {
  return {
    material: 'copper',
    turn_fxn: { kind: 'uniform', total_turns: 8, t_min: 0, t_max: 1 },
    cross_section: { kind: 'circular', diameter: 0.00635 }, // 0.25 in
    start,
    end,
    tank_capacitance: 1.88e-8, // absolute farads (never scaled by unit_scale)
    lead_length: 0.762, // 30 in
    lead_dia: 0.00508, // 0.2 in
  };
}

export function newTopload(center: Point, radius: number): ToploadSchema {
  return {
    material: 'aluminum',
    shape: { kind: 'circle', center, radius },
  };
}

export function newGround(center: Point, radius: number): GroundSchema {
  return {
    material: 'copper',
    shape: { kind: 'circle', center, radius },
  };
}

// ---------------------------------------------------------------------------
// Default coil — a simple starting point.
//
// All geometry is stored in SI base units (metres). The backend's `unit_scale`
// (metres per coil unit) is therefore always 1 and never surfaced in the UI;
// the frontend converts to/from the user's chosen display units. The values
// below are the classic JavaTC example coil, whose inch dimensions are noted.
// ---------------------------------------------------------------------------

export function defaultCoil(): Coil {
  return {
    secondary: newSecondary([0.057658, 0.5842], [0.057658, 1.13792]), // [2.27,23]–[2.27,44.8] in
    primary: newPrimary([0.09525, 0.5842], [0.202438, 0.5842]), // [3.75,23]–[7.97,23] in
    toploads: [newTopload([0.187325, 1.23952], 0.079375)], // center [7.375,48.8] in, r 3.125 in
    grounds: [],
    r_max: 2.54, // 100 in
    z_max: 3.81, // 150 in
    unit_scale: 1,
    discretization_order: 30,
    bc_bottom: null,
    bc_top: null,
    bc_right: null,
  };
}

/**
 * A blank starting point: just a bare solenoid secondary on the default
 * domain, with no primary, toploads, or grounds. The secondary is mandatory
 * (the schema's `secondary` is non-nullable and the whole model is a
 * resonator), so "blank" is the minimum simulatable coil, not an empty one.
 * Shares the demo's domain/units so the new winding lands on-canvas.
 */
export function blankCoil(): Coil {
  return {
    secondary: newSecondary([0.057658, 0.5842], [0.057658, 1.13792]),
    primary: null,
    toploads: [],
    grounds: [],
    r_max: 2.54,
    z_max: 3.81,
    unit_scale: 1,
    discretization_order: 30,
    bc_bottom: null,
    bc_top: null,
    bc_right: null,
  };
}

// ---------------------------------------------------------------------------
// Right-half-plane constraint (r >= 0)
// ---------------------------------------------------------------------------
//
// The geometry is the (r, z) cross-section of a solid of revolution about the
// r = 0 axis, so a negative radial coordinate is unphysical: the left half of
// the canvas is only a mirror of the right. `clampToRightHalfPlane` folds any
// negative r back onto the axis, and every store mutation runs through it, so
// no input path (canvas drag, placement, sidebar, context menu) can persist a
// point on the left. The helpers return their input unchanged when nothing
// needed clamping, so an already-valid coil keeps its object identity.

function clampR(p: Point): Point {
  return p[0] < 0 ? [0, p[1]] : p;
}

function mapPreserve<T>(items: T[], fn: (item: T) => T): T[] {
  let changed = false;
  const out = items.map((item) => {
    const next = fn(item);
    if (next !== item) changed = true;
    return next;
  });
  return changed ? out : items;
}

function clampShapeR(shape: GeometrySchema): GeometrySchema {
  if (shape.kind === 'circle') {
    const center = clampR(shape.center);
    return center === shape.center ? shape : { ...shape, center };
  }
  const vertices = mapPreserve(shape.vertices, clampR);
  return vertices === shape.vertices ? shape : { ...shape, vertices };
}

function clampConductorR<C extends ToploadSchema | GroundSchema>(conductor: C): C {
  const shape = clampShapeR(conductor.shape);
  return shape === conductor.shape ? conductor : { ...conductor, shape };
}

/** Fold every geometry coordinate onto the physical half-plane r >= 0.
 *  Returns the same coil object when nothing needed clamping. */
export function clampToRightHalfPlane(coil: Coil): Coil {
  const secStart = clampR(coil.secondary.start);
  const secEnd = clampR(coil.secondary.end);
  const secondary =
    secStart === coil.secondary.start && secEnd === coil.secondary.end
      ? coil.secondary
      : { ...coil.secondary, start: secStart, end: secEnd };

  let primary = coil.primary;
  if (primary) {
    const start = clampR(primary.start);
    const end = clampR(primary.end);
    if (start !== primary.start || end !== primary.end) {
      primary = { ...primary, start, end };
    }
  }

  const toploads = mapPreserve(coil.toploads, clampConductorR);
  const grounds = mapPreserve(coil.grounds, clampConductorR);

  if (
    secondary === coil.secondary &&
    primary === coil.primary &&
    toploads === coil.toploads &&
    grounds === coil.grounds
  ) {
    return coil;
  }
  return { ...coil, secondary, primary, toploads, grounds };
}
