import { beforeEach, describe, expect, it } from 'vitest';

import { blankCoil, defaultCoil } from '../domain/coil';
import type { AnalysisResponse } from '../api/client';
import { useEditorStore } from './store';

const analysis = {
  secondary: { resonant_frequency: 231000 },
  bundle: { geometry_fingerprint: 'fp', discretization_order: 30 },
} as unknown as AnalysisResponse;

const reset = () =>
  useEditorStore.setState({
    coil: defaultCoil(),
    selection: [{ kind: 'secondary' }],
    revision: 0,
    past: [],
    future: [],
    analysis: null,
    bundle: null,
    analyzedRevision: null,
  });

// The hook derives dirty as `analyzedRevision !== revision`; assert on that.
const isDirty = () => {
  const s = useEditorStore.getState();
  return s.analyzedRevision !== s.revision;
};

describe('session actions', () => {
  beforeEach(reset);

  it('markRun + recordAnalysis mark results up to date', () => {
    const rev = useEditorStore.getState().revision;
    useEditorStore.getState().markRun(rev);
    useEditorStore.getState().recordAnalysis(analysis);
    const s = useEditorStore.getState();
    expect(s.analysis).toBe(analysis);
    expect(s.bundle).toBe(analysis.bundle);
    expect(isDirty()).toBe(false);
  });

  it('an edit after a run makes results stale', () => {
    const rev = useEditorStore.getState().revision;
    useEditorStore.getState().markRun(rev);
    useEditorStore.getState().recordAnalysis(analysis);
    useEditorStore.getState().updateSecondary({ wire_dia: 0.05 });
    expect(isDirty()).toBe(true);
  });

  it('loadSession with fresh outputs reads as up to date', () => {
    useEditorStore.getState().loadSession({ coil: blankCoil(), analysis, stale: false });
    const s = useEditorStore.getState();
    expect(s.coil.primary).toBeNull();
    expect(s.analysis).toBe(analysis);
    expect(s.bundle).toBe(analysis.bundle);
    expect(isDirty()).toBe(false);
  });

  it('loadSession with stale outputs reads as dirty but keeps the outputs', () => {
    useEditorStore.getState().loadSession({ coil: blankCoil(), analysis, stale: true });
    expect(useEditorStore.getState().analysis).toBe(analysis);
    expect(isDirty()).toBe(true);
  });

  it('loadSession with no outputs clears analysis and reads as never-run', () => {
    // Seed some outputs first, then load a session without any.
    useEditorStore.getState().recordAnalysis(analysis);
    useEditorStore.getState().loadSession({ coil: defaultCoil(), analysis: null, stale: false });
    const s = useEditorStore.getState();
    expect(s.analysis).toBeNull();
    expect(s.bundle).toBeNull();
    expect(s.analyzedRevision).toBeNull();
  });

  it('loadSession is a single undo step', () => {
    const before = useEditorStore.getState().coil;
    useEditorStore.getState().loadSession({ coil: blankCoil(), analysis: null, stale: false });
    useEditorStore.getState().undo();
    expect(useEditorStore.getState().coil).toBe(before);
  });
});
