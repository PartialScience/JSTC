/** Engineering-notation formatting for SI result values. */
const PREFIXES: [number, string][] = [
  [1e9, 'G'],
  [1e6, 'M'],
  [1e3, 'k'],
  [1, ''],
  [1e-3, 'm'],
  [1e-6, 'µ'],
  [1e-9, 'n'],
  [1e-12, 'p'],
  [1e-15, 'f'],
];

export function eng(value: number, unit: string, sig = 3): string {
  if (value === 0) return `0 ${unit}`;
  if (!Number.isFinite(value)) return `— ${unit}`;
  const abs = Math.abs(value);
  const found = PREFIXES.find(([m]) => abs >= m) ?? PREFIXES[PREFIXES.length - 1]!;
  const [mult, prefix] = found;
  const scaled = value / mult;
  return `${scaled.toPrecision(sig)} ${prefix}${unit}`;
}

export function hz(value: number): string {
  return eng(value, 'Hz');
}
