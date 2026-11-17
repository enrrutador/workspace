# Atlas Agent

Agente AI modular en TypeScript con motor de decisiones **Forge**, ejecutor **Brain** y sistema de confianza **Shield**. Corre en CLI y Telegram, persiste memoria en SQLite (WASM) y puede ejecutar misiones autónomas de investigación con un ciclo cognitivo de 10 pasos.

> Estado: **alpha / uso personal**. No es un sandbox: ejecuta herramientas reales (shell, archivos, git, web). Leé la sección de seguridad antes de exponerlo.

## Features

- **21 skills**: shell, archivos, git, web search/scrape/download, visión, audio, código, traducción, memoria y más, con métricas de uso (`/skills [✓n ✗n]`).
- **Router de fuentes** con clasificación regex + LLM, 6 agentes especializados, descomposición de preguntas compuestas, caché semántica y feedback loop.
- **Multi-hop de tools con salida determinística**: si todas las herramientas fallan, la respuesta lista los errores reales — nunca inventa éxitos.
- **Forge Missions**: investigación autónoma en background con 10 pasos por idea, pausa/reanudación y notificaciones.
- **Shield**: 5 niveles de confianza, control de herramientas y sandbox de rutas.
- **Memoria persistente**: SQLite, sesiones, RAG del código, curated memory (`MEMORY.md`) y logs diarios.
- **Interfaces**: CLI (con spinner de progreso), Telegram (solo admin) y dashboard de estado.

## Arquitectura

```
User → CLI / Telegram → Brain → Arms (tools)
                             ↘ TrustGate → Forge → proceed | forge | autonomous | propose
```

Detalle completo en [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) y [`docs/FORGE_MISSIONS.md`](docs/FORGE_MISSIONS.md).

## Requisitos

- Node.js >= 20
- npm
- Python 3 (opcional, automatización de escritorio)
- API key compatible con OpenAI (por defecto NVIDIA NIM)

## Quickstart

```bash
npm ci
cp config/.env.example .env
# editá .env y poné OPENAI_API_KEY (y TELEGRAM_BOT_TOKEN si usás Telegram)

npm run build
npm start          # CLI
# o: node dist/main.js telegram
# o: node dist/main.js both
```

Desarrollo con recarga:

```bash
npm run dev
```

## Configuración

| Variable | Descripción | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | API key del proveedor LLM | — |
| `OPENAI_BASE_URL` | Endpoint compatible OpenAI | `https://integrate.api.nvidia.com/v1` |
| `MODEL_NAME` | Modelo principal (verificado con `stepfun-ai/step-5-preview` y `meta/muse-glimmer-30b`) | `stepfun-ai/step-5-preview` |
| `CLASSIFIER_MODEL` | Modelo del clasificador/descomponedor (si difiere) | igual a `MODEL_NAME` |
| `CLASSIFIER_MAX_TOKENS` / `CLASSIFIER_TIMEOUT_MS` | Presupuesto y timeout del clasificador (models reasoning queman cientos de tokens antes de responder) | `256` / `3000` |
| `CLASSIFIER_REASONING_EFFORT` / `DECOMPOSER_REASONING_EFFORT` | `low` baja el thinking de clasificación/descomposición (si el modelo lo soporta) | — |
| `ATLAS_LLM_TIMEOUT_MS` | Timeout HTTP de cada request al LLM | `120000` |
| `ATLAS_SOURCE_TIMEOUT_MS` | Timeout por source en el orquestador | `60000` |
| `DECOMPOSER_MAX_TOKENS` | Presupuesto del descomponedor de compuestas | `1200` |
| `TELEGRAM_BOT_TOKEN` | Token del bot | — |
| `ADMIN_CHAT_ID` | Chat autorizado de Telegram | `0` |
| `DATA_DIR` / `ATLAS_DATA_DIR` | Estado runtime (DB, logs, misiones) | `./data` |
| `ATLAS_TRUST_LEVEL` | Nivel de confianza 1–5 | `3` |
| `ATLAS_ALLOWED_ROOTS` | Raíces permitidas para archivos (separadas por `:` o `,`) | cwd + temp |
| `ATLAS_ALLOW_DANGEROUS` | Desactiva bloqueos del terminal | `false` |
| `CONFIDENCE_THRESHOLD` | Umbral del router de fuentes | `0.6` |

## Niveles de confianza

| Nivel | Nombre | Comportamiento |
|-------|--------|----------------|
| 1 | Cautious | Solo lectura; el resto requiere aprobación |
| 2 | Safe | Lectura y escritura; shell/git/delete bloqueados |
| 3 | Trusted | Todo excepto operaciones críticas (default) |
| 4 | Autonomous | Todo, incluidas operaciones críticas |
| 5 | Night Shift | Autonomía total |

Las operaciones que superan el nivel actual se convierten en propuestas (`/approve`, `/reject`).

## Seguridad

- El terminal bloquea escalada de privilegios, borrado de `/` o `$HOME`, `mkfs`/`dd`, fork bombs, `curl | sh`, `eval`, force-push y redirecciones a directorios del sistema. Revisa también `bash -c` y `$(...)`.
- Las herramientas de archivos están limitadas a `cwd` + temp y rechazan `.env*`, `.ssh`, `.aws`, `.git`, claves y certificados. Los symlinks se resuelven antes de validar.
- Telegram solo atiende a `ADMIN_CHAT_ID` cuando está configurado.
- **No es un sandbox.** Para producción, corré Atlas en un contenedor/usuario sin privilegios y con secretos fuera del alcance del proceso.

## Tests

```bash
npm test            # 20 tests: trust, seguridad, path guard, persistencia,
                    # pipeline con LLM mock, memoria y RAG
npm run typecheck   # src + tests
npm run build
```

CI: [`.github/workflows/ci.yml`](.github/workflows/ci.yml) corre typecheck, tests y build en Node 20 y 22.

## Estructura

```
src/          código compilado a dist/
tests/        node:test + tsx
docs/         arquitectura, misiones y changelog
config/       .env.example
legacy/       skills viejas, NO se compilan ni cargan
```

## Licencia

MIT — ver [`LICENSE`](LICENSE).
