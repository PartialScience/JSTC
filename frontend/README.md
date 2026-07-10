# JSTC Frontend

Interactive Tesla-coil designer: a geometry editor over the JSTC simulation
API. Built with Vite + React + TypeScript, Konva (canvas editor), Zustand
(state), TanStack Query (API orchestration), and Recharts (results).

## Layout

- **Top (100vh)** — the editor. A left parameter column (every coil
  parameter, editable, synced live) and a right interactive canvas showing
  the coil as a mirrored (r, z) cross-section. A toolbar places new
  components (secondary, primary, topload, ground). Drag handles to move
  endpoints; right-click for a context menu (exact point entry, delete).
- **Below (scroll)** — results: secondary/primary/coupling/coupled output
  cards, the primary input-impedance sweep chart, and SPICE export.

## Architecture notes

- **Types are generated** from the backend's OpenAPI (`npm run gen:api` →
  `src/api/schema.ts`), so the coil the UI edits is exactly the schema the
  backend validates.
- **The Viewport** (`src/editor/viewport.ts`) is the single world↔screen
  transform every layer shares. The future field-solve overlay slots in as
  a background layer behind the Konva geometry, using this same transform.
- **Caching contract**: `useAnalysis` holds the geometric matrix bundle and
  reuses it for every fast call; a 409 (stale bundle) transparently
  refetches `/simulation/matrices`. Cheap edits (materials, tank cap,
  unit scale) reuse the bundle in milliseconds.

## Scripts

```bash
npm run dev        # dev server (proxies /simulation to the backend :8420)
npm run build      # typecheck + production build
npm run typecheck  # tsc --noEmit
npm run lint       # eslint
npm run test       # vitest unit tests
npm run test:e2e   # playwright (run under xvfb in headless containers)
npm run gen:api    # regenerate API types from ./openapi.json
```

E2E tests mock the backend via route interception, so they never wait on
the real FEM solve. In a headless container, run them under a virtual
display: `xvfb-run -a npm run test:e2e`.
