#!/usr/bin/env node
/**
 * Tests de integración del pipeline crítico con LLM MOCKEADO (sin red):
 * - confidenceRouter.runToolLoop: recuperación tras tool fallida,
 *   salida determinística cuando TODAS las tools fallan y nudge ante
 *   "intención sin toolcall".
 * - Clasificador offline (reglas regex) para las categorías críticas.
 * - Memoria: recall multi-fragmento sobre consultas compuestas.
 */
import { describe, it, after, before } from 'node:test';
import assert from 'node:assert';
import { rmSync } from 'node:fs';
import { confidenceRouter } from '../src/brain/confidence_router.js';
import { brainSkills } from '../src/brain/skills.js';
import { queryClassifier } from '../src/brain/query_classifier.js';
import { memoryTool } from '../src/arms/tools/memory_tool.js';
import { fileManagerTool } from '../src/arms/tools/file_manager.js';
import { atlasDB } from '../src/memory/atlas_db.js';

const TMP_FILE = 'workspace/.tmp_pipeline.txt';

// El pipeline vive detrás de skills + DB: igual que hace main.ts, se
// registran los skills mínimos para los tests (sin red).
before(async () => {
  await atlasDB.initialize();
  if (!brainSkills.has('save_file')) {
    brainSkills.register({
      name: 'save_file',
      description: 'Guarda contenido a un archivo',
      parameters: [
        { name: 'path', type: 'string', description: 'Ruta', required: true },
        { name: 'content', type: 'string', description: 'Contenido', required: true },
      ],
      handler: async (args: any) => fileManagerTool.writeFile(args.path, args.content),
    });
  }
  if (!brainSkills.has('delete_file')) {
    brainSkills.register({
      name: 'delete_file',
      description: 'Borra un archivo',
      parameters: [{ name: 'path', type: 'string', description: 'Ruta', required: true }],
      handler: async (args: any) => fileManagerTool.deleteFile(args.path),
    });
  }
});

