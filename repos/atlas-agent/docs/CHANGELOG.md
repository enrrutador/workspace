# Atlas Agent — Changelog

## [4.4.0] — 2026-11-06

### Streaming del reasoning, guard endurecido y 26 tests

#### Streaming SSE

- **`LLMClient.chatCompletion` streamea** (`ATLAS_LLM_STREAM=0` para opt-out): deltas de `reasoning_content`/`content` vía un observer (`setStreamObserver`); cualquier error de stream hace fallback transparente al modo sin stream. Retry interno si el stream termina sin content (reasoning quemó el presupuesto).
- **CLI**: el spinner pasa a `🧠` y muestra los últimos 60 chars del reasoning en dim mientras piensa el modelo — ver lo que raciocina en vivo en vez de 10-60s de silencio. Verificado live (s15): respuesta correcta en 10.4s sin fallback.

#### Terminal guard

- Nuevos bloqueos: `chattr` (atributos de filesystem) y wrappers de emuladores de terminal con `sudo`/`su`/`doas` (`xterm -e sudo id`).
- Extensión de tests de seguridad: wrappers anidados con env-prefix, `curl|sh`/`wget|sh` dentro de `$()` vía `sh -lc`, kill de PID 1, mkfs/dd, redirects a /etc, fork bombs. Casos permitidos explícitos: correr scripts propios (`sh /tmp/atlas_install.sh`), downloads con `-o`.

#### Tests y matcher

- **26 tests** (20 + 6 unitarios de brain): keywords de skill_matcher translate/git sin acento (`traducime`, `japones` — la strip de idioma usa `[a-záéíóúñü]+` porque `\w` no matchea acentos), frases de git completas (`git status` etc. — la palabra sola `git` score 3 < threshold 5), descomponedor con dedupe de sub-preguntas redundantes.
- Calibración de thresholds documentada en `src/common/confidence.ts` (sesiones live s9-s15: skill directo 0.9, síntesis 0.85, declinación honesta 0.2/0.3 — sin cambios de valores).

## [4.3.0] — 2026-11-05

### Pipeline blindado, UX de esperas largas y calibración con modelos reasoning

Trabajado en vivo contra el catálogo NVIDIA (`stepfun-ai/step-5-preview` y `meta/muse-glimmer-30b`, los únicos chat-usable de la cuenta).

#### Acción de tools con salida determinística

- **Multi-hop de tools (`runToolLoop`)**: hasta 3 intentos guiados por el LLM con nap ("Eso es una intención, no un resultado"), herramientas desconocidas/args inválidos con feedback al modelo, y **salida determinística si todas las tools fallan** (lista los errores reales; jamás acepta una síntesis que afirme éxito falso).
- **Detección de guardado en memoria**: `recordá que / acordate / anotame / guardame` (sin signos de pregunta) persiste vía `memory_store`.
- **Recall multi-fragmento**: "listá lo que sabés de mí: dónde trabajo y mi comida favorita" devuelve ambos hechos (fusiona consultas: segmentos, bigramas, stopwords).
- **Bug de producción**: skills que devuelven `void` en éxito (`save_file`) crasheaban `JSON.stringify(undefined).slice()` *después* de haber escrito el archivo — marcadas como fallidas. Fix: `stringifySkillResult`.
- **Bug math**: el sanitizer borraba las letras antes de reemplazar funciones → `sqrt(196)` evaluaba `(196)`. Ahora preserva solo funciones/constantes seguras; entran frases humanas (`raíz cuadrada de X`, `15% de Y` = `(15/100)*Y`) y keywords de match (`cuanto es`, `sqrt`, `raíz`).
- **Retry de content nulo**: los modelos reasoning a veces queman todo el presupuesto en `reasoning_content` y devuelven `content: null`; `LLMClient` reintenta antes de responder "No response".

#### Orquestación consolidada

