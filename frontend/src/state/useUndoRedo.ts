/**
 * Global keyboard shortcuts for undo/redo. Ctrl/Cmd+Z undoes; Ctrl/Cmd+Y or
 * Ctrl/Cmd+Shift+Z redoes. Skipped while a text/number input is focused so
 * the browser's native field-level undo still works there.
 */
import { useEffect } from 'react';

import { useEditorStore } from './store';

function isEditableTarget(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false;
  const tag = el.tagName;
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || el.isContentEditable;
}

export function useUndoRedo(): void {
  const undo = useEditorStore((s) => s.undo);
  const redo = useEditorStore((s) => s.redo);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const mod = e.ctrlKey || e.metaKey;
      if (!mod || e.key.toLowerCase() !== 'z') {
        // Ctrl+Y as an alternate redo.
        if (mod && e.key.toLowerCase() === 'y' && !isEditableTarget(e.target)) {
          e.preventDefault();
          redo();
        }
        return;
      }
      if (isEditableTarget(e.target)) return; // let inputs handle their own undo
      e.preventDefault();
      if (e.shiftKey) redo();
      else undo();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [undo, redo]);
}
