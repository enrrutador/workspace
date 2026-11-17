# Modelos a costo $0 — estrategia

## La estrategia en una línea

**Local primero, plan gratuito como complemento, nada pago.** Los modelos de código abierto corriendo en hardware propio (vía Ollama o vLLM) hacen el trabajo pesado; los planes gratuitos de proveedores cubren picos o capacidades que lo local no da.

## Modelos locales (base del sistema)

Servidores de inferencia de código abierto:

- **Ollama** — la forma más simple de correr modelos locales: `ollama run` y listo. Ideal para empezar.
- **vLLM** — servidor de alto rendimiento (rendimiento, procesamiento por lotes, API compatible con OpenAI). Para cuando un agente necesita servir muchas solicitudes.

Familias de modelos a considerar (verificar las versiones vigentes al momento de instalar):

- **Qwen** (Alibaba) — buen equilibrio razonamiento/tamaño; suele rendir bien en tareas agénticas y uso de herramientas.
- **Llama** (Meta) — ecosistema amplio, muchas variantes cuantizadas.
- Otras familias de código abierto según el caso (Mistral, Gemma, DeepSeek, etc.).

### Cómo elegir el tamaño según la tarea y el hardware

Regla práctica: **el modelo más chico que resuelva la tarea de forma confiable.**

| Tarea | Tamaño orientativo |
|---|---|
| Clasificación, extracción de datos, respuestas con contexto dado | 3B–8B (rápido, barato en VRAM) |
| Razonamiento medio, redacción, resúmenes | 8B–14B |
| Tareas agénticas con herramientas, multi-paso | 14B–32B (o más, si el hardware lo permite) |
| Razonamiento pesado, planificación compleja | 32B–70B+ (solo si hay GPU con VRAM suficiente) |

Limitantes reales del hardware propio:

- **VRAM de GPU** manda: un modelo 8B cuantizado (Q4) necesita ~5–6 GB; un 32B, ~20 GB; un 70B, ~40 GB+.
- **Sin GPU dedicada**: modelos chicos (≤8B) en CPU son usables para tareas acotadas, pero lentos para agentes conversacionales.
- **Cuantización** (Q4_K_M y similares): reduce VRAM a costa de una pequeña pérdida de calidad; casi siempre vale la pena.

Medí siempre con *tu* hardware y *tus* tareas: una referencia de 10 casos reales vale más que cualquier tabla.

## Planes gratuitos como complemento

Los niveles gratuitos de proveedores de modelos sirven para:

- Capacidades que lo local no cubre bien (p. ej. ventanas de contexto muy grandes, ciertos modelos multimodales).
- Picos de demanda que exceden la GPU propia.
- Comparar calidad local vs. proveedor en una tarea concreta.

Sus límites (verificar vigentes en cada proveedor al momento de usar):

- **Cuotas mensuales/diarias** de solicitudes o tokens, que se agotan.
- **Límites de tasa** que frenan ráfagas.
- **Cambios unilaterales**: el proveedor puede recortar el plan gratuito en cualquier momento. Nada crítico puede depender solo de un plan gratuito.
- **Privacidad**: los datos salen de tu hardware. Nunca enviar datos de clientes o sensibles a un plan gratuito.

El gateway ([LiteLLM proxy](../README.md)) administra las cuotas de los planes gratuitos: techos por clave y por agente, para que un bucle no queme la cuota mensual en una tarde.

## Contrapartidas honestas

1. **Los modelos locales y free rinden menos que los modelos de punta** en tareas agénticas complejas (planificación larga, uso de herramientas encadenado, razonamiento abstracto). No es una opinión: es el estado del arte en 2026.
2. **El diseño operativo asume esta limitación**: por eso se priorizan **tareas acotadas** — un agente, una función, una tarea medible (ver piloto Conciliador/Control de Calidad en `../pipeline/`). Los modelos chicos rinden bien cuando el problema está bien delimitado.
3. **Cuándo se justifica un modelo más grande**: cuando la referencia de la tarea muestra que el modelo chico falla de forma sistemática *y* la tarea ya genera valor medido. Subir de tamaño es una decisión con evidencia, no por defecto.
4. **Cuándo se justificaría un modelo pago**: solo si el valor generado lo paga con margen claro *y* Fabian lo aprueba (regla de [README](README.md)). Hasta entonces, el techo es $0.

## Cómo el gateway enruta entre local y plan gratuito

El LiteLLM proxy autohospedado actúa como único punto de entrada de todos los agentes a los modelos:

1. **El agente nunca llama a un modelo directamente**: llama al proxy con un nombre lógico (p. ej. `agente-qa-rapido`, `agente-reconciler`).
2. **El proxy decide la ruta** según reglas configuradas: por defecto → modelo local (Ollama/vLLM); si el local no responde o la tarea lo requiere → plan gratuito (con cuota).
3. **Respaldo**: si el plan gratuito devuelve límite de tasa, el proxy reintenta en local o encola. Nada se pierde por un 429.
4. **Presupuestos**: techos por solicitud, por sesión y por clave viven en el proxy, no en el código del agente (principio del diseño operativo).
5. **Observabilidad**: cada llamada queda registrada y se puede ver en Langfuse: qué modelo se usó, cuánto costó (en tokens y en cuota), qué latencia tuvo.

Esto significa que **cambiar de modelo no requiere tocar ningún agente**: se cambia la configuración del proxy y todos los agentes migran. La estrategia de modelos es configuración, no código.
