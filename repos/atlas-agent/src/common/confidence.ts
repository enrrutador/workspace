/**
 * Umbrales y niveles de confianza centralizados.
 * Antes estaba el 0.3 / 0.5 / 0.85 / 0.9 / 0.95 repartido por el pipeline
 * sin significado común. Criterios con los modelos del catálogo NVIDIA
 * (stepfun-ai/step-5-preview / meta/muse-glimmer-30b en vivo):
 * - tool ejecutada con archivo real en disco → 0.85-0.95 según verificación.
 * - declinaciones honestas (no encontré el archivo) → 0.2-0.3: son verdad,
 *   pero no resolvieron la tarea.
 */

/** Aceptación del plan directo del orquestador (antes 0.6 via env). */
export const CONFIDENCE_THRESHOLD = parseFloat(process.env.CONFIDENCE_THRESHOLD || '0.6');

/**
 * Calibración observada en sesiones live (s9-s15, step-5-preview/muse-30b):
 * - skill determinístico ejecutado (archivo real en disco, resultado exacto)
 *   → 0.9 es razonable; CONFIIDENCE_THRESHOLD 0.6 nunca lo dejó caer mal.
 * - declinaciones honestas 0.2/0.3 → correctas: entran como fallback pero no
 *   pasan threshold (no se cachean ni sintetizan como éxito).
 * - síntesis de tool verificada 0.85 ok: por encima de threshold pero por
 *   debajo de un skill directo.
 * No se cambiaron los valores: los live runs no mostraron falsos positivos
 * que ameriten recalibrar. Ajustes finos → envs, sin recompilar.
 */
export const CONF = {
  /** Skill ejecutado directo con match fuerte del input. */
  SKILL_DIRECT: 0.9,
  /** Síntesis LLM a partir de un tool VERIFICADO (exit real). */
  TOOL_SYNTHESIS: 0.85,
  /** LLM puro conversacional (sin tools). */
  LLM_PLAIN: 0.9,
  /** Mínimo de match del skill_matcher para ruta skill_direct. */
  SKILL_MATCH_MIN: 0.15,
  /** Fallo total de tools: salida determinística con errores reales. */
  DETERMINISTIC_FAILURE: 0.3,
  /** Resultado de búsqueda web usada para responder. */
  WEB_RESULTS: 0.7,
  /** Fallback sintético de web (sin resultados reales). */
  WEB_SYNTHESIS: 0.3,
  /** Hecho guardado en memoria. */
  MEMORY_STORED: 0.95,
  /** Recall de memoria con resultados. */
  MEMORY_RECALL: 0.85,
  /** Declinación honesta / recurso no disponible. */
  UNAVAILABLE: 0.2,
  /** Filtrado de planes débiles en el orquestador multi-agent. */
  PLAN_MIN: 0.3,
  /** Aceptar resultado secuencial de un source del plan. */
  SEQUENTIAL_ACCEPT: 0.5,
} as const;
