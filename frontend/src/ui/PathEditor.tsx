/**
 * Winding-path editor: the sidebar block for a winding's centerline.
 *
 * The path kind is chosen inline (line / arc / spline); each kind exposes its
 * defining parameters as ordinary quantity fields, so the line case renders
 * exactly the familiar start/end rows (same test ids as before). Switching
 * kinds preserves the geometry where it can: line <-> arc keep the endpoints
 * (a fresh arc starts at a gentle bend), and a new spline interpolates the
 * old endpoints through their midpoint - i.e. it starts out exactly straight.
 *
 * Arc and spline paths are not yet experimentally validated; the kind select
 * carries the same badge/wording the Results banner shows (one registry, no
 * drift - see domain/provenance.ts).
 */
import type { PathSchema } from '../api/client';
import type { Point } from '../domain/coil';
import { pathControlPoints, pathEndpoints } from '../domain/paths';
import { unvalidatedFeature } from '../domain/provenance';
import { QuantityField, SelectField } from './fields';

export type PathKind = PathSchema['kind'];
const PATH_KINDS: readonly PathKind[] = ['line', 'arc', 'spline'];

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

function convertPath(path: PathSchema, kind: PathKind): PathSchema {
  if (kind === path.kind) return path;
  const { start, end } = pathEndpoints(path);
  if (kind === 'line') return { kind: 'line', start, end };
  if (kind === 'arc') {
    // Reuse an existing interior point as the through point where one
    // exists and isn't collinear; otherwise bend gently off the chord.
    const pts = pathControlPoints(path);
    const candidate = pts.length > 2 ? pts[Math.floor(pts.length / 2)]! : null;
    const mid = candidate && !collinear(start, candidate, end) ? candidate : bentMid(start, end);
    return { kind: 'arc', start, mid, end };
  }
  // spline through the path's defining points (an arc's through point
  // carries over; a line starts exactly straight via its midpoint)
  if (path.kind === 'arc') {
    return { kind: 'spline', points: [start, path.mid as Point, end] };
  }
  const mid: Point = [(start[0] + end[0]) / 2, (start[1] + end[1]) / 2];
  return { kind: 'spline', points: [start, mid, end] };
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

  const pointRow = (
    label: string,
    value: Point,
    fieldId: string,
    commit: (p: Point) => void,
  ) => (
    <div className="field-row">
      <QuantityField
        label={`${label} r`}
        kind="length"
        fieldId={`${fieldId}-r`}
        value={value[0]}
        min={0}
        onCommit={(r) => commit([r, value[1]])}
        testId={`${fieldId}-r`}
      />
      <QuantityField
        label={`${label} z`}
        kind="length"
        fieldId={`${fieldId}-z`}
        value={value[1]}
        onCommit={(z) => commit([value[0], z])}
        testId={`${fieldId}-z`}
      />
    </div>
  );

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

      {(path.kind === 'line' || path.kind === 'arc') && (
        <>
          {pointRow('start', path.start as Point, `${prefix}-start`, (start) =>
            onChange({ ...path, start }),
          )}
          {path.kind === 'arc' &&
            pointRow('mid', path.mid as Point, `${prefix}-mid`, (mid) =>
              onChange({ ...path, mid }),
            )}
          {pointRow('end', path.end as Point, `${prefix}-end`, (end) =>
            onChange({ ...path, end }),
          )}
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
