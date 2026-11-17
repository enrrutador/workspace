#!/usr/bin/env node
/**
 * Tests unitarios puros (sin red, sin LLM):
 * - skill_matcher: match + extracción de args (math, traducción, git, shell)
 * - subquestion_decomposer: filtro de sub-preguntas redundantes
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { matchSkillFromInput } from '../src/brain/skill_matcher.js';
import { subQuestionDecomposer } from '../src/brain/subquestion_decomposer.js';
import { brainSkills } from '../src/brain/skills.js';

function rawSkillsFor(names: string[]): Parameters<typeof matchSkillFromInput>[1] {
  // matchSkillFromInput recibe la lista de skills: registro mínimos
  if (!brainSkills.has('math_calculate')) {
    brainSkills.register({
      name: 'math_calculate',
      description: 'Calcula expresiones matematicas',
      parameters: [{ name: 'expression', type: 'string', description: 'Expr', required: true }],
      handler: async () => '(mock)',
    });
  }
  if (!brainSkills.has('translate')) {
    brainSkills.register({
      name: 'translate',
      description: 'Traduce texto',
      parameters: [
        { name: 'text', type: 'string', description: 'Texto', required: true },
        { name: 'target_lang', type: 'string', description: 'Idioma', required: true },
      ],
      handler: async () => '(mock)',
    });
  }
  if (!brainSkills.has('git_manager')) {
    brainSkills.register({
      name: 'git_manager',
      description: 'Operaciones Git',
      parameters: [{ name: 'description', type: 'string', description: 'd', required: false }],
      handler: async () => '(mock)',
    });
  }
  return brainSkills.listRaw().filter(s => names.includes(s.name));
}

test('skill_matcher: math con frases coloquiales', () => {
  const [math] = rawSkillsFor(['math_calculate']);

  const m1 = matchSkillFromInput('cuanto es sqrt(196)', [math]);
  assert.equal(m1?.name, 'math_calculate');
  assert.equal((m1?.args as any).expression, 'sqrt(196)');

  const m2 = matchSkillFromInput('cuanto es el 15% de 2350', [math]);
  assert.equal(m2?.name, 'math_calculate');
  // sin 'calcular|cuanto es X' estricto, cae al fallback: el input completo
  // (mathTool entiende frases en lenguaje humano)
  assert.equal((m2?.args as any).expression, 'el 15% de 2350');
});

test('skill_matcher: traducción con idiomas sin acento', () => {
  const [translate] = rawSkillsFor(['translate']);

  const m1 = matchSkillFromInput('traduci good morning al japones', [translate]);
  assert.equal(m1?.name, 'translate');
  assert.equal((m1?.args as any).target_lang, 'japones');
  assert.equal((m1?.args as any).text, 'good morning');

  const m2 = matchSkillFromInput('traduci hola al inglés', [translate]);
  assert.equal((m2?.args as any).target_lang, 'inglés');
  assert.equal((m2?.args as any).text, 'hola');
});

test('skill_matcher: git y shell toleran formato con dos puntos', () => {
  const skills = rawSkillsFor(['git_manager']);

  const m1 = matchSkillFromInput('git status', skills);
  assert.equal(m1?.name, 'git_manager');
});

test('skill_matcher: input sin keywords no matchea nada', () => {
  const skills = rawSkillsFor(['math_calculate', 'translate']);
  const m = matchSkillFromInput('hola que tal anda todo', skills);
  assert.equal(m, null);
});

test('descomponedor: sub-pregunta redundante (subconjunto) se descarta', async () => {
  // El split regex separa en 'y': parte B ⊂ parte A → solo queda la rica.
  const d = await subQuestionDecomposer.decompose('traduci good morning al frances y ademas traduci good morning');
  assert.equal(d.subQuestions.length, 1);
  assert.ok(d.subQuestions[0].text.includes('frances'));
});

test('descomponedor: compuesta válida mantiene ambas partes', async () => {
  const d = await subQuestionDecomposer.decompose('cuanto es sqrt(196) y ademas translate hello al espaÑol');
  // sqrt → tool, translate → tool: partes con contenido distinto quedan ambas
  assert.equal(d.subQuestions.length, 2);
});
