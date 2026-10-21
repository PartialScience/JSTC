/**
 * Left parameter column. Every coil parameter is visible and editable here,
 * organized by component; edits sync live with the canvas (both are views of
 * the same store). Clicking a section selects that component.
 */
import { useEffect, useRef } from 'react';

import type {
  GroundSchema,
  MaterialSchema,
  ToploadSchema,
} from '../api/client';
import type { ComponentRef, Point } from '../domain/coil';
import { isSelected, refKey } from '../domain/coil';
import { convertShape, insertVertex, deleteVertex, type ShapeKind } from '../editor/shapeOps';
import { evaluatePath } from '../domain/paths';
import { DensityEditor } from './DensityEditor';
import { FieldDrivePanel } from './FieldDrivePanel';
import { PathEditor } from './PathEditor';
import { useEditorStore } from '../state/store';
import { NumberField, QuantityField, SelectField } from './fields';

const MATERIALS: readonly MaterialSchema[] = ['copper', 'aluminum'];

/** Arc length of a path, tolerating transiently-degenerate editor states. */
function safePathLength(path: Parameters<typeof evaluatePath>[0]): number {
  try {
    return evaluatePath(path).length;
  } catch {
    return 0;
  }
}
const SHAPE_KINDS: readonly ShapeKind[] = ['circle', 'rectangle', 'polygon'];

function Section({
  title,
  refTarget,
  children,
  onRemove,
}: {
  title: string;
  refTarget?: ComponentRef;
  children: React.ReactNode;
  onRemove?: () => void;
}) {
  const selection = useEditorStore((s) => s.selection);
  const select = useEditorStore((s) => s.select);
  const active = refTarget ? isSelected(selection, refTarget) : false;
  return (
    <section
      className={active ? 'sidebar-section active' : 'sidebar-section'}
      data-ref-key={refTarget ? refKey(refTarget) : undefined}
    >
      <header
        className="sidebar-section-header"
        onClick={refTarget ? () => select(refTarget) : undefined}
      >
        <span>{title}</span>
        {onRemove && (
          <button
            type="button"
            className="link-btn"
            onClick={(e) => {
              e.stopPropagation();
              onRemove();
            }}
          >
            remove
          </button>
        )}
      </header>
      <div className="sidebar-section-body">{children}</div>
    </section>
  );
}

function ConductorEditor({
  data,
  onPatch,
  testPrefix,
}: {
  data: ToploadSchema | GroundSchema;
  onPatch: (patch: Partial<ToploadSchema | GroundSchema>) => void;
  testPrefix: string;
}) {
  const shape = data.shape;
  return (
    <>
      <SelectField
        label="Material"
        value={data.material}
        options={MATERIALS}
        onChange={(material) => onPatch({ material })}
        testId={`${testPrefix}-material`}
      />
      <SelectField
        label="Shape"
        value={shape.kind}
        options={SHAPE_KINDS}
        onChange={(kind) => onPatch({ shape: convertShape(shape, kind) })}
        testId={`${testPrefix}-kind`}
      />
      {shape.kind === 'circle' ? (
        <>
          <div className="field-row">
            <QuantityField
              label="center r"
              kind="length"
              fieldId={`${testPrefix}-cr`}
              value={shape.center[0]}
              min={0}
              onCommit={(r) => onPatch({ shape: { ...shape, center: [r, shape.center[1]] } })}
              testId={`${testPrefix}-cr`}
            />
            <QuantityField
              label="center z"
              kind="length"
              fieldId={`${testPrefix}-cz`}
              value={shape.center[1]}
              onCommit={(z) => onPatch({ shape: { ...shape, center: [shape.center[0], z] } })}
              testId={`${testPrefix}-cz`}
            />
          </div>
          <QuantityField
            label="radius"
            kind="length"
            fieldId={`${testPrefix}-radius`}
            value={shape.radius}
            min={0}
            onCommit={(radius) => onPatch({ shape: { ...shape, radius } })}
            testId={`${testPrefix}-radius`}
          />
        </>
      ) : (
        <div className="vertex-editor" data-testid={`${testPrefix}-vertices`}>
          <div className="field-note">{shape.kind} — {shape.vertices.length} vertices</div>
          {shape.vertices.map((v, i) => (
            <div className="field-row vertex-row" key={i}>
              <QuantityField
                label={`v${i} r`}
                kind="length"
                fieldId={`${testPrefix}-v${i}-r`}
                value={v[0]}
                min={0}
                onCommit={(r) =>
                  onPatch({
                    shape: {
                      ...shape,
                      vertices: shape.vertices.map(
                        (w, j) => (j === i ? [r, w[1]] : [w[0], w[1]]) as Point,
                      ),
                    },
                  })
                }
                testId={`${testPrefix}-v${i}-r`}
              />
              <QuantityField
                label={`v${i} z`}
                kind="length"
                fieldId={`${testPrefix}-v${i}-z`}
                value={v[1]}
                onCommit={(z) =>
                  onPatch({
                    shape: {
                      ...shape,
                      vertices: shape.vertices.map(
                        (w, j) => (j === i ? [w[0], z] : [w[0], w[1]]) as Point,
                      ),
                    },
                  })
                }
                testId={`${testPrefix}-v${i}-z`}
              />
              <button
                type="button"
                className="link-btn"
                title="Delete vertex"
                disabled={shape.vertices.length <= 3}
                onClick={() => {
                  const next = deleteVertex(shape, i);
                  if (next) onPatch({ shape: next });
                }}
                data-testid={`${testPrefix}-v${i}-del`}
              >
                ✕
              </button>
            </div>
          ))}
          <button
            type="button"
            className="link-btn add-vertex"
            data-testid={`${testPrefix}-add-vertex`}
            onClick={() => {
              // Insert near the last edge midpoint.
              const n = shape.vertices.length;
              const a = shape.vertices[n - 1]!;
              const b = shape.vertices[0]!;
              onPatch({ shape: insertVertex(shape, [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]) });
            }}
          >
            + add vertex
          </button>
        </div>
      )}
    </>
  );
}

