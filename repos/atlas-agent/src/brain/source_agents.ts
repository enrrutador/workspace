import { logger } from '../common/logger.js';
import { stringifySkillResult } from '../common/utils.js';
import { QueryCategory, ClassificationResult, SourcePlan, RoutedResult, DataSource } from '../common/types.js';
import { brainSkills } from './skills.js';
import { matchSkillFromInput } from './skill_matcher.js';
import { confidenceRouter } from './confidence_router.js';
import { CONF } from '../common/confidence.js';

export interface SourceAgentConfig {
  name: string;
  sources: DataSource[];
  category: QueryCategory;
  maxRetries: number;
  retryDelayMs: number;
}

interface SourceAgentResult {
  content: string;
  confidence: number;
  source: DataSource;
  metadata?: Record<string, any>;
  retryCount: number;
}

class BaseSourceAgent {
  protected config: SourceAgentConfig;
  protected llmClient: any = null;
  protected systemPrompt: string = '';

  constructor(config: SourceAgentConfig) {
    this.config = config;
  }

  setLLMClient(client: any): void {
    this.llmClient = client;
  }

  setSystemPrompt(prompt: string): void {
    this.systemPrompt = prompt;
  }

  canHandle(source: DataSource): boolean {
    return this.config.sources.includes(source);
  }

  protected async retry<T>(fn: () => Promise<T>, retries: number = this.config.maxRetries): Promise<T> {
    let lastError: Error | null = null;
    for (let i = 0; i <= retries; i++) {
      try {
        return await fn();
      } catch (err) {
        lastError = err as Error;
        if (i < retries) {
          logger.warn(this.config.name, `Retry ${i + 1}/${retries}: ${lastError.message}`);
          await new Promise(r => setTimeout(r, this.config.retryDelayMs * (i + 1)));
        }
      }
    }
    throw lastError || new Error('Retry failed');
  }
}

class GeneralAgent extends BaseSourceAgent {
  constructor() {
    super({
      name: 'general_agent',
      sources: ['llm'],
      category: 'general',
      maxRetries: 1,
      retryDelayMs: 1000,
    });
  }

  async execute(messages: any[], _input: string): Promise<SourceAgentResult> {
    return this.retry(async () => {
      if (!this.llmClient) {
        return { content: 'LLM no disponible', confidence: 0, source: 'llm' as DataSource, retryCount: 0 };
      }

      const workingMessages: any[] = [
        { role: 'system', content: this.systemPrompt },
        ...messages.slice(-6).map(m => ({ role: m.role, content: m.content ?? '' })),
      ];

      const response = await this.llmClient.chatCompletion(workingMessages, 512);
      return {
        content: response,
        confidence: 0.9,
        source: 'llm',
        retryCount: 0,
      };
    });
  }
}

class MemoryAgent extends BaseSourceAgent {
  constructor() {
    super({
      name: 'memory_agent',
      sources: ['memory_store'],
      category: 'memory',
      maxRetries: 1,
      retryDelayMs: 500,
    });
  }

  async execute(input: string, _classification: ClassificationResult): Promise<SourceAgentResult> {
    return this.retry(async () => {
      // Guardado explícito sin pasar por LLM ("recordá que ...", "anotá ...")
      const saveMatch = input.match(
        /\b(?:record[áa]te?|record[áa]|acordate|recuerd[ao]|anot[áa]me?|guard[áa]me?|anotar)\s*(?:que\s+|:|,)?\s*(.+)/i
      );
      if (saveMatch && !/\?|cu[áa]l|quiero saber/i.test(input)) {
        const content = saveMatch[1].trim();
        if (content.length >= 3 && brainSkills.has('memory_store')) {
          await brainSkills.execute('memory_store', {
            content,
            layer: /favorit[oa]|prefier[oa]|es mi|vivo en|trabajo en|nombre/i.test(content)
              ? 'user_preference'
              : 'semantic',
          });
          return { content: `Listo, lo guardé en memoria: "${content}"`, confidence: CONF.MEMORY_STORED, source: 'memory_store' as DataSource, retryCount: 0 };
        }
      }

      if (!brainSkills.has('memory_recall')) {
        return { content: 'No tengo memoria disponible.', confidence: CONF.UNAVAILABLE, source: 'memory_store' as DataSource, retryCount: 0 };
      }

      const query = input
        .replace(/(?:record[áa]|recuerda|acordate|que\s+(?:hablamos|dimos|guard|almacen|memoriz|anote))[\s:]*/i, '')
        .trim() || input;

      const result = await brainSkills.execute('memory_recall', { query });
      const content = stringifySkillResult(result);

      const confidence = content.includes('No encontré nada') ? 0.3 : 0.85;
      return { content, confidence, source: 'memory_store' as DataSource, retryCount: 0 };
    });
  }
}

