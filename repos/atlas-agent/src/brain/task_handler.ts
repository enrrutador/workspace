import { logger } from '../common/logger.js';
import { CONFIDENCE_THRESHOLD } from '../common/confidence.js';
import { brainSkills } from './skills.js';
import { Message, ForgeInput, ClassificationResult, FeedbackType } from '../common/types.js';
import { confidenceRouter } from './confidence_router.js';
import { synthesizer } from './synthesizer.js';
import { subQuestionDecomposer } from './subquestion_decomposer.js';
import { sourceAgentOrchestrator } from './source_agents.js';
import { semanticCache } from './semantic_cache.js';
import { feedbackLoop } from './feedback_loop.js';
import { multiAgentOrchestrator } from './multi_agent_orchestrator.js';
import { queryClassifier } from './query_classifier.js';
import { contextCompressor } from './context_compressor.js';

export interface TaskResult {
  success: boolean;
  response: string;
  escalated?: boolean;
  forgeInput?: ForgeInput;
  metadata?: Record<string, any>;
}

const CACHE_ENABLED = process.env.CACHE_ENABLED !== 'false';

interface LastResponse {
  query: string;
  category: string;
  source: string;
  response: string;
}

export class TaskHandler {
  private static instance: TaskHandler;
  private llmClient: any = null;
  private systemPrompt: string = '';
  // Por sesión (CLI y cada chat de Telegram tienen su propio contexto de
  // feedback); antes era un campo global compartido entre sesiones.
  private lastResponse: Map<string, LastResponse> = new Map();

  private constructor() {}

  static getInstance(): TaskHandler {
    if (!TaskHandler.instance) {
      TaskHandler.instance = new TaskHandler();
    }
    return TaskHandler.instance;
  }

  setLLMClient(client: any): void {
    this.llmClient = client;
  }

  setSystemPrompt(prompt: string): void {
    this.systemPrompt = prompt;
  }

  async handle(messages: Message[], sessionId: string): Promise<TaskResult> {
    const lastMessage = messages[messages.length - 1];
    if (!lastMessage || lastMessage.role !== 'user') {
      return { success: false, response: 'No user message found' };
    }

    const input = lastMessage.content || '';
    logger.info('task_handler', `Processing: "${input.slice(0, 100)}"`);

    const lastResp = this.lastResponse.get(sessionId);
    if (lastResp) {
      const feedbackType = feedbackLoop.detectFeedback(input);
      if (feedbackType && messages.length >= 2) {
        return this.handleFeedback(input, feedbackType, messages, sessionId);
      }
    }

    const selfQuery = input.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim();
    if (/que (sabes|puedes) (hacer|usar)|cuales son tus (habilidades|skills|herramientas)|list.*skills|que herramientas|what can you do|que (cosas|tareas) (puedes|sabes)|de que eres capaz|que podes hacer|mostra.*(skills|herramientas)/i.test(selfQuery)) {
      const skills = brainSkills.list();
      const skillList = skills.map(s => ` • ${s.description}`).join('\n');
      return {
        success: true,
        response: `¡Hola! Soy Atlas, tu agente AI. Estas son las cosas que sé hacer:\n\n${skillList}\n\n¿En qué te ayudo?`,
      };
    }

    try {
      const decomposition = await subQuestionDecomposer.decompose(input);
      logger.info('task_handler', `Decomposition: isCompound=${decomposition.isCompound}, subQs=${decomposition.subQuestions.length}, strategy=${decomposition.strategy}`);

      if (decomposition.subQuestions.length === 1) {
        return this.processSingleQuery(messages, input, decomposition.subQuestions[0].classification, sessionId);
      }

      let results: Array<{ subQuestion: string; result: { source: string; content: string; confidence: number }; synthesizedResponse: string }>;

      // Consolidación: un solo camino para compuestos (antes había dos pilas
      // con comportamientos distintos según USE_MULTI_AGENT true/false).
      const orchestratorResults = await multiAgentOrchestrator.orchestrateCompound(
        decomposition.subQuestions,
        messages,
        decomposition.strategy as 'sequential' | 'parallel' | 'pipeline',
      );
      results = orchestratorResults.map(r => ({
        subQuestion: r.subQuestion,
        result: { source: r.result.source, content: r.result.content, confidence: r.result.confidence },
        synthesizedResponse: r.synthesizedResponse,
      }));

      const finalResponse = this.mergeSubResponses(results.map(r => ({
        subQuestion: r.subQuestion,
        response: r.synthesizedResponse,
        category: decomposition.subQuestions.find(sq => sq.text === r.subQuestion)?.classification.category || 'general',
        source: r.result.source,
      })));

      this.lastResponse.set(sessionId, {
        query: input,
        category: 'compound',
        source: 'multi_agent',
        response: finalResponse,
      });

      return {
        success: true,
        response: finalResponse,
        metadata: {
          category: 'compound',
          subQuestions: decomposition.subQuestions.length,
          strategy: decomposition.strategy,
          subResults: results.map(r => ({ source: r.result.source })),
        },
      };
    } catch (err) {
      logger.error('task_handler', `Classification/routing failed: ${err}`);

      if (this.llmClient && this.systemPrompt) {
        logger.info('task_handler', 'Falling back to direct LLM after error');
        const workingMessages: any[] = [
          { role: 'system', content: this.systemPrompt },
          ...contextCompressor.compress(messages)
            .filter(m => m.role !== 'system')
            .map(m => ({ role: m.role, content: m.content ?? '' })),
        ];
        try {
          const response = await this.llmClient.chatCompletion(workingMessages, 1024);
          return {
            success: true,
            response: this.cleanupFillers(response),
            metadata: { source: 'llm_error_fallback' },
          };
        } catch {}
      }

      return {
        success: true,
        response: 'Procesando con Forge...',
        escalated: true,
        forgeInput: {
          problem: input,
          context: messages.slice(-10).map(m => `${m.role}: ${m.content}`).join('\n'),
          mode: 'decision',
        },
      };
    }
  }

