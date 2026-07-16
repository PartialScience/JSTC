/**
 * Results section (below the 100vh editor). Every available output label is
 * shown at all times; values fill in after the user runs the calculation
 * (the FEM solve is expensive, so it is on-demand, not per-edit). The
 * impedance sweep and SPICE export reuse the analysis bundle.
 */
import { useMemo, useState, type JSX } from 'react';
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

import type {
  AnalysisResponse,
  CoilSchema,
  CouplingOutputs,
  CoupledOutputs,
  MatrixBundle,
  PrimaryOutputs,
  SecondaryOutputs,
} from '../api/client';
import { useImpedance, useSpice } from '../api/simulation';
import { useEditorStore } from '../state/store';
import { useThemeColors } from '../theme';
import {
  outputParts,
  outputUnitChoices,
  resolveOutputPref,
  type OutputUnitPref,
  type QuantityKind,
} from '../units/units';
import { EigenModesChart } from './EigenModes';
import { MatrixViewer } from './MatrixViewer';
import { eng } from './format';

// A field descriptor: how to pull a scalar out of an outputs object and
// format it. `get` may return null/undefined (value not available). A field
// either carries a physical `kind` (formatted via the unit preferences, with a
// clickable unit) or a bespoke `fmt` (dimensionless: Q, k, %, °, turns/length).
interface Field<T> {
  label: string;
  get: (o: T) => number | null | undefined;
  kind?: QuantityKind;
  fmt?: (v: number) => string;
  testId?: string;
}

const num = (digits: number, suffix = '') => (v: number) =>
  `${v.toFixed(digits)}${suffix}`;

const SECONDARY_FIELDS: Field<SecondaryOutputs>[] = [
  { label: 'Resonant frequency', get: (o) => o.resonant_frequency, kind: 'frequency', testId: 'res-fres' },
  { label: '2nd Harmonic', get: (o) => o.eigen_frequencies?.[1], kind: 'frequency' },
  { label: '3rd Harmonic', get: (o) => o.eigen_frequencies?.[2], kind: 'frequency' },
  { label: 'Les (series L)', get: (o) => o.effective_series_inductance, kind: 'inductance' },
  { label: 'Lee (energy L)', get: (o) => o.energy_inductance, kind: 'inductance' },
  { label: 'Ldc', get: (o) => o.dc_inductance, kind: 'inductance' },
  { label: 'Ces (shunt C)', get: (o) => o.effective_shunt_capacitance, kind: 'capacitance' },
  { label: 'Cee (energy C)', get: (o) => o.energy_capacitance, kind: 'capacitance' },
  { label: 'Cdc', get: (o) => o.dc_capacitance, kind: 'capacitance' },
  { label: 'Topload C', get: (o) => o.topload_effective_capacitance, kind: 'capacitance' },
  { label: 'Reactance @ res', get: (o) => o.reactance_at_resonance, kind: 'resistance' },
  { label: 'DC resistance', get: (o) => o.dc_resistance, kind: 'resistance' },
  { label: 'AC resistance', get: (o) => o.ac_resistance, kind: 'resistance' },
  { label: 'Q factor', get: (o) => o.quality_factor, fmt: num(0) },
  { label: 'Skin depth', get: (o) => o.skin_depth, kind: 'length' },
  { label: 'Winding length', get: (o) => o.winding_length, kind: 'length' },
  { label: 'Wire length', get: (o) => o.conductor_length, kind: 'length' },
  { label: 'Coil pitch', get: (o) => o.coil_pitch, kind: 'length' },
  { label: 'Turns / length', get: (o) => o.turns_per_length, fmt: num(0, ' /m') },
  { label: 'Turn spacing', get: (o) => o.turn_spacing, kind: 'length' },
  { label: 'Mean diameter', get: (o) => o.mean_diameter, kind: 'length' },
  { label: 'H/D aspect', get: (o) => o.aspect_ratio, fmt: num(2) },
  { label: 'Inclination', get: (o) => o.inclination_degrees, fmt: num(0, '°') },
  { label: 'Wire weight', get: (o) => o.wire_weight, kind: 'mass' },
];

