/**
 * Editor toolbar: the Select (box-select) toggle plus a placement control per
 * component type on the left; theme toggle, undo/redo and the Run button on
 * the right.
 *
 * Panning is the default canvas mode, where clicking a component selects it and
 * dragging pans (or moves a component). Select is a toggle whose only job is
 * box (marquee) selection: while it's on, dragging draws a selection rectangle;
 * click-to-select still works. The primary and secondary are singletons, so
 * their buttons gray out once one exists. Toploads and grounds have a geometry,
 * so their buttons are dropdowns: clicking one opens a menu of shapes (circle /
 * rectangle / polygon) and picking one arms placement with that geometry — the
 * choice is made in the button itself, never via a second control that appears.
 */
import { useEffect, useState } from 'react';

import { useEditorStore } from '../state/store';
import type { Tool } from '../domain/coil';
import type { ShapeKind } from '../editor/shapeOps';

/** The compact (stacked) layout breakpoint. Keep in sync with the
 *  `@media (max-width: 900px), (max-aspect-ratio: 4/5)` rule in styles.css:
 *  below it the placement tools collapse into a single "+ Add" menu. */
const COMPACT_QUERY = '(max-width: 900px), (max-aspect-ratio: 4 / 5)';

/** Reactive media-query match. Resolves to false (desktop) when matchMedia is
 *  unavailable, e.g. jsdom under unit tests. */
function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(
    () => typeof window !== 'undefined' && !!window.matchMedia && window.matchMedia(query).matches,
  );
  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const mql = window.matchMedia(query);
    const onChange = () => setMatches(mql.matches);
    onChange();
    mql.addEventListener('change', onChange);
    return () => mql.removeEventListener('change', onChange);
  }, [query]);
  return matches;
}

const TOOLS: { tool: Tool; label: string; hint: string }[] = [
  { tool: 'secondary', label: '+ Secondary', hint: 'Place the secondary winding' },
  { tool: 'primary', label: '+ Primary', hint: 'Place the primary winding' },
];

/** Tools whose placement geometry is chosen from the button's dropdown. */
const SHAPE_TOOLS: { tool: Tool; label: string; hint: string }[] = [
  { tool: 'topload', label: 'Topload', hint: 'Place a topload' },
  { tool: 'ground', label: 'Ground', hint: 'Place a grounded conductor' },
];

/** Tools that place a singleton component: disabled once one exists. */
const SINGLETON_EXISTS_HINT: Partial<Record<Tool, string>> = {
  primary: 'A primary already exists',
  secondary: 'A secondary already exists',
};

const SHAPE_OPTIONS: { kind: ShapeKind; label: string }[] = [
  { kind: 'circle', label: 'Circle' },
  { kind: 'rectangle', label: 'Rectangle' },
  { kind: 'polygon', label: 'Polygon' },
];

const shapeLabel = (kind: ShapeKind) =>
  SHAPE_OPTIONS.find((o) => o.kind === kind)?.label ?? kind;

interface ToolbarProps {
  onRun: () => void;
  running: boolean;
  dirty: boolean;
  hasRun: boolean;
}

/** A placement button that opens a geometry menu when clicked. Selecting a
 *  geometry arms the tool with that shape and closes the menu. */