  private async handleFeedback(input: string, feedbackType: FeedbackType, messages: Message[], sessionId: string): Promise<TaskResult> {
    const lastResp = this.lastResponse.get(sessionId);
    if (!lastResp) {
      return this.processSingleQuery(messages, input, await queryClassifier.classify(input), sessionId);
    }

    logger.info('task_handler', `Feedback detected: ${feedbackType} for previous response`);

    feedbackLoop.recordFeedback(
      lastResp.query,
      lastResp.category as any,
      lastResp.source as any,
      lastResp.response,
      feedbackType,
      input,
    );

    switch (feedbackType) {
      case 'correction':
      case 'clarification': {
        const originalQuery = lastResp.query;
        const classification = await queryClassifier.classify(originalQuery);
        const sourcePlan = confidenceRouter.getSourcePlan(classification);
        const adjustedPlan = sourcePlan.map(sp => ({
          ...sp,
          confidence: feedbackLoop.getAdjustedConfidence(classification.category, sp.source, sp.confidence),
        })).sort((a, b) => b.confidence - a.confidence);

        if (adjustedPlan.length > 1) {
          const nextSource = adjustedPlan.find(sp => sp.source !== lastResp.source);
          if (nextSource && nextSource.confidence >= CONFIDENCE_THRESHOLD) {
            logger.info('task_handler', `Retrying with different source: ${nextSource.source} (original was: ${lastResp.source})`);
            const result = await sourceAgentOrchestrator.executeSource(nextSource, messages, originalQuery, classification);
            const synthesized = await synthesizer.synthesize(result, classification.category, originalQuery);
            this.lastResponse.set(sessionId, { query: originalQuery, category: classification.category, source: nextSource.source, response: synthesized });
            return {
              success: true,
              response: `Probé con otra fuente:\n\n${synthesized}`,
              metadata: { category: classification.category, source: nextSource.source, feedbackRetried: true },
            };
          }
        }

        if (this.llmClient && this.systemPrompt) {
          const workingMessages: any[] = [
            { role: 'system', content: this.systemPrompt },
            { role: 'user', content: originalQuery },
            { role: 'assistant', content: lastResp.response },
            { role: 'user', content: `Eso no es correcto. ${input}. Respondé de nuevo mejor.` },
          ];
          const response = await this.llmClient.chatCompletion(workingMessages, 1024);
          this.lastResponse.set(sessionId, { query: originalQuery, category: classification.category, source: 'llm_retry', response });
          return {
            success: true,
            response: this.cleanupFillers(response),
            metadata: { category: classification.category, source: 'llm_retry', feedbackType },
          };
        }

        return {
          success: true,
          response: 'Entendido, voy a tener en cuenta tu corrección para la próxima.',
          metadata: { feedbackRecorded: true },
        };
      }

      case 'confirmation':
        return {
          success: true,
          response: '¡Genial! Si necesitás algo más, decime.',
          metadata: { feedbackRecorded: true },
        };

      case 'rejection':
        return {
          success: true,
          response: 'Entiendo, lo voy a tener en cuenta. Si querés, probá reformular la pregunta y lo intento de nuevo.',
          metadata: { feedbackRecorded: true },
        };

      default:
        return this.processSingleQuery(messages, input, await queryClassifier.classify(input), sessionId);
    }
  }