const PRIMARY_FIELDS: Field<PrimaryOutputs>[] = [
  { label: 'Resonant frequency', get: (o) => o.resonant_frequency, kind: 'frequency', testId: 'res-pfres' },
  { label: 'Ldc (winding)', get: (o) => o.dc_inductance, kind: 'inductance' },
  { label: 'Lead inductance', get: (o) => o.lead_inductance, kind: 'inductance' },
  { label: 'Total inductance', get: (o) => o.total_inductance, kind: 'inductance' },
  { label: 'Detuned', get: (o) => o.percent_detuned, fmt: num(1, ' %') },
  { label: 'Wire length', get: (o) => o.wire_length, kind: 'length' },
  { label: 'Coil pitch', get: (o) => o.coil_pitch, kind: 'length' },
  { label: 'Turn spacing', get: (o) => o.turn_spacing, kind: 'length' },
  { label: 'DC resistance', get: (o) => o.dc_resistance, kind: 'resistance' },
];

const COUPLING_FIELDS: Field<CouplingOutputs>[] = [
  { label: 'k (coupling)', get: (o) => o.coupling_coefficient, fmt: num(3), testId: 'res-k' },
  { label: 'Lm (mutual)', get: (o) => o.mutual_inductance, kind: 'inductance' },
  { label: 'Transfer half-cycles', get: (o) => o.half_cycles_for_energy_transfer, fmt: num(1) },
  { label: 'Transfer time', get: (o) => o.energy_transfer_time, kind: 'time' },
];

const COUPLED_FIELDS: Field<CoupledOutputs>[] = [
  { label: 'Lower mode', get: (o) => o.split_lower, kind: 'frequency', testId: 'res-split-lower' },
  { label: 'Upper mode', get: (o) => o.split_upper, kind: 'frequency', testId: 'res-split-upper' },
  { label: 'Frequency split', get: (o) => o.frequency_split, kind: 'frequency' },
];

/** The clickable unit on an output value: opens a small menu to pin the display
 *  unit for this one value (each result value is independently unit-able). */
function OutputUnit({
  fieldId,
  kind,
  pref,
  label,
}: {
  fieldId: string;
  kind: QuantityKind;
  pref: OutputUnitPref;
  label: string;
}) {
  const setOutputUnit = useEditorStore((s) => s.setOutputUnit);
  const [open, setOpen] = useState(false);
  const choices = outputUnitChoices(kind);

  return (
    <span className="unit-picker">
      <button
        type="button"
        className="unit-btn"
        title="Change unit"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        {label}
      </button>
      {open && (
        <>
          <div className="dropdown-backdrop" onClick={() => setOpen(false)} />
          <div className="dropdown-menu unit-menu" role="menu">
            {choices.map((c) => (
              <button
                key={c.value}
                type="button"
                role="menuitemradio"
                aria-checked={pref === c.value}
                className="dropdown-item"
                onClick={() => {
                  setOutputUnit(fieldId, c.value);
                  setOpen(false);
                }}
              >
                <span className="check">{pref === c.value ? '✓' : ''}</span>
                {c.label}
              </button>
            ))}
          </div>
        </>
      )}
    </span>
  );
}

/** The formatted value + clickable unit for a physical output. Reads this
 *  value's own display preference (falling back to the system baseline). */
function UnitValue({
  value,
  kind,
  fieldId,
  testId,
}: {
  value: number;
  kind: QuantityKind;
  fieldId: string;
  testId?: string;
}) {
  const pref: OutputUnitPref = useEditorStore((s) => resolveOutputPref(s.unitPrefs, fieldId, kind));
  const parts = outputParts(value, kind, pref);
  return (
    <span className="stat-value" data-testid={testId}>
      {parts.value}{' '}
      {parts.unit && <OutputUnit fieldId={fieldId} kind={kind} pref={pref} label={parts.unit} />}
    </span>
  );
}

