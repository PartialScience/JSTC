/**
 * A small LRU cache of matrix bundles keyed by a stable hash of the coil.
 *
 * The expensive FEM matrix bundle depends only on the coil geometry, and the
 * server stamps each bundle with a geometry fingerprint it validates on every
 * request. The client can't compute that fingerprint itself, so we key the
 * cache on a stable serialization of the *whole* coil: a cache hit therefore
 * means the exact same coil, so the stored bundle is guaranteed to match (no
 * false hits — the server would 409 otherwise, and never does on a hit).
 *
 * This makes revisiting any previously-solved geometry — undo/redo,
 * revert-and-retry, A/B comparisons — reuse its bundle and skip the FEM
 * solve entirely (only the fast /analyze call runs). Coils that differ only
 * in non-geometry fields (unit scale, materials, tank capacitance) map to
 * different keys but the same bundle; that harmless duplication is bounded by
 * the LRU capacity, and it keeps us from having to mirror the server's
 * fingerprint-exclusion logic on the client.
 */

/** Deterministic JSON with sorted object keys, so structurally equal coils
 *  serialize identically regardless of property insertion order. */
export function stableStringify(value: unknown): string {
  if (value === null || typeof value !== 'object') return JSON.stringify(value) ?? 'null';
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`;
  const obj = value as Record<string, unknown>;
  const keys = Object.keys(obj).sort();
  return `{${keys.map((k) => `${JSON.stringify(k)}:${stableStringify(obj[k])}`).join(',')}}`;
}

/** Insertion-ordered LRU cache. get() promotes to most-recently-used;
 *  set() evicts the least-recently-used once capacity is exceeded. */
export class LruCache<V> {
  private readonly map = new Map<string, V>();

  constructor(private readonly capacity: number) {
    if (capacity < 1) throw new Error('LruCache capacity must be >= 1');
  }

  get(key: string): V | undefined {
    const value = this.map.get(key);
    if (value !== undefined) {
      // Re-insert to mark most-recently-used.
      this.map.delete(key);
      this.map.set(key, value);
    }
    return value;
  }

  set(key: string, value: V): void {
    if (this.map.has(key)) this.map.delete(key);
    this.map.set(key, value);
    while (this.map.size > this.capacity) {
      const oldest = this.map.keys().next().value;
      if (oldest === undefined) break;
      this.map.delete(oldest);
    }
  }

  has(key: string): boolean {
    return this.map.has(key);
  }

  get size(): number {
    return this.map.size;
  }
}
