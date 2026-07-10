#!/usr/bin/env node
/**
 * Free the given TCP ports before starting the dev stack, so a leftover
 * process from a previous (crashed or force-quit) run can't block the
 * frontend/backend from binding — the classic "npm run dev fails with the
 * port already in use / ECONNREFUSED" trap in a long-lived dev container.
 *
 * Usage: node scripts/free-ports.mjs 5173 8420
 */
import { execSync } from 'node:child_process';

const ports = process.argv.slice(2);

function pidsOnPort(port) {
  // Try lsof, then fuser, then ss — whichever exists.
  for (const cmd of [
    `lsof -ti tcp:${port}`,
    `fuser ${port}/tcp 2>/dev/null`,
    `ss -tlnpH "sport = :${port}" 2>/dev/null | grep -oP 'pid=\\K[0-9]+'`,
  ]) {
    try {
      const out = execSync(cmd, { stdio: ['ignore', 'pipe', 'ignore'] })
        .toString()
        .trim();
      if (out) return [...new Set(out.split(/\s+/).filter(Boolean))];
    } catch {
      // command not found or no match; try the next
    }
  }
  return [];
}

for (const port of ports) {
  const pids = pidsOnPort(port);
  if (pids.length === 0) continue;
  try {
    execSync(`kill -9 ${pids.join(' ')}`, { stdio: 'ignore' });
    console.log(`[free-ports] freed :${port} (killed ${pids.join(', ')})`);
  } catch {
    console.warn(`[free-ports] could not kill process(es) on :${port}: ${pids.join(', ')}`);
  }
}