class WebAgent extends BaseSourceAgent {
  constructor() {
    super({
      name: 'web_agent',
      sources: ['web_search', 'web_scrape'],
      category: 'web',
      maxRetries: 2,
      retryDelayMs: 2000,
    });
  }

  async execute(input: string, classification: ClassificationResult, plan: SourcePlan): Promise<SourceAgentResult> {
    let retryCount = 0;

    if (plan.source === 'web_search' && brainSkills.has('web_search')) {
      try {
        const query = this.buildWebQuery(input, classification);
        const searchType = classification.subIntent === 'news' ? 'news' : 'web';
        const result = await brainSkills.execute('web_search', { query, type: searchType, count: 8 });
        const content = stringifySkillResult(result);
        return {
          content,
          confidence: 0.85,
          source: 'web_search',
          metadata: { query, type: searchType },
          retryCount,
        };
      } catch (err) {
        logger.warn('web_agent', `web_search failed: ${err}`);
        retryCount++;
      }
    }

    if (plan.source === 'web_scrape' || retryCount > 0) {
      const url = plan.skillArgs?.url;
      if (url && brainSkills.has('web_scrape')) {
        try {
          const result = await brainSkills.execute('web_scrape', { url, depth: plan.skillArgs?.depth || 'basic' });
          const content = stringifySkillResult(result);
          return { content, confidence: CONF.WEB_RESULTS, source: 'web_scrape', metadata: { url }, retryCount };
        } catch (err) {
          logger.warn('web_agent', `web_scrape also failed: ${err}`);
          retryCount++;
        }
      }
    }

    if (this.llmClient) {
      logger.info('web_agent', 'Falling back to LLM synthesis for web query');
      const workingMessages: any[] = [
        { role: 'system', content: this.systemPrompt + '\n\nEl usuario pregunta por información actual que no pudimos obtener en la web. Respondé con lo que sepas, pero aclará que puede no estar actualizado.' },
        { role: 'user', content: input },
      ];
      try {
        const response = await this.llmClient.chatCompletion(workingMessages, 512);
        return { content: response, confidence: CONF.WEB_SYNTHESIS, source: 'llm_synthesis' as DataSource, retryCount };
      } catch {}
    }

    return { content: 'No pude obtener información actual. Probá de nuevo en un rato.', confidence: 0, source: 'web_search', retryCount };
  }

  private buildWebQuery(input: string, classification: ClassificationResult): string {
    let query = input
      .replace(/^(decime|dame|contame|mostrame|necesito|quiero|quisiera|pod[eé]s|busc[áa]|buscar|averigu[áa]|encontr[áa]|investig[áa])\s+/i, '')
      .replace(/\s*(por favor|porfa|pls|please|gracias)\s*$/i, '')
      .trim();

    if (classification.subIntent === 'weather') {
      if (!/hoy|ahora|actual/.test(query.toLowerCase())) {
        query += ' hoy';
      }
    }

    return query || input;
  }
}

class CodeAgent extends BaseSourceAgent {
  constructor() {
    super({
      name: 'code_agent',
      sources: ['llm_with_context'],
      category: 'code',
      maxRetries: 2,
      retryDelayMs: 2000,
    });
  }

