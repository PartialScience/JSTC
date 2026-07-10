/**
 * Provides the active theme to the tree. The theme follows the OS
 * color-scheme preference and updates live when the user changes it (no
 * manual override). Color definitions live in ./palette; the context/apply
 * machinery lives in ./context.
 */
import { useEffect, useMemo, useState, type ReactNode } from 'react';

import { THEMES } from './palette';
import {
  applyTheme,
  initialTheme,
  systemTheme,
  ThemeContext,
  type ThemeContextValue,
} from './context';

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [name, setName] = useState(initialTheme);

  // Track the OS color-scheme preference and re-sync whenever it flips.
  useEffect(() => {
    const mql = window.matchMedia?.('(prefers-color-scheme: light)');
    if (!mql) return;
    const sync = () => setName(systemTheme());
    sync(); // catch a change that happened between import and mount
    mql.addEventListener('change', sync);
    return () => mql.removeEventListener('change', sync);
  }, []);

  useEffect(() => {
    applyTheme(name);
  }, [name]);

  const value = useMemo<ThemeContextValue>(
    () => ({ name, colors: THEMES[name] }),
    [name],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}
