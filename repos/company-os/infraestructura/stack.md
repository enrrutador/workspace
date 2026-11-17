# Stack estándar de la empresa

> Lo que usamos por defecto para construir productos. Elegido con tres criterios:
> **costo $0** (open-source o planes gratuitos), **madurez** (tecnología probada,
> no experimentos) y **una sola base de conocimiento** (los agentes aprenden un
> stack, no cinco).

## Web

| Capa | Estándar | Alternativas aceptadas |
|---|---|---|
| Backend | Python + FastAPI | Node.js + Express (si el producto lo justifica) |
| Frontend | React + TypeScript (Vite) | — |
| Base de datos | PostgreSQL | DuckDB (analítica local), SQLite (prototipos) |
| Tiempo real | WebSockets (FastAPI) / SSE | — |

## Mobile

| Capa | Estándar | Alternativas aceptadas |
|---|---|---|
| Apps iOS/Android | React Native (una base de código) | Flutter (si el producto lo justifica) |

## Datos

| Capa | Estándar |
|---|---|
| Pipelines | Python (orquestación simple con cron/scheduler; Airflow solo si el volumen lo pide) |
| Almacén | PostgreSQL (operacional) + DuckDB (analítica) |
| Formatos | Parquet para intercambio, JSON para APIs |

## ML / IA

| Capa | Estándar |
|---|---|
| Entrenamiento | Python + PyTorch + HuggingFace |
| Inferencia local | Ollama / vLLM |
| LLMs en producto | Vía LiteLLM proxy (única puerta de salida) |
| Evaluación | Conjuntos de prueba versionados + métricas definidas antes de entrenar |

## Infraestructura

| Capa | Estándar |
|---|---|
| Contenedores | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| Observabilidad | Langfuse (agentes) + tableros propios (productos) |

## Reglas

1. **El estándar es el default, no una cárcel**: un producto puede desviarse con propuesta escrita del Arquitecto y aprobación de Fabian.
2. **Nada pago sin aprobación**: cualquier servicio con costo entra por la compuerta de Fabian, aunque esté en esta tabla como alternativa.
3. **Un stack por producto**: no mezclar alternativas dentro del mismo producto sin justificación.
4. **Actualizaciones**: el Arquitecto propone cambios al stack; Fabian aprueba. La tabla vive acá, no en la memoria de cada agente.
