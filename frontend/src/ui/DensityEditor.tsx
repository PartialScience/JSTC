/**
 * Winding-density editor: uniform turn count, or graded cumulative turn
 * control points.
 *
 * Graded mode shows the control points twice, always in sync:
 *  * an editable table (position along the winding in length units;
 *    cumulative turns). The focused cell shows full precision, resting rows
 *    are curtailed for readability (display-only - stored values keep full
 *    precision);
 *  * a collapsible plot of the cumulative turn curve, with draggable
 *    points.
 * Hovering a table row highlights its point in the plot and vice versa.
 * The plot's turn axis auto-scales to the data with a little headroom.
 *
 * Graded density is not yet experimentally validated; the mode select
 * carries the same badge/wording as the Results banner (one registry).
 */
import { useRef, useState } from 'react';

import type { GradedTurnProfileSchema, TurnProfileSchema } from '../api/client';
import { unvalidatedFeature } from '../domain/provenance';
import { NumberField, QuantityField, SelectField } from './fields';

type DensityKind = TurnProfileSchema['kind'];
type GradedPoint = [number, number];

const EPS_U = 1e-4;
const EPS_N = 1e-9;

function totalTurnsOf(turns: TurnProfileSchema): number {
  return turns.kind === 'uniform'
    ? turns.total_turns
    : turns.points[turns.points.length - 1]![1];
}

function convertTurns(turns: TurnProfileSchema, kind: DensityKind): TurnProfileSchema {
  if (kind === turns.kind) return turns;
  const total = totalTurnsOf(turns);
  if (kind === 'uniform') return { kind: 'uniform', total_turns: total };
  return { kind: 'graded', points: [[0, 0], [1, total]] };
}

/** Clamp a point's (u, n) between its neighbors (both strictly increasing). */
function clampPoint(
  points: GradedPoint[],
  i: number,
  u: number,
  n: number,
): GradedPoint {
  const isFirst = i === 0;
  const isLast = i === points.length - 1;
  const uLo = isFirst ? 0 : points[i - 1]![0] + EPS_U;
  const uHi = isLast ? 1 : points[i + 1]![0] - EPS_U;
  const nLo = isFirst ? 0 : points[i - 1]![1] + EPS_N;
  const nHi = isLast ? Infinity : points[i + 1]![1] - EPS_N;
  return [
    isFirst ? 0 : isLast ? 1 : Math.min(Math.max(u, uLo), uHi),
    isFirst ? 0 : Math.min(Math.max(n, nLo), nHi),
  ];
}

export function DensityEditor({
  turns,
  pathLength,
  prefix,
  winding,
  onChange,
}: {
  turns: TurnProfileSchema;
  /** Arc length of the winding path, SI — positions display as u * length. */
  pathLength: number;
  prefix: string;
  winding: 'secondary' | 'primary';
  onChange: (turns: TurnProfileSchema) => void;
}) {
  const [plotOpen, setPlotOpen] = useState(true);
  const [highlight, setHighlight] = useState<number | null>(null);

  const mark = turns.kind === 'graded' ? unvalidatedFeature(`graded-${winding}-turns`) : null;

  const patchPoint = (points: GradedPoint[], i: number, u: number, n: number) => {
    const next = points.map((p, j) => (j === i ? clampPoint(points, i, u, n) : p));
    onChange({ kind: 'graded', points: next });
  };

  return (
    <>
      <SelectField
        label="winding density"
        value={turns.kind}
        options={['uniform', 'graded'] as const}
        onChange={(kind) => onChange(convertTurns(turns, kind))}
        testId={`${prefix}-density-kind`}
        unvalidated={mark}
      />

      {turns.kind === 'uniform' ? (
        <NumberField
          label="turns"
          value={turns.total_turns}
          min={0}
          onCommit={(total_turns) => onChange({ kind: 'uniform', total_turns })}
          testId={`${prefix}-turns`}
        />
      ) : (
        <GradedEditor
          turns={turns}
          pathLength={pathLength}
          prefix={prefix}
          plotOpen={plotOpen}
          setPlotOpen={setPlotOpen}
          highlight={highlight}
          setHighlight={setHighlight}
          patchPoint={patchPoint}
          onChange={onChange}
        />
      )}
    </>
  );
}

