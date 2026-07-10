import { describe, expect, it } from 'vitest';

import { LruCache, stableStringify } from './bundleCache';

describe('stableStringify', () => {
  it('is independent of key insertion order', () => {
    expect(stableStringify({ a: 1, b: 2 })).toBe(stableStringify({ b: 2, a: 1 }));
  });

  it('distinguishes different values', () => {
    expect(stableStringify({ a: 1 })).not.toBe(stableStringify({ a: 2 }));
  });

  it('handles nested objects and arrays', () => {
    const x = { p: [1, { z: 9, y: 8 }], q: null };
    const y = { q: null, p: [1, { y: 8, z: 9 }] };
    expect(stableStringify(x)).toBe(stableStringify(y));
  });

  it('separates array order (order is significant)', () => {
    expect(stableStringify([1, 2])).not.toBe(stableStringify([2, 1]));
  });
});

describe('LruCache', () => {
  it('stores and retrieves values', () => {
    const c = new LruCache<number>(3);
    c.set('a', 1);
    expect(c.get('a')).toBe(1);
    expect(c.get('missing')).toBeUndefined();
  });

  it('evicts the least-recently-used entry beyond capacity', () => {
    const c = new LruCache<number>(2);
    c.set('a', 1);
    c.set('b', 2);
    c.set('c', 3); // evicts 'a'
    expect(c.has('a')).toBe(false);
    expect(c.get('b')).toBe(2);
    expect(c.get('c')).toBe(3);
  });

  it('get() promotes an entry so it survives eviction', () => {
    const c = new LruCache<number>(2);
    c.set('a', 1);
    c.set('b', 2);
    c.get('a'); // 'a' now most-recently-used
    c.set('c', 3); // evicts 'b', not 'a'
    expect(c.has('a')).toBe(true);
    expect(c.has('b')).toBe(false);
  });

  it('updating an existing key refreshes it without growing', () => {
    const c = new LruCache<number>(2);
    c.set('a', 1);
    c.set('b', 2);
    c.set('a', 11); // refresh 'a'
    c.set('c', 3); // evicts 'b'
    expect(c.get('a')).toBe(11);
    expect(c.has('b')).toBe(false);
    expect(c.size).toBe(2);
  });

  it('rejects a capacity below 1', () => {
    expect(() => new LruCache<number>(0)).toThrow();
  });
});
