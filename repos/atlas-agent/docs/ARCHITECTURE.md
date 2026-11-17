# Atlas Agent v4.2 — Architecture

## Overview

Atlas is a modular AI agent built around three core pillars:

- **Brain** — Executor: classifies requests, runs skills, schedules work
- **Forge** — Decision engine and autonomous mission runner
- **Shield** — Trust policy, tool permissions, path guard and monitoring

```
User → Interface → Brain → (simple) → Arms (execute)
                        → (complex) → TrustGate → Forge → decide
                                                 ↗ proceed    → Brain executes
                                                 ↗ forge      → Forge reasons
                                                 ↗ autonomous → runs independently
                                                 ↗ propose    → needs user approval
```

## Module Structure

```
src/
├── main.ts                    # Entry point, initializes all modules
├── common/
│   ├── types.ts               # Shared interfaces (Operation, Skill, Message, etc.)
│   ├── logger.ts              # Logger singleton with EventEmitter for TUI
│   ├── paths.ts               # DATA_DIR-aware path helper
│   └── utils.ts               # generateId, hashString, delay, etc.
├── memory/
│   ├── atlas_db.ts            # SQLite via sql.js (WASM), lifecycle flush
│   ├── memory_store.ts        # CRUD on memories table
│   ├── session_db.ts          # Chat session persistence (30-day prune)
│   ├── qmd_memory.ts          # Daily markdown logs + optional vector index
│   ├── rag.ts                 # Codebase indexing into memory
│   └── index.ts
├── shield/
│   ├── trust_ladder.ts        # 5 autonomy levels + risk classification
│   ├── trust_gate.ts          # Brain↔Forge gate
│   ├── tool_guardian.ts       # Tool access control per trust level
│   ├── path_guard.ts          # File sandbox + secret-file protection
│   └── monitor.ts             # Error tracking + admin alerts
├── arms/
│   ├── tools/                 # terminal, file_manager, git, web, vision, audio…
│   ├── bridge/                # Python JSON-RPC bridge (stdin/stdout)
│   └── index.ts
├── brain/
│   ├── skills.ts              # Skill registry & execution
│   ├── task_handler.ts        # Processes user requests
│   ├── task_planner.ts        # Multi-step plan creation & execution
│   ├── scheduler.ts           # Time-based task scheduling
│   ├── message_queue.ts       # Priority-based async message processing
│   ├── context_compressor.ts  # Token-aware context reduction
│   ├── idle_builder.ts        # Autonomous task generation when idle
│   ├── query_classifier.ts    # Regex + LLM query classification
│   ├── confidence_router.ts   # Source routing by confidence
│   ├── source_agents.ts       # 6 specialized source agents
│   ├── subquestion_decomposer.ts
│   ├── multi_agent_orchestrator.ts
│   ├── semantic_cache.ts
│   └── feedback_loop.ts
├── forge/
│   ├── core/                  # gate, decision, context, reasoner, autonomous
│   ├── memory/                # past decisions and patterns
│   ├── missions/              # 10-step cognitive cycle, persistence, resume
│   ├── proposals/             # proposal lifecycle (pending→approved/rejected)
│   └── skills/auto_generator.ts
└── interfaces/
    ├── cli.ts                 # Terminal CLI
    ├── telegram/bot.ts        # Telegram bot (admin-only)
    ├── tui/logs_panel.ts      # Real-time log viewer
    └── dashboard.ts           # System health overview

tests/                         # node:test + tsx (no external test framework)
legacy/skills/                 # old experiments, NOT built or loaded
```

## Trust Levels

Configured with `ATLAS_TRUST_LEVEL` (default `3`).

| Level | Name | Low | Medium | High | Critical |
|-------|------|-----|--------|------|----------|
| 1 | Cautious | ✓ | ✗ | ✗ | ✗ |
| 2 | Safe | ✓ | ✓ | ✗ | ✗ |
| 3 | Trusted | ✓ | ✓ | ✓ | ✗ |
| 4 | Autonomous | ✓ | ✓ | ✓ | ✓ |
| 5 | Night Shift | ✓ | ✓ | ✓ | ✓ |

`classifyOperation()` assigns risk from the tool name or from the task text
(delete/push/deploy/credential keywords raise the risk). Operations above the
current level are returned as `propose` by `TrustGate`; `ToolGuardian` blocks
the corresponding tools before they execute.

## Security model

- **Terminal** (`src/arms/tools/terminal.ts`): splits the command into
  independent segments and blocks privilege escalation, disk/format commands,
  root/home deletion, fork bombs, piping downloads into interpreters,
  `eval`, force-push, and redirection into system directories. Shell wrappers
  (`bash -c`) and `$(...)` substitutions are inspected recursively.
  `ATLAS_ALLOW_DANGEROUS=true` disables these checks (not recommended).
- **Files** (`src/shield/path_guard.ts`): reads/writes/deletes are limited to
  `process.cwd()` and the OS temp dir by default. Override with
  `ATLAS_ALLOWED_ROOTS` (path-delimiter or comma separated). Secret files
  (`.env*`, `.ssh`, `.aws`, `.git`, keys, certificates, credentials) are always
  rejected. Symlinks are resolved before the check.
- **Tools** (`src/shield/tool_guardian.ts`): every tool is gated by the trust
  ladder.
- **Telegram**: only responds to `ADMIN_CHAT_ID` when it is set.

This is defense in depth, not a sandbox. Run Atlas with the least privileges
possible and do not expose the Telegram bot to untrusted users.

## Data layout

All runtime state lives under `DATA_DIR` (default `./data`, also accepts
`ATLAS_DATA_DIR`):

```
data/
├── atlas.db
├── logs/
├── missions/
├── proposals.json
├── downloads/
└── generated_skills/
```

`workspace/memory/*.md` is optional personal knowledge read at startup.

## Cross-platform support

- **macOS/Linux**: `python3`, `wmctrl`/`xdotool` for desktop automation
- **Windows**: `python`, `pygetwindow`
- **SQLite**: sql.js (WASM) — no native compilation
- **Bridge**: JSON-RPC over stdin/stdout

## Requirements

- Node.js >= 20
- Python 3.x (optional, desktop automation bridge)
- Optional: `vectra` for vector search (not installed by default)

## Tests

`npm test` runs `tests/*.test.ts` with Node's built-in test runner through
`tsx`. `npm run test:e2e` runs the live classifier script and requires an API
key.
