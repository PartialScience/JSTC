import type { Page } from '@playwright/test';

/**
 * Install a mocked backend via route interception. Returns canned, stable
 * responses for the simulation endpoints so e2e tests exercise the full UI
 * flow (edit -> request -> results) without the real FEM solve. Also counts
 * calls so tests can assert the caching behavior (matrices fetched rarely,
 * analyze often).
 */
export interface MockStats {
  matrices: number;
  analyze: number;
  impedance: number;
  spice: number;
  field: number;
  /** The most recent impedance sweep the frontend requested. */
  lastImpedance?: { count: number; fminHz: number; fmaxHz: number };
  lastFieldType?: 'electric' | 'magnetic';
}

const bundle = {
  nodal_capacitance: [
    [1, -0.5],
    [-0.5, 1],
  ],
  topload_charge: [0.1, 0.2],
  inductance: [[2]],
  coupling: [0.3],
  discretization_order: 30,
  geometry_fingerprint: 'mock-fingerprint',
};

const analysis = {
  secondary: {
    resonant_frequency: 231213.6,
    eigen_frequencies: [231213.6, 865632.4, 1393598.4],
    dc_inductance: 0.01735,
    effective_series_inductance: 0.01697,
    energy_inductance: 0.01734,
    dc_capacitance: 4.006e-11,
    effective_shunt_capacitance: 2.792e-11,
    energy_capacitance: 2.733e-11,
    topload_effective_capacitance: 2.327e-11,
    winding_length: 0.554,
    conductor_length: 324.13,
    coil_pitch: 6.19e-4,
    turns_per_length: 1615.7,
    turn_spacing: 1.08e-4,
    mean_diameter: 0.1153,
    aspect_ratio: 4.805,
    inclination_degrees: 90,
    reactance_at_resonance: 24654.7,
    skin_depth: 1.356e-4,
    dc_resistance: 26.56,
    ac_resistance: 87.54,
    quality_factor: 281.6,
    wire_weight: 0.595,
  },
  primary: {
    dc_inductance: 2.559e-5,
    lead_inductance: 8.61e-7,
    total_inductance: 2.645e-5,
    resonant_frequency: 225679.9,
    percent_detuned: 2.452,
    wire_length: 7.891,
    coil_pitch: 0.0127,
    turn_spacing: 0.00635,
    dc_resistance: 0.00418,
  },
  coupling: {
    mutual_inductance: 8.648e-5,
    coupling_coefficient: 0.1298,
    half_cycles_for_energy_transfer: 7.706,
    energy_transfer_time: 1.687e-5,
  },
  coupled: {
    mode_frequencies: [214523.2, 245127.5, 874037.9],
    split_lower: 214523.2,
    split_upper: 245127.5,
    frequency_split: 30604.3,
  },
  modes: {
    frequencies: [231213.6, 865632.4, 1393598.4],
    voltage_positions: [0, 0.25, 0.5, 0.75, 1],
    current_positions: [0.125, 0.375, 0.625, 0.875],
    voltage_modes: [
      [0, 0.38, 0.71, 0.92, 1.0],
      [0, 0.85, 0.55, -0.35, 0.6],
      [0, 0.9, -0.4, 0.7, 0.3],
    ],
    current_modes: [
      [1.0, 0.85, 0.55, 0.2],
      [1.0, -0.2, -0.8, 0.4],
      [0.9, -0.7, 0.5, -0.3],
    ],
  },
  bundle,
};

// Fields the server excludes from the geometry fingerprint (a change to
// them reuses the bundle). Mirrored here so the mock 409s on real geometry
// changes but not on cheap edits, exercising the client's bundle caching.
const CHEAP_KEYS = new Set([
  'unit_scale',
  'material',
  'tank_capacitance',
  'lead_length',
  'lead_dia',
]);

function mockFingerprint(coil: unknown): string {
  const strip = (v: unknown): unknown => {
    if (Array.isArray(v)) return v.map(strip);
    if (v && typeof v === 'object') {
      const out: Record<string, unknown> = {};
      for (const [k, val] of Object.entries(v as Record<string, unknown>)) {
        if (!CHEAP_KEYS.has(k)) out[k] = strip(val);
      }
      return out;
    }
    return v;
  };
  return JSON.stringify(strip(coil));
}

export async function installMockApi(page: Page): Promise<MockStats> {
  const stats: MockStats = { matrices: 0, analyze: 0, impedance: 0, spice: 0, field: 0 };

  await page.route('**/simulation/matrices', async (route) => {
    stats.matrices += 1;
    const body = route.request().postDataJSON() as { coil: unknown };
    await route.fulfill({
      json: { ...bundle, geometry_fingerprint: mockFingerprint(body.coil) },
    });
  });

  await page.route('**/simulation/analyze', async (route) => {
    stats.analyze += 1;
    const body = route.request().postDataJSON() as {
      coil: unknown;
      bundle?: { geometry_fingerprint: string };
    };
    const fp = mockFingerprint(body.coil);
    // A passed bundle that doesn't match this geometry is stale -> 409, just
    // like the real server, so the client refetches matrices.
    if (body.bundle && body.bundle.geometry_fingerprint !== fp) {
      await route.fulfill({ status: 409, json: { detail: 'stale bundle' } });
      return;
    }
    const stamped = { ...bundle, geometry_fingerprint: fp };
    await route.fulfill({ json: { ...analysis, bundle: stamped } });
  });

  await page.route('**/simulation/impedance', async (route) => {
    stats.impedance += 1;
    // Echo the requested sweep so tests can assert the controls took effect.
    const body = route.request().postDataJSON() as { frequencies_hz: number[] };
    const freqs = body.frequencies_hz ?? [];
    stats.lastImpedance = {
      count: freqs.length,
      fminHz: freqs[0] ?? 0,
      fmaxHz: freqs[freqs.length - 1] ?? 0,
    };
    const points = freqs.map((f) => {
      // A peak near the secondary resonance.
      const mag = 200 / (1 + Math.abs(f - 231e3) / 2e3);
      return { frequency_hz: f, resistance: mag * 0.3, reactance: mag * 0.9, magnitude: mag };
    });
    await route.fulfill({ json: { points, bundle } });
  });

  await page.route('**/simulation/spice', async (route) => {
    stats.spice += 1;
    await route.fulfill({
      json: {
        netlist: '* mock\n.subckt teslacoil prim_in prim_gnd\n.ends teslacoil\n',
        bundle,
      },
    });
  });

  await page.route('**/simulation/field', async (route) => {
    stats.field += 1;
    const body = route.request().postDataJSON() as {
      field_type: 'electric' | 'magnetic';
      grid_nr: number;
      grid_nz: number;
    };
    stats.lastFieldType = body.field_type;
    const nr = body.grid_nr;
    const nz = body.grid_nz;
    const real: number[] = [];
    const imag: number[] = [];
    const mask: boolean[] = [];
    // A smooth synthetic field: potential rising toward the top.
    for (let iz = 0; iz < nz; iz++) {
      for (let ir = 0; ir < nr; ir++) {
        real.push((iz / (nz - 1)) * 1000 - (ir / (nr - 1)) * 100);
        imag.push(0);
        mask.push(true);
      }
    }
    await route.fulfill({
      json: {
        field_type: body.field_type,
        quantity: body.field_type === 'electric' ? 'potential [V]' : 'vector_potential [T*m]',
        nr,
        nz,
        r_min: 0,
        r_max: 100,
        z_min: 0,
        z_max: 150,
        unit_scale: 0.0254,
        real,
        imag,
        mask,
        bundle,
      },
    });
  });

  return stats;
}
