/**
 * Konva renderers for each coil component. Every component is drawn on both
 * sides of the r=0 axis (mirrored full cross-section); only the +r side
 * carries interactive handles. Screen positions come from the shared
 * viewport via the `toScreen` prop, so these components hold no transform
 * state of their own.
 */
import { useRef, useState } from 'react';
import { Circle, Line } from 'react-konva';
import type Konva from 'konva';
import type { KonvaEventObject } from 'konva/lib/Node';

import type {
  GroundSchema,
  PrimarySchema,
  SecondarySchema,
  ToploadSchema,
} from '../api/client';
import type { ComponentRef, Point } from '../domain/coil';
import type { ThemeColors } from '../theme';
import {
  mirrorX,
  primaryRingOutlines,
  secondaryOutline,
  shapeOutline,
  toFlatScreen,
} from './geometry';
import { moveVertex, shapeVertices } from './shapeOps';

/** Perpendicular half-width of a winding from a dragged point: the distance
 *  from the point to the centerline, projected on the normal. */
function halfWidthFrom(start: Point, end: Point, p: Point): number {
  const dx = end[0] - start[0];
  const dz = end[1] - start[1];
  const len = Math.hypot(dx, dz) || 1;
  const nx = -dz / len;
  const nz = dx / len;
  const mx = (start[0] + end[0]) / 2;
  const mz = (start[1] + end[1]) / 2;
  return Math.max(Math.abs((p[0] - mx) * nx + (p[1] - mz) * nz), 1e-4);
}

/** World position of a winding's wire-width handle (midpoint + normal*half). */
function wireHandlePoint(start: Point, end: Point, half: number): Point {
  const dx = end[0] - start[0];
  const dz = end[1] - start[1];
  const len = Math.hypot(dx, dz) || 1;
  const nx = -dz / len;
  const nz = dx / len;
  return [(start[0] + end[0]) / 2 + nx * half, (start[1] + end[1]) / 2 + nz * half];
}

export interface ToScreen {
  (x: number, z: number): { x: number; y: number };
}

/** Touch pointers need a much larger hit target than the ~6px drawn handle,
 *  and a right-click equivalent. Detect a coarse pointer once at module load. */
const COARSE_POINTER =
  typeof window !== 'undefined' && !!window.matchMedia?.('(pointer: coarse)').matches;

/** How long a stationary finger must rest on a shape/handle to open its
 *  context menu (the touch stand-in for a right-click). */
const LONG_PRESS_MS = 500;
/** A press that drifts more than this (screen px) is a drag/tap, not a hold. */
const LONG_PRESS_SLOP = 10;

/**
 * Long-press detection for a Konva node: start a timer on touchstart, cancel
 * it if the finger drifts or lifts early, and fire `onLongPress` with the
 * touched node otherwise. Returns handlers to spread onto the node; a no-op
 * set on non-touch devices so nothing extra is wired up.
 */
function useKonvaLongPress(onLongPress: (node: Konva.Node) => void) {
  const timer = useRef<number | null>(null);
  const origin = useRef<{ x: number; y: number } | null>(null);

  const cancel = () => {
    if (timer.current !== null) {
      window.clearTimeout(timer.current);
      timer.current = null;
    }
    origin.current = null;
  };

  if (!COARSE_POINTER) return {};

  return {
    onTouchStart: (e: KonvaEventObject<TouchEvent>) => {
      const t = e.evt.touches[0];
      origin.current = t ? { x: t.clientX, y: t.clientY } : null;
      const node = e.target as Konva.Node;
      cancel();
      timer.current = window.setTimeout(() => {
        timer.current = null;
        onLongPress(node);
      }, LONG_PRESS_MS);
    },
    onTouchMove: (e: KonvaEventObject<TouchEvent>) => {
      const t = e.evt.touches[0];
      if (t && origin.current) {
        const drift = Math.hypot(t.clientX - origin.current.x, t.clientY - origin.current.y);
        if (drift > LONG_PRESS_SLOP) cancel();
      }
    },
    onTouchEnd: cancel,
  };
}

interface HandleProps {
  world: Point;
  toScreen: ToScreen;
  testId: string;
  colors: ThemeColors;
  /** Overrides the default handle fill (e.g. wire/vertex accents). */
  color?: string;
  onDrag: (world: Point) => void;
  onContextMenu: (evt: KonvaEventObject<PointerEvent>) => void;
}

const HANDLE_RADIUS = COARSE_POINTER ? 8 : 6;
/** Extra invisible hit padding around a handle so a fingertip can grab it
 *  without the dot itself having to be finger-sized. */
const HANDLE_HIT_STROKE = COARSE_POINTER ? 26 : undefined;

