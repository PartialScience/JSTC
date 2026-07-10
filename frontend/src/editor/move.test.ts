import { describe, expect, it } from 'vitest';

import { defaultCoil } from '../domain/coil';
import { selectionMinR, translateComponents } from './move';

// Default coil: secondary at r=2.27 (z 23→44.8), primary at r 3.75→7.97 (z 23),
// one topload circle centered at (7.375, 48.8), radius 3.125.

const circleCenter = (coil: ReturnType<typeof defaultCoil>, i: number) => {
  const shape = coil.toploads[i]!.shape;
  if (shape.kind !== 'circle') throw new Error('expected circle');
  return shape.center;
};

describe('selectionMinR', () => {
  it('is the smallest defining r among the selection', () => {
    const coil = defaultCoil();
    expect(selectionMinR(coil, [{ kind: 'secondary' }])).toBeCloseTo(2.27);
    expect(selectionMinR(coil, [{ kind: 'topload', index: 0 }])).toBeCloseTo(7.375);
    expect(
      selectionMinR(coil, [{ kind: 'secondary' }, { kind: 'topload', index: 0 }]),
    ).toBeCloseTo(2.27);
  });

  it('is null when nothing translatable is selected', () => {
    expect(selectionMinR(defaultCoil(), [])).toBeNull();
  });
});

describe('translateComponents', () => {
  it('translates a single conductor and leaves others untouched', () => {
    const coil = defaultCoil();
    const moved = translateComponents(coil, [{ kind: 'topload', index: 0 }], 2, -3);
    expect(circleCenter(moved, 0)).toEqual([9.375, 45.8]);
    expect(moved.secondary).toBe(coil.secondary); // untouched, same reference
    expect(moved.primary).toBe(coil.primary);
  });

  it('translates a group rigidly by the same delta', () => {
    const coil = defaultCoil();
    const moved = translateComponents(
      coil,
      [{ kind: 'secondary' }, { kind: 'topload', index: 0 }],
      1,
      1,
    );
    expect(moved.secondary.start).toEqual([3.27, 24]);
    expect(moved.secondary.end).toEqual([3.27, 45.8]);
    expect(circleCenter(moved, 0)).toEqual([8.375, 49.8]);
    expect(moved.primary).toBe(coil.primary); // not selected
  });

  it('clamps the radial delta so nothing crosses r = 0', () => {
    const coil = defaultCoil();
    // A huge leftward drag: the secondary (min r 2.27) stops at the axis.
    const moved = translateComponents(coil, [{ kind: 'secondary' }], -10, 5);
    expect(moved.secondary.start[0]).toBeCloseTo(0);
    expect(moved.secondary.end[0]).toBeCloseTo(0);
    // z is unconstrained and moves the full amount.
    expect(moved.secondary.start[1]).toBeCloseTo(28);
  });

  it('clamps a group by its leftmost member, preserving spacing', () => {
    const coil = defaultCoil();
    const moved = translateComponents(
      coil,
      [{ kind: 'secondary' }, { kind: 'topload', index: 0 }],
      -5,
      0,
    );
    // Group min r is the secondary at 2.27, so the clamped delta is -2.27.
    expect(moved.secondary.start[0]).toBeCloseTo(0);
    expect(circleCenter(moved, 0)[0]).toBeCloseTo(7.375 - 2.27);
  });

  it('returns the same coil when nothing translatable is selected', () => {
    const coil = defaultCoil();
    expect(translateComponents(coil, [], 5, 5)).toBe(coil);
  });

  it('returns the same coil when the clamped move is a no-op', () => {
    const coil = defaultCoil();
    // Already-selected secondary pushed left while a component sits on the axis
    // would no-op; here a zero delta is the simplest no-op.
    expect(translateComponents(coil, [{ kind: 'secondary' }], 0, 0)).toBe(coil);
  });
});
