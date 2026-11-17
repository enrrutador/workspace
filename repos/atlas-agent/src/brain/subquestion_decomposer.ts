import { logger } from '../common/logger.js';
import { ClassificationResult } from '../common/types.js';
import { queryClassifier } from './query_classifier.js';

export interface SubQuestion {
  text: string;
  classification: ClassificationResult;
  index: number;
}

export interface DecompositionResult {
  original: string;
  subQuestions: SubQuestion[];
  isCompound: boolean;
  strategy: 'sequential' | 'parallel' | 'single';
}

const COMPOUND_INDICATORS: RegExp[] = [
  /[,;]\s*(?:y\s+)?(?:tambi[eé]n|adem[aá]s|luego|despu[eé]s|tampoco|pero|aunque|mientras|sin embargo)\s+/i,
  /\s+(?:y\s+(?:tambi[eé]n|adem[aá]s|luego))\s+/i,
  /(?:y\s+tambi[eé]n|y\s+adem[aá]s|y\s+luego|y\s+despu[eé]s)\s+/i,
  /\?\s*[,.]?\s*(?:y\s+)?(?:tambi[eé]n|adem[aá]s|luego|despu[eé]s)/i,
  /\?\s*[,.]?\s*(?:y\s+)?(?:qu[eé]|qui[eé]n|c[oó]mo|cu[aá]ndo|d[oó]nde|cu[aá]nto|cu[aá]l|por qu[eé]|porqu[eé])\s+/i,
  /\?\s*[,.]?\s*(?:y\s+)?(?:what|who|how|when|where|how much|which|why)\s+/i,
  /(?:y\s+(?:a\s+|al\s+|de\s+|del\s+|en\s+)?(?:qu[eé]|qui[eé]n|c[oó]mo|cu[aá]ndo|d[oó]nde|cu[aá]nto|cu[aá]l|por\s+qu[eé]))\s+/i,
];

const SPLIT_PATTERNS: RegExp[] = [
  /\s+y\s+(?=(?:a\s+|al\s+|de\s+|del\s+|en\s+)?(?:qu[eé]|qui[eé]n|c[oó]mo|cu[aá]ndo|d[oó]nde|cu[aá]nto|cu[aá]l|por\s+qu[eé])\s+)/i,
  /(?:y\s+(?:tambi[eé]n|adem[aá]s|luego|despu[eé]s))\s+/i,
  /(?:,\s*(?:y\s+)?(?:tambi[eé]n|adem[aá]s|luego|despu[eé]s))\s+/i,
  /\?\s*[,.]?\s*(?=(?:y\s+)?(?:qu[eé]|qui[eé]n|c[oó]mo|cu[aá]ndo|d[oó]nde|cu[aá]nto|cu[aá]l|por\s+qu[eé]|porqu[eé]|what|who|how|when|where|which|why)\s+)/i,
];

const SINGLE_QUESTION_PATTERNS: RegExp[] = [
  /^(?:hola|hey|buenas|que\s+tal|como\s+andas|como\s+estas|gracias|thx|ok|dale|si|no|bien|chau|adios)/i,
  /^(?:que\s+(?:sabes|puedes)|cuales\s+son\s+tus|list.*skills|que\s+herramientas)/i,
];

export class SubQuestionDecomposer {
  private static instance: SubQuestionDecomposer;
  private llmClient: any = null;
  private classifierModel: string = process.env.CLASSIFIER_MODEL || 'nvidia/nemotron-mini-4b-instruct';
  private timeoutMs: number = 5000;

  private constructor() {}

  static getInstance(): SubQuestionDecomposer {
    if (!SubQuestionDecomposer.instance) {
      SubQuestionDecomposer.instance = new SubQuestionDecomposer();
    }
    return SubQuestionDecomposer.instance;
  }

  setLLMClient(client: any): void {
    this.llmClient = client;
  }

  setClassifierModel(model: string): void {
    this.classifierModel = model;
  }

  setTimeoutMs(ms: number): void {
    this.timeoutMs = ms;
  }

