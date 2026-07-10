/**
 * Editor keyboard & pointer shortcuts, complementing undo/redo and the
 * canvas's own Space/Escape/Delete handling:
 *
 *   Ctrl/Cmd + C / V     copy / paste the selected toploads or grounds
 *   Enter                open the context menu for the selection
 *   double-click a shape open the context menu at the pointer
 *
 * (Delete/Backspace deletion lives with the canvas, alongside marquee select.)
 *
 * These are skipped while a form field is focused so native editing still
 * works. Live store state is read through getState() inside each handler, so a
 * selection made by the click immediately preceding the key/double-click is
 * always seen (a render-closure snapshot could be stale within that gesture).
 */
import { useEffect } from 'react';

import type { ComponentRef, Point } from '../domain/coil';
import { shapeCentroid } from '../editor/geometry';
import { useEditorStore, type EditorState } from './store';

const CANVAS_SELECTOR = '[data-testid="coil-canvas"]';

function isEditableTarget(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false;
  const tag = el.tagName;
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || el.isContentEditable;
}

/** Editable fields plus buttons/links, whose own Enter activation must not be
 *  stolen when opening the context menu via the keyboard. */
function isInteractiveTarget(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false;
  const tag = el.tagName;
  return tag === 'BUTTON' || tag === 'A' || isEditableTarget(el);
}

function midpoint(a: Point, b: Point): Point {
  return [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
}

/** A representative world point for a component, used as the context menu's
 *  anchor (e.g. where "add vertex here" inserts). */
function anchorWorld(state: EditorState, ref: ComponentRef): Point {
  const { coil } = state;
  if (ref.kind === 'secondary') return midpoint(coil.secondary.start, coil.secondary.end);
  if (ref.kind === 'primary' && coil.primary)
    return midpoint(coil.primary.start, coil.primary.end);
  if (ref.kind === 'topload') return shapeCentroid(coil.toploads[ref.index]!.shape);
  if (ref.kind === 'ground') return shapeCentroid(coil.grounds[ref.index]!.shape);
  return [0, 0];
}

/** Open the same single-target context menu a right-click opens, at screen
 *  (x, y). Uses the most-recently selected component when several are held. */
function openMenuAt(x: number, y: number): void {
  const state = useEditorStore.getState();
  const ref = state.selection[state.selection.length - 1];
  if (!ref) return;
  state.openContextMenu({ x, y, ref, world: anchorWorld(state, ref) });
}

export function useEditorKeyboard(): void {
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const state = useEditorStore.getState();
      const mod = e.ctrlKey || e.metaKey;

      // Ctrl/Cmd + C / V -> copy / paste the selected multi-instance components.
      if (mod && !e.shiftKey && !e.altKey && e.key.toLowerCase() === 'c') {
        if (isEditableTarget(e.target)) return;
        const copyable = state.selection.some(
          (ref) => ref.kind === 'topload' || ref.kind === 'ground',
        );
        if (copyable) {
          e.preventDefault();
          state.copySelection();
        }
        return;
      }
      if (mod && !e.shiftKey && !e.altKey && e.key.toLowerCase() === 'v') {
        if (isEditableTarget(e.target)) return;
        if (state.clipboard.length > 0) {
          e.preventDefault();
          state.pasteClipboard();
        }
        return;
      }

      // Enter -> open the context menu for the selection (centered on canvas).
      if (e.key === 'Enter' && !mod) {
        if (isInteractiveTarget(e.target)) return;
        if (state.selection.length === 0) return;
        const rect = document.querySelector(CANVAS_SELECTOR)?.getBoundingClientRect();
        if (!rect) return;
        e.preventDefault();
        openMenuAt(rect.left + rect.width / 2, rect.top + rect.height / 2);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  useEffect(() => {
    const onDblClick = (e: MouseEvent) => {
      const target = e.target;
      if (!(target instanceof Element) || !target.closest(CANVAS_SELECTOR)) return;
      // A double-click on a shape leaves it selected (the preceding clicks
      // select it); on empty canvas the selection is cleared, so this no-ops.
      if (useEditorStore.getState().selection.length === 0) return;
      e.preventDefault();
      openMenuAt(e.clientX, e.clientY);
    };
    window.addEventListener('dblclick', onDblClick);
    return () => window.removeEventListener('dblclick', onDblClick);
  }, []);
}
