/**
 * Rigid translation of a selection. Dragging a selected component's body
 * moves the whole selection as one group; the radial delta is clamped so the
 * group's leftmost defining point stops at the r = 0 axis (the whole
 * selection stops together, preserving each shape - unlike the store's
 * per-point fold, which would deform a shape pushed across the axis).
 *
 * Pure and framework-free (unit tested); the canvas turns a body-drag into
 * incremental (dr, dz) deltas and the store applies them.
 */
import type { GeometrySchema } from '../api/client';
import { isSelected, type Coil, type Point, type Selection } from '../domain/coil';
import { translateShape } from './shapeOps';

/** The smallest r among a shape's defining coordinates (circle center, or
 *  polygon/rectangle vertices) - matching what the r >= 0 clamp constrains. */
function shapeMinR(shape: GeometrySchema): number {
  if (shape.kind === 'circle') return shape.center[0];
  return Math.min(...shape.vertices.map((v) => v[0]));
}

/**
 * The smallest r coordinate among all selected components' defining points,
 * or null when nothing translatable is selected.
 */
export function selectionMinR(coil: Coil, selection: Selection): number | null {
  let min = Infinity;
  if (isSelected(selection, { kind: 'secondary' })) {
    min = Math.min(min, coil.secondary.start[0], coil.secondary.end[0]);
  }
  if (coil.primary && isSelected(selection, { kind: 'primary' })) {
    min = Math.min(min, coil.primary.start[0], coil.primary.end[0]);
  }
  coil.toploads.forEach((t, i) => {
    if (isSelected(selection, { kind: 'topload', index: i })) {
      min = Math.min(min, shapeMinR(t.shape));
    }
  });
  coil.grounds.forEach((g, i) => {
    if (isSelected(selection, { kind: 'ground', index: i })) {
      min = Math.min(min, shapeMinR(g.shape));
    }
  });
  return Number.isFinite(min) ? min : null;
}

const shift = (p: Point, dr: number, dz: number): Point => [p[0] + dr, p[1] + dz];

/**
 * Translate every selected component by (dr, dz) as one rigid group, clamping
 * the radial delta so nothing crosses r = 0. Returns the same coil object when
 * nothing translatable is selected or the clamped move is a no-op.
 */
export function translateComponents(
  coil: Coil,
  selection: Selection,
  dr: number,
  dz: number,
): Coil {
  const minR = selectionMinR(coil, selection);
  if (minR === null) return coil;
  // Never push the leftmost point below the axis; the whole group stops there.
  const cdr = Math.max(dr, -minR);
  if (cdr === 0 && dz === 0) return coil;

  const secondary = isSelected(selection, { kind: 'secondary' })
    ? {
        ...coil.secondary,
        start: shift(coil.secondary.start, cdr, dz),
        end: shift(coil.secondary.end, cdr, dz),
      }
    : coil.secondary;

  const primary =
    coil.primary && isSelected(selection, { kind: 'primary' })
      ? {
          ...coil.primary,
          start: shift(coil.primary.start, cdr, dz),
          end: shift(coil.primary.end, cdr, dz),
        }
      : coil.primary;

  const toploads = coil.toploads.map((t, i) =>
    isSelected(selection, { kind: 'topload', index: i })
      ? { ...t, shape: translateShape(t.shape, cdr, dz) }
      : t,
  );
  const grounds = coil.grounds.map((g, i) =>
    isSelected(selection, { kind: 'ground', index: i })
      ? { ...g, shape: translateShape(g.shape, cdr, dz) }
      : g,
  );

  return { ...coil, secondary, primary, toploads, grounds };
}
