/**
 * Shared path helpers. DATA_DIR / ATLAS_DATA_DIR lets deployments move the
 * runtime state (DB, logs, missions, downloads) without touching the cwd.
 */

import path from 'path';

export function dataDir(...parts: string[]): string {
  const base = process.env.ATLAS_DATA_DIR || process.env.DATA_DIR || 'data';
  return path.resolve(process.cwd(), base, ...parts);
}