function GradedEditor({
  turns,
  pathLength,
  prefix,
  plotOpen,
  setPlotOpen,
  highlight,
  setHighlight,
  patchPoint,
  onChange,
}: {
  turns: GradedTurnProfileSchema;
  pathLength: number;
  prefix: string;
  plotOpen: boolean;
  setPlotOpen: (v: boolean) => void;
  highlight: number | null;
  setHighlight: (v: number | null) => void;
  patchPoint: (points: GradedPoint[], i: number, u: number, n: number) => void;
  onChange: (turns: TurnProfileSchema) => void;
}) {
  const points = turns.points as GradedPoint[];

  const addPoint = () => {
    // Insert at the midpoint of the widest position gap.
    let gapAt = 1;
    let gapSize = -1;
    for (let i = 1; i < points.length; i++) {
      const g = points[i]![0] - points[i - 1]![0];
      if (g > gapSize) {
        gapSize = g;
        gapAt = i;
      }
    }
    const a = points[gapAt - 1]!;
    const b = points[gapAt]!;
    const mid: GradedPoint = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
    onChange({
      kind: 'graded',
      points: [...points.slice(0, gapAt), mid, ...points.slice(gapAt)],
    });
  };

  const removePoint = (i: number) =>
    onChange({ kind: 'graded', points: points.filter((_, j) => j !== i) });

  return (
    <div className="density-editor" data-testid={`${prefix}-density-editor`}>
      <div className="field-note">
        cumulative turns at positions along the winding
        <button
          type="button"
          className="link-btn"
          style={{ float: 'right' }}
          onClick={() => setPlotOpen(!plotOpen)}
          data-testid={`${prefix}-density-plot-toggle`}
        >
          {plotOpen ? 'hide plot' : 'show plot'}
        </button>
      </div>

      {plotOpen && (
        <DensityPlot
          points={points}
          highlight={highlight}
          setHighlight={setHighlight}
          onDrag={(i, u, n) => patchPoint(points, i, u, n)}
          testId={`${prefix}-density-plot`}
        />
      )}

      {points.map((p, i) => {
        const first = i === 0;
        const last = i === points.length - 1;
        return (
          <div
            className={`field-row vertex-row${highlight === i ? ' highlighted' : ''}`}
            key={i}
            data-testid={`${prefix}-density-row-${i}`}
            onMouseEnter={() => setHighlight(i)}
            onMouseLeave={() => setHighlight(null)}
          >
            <QuantityField
              label={`position`}
              kind="length"
              fieldId={`${prefix}-density-${i}-pos`}
              value={p[0] * pathLength}
              min={0}
              onCommit={(v) => {
                if (first || last) return; // endpoints are pinned to 0 and L
                patchPoint(points, i, pathLength > 0 ? v / pathLength : 0, p[1]);
              }}
              testId={`${prefix}-density-${i}-pos`}
            />
            <NumberField
              label="turns"
              value={p[1]}
              min={0}
              displayPrecision={5}
              onCommit={(n) => {
                if (first) return; // the winding starts at zero turns
                patchPoint(points, i, p[0], n);
              }}
              testId={`${prefix}-density-${i}-turns`}
            />
            <button
              type="button"
              className="link-btn"
              title="Delete point"
              disabled={first || last}
              onClick={() => removePoint(i)}
              data-testid={`${prefix}-density-${i}-del`}
            >
              ✕
            </button>
          </div>
        );
      })}
      <button
        type="button"
        className="link-btn add-vertex"
        data-testid={`${prefix}-density-add`}
        onClick={addPoint}
      >
        + add point
      </button>
    </div>
  );
}

const PLOT_W = 260;
const PLOT_H = 130;
const PAD = { left: 10, right: 10, top: 10, bottom: 14 };

function DensityPlot({
  points,
  highlight,
  setHighlight,
  onDrag,
  testId,
}: {
  points: GradedPoint[];
  highlight: number | null;
  setHighlight: (v: number | null) => void;
  onDrag: (i: number, u: number, n: number) => void;
  testId: string;
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const dragIndex = useRef<number | null>(null);

  // Turn axis auto-scales to the data with ~8% headroom.
  const nMax = Math.max(...points.map((p) => p[1]), 1) * 1.08;
  const toX = (u: number) => PAD.left + u * (PLOT_W - PAD.left - PAD.right);
  const toY = (n: number) => PLOT_H - PAD.bottom - (n / nMax) * (PLOT_H - PAD.top - PAD.bottom);

  const fromScreen = (evt: React.PointerEvent): [number, number] => {
    const svg = svgRef.current!;
    const rect = svg.getBoundingClientRect();
    const x = ((evt.clientX - rect.left) / rect.width) * PLOT_W;
    const y = ((evt.clientY - rect.top) / rect.height) * PLOT_H;
    const u = (x - PAD.left) / (PLOT_W - PAD.left - PAD.right);
    const n = ((PLOT_H - PAD.bottom - y) / (PLOT_H - PAD.top - PAD.bottom)) * nMax;
    return [Math.min(Math.max(u, 0), 1), Math.max(n, 0)];
  };

  return (
    <svg
      ref={svgRef}
      className="density-plot"
      viewBox={`0 0 ${PLOT_W} ${PLOT_H}`}
      data-testid={testId}
      style={{ width: '100%', touchAction: 'none' }}
      onPointerMove={(e) => {
        if (dragIndex.current == null) return;
        const [u, n] = fromScreen(e);
        onDrag(dragIndex.current, u, n);
      }}
      onPointerUp={(e) => {
        dragIndex.current = null;
        (e.target as Element).releasePointerCapture?.(e.pointerId);
      }}
    >
      {/* axes */}
      <line
        x1={PAD.left}
        y1={PLOT_H - PAD.bottom}
        x2={PLOT_W - PAD.right}
        y2={PLOT_H - PAD.bottom}
        className="density-plot-axis"
      />
      <line
        x1={PAD.left}
        y1={PAD.top}
        x2={PAD.left}
        y2={PLOT_H - PAD.bottom}
        className="density-plot-axis"
      />
      {/* cumulative turn curve (linear between control points) */}
      <polyline
        className="density-plot-curve"
        fill="none"
        points={points.map((p) => `${toX(p[0])},${toY(p[1])}`).join(' ')}
      />
      {points.map((p, i) => (
        <circle
          key={i}
          cx={toX(p[0])}
          cy={toY(p[1])}
          r={highlight === i ? 5 : 3.5}
          className={`density-plot-point${highlight === i ? ' highlighted' : ''}`}
          data-testid={`${testId}-point-${i}`}
          onPointerDown={(e) => {
            dragIndex.current = i;
            (e.target as Element).setPointerCapture?.(e.pointerId);
          }}
          onPointerEnter={() => setHighlight(i)}
          onPointerLeave={() => setHighlight(null)}
        />
      ))}
    </svg>
  );
}
