import { describe, expect, it } from 'vitest';

import { newSecondary } from '../domain/coil';
import {
  mirrorX,
  pointInPolygon,
  rectIntersectsPolygon,
  secondaryOutline,
  segmentsIntersect,
  shapeCentroid,
  shapeOutline,
} from './geometry';

describe('secondaryOutline', () => {
  it('produces a closed capsule at wire_dia/2 from the centerline', () => {
    const sec = newSecondary([2, 0], [2, 10]);
    sec.wire_dia = 0.4;
    const pts = secondaryOutline(sec);
    // Every point is within the half-width envelope of the vertical segment.
    for (const [x, z] of pts) {
      const radial = Math.abs(x - 2);
      if (z >= 0 && z <= 10) {
        expect(radial).toBeLessThanOrEqual(0.2 + 1e-9);
      } else {
        // In the cap region, distance to the nearer endpoint <= half
        const d = Math.min(Math.hypot(x - 2, z - 0), Math.hypot(x - 2, z - 10));
        expect(d).toBeLessThanOrEqual(0.2 + 1e-9);
      }
    }
    expect(pts.length).toBeGreaterThan(4);
  });
});

describe('shapeOutline', () => {
  it('samples a circle at the given radius', () => {
    const pts = shapeOutline({ kind: 'circle', center: [3, 4], radius: 2 }, 32);
    expect(pts).toHaveLength(32);
    for (const [x, z] of pts) {
      expect(Math.hypot(x - 3, z - 4)).toBeCloseTo(2, 9);
    }
  });

  it('returns rectangle vertices verbatim', () => {
    const verts: [number, number][] = [
      [0, 0],
      [1, 0],
      [1, 1],
      [0, 1],
    ];
    const pts = shapeOutline({ kind: 'rectangle', vertices: verts });
    expect(pts).toEqual(verts);
  });
});

describe('mirrorX', () => {
  it('negates x, preserves z', () => {
    expect(mirrorX([[2, 5], [-3, 1]])).toEqual([
      [-2, 5],
      [3, 1],
    ]);
  });
});

describe('shapeCentroid', () => {
  it('is the circle center', () => {
    expect(shapeCentroid({ kind: 'circle', center: [7, 8], radius: 1 })).toEqual([7, 8]);
  });

  it('averages polygon vertices', () => {
    expect(
      shapeCentroid({
        kind: 'rectangle',
        vertices: [
          [0, 0],
          [2, 0],
          [2, 2],
          [0, 2],
        ],
      }),
    ).toEqual([1, 1]);
  });
});

describe('pointInPolygon', () => {
  const square: [number, number][] = [
    [0, 0],
    [4, 0],
    [4, 4],
    [0, 4],
  ];

  it('detects points inside and outside', () => {
    expect(pointInPolygon([2, 2], square)).toBe(true);
    expect(pointInPolygon([5, 2], square)).toBe(false);
    expect(pointInPolygon([-1, -1], square)).toBe(false);
  });
});

describe('segmentsIntersect', () => {
  it('detects crossing and non-crossing segments', () => {
    expect(segmentsIntersect([0, 0], [4, 4], [0, 4], [4, 0])).toBe(true);
    expect(segmentsIntersect([0, 0], [1, 0], [0, 1], [1, 1])).toBe(false);
  });
});

describe('rectIntersectsPolygon', () => {
  const square: [number, number][] = [
    [0, 0],
    [4, 0],
    [4, 4],
    [0, 4],
  ];

  it('true when the rect overlaps, contains, or is contained', () => {
    // Overlapping corner.
    expect(rectIntersectsPolygon({ xMin: 3, xMax: 6, zMin: 3, zMax: 6 }, square)).toBe(true);
    // Rect fully inside the polygon.
    expect(rectIntersectsPolygon({ xMin: 1, xMax: 2, zMin: 1, zMax: 2 }, square)).toBe(true);
    // Polygon fully inside the rect.
    expect(rectIntersectsPolygon({ xMin: -1, xMax: 5, zMin: -1, zMax: 5 }, square)).toBe(true);
  });

  it('false when the rect is disjoint from the polygon', () => {
    expect(rectIntersectsPolygon({ xMin: 10, xMax: 12, zMin: 10, zMax: 12 }, square)).toBe(
      false,
    );
  });

  it('touches a thin vertical capsule the marquee only grazes', () => {
    const sec = newSecondary([2, 0], [2, 10]);
    sec.wire_dia = 0.02; // sub-pixel thin, the hard-to-click case
    const outline = secondaryOutline(sec);
    // A wide box that barely straddles the centerline still selects it.
    expect(rectIntersectsPolygon({ xMin: 1.9, xMax: 2.1, zMin: 3, zMax: 7 }, outline)).toBe(
      true,
    );
  });
});
