/**
 * Read-only 3-D viewer of the coil.
 *
 * The whole model is axisymmetric: it is described in the 2-D (r, z) half-plane
 * and understood as the solid of revolution about the vertical (z) axis. This
 * view makes that literal — every component's (r, z) cross-section is revolved
 * 360° about the axis (a `LatheGeometry` surface of revolution), so the user
 * can see how the flat cross-section they edit maps to the real coil:
 *
 *   - the secondary winding  → a cylindrical / conical shell,
 *   - toploads and grounds   → tori / rings / discs,
 *   - the primary            → one concentric ring per turn, placed at exactly
 *                              the `ring_centers` the physics solves with
 *                              (`primaryRingCenters`, the honest approximation
 *                              the coupling / inductance / electrostatic solvers
 *                              all use).
 *
 * It is a viewer, not an editor: the only interactions are camera moves
 * (orbit / zoom / pan). Edits still happen in the sidebar, which stays mounted,
 * and this scene rebuilds from the live `coil` so changes show in real time.
 *
 * Mapping: coil (r, z) → three.js (x, y, z) with y = z (up) and revolution in
 * the x–z plane. The scene is shifted so the coil's mid-height sits at the
 * origin, keeping the orbit pivot centered as geometry changes.
 */
import { useEffect, useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { Grid, Line, OrbitControls } from '@react-three/drei';
import * as THREE from 'three';

import type { Coil, Point } from '../domain/coil';
import { primaryRingOutlines, secondaryOutline, shapeOutline } from '../editor/geometry';
import { useEditorStore } from '../state/store';
import { useThemeColors, type ThemeColors } from '../theme';

/** A revolved shell to draw: its geometry plus surface color/opacity. */
interface RevolvedMesh {
  key: string;
  geometry: THREE.LatheGeometry;
  color: string;
  opacity: number;
}

/** Surface of revolution of an (r, z) cross-section outline about the vertical
 *  axis. Radii are clamped to r ≥ 0 (the physical half-plane) and the profile
 *  loop is closed so the revolved shell is watertight. */
function latheFromOutline(outline: Point[], segments: number): THREE.LatheGeometry {
  const pts = outline.map(([r, z]) => new THREE.Vector2(Math.max(r, 0), z));
  if (pts.length > 0) pts.push(pts[0]!.clone());
  const geometry = new THREE.LatheGeometry(pts, segments);
  geometry.computeVertexNormals();
  return geometry;
}

interface Scene {
  meshes: RevolvedMesh[];
  /** Coil mid-height; the scene group is shifted down by this so the coil is
   *  centered on the origin. */
  centerY: number;
  /** z of the coil's base plane (for the reference grid), in scene coords. */
  baseY: number;
  /** Suggested initial camera distance from the origin. */
  extent: number;
}

/** Build every revolved shell from the coil, plus framing metrics. Runs only
 *  when the coil (or theme) changes, so live sidebar edits update the scene. */
function buildScene(coil: Coil, colors: ThemeColors): Scene {
  const meshes: RevolvedMesh[] = [];
  let rMax = 0;
  let zMin = Infinity;
  let zMax = -Infinity;

  const track = (outline: Point[]) => {
    for (const [r, z] of outline) {
      rMax = Math.max(rMax, Math.abs(r));
      zMin = Math.min(zMin, z);
      zMax = Math.max(zMax, z);
    }
  };

  // Secondary — a single revolved capsule (cylindrical/conical shell).
  const secOutline = secondaryOutline(coil.secondary, 10);
  track(secOutline);
  meshes.push({
    key: 'secondary',
    geometry: latheFromOutline(secOutline, 96),
    color: colors.secondary.stroke,
    opacity: 0.8,
  });

  // Primary — one concentric ring per turn, at the solver's ring centers.
  if (coil.primary) {
    const color = colors.materials[coil.primary.material].stroke;
    primaryRingOutlines(coil.primary, 20).forEach((ring, i) => {
      track(ring);
      meshes.push({
        key: `primary-ring-${i}`,
        geometry: latheFromOutline(ring, 40),
        color,
        opacity: 0.9,
      });
    });
  }

  // Toploads and grounds — revolved shapes (torus / ring / disc).
  coil.toploads.forEach((t, i) => {
    const outline = shapeOutline(t.shape, 48);
    track(outline);
    meshes.push({
      key: `topload-${i}`,
      geometry: latheFromOutline(outline, 96),
      color: colors.materials[t.material].stroke,
      opacity: 0.7,
    });
  });
  coil.grounds.forEach((g, i) => {
    const outline = shapeOutline(g.shape, 48);
    track(outline);
    meshes.push({
      key: `ground-${i}`,
      geometry: latheFromOutline(outline, 96),
      color: colors.materials[g.material].stroke,
      opacity: 0.7,
    });
  });

  if (!Number.isFinite(zMin)) {
    zMin = 0;
    zMax = coil.z_max || 1;
  }
  const centerY = (zMin + zMax) / 2;
  const height = Math.max(zMax - zMin, 1e-3);
  const extent = Math.max(rMax * 2, height);

  return { meshes, centerY, baseY: zMin - centerY, extent };
}

/** One revolved component shell. */
function ShellMesh({ mesh }: { mesh: RevolvedMesh }) {
  return (
    <mesh geometry={mesh.geometry}>
      <meshStandardMaterial
        color={mesh.color}
        transparent
        opacity={mesh.opacity}
        side={THREE.DoubleSide}
        roughness={0.45}
        metalness={0.15}
      />
    </mesh>
  );
}

export function Coil3DView() {
  const coil = useEditorStore((s) => s.coil);
  const colors = useThemeColors();

  const scene = useMemo(() => buildScene(coil, colors), [coil, colors]);

  // three.js geometries hold GPU buffers that are not garbage-collected, so
  // dispose the previous set whenever the scene is rebuilt (and on unmount).
  useEffect(
    () => () => {
      for (const m of scene.meshes) m.geometry.dispose();
    },
    [scene],
  );

  const d = scene.extent;
  // A three-quarter view: off to one side, slightly above, pulled back enough
  // to frame the whole coil. The user can orbit/zoom from here.
  const cameraPosition: [number, number, number] = [d * 1.15, d * 0.7, d * 1.6];
  const gridSize = Math.max(scene.extent * 3, 1);

  return (
    <div
      data-testid="coil-3d-view"
      style={{ width: '100%', height: '100%', background: colors.canvasBg }}
    >
      <Canvas
        camera={{ position: cameraPosition, fov: 45, near: d / 100, far: d * 40 }}
        dpr={[1, 2]}
      >
        <color attach="background" args={[colors.canvasBg]} />
        <ambientLight intensity={0.7} />
        <hemisphereLight intensity={0.5} />
        <directionalLight position={[d, d * 1.5, d]} intensity={1.1} />
        <directionalLight position={[-d, d * 0.5, -d * 0.5]} intensity={0.4} />

        <group position={[0, -scene.centerY, 0]}>
          {scene.meshes.map((m) => (
            <ShellMesh key={m.key} mesh={m} />
          ))}
        </group>

        {/* Reference grid on the coil's base plane and the r = 0 axis line. */}
        <Grid
          position={[0, scene.baseY, 0]}
          args={[gridSize, gridSize]}
          cellSize={gridSize / 20}
          sectionSize={gridSize / 4}
          cellColor={colors.wall}
          sectionColor={colors.axis}
          fadeDistance={gridSize * 2}
          infiniteGrid={false}
        />
        <Line
          points={[
            [0, scene.baseY, 0],
            [0, scene.extent, 0],
          ]}
          color={colors.axis}
          lineWidth={1}
          dashed
          dashSize={scene.extent / 30}
          gapSize={scene.extent / 30}
        />

        <OrbitControls makeDefault enablePan target={[0, 0, 0]} />
      </Canvas>
    </div>
  );
}

// Default export so App can code-split the (heavy) three.js bundle behind a
// React.lazy import — it loads only when the 3-D view is first opened.
export default Coil3DView;
