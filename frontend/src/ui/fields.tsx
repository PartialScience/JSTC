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

interface NumberFieldProps {
  label: string;
  value: number;
  onCommit: (value: number) => void;
  step?: number | 'any';
  min?: number;
  testId?: string;
}

export function NumberField({
  label,
  value,
  onCommit,
  step = 'any',
  min,
  testId,
}: NumberFieldProps) {
  const [draft, setDraft] = useState(String(value));
  const focused = useRef(false);

  // Keep the draft in sync with external changes while not being edited.
  useEffect(() => {
    if (!focused.current) setDraft(String(value));
  }, [value]);

  return (
    <label className="field">
      <span>{label}</span>
      <input
        type="number"
        step={step}
        min={min}
        data-testid={testId}
        value={draft}
        onFocus={() => (focused.current = true)}
        onBlur={() => {
          focused.current = false;
          setDraft(String(value));
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

  return (
    <label className={error ? 'field field-invalid' : 'field'}>
      <span>{label}</span>
      <div className="quantity-input">
        <input
          ref={inputRef}
          type="text"
          // Full keyboard (not inputMode="decimal") so the unit suffix (mm, nF…)
          // is typeable on mobile, where a numeric keypad blocks letters.
          inputMode="text"
          data-testid={testId}
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
}

export function SelectField<T extends string>({
  label,
  value,
  options,
  onChange,
  testId,
}: SelectFieldProps<T>) {
  return (
    <label className="field">
      <span>{label}</span>
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
