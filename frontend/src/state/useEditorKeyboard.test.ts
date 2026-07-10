import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { defaultCoil } from '../domain/coil';
import { useEditorStore } from './store';
import { useEditorKeyboard } from './useEditorKeyboard';

function pressKey(init: KeyboardEventInit) {
  act(() => {
    window.dispatchEvent(new KeyboardEvent('keydown', init));
  });
}

beforeEach(() => {
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
});

afterEach(() => {
  document.body.innerHTML = '';
});

describe('useEditorKeyboard', () => {
  it('Ctrl+C then Ctrl+V pastes an offset copy and selects it', () => {
    renderHook(() => useEditorKeyboard());
    act(() => useEditorStore.getState().select({ kind: 'topload', index: 0 }));
    pressKey({ key: 'c', ctrlKey: true });
    pressKey({ key: 'v', ctrlKey: true });
    const st = useEditorStore.getState();
    expect(st.coil.toploads).toHaveLength(2);
    expect(st.selection).toEqual([{ kind: 'topload', index: 1 }]);
  });

  it('does not copy while a form field is focused', () => {
    renderHook(() => useEditorKeyboard());
    act(() => useEditorStore.getState().select({ kind: 'topload', index: 0 }));
    const input = document.createElement('input');
    document.body.appendChild(input);
    input.focus();
    act(() => {
      input.dispatchEvent(new KeyboardEvent('keydown', { key: 'c', ctrlKey: true, bubbles: true }));
    });
    expect(useEditorStore.getState().clipboard).toEqual([]);
  });

  it('Enter opens the context menu for the selection', () => {
    const canvas = document.createElement('div');
    canvas.setAttribute('data-testid', 'coil-canvas');
    document.body.appendChild(canvas);

    renderHook(() => useEditorKeyboard());
    act(() => useEditorStore.getState().select({ kind: 'topload', index: 0 }));
    pressKey({ key: 'Enter' });

    const menu = useEditorStore.getState().contextMenu;
    expect(menu?.ref).toEqual({ kind: 'topload', index: 0 });
    expect(menu?.handle).toBeUndefined(); // the body menu, like a right-click
  });

  it('double-clicking a selected shape opens the context menu at the pointer', () => {
    const canvas = document.createElement('div');
    canvas.setAttribute('data-testid', 'coil-canvas');
    document.body.appendChild(canvas);

    renderHook(() => useEditorKeyboard());
    act(() => useEditorStore.getState().select({ kind: 'topload', index: 0 }));
    act(() => {
      canvas.dispatchEvent(new MouseEvent('dblclick', { bubbles: true, clientX: 12, clientY: 34 }));
    });

    const menu = useEditorStore.getState().contextMenu;
    expect(menu?.ref).toEqual({ kind: 'topload', index: 0 });
    expect(menu?.x).toBe(12);
    expect(menu?.y).toBe(34);
  });

  it('does nothing on double-click when the selection is empty', () => {
    const canvas = document.createElement('div');
    canvas.setAttribute('data-testid', 'coil-canvas');
    document.body.appendChild(canvas);

    renderHook(() => useEditorKeyboard());
    act(() => useEditorStore.getState().select(null));
    act(() => {
      canvas.dispatchEvent(new MouseEvent('dblclick', { bubbles: true, clientX: 5, clientY: 5 }));
    });
    expect(useEditorStore.getState().contextMenu).toBeNull();
  });
});
