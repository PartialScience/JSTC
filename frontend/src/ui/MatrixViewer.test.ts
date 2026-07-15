import { describe, expect, it } from 'vitest';

import type { MatrixBundle } from '../api/client';
import {
  cellColor,
  colorScale,
  convertCell,
  formatCell,
  matricesFromBundle,
  matrixCsvName,
  matrixToCsv,
  textColorFor,
  type NamedMatrix,
} from './matrixData';

function bundle(patch: Partial<MatrixBundle>): MatrixBundle {
  return {
    nodal_capacitance: [],
    topload_charge: [],
    inductance: [],
    coupling: [],
    discretization_order: 0,
    geometry_fingerprint: 'x',
    ...patch,
  };
}

describe('matricesFromBundle', () => {
  it('exposes the populated matrices and skips empty ones', () => {
    const m = matricesFromBundle(
      bundle({
        nodal_capacitance: [
          [1, 2],
          [2, 3],
        ],
        inductance: [[5]],
        coupling: [], // no primary -> skipped
        topload_charge: [0.1, 0.2],
      }),
    );
    expect(m.map((x) => x.key)).toEqual(['capacitance', 'inductance', 'topload_charge']);
  });

  it('includes the coupling vector as a single-column matrix when present', () => {
    const m = matricesFromBundle(bundle({ inductance: [[1]], coupling: [0.4, 0.5, 0.6] }));
    const coupling = m.find((x) => x.key === 'coupling')!;
    expect(coupling.columns).toBeNull();
    expect(coupling.rows).toEqual([[0.4], [0.5], [0.6]]);
  });

  it('returns nothing for a fully empty bundle', () => {
    expect(matricesFromBundle(bundle({}))).toEqual([]);
  });
});

describe('formatCell', () => {
  it('formats across magnitudes', () => {
    expect(formatCell(0)).toBe('0');
    expect(formatCell(1.23456)).toBe('1.23');
    expect(formatCell(1234)).toBe('1.23e+3');
    expect(formatCell(1e-5)).toBe('1.00e-5');
    expect(formatCell(NaN)).toBe('—');
  });
});

describe('colorScale', () => {
  it('is diverging when the values straddle zero', () => {
    const s = colorScale([
      [-2, 1],
      [0, 3],
    ]);
    expect(s.diverging).toBe(true);
    expect(s.magnitude).toBe(3);
  });

  it('is sequential when all values share a sign', () => {
    const s = colorScale([[1, 2, 4]]);
    expect(s.diverging).toBe(false);
    expect(s.min).toBe(1);
    expect(s.max).toBe(4);
  });
});

describe('cellColor / textColorFor', () => {
  it('maps a diverging scale blue↔red about zero', () => {
    const s = colorScale([
      [-1, 1],
    ]);
    expect(cellColor(-1, s)).toBe('rgb(37, 99, 235)'); // LOW (blue)
    expect(cellColor(1, s)).toBe('rgb(220, 38, 38)'); // HIGH (red)
  });

  it('returns readable text for light and dark cell colors', () => {
    expect(textColorFor('rgb(37, 99, 235)')).toBe('#f8fafc'); // dark bg -> light text
    expect(textColorFor('rgb(240, 240, 240)')).toBe('#0b1120'); // light bg -> dark text
    expect(textColorFor(null)).toBe('inherit');
  });
});

describe('matrixToCsv', () => {
  it('writes an index header/column for a 2-D matrix', () => {
    const m: NamedMatrix = {
      key: 'k',
      name: 'K',
      caption: '',
      columns: [0, 1],
      rows: [
        [1, 2],
        [3, 4],
      ],
      physical: { kind: 'capacitance', factor: 1 },
    };
    expect(matrixToCsv(m)).toBe(',0,1\n0,1,2\n1,3,4');
  });

  it('omits the column header for a vector', () => {
    const m: NamedMatrix = {
      key: 'v',
      name: 'V',
      caption: '',
      columns: null,
      rows: [[0.4], [0.5]],
      physical: { kind: 'inductance', factor: 1 },
    };
    expect(matrixToCsv(m)).toBe('0,0.4\n1,0.5');
  });
});

describe('matrix unit conversion', () => {
  const cap = matricesFromBundle(
    { nodal_capacitance: [[1]], topload_charge: [], inductance: [], coupling: [] } as never,
  ).find((x) => x.key === 'capacitance')!;

  it('leaves geometric values raw', () => {
    expect(convertCell(1, cap, 'geometric')).toBe(1);
  });

  it('converts a geometric entry to a physical unit (pF)', () => {
    // 1 geometric × 2π·ε₀ ≈ 5.563e-11 F ≈ 55.6 pF
    expect(convertCell(1, cap, 'pF')).toBeCloseTo(55.63, 2);
  });

  it('encodes the unit in the CSV filename', () => {
    expect(matrixCsvName(cap, 'pF')).toBe('capacitance_pF.csv');
    expect(matrixCsvName(cap, 'geometric')).toBe('capacitance_geometric.csv');
  });
});