  async execute(messages: any[], input: string, _classification: ClassificationResult): Promise<SourceAgentResult> {
    return this.retry(async () => {
      if (!this.llmClient) {
        return { content: 'LLM no disponible para code', confidence: 0, source: 'llm_with_context' as DataSource, retryCount: 0 };
      }

      const skills = brainSkills.listRaw();
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

      const workingMessages: any[] = [
        { role: 'system', content: this.systemPrompt },
        ...messages.slice(-6).map(m => ({ role: m.role, content: m.content ?? '' })),
      ];

      const response = await this.llmClient.chatCompletionWithTools(workingMessages, toolDefs, 1024);

      if (response.toolCalls && response.toolCalls.length > 0) {
        const results: string[] = [];
        workingMessages.push({
          role: 'assistant',
          content: response.content ?? null,
          tool_calls: response.toolCalls.map((tc: any) => ({
            id: tc.id,
            type: 'function',
            function: tc.function,
          })),
        });

        for (const tc of response.toolCalls) {
          let args: Record<string, any> = {};
          try { args = JSON.parse(tc.function.arguments); } catch { args = { input }; }

          try {
            const result = await brainSkills.execute(tc.function.name, args);
            const resultStr = stringifySkillResult(result);
            results.push(resultStr.slice(0, 8000));
            workingMessages.push({
              role: 'tool',
              tool_call_id: tc.id,
              content: resultStr.slice(0, 8000),
            });
          } catch (err) {
            workingMessages.push({
              role: 'tool',
              tool_call_id: tc.id,
              content: `Error: ${(err as Error).message}`,
            });
          }
        }

        workingMessages.push({
          role: 'user',
          content: 'Sintetizá los resultados y respondé al usuario en español coloquial. No pegues datos crudos.',
        });

        const finalResponse = await this.llmClient.chatCompletion(workingMessages, 1024);
        return {
          content: finalResponse,
          confidence: 0.85,
          source: 'llm_with_context',
          metadata: { toolsUsed: response.toolCalls.map((tc: any) => tc.function.name) },
          retryCount: 0,
        };
      }

      return {
        content: response.content || 'No se me ocurrió qué decir.',
        confidence: 0.85,
        source: 'llm_with_context',
        retryCount: 0,
      };
    });
  }
}

class ProjectAgent extends BaseSourceAgent {
  constructor() {
    super({
      name: 'project_agent',
      sources: ['file_system', 'git'],
      category: 'project',
      maxRetries: 1,
      retryDelayMs: 1000,
    });
  }

  async execute(_input: string, plan: SourcePlan): Promise<SourceAgentResult> {
    const skillName = plan.skillName || (plan.source === 'git' ? 'git_manager' : 'list_files');
    const skillArgs = plan.skillArgs || (plan.source === 'git' ? { command: 'status' } : { path: '.' });

    if (!brainSkills.has(skillName)) {
      return { content: `Skill ${skillName} no disponible.`, confidence: 0, source: plan.source, retryCount: 0 };
    }

    try {
      const result = await brainSkills.execute(skillName, skillArgs);
      const content = stringifySkillResult(result);
      return { content, confidence: CONF.SKILL_DIRECT, source: plan.source, retryCount: 0 };
    } catch (err) {
      return { content: `Error: ${(err as Error).message}`, confidence: 0, source: plan.source, retryCount: 0 };
    }
  }
}

class ToolAgent extends BaseSourceAgent {
  constructor() {
    super({
      name: 'tool_agent',
      sources: ['skill_direct', 'llm_confirm'],
      category: 'tool',
      maxRetries: 1,
      retryDelayMs: 1000,
    });
  }

  async execute(input: string, plan: SourcePlan): Promise<SourceAgentResult> {
    if (plan.source === 'skill_direct') {
      const skillMatch = matchSkillFromInput(input, brainSkills.listRaw());
      const skillName = plan.skillName || skillMatch?.name;
      const skillArgs = plan.skillArgs || skillMatch?.args || {};

      const skillDef = skillName ? brainSkills.listRaw().find(s => s.name === skillName) : undefined;
      // Ejecución directa SOLO si los args requeridos están completos:
      // antes le pasaba {} a read_file/save_file (la extracción heurística
      // no alcanza) y hasta "creá el archivo X" coría el skill equivocado.
      const hasRequired = !!skillDef && skillDef.parameters
        .filter(p => p.required)
        .every(p => {
          const v = (skillArgs as Record<string, any>)[p.name];
          return v !== undefined && String(v).trim() !== '';
        });

      if (skillName && brainSkills.has(skillName) && hasRequired) {
        try {
          const result = await brainSkills.execute(skillName, skillArgs);
          const content = stringifySkillResult(result);
          return { content, confidence: CONF.SKILL_DIRECT, source: 'skill_direct', metadata: { skillName }, retryCount: 0 };
        } catch (err) {
          return { content: `Error: ${(err as Error).message}`, confidence: 0, source: 'skill_direct' as DataSource, retryCount: 0 };
        }
      }

      // Args incompletos o skill desconocido: loop de tools guiado por LLM
      // (multi-hop, validación de args, salida determinística ante fallos).
      if (this.llmClient) {
        const result = await confidenceRouter.runToolLoop(
          [
            { role: 'system', content: this.systemPrompt },
            { role: 'user', content: input },
          ],
          input,
        );
        return {
          content: result.content,
          confidence: result.confidence,
          source: (result.source || 'skill_direct') as DataSource,
          metadata: result.metadata as any,
          retryCount: 0,
        };
      }
      return { content: 'No encontré la herramienta adecuada (y el LLM no está disponible).', confidence: CONF.UNAVAILABLE, source: 'skill_direct' as DataSource, retryCount: 0 };
    }

    if (plan.source === 'llm_confirm' && this.llmClient) {
      // Ya no es un chat a ciegas: resolvemos por el loop de tools, que
      // sí puede ejecutar (y honestamente fallar) acciones.
      const result = await confidenceRouter.runToolLoop(
        [
          { role: 'system', content: this.systemPrompt },
          { role: 'user', content: input },
        ],
        input,
      );
      return {
        content: result.content,
        confidence: result.confidence,
        source: (result.source || 'llm_confirm') as DataSource,
        metadata: result.metadata as any,
        retryCount: 0,
      };
    }

    return { content: 'Fuente no manejada por tool_agent.', confidence: 0, source: plan.source, retryCount: 0 };
  }
}

