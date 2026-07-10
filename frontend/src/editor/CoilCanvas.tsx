/**
 * The interactive editor canvas: a Konva stage rendering the coil as a
 * mirrored (r, z) cross-section. Pan/zoom and placement are driven through
 * the shared Viewport, which every layer (and the future field solve) reads.
 */
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { Layer, Line, Rect, Stage, Text } from 'react-konva';
import type Konva from 'konva';
import type { KonvaEventObject } from 'konva/lib/Node';

import type { CoilSchema } from '../api/client';
import { useField } from '../api/simulation';
import type { ComponentRef, Point, Tool } from '../domain/coil';
import { isSelected } from '../domain/coil';
import { FieldLayer } from '../field/FieldLayer';
import { FIELD_GRID_NR, FIELD_GRID_NZ, useEditorStore } from '../state/store';
import type { HandleKind } from '../state/store';
import { useThemeColors } from '../theme';
import { rectFromCorners } from './geometry';
import { pointInSelection, refsInRect } from './selection';
import {
  ConductorShape,
  PrimaryShape,
  SecondaryShape,
  type ToScreen,
} from './shapes';
import {
  domainBounds,
  fitBounds,
  pan,
  screenToWorld,
  worldToScreen,
  zoomAbout,
  type Viewport,
} from './viewport';

interface Size {
  width: number;
  height: number;
}

/** A press that moves less than this (screen px) is a click, not a drag. */
const DRAG_THRESHOLD = 3;

/** A finger that moves less than this (screen px) between touchstart and
 *  touchend is treated as a tap, not a pan. */
const TOUCH_TAP_SLOP = 8;

/** A screen-space rectangle (the marquee box, drawn in stage coordinates). */
interface ScreenRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

/** Normalized screen rectangle spanning two corner points. */
function screenRect(
  a: { x: number; y: number },
  b: { x: number; y: number },
): ScreenRect {
  return {
    x: Math.min(a.x, b.x),
    y: Math.min(a.y, b.y),
    width: Math.abs(a.x - b.x),
    height: Math.abs(a.y - b.y),
  };
}

/** The placement tools add a component on click, then revert to pan. `pan` and
 *  `select` are the two interaction modes; everything else places. */
const isPlacementTool = (t: Tool): boolean => t !== 'pan' && t !== 'select';

/** Whether the primary input is touch-like (finger/stylus) rather than a
 *  mouse. Drives the on-canvas hint text; the gesture handlers themselves key
 *  off the actual event type, so a hybrid device supports both. */
const isCoarsePointer = () =>
  typeof window !== 'undefined' && !!window.matchMedia?.('(pointer: coarse)').matches;

/** Live multi-touch gesture bookkeeping (kept in a ref so rapid touchmove
 *  events never race React state). One-finger drags on empty space pan; two
 *  fingers pinch-zoom (and pan by their midpoint). */
interface TouchGesture {
  mode: 'none' | 'pan' | 'pinch' | 'move' | 'marquee';
  /** Last one-finger position, for incremental panning. */
  panLast: { x: number; y: number } | null;
  /** Last one-finger world position, for incremental moving of the selection. */
  moveLastWorld: Point | null;
  /** Last two-finger separation and midpoint, for incremental pinch-zoom. */
  pinchDist: number;
  pinchMid: { x: number; y: number } | null;
  /** Where the first finger went down, to tell a tap from a drag. */
  startPos: { x: number; y: number } | null;
  startOnBackground: boolean;
  moved: boolean;
}

/** A Touch's position relative to the Konva stage's container (canvas px). */
function touchToStage(
  stage: Konva.Stage,
  touch: Touch,
): { x: number; y: number } {
  const rect = stage.container().getBoundingClientRect();
  return { x: touch.clientX - rect.left, y: touch.clientY - rect.top };
}

