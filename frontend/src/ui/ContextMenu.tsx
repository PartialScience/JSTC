/**
 * Right-click context menu. On a handle it offers exact numeric entry of the
 * point (endpoint, center, or a polygon vertex) and, for vertices, deletion.
 * On a component body it offers select/delete, and for toploads/grounds the
 * shape-type conversions and "add vertex".
 */
import { useState } from 'react';

import type { GroundSchema, ToploadSchema } from '../api/client';
import type { ComponentRef, Point } from '../domain/coil';
import { useEditorStore } from '../state/store';
import { convertShape, deleteVertex, insertVertex, type ShapeKind } from '../editor/shapeOps';

const SHAPE_KINDS: ShapeKind[] = ['circle', 'rectangle', 'polygon'];

export function ContextMenu() {
  const menu = useEditorStore((s) => s.contextMenu);
  const close = useEditorStore((s) => s.closeContextMenu);
  const coil = useEditorStore((s) => s.coil);
  const select = useEditorStore((s) => s.select);
  const updateSecondary = useEditorStore((s) => s.updateSecondary);
  const updatePrimary = useEditorStore((s) => s.updatePrimary);
  const updateTopload = useEditorStore((s) => s.updateTopload);
  const updateGround = useEditorStore((s) => s.updateGround);
  const removeTopload = useEditorStore((s) => s.removeTopload);
  const removeGround = useEditorStore((s) => s.removeGround);
  const removePrimary = useEditorStore((s) => s.removePrimary);

  const [pt, setPt] = useState<Point | null>(null);

  if (!menu) return null;

  // Lazily seed the point editor with the handle's current world position.
  if (menu.handle && menu.world && pt === null) setPt(menu.world);

  const conductor = (ref: ComponentRef): ToploadSchema | GroundSchema | undefined => {
    if (ref.kind === 'topload') return coil.toploads[ref.index];
    if (ref.kind === 'ground') return coil.grounds[ref.index];
    return undefined;
  };

  const patchConductor = (
    ref: ComponentRef,
    patch: Partial<ToploadSchema | GroundSchema>,
  ) => {
    if (ref.kind === 'topload') updateTopload(ref.index, patch);
    else if (ref.kind === 'ground') updateGround(ref.index, patch);
  };

  const applyPoint = () => {
    if (!pt) return;
    const { ref, handle, vertexIndex } = menu;
    if (handle === 'vertex' && vertexIndex != null) {
      const shape = conductor(ref)?.shape;
      if (shape && shape.kind !== 'circle') {
        const vertices = shape.vertices.map((v, i) => (i === vertexIndex ? pt : ([v[0], v[1]] as Point)));
        patchConductor(ref, { shape: { ...shape, vertices } });
      }
    } else if (ref.kind === 'secondary') {
      updateSecondary(handle === 'start' ? { start: pt } : { end: pt });
    } else if (ref.kind === 'primary') {
      updatePrimary(handle === 'start' ? { start: pt } : { end: pt });
    } else if (handle === 'center') {
      const shape = conductor(ref)?.shape;
      if (shape?.kind === 'circle') patchConductor(ref, { shape: { ...shape, center: pt } });
    }
    close();
  };

  const removeComponent = () => {
    if (menu.ref.kind === 'topload') removeTopload(menu.ref.index);
    else if (menu.ref.kind === 'ground') removeGround(menu.ref.index);
    else if (menu.ref.kind === 'primary') removePrimary();
    close();
  };

  const removeVertex = () => {
    const { ref, vertexIndex } = menu;
    const shape = conductor(ref)?.shape;
    if (shape && vertexIndex != null) {
      const next = deleteVertex(shape, vertexIndex);
      if (next) patchConductor(ref, { shape: next });
    }
    close();
  };

  const addVertex = () => {
    const shape = conductor(menu.ref)?.shape;
    if (shape && menu.world) patchConductor(menu.ref, { shape: insertVertex(shape, menu.world) });
    close();
  };

  const convert = (kind: ShapeKind) => {
    const shape = conductor(menu.ref)?.shape;
    if (shape) patchConductor(menu.ref, { shape: convertShape(shape, kind) });
    close();
  };

  // Keep the menu on-screen: a right-click or long-press near the right/bottom
  // edge would otherwise open partly off the viewport (acute on phones). Clamp
  // the top-left corner against a conservative estimate of the menu's size.
  const MENU_W = 240;
  const MENU_H = 320;
  const vw = typeof window !== 'undefined' ? window.innerWidth : MENU_W;
  const vh = typeof window !== 'undefined' ? window.innerHeight : MENU_H;
  const left = Math.max(8, Math.min(menu.x, vw - MENU_W - 8));
  const top = Math.max(8, Math.min(menu.y, vh - MENU_H - 8));

  const isConductor = menu.ref.kind === 'topload' || menu.ref.kind === 'ground';
  const shape = conductor(menu.ref)?.shape;
  const label = isConductor
    ? `${menu.ref.kind} #${(menu.ref as { index: number }).index + 1}`
    : menu.ref.kind;
  const vertexDeletable =
    menu.handle === 'vertex' && shape?.kind !== 'circle' && (shape?.vertices.length ?? 0) > 3;

  return (
    <>
      <div
        className="context-backdrop"
        onClick={close}
        onContextMenu={(e) => {
          e.preventDefault();
          close();
        }}
      />
      <div
        className="context-menu"
        data-testid="context-menu"
        style={{ left, top }}
        onContextMenu={(e) => e.preventDefault()}
      >
        {menu.handle && menu.handle !== 'wire' && menu.handle !== 'radius' && pt ? (
          <div className="context-point-editor" data-testid="point-editor">
            <div className="context-title">
              Edit {menu.handle === 'vertex' ? `vertex ${menu.vertexIndex}` : menu.handle}
            </div>
            <label>
              r
              <input
                type="number"
                step="any"
                min="0"
                data-testid="point-r"
                value={pt[0]}
                onChange={(e) => setPt([Number(e.target.value), pt[1]])}
              />
            </label>
            <label>
              z
              <input
                type="number"
                step="any"
                data-testid="point-z"
                value={pt[1]}
                onChange={(e) => setPt([pt[0], Number(e.target.value)])}
              />
            </label>
            <button type="button" data-testid="point-apply" onClick={applyPoint}>
              Apply
            </button>
            {vertexDeletable && (
              <button type="button" data-testid="vertex-delete" onClick={removeVertex}>
                Delete vertex
              </button>
            )}
          </div>
        ) : (
          <>
            <div className="context-title">{label}</div>
            <button
              type="button"
              data-testid="ctx-edit"
              onClick={() => {
                select(menu.ref);
                close();
              }}
            >
              Edit parameters →
            </button>
            {isConductor && shape && shape.kind !== 'circle' && (
              <button type="button" data-testid="ctx-add-vertex" onClick={addVertex}>
                Add vertex here
              </button>
            )}
            {isConductor &&
              SHAPE_KINDS.filter((k) => k !== shape?.kind).map((k) => (
                <button
                  key={k}
                  type="button"
                  data-testid={`ctx-convert-${k}`}
                  onClick={() => convert(k)}
                >
                  Convert to {k}
                </button>
              ))}
            {menu.ref.kind !== 'secondary' && (
              <button type="button" data-testid="ctx-delete" onClick={removeComponent}>
                Delete
              </button>
            )}
          </>
        )}
      </div>
    </>
  );
}
