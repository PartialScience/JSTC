import { beforeEach, describe, expect, it } from 'vitest';

import { defaultCoil } from '../domain/coil';
import { useEditorStore } from './store';

const reset = () =>
  useEditorStore.setState({
    coil: defaultCoil(),
    selection: [{ kind: 'secondary' }],
    tool: 'pan',
    placementShape: 'circle',
    clipboard: [],
    contextMenu: null,
    revision: 0,
    past: [],
    future: [],
  });

describe('editor store', () => {
  beforeEach(reset);

  it('updates a secondary field and bumps revision', () => {
    const before = useEditorStore.getState().revision;
    useEditorStore.getState().updateSecondary({ wire_dia: 0.05 });
    const s = useEditorStore.getState();
    expect(s.coil.secondary.wire_dia).toBe(0.05);
    expect(s.revision).toBe(before + 1);
  });

  it('adds and removes toploads', () => {
    const { addTopload } = useEditorStore.getState();
    addTopload([5, 40], 2);
    expect(useEditorStore.getState().coil.toploads).toHaveLength(2);
    useEditorStore.getState().removeTopload(0);
    const toploads = useEditorStore.getState().coil.toploads;
    expect(toploads).toHaveLength(1);
    // The remaining one is the newly added
    expect(toploads[0]?.shape.kind).toBe('circle');
  });

  it('adds a topload with the chosen geometry', () => {
    const s = useEditorStore.getState();
    s.addTopload([5, 40], 2, 'rectangle');
    s.addGround([4, 10], 1.5, 'polygon');
    const { toploads, grounds } = useEditorStore.getState().coil;
    expect(toploads[toploads.length - 1]?.shape.kind).toBe('rectangle');
    expect(grounds[grounds.length - 1]?.shape.kind).toBe('polygon');
  });

  it('tracks the placement shape selection', () => {
    expect(useEditorStore.getState().placementShape).toBe('circle');
    useEditorStore.getState().setPlacementShape('polygon');
    expect(useEditorStore.getState().placementShape).toBe('polygon');
  });

  it('adds a primary and clears it, deselecting if selected', () => {
    const store = useEditorStore.getState();
    store.addPrimary([3, 20], [7, 20]);
    expect(useEditorStore.getState().coil.primary).not.toBeNull();
    useEditorStore.getState().select({ kind: 'primary' });
    useEditorStore.getState().removePrimary();
    expect(useEditorStore.getState().coil.primary).toBeNull();
    expect(useEditorStore.getState().selection).toEqual([]);
  });

  it('edits topload geometry immutably', () => {
    const original = useEditorStore.getState().coil.toploads[0];
    useEditorStore.getState().updateTopload(0, {
      shape: { kind: 'circle', center: [8, 50], radius: 4 },
    });
    const updated = useEditorStore.getState().coil.toploads[0];
    expect(updated).not.toBe(original);
    expect(updated?.shape).toEqual({ kind: 'circle', center: [8, 50], radius: 4 });
  });

  it('changes tool and selection', () => {
    useEditorStore.getState().setTool('topload');
    expect(useEditorStore.getState().tool).toBe('topload');
    useEditorStore.getState().select({ kind: 'topload', index: 0 });
    expect(useEditorStore.getState().selection).toEqual([{ kind: 'topload', index: 0 }]);
  });

  it('toggles and marquee-sets multi-selection, and deletes selected', () => {
    const store = useEditorStore.getState();
    store.addPrimary([3, 20], [7, 20]);
    store.addTopload([5, 40], 2); // now two toploads (index 0 and 1)

    // Marquee-style multi-select, then toggle one off and back on.
    useEditorStore
      .getState()
      .setSelection([{ kind: 'primary' }, { kind: 'topload', index: 1 }]);
    expect(useEditorStore.getState().selection).toHaveLength(2);
    useEditorStore.getState().toggleSelect({ kind: 'topload', index: 1 });
    expect(useEditorStore.getState().selection).toEqual([{ kind: 'primary' }]);
    useEditorStore.getState().toggleSelect({ kind: 'topload', index: 1 });
    expect(useEditorStore.getState().selection).toHaveLength(2);

    // Delete removes the primary and the selected topload, leaving one topload.
    useEditorStore.getState().deleteSelected();
    const s = useEditorStore.getState();
    expect(s.coil.primary).toBeNull();
    expect(s.coil.toploads).toHaveLength(1);
    expect(s.selection).toEqual([]);
  });

  it('translateSelection moves the whole selection and clamps at r = 0', () => {
    const store = useEditorStore.getState();
    store.select({ kind: 'secondary' });
    const before = useEditorStore.getState().coil.secondary;

    // Move right and up: both endpoints shift by the same delta.
    useEditorStore.getState().translateSelection(1.5, 2);
    let sec = useEditorStore.getState().coil.secondary;
    expect(sec.start[0]).toBeCloseTo(before.start[0] + 1.5);
    expect(sec.end[1]).toBeCloseTo(before.end[1] + 2);

    // A large leftward move stops the winding at the axis, never negative.
    useEditorStore.getState().translateSelection(-999, 0);
    sec = useEditorStore.getState().coil.secondary;
    expect(sec.start[0]).toBeCloseTo(0);
    expect(sec.end[0]).toBeCloseTo(0);
  });
});

