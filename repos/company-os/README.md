# company-os — La empresa como código

La empresa de Fabian: una compañía de tecnología multi-producto estilo Meta, operada 100% por agentes de IA con Fabian como único humano. Este repositorio es su definición operativa: visión, reglas, organigrama, infraestructura y pipeline de producto — todo versionado como código.

## Visión (en 5 líneas)

1. **Una empresa, muchos productos.** Como Meta: el crecimiento viene de construir y adquirir productos, no de apostar todo a uno solo.
2. **La tesis unificadora es la conexión entre productos tecnológicos.** Cada producto nace interoperable: el ecosistema se vuelve la ventaja.
3. **El plantel son agentes de IA.** 26 agentes con roles definidos ejecutan cada función; Fabian dirige y aprueba lo irreversible.
4. **Costo total: $0.** Todo de código abierto, autohospedado, modelos locales o planes gratuitos. Ningún agente incorpora un servicio pago sin que el valor lo justifique y Fabian lo apruebe.
5. **Se empieza chico y se escala lo medido.** Un agente, una función, una tarea medible — y se escala solo lo que ya funciona y está auditado.

## Tesis

[La tesis en profundidad](empresa/vision.md): los productos tecnológicos se conectan entre sí, y una empresa que diseña cada producto como parte de un ecosistema interoperable (MCP como sistema nervioso) gana una ventaja estructural frente a quienes construyen productos aislados.

## Modelo

Multi-producto estilo Meta: una sola empresa, muchos productos que comparten infra (modelos, gateway, observabilidad, aprobaciones). Los productos compiten por capacidad de agentes y atención de Fabian; un mapa de dependencias obliga a considerar la red antes de matar un producto. Para construir, adquirir o matar productos existe el [pipeline de compuertas por etapa](pipeline/README.md) (detalle en el [diseño operativo v1](empresa/diseno-operativo-v1.md)).

## Mapa del repo

- `empresa/` — estrategia y gobierno: visión, tesis, restricciones duras y organigrama.
- `agentes/` — fichas de cada agente (rol, permisos, autonomía, manual operativo) por área.
- `infraestructura/` — pila tecnológica: modelos, orquestación, gateway, observabilidad, aprobaciones.
- `pipeline/` — [pipeline de producto con compuertas por etapa](pipeline/README.md): etapas, compuertas y artefactos por traspaso.
- `gobernanza/` — reglas transversales: aprobaciones, auditoría, autonomía graduada e identidades.
- `productos/` — portafolio de productos del ecosistema.
- `legal/` — base legal: SAS, contratos, cumplimiento.

## Estado

Borrador v1 — 2026-10-07. Fuente de verdad: el [diseño operativo v1](empresa/diseno-operativo-v1.md) (borrador en revisión con Fabian).

## Reglas de oro

- **Todo queda registrado**: sin registro, no existe.
- **El presupuesto vive en el gateway**, no en el código del agente.
- **Autonomía graduada por riesgo**: autónomo lo reversible, on-the-loop lo medio, in-the-loop lo irreversible (aprobación previa de Fabian).
- **Máxima restricción al lanzar**; más autonomía solo tras ~30 días con tasa de aprobación alta.
