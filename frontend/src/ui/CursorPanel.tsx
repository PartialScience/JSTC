/**
 * The "Cursors" sidebar section for the field views. Lists every probe point
 * with its position and the field values sampled at it, each value a
 * click-to-copy target (3 s.f. shown, full precision copied). Points are shared
 * across the E and B views; this list shows whichever field the current view
 * displays. Adding a point drops it in the view (drag to move); the × removes it.
 */
import { useMemo, useState } from 'react';

import {
  fieldQuantityLabels,
  measure,
  measureLength,
  pair,
  type Measure,
} from '../field/fieldFormat';
import { fieldDataFromResponse } from '../field/fieldMath';
import { buildFieldSampler, type FieldKind } from '../field/sampleField';
import { useEditorStore } from '../state/store';
import { useViewField } from '../state/useViewField';
import { resolveOutputPref } from '../units/units';

/** One label + value row that copies its full-precision value on click. */
function CopyRow({ label, value }: { label: string; value: Measure }) {
  const [copied, setCopied] = useState(false);
  const canCopy = value.copy !== '';

  const onClick = () => {
    if (!canCopy || !navigator.clipboard) return;
    navigator.clipboard
      .writeText(value.copy)
      .then(() => {
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1200);
      })
      .catch(() => {});
  };

  return (
    <button
      type="button"
      className={`cursor-row${copied ? ' copied' : ''}`}
      onClick={onClick}
      disabled={!canCopy}
      title={canCopy ? 'Click to copy' : undefined}
    >
      <span className="cursor-row-label">{label}</span>
      <span className="cursor-row-value">{value.text}</span>
      <span className="cursor-row-hint" aria-hidden="true">
        {copied ? 'copied ✓' : 'copy'}
      </span>
    </button>
  );
}

/** The body of the Cursors section (add button + per-cursor cards). */
export function CursorList() {
  const viewMode = useEditorStore((s) => s.viewMode);
  const cursors = useEditorStore((s) => s.fieldCursors);
  const addCursor = useEditorStore((s) => s.addFieldCursor);
  const removeCursor = useEditorStore((s) => s.removeFieldCursor);
  const lengthPref = useEditorStore((s) => resolveOutputPref(s.unitPrefs, 'field-coord', 'length'));
  const fieldQuery = useViewField();

  const kind: FieldKind = viewMode === 'bfield' ? 'B' : 'E';
  const labels = fieldQuantityLabels(kind);

  const sampler = useMemo(
    () => (fieldQuery.data ? buildFieldSampler(fieldDataFromResponse(fieldQuery.data), kind) : null),
    [fieldQuery.data, kind],
  );

  return (
    <div className="cursor-list">
      <button
        type="button"
        className="cursor-add"
        onClick={addCursor}
        data-testid="cursor-add"
      >
        + Add cursor
      </button>

      {cursors.length === 0 ? (
        <p className="cursor-empty">
          Add a point to read the field at an exact spot. Drag it anywhere in the view.
        </p>
      ) : (
        cursors.map((cur, i) => {
          const s = sampler?.sampleAt(cur.x, cur.z);
          const position = pair(
            measureLength(Math.abs(cur.x), lengthPref),
            measureLength(cur.z, lengthPref),
          );
          const vector = pair(
            measure(s?.vr, labels.vectorUnit),
            measure(s?.vz, labels.vectorUnit),
          );
          return (
            <div className="cursor-card" key={cur.id} data-testid="cursor-card">
              <div className="cursor-card-head">
                <span className="cursor-dot" style={{ background: cur.color }} aria-hidden="true" />
                <span className="cursor-name">Cursor {i + 1}</span>
                <button
                  type="button"
                  className="cursor-remove"
                  onClick={() => removeCursor(cur.id)}
                  title="Remove cursor"
                  aria-label={`Remove cursor ${i + 1}`}
                  data-testid="cursor-remove"
                >
                  ×
                </button>
              </div>
              <div className="cursor-rows">
                <CopyRow label="Position (r, z)" value={position} />
                <CopyRow label={labels.fieldLabel} value={vector} />
                <CopyRow label={labels.potentialLabel} value={measure(s?.potential, labels.potentialUnit)} />
                <CopyRow label="Field intensity" value={measure(s?.intensity, labels.intensityUnit)} />
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}