describe('copy / paste', () => {
  beforeEach(reset);

  it('copies and pastes a topload as a new, offset, selected instance', () => {
    const s = useEditorStore.getState();
    s.select({ kind: 'topload', index: 0 });
    const original = useEditorStore.getState().coil.toploads[0]!;
    useEditorStore.getState().copySelection();
    useEditorStore.getState().pasteClipboard();

    const st = useEditorStore.getState();
    expect(st.coil.toploads).toHaveLength(2);
    expect(st.selection).toEqual([{ kind: 'topload', index: 1 }]);
    const pasted = st.coil.toploads[1]!;
    expect(pasted.shape.kind).toBe('circle');
    if (pasted.shape.kind === 'circle' && original.shape.kind === 'circle') {
      // Offset from the original, not on top of it.
      expect(pasted.shape.center).not.toEqual(original.shape.center);
    }
  });

  it('copies and pastes every selected conductor at once', () => {
    const s = useEditorStore.getState();
    s.addGround([4, 10], 1.5); // one topload (0) + one ground (0)
    useEditorStore
      .getState()
      .setSelection([{ kind: 'topload', index: 0 }, { kind: 'ground', index: 0 }]);
    useEditorStore.getState().copySelection();
    useEditorStore.getState().pasteClipboard();

    const st = useEditorStore.getState();
    expect(st.coil.toploads).toHaveLength(2);
    expect(st.coil.grounds).toHaveLength(2);
    expect(st.selection).toHaveLength(2);
  });

  it('paste with an empty clipboard is a no-op', () => {
    const before = useEditorStore.getState().coil;
    useEditorStore.getState().pasteClipboard();
    expect(useEditorStore.getState().coil).toBe(before);
  });

  it('copy ignores singleton components (secondary/primary)', () => {
    const s = useEditorStore.getState();
    s.select({ kind: 'secondary' });
    useEditorStore.getState().copySelection();
    expect(useEditorStore.getState().clipboard).toEqual([]);
  });
});

describe('right-half-plane clamp (r >= 0)', () => {
  beforeEach(reset);

  it('clamps a negative secondary r to the axis', () => {
    useEditorStore.getState().updateSecondary({ start: [-5, 10] });
    expect(useEditorStore.getState().coil.secondary.start).toEqual([0, 10]);
  });

  it('clamps a negative topload center r', () => {
    useEditorStore.getState().updateTopload(0, {
      shape: { kind: 'circle', center: [-3, 20], radius: 2 },
    });
    const shape = useEditorStore.getState().coil.toploads[0]!.shape;
    expect(shape.kind).toBe('circle');
    if (shape.kind === 'circle') expect(shape.center[0]).toBe(0);
  });

  it('leaves a valid coil untouched (identity preserved)', () => {
    const before = useEditorStore.getState().coil;
    useEditorStore.getState().updateSecondary({ wire_dia: 0.05 });
    // Only the secondary object changes; unedited conductors keep identity.
    expect(useEditorStore.getState().coil.toploads).toBe(before.toploads);
  });
});

describe('undo / redo', () => {
  beforeEach(reset);

  it('undo restores the previous coil; redo re-applies', () => {
    const s = useEditorStore.getState();
    expect(s.past).toHaveLength(0);

    s.updateSecondary({ wire_dia: 0.1 });
    expect(useEditorStore.getState().coil.secondary.wire_dia).toBe(0.1);
    expect(useEditorStore.getState().past).toHaveLength(1);

    useEditorStore.getState().undo();
    expect(useEditorStore.getState().coil.secondary.wire_dia).not.toBe(0.1);
    expect(useEditorStore.getState().future).toHaveLength(1);

    useEditorStore.getState().redo();
    expect(useEditorStore.getState().coil.secondary.wire_dia).toBe(0.1);
    expect(useEditorStore.getState().future).toHaveLength(0);
  });

  it('undo on empty history is a no-op', () => {
    const before = useEditorStore.getState().coil;
    useEditorStore.getState().undo();
    expect(useEditorStore.getState().coil).toBe(before);
  });

  it('a new edit after undo clears the redo stack', () => {
    const s = useEditorStore.getState();
    s.addTopload([5, 40], 2);
    useEditorStore.getState().undo();
    expect(useEditorStore.getState().future).toHaveLength(1);
    useEditorStore.getState().updateSecondary({ wire_dia: 0.07 });
    expect(useEditorStore.getState().future).toHaveLength(0);
  });

  it('coalesces rapid consecutive edits into one undo step', () => {
    const s = useEditorStore.getState();
    // Two edits within the coalesce window record only one history entry.
    s.updateSecondary({ wire_dia: 0.03 });
    s.updateSecondary({ wire_dia: 0.04 });
    expect(useEditorStore.getState().past).toHaveLength(1);
    useEditorStore.getState().undo();
    // Undo jumps back past the whole burst to the original.
    expect(useEditorStore.getState().coil.secondary.wire_dia).not.toBe(0.04);
  });
});
