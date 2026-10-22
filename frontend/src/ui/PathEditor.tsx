/**
 * Winding-path editor: the sidebar block for a winding's centerline.
 *
 * The path kind is chosen inline (line / arc / spline / piecewise); each
 * kind exposes its defining parameters as ordinary quantity fields, so the
 * line case renders exactly the familiar start/end rows. Switching kinds
 * preserves the geometry where it can.
 *
 * A piecewise path renders as an expandable list of segment cards. The
 * first segment is an ordinary line/arc/spline; every later segment is a
 * CONTINUATION that inherits its start point and tangent from the previous
 * segment's end, so tangent continuity holds by construction — each card
 * edits only that segment's free parameters (line-from: length; arc-from:
 * endpoint; spline-from: interpolation points) and shows the inherited
 * junction read-only. Edits ripple downstream by re-propagation.
 *
 * Arc, spline and piecewise paths are not yet experimentally validated;
 * the kind select carries the same badge/wording the Results banner shows
 * (one registry, no drift - see domain/provenance.ts).
 */
import { useState } from 'react';

import type {
  ContinuationSchema,
  PathSchema,
  PiecewisePathSchema,
  SimplePathSchema,
} from '../api/client';
import type { Point } from '../domain/coil';
import { junctionBefore, pathControlPoints, pathEndpoints } from '../domain/paths';
import { unvalidatedFeature } from '../domain/provenance';
import { DEFAULT_INPUT_UNIT, formatInput, unitSymbol } from '../units/units';
import { QuantityField, SelectField } from './fields';

export type PathKind = PathSchema['kind'];
const PATH_KINDS: readonly PathKind[] = ['line', 'arc', 'spline', 'piecewise'];
type ContinuationKind = ContinuationSchema['kind'];
const CONTINUATION_KINDS: readonly ContinuationKind[] = ['line-from', 'arc-from', 'spline-from'];

/** A gently-bent through point: the chord midpoint pushed off by 15% of
 *  the chord on the left-normal side (visibly an arc, never collinear). */
function bentMid(start: Point, end: Point): Point {
  const dx = end[0] - start[0];
  const dz = end[1] - start[1];
  const chord = Math.hypot(dx, dz) || 1;
  return [
    (start[0] + end[0]) / 2 - (dz / chord) * 0.15 * chord,
    (start[1] + end[1]) / 2 + (dx / chord) * 0.15 * chord,
  ];
}

function collinear(a: Point, b: Point, c: Point): boolean {
  const d = a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]);
  const scale = Math.max(Math.hypot(b[0] - a[0], b[1] - a[1]), Math.hypot(c[0] - a[0], c[1] - a[1]), 1e-30);
  return Math.abs(d) <= 1e-9 * scale * scale;
}

function toSimple(path: PathSchema, kind: 'line' | 'arc' | 'spline'): SimplePathSchema {
  const { start, end } = pathEndpoints(path);
  if (kind === 'line') return { kind: 'line', start, end };
  if (kind === 'arc') {
    const pts = pathControlPoints(path);
    const candidate = pts.length > 2 ? pts[Math.floor(pts.length / 2)]! : null;
    const mid = candidate && !collinear(start, candidate, end) ? candidate : bentMid(start, end);
    return { kind: 'arc', start, mid, end };
  }
  if (path.kind === 'arc') {
    return { kind: 'spline', points: [start, path.mid as Point, end] };
  }
  const mid: Point = [(start[0] + end[0]) / 2, (start[1] + end[1]) / 2];
  return { kind: 'spline', points: [start, mid, end] };
}

function convertPath(path: PathSchema, kind: PathKind): PathSchema {
  if (kind === path.kind) return path;
  if (kind === 'piecewise') {
    const first: SimplePathSchema = path.kind === 'piecewise' ? path.first : path;
    // Start the chain with a straight continuation: exactly tangent, and a
    // visible second segment to grab.
    let length = 0.01;
    try {
      const { start, end } = pathEndpoints(first);
      length = Math.max(0.15 * Math.hypot(end[0] - start[0], end[1] - start[1]), 1e-4);
    } catch {
      /* keep the fallback */
    }
    return { kind: 'piecewise', first, rest: [{ kind: 'line-from', length }] };
  }
  return toSimple(path, kind);
}

/** Convert a continuation to another kind, preserving its current end
 *  where the junction state is available. */
