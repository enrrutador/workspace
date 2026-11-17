/**
 * Atlas Terminal Tool v2 — Production-grade shell command execution
 * 
 * Patterns from: LangChain ShellTool, Codex CLI, Claude Code, OpenAI Agents SDK
 * - spawn with process group for reliable kill (SIGTERM → grace → SIGKILL)
 * - Separate stdout/stderr streaming
 * - Structured result type
 * - Encoding-aware, output-capped
 * - Cross-platform (Unix process groups, Windows direct kill)
 */

import { spawn, SpawnOptions } from 'child_process';
import { platform } from 'os';
import { logger } from '../../common/logger.js';
import { toolGuardian } from '../../shield/tool_guardian.js';

const IS_WIN = platform() === 'win32';
const SHELL = IS_WIN ? process.env.COMSPEC || 'cmd.exe' : '/bin/bash';
const SHELL_ARG = IS_WIN ? '/C' : '-c';

const DEFAULT_TIMEOUT_MS = 30_000;
const GRACE_PERIOD_MS = 2_000;
const MAX_OUTPUT_BYTES = 1_048_576; // 1MB per stream

const ALLOW_DANGEROUS = process.env.ATLAS_ALLOW_DANGEROUS === 'true';

interface BlockRule {
  pattern: RegExp;
  reason: string;
}

const SENSITIVE_COMMAND: BlockRule = {
  pattern: /^(sudo|su|doas|passwd|chpasswd)\b/i,
  reason: 'privilege escalation and password changes are disabled',
};

const SYSTEM_COMMAND: BlockRule = {
  pattern: /^(dd|mkfs(\.\w+)?|fdisk|parted|mount|umount|mkswap|swapon|swapoff|iptables|ufw|systemctl|service|shutdown|reboot|halt|poweroff|init)\b/i,
  reason: 'system-level command is disabled',
};