  private async processSingleQuery(
    messages: Message[],
    input: string,
    classification: ClassificationResult,
    sessionId: string,
  ): Promise<TaskResult> {
    logger.info('task_handler', `Single query: "${input.slice(0, 80)}" → ${classification.category} (${classification.confidence}) via ${classification.source}`);

    if (CACHE_ENABLED) {
      const cached = semanticCache.get(input, classification.category);
      if (cached) {
        logger.info('task_handler', `Cache HIT for: "${input.slice(0, 60)}"`);
        this.lastResponse.set(sessionId, { query: input, category: classification.category, source: cached.result.source, response: cached.synthesizedResponse });
        return {
          success: true,
          response: cached.synthesizedResponse,
          metadata: {
            category: classification.category,
            source: cached.result.source,
            confidence: cached.result.confidence,
            fromCache: true,
          },
        };
      }
    }

    const previousCorrection = feedbackLoop.getCorrectionForQuery(input, classification.category);
    if (previousCorrection) {
      logger.info('task_handler', `Found previous correction for similar query`);
    }

    const sourcePlan = confidenceRouter.getSourcePlan(classification);
    const adjustedPlan = sourcePlan.map(sp => ({
      ...sp,
      confidence: feedbackLoop.getAdjustedConfidence(classification.category, sp.source, sp.confidence),
    }));
    logger.info('task_handler', `Source plan: ${adjustedPlan.map(s => `${s.source}(${s.confidence.toFixed(2)})`).join(' → ')}`);

    const fallbackPlan = adjustedPlan.filter(sp => sp.confidence < CONFIDENCE_THRESHOLD);

    let result: any = null;

    try {
      result = await multiAgentOrchestrator.orchestrate(input, messages, classification);
    } catch (err) {
      logger.error('task_handler', `Multi-agent orchestration failed: ${err}`);
    }

    // Fallbacks de baja confianza del plan (antes quedaban muertos: getSourcePlan
    // los filtraba por threshold y jamás se ejecutaban). Mejor una respuesta
    // mediocre que "No pude resolver eso".
    let usedFallback = false;
    if ((!result || result.confidence < CONFIDENCE_THRESHOLD) && fallbackPlan.length > 0) {
      for (const source of fallbackPlan) {
        logger.info('task_handler', `Trying low-confidence fallback source ${source.source} (confidence ${source.confidence.toFixed(2)})`);
        try {
          const r = await sourceAgentOrchestrator.executeSource(source, messages, input, classification);
          if (r.confidence > 0 && r.content) {
            result = r;
            usedFallback = true;
            break;
          }
        } catch (err) {
          logger.error('task_handler', `Fallback source ${source.source} failed: ${err}`);
        }
      }
    }

    if (result && (usedFallback || result.confidence >= CONFIDENCE_THRESHOLD)) {
      const synthesized = await synthesizer.synthesize(result, classification.category, input);
      logger.info('task_handler', `Response from ${result.source} (confidence: ${result.confidence})`);

      if (CACHE_ENABLED && classification.category !== 'tool' && result.confidence >= CONFIDENCE_THRESHOLD) {
        semanticCache.store(input, classification.category, result, synthesized);
      }

      this.lastResponse.set(sessionId, { query: input, category: classification.category, source: result.source, response: synthesized });

      return {
        success: true,
        response: synthesized,
        metadata: {
          category: classification.category,
          source: result.source,
          confidence: result.confidence,
          classificationSource: classification.source,
          subIntent: classification.subIntent,
        },
      };
    }

    if (this.llmClient && this.systemPrompt) {
      logger.info('task_handler', 'All sources below threshold, falling back to direct LLM');
      const workingMessages: any[] = [
        { role: 'system', content: this.systemPrompt },
        ...contextCompressor.compress(messages)
          .filter(m => m.role !== 'system')
          .map(m => ({ role: m.role, content: m.content ?? '' })),
      ];
      const response = await this.llmClient.chatCompletion(workingMessages, 1024);
      this.lastResponse.set(sessionId, { query: input, category: classification.category, source: 'llm_fallback', response });
      return {
        success: true,
        response: this.cleanupFillers(response),
        metadata: { category: classification.category, source: 'llm_fallback' },
      };
    }

    return {
      success: true,
      response: 'No pude resolver eso. Probá reformular la pregunta.',
      metadata: { category: classification.category },
    };
  }