function PlacementDropdown({ tool, label, hint }: { tool: Tool; label: string; hint: string }) {
  const activeTool = useEditorStore((s) => s.tool);
  const setTool = useEditorStore((s) => s.setTool);
  const placementShape = useEditorStore((s) => s.placementShape);
  const setPlacementShape = useEditorStore((s) => s.setPlacementShape);
  const [open, setOpen] = useState(false);

  const active = activeTool === tool;

  const pick = (kind: ShapeKind) => {
    setPlacementShape(kind);
    setTool(tool);
    setOpen(false);
  };

  return (
    <div className="placement-dropdown">
      <button
        type="button"
        data-testid={`tool-${tool}`}
        className={active ? 'toolbar-btn active' : 'toolbar-btn'}
        title={hint}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        + {label}
        {active ? ` · ${shapeLabel(placementShape)}` : ''} ▾
      </button>
      {open && (
        <>
          <div className="dropdown-backdrop" onClick={() => setOpen(false)} />
          <div className="dropdown-menu" role="menu" data-testid={`shape-menu-${tool}`}>
            {SHAPE_OPTIONS.map((o) => {
              const selected = placementShape === o.kind;
              return (
                <button
                  key={o.kind}
                  type="button"
                  role="menuitemradio"
                  aria-checked={selected}
                  data-testid={`shape-${tool}-${o.kind}`}
                  className="dropdown-item"
                  onClick={() => pick(o.kind)}
                >
                  <span className="check">{selected ? '✓' : ''}</span>
                  {o.label}
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

/** Component types offered by the compact "+ Add" menu, in display order. */
const ADD_TOOLS: { tool: Tool; label: string }[] = [
  { tool: 'secondary', label: 'Secondary' },
  { tool: 'primary', label: 'Primary' },
  { tool: 'topload', label: 'Topload' },
  { tool: 'ground', label: 'Ground' },
];

const toolLabel = (tool: Tool) => ADD_TOOLS.find((t) => t.tool === tool)?.label ?? '';

/** Compact placement control for narrow layouts: a single "+ Add" button whose
 *  menu lists the component types. Toploads/grounds are armed with the current
 *  placement geometry (default circle) — the shape can be changed after placing
 *  via the sidebar or the shape's context menu, so the menu stays a flat list.
 *  Desktop keeps the per-type buttons with their inline geometry pickers. */
function AddMenu() {
  const activeTool = useEditorStore((s) => s.tool);
  const setTool = useEditorStore((s) => s.setTool);
  const hasPrimary = useEditorStore((s) => s.coil.primary !== null);
  const hasSecondary = useEditorStore((s) => s.coil.secondary !== null);
  const [open, setOpen] = useState(false);

  // Armed only while a placement tool is active — not in the pan/select modes.
  const armed = activeTool !== 'pan' && activeTool !== 'select';
  const disabledFor = (tool: Tool) =>
    (tool === 'primary' && hasPrimary) || (tool === 'secondary' && hasSecondary);

  const pick = (tool: Tool) => {
    setTool(tool);
    setOpen(false);
  };

  return (
    <div className="placement-dropdown">
      <button
        type="button"
        data-testid="tool-add"
        className={armed ? 'toolbar-btn active' : 'toolbar-btn'}
        aria-haspopup="menu"
        aria-expanded={open}
        title="Add a component"
        onClick={() => setOpen((v) => !v)}
      >
        + Add{armed ? ` · ${toolLabel(activeTool)}` : ''} ▾
      </button>
      {open && (
        <>
          <div className="dropdown-backdrop" onClick={() => setOpen(false)} />
          <div className="dropdown-menu" role="menu" data-testid="add-menu">
            {ADD_TOOLS.map((t) => (
              <button
                key={t.tool}
                type="button"
                role="menuitem"
                data-testid={`add-${t.tool}`}
                className="dropdown-item"
                disabled={disabledFor(t.tool)}
                onClick={() => pick(t.tool)}
              >
                + {t.label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

const VIEW_MODES = [
  { mode: 'edit' as const, label: '2D' },
  { mode: '3d' as const, label: '3D' },
  { mode: 'efield' as const, label: 'E-field' },
  { mode: 'bfield' as const, label: 'B-field' },
];

/** View modes that overlay a computed field and so lock until a run exists.
 *  2D (edit) and 3D are geometry-only and always available. */
const FIELD_MODES = new Set(['efield', 'bfield']);

export function Toolbar({ onRun, running, dirty, hasRun }: ToolbarProps) {
  const tool = useEditorStore((s) => s.tool);
  const setTool = useEditorStore((s) => s.setTool);
  const viewMode = useEditorStore((s) => s.viewMode);
  const setViewMode = useEditorStore((s) => s.setViewMode);
  const hasBundle = useEditorStore((s) => s.bundle !== null);
  const hasPrimary = useEditorStore((s) => s.coil.primary !== null);
  const hasSecondary = useEditorStore((s) => s.coil.secondary !== null);
  const undo = useEditorStore((s) => s.undo);
  const redo = useEditorStore((s) => s.redo);
  const canUndo = useEditorStore((s) => s.past.length > 0);
  const canRedo = useEditorStore((s) => s.future.length > 0);

  const runLabel = running ? 'Running…' : hasRun && !dirty ? 'Up to date' : 'Run calculations';

  // On narrow layouts the five placement buttons collapse into one "+ Add"
  // menu so the toolbar stays a tidy row instead of a ragged wrap. Desktop
  // keeps the full set of buttons with their inline geometry pickers.
  const compact = useMediaQuery(COMPACT_QUERY);

  return (
    <div className="toolbar" role="toolbar" aria-label="Editor tools">
      <div className="toolbar-group segmented" role="group" aria-label="View mode">
        {VIEW_MODES.map((v) => {
          const locked = FIELD_MODES.has(v.mode) && !hasBundle;
          return (
            <button
              key={v.mode}
              type="button"
              data-testid={`mode-${v.mode}`}
              className={viewMode === v.mode ? 'seg-btn active' : 'seg-btn'}
              aria-pressed={viewMode === v.mode}
              disabled={locked}
              title={locked ? 'Run the calculation first to view fields' : `${v.label} view`}
              onClick={() => setViewMode(v.mode)}
            >
              {v.label}
            </button>
          );
        })}
      </div>

      {viewMode === 'edit' && (
      <div className="toolbar-group">
        <button
          type="button"
          data-testid="tool-select"
          className={tool === 'select' ? 'toolbar-btn active' : 'toolbar-btn'}
          title="Box-select: drag a box to select many. (You can always click a component to select it.)"
          aria-pressed={tool === 'select'}
          onClick={() => setTool(tool === 'select' ? 'pan' : 'select')}
        >
          Select
        </button>

        {compact ? (
          <AddMenu />
        ) : (
          <>
            {TOOLS.map((t) => {
              const disabled =
                (t.tool === 'primary' && hasPrimary) ||
                (t.tool === 'secondary' && hasSecondary);
              return (
                <button
                  key={t.tool}
                  type="button"
                  data-testid={`tool-${t.tool}`}
                  className={tool === t.tool ? 'toolbar-btn active' : 'toolbar-btn'}
                  title={disabled ? SINGLETON_EXISTS_HINT[t.tool] : t.hint}
                  disabled={disabled}
                  onClick={() => setTool(t.tool)}
                >
                  {t.label}
                </button>
              );
            })}

            {SHAPE_TOOLS.map((t) => (
              <PlacementDropdown key={t.tool} tool={t.tool} label={t.label} hint={t.hint} />
            ))}
          </>
        )}
      </div>
      )}

      <div className="toolbar-group">
        <button
          type="button"
          data-testid="undo"
          className="toolbar-btn"
          title="Undo (Ctrl+Z)"
          disabled={!canUndo}
          onClick={undo}
        >
          ↶ Undo
        </button>
        <button
          type="button"
          data-testid="redo"
          className="toolbar-btn"
          title="Redo (Ctrl+Shift+Z)"
          disabled={!canRedo}
          onClick={redo}
        >
          ↷ Redo
        </button>
        <button
          type="button"
          data-testid="run"
          className={dirty || !hasRun ? 'toolbar-btn run dirty' : 'toolbar-btn run'}
          title="Run the full simulation"
          disabled={running}
          onClick={onRun}
        >
          {runLabel}
        </button>
      </div>
    </div>
  );
}