describe('runToolLoop (LLM mock)', () => {
  after(() => {
    rmSync(TMP_FILE, { force: true });
  });

  it('se recupera: tool fallida → reintento exitoso → archivo real con contenido', async () => {
    let chatUses = 0;
    const llm = {
      chatCompletionWithTools: async (msgs: any[]) => {
        if (msgs.some(m => m.role === 'tool' && String(m.content || '').includes('ENOENT'))) {
          return {
            content: 'reintentando',
            toolCalls: [{
              id: 'c2',
              function: { name: 'save_file', arguments: JSON.stringify({ path: TMP_FILE, content: 'atlas suave 2' }) },
            }],
          };
        }
        return {
          content: 'lo borro',
          toolCalls: [{ id: 'c1', function: { name: 'delete_file', arguments: JSON.stringify({ path: 'workspace/nunca_existio_9x.txt' }) } }],
        };
      },
      chatCompletion: async () => { chatUses++; return 'Archivo guardado correctamente.'; },
    };
    confidenceRouter.setLLMClient(llm);

    const r = await confidenceRouter.runToolLoop(
      [{ role: 'user', content: 'borra el archivo y despues crealo' }],
      'borra workspace/nunca_existio_9x.txt y crea ' + TMP_FILE,
    );

    assert.equal(r.content, 'Archivo guardado correctamente.');
    assert.ok(r.confidence >= 0.5, 'confianza >= 0.5 tras éxito');
    assert.deepEqual(r.metadata?.toolsUsed, ['save_file']);
    assert.equal(chatUses, 1, 'una sola llamada de síntesis');
    const saved = (await import('node:fs')).readFileSync(TMP_FILE, 'utf-8');
    assert.equal(saved, 'atlas suave 2', 'el archivo EXISTE en disco con el contenido pedido');
  });

  it('todas las tools fallan → salida determinística, jamás éxito falso del LLM', async () => {
    let synthesisUsed = false;
    const llm = {
      chatCompletionWithTools: async () => ({
        content: '',
        toolCalls: [{ id: 'd1', function: { name: 'delete_file', arguments: JSON.stringify({ path: 'workspace/sigue_inexistente_9x.txt' }) } }],
      }),
      chatCompletion: async () => { synthesisUsed = true; return 'LISTO, LO HICE.'; },
    };
    confidenceRouter.setLLMClient(llm);

    const r = await confidenceRouter.runToolLoop(
      [{ role: 'user', content: 'borra' }],
      'borra workspace/sigue_inexistente_9x.txt',
    );

    assert.ok(r.content.includes('No pude completar la operación'), 'mensaje determinístico');
    assert.ok(r.content.includes('ENOENT') || r.content.toLowerCase().includes('error'), 'lista el error real');
    assert.ok(!r.content.includes('LISTO'), 'no acepta la síntesis que afirma éxito falso');
    assert.ok(r.confidence < 0.5);
    assert.equal(synthesisUsed, false, 'no se llama al LLM para sintetizar en fallo total');
  });

  it('nudge: respuesta sin toolcall ("intención") no se acepta; el hop siguiente ejecuta', async () => {
    let nudges = 0;
    const llm = {
      chatCompletionWithTools: async (msgs: any[]) => {
        if (msgs.some(m => String(m.content || '').includes('intención, no un resultado'))) {
          nudges++;
          return {
            content: 'ahora sí',
            toolCalls: [{ id: 'n2', function: { name: 'save_file', arguments: JSON.stringify({ path: TMP_FILE, content: 'atlas tras nudgeo' }) } }],
          };
        }
        return { content: 'Voy a borrarlo ahora mismo.', toolCalls: [] };
      },
      chatCompletion: async () => 'Listo, creé el archivo.',
    };
    confidenceRouter.setLLMClient(llm);

    const r = await confidenceRouter.runToolLoop([{ role: 'user', content: 'crea el archivo' }], 'crea ' + TMP_FILE);

    assert.equal(nudges, 1, 'se pidió el toolcall una vez');
    assert.equal(r.content, 'Listo, creé el archivo.');
    const saved = (await import('node:fs')).readFileSync(TMP_FILE, 'utf-8');
    assert.equal(saved, 'atlas tras nudgeo');
  });
});

describe('clasificador offline (reglas regex)', () => {
  it('mapea estados críticos sin necesitar red', async () => {
    const tool = await queryClassifier.classify('traduci hello al frances');
    assert.equal(tool.category, 'tool');

    const tool2 = await queryClassifier.classify('borra el archivo workspace/prueba1.txt');
    assert.equal(tool2.category, 'tool');

    const mem = await queryClassifier.classify('listame lo que sabes de mi: comida favorita y donde trabajo');
    assert.equal(mem.category, 'memory');

    // Calibración nueva: cálculos van a tool (math_calculate determinístico,
    // la ruta general LLM tarda 30-60s con modelos reasoning y a veces vuelve
    // vacía).
    const gen = await queryClassifier.classify('cuanto es 15% de 2350');
    assert.equal(gen.category, 'tool');

    const general = await queryClassifier.classify('quién ganó el mundial de 2022');
    assert.equal(general.category, 'general');
  });
});

describe('memoria multi-fragmento', () => {
  it('recall compuesto devuelve todos los fragmentos guardados', async () => {
    await memoryTool.store({ content: 'mi comida favorita es el asado', layer: 'user_preference' });
    await memoryTool.store({ content: 'trabajo como analista en la empresa globo', layer: 'semantic' });

    const res = await memoryTool.recall({
      query: 'listame lo que sabes de mi: donde trabajo y mi comida favorita',
    });

    assert.ok(res.toLowerCase().includes('asado'), 'encuentra el hecho de comida');
    assert.ok(res.toLowerCase().includes('globo'), 'encuentra el hecho de trabajo');
  });
});