function convertContinuation(
  path: PiecewisePathSchema,
  seg: number,
  kind: ContinuationKind,
): ContinuationSchema {
  const cont = path.rest[seg]!;
  if (cont.kind === kind) return cont;
  const j = junctionBefore(path, seg);
  const endJ = junctionBefore(path, seg + 1);
  const currentEnd: Point | null = endJ ? endJ.point : null;

  if (kind === 'line-from') {
    const length =
      j && currentEnd
        ? Math.max(Math.hypot(currentEnd[0] - j.point[0], currentEnd[1] - j.point[1]), 1e-4)
        : 0.01;
    return { kind: 'line-from', length };
  }
  if (kind === 'arc-from') {
    if (j && currentEnd) {
      // Straight-ahead endpoints are degenerate for a tangent arc: bend off
      // the tangent line slightly so the conversion always succeeds.
      const dx = currentEnd[0] - j.point[0];
      const dz = currentEnd[1] - j.point[1];
      const cross = j.tangent[0] * dz - j.tangent[1] * dx;
      const chord = Math.hypot(dx, dz) || 1;
      if (Math.abs(cross) > 1e-9 * chord) return { kind: 'arc-from', end: currentEnd };
      const n: Point = [-j.tangent[1], j.tangent[0]];
      return {
        kind: 'arc-from',
        end: [currentEnd[0] + 0.15 * chord * n[0], currentEnd[1] + 0.15 * chord * n[1]],
      };
    }
    return { kind: 'arc-from', end: currentEnd ?? [1, 1] };
  }
  return { kind: 'spline-from', points: [currentEnd ?? [1, 1]] };
}

