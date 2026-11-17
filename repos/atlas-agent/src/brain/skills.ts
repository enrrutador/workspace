/**
 * Atlas Brain Skills - Skill registration and execution
 */

import { logger } from '../common/logger.js';
import { Skill } from '../common/types.js';

export class BrainSkills {
  private stats: Record<string, { ok: number; fail: number }> = {};
  private statsListener?: (stats: Record<string, { ok: number; fail: number }>) => void;

  private static instance: BrainSkills;
  private registry: Map<string, Skill> = new Map();

  private constructor() {}

  static getInstance(): BrainSkills {
    if (!BrainSkills.instance) {
      BrainSkills.instance = new BrainSkills();
    }
    return BrainSkills.instance;
  }

  register(skill: Skill): void {
    this.registry.set(skill.name, skill);
    logger.info('brain_skills', `Registered: ${skill.name}`);
  }

  unregister(name: string): void {
    this.registry.delete(name);
    logger.info('brain_skills', `Unregistered: ${name}`);
  }

  canHandle(_name: string): boolean {
    return true;
  }

  async execute(name: string, args: Record<string, any>): Promise<any> {
    const skill = this.registry.get(name);
    if (!skill) {
      throw new Error(`Skill not found: ${name}`);
    }

    logger.info('brain_skills', `Executing: ${name}`);
    try {
      const result = await skill.handler(args);
      logger.info('brain_skills', `Completed: ${name}`);
      this.stats[name] = this.stats[name] || { ok: 0, fail: 0 };
      this.stats[name].ok++;
      this.statsListener?.(this.stats);
      return result;
    } catch (err) {
      logger.error('brain_skills', `Failed: ${name} — ${err}`);
      this.stats[name] = this.stats[name] || { ok: 0, fail: 0 };
      this.stats[name].fail++;
      this.statsListener?.(this.stats);
      throw err;
    }
  }

  /** Métrica de éxito/fallo por skill (para /skills y diagnósticos). */
  getToolStats(): Record<string, { ok: number; fail: number }> {
    return this.stats;
  }

  /** Restaura stats persistidas (SQLite) al arrancar. */
  loadToolStats(persisted: Record<string, { ok: number; fail: number }>): void {
    for (const [k, v] of Object.entries(persisted)) {
      if (v && typeof v.ok === 'number' && typeof v.fail === 'number') {
        this.stats[k] = { ok: v.ok, fail: v.fail };
      }
    }
  }

  /** Callback por si main.ts quiere persistir cambios (SQLite). */
  setStatsListener(fn: (stats: Record<string, { ok: number; fail: number }>) => void): void {
    this.statsListener = fn;
  }

  list(): Array<{ name: string; description: string }> {
    return Array.from(this.registry.values()).map(s => ({
      name: s.name,
      description: s.description,
    }));
  }

  listRaw(): Skill[] {
    return Array.from(this.registry.values());
  }

  has(name: string): boolean {
    return this.registry.has(name);
  }
}

export const brainSkills = BrainSkills.getInstance();
