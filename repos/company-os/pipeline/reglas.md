# Reglas de flujo del pipeline

Las reglas que hacen que el pipeline funcione en vez de ser un diagrama lindo.

## WIP máximo por etapa

Sin excepciones. El WIP limita el trabajo en curso para que los agentes no quemen capacidad en diez frentes a la vez.

| Etapa | WIP máximo | Por qué |
|---|---|---|
| 0. Búsqueda | Sin límite | Es pila, no trabajo activo. |
| 1. Tesis | 2 | Más de dos hipótesis a la vez diluyen a Fabian y al Gerente General. |
| 2. Validación | 2 | Validar bien exige foco; validar a medias es peor que no validar. |
| 3. Construcción | 1 | Un solo producto en construcción. Terminar > empezar. |
| 4. Uso interno | 2 | Se puede usar internamente en paralelo, pero cada uno exige atención real. |
| 5. Lanzamiento | 1 | Lanzar es un evento: un producto a la vez. |
| 6. Comercial | 3 | El equipo comercial puede manejar hasta 3 productos activos. |
| 7. Activación | 5 | Las activaciones son paralelizables, pero cada cliente activo cuenta. |
| 8. Operación | Sin límite | Los productos vivos se operan; el límite lo pone el P&L. |
| 9. Ciclos | Sin límite | Devolución continua. |

Si una etapa está en su tope, nada nuevo entra: el trabajo se encola en Búsqueda o se mata.

## SLA 48h en compuertas

Fabian decide en **48 horas** o la etapa **se pausa sola**. Pausar ≠ matar: el trabajo queda congelado con su artefacto hasta que haya decisión. Esto protege a los agentes de quedar bloqueados y a Fabian de decidir apurado.

Las aprobaciones se acumulan en cola y Fabian las resuelve en ventanas diarias (mañana y tarde) desde el celular — aprobaciones por lote, no interrupciones.

## Presupuesto semanal de atención de Fabian: el WIP maestro

Fabian es el único humano y el destino final de toda escalación. Sus horas reales son el recurso más escaso de la empresa, así que el pipeline se estrangula a ellas: **es el WIP maestro**.

- Cada semana, Fabian declara cuántas horas de decisión/revisión tiene disponibles.
- El Gerente General planifica compuertas, equipos rojos y entrevistas clave dentro de ese presupuesto.
- Si el presupuesto no alcanza, se pausa o se mata trabajo — nunca se le pide a Fabian que "haga un esfuerzo extra" de forma sistemática.

## Tablero del pipeline

- **Dueño:** [Analista](../agentes/marketing/analista.md). Autónomo.
- **Métricas mínimas:** conversión por etapa, tiempo de ciclo por etapa, tasa de cierre (qué % muere en cada compuerta), WIP actual vs. máximo, SLA de compuertas (decisiones a tiempo vs. pausas automáticas).
- **Regla:** sin métricas, las compuertas son intuición. El tablero se revisa en cada revisión de portfolio.

## Criterios de cierre

- **Cómo se escriben:** en la etapa 1 (Tesis), junto a la hipótesis. Deben ser observables y medibles: p. ej. "si en 4 semanas de validación no hay 10 entrevistas con dolor confirmado, se mata" o "si los precios validados no cubren el costo operativo proyectado, se mata". Nada de "si no funciona" — eso no es un criterio, es un deseo.
- **Quién puede matar:** Fabian en cualquier compuerta; el Gerente General puede proponer el cierre con evidencia en cualquier momento; el cierre automático se dispara cuando se cumple un criterio escrito (se pausa y se eleva a Fabian para confirmación).
- **Cuándo:** en las compuertas (1, 2 y 3) y en la revisión periódica de portafolio para productos en Operación. Matar temprano y barato es una victoria, no un fracaso.

## Validar antes de construir

Regla de oro, sin atajos: **ningún producto entra a Construcción sin pasar la Compuerta 1 con evidencia**. Construir para validar solo se permite con el MVP más chico posible, y el MVP también necesita su hipótesis y su criterio de kill.

---

**Ver también:** [etapas.md](etapas.md) · [portfolio.md](portfolio.md) · [README.md](README.md)
