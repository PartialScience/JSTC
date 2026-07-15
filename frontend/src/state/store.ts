/**
 * The single source of truth for the coil geometry and editor UI state.
 * The sidebar and canvas are both views of this store, so edits in either
 * place sync in real time.
 */
import { create } from 'zustand';

import type {
  AnalysisResponse,
  GroundSchema,
  MatrixBundle,
  PrimarySchema,
  SecondarySchema,
  ToploadSchema,
} from '../api/client';
import {
  clampToRightHalfPlane,
  defaultCoil,
  newGround,
  newPrimary,
  newSecondary,
  newTopload,
  toggleRef,
  type Coil,
  type ComponentRef,
  type Point,
  type Selection,
  type Tool,
} from '../domain/coil';
import { translateComponents } from '../editor/move';
import { convertShape, translateShape, type ShapeKind } from '../editor/shapeOps';
import {
  defaultUnitPrefs,
  type OutputUnitPref,
  type UnitPrefs,
  type UnitSystem,
} from '../units/units';

export type HandleKind = 'start' | 'end' | 'center' | 'radius' | 'vertex' | 'wire';

/** A copied component, held for paste. Only components that can have multiple
 *  instances (toploads, grounds) are copyable; a multi-selection copies
 *  several at once. */
export type ClipboardItem =
  | { kind: 'topload'; data: ToploadSchema }
  | { kind: 'ground'; data: GroundSchema };

export interface ContextMenuState {
  x: number;
  y: number;
  ref: ComponentRef;
  handle?: HandleKind;
  /** Vertex index, when the handle is a polygon/rectangle vertex. */
  vertexIndex?: number;
  /** World point of the handle, for exact numeric entry. */
  world?: Point;
}

export type ViewMode = 'edit' | '3d' | 'efield' | 'bfield';

/** The field overlays that require a computed solution (and so lock until a run
 *  has produced a bundle). '3d' is a pure geometry view and is not one. */
export const FIELD_VIEW_MODES: ViewMode[] = ['efield', 'bfield'];

export interface FieldDrive {
  frequencyHz: number;
  primaryCurrent: number;
  referenceMode: 'floating' | 'grounded';
  hotEnd: 'inner' | 'outer';
}

export interface FieldDisplay {
  colormap: 'intensity' | 'potential';
  showContours: boolean;
  showArrows: boolean;
}

export const DEFAULT_FIELD_DRIVE: FieldDrive = {
  frequencyHz: 0, // 0 = "use the coil's lower split mode" (resolved in the UI)
  primaryCurrent: 100,
  referenceMode: 'floating',
  hotEnd: 'outer',
};

export const DEFAULT_FIELD_DISPLAY: FieldDisplay = {
  colormap: 'intensity',
  showContours: true,
  showArrows: false,
};

/** Grid resolution for field requests (fixed; the client downsamples/renders). */
export const FIELD_GRID_NR = 120;
export const FIELD_GRID_NZ = 180;

export interface EditorState {
  coil: Coil;
  selection: Selection;
  tool: Tool;
  contextMenu: ContextMenuState | null;
  /** The geometry a topload/ground placement produces, chosen in the toolbar
   *  before clicking on the canvas (so placement never silently defaults). */
  placementShape: ShapeKind;
  /** Copied components, for paste (empty until something is copied). */
  clipboard: ClipboardItem[];
  /** Monotonic counter bumped on every geometry change, for change tracking. */
  revision: number;
  /** Undo/redo history of past and future coil states. */
  past: Coil[];
  future: Coil[];

  // --- Analysis session (lifted here so it is serializable and restorable
  // from one place: import/export round-trips the whole session, not just the
  // geometry). The bundle rides inside `analysis`; `bundle` mirrors it for the
  // fast impedance/SPICE endpoints. ---
  /** Last computed outputs, or null until the calculation is run. */
  analysis: AnalysisResponse | null;
  /** Cached FEM matrix bundle from the last run (= analysis.bundle). */
  bundle: MatrixBundle | null;
  /** The `revision` the current analysis corresponds to, or null if never
   *  run. `analyzedRevision !== revision` is the "results are stale" flag. */
  analyzedRevision: number | null;

