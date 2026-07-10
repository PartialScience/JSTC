/**
 * Pure geometry helpers: turn schema components into world-space polylines
 * and handle positions for rendering. Kept framework-free and unit-tested;
 * the Konva layer maps these through the viewport.
 */
import type { GeometrySchema, PrimarySchema, SecondarySchema } from '../api/client';
import type { Point } from '../domain/coil';
import { primaryCrossSectionHalfExtent, primaryRingCenters } from './primaryRings';

/** The winding as a stadium/capsule outline in world (r, z), one side of the
 *  axis. The secondary is a line of half-width wire_dia/2 with round caps. */
export function secondaryOutline(sec: SecondarySchema, capSegments = 8): Point[] {
  const [x0, z0] = sec.start;
  const [x1, z1] = sec.end;
  const half = sec.wire_dia / 2;
  const dx = x1 - x0;
  const dz = z1 - z0;
  const len = Math.hypot(dx, dz) || 1;
  // Unit tangent and left normal.
  const tx = dx / len;
  const tz = dz / len;
  const nx = -tz;
  const nz = tx;

  const pts: Point[] = [];
  // Left side start -> end
  pts.push([x0 + nx * half, z0 + nz * half]);
  pts.push([x1 + nx * half, z1 + nz * half]);
  // End cap (semicircle from +n to -n around the end point)
  for (let i = 1; i < capSegments; i++) {
    const a = (Math.PI * i) / capSegments;
    // Rotate the +normal toward the tangent then to -normal
    const ca = Math.cos(a);
    const sa = Math.sin(a);
    const ox = nx * ca + tx * sa;
    const oz = nz * ca + tz * sa;
    pts.push([x1 + ox * half, z1 + oz * half]);
  }
  // Right side end -> start
  pts.push([x1 - nx * half, z1 - nz * half]);
  pts.push([x0 - nx * half, z0 - nz * half]);
  // Start cap (semicircle back to +n)
  for (let i = 1; i < capSegments; i++) {
    const a = (Math.PI * i) / capSegments;
    const ca = Math.cos(a);
    const sa = Math.sin(a);
    const ox = -nx * ca - tx * sa;
    const oz = -nz * ca - tz * sa;
    pts.push([x0 + ox * half, z0 + oz * half]);
  }
  return pts;
}

/** The primary's capsule outline in world (r, z), one side of the axis. The
 *  primary reuses the winding capsule with its cross-section width as the
 *  effective wire diameter (round conductor -> diameter, ribbon -> width). */
export function primaryOutline(prim: PrimarySchema, capSegments = 8): Point[] {
  const width =
    prim.cross_section.kind === 'circular'
      ? prim.cross_section.diameter
      : prim.cross_section.width;
  return secondaryOutline({ ...prim, wire_dia: width } as SecondarySchema, capSegments);
}

/** The primary's per-turn ring cross-sections as world-space polygons (one
 *  side of the axis). One polygon per turn, centered on the ring center the
 *  solver uses (`primaryRingCenters`) and sized to the conductor cross-section
 *  — a circle for round wire, a rectangle for ribbon. This is the honest 2-D
 *  picture of the primary: the discrete rings the physics actually models,
 *  rather than a single swept band. */
export function primaryRingOutlines(prim: PrimarySchema, circleSegments = 32): Point[][] {
  const { r, z, circular } = primaryCrossSectionHalfExtent(prim);
  return primaryRingCenters(prim).map(([cx, cz]) => {
    if (circular) {
      const pts: Point[] = [];
      for (let i = 0; i < circleSegments; i++) {
        const a = (2 * Math.PI * i) / circleSegments;
        pts.push([cx + r * Math.cos(a), cz + r * Math.sin(a)]);
      }
      return pts;
    }
    return [
      [cx - r, cz - z],
      [cx + r, cz - z],
      [cx + r, cz + z],
      [cx - r, cz + z],
    ];
  });
}

/** Sample a shape's boundary into a world-space polygon (one side). */
export function shapeOutline(shape: GeometrySchema, circleSegments = 48): Point[] {
  if (shape.kind === 'circle') {
    const [cx, cz] = shape.center;
    const pts: Point[] = [];
    for (let i = 0; i < circleSegments; i++) {
      const a = (2 * Math.PI * i) / circleSegments;
      pts.push([cx + shape.radius * Math.cos(a), cz + shape.radius * Math.sin(a)]);
    }
    return pts;
  }
  // rectangle / polygon: vertices are already the outline
  return shape.vertices.map((v) => [v[0], v[1]] as Point);
}