const BLOCKED_RULES: BlockRule[] = [
  SENSITIVE_COMMAND,
  SYSTEM_COMMAND,
  { pattern: /^chown\b/i, reason: 'ownership changes are disabled' },
  { pattern: /^chmod\s+(-R\s+)?[0-7]*777(\s|$)/i, reason: 'world-writable permissions are disabled' },
  { pattern: /^rm\b.*(\s\/(\*|\s|$)|\s--no-preserve-root\b)/i, reason: 'refusing to delete the filesystem root' },
  { pattern: /^rm\b.*\s(~|\$HOME)(\/|\s|$)/i, reason: 'refusing to delete the home directory' },
  { pattern: /^rm\b.*\s\.\.(\/|\s|$)/i, reason: 'refusing to delete parent directories' },
  { pattern: /^rm\b.*\s\/(etc|usr|bin|sbin|lib|lib64|boot|dev|proc|sys|var|opt|home|root)(\/|\s|$)/i, reason: 'refusing to delete a system directory' },
  { pattern: /^kill\s+(-9\s+)?1(\s|$)/i, reason: 'refusing to kill init/PID 1' },
  { pattern: /^git\s+push\b.*(\s--force\b|\s-f\b)/i, reason: 'force-push is disabled; push a new commit instead' },
  { pattern: /:\s*\(\s*\)\s*\{/, reason: 'fork bombs are disabled' },
  { pattern: /\bof=\/dev\//i, reason: 'writing directly to block devices is disabled' },
  { pattern: /(curl|wget)\b[^|;]*\|\s*(sh|bash|zsh|dash|ksh|python3?|node)\b/i, reason: 'piping downloaded content into an interpreter is disabled' },
  { pattern: /(sh|bash|zsh)\s+<\(\s*(curl|wget)\b/i, reason: 'executing downloaded content from process substitution is disabled' },
  { pattern: />\s*\/(etc|boot|dev|proc|sys)\//i, reason: 'redirection into system directories is disabled' },
  { pattern: /^eval\b/i, reason: 'eval is disabled; run the command directly' },
  { pattern: /^history\s+-c\b/i, reason: 'clearing shell history is disabled' },
  { pattern: /^(?:xterm|gnome-terminal|konsole|tilix|wt|cmd)\b.*\b(?:sudo|su|doas)\b/i, reason: 'privilege escalation is disabled (terminal emulator wrapper)' },
  { pattern: /^chattr\b/i, reason: 'filesystem attribute changes are disabled' },
];

const SHELL_WRAPPERS = /^(?:bash|sh|zsh|dash|ksh)\s+-[a-z]*c\s+(.+)$/is;
const BUILTIN_PREFIX = /^(?:(?:command|builtin|exec|nohup|time|env)\s+)+/i;

function stripEnvAssignments(segment: string): string {
  let result = segment.trim();

  for (let i = 0; i < 5; i++) {
    const next = result
      .replace(/^(?:[A-Za-z_][A-Za-z0-9_]*=(?:"[^"]*"|'[^']*'|\S*)\s+)+/, '')
      .replace(BUILTIN_PREFIX, '')
      .replace(/^[({!]+\s*/, '')
      .trim();
    if (next === result) break;
    result = next;
  }

  return result;
}

/**
 * Splits a shell command into independent segments so a dangerous command
 * cannot hide after `;`, `&&`, `||`, `&`, a pipe or a newline.
 */
export function splitCommand(command: string): string[] {
  return command
    .split(/\n|;|&&|\|\||\||&/)
    .map(stripEnvAssignments)
    .filter(Boolean);
}

function extractSubstitutions(segment: string): string[] {
  const found: string[] = [];
  const patterns = [/\$\(([^()]*)\)/g, /`([^`]*)`/g];
  for (const pattern of patterns) {
    for (const match of segment.matchAll(pattern)) {
      const inner = match[1]?.trim();
      if (inner) found.push(inner);
    }
  }
  return found;
}

/**
 * Returns the reason a command is blocked, or null when it is allowed.
 */
export function findBlockedReason(command: string, depth = 0): string | null {
  if (ALLOW_DANGEROUS || depth > 3) return null;

  for (const rule of BLOCKED_RULES) {
    if (!rule.pattern.source.startsWith('^') && rule.pattern.test(command)) {
      return rule.reason;
    }
  }

  for (const segment of splitCommand(command)) {
    for (const rule of BLOCKED_RULES) {
      if (rule.pattern.test(segment)) {
        return rule.reason;
      }
    }

    const wrapped = segment.match(SHELL_WRAPPERS);
    if (wrapped) {
      const inner = wrapped[1].trim().replace(/^(['"])(.*)\1$/s, '$2');
      const reason = findBlockedReason(inner, depth + 1);
      if (reason) return reason;
    }

    for (const substitution of extractSubstitutions(segment)) {
      const reason = findBlockedReason(substitution, depth + 1);
      if (reason) return reason;
    }
  }

  return null;
}

export interface ExecResult {
  stdout: string;
  stderr: string;
  exitCode: number;
  timedOut: boolean;
  truncated: boolean;
  command: string;
}

export class TerminalTool {
  private static instance: TerminalTool;

  private constructor() {}

  static getInstance(): TerminalTool {
    if (!TerminalTool.instance) {
      TerminalTool.instance = new TerminalTool();
    }
    return TerminalTool.instance;
  }

  async execute(
    command: string,
    options?: {
      timeout?: number;
      cwd?: string;
      env?: Record<string, string>;
      maxOutput?: number;
    }
  ): Promise<ExecResult> {
    const guard = toolGuardian.canUseTool('shell_execute');
    if (!guard.allowed) {
      logger.warn('terminal', `Blocked by trust ladder: ${guard.reason}`);
      return {
        stdout: '',
        stderr: guard.reason || 'Comando bloqueado por el nivel de confianza.',
        exitCode: 1,
        timedOut: false,
        truncated: false,
        command,
      };
    }

    const blockedReason = findBlockedReason(command);
    if (blockedReason) {
      logger.warn('terminal', `Blocked command (${blockedReason}): ${command.slice(0, 100)}`);
      return {
        stdout: '',
        stderr: `Comando bloqueado por seguridad: ${blockedReason}.`,
        exitCode: 1,
        timedOut: false,
        truncated: false,
        command,
      };
    }

    const timeout = options?.timeout ?? DEFAULT_TIMEOUT_MS;
    const maxOutput = options?.maxOutput ?? MAX_OUTPUT_BYTES;

    const spawnOpts: SpawnOptions = {
      cwd: options?.cwd,
      env: options?.env ? { ...process.env, ...options.env } : process.env,
      stdio: ['pipe', 'pipe', 'pipe'],
      // Unix: grupo de procesos propio para poder matar el árbol completo.
      // Antes detached:false → kill(-pid) fallaba con ESRCH y al timeout solo
      // moría el shell, quedando los nietos huérfanos.
      detached: !IS_WIN,
    };

    logger.info('terminal', `Exec: ${command.slice(0, 120)}`);

    const child = spawn(SHELL, [SHELL_ARG, command], spawnOpts);

    const stdoutChunks: Buffer[] = [];
    const stderrChunks: Buffer[] = [];
    let stdoutLen = 0;
    let stderrLen = 0;
    let truncated = false;

    const stdoutReader = (chunk: Buffer) => {
      const remaining = maxOutput - stdoutLen;
      if (remaining <= 0) {
        truncated = true;
        return;
      }
      const slice = chunk.subarray(0, remaining);
      stdoutChunks.push(slice);
      stdoutLen += slice.length;
    };

    const stderrReader = (chunk: Buffer) => {
      const remaining = maxOutput - stderrLen;
      if (remaining <= 0) {
        truncated = true;
        return;
      }
      const slice = chunk.subarray(0, remaining);
      stderrChunks.push(slice);
      stderrLen += slice.length;
    };

    if (child.stdout) child.stdout.on('data', stdoutReader);
    if (child.stderr) child.stderr.on('data', stderrReader);

    const killProcessTree = (signal: NodeJS.Signals) => {
      if (child.pid === undefined) return;
      try {
        if (!IS_WIN) {
          process.kill(-child.pid, signal);
        } else {
          child.kill(signal);
        }
      } catch {
        try {
          child.kill(signal);
        } catch {
          // Ya murió
        }
      }
    };

    const timeoutHandle = setTimeout(() => {
      killProcessTree('SIGTERM');
      // Grace period then force kill
      setTimeout(() => {
        killProcessTree('SIGKILL');
      }, GRACE_PERIOD_MS);
    }, timeout);

    return new Promise<ExecResult>((resolve) => {
      let settled = false;
      const settle = (timedOut: boolean) => {
        if (settled) return;
        settled = true;
        clearTimeout(timeoutHandle);

        const decode = (chunks: Buffer[]): string =>
          Buffer.concat(chunks).toString('utf-8').trimEnd();

        let stderr = decode(stderrChunks);
        if (timedOut) {
          const msg = `[Timeout] El comando no respondio en ${timeout}ms`;
          stderr = stderr ? stderr + '\n' + msg : msg;
        }

        const result: ExecResult = {
          stdout: decode(stdoutChunks),
          stderr,
          exitCode: timedOut ? -1 : (child.exitCode ?? 1),
          timedOut,
          truncated,
          command,
        };

        logger.info('terminal', `Done (exit: ${result.exitCode}, out: ${result.stdout.length}, err: ${result.stderr.length}, timeout: ${result.timedOut})`);
        resolve(result);
      };

      child.on('error', (err) => {
        logger.error('terminal', `Spawn error: ${err.message}`);
        settle(false);
      });

      child.on('exit', (_code, signal) => {
        const timedOut = signal === 'SIGTERM' || signal === 'SIGKILL';
        // On timeout the exit already triggered — just collect rest and settle
        if (timedOut) {
          settle(true);
        } else {
          // Small delay to drain remaining output buffers
          setTimeout(() => settle(false), 50);
        }
      });
    });
  }
}

export const terminalTool = TerminalTool.getInstance();
