/**
 * Small controlled input helpers used throughout the sidebar. NumberField
 * keeps a local draft so partially-typed values (e.g. "-", "1.") don't fight
 * the user, committing only parseable numbers.
 */
import { useEffect, useRef, useState } from 'react';

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