/** Global Imperial / SI output-unit presets. SI puts every kind on automatic
 *  engineering-prefixed SI; Imperial switches lengths (mil/in/ft) and mass (lb)
 *  to imperial and leaves the electrical kinds on SI (they have no imperial
 *  form). These affect the displayed outputs only, not the input fields. */
function UnitSystemButtons() {
  const system = useEditorStore((s) => s.unitPrefs.system);
  const setUnitSystem = useEditorStore((s) => s.setUnitSystem);
  const isSI = system === 'SI';
  const isImperial = system === 'imperial';

  return (
    <div className="unit-system" role="group" aria-label="Output units">
      <button
        type="button"
        className={isSI ? 'unit-system-btn active' : 'unit-system-btn'}
        data-testid="units-si"
        aria-pressed={isSI}
        title="Show all outputs in SI units"
        onClick={() => setUnitSystem('SI')}
      >
        SI
      </button>
      <button
        type="button"
        className={isImperial ? 'unit-system-btn active' : 'unit-system-btn'}
        data-testid="units-imperial"
        aria-pressed={isImperial}
        title="Show lengths and mass in imperial units"
        onClick={() => setUnitSystem('imperial')}
      >
        Imperial
      </button>
    </div>
  );
}

function Stat<T>({
  field,
  data,
  fieldId,
}: {
  field: Field<T>;
  data: T | null | undefined;
  fieldId: string;
}) {
  const value = data == null ? null : field.get(data);
  const available = value != null && Number.isFinite(value);
  return (
    <div className="stat">
      <div className="stat-label">{field.label}</div>
      {available && field.kind ? (
        <UnitValue value={value} kind={field.kind} fieldId={fieldId} testId={field.testId} />
      ) : (
        <div className="stat-value" data-testid={field.testId}>
          {available ? (field.fmt ? field.fmt(value) : String(value)) : '—'}
        </div>
      )}
    </div>
  );
}

function Card<T>({
  title,
  fields,
  data,
}: {
  title: string;
  fields: Field<T>[];
  data: T | null | undefined;
}) {
  return (
    <div className="result-card">
      <h3>{title}</h3>
      <div className="stat-grid">
        {fields.map((f) => (
          // Field id is stable per value (card + label) so each result value
          // remembers its own unit independently.
          <Stat key={f.label} field={f} data={data} fieldId={`${title}.${f.label}`} />
        ))}
      </div>
    </div>
  );
}

interface SweepRange {
  fminKhz: number;
  fmaxKhz: number;
  points: number;
}

const MIN_POINTS = 2;
const MAX_POINTS = 2000;

/** The default sweep range: a window around the resonance / split modes. */
function autoRange(analysis: AnalysisResponse): SweepRange {
  const coupled = analysis.coupled;
  const center = analysis.secondary.resonant_frequency;
  const lo = coupled ? coupled.split_lower * 0.85 : center * 0.7;
  const hi = coupled ? coupled.split_upper * 1.15 : center * 1.3;
  return { fminKhz: lo / 1e3, fmaxKhz: hi / 1e3, points: 1000 };
}

function ImpedanceControls({
  range,
  isCustom,
  onChange,
  onAuto,
}: {
  range: SweepRange;
  isCustom: boolean;
  onChange: (patch: Partial<SweepRange>) => void;
  onAuto: () => void;
}) {
  return (
    <div className="impedance-controls" data-testid="impedance-controls">
      <label>
        f min (kHz)
        <input
          type="number"
          step="any"
          min={0}
          data-testid="imp-fmin"
          value={Number(range.fminKhz.toFixed(3))}
          onChange={(e) => onChange({ fminKhz: Number(e.target.value) })}
        />
      </label>
      <label>
        f max (kHz)
        <input
          type="number"
          step="any"
          min={0}
          data-testid="imp-fmax"
          value={Number(range.fmaxKhz.toFixed(3))}
          onChange={(e) => onChange({ fmaxKhz: Number(e.target.value) })}
        />
      </label>
      <label>
        points
        <input
          type="number"
          step="1"
          min={MIN_POINTS}
          max={MAX_POINTS}
          data-testid="imp-points"
          value={range.points}
          onChange={(e) => onChange({ points: Math.round(Number(e.target.value)) })}
        />
      </label>
      <button
        type="button"
        className="link-btn"
        data-testid="imp-auto"
        disabled={!isCustom}
        onClick={onAuto}
        title="Reset the range to a window around resonance"
      >
        Auto
      </button>
    </div>
  );
}