/** Flatten world points to a flat number[] for a Konva Line/Shape, mapped by
 *  a caller-supplied world->screen function. */
export function toFlatScreen(
  pts: Point[],
  toScreen: (x: number, z: number) => { x: number; y: number },
): number[] {
  const out: number[] = [];
  for (const [wx, wz] of pts) {
    const s = toScreen(wx, wz);
    out.push(s.x, s.y);
  }
  return out;
}

/** Mirror world points across the axis (x -> -x). */
export function mirrorX(pts: Point[]): Point[] {
  return pts.map(([x, z]) => [-x, z] as Point);
}

/** Axis-aligned bounding box of a shape's center handles for hit-testing /
 *  right-click menu placement (world coords). */
export function shapeCentroid(shape: GeometrySchema): Point {
  if (shape.kind === 'circle') return [shape.center[0], shape.center[1]];
  const n = shape.vertices.length || 1;
  let sx = 0;
  let sz = 0;
  for (const v of shape.vertices) {
    sx += v[0];
    sz += v[1];
  }
  return [sx / n, sz / n];
}

// ---------------------------------------------------------------------------
// Hit-testing (marquee selection). All in world (r, z) coordinates.
// ---------------------------------------------------------------------------

/** An axis-aligned world-space rectangle. */
export interface WorldRect {
  xMin: number;
  xMax: number;
  zMin: number;
  zMax: number;
}

/** Build a normalized rectangle from any two world corners. */
export function rectFromCorners(a: Point, b: Point): WorldRect {
  return {
    xMin: Math.min(a[0], b[0]),
    xMax: Math.max(a[0], b[0]),
    zMin: Math.min(a[1], b[1]),
    zMax: Math.max(a[1], b[1]),
  };
}

/** Ray-casting point-in-polygon test (polygon given as a closed loop of
 *  vertices; the closing edge is implicit). */
export function pointInPolygon(p: Point, poly: Point[]): boolean {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, zi] = poly[i]!;
    const [xj, zj] = poly[j]!;
    const crosses = zi > p[1] !== zj > p[1];
    if (crosses && p[0] < ((xj - xi) * (p[1] - zi)) / (zj - zi) + xi) {
      inside = !inside;
    }
  }
  return inside;
}

/** Whether segment ab intersects segment cd (proper or touching). */
export function segmentsIntersect(a: Point, b: Point, c: Point, d: Point): boolean {
  const o = (p: Point, q: Point, r: Point) =>
    (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]);
  const onSeg = (p: Point, q: Point, r: Point) =>
    Math.min(p[0], r[0]) <= q[0] &&
    q[0] <= Math.max(p[0], r[0]) &&
    Math.min(p[1], r[1]) <= q[1] &&
    q[1] <= Math.max(p[1], r[1]);
  const o1 = o(a, b, c);
  const o2 = o(a, b, d);
  const o3 = o(c, d, a);
  const o4 = o(c, d, b);
  if (o1 * o2 < 0 && o3 * o4 < 0) return true;
  // Collinear/touching cases.
  if (o1 === 0 && onSeg(a, c, b)) return true;
  if (o2 === 0 && onSeg(a, d, b)) return true;
  if (o3 === 0 && onSeg(c, a, d)) return true;
  if (o4 === 0 && onSeg(c, b, d)) return true;
  return false;
}

/** Whether a world rectangle overlaps a polygon (touching counts). Handles
 *  every case: a vertex inside the rect, the rect inside the polygon, or any
 *  edges crossing. Used for "touch to select" marquee behaviour. */
export function rectIntersectsPolygon(rect: WorldRect, poly: Point[]): boolean {
  if (poly.length === 0) return false;
  const inRect = (p: Point) =>
    p[0] >= rect.xMin && p[0] <= rect.xMax && p[1] >= rect.zMin && p[1] <= rect.zMax;

  // Any polygon vertex inside the rect.
  if (poly.some(inRect)) return true;

  // The rect (any corner) inside the polygon.
  const corners: Point[] = [
    [rect.xMin, rect.zMin],
    [rect.xMax, rect.zMin],
    [rect.xMax, rect.zMax],
    [rect.xMin, rect.zMax],
  ];
  if (corners.some((c) => pointInPolygon(c, poly))) return true;

  // Any polygon edge crossing any rect edge.
  for (let i = 0; i < poly.length; i++) {
    const a = poly[i]!;
    const b = poly[(i + 1) % poly.length]!;
    for (let k = 0; k < 4; k++) {
      if (segmentsIntersect(a, b, corners[k]!, corners[(k + 1) % 4]!)) return true;
    }
  }
  return false;
}
