/**
 * Viewport: the single world<->screen transform shared by every layer of
 * the editor (geometry now, field solve later). "World" is the axisymmetric
 * (r, z) half-plane with z pointing up; the editor renders a MIRRORED full
 * cross-section, so a component authored at radius r is drawn at world x =
 * +r and x = -r. This module is pure and framework-agnostic (fully unit
 * tested); Konva only consumes its numbers.
 */

export interface Viewport {
  /** Pixels per world unit. */
  scale: number;
  /** Screen x of world x = 0. */
  tx: number;
  /** Screen y of world z = 0. */
  ty: number;
}

export interface Size {
  width: number;
  height: number;
}

export interface WorldBounds {
  xMin: number;
  xMax: number;
  zMin: number;
  zMax: number;
}

/** World (x, z) -> screen (x, y). z is up, so screen y is flipped. */
export function worldToScreen(
  vp: Viewport,
  wx: number,
  wz: number,
): { x: number; y: number } {
  return { x: vp.tx + wx * vp.scale, y: vp.ty - wz * vp.scale };
}

/** Screen (x, y) -> world (x, z). Inverse of worldToScreen. */
export function screenToWorld(
  vp: Viewport,
  sx: number,
  sy: number,
): { x: number; z: number } {
  return { x: (sx - vp.tx) / vp.scale, z: (vp.ty - sy) / vp.scale };
}

/** A world-space length rendered in screen pixels. */
export function worldToScreenLength(vp: Viewport, length: number): number {
  return length * vp.scale;
}

/**
 * Fit a world bounding box into the canvas with padding, returning a
 * viewport that centers it.
 */
export function fitBounds(
  bounds: WorldBounds,
  size: Size,
  padding = 40,
): Viewport {
  const worldW = Math.max(bounds.xMax - bounds.xMin, 1e-9);
  const worldH = Math.max(bounds.zMax - bounds.zMin, 1e-9);
  const availW = Math.max(size.width - 2 * padding, 1);
  const availH = Math.max(size.height - 2 * padding, 1);
  const scale = Math.min(availW / worldW, availH / worldH);

  // Center the world box in the canvas.
  const worldCx = (bounds.xMin + bounds.xMax) / 2;
  const worldCz = (bounds.zMin + bounds.zMax) / 2;
  const tx = size.width / 2 - worldCx * scale;
  const ty = size.height / 2 + worldCz * scale;
  return { scale, tx, ty };
}

/** The mirrored full-cross-section world bounds for a domain of extent r_max
 *  (radial) and z_max (vertical): x spans [-r_max, +r_max]. */
export function domainBounds(rMax: number, zMax: number): WorldBounds {
  return { xMin: -rMax, xMax: rMax, zMin: 0, zMax };
}

/**
 * Zoom by a factor about a fixed screen point (keeps the world point under
 * the cursor stationary).
 */
export function zoomAbout(
  vp: Viewport,
  screenX: number,
  screenY: number,
  factor: number,
  minScale = 1e-4,
  maxScale = 1e9,
): Viewport {
  const nextScale = Math.min(Math.max(vp.scale * factor, minScale), maxScale);
  const world = screenToWorld(vp, screenX, screenY);
  // Solve for translation that keeps `world` at (screenX, screenY).
  const tx = screenX - world.x * nextScale;
  const ty = screenY + world.z * nextScale;
  return { scale: nextScale, tx, ty };
}

/** Pan by a screen-space delta. */
export function pan(vp: Viewport, dx: number, dy: number): Viewport {
  return { ...vp, tx: vp.tx + dx, ty: vp.ty + dy };
}