function Handle({ world, toScreen, testId, colors, color, onDrag, onContextMenu }: HandleProps) {
  const s = toScreen(world[0], world[1]);
  const longPress = useKonvaLongPress((node) =>
    onContextMenu({ target: node } as unknown as KonvaEventObject<PointerEvent>),
  );
  return (
    <Circle
      x={s.x}
      y={s.y}
      radius={HANDLE_RADIUS}
      hitStrokeWidth={HANDLE_HIT_STROKE}
      fill={color ?? colors.handleFill}
      stroke={colors.handleStroke}
      strokeWidth={1}
      draggable
      name={testId}
      onDragMove={(e) => {
        const stage = e.target.getStage();
        const pos = stage?.getPointerPosition();
        if (!pos) return;
        // Forward the raw screen point; the parent converts it via fromScreen.
        onDrag([pos.x, pos.y]);
      }}
      onContextMenu={(e) => {
        e.evt.preventDefault();
        onContextMenu(e as unknown as KonvaEventObject<PointerEvent>);
      }}
      onMouseEnter={(e) => {
        const c = e.target.getStage()?.container();
        if (c) c.style.cursor = 'grab';
      }}
      onMouseLeave={(e) => {
        const c = e.target.getStage()?.container();
        if (c) c.style.cursor = 'default';
      }}
      {...longPress}
    />
  );
}

interface OutlineProps {
  points: Point[];
  toScreen: ToScreen;
  stroke: string;
  fill?: string;
  selected: boolean;
  /** Mouse press on the body: selects and arms a body-drag move. `additive`
   *  is true when Shift is held (toggle into a multi-select). */
  onBodyDown: (additive: boolean, evt: KonvaEventObject<MouseEvent>) => void;
  /** Touch tap on the body (no drag-move on touch): select only. */
  onSelect: (additive: boolean) => void;
  onContextMenu: (evt: KonvaEventObject<PointerEvent>) => void;
  testId: string;
  closed?: boolean;
}

/** Invisible hit padding (screen px) around thin outlines. A bare secondary
 *  capsule is sub-pixel wide on screen, so without this its clickable area is
 *  effectively nothing; this fattens the hit region without changing the
 *  drawn stroke. Touch pointers get an even wider band. */
const HIT_STROKE = COARSE_POINTER ? 24 : 14;

function Outline({
  points,
  toScreen,
  stroke,
  fill,
  selected,
  onBodyDown,
  onSelect,
  onContextMenu,
  testId,
  closed = true,
}: OutlineProps) {
  const longPress = useKonvaLongPress((node) =>
    onContextMenu({ target: node } as unknown as KonvaEventObject<PointerEvent>),
  );
  // Both the +r outline and its mirror are interactive, so a press on either
  // arm of the mirrored cross-section selects/moves the component (mouse), taps
  // to select (touch), or long-presses for the context menu (touch).
  //
  // Mouse press arms a body-drag move; touch tap only selects (touch body-drag
  // would fight one-finger canvas panning), and a touch long-press opens the
  // context menu.
  const draw = (pts: Point[], primary: boolean, key: string) => (
    <Line
      key={key}
      name={primary ? testId : `${testId}-mirror`}
      points={toFlatScreen(pts, toScreen)}
      closed={closed}
      stroke={stroke}
      strokeWidth={selected ? 2.5 : 1.5}
      hitStrokeWidth={HIT_STROKE}
      fill={fill}
      onMouseDown={(e) => {
        if (e.evt.button === 0) onBodyDown(e.evt.shiftKey, e);
      }}
      onTap={() => onSelect(false)}
      onContextMenu={(e) => {
        e.evt.preventDefault();
        onContextMenu(e as unknown as KonvaEventObject<PointerEvent>);
      }}
      {...longPress}
    />
  );
  return (
    <>
      {draw(points, true, 'r')}
      {draw(mirrorX(points), false, 'l')}
    </>
  );
}

// ---------------------------------------------------------------------------

interface ComponentRenderProps<T> {
  data: T;
  target: ComponentRef;
  colors: ThemeColors;
  toScreen: ToScreen;
  fromScreen: (sx: number, sy: number) => Point;
  selected: boolean;
  onSelect: (ref: ComponentRef, additive: boolean) => void;
  onBodyDown: (ref: ComponentRef, additive: boolean, evt: KonvaEventObject<MouseEvent>) => void;
  onContextMenu: (
    evt: KonvaEventObject<PointerEvent>,
    target: ComponentRef,
    handle?: 'start' | 'end' | 'center' | 'radius' | 'vertex' | 'wire',
    vertexIndex?: number,
  ) => void;
  onPatch: (patch: Partial<T>) => void;
}

