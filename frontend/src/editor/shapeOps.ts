/**
 * Pure operations on conductor shapes: per-vertex edits and type
 * conversions, honoring the schema invariants (a rectangle has exactly 4
 * vertices; a polygon has >= 3). Adding a vertex to a rectangle promotes it
 * to a polygon; deleting one does too. Framework-free and unit-tested.
 */
import type { GeometrySchema } from '../api/client';
import type { Point } from '../domain/coil';

export type ShapeKind = GeometrySchema['kind'];
type CircleShape = Extract<GeometrySchema, { kind: 'circle' }>;
type RectShape = Extract<GeometrySchema, { kind: 'rectangle' }>;
type PolyShape = Extract<GeometrySchema, { kind: 'polygon' }>;

function bbox(verts: Point[]) {
  const xs = verts.map((v) => v[0]);
  const zs = verts.map((v) => v[1]);
  return {
    xMin: Math.min(...xs),
    xMax: Math.max(...xs),
    zMin: Math.min(...zs),
    zMax: Math.max(...zs),
  };
}

function centroid(verts: Point[]): Point {
  const n = verts.length || 1;
  return [
    verts.reduce((a, v) => a + v[0], 0) / n,
    verts.reduce((a, v) => a + v[1], 0) / n,
  ];
}

/** The editable vertices of a shape (empty for a circle, which uses center
 *  and radius handles instead). */
export function shapeVertices(shape: GeometrySchema): Point[] {
  return shape.kind === 'circle' ? [] : shape.vertices.map((v) => [v[0], v[1]]);
}

/** Replace vertex `index`. Kind is preserved (rectangle stays a rectangle). */
export function moveVertex(
  shape: GeometrySchema,
  index: number,
  p: Point,
): GeometrySchema {
  if (shape.kind === 'circle') return shape;
  const vertices = shape.vertices.map((v, i) => (i === index ? p : ([v[0], v[1]] as Point)));
  return { ...shape, vertices };
}

/** Insert a vertex at the nearest edge to `p`. A rectangle becomes a polygon
 *  (it would otherwise exceed 4 vertices). */
export function insertVertex(shape: GeometrySchema, p: Point): GeometrySchema {
  if (shape.kind === 'circle') return shape;
  const verts = shape.vertices.map((v) => [v[0], v[1]] as Point);
  const n = verts.length;

  // Nearest edge by point-to-segment distance.
  let best = 0;
  let bestD = Infinity;
  for (let i = 0; i < n; i++) {
    const a = verts[i]!;
    const b = verts[(i + 1) % n]!;
    const d = segmentDistance(p, a, b);
    if (d < bestD) {
      bestD = d;
      best = i;
    }
  }
  const vertices = [...verts.slice(0, best + 1), p, ...verts.slice(best + 1)];
  return { kind: 'polygon', vertices };
}

/** Delete vertex `index`. Returns null if the shape would drop below 3
 *  vertices. A rectangle becomes a polygon. */
export function deleteVertex(shape: GeometrySchema, index: number): GeometrySchema | null {
  if (shape.kind === 'circle') return null;
  if (shape.vertices.length <= 3) return null;
  const vertices = shape.vertices
    .filter((_, i) => i !== index)
    .map((v) => [v[0], v[1]] as Point);
  return { kind: 'polygon', vertices };
}

/** Translate a shape by (dx, dz), keeping its kind. Used to offset a pasted
 *  copy so it doesn't land exactly on top of the original. */
export function translateShape(shape: GeometrySchema, dx: number, dz: number): GeometrySchema {
  if (shape.kind === 'circle') {
    return { ...shape, center: [shape.center[0] + dx, shape.center[1] + dz] };
  }
  return {
    ...shape,
    vertices: shape.vertices.map((v) => [v[0] + dx, v[1] + dz] as Point),
  };
}

/** Convert a shape to another kind, choosing a sensible geometry. */
export function convertShape(shape: GeometrySchema, kind: ShapeKind): GeometrySchema {
  if (shape.kind === kind) return shape;

  if (kind === 'circle') {
    if (shape.kind === 'circle') return shape;
    const verts = shape.vertices.map((v) => [v[0], v[1]] as Point);
    const c = centroid(verts);
    const b = bbox(verts);
    const radius = Math.max((b.xMax - b.xMin) / 2, (b.zMax - b.zMin) / 2, 1e-6);
    return { kind: 'circle', center: c, radius } satisfies CircleShape;
  }

  // Target is rectangle or polygon: need a vertex list.
  let verts: Point[];
  if (shape.kind === 'circle') {
    const { center, radius } = shape;
    if (kind === 'rectangle') {
      verts = [
        [center[0] - radius, center[1] - radius],
        [center[0] + radius, center[1] - radius],
        [center[0] + radius, center[1] + radius],
        [center[0] - radius, center[1] + radius],
      ];
    } else {
      const segs = 16;
      verts = Array.from({ length: segs }, (_, i) => {
        const a = (2 * Math.PI * i) / segs;
        return [center[0] + radius * Math.cos(a), center[1] + radius * Math.sin(a)] as Point;
      });
    }
  } else {
    verts = shape.vertices.map((v) => [v[0], v[1]] as Point);
    if (kind === 'rectangle') {
      // Collapse to the bounding box (exactly 4 vertices).
      const b = bbox(verts);
      verts = [
        [b.xMin, b.zMin],
        [b.xMax, b.zMin],
        [b.xMax, b.zMax],
        [b.xMin, b.zMax],
      ];
    }
  }

  return kind === 'rectangle'
    ? ({ kind: 'rectangle', vertices: verts } satisfies RectShape)
    : ({ kind: 'polygon', vertices: verts } satisfies PolyShape);
}

function segmentDistance(p: Point, a: Point, b: Point): number {
  const dx = b[0] - a[0];
  const dz = b[1] - a[1];
  const lenSq = dx * dx + dz * dz;
  if (lenSq === 0) return Math.hypot(p[0] - a[0], p[1] - a[1]);
  let t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / lenSq;
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dz));
}
