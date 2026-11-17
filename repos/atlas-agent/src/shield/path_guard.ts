/**
 * Atlas Path Guard - Restricts file operations to configured roots and
 * refuses access to credential/secret files.
 */

import fs from 'fs';
import os from 'os';
import path from 'path';

export type PathMode = 'read' | 'write' | 'delete' | 'list';

export interface PathCheck {
  allowed: boolean;
  reason?: string;
  resolvedPath?: string;
}

const SENSITIVE_DIRS = new Set([
  '.ssh',
  '.aws',
  '.gnupg',
  '.kube',
  '.docker',
  '.config',
  '.git',
]);

const SENSITIVE_BASENAMES = new Set([
  '.env',
  '.netrc',
  '.npmrc',
  '.pypirc',
  '.git-credentials',
  'credentials',
  'credentials.json',
  'secrets.json',
  'tokens.json',
  'id_rsa',
  'id_dsa',
  'id_ecdsa',
  'id_ed25519',
]);

const SENSITIVE_EXTENSIONS = new Set(['.pem', '.key', '.p12', '.pfx']);

function normalizeRoot(root: string): string {
  const resolved = path.resolve(root);
  try {
    return fs.realpathSync(resolved);
  } catch {
    return resolved;
  }
}

export function allowedRoots(): string[] {
  const raw = process.env.ATLAS_ALLOWED_ROOTS;
  if (raw) {
    const roots = raw
      .split(path.delimiter)
      .flatMap(part => part.split(','))
      .map(part => part.trim())
      .filter(Boolean);
    if (roots.length > 0) return roots.map(normalizeRoot);
  }
  return [normalizeRoot(process.cwd()), normalizeRoot(os.tmpdir())];
}

function resolveWithExistingParent(target: string): string {
  if (fs.existsSync(target)) {
    try {
      return fs.realpathSync(target);
    } catch {
      return target;
    }
  }

  const missing: string[] = [];
  let current = target;
  while (!fs.existsSync(current)) {
    missing.unshift(path.basename(current));
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }

  try {
    return path.join(fs.realpathSync(current), ...missing);
  } catch {
    return target;
  }
}

function isInside(root: string, target: string): boolean {
  const relative = path.relative(root, target);
  return relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative));
}

function isSensitive(target: string): boolean {
  const normalized = target.split(path.sep).join('/');
  const segments = normalized.split('/');
  const basename = path.basename(target).toLowerCase();
  const extension = path.extname(basename).toLowerCase();

  if (SENSITIVE_BASENAMES.has(basename)) return true;
  if (basename.startsWith('.env.')) return true;
  if (basename.startsWith('id_') && !basename.endsWith('.pub')) return true;
  if (SENSITIVE_EXTENSIONS.has(extension)) return true;
  if (segments.some(segment => SENSITIVE_DIRS.has(segment.toLowerCase()))) return true;

  return false;
}

export function checkPath(inputPath: string, _mode: PathMode = 'read'): PathCheck {
  if (!inputPath || typeof inputPath !== 'string') {
    return { allowed: false, reason: 'A non-empty path is required' };
  }

  if (inputPath.includes('\0')) {
    return { allowed: false, reason: 'Invalid path' };
  }

  const resolved = resolveWithExistingParent(path.resolve(inputPath));

  if (isSensitive(resolved)) {
    return {
      allowed: false,
      reason: `Access to sensitive file or directory is blocked: ${inputPath}`,
      resolvedPath: resolved,
    };
  }

  const roots = allowedRoots();
  if (!roots.some(root => isInside(root, resolved))) {
    return {
      allowed: false,
      reason: `Path is outside the allowed roots (${roots.join(', ')}): ${inputPath}`,
      resolvedPath: resolved,
    };
  }

  return { allowed: true, resolvedPath: resolved };
}

export function assertAllowedPath(inputPath: string, mode: PathMode = 'read'): string {
  const result = checkPath(inputPath, mode);
  if (!result.allowed || !result.resolvedPath) {
    throw new Error(result.reason || `Path not allowed: ${inputPath}`);
  }
  return result.resolvedPath;
}
