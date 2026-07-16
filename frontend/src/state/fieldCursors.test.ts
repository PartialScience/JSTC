import { beforeEach, describe, expect, it } from 'vitest';

import { CURSOR_COLORS, useEditorStore } from './store';

const reset = () => useEditorStore.setState({ fieldCursors: [] });

describe('field cursor actions', () => {
  beforeEach(reset);

  it('adds cursors at the domain centre with cycling colours and unique ids', () => {
    const { addFieldCursor, coil } = useEditorStore.getState();
    addFieldCursor();
    addFieldCursor();
    const cursors = useEditorStore.getState().fieldCursors;
    expect(cursors).toHaveLength(2);
    expect(cursors[0]!.x).toBeCloseTo(coil.r_max / 2, 9);
    expect(cursors[0]!.z).toBeCloseTo(coil.z_max / 2, 9);
    expect(cursors[0]!.color).toBe(CURSOR_COLORS[0]);
    expect(cursors[1]!.color).toBe(CURSOR_COLORS[1]);
    expect(cursors[0]!.id).not.toBe(cursors[1]!.id);
  });

  it('moves a cursor to a new world position', () => {
    const { addFieldCursor } = useEditorStore.getState();
    addFieldCursor();
    const id = useEditorStore.getState().fieldCursors[0]!.id;
    useEditorStore.getState().moveFieldCursor(id, -1.5, 2.25);
    const moved = useEditorStore.getState().fieldCursors[0]!;
    expect(moved.x).toBe(-1.5);
    expect(moved.z).toBe(2.25);
  });

  it('removes a cursor by id', () => {
    const { addFieldCursor } = useEditorStore.getState();
    addFieldCursor();
    addFieldCursor();
    const { fieldCursors, removeFieldCursor } = useEditorStore.getState();
    removeFieldCursor(fieldCursors[0]!.id);
    const rest = useEditorStore.getState().fieldCursors;
    expect(rest).toHaveLength(1);
    expect(rest[0]!.id).toBe(fieldCursors[1]!.id);
  });
});
