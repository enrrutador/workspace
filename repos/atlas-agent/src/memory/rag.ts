/**
 * Atlas RAG - Codebase indexing for retrieval-augmented generation
 * Background indexing of source files into memory store
 */

import fs from 'fs';
import path from 'path';
import { memoryStore as getMemoryStore } from './memory_store.js';
import { atlasDB } from './atlas_db.js';
import { logger } from '../common/logger.js';

const INDEXABLE_EXTENSIONS = new Set(['.ts', '.js', '.json', '.md', '.txt']);
const MAX_FILES_PER_RUN = 50;
const MAX_FILE_SIZE = 30_000;
const BATCH_PAUSE_MS = 50;

// Los mtimes se persisten en la tabla kv: antes vivian solo en memoria y
// tras cada restart se re-insertaban los mismos archivos hasta agotarlos.
const MTIME_KEY_PREFIX = 'rag_mtime:';

export class RAGManager {
  private static instance: RAGManager;
  private srcDir: string;
  private indexedFiles: Map<string, number> = new Map();
  private isIndexing = false;

  private constructor() {
    this.srcDir = path.join(process.cwd(), 'src');
    this.loadIndexState();
  }

  private loadIndexState(): void {
    try {
      const rows = atlasDB.all('SELECT key, value FROM kv WHERE key LIKE ?', [`${MTIME_KEY_PREFIX}%`]);
      for (const row of rows) {
        this.indexedFiles.set(String(row.key).slice(MTIME_KEY_PREFIX.length), Number(row.value) || 0);
      }
      logger.debug('rag', `Loaded ${rows.length} indexed file records`);
    } catch {
      // DB no lista todavia: empieza vacio y se llena al indexar
    }
  }

  private persistState(filePath: string, mtime: number): void {
    try {
      atlasDB.run(
        'INSERT INTO kv (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value',
        [`${MTIME_KEY_PREFIX}${filePath}`, String(mtime)]
      );
    } catch {
      // Persistencia best-effort
    }
  }

  static getInstance(): RAGManager {
    if (!RAGManager.instance) {
      RAGManager.instance = new RAGManager();
    }
    return RAGManager.instance;
  }

  async indexCodebase(): Promise<void> {
    if (this.isIndexing) return;
    this.isIndexing = true;

    logger.info('rag', 'Starting background codebase indexing...');
    let indexed = 0;

    try {
      const store = getMemoryStore;
      const files = this.collectFiles(this.srcDir);

      for (let i = 0; i < files.length && indexed < MAX_FILES_PER_RUN; i++) {
        const { filePath, mtime } = files[i];
        if (this.indexedFiles.get(filePath) === mtime) continue;

        try {
          const content = fs.readFileSync(filePath, 'utf-8');
          if (!content || content.length > MAX_FILE_SIZE) continue;

          await store.store(
            `[FILE: ${path.basename(filePath)}]\n${content.slice(0, 2000)}`,
            'semantic',
            `codebase:${filePath.replace(process.cwd(), '')}`
          );

          this.indexedFiles.set(filePath, mtime);
          this.persistState(filePath, mtime);
          indexed++;

          if (indexed % 5 === 0) {
            await new Promise(r => setTimeout(r, BATCH_PAUSE_MS));
          }
        } catch {
          // Skip unreadable files
        }
      }

      logger.info('rag', `Indexed ${indexed} files`);
    } catch (err) {
      logger.error('rag', `Indexing error: ${err}`);
    } finally {
      this.isIndexing = false;
    }
  }

  private collectFiles(dir: string): Array<{ filePath: string; mtime: number }> {
    const results: Array<{ filePath: string; mtime: number }> = [];
    if (!fs.existsSync(dir)) return results;

    const walk = (d: string): void => {
      let entries;
      try {
        entries = fs.readdirSync(d, { withFileTypes: true });
      } catch {
        return;
      }

      for (const entry of entries) {
        if (entry.name.startsWith('.')) continue;
        if (['node_modules', 'data', 'dist', 'legacy'].includes(entry.name)) continue;

        const full = path.join(d, entry.name);
        if (entry.isDirectory()) {
          walk(full);
        } else if (entry.isFile()) {
          const ext = path.extname(entry.name).toLowerCase();
          if (!INDEXABLE_EXTENSIONS.has(ext)) continue;

          try {
            const { mtimeMs } = fs.statSync(full);
            results.push({ filePath: full, mtime: mtimeMs });
          } catch {
            // Skip unreadable
          }
        }
      }
    };

    walk(dir);
    return results;
  }
}

export const ragManager = RAGManager.getInstance();
