import { describe, expect, it } from 'vitest';

import type { GeometrySchema } from '../api/client';
import {
  convertShape,
  deleteVertex,
  insertVertex,
  moveVertex,
  shapeVertices,
  translateShape,
} from './shapeOps';

const rect: GeometrySchema = {
  kind: 'rectangle',
  vertices: [
    [0, 0],
    [4, 0],
    [4, 2],
    [0, 2],
  ],
};
const circle: GeometrySchema = { kind: 'circle', center: [5, 5], radius: 3 };

describe('shapeVertices', () => {
  it('is empty for a circle, the vertices otherwise', () => {
    expect(shapeVertices(circle)).toEqual([]);
    expect(shapeVertices(rect)).toHaveLength(4);
  });
});

describe('moveVertex', () => {
  it('replaces one vertex, keeping the kind', () => {
    const out = moveVertex(rect, 2, [9, 9]);
    expect(out.kind).toBe('rectangle');
    if (out.kind !== 'circle') expect(out.vertices[2]).toEqual([9, 9]);
  });
});

describe('insertVertex', () => {
  it('promotes a rectangle to a polygon with the new vertex on the nearest edge', () => {
    // A point just outside the bottom edge -> inserted between v0 and v1.
    const out = insertVertex(rect, [2, -0.1]);
    expect(out.kind).toBe('polygon');
    if (out.kind !== 'circle') {
      expect(out.vertices).toHaveLength(5);
      expect(out.vertices[1]).toEqual([2, -0.1]);
    }
  });
});

describe('deleteVertex', () => {
  it('drops a vertex and demotes a rectangle to a triangle polygon', () => {
    const out = deleteVertex(rect, 0);
    expect(out?.kind).toBe('polygon');
    if (out && out.kind !== 'circle') expect(out.vertices).toHaveLength(3);
  });

  it('refuses to go below 3 vertices', () => {
    const tri: GeometrySchema = { kind: 'polygon', vertices: [[0, 0], [1, 0], [0, 1]] };
    expect(deleteVertex(tri, 0)).toBeNull();
  });

  it('returns null for a circle', () => {
    expect(deleteVertex(circle, 0)).toBeNull();
  });
});

describe('translateShape', () => {
  it('offsets a circle center, keeping the kind and radius', () => {
    const out = translateShape(circle, 2, -3);
    expect(out.kind).toBe('circle');
    if (out.kind === 'circle') {
      expect(out.center).toEqual([7, 2]);
      expect(out.radius).toBe(3);
    }
  });

  it('offsets every vertex of a rectangle/polygon', () => {
    const out = translateShape(rect, 1, 1);
    expect(out.kind).toBe('rectangle');
    if (out.kind !== 'circle') {
      expect(out.vertices).toEqual([
        [1, 1],
        [5, 1],
        [5, 3],
        [1, 3],
      ]);
    }
  });
});

describe('convertShape', () => {
  it('circle -> rectangle is the bounding square', () => {
    const out = convertShape(circle, 'rectangle');
    expect(out.kind).toBe('rectangle');
    if (out.kind !== 'circle') {
      expect(out.vertices).toHaveLength(4);
      expect(out.vertices).toContainEqual([2, 2]); // center 5,5 minus radius 3
      expect(out.vertices).toContainEqual([8, 8]);
    }
  });

  it('circle -> polygon samples the circle', () => {
    const out = convertShape(circle, 'polygon');
    expect(out.kind).toBe('polygon');
    if (out.kind !== 'circle') {
      for (const v of out.vertices) {
        expect(Math.hypot(v[0] - 5, v[1] - 5)).toBeCloseTo(3, 6);
      }
    }
  });

  it('rectangle -> circle centers on the centroid', () => {
    const out = convertShape(rect, 'circle');
    expect(out.kind).toBe('circle');
    if (out.kind === 'circle') {
      expect(out.center).toEqual([2, 1]);
      expect(out.radius).toBeCloseTo(2, 6); // half the 4-wide bbox
    }
  });

  it('polygon -> rectangle collapses to the bounding box (4 vertices)', () => {
    const poly: GeometrySchema = {
      kind: 'polygon',
      vertices: [[0, 0], [3, 1], [2, 4], [-1, 2]],
    };
    const out = convertShape(poly, 'rectangle');
    expect(out.kind).toBe('rectangle');
    if (out.kind !== 'circle') expect(out.vertices).toHaveLength(4);
  });

  it('is a no-op when the kind is unchanged', () => {
    expect(convertShape(rect, 'rectangle')).toBe(rect);
  });
});
