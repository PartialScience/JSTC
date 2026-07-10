/**
 * Theme context and the machinery that applies a palette to the document.
 * The active theme simply follows the OS color-scheme preference — there is
 * no manual override. Kept component-free (no JSX) so the provider file can
 * stay fast-refresh friendly.
 */
import { createContext, useContext } from 'react';

import { THEMES, type ThemeColors, type ThemeName } from './palette';

/** `panelAlt` -> `--panel-alt`. */
function cssVarName(key: string): string {
  return `--${key.replace(/[A-Z]/g, (m) => `-${m.toLowerCase()}`)}`;
}

/** Push a theme's scalar colors onto :root as custom properties and stamp
 *  `data-theme`. Nested component palettes are JS-only and skipped. */
export function applyTheme(name: ThemeName): void {
  const root = document.documentElement;
  for (const [key, value] of Object.entries(THEMES[name])) {
    if (typeof value === 'string') root.style.setProperty(cssVarName(key), value);
  }
  root.setAttribute('data-theme', name);
}

/** The OS color-scheme preference (defaults to dark). */
export function systemTheme(): ThemeName {
  return window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

// Apply synchronously at import time so the first paint is already themed
// (no flash of a wrong palette before React mounts).
export const initialTheme = systemTheme();
applyTheme(initialTheme);

export interface ThemeContextValue {
  name: ThemeName;
  colors: ThemeColors;
}

export const ThemeContext = createContext<ThemeContextValue>({
  name: initialTheme,
  colors: THEMES[initialTheme],
});

/** The active theme: its name and resolved color objects. */
export function useTheme(): ThemeContextValue {
  return useContext(ThemeContext);
}

/** The active theme's color objects (convenience for render code). */
export function useThemeColors(): ThemeColors {
  return useContext(ThemeContext).colors;
}
