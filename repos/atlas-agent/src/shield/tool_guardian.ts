/**
 * Atlas Tool Guardian - Enforces the trust ladder on tool usage
 */

import { logger } from '../common/logger.js';
import { TrustCheck, classifyOperation, trustLadder } from './trust_ladder.js';

export const KNOWN_TOOLS = [
  'shell_execute',
  'web_search',
  'web_scrape',
  'web_download',
  'read_file',
  'save_file',
  'delete_file',
  'download_file',
  'list_files',
  'nvidia_vision',
  'nvidia_audio',
  'social_media',
  'code_analyze',
  'code_generate',
  'code_debug',
  'project_scaffold',
  'git_manager',
  'math_calculate',
  'translate',
  'memory_recall',
] as const;

export class ToolGuardian {
  private static instance: ToolGuardian;

  private constructor() {}

  static getInstance(): ToolGuardian {
    if (!ToolGuardian.instance) {
      ToolGuardian.instance = new ToolGuardian();
    }
    return ToolGuardian.instance;
  }

  canUseTool(toolName: string): TrustCheck {
    const check = trustLadder.canExecute(classifyOperation(toolName));
    if (!check.allowed) {
      logger.warn('tool_guardian', `Blocked "${toolName}": ${check.reason}`);
    }
    return check;
  }

  getAvailableTools(): string[] {
    return KNOWN_TOOLS.filter(tool => this.canUseTool(tool).allowed);
  }
}

export const toolGuardian = ToolGuardian.getInstance();