export function SecondaryShape(props: ComponentRenderProps<SecondarySchema>) {
  const { data, target, colors, toScreen, fromScreen, selected, onSelect, onBodyDown, onContextMenu, onPatch } =
    props;
  return (
    <>
      <Outline
        points={secondaryOutline(data)}
        toScreen={toScreen}
        stroke={colors.secondary.stroke}
        fill={colors.secondary.fill}
        selected={selected}
        onBodyDown={(additive, e) => onBodyDown(target, additive, e)}
        onSelect={(additive) => onSelect(target, additive)}
        onContextMenu={(e) => onContextMenu(e, target)}
        testId="shape-secondary"
      />
      {selected && (
        <>
          <Handle
            world={data.start}
            toScreen={toScreen}
            colors={colors}
            testId="handle-secondary-start"
            onDrag={(screen) => onPatch({ start: fromScreen(screen[0], screen[1]) })}
            onContextMenu={(e) => onContextMenu(e, target, 'start')}
          />
          <Handle
            world={data.end}
            toScreen={toScreen}
            colors={colors}
            testId="handle-secondary-end"
            onDrag={(screen) => onPatch({ end: fromScreen(screen[0], screen[1]) })}
            onContextMenu={(e) => onContextMenu(e, target, 'end')}
          />
          <Handle
            world={wireHandlePoint(data.start, data.end, data.wire_dia / 2)}
            toScreen={toScreen}
            colors={colors}
            testId="handle-secondary-wire"
            color={colors.secondary.handle}
            onDrag={(screen) =>
              onPatch({
                wire_dia:
                  2 * halfWidthFrom(data.start, data.end, fromScreen(screen[0], screen[1])),
              })
            }
            onContextMenu={(e) => onContextMenu(e, target, 'wire')}
          />
        </>
      )}
    </>
  );
}

/** The primary is drawn as the discrete per-turn rings the physics models,
 *  not a single swept band. The connecting centerline is hidden until the
 *  primary is hovered or selected; interaction (select / move / context menu)
 *  happens along that centerline, so the familiar "click and drag the line"
 *  gesture — including the start/end handles — is unchanged. */
export function PrimaryShape(props: ComponentRenderProps<PrimarySchema>) {
  const { data, target, colors, toScreen, fromScreen, selected, onSelect, onBodyDown, onContextMenu, onPatch } =
    props;
  const width =
    data.cross_section.kind === 'circular'
      ? data.cross_section.diameter
      : data.cross_section.width;
  const palette = colors.materials[data.material];
  const rings = primaryRingOutlines(data);
  const centerline: Point[] = [data.start, data.end];
  const [hovered, setHovered] = useState(false);
  const showCenterline = hovered || selected;

  const capsule = secondaryOutline({ ...data, wire_dia: width } as unknown as SecondarySchema);

  const longPress = useKonvaLongPress((node) =>
    onContextMenu({ target: node } as unknown as KonvaEventObject<PointerEvent>, target),
  );

  // Invisible filled capsule along each arm of the winding: the primary's hit
  // region. A press selects/moves it (mouse), a tap selects (touch), a
  // right-click / long-press opens its menu, and hovering reveals the
  // connecting centerline. A near-zero-alpha fill makes the whole band
  // hit-testable (a filled area is a reliable Konva hit target) without
  // drawing anything visible.
  const hitCapsule = (pts: Point[], key: string, primary: boolean) => (
    <Line
      key={key}
      name={primary ? 'shape-primary' : 'shape-primary-mirror'}
      points={toFlatScreen(pts, toScreen)}
      closed
      fill="rgba(0,0,0,0.001)"
      hitStrokeWidth={HIT_STROKE}
      onMouseDown={(e) => {
        if (e.evt.button === 0) onBodyDown(target, e.evt.shiftKey, e);
      }}
      onTap={() => onSelect(target, false)}
      onMouseEnter={(e) => {
        setHovered(true);
        const c = e.target.getStage()?.container();
        if (c) c.style.cursor = 'pointer';
      }}
      onMouseLeave={(e) => {
        setHovered(false);
        const c = e.target.getStage()?.container();
        if (c) c.style.cursor = 'default';
      }}
      onContextMenu={(e) => {
        e.evt.preventDefault();
        onContextMenu(e as unknown as KonvaEventObject<PointerEvent>, target);
      }}
      {...longPress}
    />
  );

  return (
    <>
      {/* Per-turn ring cross-sections (both arms of the mirror). */}
      {[false, true].map((mirror) =>
        rings.map((poly, i) => (
          <Line
            key={`ring-${mirror ? 'l' : 'r'}-${i}`}
            points={toFlatScreen(mirror ? mirrorX(poly) : poly, toScreen)}
            closed
            stroke={palette.stroke}
            strokeWidth={selected ? 2 : 1.5}
            fill={palette.fill}
            listening={false}
          />
        )),
      )}

      {/* Connecting centerline (both arms), revealed on hover / selection, in
          the accent color so it reads as one winding threaded through the
          rings (drawn over them, not the same color as the copper). */}
      {showCenterline &&
        [centerline, mirrorX(centerline)].map((pts, i) => (
          <Line
            key={`center-${i}`}
            points={toFlatScreen(pts, toScreen)}
            stroke={colors.handleFill}
            strokeWidth={1.5}
            dash={[6, 5]}
            opacity={0.9}
            listening={false}
          />
        ))}

      {hitCapsule(capsule, 'hit-r', true)}
      {hitCapsule(mirrorX(capsule), 'hit-l', false)}

      {selected && (
        <>
          <Handle
            world={data.start}
            toScreen={toScreen}
            colors={colors}
            testId="handle-primary-start"
            onDrag={(screen) => onPatch({ start: fromScreen(screen[0], screen[1]) })}
            onContextMenu={(e) => onContextMenu(e, target, 'start')}
          />
          <Handle
            world={data.end}
            toScreen={toScreen}
            colors={colors}
            testId="handle-primary-end"
            onDrag={(screen) => onPatch({ end: fromScreen(screen[0], screen[1]) })}
            onContextMenu={(e) => onContextMenu(e, target, 'end')}
          />
          <Handle
            world={wireHandlePoint(data.start, data.end, width / 2)}
            toScreen={toScreen}
            colors={colors}
            testId="handle-primary-wire"
            color={palette.handle}
            onDrag={(screen) => {
              const w = 2 * halfWidthFrom(data.start, data.end, fromScreen(screen[0], screen[1]));
              onPatch({
                cross_section:
                  data.cross_section.kind === 'circular'
                    ? { kind: 'circular', diameter: w }
                    : { kind: 'rectangular', width: w, height: data.cross_section.height },
              });
            }}
            onContextMenu={(e) => onContextMenu(e, target, 'wire')}
          />
        </>
      )}
    </>
  );
}