function ImpedanceChart({
  coil,
  bundle,
  analysis,
}: {
  coil: CoilSchema;
  bundle: MatrixBundle | null | undefined;
  analysis: AnalysisResponse;
}) {
  // The range follows the resonance-based auto window until the user edits
  // it; "Auto" clears the override and re-follows (also when analysis
  // changes after a re-run).
  const auto = useMemo(() => autoRange(analysis), [analysis]);
  const [custom, setCustom] = useState<SweepRange | null>(null);
  const range = custom ?? auto;

  const valid = range.fmaxKhz > range.fminKhz && range.fminKhz >= 0 && range.points >= MIN_POINTS;

  const frequencies = useMemo(() => {
    if (!valid) return [];
    const n = Math.min(Math.max(Math.round(range.points), MIN_POINTS), MAX_POINTS);
    const lo = range.fminKhz * 1e3;
    const hi = range.fmaxKhz * 1e3;
    return Array.from({ length: n }, (_, i) => lo + ((hi - lo) * i) / (n - 1));
  }, [range.fminKhz, range.fmaxKhz, range.points, valid]);

  const modes = analysis.coupled
    ? [analysis.coupled.split_lower, analysis.coupled.split_upper]
    : [];

  const impedance = useImpedance(coil, bundle, frequencies, { includeLosses: true });

  const controls = (
    <ImpedanceControls
      range={range}
      isCustom={custom !== null}
      onChange={(patch) => setCustom({ ...range, ...patch })}
      onAuto={() => setCustom(null)}
    />
  );

  if (!coil.primary || coil.primary.tank_capacitance <= 0) {
    return <p className="muted">Add a primary with a tank capacitance to see the impedance sweep.</p>;
  }

  let body: JSX.Element;
  if (!valid) {
    body = (
      <p className="error" data-testid="imp-invalid">
        f max must exceed f min, and points ≥ {MIN_POINTS}.
      </p>
    );
  } else if (impedance.isPending) {
    body = <p className="muted">Computing impedance…</p>;
  } else if (impedance.isError || !impedance.data) {
    body = <p className="muted">Impedance unavailable.</p>;
  } else {
    const data = impedance.data.points.map((p) => ({
      f: p.frequency_hz / 1e3,
      // |Z| in ohms (plotted on a log axis, so decades read like dB would
      // but in real units) and phase (impedance angle) in degrees.
      mag: Math.max(p.magnitude, 1e-12),
      phaseDeg: (Math.atan2(p.reactance, p.resistance) * 180) / Math.PI,
    }));
    body = <ImpedancePlot data={data} modes={modes} />;
  }

  return (
    <>
      {controls}
      {body}
    </>
  );
}

