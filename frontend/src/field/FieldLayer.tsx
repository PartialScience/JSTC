/**
 * Konva rendering of the operating field: a heatmap image (magnitude or
 * potential), optional iso-contours and a normalized vector overlay. Drawn
 * behind the (non-interactive) geometry and mirrored across the r=0 axis to
 * match the editor's full cross-section view. Shares the editor's viewport
 * via the `toScreen` transform.
 */
import { useMemo } from 'react';
import { Group, Image as KonvaImage, Line } from 'react-konva';

import type { FieldResponse } from '../api/client';
import type { FieldDisplay } from '../state/store';
import { rasterize } from './colormap';
import {
  bIntensityMap,
  contourSegments,
  eIntensityMap,
  fieldDataFromResponse,
  robustMax,
  sampleArrows,
} from './fieldMath';

interface ToScreen {
  (x: number, z: number): { x: number; y: number };
}

export function FieldLayer({
  field,
  toScreen,
  display,
}: {
  field: FieldResponse;
  toScreen: ToScreen;
  display: FieldDisplay;
}) {
  const f = useMemo(() => fieldDataFromResponse(field), [field]);

  // The scalar we colour by, and its colour-scale max.
  const { scalar, vmax, potential } = useMemo(() => {
    if (display.colormap === 'potential') {
      // Instantaneous (real-part) potential, signed -> diverging map.
      const s = new Float64Array(f.nr * f.nz);
      for (let i = 0; i < s.length; i++) s[i] = f.mask[i] ? f.real[i]! : NaN;
      const absVals = new Float64Array(s.length);
      for (let i = 0; i < s.length; i++) absVals[i] = Math.abs(s[i]!);
      return { scalar: s, vmax: robustMax(absVals), potential: true };
    }
    const s = field.field_type === 'electric' ? eIntensityMap(f) : bIntensityMap(f);
    return { scalar: s, vmax: robustMax(s), potential: false };
  }, [f, display.colormap, field.field_type]);

  // Rasterize to an offscreen canvas Konva can draw as an image.
  const canvas = useMemo(() => {
    const img = rasterize(scalar, f, potential ? 'potential' : 'intensity', vmax);
    const c = document.createElement('canvas');
    c.width = f.nr;
    c.height = f.nz;
    c.getContext('2d')!.putImageData(img, 0, 0);
    return c;
  }, [scalar, f, vmax, potential]);

  // Image placement: world [0,r_max] x [0,z_max]. Top-left is (r=0, z=z_max).
  const tl = toScreen(f.rMin, f.zMax);
  const br = toScreen(f.rMax, f.zMin);
  const width = br.x - tl.x;
  const height = br.y - tl.y;
  const axisX = toScreen(0, f.zMax).x;

  // Contours (a handful of iso-levels across the range).
  const contourPolys = useMemo(() => {
    if (!display.showContours) return [];
    const levels: number[] = [];
    const n = 8;
    for (let i = 1; i < n; i++) {
      levels.push(potential ? (-vmax + (2 * vmax * i) / n) : (vmax * i) / n);
    }
    return contourSegments(scalar, f, levels);
  }, [display.showContours, scalar, f, vmax, potential]);

  const arrows = useMemo(
    () =>
      display.showArrows
        ? sampleArrows(f, field.field_type === 'electric' ? 'E' : 'B', 8)
        : [],
    [display.showArrows, f, field.field_type],
  );

  const arrowLenPx = 14;

  return (
    <Group listening={false}>
      {/* +r heatmap */}
      <KonvaImage image={canvas} x={tl.x} y={tl.y} width={width} height={height} />
      {/* mirrored -r heatmap (flip about the axis) */}
      <KonvaImage
        image={canvas}
        x={axisX}
        y={tl.y}
        width={width}
        height={height}
        scaleX={-1}
      />

      {contourPolys.map((s, i) => {
        const a = toScreen(s.x1, s.z1);
        const b = toScreen(s.x2, s.z2);
        const am = toScreen(-s.x1, s.z1);
        const bm = toScreen(-s.x2, s.z2);
        return (
          <Group key={`c${i}`}>
            <Line points={[a.x, a.y, b.x, b.y]} stroke="rgba(255,255,255,0.35)" strokeWidth={0.75} />
            <Line points={[am.x, am.y, bm.x, bm.y]} stroke="rgba(255,255,255,0.35)" strokeWidth={0.75} />
          </Group>
        );
      })}

      {arrows.map((ar, i) => {
        const p = toScreen(ar.x, ar.z);
        // dz is world-up; screen y is down, so negate the z component.
        const tip = { x: p.x + ar.dx * arrowLenPx, y: p.y - ar.dz * arrowLenPx };
        const pm = toScreen(-ar.x, ar.z);
        const tipm = { x: pm.x - ar.dx * arrowLenPx, y: pm.y - ar.dz * arrowLenPx };
        return (
          <Group key={`a${i}`}>
            <Line points={[p.x, p.y, tip.x, tip.y]} stroke="rgba(255,255,255,0.7)" strokeWidth={1} />
            <Line points={[pm.x, pm.y, tipm.x, tipm.y]} stroke="rgba(255,255,255,0.7)" strokeWidth={1} />
          </Group>
        );
      })}
    </Group>
  );
}