export class SourceAgentOrchestrator {
  private static instance: SourceAgentOrchestrator;
  private agents: Map<QueryCategory, BaseSourceAgent> = new Map();

  private constructor() {
    this.agents.set('general', new GeneralAgent());
    this.agents.set('memory', new MemoryAgent());
    this.agents.set('web', new WebAgent());
    this.agents.set('code', new CodeAgent());
    this.agents.set('project', new ProjectAgent());
    this.agents.set('tool', new ToolAgent());
  }

  static getInstance(): SourceAgentOrchestrator {
    if (!SourceAgentOrchestrator.instance) {
      SourceAgentOrchestrator.instance = new SourceAgentOrchestrator();
    }
    return SourceAgentOrchestrator.instance;
  }

  setLLMClient(client: any): void {
    for (const agent of this.agents.values()) {
      agent.setLLMClient(client);
    }
  }

  setSystemPrompt(prompt: string): void {
    for (const agent of this.agents.values()) {
      agent.setSystemPrompt(prompt);
    }
  }

  async executeSource(
    plan: SourcePlan,
    messages: any[],
    input: string,
    classification: ClassificationResult,
  ): Promise<RoutedResult> {
    const category = classification.category;
    const agent = this.agents.get(category);

    if (!agent) {
      logger.warn('source_agent_orchestrator', `No agent for category: ${category}`);
      return { source: plan.source, content: 'Categoría no manejada', confidence: 0 };
    }

    logger.info('source_agent_orchestrator', `Routing to ${agent['config'].name} for source: ${plan.source}`);

    try {
      if (agent instanceof GeneralAgent) {
        const result = await (agent as GeneralAgent).execute(messages, input);
        return { source: result.source, content: result.content, confidence: result.confidence, metadata: result.metadata };
      }

      if (agent instanceof MemoryAgent) {
        const result = await (agent as MemoryAgent).execute(input, classification);
        return { source: result.source, content: result.content, confidence: result.confidence, metadata: result.metadata };
      }

      if (agent instanceof WebAgent) {
        const result = await (agent as WebAgent).execute(input, classification, plan);
        return { source: result.source, content: result.content, confidence: result.confidence, metadata: result.metadata };
      }

      if (agent instanceof CodeAgent) {
        const result = await (agent as CodeAgent).execute(messages, input, classification);
        return { source: result.source, content: result.content, confidence: result.confidence, metadata: result.metadata };
      }

      if (agent instanceof ProjectAgent) {
        const result = await (agent as ProjectAgent).execute(input, plan);
        return { source: result.source, content: result.content, confidence: result.confidence, metadata: result.metadata };
      }

      if (agent instanceof ToolAgent) {
        const result = await (agent as ToolAgent).execute(input, plan);
        return { source: result.source, content: result.content, confidence: result.confidence, metadata: result.metadata };
      }

      return { source: plan.source, content: 'Agente sin handler', confidence: 0 };
    } catch (err) {
      logger.error('source_agent_orchestrator', `Agent ${agent['config'].name} failed: ${err}`);
      return { source: plan.source, content: `Error: ${(err as Error).message}`, confidence: 0 };
    }
  }
}

export const sourceAgentOrchestrator = SourceAgentOrchestrator.getInstance();
