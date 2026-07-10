/**
 * Marquee hit-testing: which components does a world-space rectangle touch?
 * Pure and framework-free (unit tested); the canvas builds the rect from the
 * dragged screen box and applies the resulting refs to the store.
 *
 * The editor renders a mirrored (±r) cross-section, so a marquee drawn over
 * either arm should select the component: every component is tested against
 * both its +r outline and the mirrored -r copy.
 */
import { isSelected, type Coil, type ComponentRef, type Point, type Selection } from '../domain/coil';
import {
  mirrorX,
  pointInPolygon,
  primaryOutline,
  rectIntersectsPolygon,
  secondaryOutline,
  shapeOutline,
  type WorldRect,
} from './geometry';

function touches(rect: WorldRect, outline: Point[]): boolean {
  return (
    rectIntersectsPolygon(rect, outline) || rectIntersectsPolygon(rect, mirrorX(outline))
  );
}

/**
 * Every component whose (mirrored) outline the rectangle overlaps, in a
 * stable order: secondary, primary, then toploads and grounds by index.
 */
export function refsInRect(coil: Coil, rect: WorldRect): ComponentRef[] {
  const refs: ComponentRef[] = [];

  if (touches(rect, secondaryOutline(coil.secondary))) {
    refs.push({ kind: 'secondary' });
  }
  if (coil.primary && touches(rect, primaryOutline(coil.primary))) {
    refs.push({ kind: 'primary' });
  }
  coil.toploads.forEach((t, index) => {
    if (touches(rect, shapeOutline(t.shape))) refs.push({ kind: 'topload', index });
  });
  coil.grounds.forEach((g, index) => {
    if (touches(rect, shapeOutline(g.shape))) refs.push({ kind: 'ground', index });
  });

  return refs;
}

/** Whether a world point falls inside any currently-selected component's
 *  (mirrored) outline. Used to decide whether a drag that starts on the body
 *  should move the selection rather than pan. */
export function pointInSelection(coil: Coil, selection: Selection, p: Point): boolean {
  const inside = (outline: Point[]) =>
    pointInPolygon(p, outline) || pointInPolygon(p, mirrorX(outline));

  if (isSelected(selection, { kind: 'secondary' }) && inside(secondaryOutline(coil.secondary))) {
    return true;
  }
  if (
    coil.primary &&
    isSelected(selection, { kind: 'primary' }) &&
    inside(primaryOutline(coil.primary))
  ) {
    return true;
  }
  return (
    coil.toploads.some(
      (t, i) => isSelected(selection, { kind: 'topload', index: i }) && inside(shapeOutline(t.shape)),
    ) ||
    coil.grounds.some(
      (g, i) => isSelected(selection, { kind: 'ground', index: i }) && inside(shapeOutline(g.shape)),
    )
  );
}