export function Sidebar() {
  const coil = useEditorStore((s) => s.coil);
  const setDomain = useEditorStore((s) => s.setDomain);
  const setOrder = useEditorStore((s) => s.setDiscretizationOrder);
  const updateSecondary = useEditorStore((s) => s.updateSecondary);
  const updatePrimary = useEditorStore((s) => s.updatePrimary);
  const removePrimary = useEditorStore((s) => s.removePrimary);
  const updateTopload = useEditorStore((s) => s.updateTopload);
  const updateGround = useEditorStore((s) => s.updateGround);
  const removeTopload = useEditorStore((s) => s.removeTopload);
  const removeGround = useEditorStore((s) => s.removeGround);
  const selection = useEditorStore((s) => s.selection);
  const viewMode = useEditorStore((s) => s.viewMode);

  const sec = coil.secondary;
  const prim = coil.primary;
  const secPathLength = safePathLength(sec.path);
  const primPathLength = prim ? safePathLength(prim.path) : 0;

  // Auto-scroll the single selected component's section into view. Only a
  // single selection scrolls; a bulk (marquee) selection leaves the scroll
  // position alone, since there's no one section to reveal.
  const containerRef = useRef<HTMLDivElement>(null);
  const singleKey = selection.length === 1 ? refKey(selection[0]!) : null;
  useEffect(() => {
    if (!singleKey) return;
    // Skip in the stacked (mobile / portrait) layout: there the sidebar sits
    // below the editor and shares the page scroll (overflow-y: visible), so
    // revealing a section would yank the whole page down past the canvas. Only
    // scroll in the side-by-side layout, where the sidebar scrolls on its own.
    // Keep this query in sync with the stacked-layout breakpoint in styles.css.
    if (window.matchMedia('(max-width: 900px), (max-aspect-ratio: 4 / 5)').matches) return;
    const el = containerRef.current?.querySelector(`[data-ref-key="${singleKey}"]`);
    el?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [singleKey]);

  // In a field view the left panel shows drive/display controls instead. The
  // 2-D editor and the 3-D viewer both keep the normal parameter panel, so
  // edits stay live in 3-D.
  if (viewMode === 'efield' || viewMode === 'bfield') return <FieldDrivePanel />;

  return (
    <div className="sidebar" data-testid="sidebar" ref={containerRef}>
      <h2 className="sidebar-title">Parameters</h2>

      <Section title="Domain">
        <div className="field-row">
          <QuantityField label="r_max" kind="length" fieldId="domain-rmax" value={coil.r_max} min={0} onCommit={(r_max) => setDomain({ r_max })} testId="domain-rmax" />
          <QuantityField label="z_max" kind="length" fieldId="domain-zmax" value={coil.z_max} min={0} onCommit={(z_max) => setDomain({ z_max })} testId="domain-zmax" />
        </div>
        <NumberField label="discretization order" value={coil.discretization_order} step={1} min={2} onCommit={(n) => setOrder(Math.round(n))} testId="domain-order" />
      </Section>

      <Section title="Secondary" refTarget={{ kind: 'secondary' }}>
        <SelectField label="Material" value={sec.material} options={MATERIALS} onChange={(material) => updateSecondary({ material })} testId="sec-material" />
        <PathEditor path={sec.path} prefix="sec" winding="secondary" onChange={(path) => updateSecondary({ path })} />
        <DensityEditor
          turns={sec.turn_fxn}
          pathLength={secPathLength}
          prefix="sec"
          winding="secondary"
          onChange={(turn_fxn) => updateSecondary({ turn_fxn })}
        />
        <QuantityField label="wire diameter" kind="length" fieldId="sec-wire-dia" value={sec.wire_dia} min={0} onCommit={(wire_dia) => updateSecondary({ wire_dia })} testId="sec-wire-dia" />
      </Section>

      {prim && (
        <Section title="Primary" refTarget={{ kind: 'primary' }} onRemove={removePrimary}>
          <SelectField label="Material" value={prim.material} options={MATERIALS} onChange={(material) => updatePrimary({ material })} testId="prim-material" />
          <PathEditor path={prim.path} prefix="prim" winding="primary" onChange={(path) => updatePrimary({ path })} />
          <DensityEditor
            turns={prim.turn_fxn}
            pathLength={primPathLength}
            prefix="prim"
            winding="primary"
            onChange={(turn_fxn) => updatePrimary({ turn_fxn })}
          />
          <SelectField
            label="cross-section"
            value={prim.cross_section.kind}
            options={['circular', 'rectangular'] as const}
            onChange={(kind) =>
              updatePrimary({
                cross_section:
                  kind === 'circular'
                    ? { kind: 'circular', diameter: 0.00635 } // 0.25 in
                    : { kind: 'rectangular', width: 0.0254, height: 0.00254 }, // 1 in × 0.1 in
              })
            }
            testId="prim-xsection"
          />
          {prim.cross_section.kind === 'circular' ? (
            <QuantityField label="conductor dia" kind="length" fieldId="prim-dia" value={prim.cross_section.diameter} min={0} onCommit={(diameter) => updatePrimary({ cross_section: { kind: 'circular', diameter } })} testId="prim-dia" />
          ) : (
            <div className="field-row">
              <QuantityField label="width" kind="length" fieldId="prim-width" value={prim.cross_section.width} min={0} onCommit={(width) => updatePrimary({ cross_section: { kind: 'rectangular', width, height: prim.cross_section.kind === 'rectangular' ? prim.cross_section.height : 0.00254 } })} testId="prim-width" />
              <QuantityField label="height" kind="length" fieldId="prim-height" value={prim.cross_section.height} min={0} onCommit={(height) => updatePrimary({ cross_section: { kind: 'rectangular', width: prim.cross_section.kind === 'rectangular' ? prim.cross_section.width : 0.0254, height } })} testId="prim-height" />
            </div>
          )}
          <QuantityField label="tank capacitance" kind="capacitance" fieldId="prim-tank" defaultUnit="nF" value={prim.tank_capacitance} min={0} onCommit={(tank_capacitance) => updatePrimary({ tank_capacitance })} testId="prim-tank" />
          <div className="field-row">
            <QuantityField label="lead length" kind="length" fieldId="prim-lead-len" value={prim.lead_length} onCommit={(lead_length) => updatePrimary({ lead_length })} testId="prim-lead-len" />
            <QuantityField label="lead dia" kind="length" fieldId="prim-lead-dia" value={prim.lead_dia} onCommit={(lead_dia) => updatePrimary({ lead_dia })} testId="prim-lead-dia" />
          </div>
        </Section>
      )}

      {coil.toploads.map((t, i) => (
        <Section key={`topload-${i}`} title={`Topload #${i + 1}`} refTarget={{ kind: 'topload', index: i }} onRemove={() => removeTopload(i)}>
          <ConductorEditor data={t} onPatch={(patch) => updateTopload(i, patch)} testPrefix={`topload-${i}`} />
        </Section>
      ))}

      {coil.grounds.map((g, i) => (
        <Section key={`ground-${i}`} title={`Ground #${i + 1}`} refTarget={{ kind: 'ground', index: i }} onRemove={() => removeGround(i)}>
          <ConductorEditor data={g} onPatch={(patch) => updateGround(i, patch)} testPrefix={`ground-${i}`} />
        </Section>
      ))}
    </div>
  );
}
