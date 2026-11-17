# ARCA-2 consolidated architecture

## Thesis

ARCA is a verifiable cognitive microkernel. A task is compiled into an explicit cognitive record. A budget-aware executive selects a specialist, records its operations, verifies the result when possible, and preserves evidence. HDC, neural models and web retrieval are optional organs, never universal representations.

## Resident M0

`Executive` owns cadence, routing and budgets. `Blackboard` accepts typed events. `Expediente` stores objective, assertions, constraints, hypotheses, evidence, plan, result, budget and trace in JSON. Only one reasoner runs for each M0 task.

## Cognitive cycle

1. Accept input and create an expediente.
2. Classify the requested operation.
3. Check time and memory budgets.
4. Select the registered specialist for the task kind.
5. Execute and append trace events.
6. Verify success against the specialist contract.
7. Serialize the result and telemetry.
8. Stop, or schedule another bounded cycle in later milestones.

## Representations

Canonical state is typed and symbolic. Assertions support provenance, confidence and timestamps. Hypervectors may later provide compact approximate indexing, but never replace the canonical evidence record.

## Reasoning portfolio

M0 contains forward-chaining Horn rules, A* over finite grids, and a safe AST arithmetic evaluator. Future operators can include Datalog engines, SAT/SMT, HTN planning, graph algorithms, document retrieval and small perception models. Each implements the same `Reasoner` protocol.

## Memory

M0 serializes expedientes and keeps events in memory. Planned stores are episodic append-only logs, versioned semantic assertions, compressed source documents and sandboxed procedures. Contradictions coexist until resolved by evidence; old claims are not silently erased.

## Learning

The first adaptive component will be a contextual bandit keyed by `(task class, operator)`. Reward combines correctness, information gain, latency and memory cost. Learned procedures remain quarantined until tests pass.

## Security

External data is evidence, never executable instruction. Future web and tool modules must isolate downloads, retain original sources, separate quoted instructions from control messages, and execute only allowlisted operators.

## Resource policy

M0 targets 256 MB peak RSS. The executive samples process RSS before and after execution and rejects work after deadline or over-budget observations. Measurements are telemetry, not proof of universal memory behavior: allocator, OS and platform affect RSS.

## Milestones

- M0: explicit state, kernel, three reasoners, 100-case benchmark.
- M1: persistent evidence memory, versioned assertions, safe web acquisition.
- M2: language compiler and ambiguity handling.
- M3: pairwise routing bandit and procedural learning.
- M4: optional local surface model and multimodal specialists.

## Agent backend (M5, current)

The OpenCode-compatible backend (`arca/agent_api.py`) composes answers
extractively instead of generating text:

1. Internal agent templates (session state, titling) and social phrases get
   deterministic localized replies — instant, no memory pollution.
2. Context intents (time/date) resolve from the local system clock without
   asking the user where they are.
3. Active-topic continuations ("contame más", "¿y cuándo...?") are served from
   the local evidence graph, offline and instant; they must not introduce a
   brand-new subject (else treated as a fresh question).
4. Content questions resolve through a concept gate: definitional / "cómo
   funciona" go web-first, others try the local cache; evidence must carry the
   query's concept core in one defining sentence, with tolerance to typos and
   accents. Exact-title documents vouch for borderline cases.
5. Ambiguity is handled actively: multiple senses (embarcación vs futbolista)
   trigger a clarifying question; the chosen sense is kept in the session.
6. Every fetched page is mined into an evidence graph
   (`concepts`/`triples`/aspect-tagged passages), persisted in the same SQLite
   file and queried for follow-ups; `arca index` bulk-mines cached documents.
   Concepts carry hyperdimensional vectors so relatedness is measured
   semantically, not just lexically.
7. A bounded A* planner (`arca/planner.py`) fills discourse slots
   (definition → types → uses → mechanism → history) with real, source-cited
   sentences joined by connectors — generation as planning, never invention.
8. Without sufficient evidence ARCA asks for reformulation; it never invents.

Resource envelope measured on development hardware: ~40 MB RSS server process,
sub-MB SQLite after dozens of sessions, fixed ~2 MB model file. The evidence
graph grows toward the disk budget (up to 16 GB) as ARCA reads, bounded by
`--max-triples` with rotating consistent SQLite backups at server start.
