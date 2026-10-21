/**
 * Small controlled input helpers used throughout the sidebar. NumberField
 * keeps a local draft so partially-typed values (e.g. "-", "1.") don't fight
 * the user, committing only parseable numbers. QuantityField adds physical
 * units: it stores an SI value but shows/accepts the user's chosen unit, and
 * parses free text like "10in" / "120 mm".
 */
import { useEffect, useRef, useState } from 'react';

import { useEditorStore } from '../state/store';
import {
  DEFAULT_INPUT_UNIT,
  formatInput,
  parseQuantity,
  unitSymbol,
  type QuantityKind,
} from '../units/units';

/** Marks a control whose current value engages a feature the community has
 *  not experimentally validated yet (see domain/provenance.ts). Rendered as
 *  a small badge beside the label; the wording matches the Results banner
 *  bullet so the two can never drift apart. */
export interface UnvalidatedMark {
  wording: string;
}

export function UnvalidatedBadge({ mark }: { mark?: UnvalidatedMark | null }) {
  if (!mark) return null;
  return (
    <span
      className="unvalidated-badge"
      title={`Not yet experimentally validated: ${mark.wording}`}
      data-testid="unvalidated-badge"
    >
      unvalidated
    </span>
  );
}

interface NumberFieldProps {
  label: string;
  value: number;
  onCommit: (value: number) => void;
  step?: number | 'any';
  min?: number;
  testId?: string;
  unvalidated?: UnvalidatedMark | null;
  /** Curtail the resting display to this many significant digits; the full
   *  precision value appears while the field is focused and is always what
   *  is stored (display-only rounding). */
  displayPrecision?: number;
  /** Render just the input (no visible label) for table cells; the label
   *  still reaches assistive tech via aria-label. */
  bare?: boolean;
  disabled?: boolean;
}

export function NumberField({
  label,
  value,
  onCommit,
  step = 'any',
  min,
  testId,
  unvalidated,
  displayPrecision,
  bare,
  disabled,
}: NumberFieldProps) {
  const atRest = (v: number) =>
    displayPrecision != null && Number.isFinite(v)
      ? String(Number(v.toPrecision(displayPrecision)))
      : String(v);
  const [draft, setDraft] = useState(atRest(value));
  const focused = useRef(false);

  // Keep the draft in sync with external changes while not being edited.
  useEffect(() => {
    if (!focused.current) setDraft(atRest(value));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, displayPrecision]);

  return (
    <label className={bare ? 'field field-bare' : 'field'}>
      {!bare && (
        <span>
          {label}
          <UnvalidatedBadge mark={unvalidated} />
        </span>
      )}
      <input
        type="number"
        step={step}
        min={min}
        data-testid={testId}
        aria-label={bare ? label : undefined}
        disabled={disabled}
        value={draft}
        onFocus={() => {
          focused.current = true;
          setDraft(String(value));
        }}
        onBlur={() => {
          focused.current = false;
          setDraft(atRest(value));
        }}
        onChange={(e) => {
          setDraft(e.target.value);
          if (e.target.value === '') return;
          let n = Number(e.target.value);
          if (!Number.isFinite(n)) return;
          // Enforce the floor (e.g. r >= 0) rather than leaving `min` cosmetic:
          // a typed-in out-of-range value is clamped before it is committed.
          if (min != null) n = Math.max(min, n);
          onCommit(n);
        }}
      />
    </label>
  );
}

interface QuantityFieldProps {
  label: string;
  /** The value in SI base units for `kind`. */
  value: number;
  /** Called with the new value in SI base units. */
  onCommit: (value: number) => void;
  /** Physical quantity, which fixes the base unit and the accepted units. */
  kind: QuantityKind;
  /** Stable id used to persist this field's chosen display unit. */
  fieldId: string;
  /** Floor in SI base units (e.g. 0 for r >= 0). */
  min?: number;
  /** Overrides the kind's default display unit (e.g. nF for tank capacitance). */
  defaultUnit?: string;
  testId?: string;
  /** Render just the input (no visible label) for table cells; the label
   *  still reaches assistive tech via aria-label. */
  bare?: boolean;
  disabled?: boolean;
}

/**
 * A number input carrying a physical unit. The store value is always SI; the
 * field shows it in the user's chosen unit (a small adornment) and parses typed
 * entries — a bare number stays in the current unit, while a unit suffix like
 * "120mm" converts and switches the field's unit. An unrecognised or
 * wrong-dimension unit shows an inline validation error and does not commit.
 */