  async decompose(input: string): Promise<DecompositionResult> {
    const trimmed = input.trim();

    for (const p of SINGLE_QUESTION_PATTERNS) {
      if (p.test(trimmed)) {
        const classification = await queryClassifier.classify(trimmed);
        return {
          original: trimmed,
          subQuestions: [{ text: trimmed, classification, index: 0 }],
          isCompound: false,
          strategy: 'single',
        };
      }
    }

    const isCompound = this.detectCompound(trimmed);

    if (!isCompound) {
      const classification = await queryClassifier.classify(trimmed);
      return {
        original: trimmed,
        subQuestions: [{ text: trimmed, classification, index: 0 }],
        isCompound: false,
        strategy: 'single',
      };
    }

    const parts = this.splitCompound(trimmed);
    const subQuestions: SubQuestion[] = [];

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i].trim();
      if (!part || part.length < 3) continue;

      const classification = await queryClassifier.classify(part);
      subQuestions.push({ text: part, classification, index: i });
    }

    if (subQuestions.length <= 1) {
      // El regex no pudo separar la query compuesta: probamos con el
      // descomponedor LLM (antes era código muerto) antes de rendirnos.
      const llmResult = await this.tryLLMDecomposition(trimmed);
      if (llmResult) {
        const prunedLlm = this.filterRedundantSubQuestions(llmResult.subQuestions);
        if (prunedLlm.length !== llmResult.subQuestions.length) {
          logger.info('subquestion_decomposer', `Deduplizadas ${llmResult.subQuestions.length - prunedLlm.length} sub-preguntas del split LLM`);
        }
        if (prunedLlm.length > 1) {
          return { ...llmResult, subQuestions: prunedLlm };
        }
      }

      const classification = await queryClassifier.classify(trimmed);
      return {
        original: trimmed,
        subQuestions: [{ text: trimmed, classification, index: 0 }],
        isCompound: false,
        strategy: 'single',
      };
    }

    const categories = [...new Set(subQuestions.map(sq => sq.classification.category))];
    const hasWebOrTool = categories.some(c => c === 'web' || c === 'tool');
    const allGeneral = categories.every(c => c === 'general');
    const strategy: DecompositionResult['strategy'] =
      allGeneral ? 'parallel' :
      hasWebOrTool ? 'sequential' :
      'parallel';

    // Dedupe: si una sub-pregunta es casi un subconjunto de otra (el split
    // falló y repitió el input completo en una parte), quedate con la parte
    // mejor cubierta: traía duplicados de tema en el merge final.
    const pruned = this.filterRedundantSubQuestions(subQuestions);
    if (pruned.length !== subQuestions.length) {
      logger.info('subquestion_decomposer', `Deduplizadas ${subQuestions.length - pruned.length} sub-preguntas redundantes`);
    }
    if (pruned.length === 1) {
      return {
        original: trimmed,
        subQuestions: pruned,
        isCompound: false,
        strategy: 'single',
      };
    }

    logger.info('subquestion_decomposer', `Compound query detected: "${trimmed.slice(0, 80)}" → ${pruned.length} sub-questions (${strategy})`);

    return {
      original: trimmed,
      subQuestions: pruned,
      isCompound: true,
      strategy,
    };
  }

  /**
   * Quita sub-preguntas cuyo contenido ya está (≈75% de tokens) dentro de
   * otra sub-pregunta más rica. Ej: ["cuanto es sqrt(196) y tradu x",
   * "tradu x"] → solo queda la primera que ya cubre el tpunto.
   */
  private filterRedundantSubQuestions(subs: SubQuestion[]): SubQuestion[] {
    if (subs.length < 2) return subs;
    const tokenize = (t: string) =>
      new Set(
        t.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')
          .replace(/[^a-z0-9\s]/g, ' ').split(/\s+/).filter(w => w.length > 2),
      );
    const tokenized = subs.map(s => tokenize(s.text));
    return subs.filter((_, i) => {
      const a = tokenized[i];
      if (!a || a.size === 0) return true;
      return !tokenized.some((b, j) => {
        if (i === j || b.size <= a.size) return false;
        let covered = 0;
        for (const t of a) if (b.has(t)) covered++;
        return covered / a.size >= 0.75;
      });
    });
  }

  private detectCompound(input: string): boolean {
    const questionMarkCount = (input.match(/\?/g) || []).length;
    if (questionMarkCount > 1) return true;

    for (const p of COMPOUND_INDICATORS) {
      if (p.test(input)) return true;
    }

    return false;
  }

  private splitCompound(input: string): string[] {
    let parts: string[] = [input];

    for (const pattern of SPLIT_PATTERNS) {
      const newParts: string[] = [];
      for (const part of parts) {
        const split = part.split(pattern);
        if (split.length > 1) {
          newParts.push(...split.filter(s => s.trim().length > 0));
        } else {
          newParts.push(part);
        }
      }
      parts = newParts;
    }

    if (parts.length === 1 && (input.match(/\?/g) || []).length > 1) {
      parts = input.split(/\?/).map(p => p.trim()).filter(p => p.length > 0);
      parts = parts.map(p => p.endsWith('?') ? p : p + '?');
    }

    parts = parts.map(p => {
      p = p.trim();
      if (!p.includes('?')) p = p + '?';
      return p;
    });

    return parts;
  }

  async decomposeWithLLM(input: string): Promise<DecompositionResult> {
    const llmResult = await this.tryLLMDecomposition(input);
    return llmResult || this.decompose(input);
  }

  private async tryLLMDecomposition(input: string): Promise<DecompositionResult | null> {
    if (!this.llmClient) {
      return null;
    }

    if (!this.detectCompound(input)) {
      return null;
    }

    try {
      const axios = (await import('axios')).default;
      const apiKey = process.env.OPENAI_API_KEY || '';
      const baseUrl = process.env.OPENAI_BASE_URL || 'https://integrate.api.nvidia.com/v1';

      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), this.timeoutMs);

      const response = await axios.post(
        `${baseUrl}/chat/completions`,
        {
          model: this.classifierModel,
          messages: [
            {
              role: 'system',
              content: `Dividí la consulta del usuario en sub-preguntas independientes. Respondé SOLO con un JSON array de strings, sin explicación.
Ejemplo: "¿Cómo está el clima en Mendoza y a cuánto está el dólar?" → ["¿Cómo está el clima en Mendoza?", "¿A cuánto está el dólar?"]
Si la consulta no es compuesta, respondé con un array de un solo elemento: ["consulta original"]`,
            },
            { role: 'user', content: input },
          ],
          temperature: 0.1,
          max_tokens: parseInt(process.env.DECOMPOSER_MAX_TOKENS || '1200', 10),
          ...(process.env.DECOMPOSER_REASONING_EFFORT
            ? { reasoning_effort: process.env.DECOMPOSER_REASONING_EFFORT }
            : {}),
        },
        {
          headers: {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json',
          },
          signal: controller.signal,
          timeout: this.timeoutMs,
        }
      );

      clearTimeout(timer);

      const raw = (response.data?.choices?.[0]?.message?.content || '').trim();
      const jsonMatch = raw.match(/\[[\s\S]*\]/);
      if (!jsonMatch) {
        logger.warn('subquestion_decomposer', `LLM decomposition returned invalid format: "${raw.slice(0, 100)}"`);
        return null;
      }

      const subTexts: string[] = JSON.parse(jsonMatch[0]);
      if (!Array.isArray(subTexts) || subTexts.length === 0) {
        return null;
      }

      if (subTexts.length === 1) {
        const classification = await queryClassifier.classify(subTexts[0]);
        return {
          original: input,
          subQuestions: [{ text: subTexts[0], classification, index: 0 }],
          isCompound: false,
          strategy: 'single',
        };
      }

      const subQuestions: SubQuestion[] = [];
      for (let i = 0; i < subTexts.length; i++) {
        const text = subTexts[i].trim();
        if (!text || text.length < 3) continue;
        const classification = await queryClassifier.classify(text);
        subQuestions.push({ text, classification, index: i });
      }

      if (subQuestions.length === 0) {
        return null;
      }

      const categories = [...new Set(subQuestions.map(sq => sq.classification.category))];
      const strategy: DecompositionResult['strategy'] =
        categories.every(c => c === 'general') ? 'parallel' :
        categories.some(c => c === 'web' || c === 'tool') ? 'sequential' :
        'parallel';

      logger.info('subquestion_decomposer', `LLM decomposition: "${input.slice(0, 80)}" → ${subQuestions.length} sub-questions (${strategy})`);

      return {
        original: input,
        subQuestions,
        isCompound: true,
        strategy,
      };
    } catch (err) {
      logger.warn('subquestion_decomposer', `LLM decomposition failed: ${err}`);
      return null;
    }
  }
}

export const subQuestionDecomposer = SubQuestionDecomposer.getInstance();
