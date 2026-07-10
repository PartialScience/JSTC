/**
 * Eigenmode pane: plots the secondary's voltage and current mode shapes along
 * the winding (base -> top), stacked in two panels that share the position
 * axis. A chip selector chooses which modes are drawn (each keeps a stable
 * per-mode color), a legend to the right names each shown mode's eigen
 * frequency, and the CSV export writes every mode (not just the shown ones).
 */
import { useMemo, useState } from 'react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import type { EigenModesOutputs } from '../api/client';
import { useThemeColors } from '../theme';
import { eng, hz } from './format';

/** How many modes are shown by default: fundamental + first two overtones. */
const DEFAULT_SHOWN = 3;

/** A mode's stable color: indexed by mode number so it never changes as the
 *  selection changes. Cycles when there are more modes than palette entries. */
function seriesColor(series: string[], modeIndex: number): string {
  return series[modeIndex % series.length]!;
}

/** Compact frequency for the dense chip row (e.g. "285k", "1.2M"). */
function compactHz(f: number): string {
  if (f >= 1e6) return `${(f / 1e6).toFixed(f >= 1e7 ? 0 : 1)}M`;
  if (f >= 1e3) return `${(f / 1e3).toFixed(0)}k`;
  return `${f.toFixed(0)}`;
}

/** Peak-normalizing scale for one mode's samples (1 when not normalizing). */
function modeScale(values: number[], normalize: boolean): number {
  if (!normalize) return 1;
  let peak = 0;
  for (const v of values) peak = Math.max(peak, Math.abs(v));
  return peak > 0 ? 1 / peak : 1;
}

/** Compact y-axis tick text. Raw current amplitudes are tiny (~1e-5), so a
 *  plain decimal ("0.0000080") is wide enough to collide with the axis title;
 *  fall back to exponential ("8.0e-6") outside a comfortable mid range. */
function axisTick(v: number): string {
  if (v === 0) return '0';
  const a = Math.abs(v);
  return a < 1e-3 || a >= 1e4 ? v.toExponential(1) : v.toPrecision(2);
}

interface PanelProps {
  positions: number[];
  modeVectors: number[][];
  shown: number[];
  scales: number[];
  colors: string[];
  yLabel: string;
  showXLabel: boolean;
  xMax: number;
  xTicks: number[];
  chartAxis: string;
  chartGrid: string;
  tooltipBg: string;
  tooltipBorder: string;
  testId: string;
}