export function ConductorShape(
  props: ComponentRenderProps<ToploadSchema | GroundSchema> & {
    testId: string;
  },
) {
  const {
    data,
    target,
    colors,
    toScreen,
    fromScreen,
    selected,
    onSelect,
    onBodyDown,
    onContextMenu,
    onPatch,
    testId,
  } = props;
  const { stroke, fill } = colors.materials[data.material];
  return (
    <>
      <Outline
        points={shapeOutline(data.shape)}
        toScreen={toScreen}
        stroke={stroke}
        fill={fill}
        selected={selected}
        onBodyDown={(additive, e) => onBodyDown(target, additive, e)}
        onSelect={(additive) => onSelect(target, additive)}
        onContextMenu={(e) => onContextMenu(e, target)}
        testId={testId}
      />
      {selected && (
        <>
          {/* The body itself is draggable to move the shape (see CoilCanvas);
              the handles here only resize/reshape. */}
          {data.shape.kind === 'circle' && (
            <Handle
              world={[data.shape.center[0] + data.shape.radius, data.shape.center[1]]}
              toScreen={toScreen}
              colors={colors}
              testId={`${testId}-radius`}
              onDrag={(screen) => {
                const w = fromScreen(screen[0], screen[1]);
                const center: Point = data.shape.kind === 'circle' ? data.shape.center : [0, 0];
                const r = Math.max(
                  Math.hypot(w[0] - center[0], w[1] - center[1]),
                  1e-4,
                );
                if (data.shape.kind === 'circle') {
                  onPatch({ shape: { ...data.shape, radius: r } } as Partial<
                    ToploadSchema | GroundSchema
                  >);
                }
              }}
              onContextMenu={(e) => onContextMenu(e, target, 'radius')}
            />
          )}
          {/* One draggable handle per polygon/rectangle vertex. */}
          {shapeVertices(data.shape).map((v, i) => (
            <Handle
              key={`v-${i}`}
              world={v}
              toScreen={toScreen}
              colors={colors}
              testId={`${testId}-vertex-${i}`}
              color={colors.vertexHandle}
              onDrag={(screen) =>
                onPatch({
                  shape: moveVertex(data.shape, i, fromScreen(screen[0], screen[1])),
                } as Partial<ToploadSchema | GroundSchema>)
              }
              onContextMenu={(e) => onContextMenu(e, target, 'vertex', i)}
            />
          ))}
        </>
      )}
    </>
  );
}
