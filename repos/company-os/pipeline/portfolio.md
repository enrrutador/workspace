# Portafolio: varios productos, una sola empresa

El pipeline crea productos; esta capa decide cuáles viven, cuáles compiten y cuáles mueren.

## Cómo compiten los productos por capacidad

Los productos no existen en el vacío: compiten entre sí por dos recursos escasos.

1. **Capacidad de agentes.** Los equipos (Arquitecto, Constructor, Revisor, Control de Calidad, Datos/ML, comercial, soporte) son compartidos. El Gerente General asigna capacidad según prioridad del portafolio, respetando el WIP máximo por etapa (ver [reglas.md](reglas.md)). Un producto en Construcción ocupa el lugar de Construcción: los demás esperan o mueren.
2. **Atención de Fabian.** Es el WIP maestro: compuertas, equipos rojos, entrevistas clave y escalaciones. El presupuesto semanal se reparte entre productos; el que no entra en el presupuesto, se pausa.

La priorización la propone el Gerente General con datos del tablero y la decide Fabian en la revisión periódica de portafolio.

## Mapa de dependencias entre productos (obligatorio)

La tesis de la empresa es la **conexión entre productos tecnológicos**: los productos interoperan (vía MCP) y se potencian. Eso tiene un costo: **matar uno puede romper otro**.

- Cada producto mantiene un **mapa de dependencias**: qué consume de otros productos (APIs, datos, autenticación) y qué otros productos consumen de él.
- El mapa se actualiza en cada traspaso de etapa y lo verifica el Gerente General.
- Ninguna decisión de cierre o discontinuación se toma sin revisar el mapa: si el producto tiene dependientes, hay que migrarlos o absorber la funcionalidad antes de matarlo.

## P&L por producto

- **Dueño:** [Responsable de Informes](../agentes/finanzas/responsable-informes.md). Autónomo; reporta P&L mensual y flujo de caja por producto.
- **Uso:** es la base de las decisiones de portfolio. Un producto en Operación se juzga por sus números: ingresos, costos (infra, tokens, soporte), margen y tendencia.
- **Regla:** lo que no se mide no se defiende. Sin P&L al día, un producto no puede pedir más capacidad.

## Proceso de discontinuación (productos con clientes)

Matar un producto con clientes activos exige un proceso, no un interruptor. Paso a paso:

1. **Decisión.** Fabian aprueba la discontinuación con fecha de corte, tras revisar el mapa de dependencias y el P&L. Se nombra un responsable (típicamente el Gerente General).
2. **Comunicación a clientes.** Aviso con antelación razonable: qué se cierra, cuándo y por qué. Mensaje honesto, sin jerga. Todo agente que hable con clientes se identifica como IA.
3. **Migración.** Ofrecer camino de salida: exportación de datos del cliente, y si existe, migración a otro producto del portafolio. Soporte durante la transición.
4. **Reembolsos.** Devolver lo cobrado por períodos no prestados según los términos contratados. El Facturador genera la documentación; el Conciliador verifica. Dinero = aprobación de Fabian.
5. **Archivo.** Se congelan código, datos (con retención legal), registros y documentación. Se revocan credenciales e integraciones. El producto sale del tablero y del mapa de dependencias.

## El riesgo del cementerio de productos zombies

Con agentes baratos, crear productos es casi gratis — y ese es el peligro: acumular productos que no traccionan pero tampoco mueren, consumiendo soporte, atención y complejidad. Un zombie no pierde plata de golpe; la pierde a gotas, todos los meses.

Antídotos:

- **Revisión periódica de portafolio:** lo que no tracciona se mata o se pausa. Sin excepciones sentimentales.
- **Criterios de cierre escritos** desde la Tesis (ver [reglas.md](reglas.md)).
- **P&L por producto** como juez imparcial.
- **WIP máximo** que impide empezar lo nuevo sin terminar o matar lo viejo.

El pipeline crea productos, pero también los mata. Las dos cosas son el trabajo.

---

**Ver también:** [etapas.md](etapas.md) · [reglas.md](reglas.md) · [README.md](README.md)
