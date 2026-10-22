/**
 * Operating-mode pane: the driven phasor profiles along the secondary at a
 * chosen drive frequency and primary current — the SAME solve that seeds the
 * field visualization, exposed as plots (real volts and amps, unlike the
 * eigenmode pane's arbitrary-scale shapes).
 *
 * Inputs mirror the field view's Operating point block (frequency with the
 * Lower/Upper/f₀ presets and auto-default to the lower split mode, plus
 * primary current) but are deliberately independent of the field drive's
 * values. All phasors are referenced to the primary current (phase 0).
 *
 * The backend is only asked for the unit-current (1 A) response at the chosen
 * frequency; the system is linear in the drive current, so the primary-current
 * input scales the phasors client-side and re-plots instantly.
 *
 * Three plot styles over the same response. The stroke of every 2-D panel is
 * shaded by local phase (Mathematica ComplexPlot gradient, branch cut at ±π)
 * with a colorbar on the right:
 *  - phase-colored: static |V| and |I| vs arc length;
 *  - transient profile: the instantaneous values Re[X̂(s)e^{jωt}] inside
 *    dashed ±|X̂| envelopes on symmetric axes;
 *  - transient phasors: one wide orbitable 3-D scene with both curves over
 *    the s (arc length) axis, color-keyed V vs I, with EM-wave-style vectors
 *    from the axis to every sample. Scene mapping: +Im up, +Re away from the
 *    default viewpoint, so looking back along +s shows a conventional
 *    complex plane.
 *
 * The two transient styles carry a Desmos-style looping time slider (paused
 * at t = 0 by default) spanning one drive period T = 1/f. The steady state
 * at time t is exactly the phasor rotated by e^{jωt} (ωt = 2π·t/T): the
 * profile curves move inside their envelopes and the 3-D curves rotate
 * rigidly about the arc-length axis. Their axes are fixed over the whole
 * cycle, so nothing jumps when playback starts. Playback speed is wall-clock
 * (seconds per cycle), independent of the actual drive frequency.
 */
