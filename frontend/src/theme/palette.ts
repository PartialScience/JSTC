/**
 * The single source of truth for every color in the app.
 *
 * Nothing else in the codebase should contain a literal color. CSS reads
 * these values through generated custom properties (see ThemeProvider);
 * the Konva canvas and the Recharts plots read the same objects directly
 * via `useTheme()`. To retheme, edit here and only here.
 */
import type { MaterialSchema } from '../api/client';

export type ThemeName = 'dark' | 'light';

/** Outline / fill / handle colors for one drawn coil component. */
export interface ComponentPalette {
  /** Outline color. */
  stroke: string;
  /** Translucent interior fill. */
  fill: string;
  /** Accent for the wire/width drag handle. */
  handle: string;
}

export interface ThemeColors {
  // --- Surfaces & chrome (exposed to CSS as custom properties) ---
  bg: string;
  panel: string;
  panelAlt: string;
  border: string;
  /** A stronger border for inputs and dividers that need more contrast. */
  borderStrong: string;
  text: string;
  muted: string;
  accent: string;
  /** Text drawn on top of an accent-colored surface. */
  accentText: string;
  inputBg: string;
  danger: string;
  /** Text drawn on a translucent danger surface (error banner). */
  dangerText: string;
  success: string;
  successHover: string;
  /** Text drawn on the success button. */
  successText: string;

  // --- Editor canvas (Konva; JS only) ---
  canvasBg: string;
  wall: string;
  axis: string;
  axisLabel: string;
  handleFill: string;
  handleStroke: string;
  vertexHandle: string;
  /** Translucent fill of the marquee selection rectangle (its border uses
   *  `handleFill`). */
  selectionFill: string;

  // --- Bode / impedance plots (Recharts; JS only) ---
  chartGrid: string;
  chartAxis: string;
  chartMagnitude: string;
  chartPhase: string;
  /** Dashed reference lines marking the coupled mode frequencies. */
  chartMarker: string;
  chartZero: string;
  tooltipBg: string;
  tooltipBorder: string;
  /** Categorical series colors for multi-line plots (eigenmodes). Tuned per
   *  theme so every entry stays legible against that theme's plot background;
   *  cycled when there are more series than colors. */
  chartSeries: string[];

  // --- Drawn coil components ---
  /** The resonator: always red, independent of its wire material. */
  secondary: ComponentPalette;
  /** Per-material colors for the primary, toploads, and grounds. */
  materials: Record<MaterialSchema, ComponentPalette>;
}

const DARK: ThemeColors = {
  bg: '#0b1120',
  panel: '#0f172a',
  panelAlt: '#111c33',
  border: '#1e293b',
  borderStrong: '#334155',
  text: '#e2e8f0',
  muted: '#64748b',
  accent: '#38bdf8',
  accentText: '#06283d',
  inputBg: '#0b1120',
  danger: '#f87171',
  dangerText: '#fecaca',
  success: '#16a34a',
  successHover: '#22c55e',
  successText: '#f0fdf4',

  canvasBg: '#0b1120',
  wall: '#1e293b',
  axis: '#334155',
  axisLabel: '#475569',
  handleFill: '#38bdf8',
  handleStroke: '#0c4a6e',
  vertexHandle: '#c084fc',
  selectionFill: 'rgba(56,189,248,0.12)',

  chartGrid: '#1e293b',
  chartAxis: '#94a3b8',
  chartMagnitude: '#38bdf8',
  chartPhase: '#a78bfa',
  chartMarker: '#f59e0b',
  chartZero: '#334155',
  tooltipBg: '#0f172a',
  tooltipBorder: '#334155',
  // Bright, saturated hues that read clearly on the near-black plot bg.
  chartSeries: [
    '#38bdf8', '#f472b6', '#4ade80', '#fbbf24', '#a78bfa',
    '#22d3ee', '#fb923c', '#f87171', '#a3e635', '#e879f9',
  ],

  secondary: {
    stroke: '#ef4444',
    fill: 'rgba(239,68,68,0.15)',
    handle: '#f87171',
  },
  materials: {
    copper: {
      stroke: '#e0894a',
      fill: 'rgba(224,137,74,0.18)',
      handle: '#f0a868',
    },
    aluminum: {
      stroke: '#b0b8c0',
      fill: 'rgba(176,184,192,0.18)',
      handle: '#d5dbe2',
    },
  },
};

const LIGHT: ThemeColors = {
  bg: '#f1f5f9',
  panel: '#ffffff',
  panelAlt: '#f8fafc',
  border: '#e2e8f0',
  borderStrong: '#cbd5e1',
  text: '#0f172a',
  muted: '#64748b',
  accent: '#0284c7',
  accentText: '#f0f9ff',
  inputBg: '#ffffff',
  danger: '#dc2626',
  dangerText: '#7f1d1d',
  success: '#16a34a',
  successHover: '#15803d',
  successText: '#f0fdf4',

  canvasBg: '#eef2f7',
  wall: '#cbd5e1',
  axis: '#94a3b8',
  axisLabel: '#94a3b8',
  handleFill: '#0284c7',
  handleStroke: '#075985',
  vertexHandle: '#9333ea',
  selectionFill: 'rgba(2,132,199,0.12)',

  chartGrid: '#e2e8f0',
  chartAxis: '#475569',
  chartMagnitude: '#0284c7',
  chartPhase: '#7c3aed',
  chartMarker: '#d97706',
  chartZero: '#cbd5e1',
  tooltipBg: '#ffffff',
  tooltipBorder: '#cbd5e1',
  // Darker, saturated hues that stay legible on the near-white plot bg.
  chartSeries: [
    '#0284c7', '#db2777', '#16a34a', '#d97706', '#7c3aed',
    '#0891b2', '#ea580c', '#dc2626', '#65a30d', '#c026d3',
  ],

  secondary: {
    stroke: '#dc2626',
    fill: 'rgba(220,38,38,0.12)',
    handle: '#ef4444',
  },
  materials: {
    copper: {
      stroke: '#b45c2e',
      fill: 'rgba(180,92,46,0.14)',
      handle: '#d97a45',
    },
    aluminum: {
      stroke: '#6b7280',
      fill: 'rgba(107,114,128,0.14)',
      handle: '#9ca3af',
    },
  },
};

export const THEMES: Record<ThemeName, ThemeColors> = { dark: DARK, light: LIGHT };
