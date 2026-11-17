/**
 * Atlas Memory Tool - Recall and store information in Atlas memory
 */

import { logger } from '../../common/logger.js';
import { memoryStore } from '../../memory/memory_store.js';

export class MemoryTool {
  private static instance: MemoryTool;

  private constructor() {}

  static getInstance(): MemoryTool {
    if (!MemoryTool.instance) {
      MemoryTool.instance = new MemoryTool();
    }
    return MemoryTool.instance;
  }

  async store(args: { content: string; layer?: string; source?: string }): Promise<string> {
    try {
      const id = await memoryStore.store(args.content, (args.layer as any) || 'semantic', args.source || 'memory_tool');
      logger.info('memory', `Stored: "${args.content.slice(0, 60)}"`);
      return `Guardado en memoria (id: ${id}): "${args.content.slice(0, 100)}"`;
    } catch (err: any) {
      logger.error('memory', `Store failed: ${err.message}`);
      return `Error guardando en memoria: ${err.message}`;
    }
  }

  private static readonly RECALL_STOPWORDS = new Set([
    'sabes', 'sabe', 'listame', 'decime', 'dime', 'podes', 'tengo', 'tenes',
    'donde', 'cuales', 'cual', 'cuando', 'quien', 'quiero', 'sobre', 'todo',
    'algo', 'como', 'esta', 'estan', 'tengo', 'sos', 'vos', 'hola',
  ]);

  /**
   * Genera consultas candidatas a partir de la pregunta del usuario:
   * la frase completa, fragmentos después de ':' y tokens/bigramas relevants.
   * Antes se buscaba la frase COMPLETA con LIKE y una pregunta compuesta
   * ("listame lo que sabes de mi: comida favorita y donde trabajo")
   * no encontraba nada aunque el dato estuviera guardado.
   */
  private buildRecallQueries(query: string): string[] {
    const normalized = query.toLowerCase().trim();
    const candidates: string[] = [normalized];

    const colonParts = query.split(/[:,;]/).map(p => p.trim()).filter(p => p.length >= 4);
    candidates.push(...colonParts);

    const segments = query.split(/(?:\s(?:y|e|o|and|además|también)\s|,\s*|;\s*)/i).map(s => s.trim());
    for (const seg of segments) {
      const tokens = seg
        .split(/\s+/)
        .map(t => t.replace(/[^\wáéíóúñü]/gi, ''))
        .filter(t => t.length >= 4 && !MemoryTool.RECALL_STOPWORDS.has(t.toLowerCase()));
      if (tokens.length === 0) continue;
      candidates.push(tokens.join(' '));
      if (tokens.length >= 2) {
        for (let i = 0; i < tokens.length - 1; i++) {
          candidates.push(`${tokens[i]} ${tokens[i + 1]}`);
        }
      }
    }

    return [...new Set(candidates.map(c => c.trim()).filter(c => c.length >= 3))].slice(0, 10);
  }

  async recall(args: { query: string; limit?: number }): Promise<string> {
    const limit = args.limit || 5;
    const found: Array<{ content: string; layer: string }> = [];
    const seen = new Set<string>();

    try {
      for (const q of this.buildRecallQueries(args.query ?? '')) {
        const results = await memoryStore.search(q, limit * 2);
        for (const r of results) {
          if (!seen.has(r.content)) {
            seen.add(r.content);
            found.push({ content: r.content, layer: r.layer || 'semantic' });
          }
          if (found.length >= limit) break;
        }
        if (found.length >= limit) break;
      }

      if (found.length === 0) {
        return 'No encontré nada en memoria sobre eso.';
      }
      logger.info('memory', `Recalled: "${args.query.slice(0, 60)}" -> ${found.length} results`);
      return found.map((r, i) => `${i + 1}. [${r.layer}] ${r.content}`).join('\n');
    } catch (err: any) {
      logger.error('memory', `Recall failed: ${err.message}`);
      return `Error buscando en memoria: ${err.message}`;
    }
  }

  async delete(args: { id: string }): Promise<string> {
    try {
      await memoryStore.delete(args.id);
      logger.info('memory', `Deleted: "${args.id}"`);
      return `Eliminado de memoria: "${args.id}"`;
    } catch (err: any) {
      logger.error('memory', `Delete failed: ${err.message}`);
      return `Error eliminando de memoria: ${err.message}`;
    }
  }

  async getStats(): Promise<string> {
    try {
      const stats = await memoryStore.getStats();
      return `Memoria Atlas: ${stats.total} entradas`;
    } catch {
      return 'Estadísticas de memoria no disponibles.';
    }
  }
}

export const memoryTool = MemoryTool.getInstance();
