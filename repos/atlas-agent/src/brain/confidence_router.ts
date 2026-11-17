import { QueryCategory, ClassificationResult, SourcePlan, RoutedResult } from '../common/types.js';
import { brainSkills } from './skills.js';
import { matchSkillFromInput } from './skill_matcher.js';
import { generateId, stringifySkillResult } from '../common/utils.js';
import { CONF } from '../common/confidence.js';

interface CategoryRouting {
  sources: SourcePlan[];
  offerTools: boolean;
  maxIterations: number;
}

const ROUTING_TABLE: Record<QueryCategory, CategoryRouting> = {
  general: {
    sources: [
      { source: 'llm', confidence: 0.95 },
    ],
    offerTools: false,
    maxIterations: 1,
  },
  memory: {
    sources: [
      { source: 'memory_store', confidence: 0.9 },
      { source: 'llm', confidence: 0.5 },
    ],
    offerTools: false,
    maxIterations: 1,
  },
  project: {
    sources: [
      { source: 'file_system', confidence: 0.9, skillName: 'list_files' },
      { source: 'git', confidence: 0.7, skillName: 'git_manager' },
      { source: 'web_search', confidence: 0.4, skillName: 'web_search' },
    ],
    offerTools: true,
    maxIterations: 3,
  },
  code: {
    sources: [
      { source: 'llm_with_context', confidence: 0.85 },
      { source: 'web_search', confidence: 0.5, skillName: 'web_search' },
    ],
    offerTools: true,
    maxIterations: 5,
  },
  web: {
    sources: [
      { source: 'web_search', confidence: 0.9, skillName: 'web_search' },
      { source: 'llm_synthesis', confidence: 0.3 },
    ],
    offerTools: true,
    maxIterations: 3,
  },
  tool: {
    sources: [
      { source: 'skill_direct', confidence: 0.95 },
      { source: 'llm_confirm', confidence: 0.7 },
    ],
    offerTools: true,
    maxIterations: 3,
  },
};

export class ConfidenceRouter {
  private static instance: ConfidenceRouter;
  private llmClient: any = null;
  private systemPrompt: string = '';

  private constructor() {}

  static getInstance(): ConfidenceRouter {
    if (!ConfidenceRouter.instance) {
      ConfidenceRouter.instance = new ConfidenceRouter();
    }
    return ConfidenceRouter.instance;
  }

  setLLMClient(client: any): void {
    this.llmClient = client;
  }

  setSystemPrompt(prompt: string): void {
    this.systemPrompt = prompt;
  }

  getRouting(classification: ClassificationResult): CategoryRouting {
    return ROUTING_TABLE[classification.category] || ROUTING_TABLE.general;
  }

  getSourcePlan(classification: ClassificationResult): SourcePlan[] {
    const routing = this.getRouting(classification);
    let sources = [...routing.sources];

    if (classification.category === 'tool') {
      const skillMatch = matchSkillFromInput(
        classification.rawResponse || '',
        brainSkills.listRaw(),
      );
      if (skillMatch && skillMatch.confidence >= CONF.SKILL_MATCH_MIN) {
        sources[0] = {
          ...sources[0],
          skillName: skillMatch.name,
          skillArgs: skillMatch.args,
        };
      }
    }

    if (classification.category === 'web' && classification.subIntent) {
      sources[0].skillArgs = {
        ...sources[0].skillArgs,
        query_type: classification.subIntent,
      };
    }

    return sources;
  }

  /**
   * Flujo público de ejecución de tools con multi-hop y salida determinística.
   * Usado por la ruta llm_with_context y delegado por ToolAgent (source_agents)
   * para que TODAS las rutas de acción tengan el mismo blindaje.
   */
  async runToolLoop(messages: any[], input: string): Promise<RoutedResult> {
    if (!this.llmClient) {
      return { source: 'llm', content: 'LLM no disponible', confidence: 0 };
    }
    return this.executeLLM(messages, input, true, { category: 'tool' } as unknown as ClassificationResult);
  }