- Un solo camino multi-agent en `task_handler` (eliminado el dual `USE_MULTI_AGENT`).
- `confidence_router` reducido a routing + `runToolLoop` (fuera `executeSource` y 6 handlers muertos, ~380 líneas).
- Umbrales centralizados en `src/common/confidence.ts` (`CONF.*`, `CONFIDENCE_THRESHOLD` via env).
- Timeout por source configurable: `ATLAS_SOURCE_TIMEOUT_MS` (default 60s; el default fijo de 30s mataba la ruta general con reasoning que tarda 30-60s).

#### UX y métricas

- **Spinner CLI**: `⠙ ⚡ pensando Ns` mientras procesa y `⚡ listo en Xs` al terminar (antes ~30s de silencio con reasoning).
- **Dedupe de compuestas**: sub-preguntas redundantes se descartan en el descomponedor (contenido ⊇ otro dentro) y frases repetidas en el merge de subrespuestas (solapamiento ≥ 60%).
- **Stats de tools en SQLite** (`kv: tool_stats`): se restauran al arrancar y se reflejan en `/skills` (`math_calculate [✓1 ✗0]`).

#### Clasificador / calibración offline first

- Cálculos y traducciones van a tool determinístico (ms vs LLM general con reasoning 30-60s y a veces vacío).
- `CLASSIFIER_MAX_TOKENS` (256 default; los reasoning no caben en 10) + `CLASSIFIER_TIMEOUT_MS` (3000).
- `CLASSIFIER_REASONING_EFFORT=low` / `DECOMPOSER_REASONING_EFFORT=low` (step-5-preview: 5.3s vs estado sin control) medido por curl.

#### Tests

- 20 tests: pipeline con **LLM mock** (tool fallida → recuperación real con archivo en disco, fallo total → mensaje determinístico, nudge ante intenciones sin tool-call), clasificador offline, memoria multi-fragmento, qmd_memory (primer hecho crítico→`MEMORY.md`, semantic→log diario) y RAG (mtimes en kv sin duplicar).

## [4.2.0] — 2026-10-31

### Hardening, build and test infrastructure

- **Build fixed**: added `@types/sql.js`; `npm run build` / `npm run typecheck` are green on Node >= 20.
- **Shield is real**: `TrustLadder` enforces 5 configurable levels (`ATLAS_TRUST_LEVEL`), `TrustGate` classifies task risk and proposes operations above the current level, and `ToolGuardian` blocks tools accordingly. `ForgeGate` now consults the trust gate before reasoning.
- **Terminal hardening**: commands are split into segments; privilege escalation, disk/format commands, root/home deletion, fork bombs, `curl | sh`, `eval`, force-push and system redirection are blocked. Shell wrappers and command substitutions are inspected recursively. Opt-out: `ATLAS_ALLOW_DANGEROUS=true`.
- **Path guard**: file reads/writes/deletes are limited to `ATLAS_ALLOWED_ROOTS` (default: cwd + temp) and secret files (`.env*`, `.ssh`, `.aws`, `.git`, keys, certificates) are rejected. Symlinks are resolved before validation. Downloads sanitize filenames and only accept http(s).
- **Persistence**: SQLite now flushes synchronously on `exit`, `SIGTERM`, `SIGINT` and `uncaughtException`; the save timer no longer keeps the process alive. `DATA_DIR`/`ATLAS_DATA_DIR` now applies to DB, logs, missions, proposals, downloads and generated skills.
- **Tests + CI**: 12 `node:test` tests covering trust levels, tool permissions, terminal guard, path guard and SIGTERM persistence; GitHub Actions workflow runs typecheck, tests and build on Node 20/22.
- **Docs and release hygiene**: README, MIT LICENSE, CI workflow, corrected architecture docs, version aligned with changelog, and legacy skills moved to `legacy/skills/` (not built or loaded).

## [4.1.0] — 2026-08-29

### Forge Missions — Motor de Misiones Autónomas

Forge ahora es un trabajador autónomo bajo demanda. Se activa solo cuando el usuario le confía una misión compleja y de ejecución prolongada, y trabaja en background sin interferir con el chat normal.

#### Nuevos módulos (`src/forge/missions/`)

