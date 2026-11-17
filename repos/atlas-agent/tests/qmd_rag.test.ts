#!/usr/bin/env node
/**
 * Tests de los módulos de memoria fríos (sin red):
 * - qmd_memory: storeFact persiste el primer hecho crítico/preferencia en
 *   MEMORY.md (antes se perdía silenciosamente), logEntry + searchRecent.
 * - rag: indexCodebase persiste mtimes en kv (antes vivían solo en RAM y
 *   cada arranque re-indexaba TODO).
 */
import { describe, it, before } from 'node:test';
import assert from 'node:assert';
import { readFileSync, existsSync } from 'node:fs';
import * as path from 'node:path';
import { atlasDB } from '../src/memory/atlas_db.js';
import { qmdMemory } from '../src/memory/qmd_memory.js';
import { ragManager } from '../src/memory/rag.js';

/** Paths propios de qmd_memory (workspace/ es sandbox y está gitignored). */
const MEMORY_MD = () => path.join(process.cwd(), 'workspace', 'MEMORY.md');

const UNIQUE = `hecho-test-${Date.now()}`;

describe('qmd_memory', () => {
  before(async () => {
    await atlasDB.initialize();
  });

  it('storeFact user_preference crea MEMORY.md con el primer hecho', async () => {
    qmdMemory.storeFact(`COMIDA FAVORITA: ${UNIQUE}`, 'user_preference');
    // aunque had existed or not, MEMORY.md must exist now and contain the fact
    assert.ok(existsSync(MEMORY_MD()), 'MEMORY.md existe tras el primer hecho');
    const content = readFileSync(MEMORY_MD(), 'utf-8');
    assert.ok(content.includes(UNIQUE), 'el primer hecho consecuente a user_preference queda persistido');
  });

  it('storeFact semantic no toca MEMORY.md pero queda en el log diario', async () => {
    const before = existsSync(MEMORY_MD()) ? readFileSync(MEMORY_MD(), 'utf-8') : '';
    // El log diario es append-only y puede estar crecido por sesiones live:
    // backup/reset para que el hecho quede dentro del slice que devuelve
    // searchRecent (limita 1500 chars por día).
    const dailyFile = path.join(process.cwd(), 'workspace', 'memory', `${new Date().toISOString().split('T')[0]}.md`);
    const originalLog = existsSync(dailyFile) ? readFileSync(dailyFile, 'utf-8') : null;
    if (originalLog !== null) {
      (await import('node:fs')).writeFileSync(dailyFile, `# Memory Log - ${new Date().toISOString().split('T')[0]}\n`);
    }

    qmdMemory.storeFact(`HISTORIAL ${UNIQUE}`, 'semantic');
    const after = existsSync(MEMORY_MD()) ? readFileSync(MEMORY_MD(), 'utf-8') : '';
    assert.equal(after, before, 'MEMORY.md no cambia para layer semantic');

    const recent = qmdMemory.searchRecent(`HISTORIAL ${UNIQUE}`, 7);
    assert.ok(recent.includes(`HISTORIAL ${UNIQUE}`), 'searchRecent lo encuentra en el log diario');

    // restaurar el log original + entrada propia para no perder historial
    const restored = (originalLog ?? '') + (existsSync(dailyFile) ? readFileSync(dailyFile, 'utf-8').split('\n').slice(1).join('\n') : '');
    (await import('node:fs')).writeFileSync(dailyFile, restored);
  });
});

describe('rag', () => {
  it('indexCodebase persiste mtimes en la tabla kv', async () => {
    await atlasDB.initialize();
    await ragManager.indexCodebase();

    const rows = atlasDB.all('SELECT key, value FROM kv WHERE key LIKE ?', ['rag_mtime:%']);
    assert.ok(rows.length > 0, 'persistió mtimes de archivos indexados');

    // Segunda corrida: sin cambios, el mismo set sin duplicar keys
    await ragManager.indexCodebase();
    const rows2 = atlasDB.all('SELECT key, value FROM kv WHERE key LIKE ?', ['rag_mtime:%']);
    assert.equal(rows2.length, rows.length, 'no duplica registros de mtime en la segunda indexación');
  });
});