export function PathEditor({
  path,
  prefix,
  winding,
  onChange,
}: {
  path: PathSchema;
  /** Test-id prefix ('sec' / 'prim'). */
  prefix: string;
  winding: 'secondary' | 'primary';
  onChange: (path: PathSchema) => void;
}) {
  const mark =
    path.kind === 'line' ? null : unvalidatedFeature(`${path.kind}-${winding}`);

  return (
    <>
      <SelectField
        label="path"
        value={path.kind}
        options={PATH_KINDS}
        onChange={(kind) => onChange(convertPath(path, kind))}
        testId={`${prefix}-path-kind`}
        unvalidated={mark}
      />
      {path.kind === 'piecewise' ? (
        <PiecewiseEditor path={path} prefix={prefix} onChange={onChange} />
      ) : (
        <SimplePathFields path={path} prefix={prefix} onChange={onChange} />
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Simple (non-piecewise) path fields — also used for a chain's first segment
// ---------------------------------------------------------------------------

function PointRow({
  label,
  value,
  fieldId,
  onCommit,
}: {
  label: string;
  value: Point;
  fieldId: string;
  onCommit: (p: Point) => void;
}) {
  return (
    <div className="field-row">
      <QuantityField
        label={`${label} r`}
        kind="length"
        fieldId={`${fieldId}-r`}
        value={value[0]}
        min={0}
        onCommit={(r) => onCommit([r, value[1]])}
        testId={`${fieldId}-r`}
      />
      <QuantityField
        label={`${label} z`}
        kind="length"
        fieldId={`${fieldId}-z`}
        value={value[1]}
        onCommit={(z) => onCommit([value[0], z])}
        testId={`${fieldId}-z`}
      />
    </div>
  );
}

function SimplePathFields({
  path,
  prefix,
  onChange,
}: {
  path: SimplePathSchema;
  prefix: string;
  onChange: (path: SimplePathSchema) => void;
}) {
  return (
    <>
      {(path.kind === 'line' || path.kind === 'arc') && (
        <>
          <PointRow
            label="start"
            value={path.start as Point}
            fieldId={`${prefix}-start`}
            onCommit={(start) => onChange({ ...path, start })}
          />
          {path.kind === 'arc' && (
            <PointRow
              label="mid"
              value={path.mid as Point}
              fieldId={`${prefix}-mid`}
              onCommit={(mid) => onChange({ ...path, mid })}
            />
          )}
          <PointRow
            label="end"
            value={path.end as Point}
            fieldId={`${prefix}-end`}
            onCommit={(end) => onChange({ ...path, end })}
          />
        </>
      )}

      {path.kind === 'spline' && (
        <div className="vertex-editor" data-testid={`${prefix}-spline-points`}>
          <div className="field-note">spline — {path.points.length} points</div>
          {(path.points as Point[]).map((p, i) => (
            <div className="field-row vertex-row" key={i}>
              <QuantityField
                label={`p${i} r`}
                kind="length"
                fieldId={`${prefix}-pt-${i}-r`}
                value={p[0]}
                min={0}
                onCommit={(r) =>
                  onChange({
                    ...path,
                    points: (path.points as Point[]).map((q, j) => (j === i ? [r, q[1]] : q)),
                  })
                }
                testId={`${prefix}-pt-${i}-r`}
              />
              <QuantityField
                label={`p${i} z`}
                kind="length"
                fieldId={`${prefix}-pt-${i}-z`}
                value={p[1]}
                onCommit={(z) =>
                  onChange({
                    ...path,
                    points: (path.points as Point[]).map((q, j) => (j === i ? [q[0], z] : q)),
                  })
                }
                testId={`${prefix}-pt-${i}-z`}
              />
              <button
                type="button"
                className="link-btn"
                title="Delete point"
                disabled={path.points.length <= 2}
                onClick={() =>
                  onChange({
                    ...path,
                    points: (path.points as Point[]).filter((_, j) => j !== i),
                  })
                }
                data-testid={`${prefix}-pt-${i}-del`}
              >
                ✕
              </button>
            </div>
          ))}
          <button
            type="button"
            className="link-btn add-vertex"
            data-testid={`${prefix}-add-point`}
            onClick={() => {
              const pts = path.points as Point[];
              const a = pts[pts.length - 2]!;
              const b = pts[pts.length - 1]!;
              const mid: Point = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
              onChange({ ...path, points: [...pts.slice(0, -1), mid, b] });
            }}
          >
            + add point
          </button>
        </div>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Piecewise: an expandable list of segment cards
// ---------------------------------------------------------------------------

function SegmentCard({
  title,
  testId,
  defaultOpen = true,
  onRemove,
  children,
}: {
  title: string;
  testId: string;
  defaultOpen?: boolean;
  onRemove?: () => void;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className={`collapsible-card${open ? ' open' : ''}`} data-testid={testId}>
      <div
        className="collapsible-header"
        onClick={() => {
          if (!open) setOpen(true);
        }}
        role={open ? undefined : 'button'}
      >
        <span>{title}</span>
        <span className="collapsible-header-actions">
          {onRemove && (
            <button
              type="button"
              className="link-btn"
              title="Delete segment"
              data-testid={`${testId}-del`}
              onClick={(e) => {
                e.stopPropagation();
                onRemove();
              }}
            >
              ✕
            </button>
          )}
          <button
            type="button"
            className="collapse-arrow"
            aria-expanded={open}
            aria-label={open ? 'Collapse' : 'Expand'}
            data-testid={`${testId}-toggle`}
            onClick={(e) => {
              e.stopPropagation();
              setOpen(!open);
            }}
          >
            ▾
          </button>
        </span>
      </div>
      <div className="collapsible-body" aria-hidden={!open}>
        <div className="collapsible-inner">{children}</div>
      </div>
    </div>
  );
}

/** Junction positions display in the default length unit (the same one new
 *  quantity fields start in), tangents as unit-vector components. */
function formatPoint(p: Point): string {
  const unit = DEFAULT_INPUT_UNIT.length;
  return `(${formatInput(p[0], unit, 'length', 5)}, ${formatInput(p[1], unit, 'length', 5)}) ${unitSymbol(unit)}`;
}

function formatTangent(t: Point): string {
  const sig = (v: number) => String(Number(v.toPrecision(3)));
  return `(${sig(t[0])}, ${sig(t[1])})`;
}

function PiecewiseEditor({
  path,
  prefix,
  onChange,
}: {
  path: PiecewisePathSchema;
  prefix: string;
  onChange: (path: PathSchema) => void;
}) {
  const patchRest = (seg: number, cont: ContinuationSchema) =>
    onChange({ ...path, rest: path.rest.map((c, i) => (i === seg ? cont : c)) });

  const addSegment = () => {
    let length = 0.01;
    try {
      const j = junctionBefore(path, path.rest.length);
      void j; // reachable end: scale the new run to the chain
      const { start, end } = pathEndpoints(path);
      length = Math.max(0.1 * Math.hypot(end[0] - start[0], end[1] - start[1]), 1e-4);
    } catch {
      /* keep the fallback */
    }
    onChange({ ...path, rest: [...path.rest, { kind: 'line-from', length }] });
  };

  const removeSegment = (seg: number) => {
    const rest = path.rest.filter((_, i) => i !== seg);
    // A piecewise path with no continuations is just its first segment.
    if (rest.length === 0) onChange(path.first);
    else onChange({ ...path, rest });
  };

  return (
    <div className="piecewise-editor" data-testid={`${prefix}-piecewise-editor`}>
      <SegmentCard title={`segment 1 — ${path.first.kind}`} testId={`${prefix}-seg0`}>
        <SelectField
          label="segment type"
          value={path.first.kind}
          options={['line', 'arc', 'spline'] as const}
          onChange={(kind) =>
            onChange({ ...path, first: toSimple(path.first, kind) })
          }
          testId={`${prefix}-seg0-kind`}
        />
        <SimplePathFields
          path={path.first}
          prefix={`${prefix}-seg0`}
          onChange={(first) => onChange({ ...path, first })}
        />
      </SegmentCard>

      {path.rest.map((cont, seg) => {
        const junction = junctionBefore(path, seg);
        const segPrefix = `${prefix}-seg${seg + 1}`;
        return (
          <SegmentCard
            key={seg}
            title={`segment ${seg + 2} — ${cont.kind}`}
            testId={segPrefix}
            onRemove={() => removeSegment(seg)}
          >
            <div className="field-note">
              {junction
                ? `continues from ${formatPoint(junction.point)}, tangent ${formatTangent(junction.tangent)}`
                : 'continues from the previous segment (currently degenerate)'}
            </div>
            <SelectField
              label="segment type"
              value={cont.kind}
              options={CONTINUATION_KINDS}
              onChange={(kind) => patchRest(seg, convertContinuation(path, seg, kind))}
              testId={`${segPrefix}-kind`}
            />

            {cont.kind === 'line-from' && (
              <QuantityField
                label="length"
                kind="length"
                fieldId={`${segPrefix}-length`}
                value={cont.length}
                min={1e-9}
                onCommit={(length) => patchRest(seg, { kind: 'line-from', length })}
                testId={`${segPrefix}-length`}
              />
            )}

            {cont.kind === 'arc-from' && (
              <PointRow
                label="end"
                value={cont.end as Point}
                fieldId={`${segPrefix}-end`}
                onCommit={(end) => patchRest(seg, { kind: 'arc-from', end })}
              />
            )}

            {cont.kind === 'spline-from' && (
              <div className="vertex-editor">
                {(cont.points as Point[]).map((p, i) => (
                  <div className="field-row vertex-row" key={i}>
                    <QuantityField
                      label={`p${i} r`}
                      kind="length"
                      fieldId={`${segPrefix}-pt-${i}-r`}
                      value={p[0]}
                      min={0}
                      onCommit={(r) =>
                        patchRest(seg, {
                          kind: 'spline-from',
                          points: (cont.points as Point[]).map((q, j) => (j === i ? [r, q[1]] : q)),
                        })
                      }
                      testId={`${segPrefix}-pt-${i}-r`}
                    />
                    <QuantityField
                      label={`p${i} z`}
                      kind="length"
                      fieldId={`${segPrefix}-pt-${i}-z`}
                      value={p[1]}
                      onCommit={(z) =>
                        patchRest(seg, {
                          kind: 'spline-from',
                          points: (cont.points as Point[]).map((q, j) => (j === i ? [q[0], z] : q)),
                        })
                      }
                      testId={`${segPrefix}-pt-${i}-z`}
                    />
                    <button
                      type="button"
                      className="link-btn"
                      title="Delete point"
                      disabled={cont.points.length <= 1}
                      onClick={() =>
                        patchRest(seg, {
                          kind: 'spline-from',
                          points: (cont.points as Point[]).filter((_, j) => j !== i),
                        })
                      }
                      data-testid={`${segPrefix}-pt-${i}-del`}
                    >
                      ✕
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  className="link-btn add-vertex"
                  data-testid={`${segPrefix}-add-point`}
                  onClick={() => {
                    const pts = cont.points as Point[];
                    const last = pts[pts.length - 1]!;
                    const prev = pts.length > 1 ? pts[pts.length - 2]! : junctionBefore(path, seg)?.point;
                    const mid: Point = prev
                      ? [(prev[0] + last[0]) / 2, (prev[1] + last[1]) / 2]
                      : [last[0], last[1] + 0.01];
                    patchRest(seg, {
                      kind: 'spline-from',
                      points: [...pts.slice(0, -1), mid, last],
                    });
                  }}
                >
                  + add point
                </button>
              </div>
            )}
          </SegmentCard>
        );
      })}

      <button
        type="button"
        className="link-btn add-vertex"
        data-testid={`${prefix}-add-segment`}
        onClick={addSegment}
        disabled={path.rest.length >= 19}
      >
        + add segment
      </button>
    </div>
  );
}
