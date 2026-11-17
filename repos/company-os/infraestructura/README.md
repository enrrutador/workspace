# Infraestructura — pila a costo $0

> Principio: **pagamos con tiempo de ingeniería, no con suscripciones.** Cada servicio pago que se evita es complejidad que asumimos a cambio de independencia y costo cero.

## La pila

| Capa | Elección | Por qué |
|---|---|---|
| Modelos | De código abierto locales (Ollama/vLLM: Qwen, Llama) + planes gratuitos | $0. Detalle en [modelos.md](modelos.md) |
| Orquestación | LangGraph (Python) | Código abierto; auditable, puntos de control, human-in-the-loop nativo |
| Integraciones | MCP | Estándar abierto; es además nuestra tesis (empresa interoperable). Detalle en [mcp.md](mcp.md) |
| Gateway y presupuestos | LiteLLM proxy (autohospedado) | Techos por solicitud/sesión/clave, cortacircuitos; la política de gasto vive acá, no en el código del agente |
| Observabilidad | Langfuse (autohospedado) | Código abierto; gratis total si se auto-hospeda |
| Aprobaciones | Bot propio (Telegram/correo) | Aprobar/rechazar desde el celular lo irreversible, sin costo |
| Identidad | 1 identidad no-humana por agente | Permisos mínimos, tokens de corta vida, dueño nombrado (Fabian) |
| Hosting | Hardware propio o nube con plan gratuito | $0; escalar solo cuando un agente pague su propia infra con el valor que genera |

## Costo total: $0

Toda la pila es de código abierto y autohospedada. El único "costo" es tiempo de ingeniería y el hardware que Fabian ya tenga. Guía paso a paso para levantar todo: [setup.md](setup.md).

## Regla de oro sobre pagos

**Ningún agente incorpora un servicio pago sin que el valor que genera lo justifique y Fabian lo apruebe.** Esta regla también vale para los humanos (Fabian): si un día un producto necesita un servicio pago, entra por la misma compuerta — valor demostrado primero, aprobación después. El LiteLLM proxy es el guardián: aunque el costo sea 0 hoy, los techos y cuotas ya están configurados, así que si un día hay gasto, está controlado desde el día uno.

## Relación con el resto del repo

- La infraestructura es **compartida por todos los productos**: cada producto nuevo nace "listo para agentes" sobre MCP + gateway + observabilidad. Esa es la ventaja estructural frente a una empresa tradicional.
- El pipeline de producto asume esta infra disponible (ver `../pipeline/`).
- Las fichas de producto viven en `../productos/`.

## Ya implementado (funcional)

- **Conector de modelos** ([litellm/](litellm/)): proxy LiteLLM como puerta única a los
  proveedores. Fabian pone su API key y elige los modelos en el `.env`; los agentes
  no tocan keys. Guía de 5 minutos en [litellm/README.md](litellm/README.md).
- **Runtime de agentes** ([../runtime/](../runtime/)): los 26 agentes ejecutables —
  cada uno combina su ficha + su SKILL.md en el prompt del sistema y corre contra
  el proxy. CLI: `python3 ejecutar.py <agente> "<tarea>"`. Todo queda en
  `runtime/registro/auditoria.jsonl`.