  private async executeLLM(messages: any[], _input: string, withTools: boolean, classification: ClassificationResult): Promise<RoutedResult> {
    if (!this.llmClient) {
      return { source: 'llm', content: 'LLM no disponible', confidence: 0 };
    }

    // Usa la tabla de routing de la categoría real (antes leía siempre
    // ROUTING_TABLE.general, lo que desactivaba el tool-calling para code).
    const routing = this.getRouting(classification);
    const workingMessages: any[] = [
      { role: 'system', content: this.systemPrompt },
      ...messages.slice(-6).map(m => ({ role: m.role, content: m.content ?? '' })),
    ];

    if (withTools && routing.offerTools) {
      const skills = brainSkills.listRaw();
      const skillNames = new Set(skills.map(s => s.name));
      // El modelo llamaba read_file con {} en el primer intento: avisar
      // explícitamente como llenar los argumentos evita gastar un hop.
      workingMessages.push({
        role: 'user',
        content: 'Usando los tools de la lista: elegí el correcto y pasá TODOS los parámetros requeridos como JSON válido (ej. path, content). Nunca llames a un tool con {} vacío ni fuerces argumentos vacíos.',
      });
      const toolDefs = skills.map(s => ({
        type: 'function' as const,
        function: {
          name: s.name,
          description: s.description,
          parameters: {
            type: 'object' as const,
            properties: Object.fromEntries(
              s.parameters.map(p => [p.name, { type: p.type, description: p.description }])
            ),
            required: s.parameters.filter(p => p.required).map(p => p.name),
          },
        },
      }));

      // Multi-hop con salida determinística: si no hay NINGÚN éxito, no se
      // le entrega la síntesis a la LLM (los modelos pequeños llegan a
      // afirmar "Listo, lo hice" aunque TODOS los tools fallaran).
      const syntheticId = () => `call_${generateId()}`;
      const MAX_TOOL_HOPS = 3;
      const failures: string[] = [];
      for (let hop = 0; hop < MAX_TOOL_HOPS; hop++) {
        const response = await this.llmClient.chatCompletionWithTools(workingMessages, toolDefs, 4096);

        if (!response.toolCalls || response.toolCalls.length === 0) {
          // En la ruta 'tool' una frase sin llamada (ej. 'Voy a borrarlo')
          // no ejecuta nada: se insiste para que llame herramientas, salvo
          // que esté explicando un bloqueo ('No pude porque ...').
          const looksLikeOutcome = /(no\s+(?:pud[eo]|lo logr[eo])|imposible|bloque|fall[óo]|falla|error)/i.test(response.content || '');
          if (hop < MAX_TOOL_HOPS - 1 && !looksLikeOutcome) {
            workingMessages.push({ role: 'assistant', content: response.content ?? null });
            workingMessages.push({
              role: 'user',
              content: 'Eso es una intención, no un resultado. Ejecutá la acción llamando a un tool AHORA. Si es imposible, decí exactamente qué la bloquea y nada más.',
            });
            continue;
          }
          if (looksLikeOutcome) {
            return {
              source: 'llm',
              content: response.content || 'No se me ocurrió qué decir.',
              confidence: CONF.LLM_PLAIN,
            };
          }
          // Último hop sin herramientas y sin declinación explícita:
          // NO se acepta como respuesta (podría afirmar éxito falso).
          break;
        }

        workingMessages.push({
          role: 'assistant',
          content: response.content ?? null,
          tool_calls: response.toolCalls.map((tc: any) => ({
            id: tc.id,
            type: 'function',
            function: tc.function,
          })),
        });

        const successes: string[] = [];
        for (const tc of response.toolCalls) {
          if (!skillNames.has(tc.function.name)) {
            const msg = `Error: tool desconocido '${tc.function.name}'. Tools disponibles: ${[...skillNames].join(', ')}`;
            failures.push(`${tc.function.name}: ${msg}`);
            workingMessages.push({
              role: 'tool',
              tool_call_id: tc.id || syntheticId(),
              content: msg,
            });
            continue;
          }

          let args: Record<string, any> = {};
          try {
            args = JSON.parse(tc.function.arguments || '{}');
          } catch {
            const msg = `Error: argumentos JSON inválidos (${String(tc.function.arguments).slice(0, 200)}). Corregí los argumentos e intentá de nuevo.`;
            failures.push(`${tc.function.name}: argumentos JSON inválidos`);
            workingMessages.push({
              role: 'tool',
              tool_call_id: tc.id,
              content: msg,
            });
            continue;
          }

          try {
            const result = await brainSkills.execute(tc.function.name, args);
            const resultStr = stringifySkillResult(result);
            successes.push(`✅ ${tc.function.name}: ${resultStr.slice(0, 1500)}`);
            workingMessages.push({
              role: 'tool',
              tool_call_id: tc.id,
              content: resultStr.slice(0, 8000),
            });
          } catch (err) {
            const msg = `Error: ${(err as Error).message}`;
            failures.push(`${tc.function.name}: ${(err as Error).message.slice(0, 200)}`);
            workingMessages.push({
              role: 'tool',
              tool_call_id: tc.id,
              content: msg,
            });
          }
        }

        if (successes.length > 0) {
          workingMessages.push({
            role: 'user',
            content: 'Sintetizá los resultados y respondé al usuario en español coloquial. Los siguientes resultados de tools son VERIFICADOS y podés basarte en ellos:\n' + successes.join('\n').slice(0, 6000),
          });

          const finalResponse = await this.llmClient.chatCompletion(workingMessages, 4096);
          return {
            source: 'llm_with_context',
            content: finalResponse,
            confidence: CONF.TOOL_SYNTHESIS,
            metadata: { toolsUsed: response.toolCalls.map((tc: any) => tc.function.name) },
          };
        }

        if (hop < MAX_TOOL_HOPS - 1) {
          workingMessages.push({
            role: 'user',
            content: 'Todos los tools fallaron con el error de arriba. Analizá qué salió mal, corregí los argumentos y volvé a intentar; si no podés del todo, decí explícitamente qué queda pendiente.',
          });
        }
      }

      // Terminó de reintentar sin ningún éxito: respuesta determinística con
      // los errores reales (nunca se afirma que la operación salió bien).
      return {
        source: 'llm',
        content: `No pude completar la operación: todas las herramientas que probé fallaron.\n${failures.join('\n').slice(0, 1000)}`,
        confidence: CONF.DETERMINISTIC_FAILURE,
      };
    }

    // 1024: se lo comía el reasoning_content de los modelos reasoning y
    // volvía content nulo ('No response'). Alineado con el default del
    // LLMClient (4096).
    const response = await this.llmClient.chatCompletion(workingMessages, 4096);
    return {
      source: 'llm',
      content: response,
      confidence: CONF.LLM_PLAIN,
    };
  }
}

export const confidenceRouter = ConfidenceRouter.getInstance();