import { useEffect, useMemo, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { Line as DreiLine, Html, OrbitControls } from '@react-three/drei';
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import type { CoilSchema, MatrixBundle } from '../api/client';
import { useDrive } from '../api/simulation';
import { phaseColorCss, phaseStops } from '../field/phaseColor';
import { useEditorStore } from '../state/store';
import { useThemeColors } from '../theme';
import { QuantityField, SelectField } from './fields';
import { eng, hz } from './format';

type PlotStyle = 'phase-colored' | 'transient profile' | 'transient phasors';
const PLOT_STYLES: readonly PlotStyle[] = ['phase-colored', 'transient profile', 'transient phasors'];

/** Wall-clock seconds for one drive period at 1× playback. */
const SECONDS_PER_CYCLE = 4;
const SPEEDS = [0.25, 0.5, 1, 2, 4];

interface Series {
  positions: number[];
  re: number[];
  im: number[];
  abs: number[];
  /** Phase in (−π, π], or null where the magnitude is numerically zero
   *  (the grounded base node) and the phase is meaningless. */
  phase: (number | null)[];
}

function toSeries(positions: number[], re: number[], im: number[], scale: number): Series {
  const sre = re.map((r) => r * scale);
  const sim = im.map((v) => v * scale);
  const abs = sre.map((r, i) => Math.hypot(r, sim[i]!));
  const floor = 1e-12 * Math.max(...abs, 0);
  return {
    positions,
    re: sre,
    im: sim,
    abs,
    // scale > 0 never moves the phase; computed after scaling only so the
    // zero-magnitude mask and abs come from the same numbers.
    phase: sre.map((r, i) => (abs[i]! > floor ? Math.atan2(sim[i]!, r) : null)),
  };
}

/** One recharts row per sample. `val` is what the main line draws: the
 *  magnitude, or the instantaneous value Re[X̂e^{jθ}] when animating (with
 *  ±abs as the envelope). */
interface Row {
  pos: number;
  abs: number;
  negAbs: number;
  phase: number | null;
  val: number;
}

function toRows(s: Series, theta: number | null): Row[] {
  const cos = theta == null ? 1 : Math.cos(theta);
  const sin = theta == null ? 0 : Math.sin(theta);
  return s.positions.map((pos, i) => ({
    pos,
    abs: s.abs[i]!,
    negAbs: -s.abs[i]!,
    phase: s.phase[i]!,
    // Re[(re + j·im)(cosθ + j·sinθ)] = re·cosθ − im·sinθ
    val: theta == null ? s.abs[i]! : s.re[i]! * cos - s.im[i]! * sin,
  }));
}

export function OperatingModePane({
  coil,
  bundle,
}: {
  coil: CoilSchema;
  bundle: MatrixBundle | null | undefined;
}) {
  const driveIn = useEditorStore((s) => s.operatingDrive);
  const setDrive = useEditorStore((s) => s.setOperatingDrive);
  const analysis = useEditorStore((s) => s.analysis);
  const [style, setStyle] = useState<PlotStyle>('phase-colored');

  // Animation over one drive period: tau is the cycle fraction t/T in [0, 1).
  // Only the transient styles show the slider and evolve in time; the
  // phase-colored style is the static magnitude view.
  const transient = style !== 'phase-colored';
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [tau, setTau] = useState(0);
  useEffect(() => {
    if (!playing || !transient) return;
    let raf = 0;
    let last = performance.now();
    const tick = (now: number) => {
      const dt = (now - last) / 1000;
      last = now;
      setTau((t) => (t + (dt * speed) / SECONDS_PER_CYCLE) % 1);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [playing, transient, speed]);
  const theta = transient ? 2 * Math.PI * tau : null;

  const coupled = analysis?.coupled ?? null;
  const secRes = analysis?.secondary.resonant_frequency ?? null;
  const presets: { label: string; hz: number }[] = [];
  if (coupled) {
    presets.push({ label: 'Lower', hz: coupled.split_lower });
    presets.push({ label: 'Upper', hz: coupled.split_upper });
  }
  if (secRes) presets.push({ label: 'f₀', hz: secRes });

  const effective =
    driveIn.frequencyHz > 0 ? driveIn.frequencyHz : (coupled?.split_lower ?? secRes ?? 0);

  // The query always solves at 1 A; the current input only rescales below.
  const query = useDrive(coil, bundle, effective);
  const d = query.data;
  const amps = driveIn.primaryCurrent;

  const voltage = useMemo(
    () => (d ? toSeries(d.voltage_positions, d.voltage_real, d.voltage_imag, amps) : null),
    [d, amps],
  );
  const current = useMemo(
    () => (d ? toSeries(d.current_positions, d.current_real, d.current_imag, amps) : null),
    [d, amps],
  );
  const vRows = useMemo(() => (voltage ? toRows(voltage, theta) : []), [voltage, theta]);
  const iRows = useMemo(() => (current ? toRows(current, theta) : []), [current, theta]);

  // Shared x-axis across every stacked panel: the winding length (the last
  // voltage node), with the same ticks so the panels read as one figure.
  const xMax = d ? d.voltage_positions[d.voltage_positions.length - 1] || 1 : 1;
  const xTicks = useMemo(() => Array.from({ length: 5 }, (_, i) => (xMax * i) / 4), [xMax]);

  const period = d ? 1 / d.frequency_hz : 0;
  const panel = { xMax, xTicks };

  return (
    <div data-testid="operating-mode">
      <div className="opmode-controls">
        <QuantityField
          label="frequency"
          kind="frequency"
          fieldId="opmode-frequency"
          defaultUnit="kHz"
          value={effective}
          min={0}
          onCommit={(v) => setDrive({ frequencyHz: Math.max(0, v) })}
          testId="opmode-frequency"
        />
        <QuantityField
          label="primary current"
          kind="current"
          fieldId="opmode-current"
          value={driveIn.primaryCurrent}
          min={0}
          onCommit={(primaryCurrent) => setDrive({ primaryCurrent })}
          testId="opmode-current"
        />
        <SelectField
          label="plot style"
          value={style}
          options={PLOT_STYLES}
          onChange={setStyle}
          testId="opmode-style"
        />
      </div>
      {presets.length > 0 && (
        <div className="preset-row" data-testid="opmode-presets">
          {presets.map((p) => (
            <button
              key={p.label}
              type="button"
              className="link-btn"
              data-testid={`opmode-preset-${p.label}`}
              onClick={() => setDrive({ frequencyHz: p.hz })}
            >
              {p.label} ({(p.hz / 1e3).toFixed(1)} kHz)
            </button>
          ))}
        </div>
      )}

      {query.isError && (
        <p className="muted" data-testid="opmode-error">
          Could not compute the operating mode: {String(query.error)}
        </p>
      )}

      {d && voltage && current ? (
        <>
          <div className="opmode-readouts" data-testid="opmode-readouts">
            <span>
              |V<sub>top</sub>| = <b data-testid="opmode-vtop">{eng(voltage.abs[voltage.abs.length - 1]!, 'V')}</b>
            </span>
            <span>
              |I<sub>base</sub>| = <b>{eng(current.abs[0]!, 'A')}</b>
            </span>
            <span>
              |V<sub>p</sub>| = <b>{eng(amps * Math.hypot(d.primary_voltage_real, d.primary_voltage_imag), 'V')}</b>
            </span>
            <span>
              T = <b data-testid="opmode-period">{eng(period, 's')}</b>
            </span>
            <span className="muted">phase reference: primary current · {hz(d.frequency_hz)}</span>
            <span className="opmode-spacer" />
            <button
              type="button"
              className="eigen-csv-btn"
              data-testid="opmode-csv"
              onClick={() => exportCsv(d.frequency_hz, amps, d, voltage, current)}
            >
              Export CSV
            </button>
          </div>

          {transient && (
            <TimeSlider
              playing={playing}
              onPlaying={setPlaying}
              speed={speed}
              onSpeed={setSpeed}
              tau={tau}
              onTau={setTau}
              period={period}
            />
          )}

          {style === 'phase-colored' && (
            <div className="opmode-body">
              <div className="opmode-plots">
                <MagPanel rows={vRows} {...panel} animating={false} name="|V|" unit="V" showXLabel={false} testId="opmode-v-mag" />
                <MagPanel rows={iRows} {...panel} animating={false} name="|I|" unit="A" showXLabel testId="opmode-i-mag" />
              </div>
              <PhaseColorbar />
            </div>
          )}

          {style === 'transient profile' && (
            <div className="opmode-body">
              <div className="opmode-plots">
                <MagPanel rows={vRows} {...panel} animating name="V(t)" unit="V" showXLabel={false} testId="opmode-v-mag" />
                <MagPanel rows={iRows} {...panel} animating name="I(t)" unit="A" showXLabel testId="opmode-i-mag" />
              </div>
              <PhaseColorbar />
            </div>
          )}

          {style === 'transient phasors' && (
            <PhasorScene voltage={voltage} current={current} theta={theta ?? 0} />
          )}
        </>
      ) : (
        !query.isError && <p className="muted">Computing the operating mode…</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Desmos-style time slider: round play/pause, cycling speed chip, t readout,
// and a looping 0 → T range.
// ---------------------------------------------------------------------------

function TimeSlider({
  playing,
  onPlaying,
  speed,
  onSpeed,
  tau,
  onTau,
  period,
}: {
  playing: boolean;
  onPlaying: (p: boolean) => void;
  speed: number;
  onSpeed: (s: number) => void;
  tau: number;
  onTau: (t: number) => void;
  period: number;
}) {
  const cycleSpeed = () => onSpeed(SPEEDS[(SPEEDS.indexOf(speed) + 1) % SPEEDS.length]!);
  return (
    <div className="opmode-anim" data-testid="opmode-anim">
      <button
        type="button"
        className="opmode-play"
        data-testid="opmode-play"
        title={playing ? 'Pause' : 'Play'}
        onClick={() => onPlaying(!playing)}
      >
        {playing ? (
          <svg width="10" height="12" viewBox="0 0 10 12" aria-label="pause">
            <rect x="0" y="0" width="3.4" height="12" fill="currentColor" />
            <rect x="6.6" y="0" width="3.4" height="12" fill="currentColor" />
          </svg>
        ) : (
          <svg width="11" height="12" viewBox="0 0 11 12" aria-label="play">
            <path d="M1 0.5 L10.5 6 L1 11.5 Z" fill="currentColor" />
          </svg>
        )}
      </button>
      <button
        type="button"
        className="opmode-speed"
        data-testid="opmode-speed"
        title="Playback speed (wall-clock; one cycle takes 4 s at 1×)"
        onClick={cycleSpeed}
      >
        {speed}×
      </button>
      <span className="opmode-t" data-testid="opmode-t">
        t = {eng(tau * period, 's')}
      </span>
      <span className="opmode-anim-end">0</span>
      <input
        type="range"
        className="opmode-slider"
        data-testid="opmode-slider"
        min={0}
        max={1}
        step={0.001}
        value={tau}
        onChange={(e) => onTau(Number(e.target.value) % 1)}
      />
      <span className="opmode-anim-end">T</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// CSV export
// ---------------------------------------------------------------------------

function exportCsv(
  frequencyHz: number,
  amps: number,
  d: { primary_voltage_real: number; primary_voltage_imag: number },
  voltage: Series,
  current: Series,
) {
  const section = (title: string, s: Series) => {
    const rows = s.positions.map((p, i) =>
      [p, s.re[i], s.im[i], s.abs[i], s.phase[i] ?? ''].join(','),
    );
    return [title, 'arc_length_m,real,imag,abs,phase_rad', ...rows].join('\n');
  };
  const meta = [
    `frequency_hz,${frequencyHz}`,
    `primary_current_a,${amps}`,
    `primary_voltage_real,${amps * d.primary_voltage_real}`,
    `primary_voltage_imag,${amps * d.primary_voltage_imag}`,
    'phase_reference,primary current',
  ].join('\n');
  const csv = [meta, '', section('Voltage (V)', voltage), '', section('Current (A)', current)].join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'operating-mode.csv';
  a.click();
  URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------------------
// recharts panels (same stack and styling as the eigenmode pane)
// ---------------------------------------------------------------------------

const X_LABEL = 'Arc length along winding (base → top)';

/** One y-axis width for every panel so the stacked x-axes align. Wide enough
 *  that the rotated axis title clears tick labels like "900 MV". */
const Y_AXIS_WIDTH = 78;

function phaseText(phi: number): string {
  return `${(phi / Math.PI).toFixed(2)}π rad`;
}

function PanelXAxis({
  xMax,
  xTicks,
  showXLabel,
  stroke,
}: {
  xMax: number;
  xTicks: number[];
  showXLabel: boolean;
  stroke: string;
}) {
  return (
    <XAxis
      dataKey="pos"
      type="number"
      domain={[0, xMax]}
      ticks={xTicks}
      stroke={stroke}
      tickFormatter={(v: number) => eng(v, 'm')}
      label={
        showXLabel
          ? { value: X_LABEL, position: 'insideBottom', offset: -8, fill: stroke }
          : undefined
      }
    />
  );
}
// recharts only honors axis children declared directly under the chart, so
// the shared axis is rendered through the element type, not as <PanelXAxis/>.
PanelXAxis.displayName = 'PanelXAxis';

/** Gradient stops along x, one per sample, colored by that sample's phase.
 *  Null phases (zero magnitude) borrow the nearest defined neighbor so the
 *  stroke never flashes an arbitrary color at the grounded base. */
function phaseGradientStops(rows: Row[]): { offset: number; color: string }[] {
  const filled = rows.map((r) => r.phase);
  for (let i = 0; i < filled.length; i++) {
    if (filled[i] == null) {
      const next = filled.slice(i + 1).find((p) => p != null);
      const prev = [...filled.slice(0, i)].reverse().find((p) => p != null);
      filled[i] = prev ?? next ?? 0;
    }
  }
  const s0 = rows[0]?.pos ?? 0;
  const span = (rows[rows.length - 1]?.pos ?? 1) - s0 || 1;
  return rows.map((r, i) => ({
    offset: (r.pos - s0) / span,
    color: phaseColorCss(filled[i]!),
  }));
}

/** Profile vs arc length, the line stroked with a per-sample gradient of the
 *  phase map (smoothly interpolated by the browser). Static mode plots the
 *  magnitude; animating mode plots the instantaneous value on a symmetric
 *  axis inside a dashed ±|X̂| envelope. The gradient keeps the PHASOR phase
 *  (the whole profile advances by the same ωt, so the relative coloring is
 *  time-invariant). */
function MagPanel({
  rows,
  xMax,
  xTicks,
  name,
  unit,
  showXLabel,
  animating,
  testId,
}: {
  rows: Row[];
  xMax: number;
  xTicks: number[];
  name: string;
  unit: string;
  showXLabel: boolean;
  animating: boolean;
  testId: string;
}) {
  const colors = useThemeColors();
  const gradId = `opmode-grad-${testId}`;
  const stops = useMemo(() => phaseGradientStops(rows), [rows]);
  const peak = rows.reduce((m, r) => Math.max(m, r.abs), 0) || 1;
  // Static: recharts' auto domain picks round ticks from 0. Animated: a
  // symmetric domain confuses its tick picker ("5.20 kV"), so pin ticks to
  // ±peak, ±peak/2 and 0.
  const yDomain: [number, number | 'auto'] = animating ? [-peak * 1.1, peak * 1.1] : [0, 'auto'];
  const yTicks = animating ? [-peak, -peak / 2, 0, peak / 2, peak] : undefined;
  return (
    <div className="opmode-chart" data-testid={testId}>
      <ResponsiveContainer>
        <LineChart data={rows} margin={{ top: 8, right: 12, bottom: showXLabel ? 20 : 0, left: 10 }}>
          <defs>
            {/* objectBoundingBox x spans exactly the data's x extent, so
                offsets are plain normalized arc length. */}
            <linearGradient id={gradId} x1="0" y1="0" x2="1" y2="0">
              {stops.map((s, i) => (
                <stop key={i} offset={`${(s.offset * 100).toFixed(4)}%`} stopColor={s.color} />
              ))}
            </linearGradient>
          </defs>
          <CartesianGrid stroke={colors.chartGrid} />
          {PanelXAxis({ xMax, xTicks, showXLabel, stroke: colors.chartAxis })}
          <YAxis
            stroke={colors.chartAxis}
            width={Y_AXIS_WIDTH}
            domain={yDomain}
            ticks={yTicks}
            tickMargin={4}
            tickFormatter={(v: number) => eng(v, unit)}
            label={{ value: `${name} (${unit})`, angle: -90, position: 'insideLeft', offset: 0, fill: colors.chartAxis }}
          />
          <Tooltip
            contentStyle={{ background: colors.tooltipBg, border: `1px solid ${colors.tooltipBorder}` }}
            formatter={(v: number, _n: string, item: { payload?: Row }) => {
              const phi = item.payload?.phase;
              return [phi == null ? eng(v, unit) : `${eng(v, unit)} ∠ ${phaseText(phi)}`, name];
            }}
            labelFormatter={(l: number) => eng(Number(l), 'm')}
          />
          {/* separate conditionals, not a fragment: recharts collects chart
              children by type and does not see through fragments */}
          {animating && <ReferenceLine y={0} stroke={colors.chartZero} />}
          {animating && <Line type="monotone" dataKey="abs" stroke={colors.chartAxis} strokeDasharray="4 4" strokeWidth={1} strokeOpacity={0.55} dot={false} isAnimationActive={false} tooltipType="none" />}
          {animating && <Line type="monotone" dataKey="negAbs" stroke={colors.chartAxis} strokeDasharray="4 4" strokeWidth={1} strokeOpacity={0.55} dot={false} isAnimationActive={false} tooltipType="none" />}
          <Line
            type="monotone"
            dataKey="val"
            name={name}
            stroke={`url(#${gradId})`}
            dot={false}
            strokeWidth={2.25}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Vertical colorbar for the phase map, −π at the bottom to π at the top. */
function PhaseColorbar() {
  const colors = useThemeColors();
  const stops = phaseStops();
  return (
    <div className="opmode-colorbar" data-testid="opmode-colorbar">
      <svg viewBox="0 0 46 170" width={46} height={170}>
        <defs>
          <linearGradient id="phase-grad" x1="0" y1="1" x2="0" y2="0">
            {stops.map((c, i) => (
              <stop
                key={i}
                offset={`${(i / (stops.length - 1)) * 100}%`}
                stopColor={`rgb(${c[0]}, ${c[1]}, ${c[2]})`}
              />
            ))}
          </linearGradient>
        </defs>
        <rect x={4} y={10} width={12} height={150} fill="url(#phase-grad)" rx={2} />
        {[
          [Math.PI, 'π'],
          [Math.PI / 2, 'π/2'],
          [0, '0'],
          [-Math.PI / 2, '−π/2'],
          [-Math.PI, '−π'],
        ].map(([v, label]) => {
          const y = 10 + ((Math.PI - (v as number)) / (2 * Math.PI)) * 150;
          return (
            <g key={label as string}>
              <line x1={16} x2={20} y1={y} y2={y} stroke={colors.chartAxis} />
              <text x={23} y={y + 3} fontSize={9} fill={colors.chartAxis}>
                {label}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="opmode-colorbar-label">arg</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 3-D phasor scene: ONE wide orbitable plot with both curves over the s (arc
// length) axis, each normalized to its own peak (scales in the key) and
// color-keyed V vs I (not phase-colored). EM-wave-style vectors run from the
// s axis to every sample. `theta` = ωt rotates everything rigidly about the
// s axis (the time evolution).
//
// Scene mapping: +Im is up and +Re points AWAY from the default viewpoint,
// so a viewer looking back along +s sees a conventional complex plane
// (Re right, Im up).
// ---------------------------------------------------------------------------

/** Half-length of the s axis in scene units (Re/Im span ±1). */
const SCENE_X = 2.9;

function scenePoints(s: Series, theta: number): [number, number, number][] {
  const peak = Math.max(...s.abs) || 1;
  const xMax = s.positions[s.positions.length - 1] || 1;
  const cos = Math.cos(theta);
  const sin = Math.sin(theta);
  return s.positions.map((p, i) => {
    const reT = s.re[i]! * cos - s.im[i]! * sin;
    const imT = s.re[i]! * sin + s.im[i]! * cos;
    // scene y = Im (up), scene z = −Re (so +Re points away from the camera)
    return [(p / xMax) * 2 * SCENE_X - SCENE_X, imT / peak, -reT / peak];
  });
}

/** Disjoint segments (point pairs) from the s axis to each curve sample. */
function vectorSegments(pts: [number, number, number][]): [number, number, number][] {
  return pts.flatMap((p): [number, number, number][] => [[p[0], 0, 0], p]);
}

function PhasorScene({
  voltage,
  current,
  theta,
}: {
  voltage: Series;
  current: Series;
  theta: number;
}) {
  const colors = useThemeColors();
  const vColor = colors.chartSeries[0]!;
  const iColor = colors.chartSeries[1]!;
  const vPoints = useMemo(() => scenePoints(voltage, theta), [voltage, theta]);
  const iPoints = useMemo(() => scenePoints(current, theta), [current, theta]);
  const vVectors = useMemo(() => vectorSegments(vPoints), [vPoints]);
  const iVectors = useMemo(() => vectorSegments(iPoints), [iPoints]);
  const vPeak = Math.max(...voltage.abs) || 1;
  const iPeak = Math.max(...current.abs) || 1;

  const axisColor = colors.chartAxis;
  const labelStyle = {
    color: axisColor,
    fontSize: '11px',
    whiteSpace: 'nowrap',
    pointerEvents: 'none',
  } as const;
  return (
    <div className="opmode-3d" data-testid="opmode-3d">
      {/* Pulled back far enough that the Re/Im axis labels at the base end
          stay in frame on the wide canvas. */}
      <Canvas camera={{ position: [0.9, 1.0, 4.1], fov: 36 }}>
        <ambientLight intensity={0.8} />
        {/* axes, each labeled at its positive end: s (x), Im (up), Re (away) */}
        <DreiLine points={[[-SCENE_X, 0, 0], [SCENE_X + 0.2, 0, 0]]} color={axisColor} lineWidth={1} />
        <DreiLine points={[[-SCENE_X, -1.15, 0], [-SCENE_X, 1.15, 0]]} color={axisColor} lineWidth={1} />
        <DreiLine points={[[-SCENE_X, 0, -1.15], [-SCENE_X, 0, 1.15]]} color={axisColor} lineWidth={1} />
        <Html position={[SCENE_X + 0.38, 0, 0]} center style={labelStyle} zIndexRange={[2, 0]}>
          s
        </Html>
        <Html position={[-SCENE_X, 1.32, 0]} center style={labelStyle} zIndexRange={[2, 0]}>
          Im
        </Html>
        <Html position={[-SCENE_X, 0, -1.32]} center style={labelStyle} zIndexRange={[2, 0]}>
          Re
        </Html>
        <DreiLine segments points={vVectors} color={vColor} lineWidth={1.1} transparent opacity={0.4} />
        <DreiLine segments points={iVectors} color={iColor} lineWidth={1.1} transparent opacity={0.4} />
        <DreiLine points={vPoints} color={vColor} lineWidth={3} />
        <DreiLine points={iPoints} color={iColor} lineWidth={3} />
        <OrbitControls enablePan={false} />
      </Canvas>
      <div className="opmode-3d-caption">
        <span className="opmode-swatch" style={{ background: vColor }} /> V (axis scale ±{eng(vPeak, 'V')})
        <span className="opmode-swatch" style={{ background: iColor }} /> I (axis scale ±{eng(iPeak, 'A')})
        <span className="muted"> · s = arc length along the winding (base → top)</span>
      </div>
    </div>
  );
}