  // Undo / redo
  undo: () => void;
  redo: () => void;

  // Selection & tool
  /** Select exactly one component, or clear the selection with `null`. */
  select: (ref: ComponentRef | null) => void;
  /** Replace the selection with an explicit list (marquee result). */
  setSelection: (refs: Selection) => void;
  /** Add/remove one component from the selection (shift-click). */
  toggleSelect: (ref: ComponentRef) => void;
  /** Translate every selected component by (dr, dz) as one rigid group,
   *  clamped so nothing crosses the r = 0 axis (body-drag move). */
  translateSelection: (dr: number, dz: number) => void;
  /** Delete every selected component that can be removed (primary, toploads,
   *  grounds). The secondary is mandatory and is left untouched. */
  deleteSelected: () => void;
  setTool: (tool: Tool) => void;

  // Field visualization
  /** 'edit' shows the interactive editor; 'efield'/'bfield' overlay the
   *  operating field (geometry shown but non-interactive). */
  viewMode: ViewMode;
  fieldDrive: FieldDrive;
  fieldDisplay: FieldDisplay;
  setViewMode: (mode: ViewMode) => void;
  setFieldDrive: (patch: Partial<FieldDrive>) => void;
  setFieldDisplay: (patch: Partial<FieldDisplay>) => void;

  // Context menu
  openContextMenu: (menu: ContextMenuState) => void;
  closeContextMenu: () => void;

  // Placement geometry (topload / ground)
  setPlacementShape: (kind: ShapeKind) => void;

  // Clipboard (used by the editor copy/paste keyboard shortcuts)
  /** Copy every selected topload/ground; no-op for singleton components. */
  copySelection: () => void;
  /** Paste the clipboard as new, offset, selected instances. */
  pasteClipboard: () => void;

  // Whole-coil scalar fields
  setDomain: (patch: Partial<Pick<Coil, 'r_max' | 'z_max'>>) => void;
  setDiscretizationOrder: (order: number) => void;

  // --- Display unit preferences (cosmetic; not undoable; round-tripped) ---
  /** Per-field input units, per-kind output units, and per-matrix units. All
   *  values are stored in SI base units; these only affect what is shown/typed. */
  unitPrefs: UnitPrefs;
  /** Set the display unit for one input field (keyed by a stable field id). */
  setInputUnit: (fieldId: string, unit: string) => void;
  /** Pin the display unit for one output value (keyed by a stable field id). */
  setOutputUnit: (fieldId: string, pref: OutputUnitPref) => void;
  /** Set the baseline output-unit system (Imperial/SI), clearing per-value pins. */
  setUnitSystem: (system: UnitSystem) => void;
  /** Set the display unit for one matrix ('geometric' or a physical unit). */
  setMatrixUnit: (key: string, unit: string) => void;

  // Secondary
  updateSecondary: (patch: Partial<SecondarySchema>) => void;

  // Primary
  addPrimary: (start: Point, end: Point) => void;
  updatePrimary: (patch: Partial<PrimarySchema>) => void;
  removePrimary: () => void;

  // Toploads
  addTopload: (center: Point, radius: number, kind?: ShapeKind) => void;
  updateTopload: (index: number, patch: Partial<ToploadSchema>) => void;
  removeTopload: (index: number) => void;

  // Grounds
  addGround: (center: Point, radius: number, kind?: ShapeKind) => void;
  updateGround: (index: number, patch: Partial<GroundSchema>) => void;
  removeGround: (index: number) => void;

  // Replace the whole coil (e.g. load a preset)
  setCoil: (coil: Coil) => void;

