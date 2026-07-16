/**
 * The operating-field query for the current field view, assembled from the
 * store in one place so both the canvas (which draws it) and the sidebar (which
 * reads probe values off it) call the exact same thing. react-query dedupes by
 * the value-based key, so the two callers share a single fetch.
 */
import type { CoilSchema } from '../api/client';
import { useField } from '../api/simulation';
import { FIELD_GRID_NR, FIELD_GRID_NZ, FIELD_VIEW_MODES, useEditorStore } from './store';

export function useViewField() {
  const coil = useEditorStore((s) => s.coil);
  const bundle = useEditorStore((s) => s.bundle);
  const analysis = useEditorStore((s) => s.analysis);
  const viewMode = useEditorStore((s) => s.viewMode);
  const drive = useEditorStore((s) => s.fieldDrive);
  const fieldMode = FIELD_VIEW_MODES.includes(viewMode);

  // The user's frequency, or the lower split mode (falling back to the
  // secondary resonance) when left at 0 ("auto") — same rule as the panel.
  const effectiveFreq =
    drive.frequencyHz > 0
      ? drive.frequencyHz
      : (analysis?.coupled?.split_lower ?? analysis?.secondary.resonant_frequency ?? 0);

  return useField(
    coil as unknown as CoilSchema,
    bundle,
    {
      fieldType: viewMode === 'bfield' ? 'magnetic' : 'electric',
      frequencyHz: effectiveFreq,
      primaryCurrent: drive.primaryCurrent,
      referenceMode: drive.referenceMode,
      hotEnd: drive.hotEnd,
      gridNr: FIELD_GRID_NR,
      gridNz: FIELD_GRID_NZ,
    },
    fieldMode,
  );
}
