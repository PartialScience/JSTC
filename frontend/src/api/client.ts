/**
 * Typed API client. All request/response shapes come from the backend's
 * OpenAPI schema (src/api/schema.ts, regenerate with `npm run gen:api`), so
 * the coil the frontend edits IS the schema the backend validates.
 */
import createClient from 'openapi-fetch';

import type { components, paths } from './schema';

export const api = createClient<paths>({
  baseUrl: import.meta.env.VITE_API_BASE ?? '',
});

// Convenient aliases for the schema component types used across the app.
export type CoilSchema = components['schemas']['SimulatableTeslaCoilSchema'];
export type SecondarySchema = components['schemas']['LinearSecondaryConductorSchema'];
export type PrimarySchema = components['schemas']['LinearPrimarySchema'];
export type ToploadSchema = components['schemas']['ToploadSchema'];
export type GroundSchema = components['schemas']['GroundedConductorSchema'];
export type GeometrySchema =
  | components['schemas']['CircleSchema']
  | components['schemas']['RectangleSchema']
  | components['schemas']['PolygonSchema'];
export type CrossSectionSchema =
  | components['schemas']['CircularCrossSectionSchema']
  | components['schemas']['RectangularCrossSectionSchema'];
export type TurnProfileSchema = components['schemas']['UniformTurnProfileSchema'];
export type MaterialSchema = components['schemas']['MaterialSchema'];
export type BoundaryConditionSchema = components['schemas']['BoundaryConditionSchema'];

export type MatrixBundle = components['schemas']['MatrixBundleSchema'];
export type AnalysisResponse = components['schemas']['AnalysisResponse'];
export type SecondaryOutputs = components['schemas']['SecondaryOutputs'];
export type EigenModesOutputs = components['schemas']['EigenModesOutputs'];
export type PrimaryOutputs = components['schemas']['PrimaryOutputs'];
export type CouplingOutputs = components['schemas']['CouplingOutputs'];
export type CoupledOutputs = components['schemas']['CoupledOutputs'];
export type ImpedanceResponse = components['schemas']['ImpedanceResponse'];
export type ImpedancePoint = components['schemas']['ImpedancePoint'];
export type SpiceResponse = components['schemas']['SpiceResponse'];
export type FieldRequest = components['schemas']['FieldRequest'];
export type FieldResponse = components['schemas']['FieldResponse'];
export type FieldType = FieldRequest['field_type'];
export type ReferenceMode = NonNullable<FieldRequest['reference_mode']>;
export type HotEnd = NonNullable<FieldRequest['hot_end']>;