  // --- Analysis session ---
  /** Mark that a run started for `revision` (clears the stale flag optimistically
   *  while the solve is in flight), called by the analysis hook. */
  markRun: (revision: number) => void;
  /** Record a completed analysis (and its bundle) from the analysis hook. */
  recordAnalysis: (analysis: AnalysisResponse) => void;
  /** Load a whole session — geometry plus optional cached outputs — as one
   *  undoable step. Fresh outputs read as up-to-date; stale ones (or none) are
   *  flagged. Used by the top bar's Demo / New / Import actions. */
  loadSession: (session: {
    coil: Coil;
    analysis: AnalysisResponse | null;
    stale: boolean;
    /** Restored display units; omitted (Demo/New) resets to defaults. */
    unitPrefs?: UnitPrefs;
  }) => void;
}

const HISTORY_LIMIT = 100;
/** Consecutive edits within this window collapse into one undo step, so a
 *  handle drag (many onDragMove events) is a single undo, not hundreds. */
const COALESCE_MS = 400;
/** How far a pasted copy is offset from its source, as a fraction of the
 *  domain extent, so it lands clearly beside the original. */
const PASTE_OFFSET_FRAC = 0.04;

export const useEditorStore = create<EditorState>((set) => {
  let lastPush = 0;

  /** Record the current coil onto the undo stack (coalescing rapid bursts
   *  into one step) and clear the redo stack. */
  const pushHistory = (s: EditorState): Pick<EditorState, 'past' | 'future'> => {
    const now = Date.now();
    const coalesce = now - lastPush < COALESCE_MS && s.past.length > 0;
    lastPush = now;
    return {
      past: coalesce ? s.past : [...s.past, s.coil].slice(-HISTORY_LIMIT),
      future: [],
    };
  };

  /** Wrap a coil-mutating updater: apply it (clamped to the physical half-
   *  plane r >= 0), record history, bump revision, and clear the redo stack. */
  const mutate = (fn: (coil: Coil) => Coil) =>
    set((s) => ({
      coil: clampToRightHalfPlane(fn(s.coil)),
      ...pushHistory(s),
      revision: s.revision + 1,
    }));

  return {
    coil: defaultCoil(),
    viewMode: 'edit' as ViewMode,
    fieldDrive: { ...DEFAULT_FIELD_DRIVE },
    fieldDisplay: { ...DEFAULT_FIELD_DISPLAY },
    selection: [],
    tool: 'pan',
    contextMenu: null,
    placementShape: 'circle',
    clipboard: [],
    revision: 0,
    past: [],
    future: [],
    analysis: null,
    bundle: null,
    analyzedRevision: null,
    unitPrefs: defaultUnitPrefs(),

    undo: () =>
      set((s) => {
        if (s.past.length === 0) return {};
        lastPush = 0; // break coalescing across an undo
        const previous = s.past[s.past.length - 1]!;
        return {
          coil: previous,
          past: s.past.slice(0, -1),
          future: [s.coil, ...s.future].slice(0, HISTORY_LIMIT),
          revision: s.revision + 1,
          contextMenu: null,
        };
      }),
    redo: () =>
      set((s) => {
        if (s.future.length === 0) return {};
        lastPush = 0;
        const next = s.future[0]!;
        return {
          coil: next,
          past: [...s.past, s.coil].slice(-HISTORY_LIMIT),
          future: s.future.slice(1),
          revision: s.revision + 1,
          contextMenu: null,
        };
      }),

    select: (ref) => set({ selection: ref ? [ref] : [] }),
    setSelection: (refs) => set({ selection: refs }),
    toggleSelect: (ref) => set((s) => ({ selection: toggleRef(s.selection, ref) })),
    translateSelection: (dr, dz) =>
      set((s) => {
        const coil = translateComponents(s.coil, s.selection, dr, dz);
        if (coil === s.coil) return {}; // clamped to a no-op
        return {
          coil: clampToRightHalfPlane(coil),
          ...pushHistory(s),
          revision: s.revision + 1,
        };
      }),
    deleteSelected: () =>
      set((s) => {
        const delTop = new Set<number>();
        const delGnd = new Set<number>();
        let delPrimary = false;
        for (const ref of s.selection) {
          if (ref.kind === 'topload') delTop.add(ref.index);
          else if (ref.kind === 'ground') delGnd.add(ref.index);
          else if (ref.kind === 'primary') delPrimary = true;
        }
        if (!delPrimary && delTop.size === 0 && delGnd.size === 0) return {};
        lastPush = 0; // deletes are always their own undo step
        return {
          coil: {
            ...s.coil,
            primary: delPrimary ? null : s.coil.primary,
            toploads: s.coil.toploads.filter((_, i) => !delTop.has(i)),
            grounds: s.coil.grounds.filter((_, i) => !delGnd.has(i)),
          },
          past: [...s.past, s.coil].slice(-HISTORY_LIMIT),
          future: [],
          revision: s.revision + 1,
          selection: [],
          contextMenu: null,
        };
      }),
    setTool: (tool) => set({ tool }),

    setViewMode: (viewMode) =>
      // A field view clears the selection so no (now-inert) handles show over
      // the field, and closes any open context menu. The 2-D editor and the
      // 3-D viewer both keep the selection: the sidebar stays live in 3-D so
      // values can still be edited and seen updating in real time.
      set(
        FIELD_VIEW_MODES.includes(viewMode)
          ? { viewMode, selection: [], contextMenu: null }
          : { viewMode },
      ),
    setFieldDrive: (patch) =>
      set((s) => ({ fieldDrive: { ...s.fieldDrive, ...patch } })),
    setFieldDisplay: (patch) =>
      set((s) => ({ fieldDisplay: { ...s.fieldDisplay, ...patch } })),

    openContextMenu: (contextMenu) => set({ contextMenu }),
    closeContextMenu: () => set({ contextMenu: null }),

    setPlacementShape: (placementShape) => set({ placementShape }),

    copySelection: () =>
      set((s) => {
        const items: ClipboardItem[] = [];
        for (const ref of s.selection) {
          if (ref.kind === 'topload')
            items.push({ kind: 'topload', data: structuredClone(s.coil.toploads[ref.index]!) });
          else if (ref.kind === 'ground')
            items.push({ kind: 'ground', data: structuredClone(s.coil.grounds[ref.index]!) });
        }
        // Nothing copyable selected (e.g. only the singleton secondary/primary).
        return items.length ? { clipboard: items } : {};
      }),

    pasteClipboard: () =>
      set((s) => {
        if (s.clipboard.length === 0) return {};
        // Offset each copy (down-right) so it doesn't sit on its source, and
        // advance the clipboard to the copies so repeated pastes cascade.
        const dr = s.coil.r_max * PASTE_OFFSET_FRAC;
        const dz = -s.coil.z_max * PASTE_OFFSET_FRAC;
        let toploads = s.coil.toploads;
        let grounds = s.coil.grounds;
        const selection: ComponentRef[] = [];
        const nextClipboard: ClipboardItem[] = [];
        for (const clip of s.clipboard) {
          const data = { ...clip.data, shape: translateShape(clip.data.shape, dr, dz) };
          if (clip.kind === 'topload') {
            toploads = [...toploads, data as ToploadSchema];
            selection.push({ kind: 'topload', index: toploads.length - 1 });
            nextClipboard.push({ kind: 'topload', data: data as ToploadSchema });
          } else {
            grounds = [...grounds, data as GroundSchema];
            selection.push({ kind: 'ground', index: grounds.length - 1 });
            nextClipboard.push({ kind: 'ground', data: data as GroundSchema });
          }
        }
        return {
          coil: clampToRightHalfPlane({ ...s.coil, toploads, grounds }),
          ...pushHistory(s),
          revision: s.revision + 1,
          selection,
          clipboard: nextClipboard,
          contextMenu: null,
        };
      }),

    setDomain: (patch) => mutate((c) => ({ ...c, ...patch })),
    setDiscretizationOrder: (order) =>
      mutate((c) => ({ ...c, discretization_order: order })),

    setInputUnit: (fieldId, unit) =>
      set((s) => ({ unitPrefs: { ...s.unitPrefs, inputs: { ...s.unitPrefs.inputs, [fieldId]: unit } } })),
    setOutputUnit: (fieldId, pref) =>
      set((s) => ({ unitPrefs: { ...s.unitPrefs, outputs: { ...s.unitPrefs.outputs, [fieldId]: pref } } })),
    setUnitSystem: (system) =>
      set((s) => ({ unitPrefs: { ...s.unitPrefs, system, outputs: {} } })),
    setMatrixUnit: (key, unit) =>
      set((s) => ({ unitPrefs: { ...s.unitPrefs, matrices: { ...s.unitPrefs.matrices, [key]: unit } } })),

    updateSecondary: (patch) =>
      mutate((c) => ({ ...c, secondary: { ...c.secondary, ...patch } })),

    addPrimary: (start, end) =>
      mutate((c) => ({ ...c, primary: newPrimary(start, end) })),
    updatePrimary: (patch) =>
      mutate((c) =>
        c.primary ? { ...c, primary: { ...c.primary, ...patch } } : c,
      ),
    removePrimary: () => {
      mutate((c) => ({ ...c, primary: null }));
      set((s) => ({
        selection: s.selection.filter((ref) => ref.kind !== 'primary'),
      }));
    },

    addTopload: (center, radius, kind = 'circle') =>
      mutate((c) => {
        const t = newTopload(center, radius);
        return {
          ...c,
          toploads: [...c.toploads, { ...t, shape: convertShape(t.shape, kind) }],
        };
      }),
    updateTopload: (index, patch) =>
      mutate((c) => ({
        ...c,
        toploads: c.toploads.map((t, i) => (i === index ? { ...t, ...patch } : t)),
      })),
    removeTopload: (index) =>
      mutate((c) => ({ ...c, toploads: c.toploads.filter((_, i) => i !== index) })),

    addGround: (center, radius, kind = 'circle') =>
      mutate((c) => {
        const g = newGround(center, radius);
        return {
          ...c,
          grounds: [...c.grounds, { ...g, shape: convertShape(g.shape, kind) }],
        };
      }),
    updateGround: (index, patch) =>
      mutate((c) => ({
        ...c,
        grounds: c.grounds.map((g, i) => (i === index ? { ...g, ...patch } : g)),
      })),
    removeGround: (index) =>
      mutate((c) => ({ ...c, grounds: c.grounds.filter((_, i) => i !== index) })),

    setCoil: (coil) =>
      set((s) => ({
        coil: clampToRightHalfPlane(coil),
        past: [...s.past, s.coil].slice(-HISTORY_LIMIT),
        future: [],
        revision: s.revision + 1,
        selection: [],
      })),

    markRun: (revision) => set({ analyzedRevision: revision }),
    recordAnalysis: (analysis) =>
      set({ analysis, bundle: analysis.bundle ?? null }),

    loadSession: ({ coil, analysis, stale, unitPrefs }) =>
      set((s) => {
        const revision = s.revision + 1;
        // Fresh outputs correspond to the just-loaded coil (up to date); stale
        // ones must read as dirty, so peg their revision to the pre-load value.
        // With no outputs, there is nothing run.
        const analyzedRevision = analysis ? (stale ? s.revision : revision) : null;
        return {
          coil: clampToRightHalfPlane(coil),
          analysis,
          bundle: analysis?.bundle ?? null,
          analyzedRevision,
          // Restore saved display units on import; reset to defaults for New/Demo.
          unitPrefs: unitPrefs ?? defaultUnitPrefs(),
          past: [...s.past, s.coil].slice(-HISTORY_LIMIT),
          future: [],
          revision,
          selection: [],
          contextMenu: null,
        };
      }),
  };
});

// Expose the store for E2E/debugging (dev builds only).
if (import.meta.env.DEV) {
  (window as unknown as { __store?: unknown }).__store = useEditorStore;
}

// Re-export the secondary factory for the placement tool.
export { newSecondary };
