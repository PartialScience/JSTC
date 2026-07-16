/**
 * The probe-point overlay for the field views: a draggable dot per cursor and,
 * when field vectors are on, an arrow from each dot along the field direction.
 * Drawn in world space through the shared `toScreen` transform, in its own
 * interactive layer above the (non-interactive) heatmap and dimmed geometry.
 *
 * The dot is authored at the cursor's world x (which may be on the mirrored
 * left half); the field is axisymmetric, so the arrow's radial component is
 * flipped on the left half to point the right way — matching FieldLayer.
 */
import { useMemo } from 'react';
import { Arrow, Circle, Group, Text } from 'react-konva';
import type { KonvaEventObject } from 'konva/lib/Node';

import type { FieldResponse } from '../api/client';
import type { Point } from '../domain/coil';
import type { FieldCursor } from '../state/store';
import { fieldDataFromResponse } from './fieldMath';
import { buildFieldSampler } from './sampleField';

/** Arrow length in screen pixels (a touch longer than the heatmap's sparse
 *  arrows so a single probe vector reads clearly). */
const ARROW_LEN = 30;
const DOT_RADIUS = 6;

interface CursorLayerProps {
  cursors: FieldCursor[];
  field: FieldResponse | null;
  fieldType: 'electric' | 'magnetic';
  showArrows: boolean;
  toScreen: (x: number, z: number) => { x: number; y: number };
  fromScreen: (sx: number, sy: number) => Point;
  onMove: (id: string, x: number, z: number) => void;
}

export function CursorLayer({
  cursors,
  field,
  fieldType,
  showArrows,
  toScreen,
  fromScreen,
  onMove,
}: CursorLayerProps) {
  // The sampler (for arrow directions) is only needed when arrows are shown.
  const sampler = useMemo(() => {
    if (!showArrows || !field) return null;
    return buildFieldSampler(fieldDataFromResponse(field), fieldType === 'magnetic' ? 'B' : 'E');
  }, [showArrows, field, fieldType]);

  const setCursor = (e: KonvaEventObject<unknown>, css: string) => {
    const c = e.target.getStage()?.container();
    if (c) c.style.cursor = css;
  };

  return (
    <>
      {cursors.map((cur, i) => {
        const p = toScreen(cur.x, cur.z);

        // Field-direction arrow (instantaneous), flipped on the mirrored half.
        let arrowPts: number[] | null = null;
        if (sampler) {
          const s = sampler.sampleAt(cur.x, cur.z);
          if (s.vr != null && s.vz != null) {
            const mag = Math.hypot(s.vr, s.vz);
            if (mag > 0) {
              const sgn = cur.x >= 0 ? 1 : -1;
              const ux = (sgn * s.vr) / mag;
              const uz = s.vz / mag; // world-up; screen y is down → subtract
              arrowPts = [p.x, p.y, p.x + ux * ARROW_LEN, p.y - uz * ARROW_LEN];
            }
          }
        }

        return (
          <Group key={cur.id}>
            {arrowPts && (
              <Arrow
                points={arrowPts}
                stroke={cur.color}
                fill={cur.color}
                strokeWidth={2}
                pointerLength={7}
                pointerWidth={7}
                shadowColor="#000"
                shadowBlur={3}
                shadowOpacity={0.5}
                listening={false}
              />
            )}
            {/* Index badge, offset up-right of the dot. */}
            <Text
              x={p.x + DOT_RADIUS + 3}
              y={p.y - DOT_RADIUS - 11}
              text={String(i + 1)}
              fontSize={11}
              fontStyle="bold"
              fill="#fff"
              shadowColor="#000"
              shadowBlur={2}
              shadowOpacity={0.9}
              listening={false}
            />
            {/* The draggable probe point. White ring + dark halo so the colour
             *  stays visible on any heatmap value. */}
            <Circle
              x={p.x}
              y={p.y}
              radius={DOT_RADIUS}
              fill={cur.color}
              stroke="#ffffff"
              strokeWidth={2}
              shadowColor="#000"
              shadowBlur={3}
              shadowOpacity={0.6}
              draggable
              hitStrokeWidth={14}
              onMouseEnter={(e) => setCursor(e, 'grab')}
              onMouseLeave={(e) => setCursor(e, 'default')}
              onDragStart={(e) => setCursor(e, 'grabbing')}
              onDragMove={(e) => {
                const [x, z] = fromScreen(e.target.x(), e.target.y());
                onMove(cur.id, x, z);
              }}
              onDragEnd={(e) => setCursor(e, 'grab')}
            />
          </Group>
        );
      })}
    </>
  );
}