function ModePanel({
  positions,
  modeVectors,
  shown,
  scales,
  colors,
  yLabel,
  showXLabel,
  xMax,
  xTicks,
  chartAxis,
  chartGrid,
  tooltipBg,
  tooltipBorder,
  testId,
}: PanelProps) {
  // One row per winding position; each shown mode contributes a `m<idx>` key.
  const data = positions.map((pos, r) => {
    const row: Record<string, number> = { pos };
    for (const idx of shown) row[`m${idx}`] = modeVectors[idx]![r]! * scales[idx]!;
    return row;
  });

  return (
    <div className="eigen-panel" data-testid={testId}>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: showXLabel ? 20 : 0, left: 10 }}>
          <CartesianGrid stroke={chartGrid} />
          <XAxis
            dataKey="pos"
            type="number"
            domain={[0, xMax]}
            ticks={xTicks}
            stroke={chartAxis}
            tickFormatter={(v: number) => eng(v, 'm')}
            label={
              showXLabel
                ? { value: 'Arc length along winding (base → top)', position: 'insideBottom', offset: -8, fill: chartAxis }
                : undefined
            }
          />
          <YAxis
            stroke={chartAxis}
            width={64}
            tickMargin={4}
            tickFormatter={axisTick}
            label={{ value: yLabel, angle: -90, position: 'insideLeft', offset: 4, fill: chartAxis }}
          />
          <Tooltip
            contentStyle={{ background: tooltipBg, border: `1px solid ${tooltipBorder}` }}
            formatter={(v: number, name: string) => [v.toPrecision(4), name]}
            labelFormatter={(l: number) => eng(Number(l), 'm')}
          />
          {shown.map((idx) => (
            <Line
              key={idx}
              type="monotone"
              dataKey={`m${idx}`}
              name={`Mode ${idx + 1}`}
              stroke={seriesColor(colors, idx)}
              dot={false}
              strokeWidth={1.75}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function EigenModesChart({ modes }: { modes: EigenModesOutputs }) {
  const colors = useThemeColors();
  const count = modes.frequencies.length;

  const [selected, setSelected] = useState<Set<number>>(
    () => new Set(Array.from({ length: Math.min(DEFAULT_SHOWN, count) }, (_, i) => i)),
  );
  const [normalize, setNormalize] = useState(false);

  const shown = useMemo(
    () => [...selected].filter((i) => i < count).sort((a, b) => a - b),
    [selected, count],
  );

  // Shared x-axis: arc length (m) from base to the top node (= winding length).
  // Both panels use the same span and ticks so they read as one figure.
  const xMax = modes.voltage_positions[modes.voltage_positions.length - 1] ?? 1;
  const xTicks = useMemo(
    () => Array.from({ length: 5 }, (_, i) => (xMax * i) / 4),
    [xMax],
  );

  const voltageScales = useMemo(
    () => modes.voltage_modes.map((m) => modeScale(m, normalize)),
    [modes.voltage_modes, normalize],
  );
  const currentScales = useMemo(
    () => modes.current_modes.map((m) => modeScale(m, normalize)),
    [modes.current_modes, normalize],
  );

  const toggle = (idx: number) =>
    setSelected((s) => {
      const next = new Set(s);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });

  const exportCsv = () => {
    const header = ['arc_length_m', ...modes.frequencies.map((f, i) => `mode ${i + 1} (${hz(f)})`)].join(',');
    const section = (positions: number[], vectors: number[][], title: string) => {
      const rows = positions.map((p, r) => [p, ...vectors.map((m) => m[r])].join(','));
      return [title, header, ...rows].join('\n');
    };
    const csv = [
      section(modes.voltage_positions, modes.voltage_modes, 'Voltage eigenmodes (raw, sign-fixed)'),
      '',
      section(modes.current_positions, modes.current_modes, 'Current eigenmodes (raw, sign-fixed)'),
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'eigenmodes.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div data-testid="eigenmodes">
      <div className="eigen-controls">
        <label className="eigen-normalize">
          <input
            type="checkbox"
            data-testid="eigen-normalize"
            checked={normalize}
            onChange={(e) => setNormalize(e.target.checked)}
          />
          Normalize (unit peak)
        </label>
        <div className="eigen-spacer" />
        <button type="button" className="link-btn" data-testid="eigen-all" onClick={() => setSelected(new Set(Array.from({ length: count }, (_, i) => i)))}>
          All
        </button>
        <button type="button" className="link-btn" data-testid="eigen-none" onClick={() => setSelected(new Set())}>
          None
        </button>
        <button type="button" className="eigen-csv-btn" data-testid="eigen-csv" onClick={exportCsv} title="Download all modes as CSV">
          Export CSV
        </button>
      </div>

      <div className="eigen-chips" data-testid="eigen-selector">
        {modes.frequencies.map((f, idx) => {
          const on = selected.has(idx);
          return (
            <button
              key={idx}
              type="button"
              className={on ? 'eigen-chip on' : 'eigen-chip'}
              style={on ? { borderColor: seriesColor(colors.chartSeries, idx) } : undefined}
              title={`Mode ${idx + 1} — ${hz(f)}`}
              onClick={() => toggle(idx)}
            >
              <span className="eigen-dot" style={{ background: seriesColor(colors.chartSeries, idx) }} />
              {compactHz(f)}
            </button>
          );
        })}
      </div>

      <div className="eigen-body">
        <div className="eigen-plots">
          <ModePanel
            positions={modes.voltage_positions}
            modeVectors={modes.voltage_modes}
            shown={shown}
            scales={voltageScales}
            colors={colors.chartSeries}
            yLabel={normalize ? 'Voltage (norm.)' : 'Voltage (a.u.)'}
            showXLabel={false}
            xMax={xMax}
            xTicks={xTicks}
            chartAxis={colors.chartAxis}
            chartGrid={colors.chartGrid}
            tooltipBg={colors.tooltipBg}
            tooltipBorder={colors.tooltipBorder}
            testId="eigen-voltage"
          />
          <ModePanel
            positions={modes.current_positions}
            modeVectors={modes.current_modes}
            shown={shown}
            scales={currentScales}
            colors={colors.chartSeries}
            yLabel={normalize ? 'Current (norm.)' : 'Current (a.u.)'}
            showXLabel
            xMax={xMax}
            xTicks={xTicks}
            chartAxis={colors.chartAxis}
            chartGrid={colors.chartGrid}
            tooltipBg={colors.tooltipBg}
            tooltipBorder={colors.tooltipBorder}
            testId="eigen-current"
          />
        </div>

        <div className="eigen-legend" data-testid="eigen-legend">
          {shown.length === 0 ? (
            <p className="muted">Select a mode to plot.</p>
          ) : (
            shown.map((idx) => (
              <div key={idx} className="eigen-legend-row">
                <span className="eigen-swatch" style={{ background: seriesColor(colors.chartSeries, idx) }} />
                <span className="eigen-legend-label">Mode {idx + 1}</span>
                <span className="eigen-legend-freq">{hz(modes.frequencies[idx]!)}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