export function CoilCanvas() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState<Size>({ width: 800, height: 600 });
  const [viewport, setViewport] = useState<Viewport | null>(null);
  // A single mouse gesture, resolved lazily. On press it is `idle`; on the
  // first real move it becomes `pan`, `move`, or `marquee` based on the tool
  // and what was pressed. On release without a move it is a click (select /
  // clear / place). One state machine, so click-select works in every mode.
  const gesture = useRef<{
    startScreen: { x: number; y: number };
    /** The component under the initial press, or null for empty background. */
    ref: ComponentRef | null;
    /** Shift held at press (adds to / toggles the selection). */
    additive: boolean;
    mode: 'idle' | 'pan' | 'move' | 'marquee';
    /** Last pointer position, for incremental pan (screen) and move (world). */
    lastScreen: { x: number; y: number };
    lastWorld: Point;
  } | null>(null);
  /** The marquee rectangle to draw while box-selecting (screen coords). */
  const [marquee, setMarquee] = useState<ScreenRect | null>(null);
  const [spaceHeld, setSpaceHeld] = useState(false);
  // Touch gesture state (pan/pinch) and the latest viewport mirrored into a
  // ref, so a burst of touchmove events reads the freshest transform instead
  // of a stale render closure.
  const touch = useRef<TouchGesture>({
    mode: 'none',
    panLast: null,
    moveLastWorld: null,
    pinchDist: 0,
    pinchMid: null,
    startPos: null,
    startOnBackground: false,
    moved: false,
  });
  const vpRef = useRef<Viewport | null>(null);
  const coarsePointer = useMemo(isCoarsePointer, []);

  const colors = useThemeColors();
  const coil = useEditorStore((s) => s.coil);
  const selection = useEditorStore((s) => s.selection);
  const tool = useEditorStore((s) => s.tool);
  const placementShape = useEditorStore((s) => s.placementShape);
  const select = useEditorStore((s) => s.select);
  const setSelection = useEditorStore((s) => s.setSelection);
  const toggleSelect = useEditorStore((s) => s.toggleSelect);
  const translateSelection = useEditorStore((s) => s.translateSelection);
  const deleteSelected = useEditorStore((s) => s.deleteSelected);
  const setTool = useEditorStore((s) => s.setTool);
  const updateSecondary = useEditorStore((s) => s.updateSecondary);
  const updatePrimary = useEditorStore((s) => s.updatePrimary);
  const updateTopload = useEditorStore((s) => s.updateTopload);
  const updateGround = useEditorStore((s) => s.updateGround);
  const addTopload = useEditorStore((s) => s.addTopload);
  const addGround = useEditorStore((s) => s.addGround);
  const addPrimary = useEditorStore((s) => s.addPrimary);
  const openContextMenu = useEditorStore((s) => s.openContextMenu);
  const closeContextMenu = useEditorStore((s) => s.closeContextMenu);
  const viewMode = useEditorStore((s) => s.viewMode);
  const fieldDrive = useEditorStore((s) => s.fieldDrive);
  const fieldDisplay = useEditorStore((s) => s.fieldDisplay);
  const bundle = useEditorStore((s) => s.bundle);
  const analysis = useEditorStore((s) => s.analysis);
  const fieldMode = viewMode !== 'edit';

  // Effective drive frequency: the user's value, or the lower split mode
  // (falling back to the secondary resonance) when left at 0 ("auto").
  const effectiveFreq =
    fieldDrive.frequencyHz > 0
      ? fieldDrive.frequencyHz
      : (analysis?.coupled?.split_lower ?? analysis?.secondary.resonant_frequency ?? 0);

  const fieldQuery = useField(
    coil as unknown as CoilSchema,
    bundle,
    {
      fieldType: viewMode === 'bfield' ? 'magnetic' : 'electric',
      frequencyHz: effectiveFreq,
      primaryCurrent: fieldDrive.primaryCurrent,
      referenceMode: fieldDrive.referenceMode,
      hotEnd: fieldDrive.hotEnd,
      gridNr: FIELD_GRID_NR,
      gridNz: FIELD_GRID_NZ,
    },
    fieldMode,
  );

  // Track container size.
  useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const update = () =>
      setSize({ width: el.clientWidth, height: el.clientHeight });
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Initialize the viewport once we know the size.
  useEffect(() => {
    if (!viewport && size.width > 0) {
      setViewport(fitBounds(domainBounds(coil.r_max, coil.z_max), size));
    }
  }, [viewport, size, coil.r_max, coil.z_max]);

  const vp = viewport ?? fitBounds(domainBounds(coil.r_max, coil.z_max), size);
  // Mirror the current transform so the imperative touch handlers always start
  // from the freshest viewport (React may batch several touchmoves per frame).
  vpRef.current = vp;

  const toScreen = useCallback<ToScreen>(
    (x, z) => worldToScreen(vp, x, z),
    [vp],
  );
  const fromScreen = useCallback(
    (sx: number, sy: number): Point => {
      const w = screenToWorld(vp, sx, sy);
      return [w.x, w.z];
    },
    [vp],
  );

  // Expose a tiny transform API for Playwright to compute handle coordinates.
  useEffect(() => {
    (window as unknown as { __editor?: unknown }).__editor = {
      worldToScreen: (x: number, z: number) => worldToScreen(vp, x, z),
      screenToWorld: (sx: number, sy: number) => screenToWorld(vp, sx, sy),
      viewport: vp,
    };
  }, [vp]);

  // Canvas keyboard shortcuts: Space (hold) to pan, Escape to cancel an armed
  // tool (select/placement, back to the pan default) or else clear the
  // selection, and Delete/Backspace to remove the selected components. Skipped
  // while a form field is focused so typing is unaffected.
  useEffect(() => {
    const isEditable = (el: EventTarget | null) =>
      el instanceof HTMLElement &&
      (el.tagName === 'INPUT' ||
        el.tagName === 'TEXTAREA' ||
        el.tagName === 'SELECT' ||
        el.isContentEditable);

    const onKeyDown = (e: KeyboardEvent) => {
      if (isEditable(e.target)) return;
      if (e.key === ' ') {
        setSpaceHeld(true);
        e.preventDefault();
      } else if (e.key === 'Escape') {
        // Back out of any armed tool first; once in pan, clear the selection.
        if (useEditorStore.getState().tool !== 'pan') setTool('pan');
        else select(null);
      } else if (e.key === 'Delete' || e.key === 'Backspace') {
        deleteSelected();
        e.preventDefault();
      }
    };
    const onKeyUp = (e: KeyboardEvent) => {
      if (e.key === ' ') setSpaceHeld(false);
    };
    window.addEventListener('keydown', onKeyDown);
    window.addEventListener('keyup', onKeyUp);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('keyup', onKeyUp);
    };
  }, [select, deleteSelected, setTool]);

  const onWheel = (e: KonvaEventObject<WheelEvent>) => {
    e.evt.preventDefault();
    const stage = e.target.getStage();
    const pos = stage?.getPointerPosition();
    if (!pos) return;
    const factor = e.evt.deltaY < 0 ? 1.1 : 1 / 1.1;
    setViewport(zoomAbout(vp, pos.x, pos.y, factor));
  };

  const bgName = 'canvas-background';

  const placeAt = (world: Point) => {
    if (tool === 'topload') addTopload(world, coil.z_max * 0.04 || 2, placementShape);
    else if (tool === 'ground') addGround(world, coil.z_max * 0.03 || 1.5, placementShape);
    else if (tool === 'primary')
      addPrimary(world, [world[0] + coil.r_max * 0.05, world[1]]);
    else if (tool === 'secondary')
      updateSecondary({ start: world, end: [world[0], world[1] + coil.z_max * 0.15] });
    setTool('pan');
  };

  /** Begin a mouse gesture from a press. `ref` is the component pressed, or
   *  null for the background; `mode` is `pan` for an immediate pan (Space /
   *  middle button / field view), else `idle` (resolved on the first move). */
  const beginGesture = (
    pos: { x: number; y: number },
    ref: ComponentRef | null,
    additive: boolean,
    mode: 'idle' | 'pan',
  ) => {
    gesture.current = {
      startScreen: pos,
      ref,
      additive,
      mode,
      lastScreen: pos,
      lastWorld: fromScreen(pos.x, pos.y),
    };
  };

  const setCursor = (stage: Konva.Stage | null, cursor: string) => {
    const c = stage?.container();
    if (c) c.style.cursor = cursor;
  };

  /** Touch tap on a component body → select it (any mode). Mouse selection is
   *  handled by the gesture machine below; this is the touch (Konva `tap`) path. */
  const handleSelect = useCallback(
    (ref: ComponentRef, additive: boolean) => {
      if (useEditorStore.getState().viewMode !== 'edit') return;
      if (additive) toggleSelect(ref);
      else select(ref);
      // One-shot: a tap-select in select mode drops back to pan so the tapped
      // component can be dragged.
      const s = useEditorStore.getState();
      if (s.tool === 'select' && s.selection.length > 0) setTool('pan');
    },
    [select, toggleSelect, setTool],
  );

  /** Mouse press on a component body: begin an idle gesture carrying its ref.
   *  What happens (select / move / box-select) is decided on move / release. */
  const handleBodyDown = (
    ref: ComponentRef,
    additive: boolean,
    e: KonvaEventObject<MouseEvent>,
  ) => {
    if (spaceHeld || e.evt.button !== 0 || fieldMode) return; // stage handles pan / field
    closeContextMenu();
    const pos = e.target.getStage()?.getPointerPosition();
    if (pos) beginGesture(pos, ref, additive, 'idle');
  };

  const onMouseDown = (e: KonvaEventObject<MouseEvent>) => {
    const targetName = e.target.name();
    const onBackground = e.target === e.target.getStage() || targetName === bgName;
    const stage = e.target.getStage();
    const pos = stage?.getPointerPosition();
    if (!pos) return;

    // Field views are pan/zoom only; any left/middle press pans.
    if (fieldMode) {
      if (e.evt.button === 0 || e.evt.button === 1) {
        beginGesture(pos, null, false, 'pan');
        e.evt.preventDefault();
      }
      return;
    }
    // Middle button or Space pans immediately from anywhere (even over a body).
    if (e.evt.button === 1 || spaceHeld) {
      beginGesture(pos, null, false, 'pan');
      e.evt.preventDefault();
      return;
    }
    // A body press is handled by handleBodyDown (fires first, on the shape);
    // here we only start the background gesture.
    if (e.evt.button !== 0 || !onBackground) return;
    closeContextMenu();
    beginGesture(pos, null, e.evt.shiftKey, 'idle');
  };

  const onMouseMove = (e: KonvaEventObject<MouseEvent>) => {
    const g = gesture.current;
    if (!g) return;
    const stage = e.target.getStage();
    const pos = stage?.getPointerPosition();
    if (!pos) return;

    // Resolve the drag intent on the first move past the click threshold.
    if (g.mode === 'idle') {
      const movedEnough =
        Math.abs(pos.x - g.startScreen.x) + Math.abs(pos.y - g.startScreen.y) > DRAG_THRESHOLD;
      if (!movedEnough) return;
      if (tool === 'select') {
        g.mode = 'marquee'; // box-select
      } else if (g.ref && !isPlacementTool(tool)) {
        // Pan mode dragging a component moves it — selecting it first if the
        // drag didn't start on the existing selection.
        if (!isSelected(selection, g.ref)) select(g.ref);
        g.mode = 'move';
        setCursor(stage, 'grabbing');
      } else {
        g.mode = 'pan'; // pan mode / placement: drag the viewport
      }
    }

    if (g.mode === 'pan') {
      const dx = pos.x - g.lastScreen.x;
      const dy = pos.y - g.lastScreen.y;
      g.lastScreen = pos;
      setViewport(pan(vp, dx, dy));
    } else if (g.mode === 'move') {
      const world = fromScreen(pos.x, pos.y);
      translateSelection(world[0] - g.lastWorld[0], world[1] - g.lastWorld[1]);
      g.lastWorld = world;
    } else if (g.mode === 'marquee') {
      setMarquee(screenRect(g.startScreen, pos));
    }
  };

  const onMouseUp = (e: KonvaEventObject<MouseEvent>) => {
    const g = gesture.current;
    gesture.current = null;
    setMarquee(null);
    setCursor(e.target.getStage(), spaceHeld ? 'grab' : tool === 'pan' ? 'default' : 'crosshair');
    if (!g) return;
    const wasSelect = tool === 'select';

    if (g.mode === 'idle') {
      // A click (no significant drag).
      if (isPlacementTool(tool)) {
        placeAt(fromScreen(g.startScreen.x, g.startScreen.y));
      } else if (g.ref) {
        if (g.additive) toggleSelect(g.ref);
        else select(g.ref);
      } else if (!g.additive) {
        select(null); // click on empty space clears the selection
      }
    } else if (g.mode === 'marquee') {
      const pos = e.target.getStage()?.getPointerPosition() ?? g.lastScreen;
      const hits = refsInRect(
        coil,
        rectFromCorners(fromScreen(g.startScreen.x, g.startScreen.y), fromScreen(pos.x, pos.y)),
      );
      if (g.additive) {
        const merged = [...selection];
        for (const ref of hits) if (!isSelected(merged, ref)) merged.push(ref);
        setSelection(merged);
      } else {
        setSelection(hits);
      }
    }
    // 'pan' and 'move' need no finalization.

    // Select is a one-shot box tool: once a selection has been made, drop back
    // to pan so the user can immediately drag what they selected. (A gesture
    // that selected nothing — e.g. an empty box — stays in select mode.)
    if (wasSelect && useEditorStore.getState().selection.length > 0) setTool('pan');
  };

  // --- Touch gestures --------------------------------------------------------
  // Konva raises touch events separately from mouse events, so these never
  // interfere with the mouse marquee/pan path above. One finger on empty space
  // pans; two fingers pinch-zoom (and pan by their midpoint); a finger that
  // barely moves is a tap — deselecting, or placing when a tool is armed.
  // Selecting a component and dragging its handles are handled by the shapes
  // themselves (Konva `tap` and native touch dragging).
  const applyViewport = (next: Viewport) => {
    vpRef.current = next;
    setViewport(next);
  };

  const onTouchStart = (e: KonvaEventObject<TouchEvent>) => {
    const stage = e.target.getStage();
    if (!stage) return;
    const touches = e.evt.touches;
    const st = touch.current;
    st.moved = false;

    if (touches.length >= 2) {
      const a = touches[0];
      const b = touches[1];
      if (!a || !b) return;
      const pa = touchToStage(stage, a);
      const pb = touchToStage(stage, b);
      st.mode = 'pinch';
      st.pinchDist = Math.hypot(pa.x - pb.x, pa.y - pb.y) || 1;
      st.pinchMid = { x: (pa.x + pb.x) / 2, y: (pa.y + pb.y) / 2 };
      e.evt.preventDefault();
      return;
    }

    const t = touches[0];
    if (!t) return;
    const p = touchToStage(stage, t);
    const node = e.target;
    const onBackground = node === stage || node.name() === bgName;
    // A draggable handle owns its own touch (resize/reshape); let Konva drive
    // dragging / the long-press context menu there.
    const isHandle = typeof node.draggable === 'function' && node.draggable();
    st.startPos = p;
    st.startOnBackground = onBackground;
    st.pinchMid = null;
    if (isHandle) {
      st.mode = 'none';
      st.panLast = null;
      return;
    }
    closeContextMenu();
    st.panLast = p;
    // Resolve the one-finger gesture. Select tool → box-select (marquee); pan
    // mode on an already-selected body → move it; otherwise pan. A stationary
    // press is a tap: Konva `tap` selects a component (any edit mode) and
    // onTouchEnd handles background taps (clear / place). Field views pan only.
    if (fieldMode) {
      st.mode = 'pan';
    } else if (tool === 'select') {
      st.mode = 'marquee';
    } else if (
      tool === 'pan' &&
      !onBackground &&
      pointInSelection(coil, selection, fromScreen(p.x, p.y))
    ) {
      st.mode = 'move';
      st.moveLastWorld = fromScreen(p.x, p.y);
    } else {
      st.mode = 'pan';
    }
  };

  const onTouchMove = (e: KonvaEventObject<TouchEvent>) => {
    const stage = e.target.getStage();
    if (!stage || !vpRef.current) return;
    const touches = e.evt.touches;
    const st = touch.current;

    if (touches.length >= 2) {
      const a = touches[0];
      const b = touches[1];
      if (!a || !b) return;
      const pa = touchToStage(stage, a);
      const pb = touchToStage(stage, b);
      const dist = Math.hypot(pa.x - pb.x, pa.y - pb.y) || 1;
      const mid = { x: (pa.x + pb.x) / 2, y: (pa.y + pb.y) / 2 };
      // A second finger may arrive mid-gesture; (re)seed the pinch baseline.
      if (st.mode !== 'pinch' || !st.pinchMid) {
        st.mode = 'pinch';
        st.pinchDist = dist;
        st.pinchMid = mid;
        return;
      }
      const zoomed = zoomAbout(vpRef.current, mid.x, mid.y, dist / st.pinchDist);
      applyViewport(pan(zoomed, mid.x - st.pinchMid.x, mid.y - st.pinchMid.y));
      st.pinchDist = dist;
      st.pinchMid = mid;
      st.moved = true;
      e.evt.preventDefault();
      return;
    }

    const t = touches[0];
    if (!t) return;
    const p = touchToStage(stage, t);
    const dragged =
      st.startPos && Math.hypot(p.x - st.startPos.x, p.y - st.startPos.y) > TOUCH_TAP_SLOP;

    if (st.mode === 'move' && st.moveLastWorld) {
      if (dragged) st.moved = true;
      const world = fromScreen(p.x, p.y);
      translateSelection(world[0] - st.moveLastWorld[0], world[1] - st.moveLastWorld[1]);
      st.moveLastWorld = world;
      e.evt.preventDefault();
      return;
    }

    if (st.mode === 'marquee' && st.startPos) {
      if (dragged) st.moved = true;
      st.panLast = p;
      setMarquee(screenRect(st.startPos, p));
      e.evt.preventDefault();
      return;
    }

    if (st.mode === 'pan' && st.panLast) {
      if (dragged) st.moved = true;
      applyViewport(pan(vpRef.current, p.x - st.panLast.x, p.y - st.panLast.y));
      st.panLast = p;
      e.evt.preventDefault();
    }
  };

  const onTouchEnd = (e: KonvaEventObject<TouchEvent>) => {
    const stage = e.target.getStage();
    const st = touch.current;
    const remaining = e.evt.touches;

    // Still pinching (a finger lifted but at least two remain).
    if (remaining.length >= 2) return;

    // Dropped from two fingers to one: continue as a pan with the finger left
    // on the glass (and never treat the lift as a tap).
    if (remaining.length === 1) {
      const t = remaining[0];
      if (stage && t) {
        st.mode = 'pan';
        st.panLast = touchToStage(stage, t);
      }
      st.pinchMid = null;
      st.moved = true;
      return;
    }

    // Finalize a box-select drag: select every component the marquee touched.
    if (st.mode === 'marquee' && st.moved && st.startPos && st.panLast && !fieldMode) {
      const hits = refsInRect(
        coil,
        rectFromCorners(
          fromScreen(st.startPos.x, st.startPos.y),
          fromScreen(st.panLast.x, st.panLast.y),
        ),
      );
      setSelection(hits);
      // One-shot: drop back to pan after a box-select so the group can be dragged.
      if (hits.length > 0) setTool('pan');
    }
    setMarquee(null);

    // All fingers up. A near-stationary one-finger press on empty space is a
    // background tap: place when a placement tool is armed, else clear the
    // selection. (Taps on a component are selected by Konva `tap` ->
    // handleSelect.) Field views ignore taps.
    const wasBackgroundTap =
      st.mode !== 'pinch' &&
      st.mode !== 'none' &&
      st.startOnBackground &&
      !st.moved &&
      st.startPos !== null;
    if (wasBackgroundTap && st.startPos && !fieldMode) {
      if (isPlacementTool(tool)) placeAt(fromScreen(st.startPos.x, st.startPos.y));
      else select(null);
    }
    st.mode = 'none';
    st.panLast = null;
    st.moveLastWorld = null;
    st.pinchMid = null;
    st.startPos = null;
    st.startOnBackground = false;
    st.moved = false;
  };

  const handleContextMenu = useCallback(
    (
      evt: KonvaEventObject<PointerEvent>,
      target: ComponentRef,
      handle?: HandleKind,
      vertexIndex?: number,
    ) => {
      const stage = (evt.target as Konva.Node).getStage();
      const pos = stage?.getPointerPosition();
      const container = stage?.container().getBoundingClientRect();
      if (!pos || !container) return;
      const world = fromScreen(pos.x, pos.y);
      select(target);
      openContextMenu({
        x: container.left + pos.x,
        y: container.top + pos.y,
        ref: target,
        handle,
        vertexIndex,
        world,
      });
    },
    [fromScreen, openContextMenu, select],
  );

  // Domain rectangle corners (mirrored: x in [-r_max, r_max]).
  const wall = (a: Point, b: Point) => [
    ...Object.values(toScreen(a[0], a[1])),
    ...Object.values(toScreen(b[0], b[1])),
  ];

  return (
    <div
      ref={containerRef}
      data-testid="coil-canvas"
      style={{
        width: '100%',
        height: '100%',
        background: colors.canvasBg,
        cursor: spaceHeld ? 'grab' : fieldMode || tool === 'pan' ? 'default' : 'crosshair',
        // Own every touch gesture: without this the browser would scroll/zoom
        // the page instead of letting us pan/pinch the canvas. Also suppress
        // the long-press callout and text selection so our own long-press menu
        // is the only thing that fires.
        touchAction: 'none',
        userSelect: 'none',
        WebkitUserSelect: 'none',
        WebkitTouchCallout: 'none',
      }}
    >
      <Stage
        width={size.width}
        height={size.height}
        onWheel={onWheel}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
      >
        <Layer>
          {/* Background hit target for pan/placement */}
          <Rect
            name={bgName}
            x={0}
            y={0}
            width={size.width}
            height={size.height}
            fill={colors.canvasBg}
          />
          {/* Domain walls */}
          <Line
            points={[
              ...wall([-coil.r_max, 0], [coil.r_max, 0]),
              ...wall([coil.r_max, coil.z_max], [-coil.r_max, coil.z_max]),
            ]}
            closed
            stroke={colors.wall}
            strokeWidth={1.5}
            listening={false}
          />
          {/* r = 0 symmetry axis */}
          <Line
            points={[...wall([0, 0], [0, coil.z_max])]}
            stroke={colors.axis}
            strokeWidth={1}
            dash={[6, 6]}
            listening={false}
          />
          <Text
            x={toScreen(0, coil.z_max).x + 6}
            y={toScreen(0, coil.z_max).y}
            text="axis (r=0)"
            fontSize={11}
            fill={colors.axisLabel}
            listening={false}
          />
          {/* Interaction hint, matched to the active input device. */}
          <Text
            x={10}
            y={size.height - 20}
            text={
              fieldMode
                ? coarsePointer
                  ? 'drag: pan · pinch: zoom'
                  : 'drag: pan · scroll: zoom'
                : isPlacementTool(tool)
                  ? coarsePointer
                    ? 'tap: place · esc: cancel'
                    : 'click: place · esc: cancel'
                  : tool === 'select'
                    ? coarsePointer
                      ? 'drag: box-select · tap: select · esc: exit'
                      : 'drag: box-select · click: select · esc: exit'
                    : coarsePointer
                      ? 'tap: select · drag: pan · pinch: zoom'
                      : 'click: select · drag: pan · scroll: zoom'
            }
            fontSize={11}
            fill={colors.axisLabel}
            listening={false}
          />
        </Layer>

        {fieldMode && fieldQuery.data && (
          <Layer listening={false}>
            <FieldLayer field={fieldQuery.data} toScreen={toScreen} display={fieldDisplay} />
          </Layer>
        )}

        <Layer listening={!fieldMode} opacity={fieldMode ? 0.55 : 1}>
          <SecondaryShape
            data={coil.secondary}
            target={{ kind: 'secondary' }}
            colors={colors}
            toScreen={toScreen}
            fromScreen={fromScreen}
            selected={isSelected(selection, { kind: 'secondary' })}
            onSelect={handleSelect}
            onBodyDown={handleBodyDown}
            onContextMenu={handleContextMenu}
            onPatch={updateSecondary}
          />
          {coil.primary && (
            <PrimaryShape
              data={coil.primary}
              target={{ kind: 'primary' }}
              colors={colors}
              toScreen={toScreen}
              fromScreen={fromScreen}
              selected={isSelected(selection, { kind: 'primary' })}
              onSelect={handleSelect}
              onBodyDown={handleBodyDown}
              onContextMenu={handleContextMenu}
              onPatch={updatePrimary}
            />
          )}
          {coil.toploads.map((t, i) => (
            <ConductorShape
              key={`topload-${i}`}
              data={t}
              target={{ kind: 'topload', index: i }}
              colors={colors}
              toScreen={toScreen}
              fromScreen={fromScreen}
              selected={isSelected(selection, { kind: 'topload', index: i })}
              onSelect={handleSelect}
              onBodyDown={handleBodyDown}
              onContextMenu={handleContextMenu}
              onPatch={(patch) => updateTopload(i, patch)}
              testId="shape-topload"
            />
          ))}
          {coil.grounds.map((g, i) => (
            <ConductorShape
              key={`ground-${i}`}
              data={g}
              target={{ kind: 'ground', index: i }}
              colors={colors}
              toScreen={toScreen}
              fromScreen={fromScreen}
              selected={isSelected(selection, { kind: 'ground', index: i })}
              onSelect={handleSelect}
              onBodyDown={handleBodyDown}
              onContextMenu={handleContextMenu}
              onPatch={(patch) => updateGround(i, patch)}
              testId="shape-ground"
            />
          ))}
          {/* Marquee box (screen space) while drag-selecting in select mode. */}
          {marquee && (marquee.width > 0 || marquee.height > 0) && (
            <Rect
              x={marquee.x}
              y={marquee.y}
              width={marquee.width}
              height={marquee.height}
              fill={colors.selectionFill}
              stroke={colors.handleFill}
              strokeWidth={1}
              dash={[4, 4]}
              listening={false}
            />
          )}
        </Layer>
      </Stage>
    </div>
  );
}
