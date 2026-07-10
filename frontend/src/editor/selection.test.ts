import { describe, expect, it } from 'vitest';

import { defaultCoil } from '../domain/coil';
import { refsInRect } from './selection';

describe('refsInRect', () => {
  const coil = defaultCoil();
  // Default coil: secondary at r≈2.27 (z 23→44.8), primary at r 3.75→7.97 (z 23),
  // one topload centered at (7.375, 48.8) r=3.125.

  it('selects the thin secondary from a box that only grazes its centerline', () => {
    const hits = refsInRect(coil, { xMin: 2.0, xMax: 2.5, zMin: 25, zMax: 40 });
    expect(hits).toContainEqual({ kind: 'secondary' });
  });

  it('selects the topload but not the secondary when boxing only the top', () => {
    const hits = refsInRect(coil, { xMin: 5, xMax: 10, zMin: 46, zMax: 52 });
    expect(hits).toContainEqual({ kind: 'topload', index: 0 });
    expect(hits).not.toContainEqual({ kind: 'secondary' });
  });

  it('selects on the mirrored (-r) side too', () => {
    const hits = refsInRect(coil, { xMin: -2.5, xMax: -2.0, zMin: 25, zMax: 40 });
    expect(hits).toContainEqual({ kind: 'secondary' });
  });

  it('selects everything when the box spans the whole coil', () => {
    const hits = refsInRect(coil, { xMin: -20, xMax: 20, zMin: 0, zMax: 60 });
    expect(hits).toContainEqual({ kind: 'secondary' });
    expect(hits).toContainEqual({ kind: 'primary' });
    expect(hits).toContainEqual({ kind: 'topload', index: 0 });
  });

  it('selects nothing for a box in empty space', () => {
    expect(refsInRect(coil, { xMin: 40, xMax: 45, zMin: 100, zMax: 110 })).toEqual([]);
  });
});