function ImpedancePlot({
  data,
  modes,
}: {
  data: { f: number; mag: number; phaseDeg: number }[];
  modes: number[];
}) {
  const colors = useThemeColors();
  // Shared log-frequency axis. Explicit geometric ticks keep labels
  // readable even over a narrow sweep (d3 log auto-ticks would be sparse).
  const fs = data.map((d) => d.f);
  const fmin = Math.min(...fs);
  const fmax = Math.max(...fs);
  const ticks = Array.from({ length: 6 }, (_, i) =>
    Number((fmin * Math.pow(fmax / fmin, i / 5)).toPrecision(3)),
  );

  // |Z| axis: log-scaled in real ohms. Snap the domain out to whole
  // decades and put a tick on each so the labels read 1 Ω, 10 Ω, 100 Ω…
  const mags = data.map((d) => d.mag);
  const magLo = Math.pow(10, Math.floor(Math.log10(Math.min(...mags))));
  const magHi = Math.pow(10, Math.ceil(Math.log10(Math.max(...mags))));
  const magDecades = Math.max(1, Math.round(Math.log10(magHi / magLo)));
  const magTicks = Array.from({ length: magDecades + 1 }, (_, i) => magLo * Math.pow(10, i));
  // Each tick is an exact power of ten, so render an integer mantissa with an
  // SI prefix (1 Ω, 100 Ω, 1 kΩ) rather than eng()'s toPrecision, which would
  // turn 10 and 100 into "1e+1"/"1e+2".
  const ohmTick = (v: number) => {
    const bands: [number, string][] = [[1e9, 'G'], [1e6, 'M'], [1e3, 'k'], [1, ''], [1e-3, 'm']];
    const [mult, prefix] = bands.find(([m]) => v >= m - 1e-9) ?? bands[bands.length - 1]!;
    return `${Math.round(v / mult)} ${prefix}Ω`;
  };

  const xAxis = (showLabel: boolean) => (
    <XAxis
      dataKey="f"
      type="number"
      scale="log"
      domain={[fmin, fmax]}
      ticks={ticks}
      stroke={colors.chartAxis}
      tickFormatter={(v: number) => `${v}`}
      label={
        showLabel
          ? { value: 'Frequency (kHz)', position: 'insideBottom', offset: -8, fill: colors.chartAxis }
          : undefined
      }
    />
  );

  const modeLines = modes.map((m) => (
    <ReferenceLine key={m} x={m / 1e3} stroke={colors.chartMarker} strokeDasharray="4 4" />
  ));

  const tooltipStyle = { background: colors.tooltipBg, border: `1px solid ${colors.tooltipBorder}` } as const;
  const labelFmt = (l: number) => `${l.toFixed(1)} kHz`;

  return (
    <div data-testid="impedance-chart">
      {/* Magnitude panel (|Z| in ohms, log-scaled) */}
      <div style={{ width: '100%', height: 190 }} data-testid="bode-magnitude">
        <ResponsiveContainer>
          <LineChart data={data} margin={{ top: 10, right: 20, bottom: 0, left: 10 }}>
            <CartesianGrid stroke={colors.chartGrid} />
            {xAxis(false)}
            <YAxis
              stroke={colors.chartAxis}
              scale="log"
              domain={[magLo, magHi]}
              ticks={magTicks}
              allowDataOverflow
              tickFormatter={ohmTick}
              label={{ value: '|Z| (Ω)', angle: -90, position: 'insideLeft', fill: colors.chartAxis }}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(v: number) => [eng(v, 'Ω'), '|Z|']}
              labelFormatter={labelFmt}
            />
            {modeLines}
            <Line type="monotone" dataKey="mag" stroke={colors.chartMagnitude} dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Phase panel (degrees) */}
      <div style={{ width: '100%', height: 170 }} data-testid="bode-phase">
        <ResponsiveContainer>
          <LineChart data={data} margin={{ top: 0, right: 20, bottom: 20, left: 10 }}>
            <CartesianGrid stroke={colors.chartGrid} />
            {xAxis(true)}
            <YAxis
              stroke={colors.chartAxis}
              domain={[-90, 90]}
              ticks={[-90, -45, 0, 45, 90]}
              label={{ value: '∠Z (°)', angle: -90, position: 'insideLeft', fill: colors.chartAxis }}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(v: number) => [`${v.toFixed(1)}°`, '∠Z']}
              labelFormatter={labelFmt}
            />
            {modeLines}
            <ReferenceLine y={0} stroke={colors.chartZero} />
            <Line type="monotone" dataKey="phaseDeg" stroke={colors.chartPhase} dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