- **forge_llm.ts**: cliente LLM ligero con retry, backoff y manejo de rate limits.
- **forge_runner.ts**: núcleo del motor. Ejecuta un ciclo cognitivo de 10 pasos por cada idea (MARCO → HIPÓTESIS → INVESTIGAR → CRITICAR → ANALIZAR → CUANTIFICAR → EVALUAR → SINTETIZAR → REGISTRAR → AUTO-REVISAR), con investigación real vía `webTool` (search + scrape).
- **mission_manager.ts**: una misión a la vez, persistencia y reanudación, parsing de lenguaje natural, mecanismo de pausa/espera de respuesta del usuario.

#### Funcionalidades

- **Disparador coloquial**: frases como *"forge, trabajá en 10 variantes de X"* detectadas en Telegram y CLI (no requiere comando).
- **Comando `/forge`**: lanzar (`/forge <meta>`), status, cancel, resume.
- **Notificaciones proactivas** por idea completada + resumen final con ranking.
- **Pausa-control**: si una idea tiene score bajo, Forge pregunta y espera; timeout configurable (`FORGE_QUESTION_TIMEOUT_MS`, default 30 min).
- **Persistencia**: `data/missions/<id>.json` (ignorado por git) con reanudación tras reinicio.
- **Independencia del chat**: la misión corre en background; el agente sigue respondiendo normalmente.

#### Integraciones

- `main.ts`: inicializa forgeRunner y missionManager con la config.
- `interfaces/telegram/bot.ts`: detección de misiones, `/forge`, routing de respuestas a Forge.
- `interfaces/cli.ts`: mismo comportamiento.
- `forge/core/forge_autonomous.ts`: sus métricas (`getActiveTaskCount`, `listTasks`) ahora reflejan el estado real de las misiones activas; visible en el dashboard.

## [4.0.0] — 2026-06-03

### Architecture Rebuild (Nuclear)

Complete restructure from monolithic Windows-only agent to modular cross-platform architecture.

#### New Modules

- **common/**: types.ts, logger.ts (EventEmitter for TUI), errors.ts, utils.ts
- **memory/**: atlas_db.ts (SQLite via sql.js WASM), memory_store.ts, session_db.ts, qmd_memory.ts, rag.ts, context_manager.ts
- **shield/**: trust_ladder.ts (5 levels), trust_gate.ts (Brain↔Forge gate), tool_guardian.ts, monitor.ts (error tracking + Telegram alerts)
- **arms/**: tools/ (browser, search, terminal, downloader, file_manager), bridge/ (Python bridge JSON-RPC), credentials/ (secure storage)
- **brain/**: skills.ts, task_handler.ts, task_planner.ts, scheduler.ts, message_queue.ts, context_compressor.ts, idle_builder.ts
- **forge/**: core/ (forge_gate, forge_decision, forge_context, forge_reasoner, forge_autonomous), memory/, proposals/, skills/auto_generator.ts
- **interfaces/**: telegram/bot.ts, tui/logs_panel.ts, cli.ts, dashboard.ts

#### Key Decisions

- Forge = neurona maestra: when Brain can't decide, Forge intervenes
- sql.js over better-sqlite3 (WASM, no native deps)
- Python Bridge: JSON-RPC over stdin/stdout (cross-platform)
- Trust Gate: hot gate between Brain and Forge with failure tracking
- Nuclear rebuild instead of file-by-file migration

#### Cross-Platform

- macOS: python3, pyobjc
- Linux: python3, wmctrl/xdotool
- Windows: python, pygetwindow

#### Removed

- All .cmd/.bat scripts
- All compiled .js/.d.ts/.map artifacts from src/
- Old OpenClaw/Hermes naming → Atlas terminology
- node_modules/ (needs fresh npm install)
- Old test files, vision scripts, build artifacts

#### Backup

- Pre-restructure backup: atlas_backup_v2.tar.gz
- Git commit: "BACKUP: Estado antes de reestructuracion total v3.0"

## [3.0.0] — Previous version (Windows-only, monolithic)
