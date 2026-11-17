/**
 * Atlas Trust Ladder - Autonomy levels and per-operation risk policy
 *
 * Levels:
 *   1 Cautious    - asks before everything
 *   2 Safe        - low/medium risk automatically, high risk requires approval
 *   3 Trusted     - low/medium/high risk automatically (default)
 *   4 Autonomous  - everything, including critical operations
 *   5 Night Shift - full autonomy (same enforcement as 4; semantic marker)
 */

import { Operation } from '../common/types.js';
import { logger } from '../common/logger.js';

export type TrustLevel = 1 | 2 | 3 | 4 | 5;

export const TRUST_LEVEL_NAMES: Record<TrustLevel, string> = {
  1: 'Cautious',
  2: 'Safe',
  3: 'Trusted',
  4: 'Autonomous',
  5: 'Night Shift',
};

const MIN_LEVEL_FOR_RISK: Record<Operation['risk'], TrustLevel> = {
  low: 1,
  medium: 2,
  high: 3,
  critical: 4,
};

const DEFAULT_LEVEL: TrustLevel = 3;

const RISK_BY_TOOL: Record<string, Operation['risk']> = {
  read_file: 'low',
  list_files: 'low',
  web_search: 'low',
  web_scrape: 'low',
  math_calculate: 'low',
  translate: 'low',
  memory_recall: 'low',
  nvidia_vision: 'low',
  nvidia_audio: 'low',
  code_analyze: 'low',
  code_generate: 'low',
  code_debug: 'low',
  save_file: 'medium',
  web_download: 'medium',
  download_file: 'medium',
  project_scaffold: 'medium',
  shell_execute: 'high',
  git_manager: 'high',
  delete_file: 'high',
  social_media: 'high',
};

const HIGH_RISK_KEYWORDS = /\b(delete|remove|erase|reset|drop|truncate|push|publish|deploy|install|uninstall|chmod|chown|kill|shutdown|reboot|format|wipe|transfer|payment|purchase)\b/i;
const MEDIUM_RISK_KEYWORDS = /\b(write|create|save|download|upload|move|rename|schedule|send|post|commit|merge|branch)\b/i;
const CRITICAL_KEYWORDS = /\b(rm\s+-rf|mkfs|dd\s+of=|drop\s+database|delete\s+(repo|repository|account)|production|private\s+key|seed\s+phrase|wipe\s+disk)\b/i;
const IRREVERSIBLE_KEYWORDS = /\b(delete|remove|erase|drop|truncate|reset|format|wipe|kill|shutdown|reboot|publish|deploy|transfer|payment|purchase)\b/i;

function clampLevel(value: number): TrustLevel {
  if (!Number.isFinite(value)) return DEFAULT_LEVEL;
  return Math.min(5, Math.max(1, Math.round(value))) as TrustLevel;
}

function levelFromEnv(): TrustLevel {
  const raw = process.env.ATLAS_TRUST_LEVEL;
  if (!raw) return DEFAULT_LEVEL;
  return clampLevel(parseInt(raw, 10));
}

/**
 * Classify a tool name or free-form task description into a risk operation.
 */
export function classifyOperation(type: string, description: string = ''): Operation {
  const text = `${type} ${description}`.trim();
  const toolRisk = RISK_BY_TOOL[type];

  let risk: Operation['risk'] = toolRisk ?? 'low';
  if (CRITICAL_KEYWORDS.test(text)) risk = 'critical';
  else if (!toolRisk && HIGH_RISK_KEYWORDS.test(text)) risk = 'high';
  else if (!toolRisk && MEDIUM_RISK_KEYWORDS.test(text)) risk = 'medium';

  return {
    type,
    risk,
    reversible: !IRREVERSIBLE_KEYWORDS.test(text),
    description: description || type,
  };
}

export interface TrustCheck {
  allowed: boolean;
  needsConfirmation: boolean;
  reason?: string;
}

export class TrustLadder {
  private static instance: TrustLadder;
  private level: TrustLevel;

  private constructor() {
    this.level = levelFromEnv();
  }

  static getInstance(): TrustLadder {
    if (!TrustLadder.instance) {
      TrustLadder.instance = new TrustLadder();
    }
    return TrustLadder.instance;
  }

  getLevel(): TrustLevel {
    return this.level;
  }

  setLevel(level: number): TrustLevel {
    const next = clampLevel(level);
    if (next !== this.level) {
      logger.info('trust_ladder', `Trust level changed: ${this.level} → ${next} (${TRUST_LEVEL_NAMES[next]})`);
      this.level = next;
    }
    return this.level;
  }

  getLevelName(): string {
    return TRUST_LEVEL_NAMES[this.level];
  }

  canExecute(operation: Operation): TrustCheck {
    const effectiveRequired = MIN_LEVEL_FOR_RISK[operation.risk];

    if (this.level < effectiveRequired) {
      return {
        allowed: false,
        needsConfirmation: true,
        reason: `"${operation.type}" is ${operation.risk} risk${operation.reversible ? '' : ' and irreversible'} — requires trust level ${effectiveRequired} (${TRUST_LEVEL_NAMES[effectiveRequired as TrustLevel]}), current level is ${this.level} (${TRUST_LEVEL_NAMES[this.level]})`,
      };
    }

    return {
      allowed: true,
      needsConfirmation: this.level === 1 && operation.risk !== 'low',
      reason: `Allowed at trust level ${this.level} (${TRUST_LEVEL_NAMES[this.level]})`,
    };
  }

  requiresConfirmation(operationType: string): boolean {
    return this.canExecute(classifyOperation(operationType)).needsConfirmation;
  }

  getBehaviorPrompt(): string {
    const names = Object.entries(TRUST_LEVEL_NAMES)
      .map(([lvl, name]) => `- Level ${lvl}: ${name}`)
      .join('\n');

    return `## Trust Level: ${this.level} (${this.getLevelName()})
${names}
- Operations above the current level are proposed to the user instead of executed.
`;
  }
}

export const trustLadder = TrustLadder.getInstance();
