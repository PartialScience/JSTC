/**
 * Provenance exhaustiveness: every input-schema property reachable from the
 * coil must be explicitly classified trusted/untrusted, every untrusted key
 * must be covered by a registry entry, and the registry predicates must fire
 * on the right coils. Walks the GENERATED OpenAPI document, so adding a
 * field to the backend schema fails this test until someone answers "has
 * this been experimentally verified yet?".
 */
import { describe, expect, it } from 'vitest';

import openapi from '../../openapi.json';
import { blankCoil, defaultCoil, type Coil } from './coil';
import {
  SCHEMA_PROVENANCE,
  UNVALIDATED_FEATURES,
  activeUnvalidatedFeatures,
} from './provenance';

type SchemaNode = {
  $ref?: string;
  properties?: Record<string, SchemaNode>;
  items?: SchemaNode;
  anyOf?: SchemaNode[];
  oneOf?: SchemaNode[];
  allOf?: SchemaNode[];
  additionalProperties?: SchemaNode | boolean;
};

const components: Record<string, SchemaNode> = (
  openapi as unknown as { components: { schemas: Record<string, SchemaNode> } }
).components.schemas;

/** Every "SchemaName.property" key reachable from the coil schema. */
function reachablePropertyKeys(rootName: string): string[] {
  const seen = new Set<string>();
  const keys: string[] = [];

  const refName = (ref: string) => ref.replace('#/components/schemas/', '');

  const visitSchema = (name: string) => {
    if (seen.has(name)) return;
    seen.add(name);
    const node = components[name];
    if (!node) throw new Error(`Missing component schema: ${name}`);
    visitNode(node, name);
  };

  const visitNode = (node: SchemaNode, owner: string) => {
    if (node.$ref) {
      visitSchema(refName(node.$ref));
      return;
    }
    for (const sub of [...(node.anyOf ?? []), ...(node.oneOf ?? []), ...(node.allOf ?? [])]) {
      visitNode(sub, owner);
    }
    if (node.items) visitNode(node.items, owner);
    if (node.properties) {
      for (const [prop, child] of Object.entries(node.properties)) {
        keys.push(`${owner}.${prop}`);
        visitNode(child, owner);
      }
    }
  };

  visitSchema(rootName);
  return keys;
}

describe('schema provenance map', () => {
  const keys = reachablePropertyKeys('SimulatableTeslaCoilSchema');

  it('reaches the schemas we expect (sanity)', () => {
    expect(keys).toContain('SecondaryConductorSchema.path');
    expect(keys).toContain('ArcPathSchema.mid');
    expect(keys).toContain('GradedTurnProfileSchema.points');
  });

  it('classifies EVERY reachable input property (exhaustive)', () => {
    const missing = keys.filter((k) => !(k in SCHEMA_PROVENANCE));
    expect(
      missing,
      `Unclassified schema properties — add each to SCHEMA_PROVENANCE in ` +
        `domain/provenance.ts, explicitly answering "has this been ` +
        `experimentally verified yet?": ${missing.join(', ')}`,
    ).toEqual([]);
  });

  it('carries no stale keys for properties that no longer exist', () => {
    const known = new Set(keys);
    const stale = Object.keys(SCHEMA_PROVENANCE).filter((k) => !known.has(k));
    expect(stale).toEqual([]);
  });

  it('covers every untrusted key with a registry entry', () => {
    const covered = (key: string) =>
      UNVALIDATED_FEATURES.some((f) => f.covers.some((prefix) => key.startsWith(prefix)));
    const uncovered = Object.entries(SCHEMA_PROVENANCE)
      .filter(([, v]) => v === 'untrusted')
      .map(([k]) => k)
      .filter((k) => !covered(k));
    expect(uncovered).toEqual([]);
  });
});

describe('unvalidated feature registry', () => {
  it('is quiet for the default (all-trusted) coil', () => {
    expect(activeUnvalidatedFeatures(defaultCoil())).toEqual([]);
  });

  it('fires per winding and per feature', () => {
    const coil: Coil = defaultCoil();
    const arcSecondary: Coil = {
      ...coil,
      secondary: {
        ...coil.secondary,
        path: { kind: 'arc', start: [1, 1], mid: [1.8, 2] as [number, number], end: [1, 3] },
      },
    };
    expect(activeUnvalidatedFeatures(arcSecondary).map((f) => f.id)).toEqual([
      'arc-secondary',
    ]);

    const gradedSplinePrimary: Coil = {
      ...coil,
      primary: {
        ...coil.primary!,
        path: { kind: 'spline', points: [[2, 1], [3, 1.2], [4, 1.8]] },
        turn_fxn: { kind: 'graded', points: [[0, 0], [0.5, 6], [1, 8]] },
      },
    };
    expect(activeUnvalidatedFeatures(gradedSplinePrimary).map((f) => f.id)).toEqual([
      'spline-primary',
      'graded-primary-turns',
    ]);
  });

  it('evaluates on coil state, not on anything mounted', () => {
    // A primary-less coil cannot fire primary entries even with weird paths
    const coil = blankCoil();
    expect(activeUnvalidatedFeatures(coil)).toEqual([]);
  });
});