export function QuantityField({
  label,
  value,
  onCommit,
  kind,
  fieldId,
  min,
  defaultUnit,
  testId,
  bare,
  disabled,
}: QuantityFieldProps) {
  const storedUnit = useEditorStore((s) => s.unitPrefs.inputs[fieldId]);
  const setInputUnit = useEditorStore((s) => s.setInputUnit);
  const unit = storedUnit ?? defaultUnit ?? DEFAULT_INPUT_UNIT[kind];

  const [draft, setDraft] = useState(() => formatInput(value, unit, kind));
  const [error, setError] = useState<string | null>(null);
  // While editing, the draft carries the unit inline ("3.75 in") so it's
  // obvious the unit is editable; at rest it's just the number, with the unit
  // shown as an adornment.
  const [editing, setEditing] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Re-sync the draft to the SI value (in the current unit) on any external
  // change while the field isn't being edited — including a unit switch.
  useEffect(() => {
    if (!editing) setDraft(formatInput(value, unit, kind));
  }, [value, unit, kind, editing]);

  /** Keep the caret out of the unit: if focusing lands it at/after the unit
   *  (a click past the number, or a select-all / caret-at-end from Tab), pull
   *  it to just after the number ("3.75| in"); a click *inside* the number is
   *  left alone. Deferred to a task so it runs after the click's mouseup, which
   *  otherwise sets the caret last. */
  const keepCaretBeforeUnit = (numberLen: number) => {
    const el = inputRef.current;
    setTimeout(() => {
      if (el && document.activeElement === el && (el.selectionEnd ?? 0) > numberLen) {
        el.setSelectionRange(numberLen, numberLen);
      }
    }, 0);
  };

  const classes = ['field'];
  if (error) classes.push('field-invalid');
  if (bare) classes.push('field-bare');
  return (
    <label className={classes.join(' ')}>
      {!bare && <span>{label}</span>}
      <div className="quantity-input">
        <input
          ref={inputRef}
          type="text"
          // Full keyboard (not inputMode="decimal") so the unit suffix (mm, nF…)
          // is typeable on mobile, where a numeric keypad blocks letters.
          inputMode="text"
          data-testid={testId}
          aria-label={bare ? label : undefined}
          disabled={disabled}
          value={draft}
          aria-invalid={error ? true : undefined}
          onFocus={() => {
            const numberText = formatInput(value, unit, kind);
            setDraft(`${numberText} ${unitSymbol(unit)}`);
            setEditing(true);
            keepCaretBeforeUnit(numberText.length);
          }}
          onBlur={() => {
            setEditing(false);
            setError(null);
            setDraft(formatInput(value, unit, kind));
          }}
          onChange={(e) => {
            const text = e.target.value;
            setDraft(text);
            if (text.trim() === '') {
              setError(null);
              return;
            }
            const result = parseQuantity(text, kind, unit);
            if (!result.ok) {
              setError(result.error);
              return;
            }
            setError(null);
            const v = min != null ? Math.max(min, result.value) : result.value;
            onCommit(v);
            if (result.unit !== unit) setInputUnit(fieldId, result.unit);
          }}
        />
        {!editing && (
          <span className="quantity-unit" aria-hidden="true">
            {unitSymbol(unit)}
          </span>
        )}
      </div>
      {error && (
        <span className="field-error" data-testid={testId ? `${testId}-error` : undefined} role="alert">
          {error}
        </span>
      )}
    </label>
  );
}

interface SelectFieldProps<T extends string> {
  label: string;
  value: T;
  options: readonly T[];
  onChange: (value: T) => void;
  testId?: string;
  unvalidated?: UnvalidatedMark | null;
}

export function SelectField<T extends string>({
  label,
  value,
  options,
  onChange,
  testId,
  unvalidated,
}: SelectFieldProps<T>) {
  return (
    <label className="field">
      <span>
        {label}
        <UnvalidatedBadge mark={unvalidated} />
      </span>
      <select
        data-testid={testId}
        value={value}
        onChange={(e) => onChange(e.target.value as T)}
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </label>
  );
}


interface CheckboxFieldProps {
  label: string;
  value: boolean;
  onChange: (value: boolean) => void;
  testId?: string;
}

export function CheckboxField({ label, value, onChange, testId }: CheckboxFieldProps) {
  return (
    <label className="field field-checkbox">
      <span>{label}</span>
      <input
        type="checkbox"
        data-testid={testId}
        checked={value}
        onChange={(e) => onChange(e.target.checked)}
      />
    </label>
  );
}
