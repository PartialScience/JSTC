/**
 * Simulation data hooks. These implement the caching contract the backend
 * was designed for: the expensive geometric matrix bundle is fetched once
 * per geometry and reused for the fast endpoints. A 409 (stale bundle)
 * transparently refetches matrices and retries.
 */
import { useCallback, useMemo, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { api } from './client';
import type {
  AnalysisResponse,
  CoilSchema,
  FieldResponse,
  FieldType,
  HotEnd,
  ImpedanceResponse,
  MatrixBundle,
  ReferenceMode,
  SpiceResponse,
} from './client';
import { LruCache, stableStringify } from './bundleCache';
import { useEditorStore } from '../state/store';

export interface FieldParams {
  fieldType: FieldType;
  frequencyHz: number;
  primaryCurrent: number;
  referenceMode: ReferenceMode;
  hotEnd: HotEnd;
  gridNr: number;
  gridNz: number;
}

/** How many recent geometries' bundles to keep for instant revisits. */
const BUNDLE_CACHE_CAPACITY = 24;

class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function computeMatrices(coil: CoilSchema): Promise<MatrixBundle> {
  const { data, error, response } = await api.POST('/simulation/matrices', {
    body: { coil },
  });
  if (error || !data) throw new ApiError(`matrices request failed (HTTP ${response.status})`, response.status);
  return data;
}

/**
 * On-demand full analysis for a coil, caching and reusing the matrix
 * bundle. The calculation runs only when `run()` is called (the Run
 * button) - not on every edit - since the FEM solve is expensive. A change
 * the backend deems geometric (409) triggers a fresh matrices fetch; cheap
 * changes reuse the cached bundle in milliseconds.
 *
 * The results themselves (analysis, bundle, and which revision they cover)
 * live in the editor store, so the whole session is serializable and can be
 * restored on import. This hook is the driver: it fetches and writes results
 * back to the store, and derives `dirty`/`hasRun` from it. An imported
 * session's bundle is picked up as a request candidate below, so re-running a
 * loaded coil reuses its matrices instead of re-solving.
 *
 * `dirty` is true when the coil has changed since the last run, so the UI
 * can flag stale results.
 */
export function useAnalysis(coil: CoilSchema, revision: number) {
  // Most-recent bundle (fallback candidate for a small edit) plus an LRU
  // cache of bundles by coil, so revisiting a previously-solved geometry
  // (undo/redo, revert) reuses its bundle and skips the FEM matrices solve.
  const bundleRef = useRef<MatrixBundle | null>(null);
  const cacheRef = useRef(new LruCache<MatrixBundle>(BUNDLE_CACHE_CAPACITY));

  const analysis = useEditorStore((s) => s.analysis);
  const bundle = useEditorStore((s) => s.bundle);
  const analyzedRevision = useEditorStore((s) => s.analyzedRevision);
  const markRun = useEditorStore((s) => s.markRun);
  const recordAnalysis = useEditorStore((s) => s.recordAnalysis);

  const query = useQuery<AnalysisResponse>({
    queryKey: ['analysis'],
    // Manual: never auto-runs; `run()` calls refetch with the latest coil.
    enabled: false,
    queryFn: async () => {
      const cache = cacheRef.current;
      const key = stableStringify(coil);

      const attempt = async (b: MatrixBundle | null) => {
        const { data, error, response } = await api.POST('/simulation/analyze', {
          body: b ? { coil, bundle: b } : { coil },
        });
        if (error || !data)
          throw new ApiError(`analyze request failed (HTTP ${response.status})`, response.status);
        return data;
      };

      // A cached bundle for this exact coil is guaranteed valid (the server
      // validates the fingerprint); otherwise fall back to the most recent
      // bundle, or a bundle restored from an imported session, as a hint - a
      // small edit reuses it, and a genuine geometry change 409s and refetches.
      const candidate = cache.get(key) ?? bundleRef.current ?? useEditorStore.getState().bundle;

      let result: AnalysisResponse;
      try {
        result = await attempt(candidate);
      } catch (e) {
        if (e instanceof ApiError && e.status === 409) {
          const fresh = await computeMatrices(coil);
          result = await attempt(fresh);
        } else {
          throw e;
        }
      }
      bundleRef.current = result.bundle;
      cache.set(key, result.bundle);
      recordAnalysis(result);
      return result;
    },
    retry: false,
    staleTime: Infinity,
  });

  const run = useCallback(() => {
    markRun(revision);
    void query.refetch();
  }, [markRun, query, revision]);

  const dirty = analyzedRevision !== revision;
  const hasRun = analyzedRevision !== null;
  // Display the store's analysis/bundle (authoritative, and restorable from an
  // imported session) rather than react-query's copy.
  return { ...query, data: analysis ?? undefined, bundle, run, dirty, hasRun };
}

/** Impedance sweep, reusing the analysis bundle. */
export function useImpedance(
  coil: CoilSchema,
  bundle: MatrixBundle | null | undefined,
  frequenciesHz: number[],
  opts: { includeLosses?: boolean; includeTank?: boolean } = {},
  enabled = true,
) {
  // Key on the sweep's identity (count + endpoints), so changing fmin/fmax
  // at the same point count still refetches. React Query hashes keys
  // structurally, so scalars here are compared by value.
  const lo = frequenciesHz[0];
  const hi = frequenciesHz[frequenciesHz.length - 1];
  const key = useMemo(
    () => ['impedance', bundle?.geometry_fingerprint, frequenciesHz.length, lo, hi, opts],
    [bundle?.geometry_fingerprint, frequenciesHz.length, lo, hi, opts],
  );
  return useQuery<ImpedanceResponse>({
    queryKey: key,
    enabled: enabled && !!bundle && frequenciesHz.length > 0,
    queryFn: async () => {
      const { data, error, response } = await api.POST('/simulation/impedance', {
        body: {
          coil,
          bundle: bundle ?? undefined,
          frequencies_hz: frequenciesHz,
          include_losses: opts.includeLosses ?? true,
          include_tank: opts.includeTank ?? true,
        },
      });
      if (error || !data)
        throw new ApiError(`impedance request failed (HTTP ${response.status})`, response.status);
      return data;
    },
    retry: false,
    staleTime: 60_000,
  });
}

/** Fetch a SPICE netlist on demand (not auto-run). */
export function useSpice() {
  const [state, setState] = useState<{
    loading: boolean;
    netlist: string | null;
    error: string | null;
  }>({ loading: false, netlist: null, error: null });

  const fetchSpice = useCallback(
    async (coil: CoilSchema, bundle: MatrixBundle | null | undefined, name = 'teslacoil') => {
      setState({ loading: true, netlist: null, error: null });
      const { data, error } = await api.POST('/simulation/spice', {
        body: { coil, bundle: bundle ?? undefined, subcircuit_name: name },
      });
      if (error || !data) {
        setState({ loading: false, netlist: null, error: 'SPICE export failed' });
        return null;
      }
      const resp = data as SpiceResponse;
      setState({ loading: false, netlist: resp.netlist, error: null });
      return resp.netlist;
    },
    [],
  );

  return { ...state, fetchSpice };
}

/** Operating field (E or B) on a grid, reusing the analysis bundle. Requires
 *  a primary tank capacitance (the drive is the coupled solve). */
export function useField(
  coil: CoilSchema,
  bundle: MatrixBundle | null | undefined,
  params: FieldParams,
  enabled = true,
) {
  const key = useMemo(
    () => [
      'field',
      bundle?.geometry_fingerprint,
      params.fieldType,
      params.frequencyHz,
      params.primaryCurrent,
      params.referenceMode,
      params.hotEnd,
      params.gridNr,
      params.gridNz,
    ],
    [bundle?.geometry_fingerprint, params],
  );
  return useQuery<FieldResponse>({
    queryKey: key,
    enabled: enabled && !!bundle && params.frequencyHz > 0,
    queryFn: async () => {
      const { data, error, response } = await api.POST('/simulation/field', {
        body: {
          coil,
          bundle: bundle ?? undefined,
          field_type: params.fieldType,
          frequency_hz: params.frequencyHz,
          primary_current: params.primaryCurrent,
          reference_mode: params.referenceMode,
          hot_end: params.hotEnd,
          grid_nr: params.gridNr,
          grid_nz: params.gridNz,
        },
      });
      if (error || !data)
        throw new ApiError(`field request failed (HTTP ${response.status})`, response.status);
      return data;
    },
    retry: false,
    staleTime: 60_000,
  });
}