/** A human-friendly explanation of an analysis failure. */
function errorMessage(error: unknown): string {
  const raw = error instanceof Error ? error.message : String(error);
  // openapi-fetch throws a TypeError('Failed to fetch') when the backend
  // is unreachable (proxy ECONNREFUSED).
  if (/failed to fetch|networkerror|load failed/i.test(raw)) {
    return 'Cannot reach the server. Please check your connection and try again.';
  }
  if (/HTTP 5\d\d/.test(raw)) {
    return 'The server encountered an error while processing this request. Please try again in a moment.';
  }
  return raw;
}

export function Results({
  coil,
  analysis,
  bundle,
  isFetching,
  dirty,
  hasRun,
  onRun,
  isError,
  error,
}: {
  coil: CoilSchema;
  analysis: AnalysisResponse | undefined;
  bundle: MatrixBundle | null | undefined;
  isFetching: boolean;
  dirty: boolean;
  hasRun: boolean;
  onRun: () => void;
  isError: boolean;
  error: unknown;
}) {
  const spice = useSpice();

  const downloadSpice = async () => {
    const netlist = await spice.fetchSpice(coil, bundle);
    if (!netlist) return;
    const blob = new Blob([netlist], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'teslacoil.cir';
    a.click();
    URL.revokeObjectURL(url);
  };

  const status = isFetching
    ? 'computing…'
    : !hasRun
      ? 'not run yet'
      : dirty
        ? 'stale — geometry changed'
        : 'up to date';

  return (
    <section className="results" data-testid="results">
      <div className="results-header">
        <h2>Results</h2>
        <span className="badge" data-testid="results-status">
          {status}
        </span>
        <button
          type="button"
          className={dirty || !hasRun ? 'run-inline dirty' : 'run-inline'}
          data-testid="run-results"
          disabled={isFetching}
          onClick={onRun}
        >
          {isFetching ? 'Running…' : 'Run calculations'}
        </button>
        <UnitSystemButtons />
      </div>

      {isError && (
        <div className="error-banner" data-testid="error-banner" role="alert">
          {errorMessage(error)}
        </div>
      )}

      <div className="result-cards">
        <Card title="Secondary" fields={SECONDARY_FIELDS} data={analysis?.secondary} />
        <Card title="Primary" fields={PRIMARY_FIELDS} data={analysis?.primary} />
        <Card title="Coupling" fields={COUPLING_FIELDS} data={analysis?.coupling} />
        <Card title="Coupled modes" fields={COUPLED_FIELDS} data={analysis?.coupled} />
      </div>

      <div className="result-card">
        <h3>Primary input impedance</h3>
        {analysis ? (
          <ImpedanceChart coil={coil} bundle={bundle} analysis={analysis} />
        ) : (
          <p className="muted">Run the calculation to see the impedance sweep.</p>
        )}
      </div>

      <div className="result-card">
        <h3>Eigenmodes</h3>
        {analysis ? (
          <EigenModesChart modes={analysis.modes} />
        ) : (
          <p className="muted">Run the calculation to see the voltage and current eigenmodes.</p>
        )}
      </div>

      <div className="result-card">
        <h3>Matrices</h3>
        {bundle ? (
          <MatrixViewer bundle={bundle} />
        ) : (
          <p className="muted">Run the calculation to view and export the coil matrices.</p>
        )}
      </div>

      <div className="result-card">
        <h3>Export</h3>
        <button
          type="button"
          data-testid="spice-export"
          onClick={downloadSpice}
          disabled={spice.loading || !bundle}
          title={bundle ? 'Download SPICE subcircuit' : 'Run the calculation first'}
        >
          {spice.loading ? 'Exporting…' : 'Download SPICE netlist'}
        </button>
        {spice.error && <span className="error"> {spice.error}</span>}
      </div>
    </section>
  );
}
