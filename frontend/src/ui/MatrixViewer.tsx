/**
 * Matrix pane: browse and export the geometric matrices in the cached bundle.
 *
 * Steps through the bundle's matrices with arrows, renders each as a
 * heat-mapped grid with the numeric value in every cell, and exports the
 * current one as CSV. The data shaping and color mapping live in
 * ./matrixData (pure, unit-tested).
 */
import { useMemo, useState } from 'react';

import type { MatrixBundle } from '../api/client';
import { useEditorStore } from '../state/store';
import {
  cellColor,
  colorScale,
  formatMatrixCell,
  GEOMETRIC,
  matricesFromBundle,
  matrixCsvName,
  matrixToCsv,
  matrixUnitChoices,
  textColorFor,
  type NamedMatrix,
} from './matrixData';

function download(filename: string, text: string, mime: string): void {
  const blob = new Blob([text], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function MatrixGrid({ matrix, unit }: { matrix: NamedMatrix; unit: string }) {
  // Colour reflects relative structure, which a positive scalar unit conversion
  // preserves — so scale on the raw geometric rows regardless of display unit.
  const scale = useMemo(() => colorScale(matrix.rows), [matrix.rows]);

  return (
    <div className="matrix-grid-wrap" data-testid="matrix-grid">
      <table className="matrix-grid">
        <thead>
          <tr>
            <th className="matrix-corner" />
            {matrix.columns
              ? matrix.columns.map((c) => <th key={c}>{c}</th>)
              : <th>value</th>}
          </tr>
        </thead>
        <tbody>
          {matrix.rows.map((row, i) => (
            <tr key={i}>
              <th scope="row">{i}</th>
              {row.map((v, j) => {
                const bg = cellColor(v, scale);
                return (
                  <td
                    key={j}
                    style={{ background: bg ?? undefined, color: textColorFor(bg) }}
                    title={Number.isFinite(v) ? String(v) : undefined}
                  >
                    {formatMatrixCell(v, matrix, unit)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function MatrixViewer({ bundle }: { bundle: MatrixBundle }) {
  const matrices = useMemo(() => matricesFromBundle(bundle), [bundle]);
  const [index, setIndex] = useState(0);
  const matrixUnits = useEditorStore((s) => s.unitPrefs.matrices);
  const setMatrixUnit = useEditorStore((s) => s.setMatrixUnit);

  if (matrices.length === 0) {
    return <p className="muted">No matrices available.</p>;
  }

  // Guard against the active index outrunning the list (e.g. a coil losing its
  // primary drops the coupling matrix).
  const active = Math.min(index, matrices.length - 1);
  const matrix = matrices[active]!;
  const unit = matrixUnits[matrix.key] ?? GEOMETRIC;

  const step = (delta: number) =>
    setIndex((i) => {
      const n = matrices.length;
      return (Math.min(i, n - 1) + delta + n) % n;
    });

  const exportCsv = () =>
    download(matrixCsvName(matrix, unit), matrixToCsv(matrix, unit), 'text/csv');

  return (
    <div data-testid="matrix-viewer">
      <div className="matrix-controls">
        <button
          type="button"
          className="matrix-nav"
          data-testid="matrix-prev"
          onClick={() => step(-1)}
          disabled={matrices.length < 2}
          aria-label="Previous matrix"
          title="Previous matrix"
        >
          ‹
        </button>
        <div className="matrix-heading">
          <div className="matrix-title" data-testid="matrix-title">
            {matrix.name}
            <span className="matrix-count">
              {' '}
              {active + 1}/{matrices.length}
            </span>
          </div>
          <div className="matrix-caption">{matrix.caption}</div>
        </div>
        <button
          type="button"
          className="matrix-nav"
          data-testid="matrix-next"
          onClick={() => step(1)}
          disabled={matrices.length < 2}
          aria-label="Next matrix"
          title="Next matrix"
        >
          ›
        </button>
        <div className="matrix-spacer" />
        <label className="matrix-unit">
          <span className="visually-hidden">Units</span>
          <select
            data-testid="matrix-unit"
            value={unit}
            onChange={(e) => setMatrixUnit(matrix.key, e.target.value)}
            title="Display units for this matrix"
          >
            {matrixUnitChoices(matrix).map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="matrix-csv-btn"
          data-testid="matrix-csv"
          onClick={exportCsv}
          title={`Download ${matrix.name} as CSV`}
        >
          Export CSV
        </button>
      </div>

      <MatrixGrid matrix={matrix} unit={unit} />
    </div>
  );
}