  private mergeSubResponses(
    responses: Array<{ subQuestion: string; response: string; category: string; source: string }>,
  ): string {
    // Dedupe de contenido: sub-respuestas que repiten frases de una sub-pregunta
    // anterior (el modelo a veces repite el tema en cada parte del split).
    const seenSentences: string[][] = [];
    const tokenize = (s: string) =>
      s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')
        .replace(/[^a-z0-9\s]/g, ' ').split(/\s+/).filter(w => w.length > 2);

    const isDup = (tokens: string[]) => {
      if (tokens.length === 0) return false;
      return seenSentences.some(prev => {
        const prevSet = new Set(prev);
        let hit = 0;
        for (const t of tokens) if (prevSet.has(t)) hit++;
        // solapamiento de contenido >= 60% con una frase ya mostrada
        return hit / Math.min(tokens.length, prev.length) >= 0.6;
      });
    };

    const deduped: Array<typeof responses[0]> = [];
    for (const r of responses) {
      const sentences = r.response.replace(/\s+/g, ' ').split(/(?<=[.!?…])\s+/);
      const kept: string[] = [];
      for (const s of sentences) {
        const t = tokenize(s);
        if (isDup(t)) continue;
        seenSentences.push(t);
        kept.push(s.trim());
      }
      if (kept.length === 0) {
        logger.info('task_handler', `Sub-respuesta duplicada omitida: "${r.subQuestion.slice(0, 60)}"`);
        continue;
      }
      deduped.push({ ...r, response: kept.join(' ').trim() });
    }

    if (deduped.length === 0) return responses[0]?.response ?? '';
    responses = deduped;
    if (responses.length === 1) {
      return responses[0].response;
    }

    const allGeneral = responses.every(r => r.category === 'general');

    if (allGeneral && responses.length <= 2) {
      return responses.map(r => r.response).join('\n\n');
    }

    if (responses.length <= 3) {
      const parts = responses.map(r => {
        if (!allGeneral) {
          return `Sobre "${r.subQuestion.replace(/\?/g, '')}":\n${r.response}`;
        }
        return r.response;
      });
      return parts.join('\n\n');
    }

    const summaryParts = responses.map(r => {
      const brief = r.response.length > 300 ? r.response.slice(0, 300) + '...' : r.response;
      return `• ${brief}`;
    });
    return summaryParts.join('\n\n');
  }

  private cleanupFillers(text: string): string {
    return text
      .replace(/¿Puedo ayudarte con algo más\?/gi, '')
      .replace(/Avísame si necesitas algo\.?/gi, '')
      .replace(/Estoy aquí para ayudarte\.?/gi, '')
      .replace(/No dudes en preguntar\.?/gi, '')
      .trim() || text;
  }
}

export const taskHandler = TaskHandler.getInstance();
