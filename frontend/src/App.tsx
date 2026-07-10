import { lazy, Suspense } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { useAnalysis } from './api/simulation';
import { CoilCanvas } from './editor/CoilCanvas';
import { useEditorStore } from './state/store';

// The 3-D viewer pulls in three.js + drei (a large dependency), so load it
// lazily — the bundle is fetched only when the user first opens the 3-D view.
const Coil3DView = lazy(() => import('./three/Coil3DView'));
import { useEditorKeyboard } from './state/useEditorKeyboard';
import { useUndoRedo } from './state/useUndoRedo';
import { ThemeProvider } from './theme';
import { ContextMenu } from './ui/ContextMenu';
import { Results } from './ui/Results';
import { Sidebar } from './ui/Sidebar';
import { Toolbar } from './ui/Toolbar';
import { TopBar } from './ui/TopBar';

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false } },
});

function Workspace() {
  const coil = useEditorStore((s) => s.coil);
  const revision = useEditorStore((s) => s.revision);
  const viewMode = useEditorStore((s) => s.viewMode);
  const analysis = useAnalysis(coil, revision);
  useUndoRedo();
  useEditorKeyboard();

  return (
    <div className="app">
      <TopBar dirty={analysis.dirty} />
      <div className="editor-pane">
        <Sidebar />
        <div className="canvas-column">
          <Toolbar
            onRun={analysis.run}
            running={analysis.isFetching}
            dirty={analysis.dirty}
            hasRun={analysis.hasRun}
          />
          <div className="canvas-host">
            {viewMode === '3d' ? (
              <Suspense fallback={<div className="canvas-loading">Loading 3-D view…</div>}>
                <Coil3DView />
              </Suspense>
            ) : (
              <CoilCanvas />
            )}
          </div>
        </div>
      </div>

      <Results
        coil={coil}
        analysis={analysis.data}
        bundle={analysis.bundle}
        isFetching={analysis.isFetching}
        dirty={analysis.dirty}
        hasRun={analysis.hasRun}
        onRun={analysis.run}
        isError={analysis.isError}
        error={analysis.error}
      />

      <ContextMenu />
    </div>
  );
}

export function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <Workspace />
      </QueryClientProvider>
    </ThemeProvider>
  );
}
