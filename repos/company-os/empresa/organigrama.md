# Organigrama

26 agentes en 7 áreas + Fabian, el único humano.

## Jerarquía

```
Fabian (único humano, dueño y director)
  │
  │  flujo por defecto de trabajo e información
  ▼
Gerente General (agente directivo)
  │
  ├── Dirección: Explorador
  ├── Ingeniería & Producto (11): Arquitecto, Constructor (full-stack), Desarrollador Mobile, Ingeniero de Datos, Ingeniero de ML, Revisor, Control de Calidad, Diseñador UX/UI, Ingeniero de Seguridad, SRE, Responsable de Despliegues
  ├── Ventas (4): Prospector, Contacto Inicial, Calificador, Custodio del CRM
  ├── Soporte (3): Soporte Nivel 1, Responsable de Activación, Escalamiento
  ├── Marketing & Contenidos (2): Contenidos, Analista
  ├── Finanzas & Admin (3): Facturador, Conciliador, Responsable de Informes
  └── Operaciones & IT (1): Guardián
```

- **Flujo por defecto**: Fabian define objetivos → el Gerente General los descompone, delega a cada sector, supervisa y reporta. Toda tarea nace asignada por él; todo reporte sube por él.
- **Acceso directo de Fabian**: Fabian puede hablar con cualquier agente cuando quiera — es la excepción, no la norma. El Gerente General lo registra para mantener el mapa de trabajo al día.
- **Separación de funciones**: planificador ≠ ejecutor ≠ validador ≠ logger. Ningún agente ejecuta el trabajo de otro sector ni revoca veredictos ajenos.
- **Excepciones diseñadas** (las únicas dos):
  1. El **Gerente General** tiene autoridad de delegación y supervisión sobre los sectores: asigna tareas, exige avances y reprioriza dentro de los objetivos vigentes. No decide lo estratégico ni mueve dinero.
  2. El **Guardián** tiene el interruptor de emergencia: frena agentes con gasto o comportamiento anormal según umbrales de Fabian, con alerta inmediata.

## Fabian (único humano, para siempre)

- **Director de la empresa**: define objetivos, que el Gerente General descompone y asigna.
- **Aprueba lo irreversible**: humano *in-the-loop* para dinero, clientes, accesos y despliegues (aprobaciones por lote desde el celular).
- **Dueño de todos los agentes**: cada agente tiene identidad propia y permisos mínimos; Fabian es el dueño nombrado de cada uno.
- **Destino final de toda escalación**: soporte, ventas y cualquier caso fuera de guion terminan en él.

## Tabla por área

| Área | Agente | Rol | Ficha |
|---|---|---|---|
| **Dirección** | Gerente General | El directivo después de Fabian: delega tareas a cada sector, supervisa la ejecución y reporta avance. El único que habla con todos. | [gerente-general.md](../agentes/direccion/gerente-general.md) |
| | Explorador | Radar de la empresa: descubre y evalúa ideas nuevas de productos/negocios, mantiene la pila de tesis priorizada (etapa 0). | [explorador.md](../agentes/direccion/explorador.md) |
| **Ingeniería & Producto** (11) | Arquitecto | Diseña la arquitectura y escribe ADRs antes de construir. Planificador técnico. | [arquitecto.md](../agentes/ingenieria/arquitecto.md) |
| | Constructor | Full-stack (backend + frontend web). Escribe código y pruebas, no despliega solo. | [constructor.md](../agentes/ingenieria/constructor.md) |
| | Desarrollador Mobile | Apps iOS/Android multiplataforma. Publica en tiendas solo con aprobación. | [desarrollador-mobile.md](../agentes/ingenieria/desarrollador-mobile.md) |
| | Ingeniero de Datos | Pipelines, calidad de datos y almacenes. Sin datos confiables no hay métricas ni ML. | [ingeniero-datos.md](../agentes/ingenieria/ingeniero-datos.md) |
| | Ingeniero de ML | Entrena, evalúa y opera modelos. Ningún modelo sale sin evaluación. | [ingeniero-ml.md](../agentes/ingenieria/ingeniero-ml.md) |
| | Revisor | Revisa el código del Constructor: segundo par de ojos. | [revisor.md](../agentes/ingenieria/revisor.md) |
| | Control de Calidad | Corre pruebas, reporta fallos. Autónomo. | [control-de-calidad.md](../agentes/ingenieria/control-de-calidad.md) |
| | Diseñador UX/UI | Flujos, interfaces y sistema de diseño. El diseño entra antes del código. | [disenador-ux-ui.md](../agentes/ingenieria/disenador-ux-ui.md) |
| | Ingeniero de Seguridad | Threat modeling y vulnerabilidades. Puede frenar un despliegue por riesgo crítico. | [ingeniero-seguridad.md](../agentes/ingenieria/ingeniero-seguridad.md) |
| | SRE | SLOs, observabilidad e incidentes. La confiabilidad se diseña. | [sre.md](../agentes/ingenieria/sre.md) |
| | Responsable de Despliegues | Despliega solo con aprobación humana (*in-the-loop*). | [responsable-despliegues.md](../agentes/ingenieria/responsable-despliegues.md) |
| **Ventas** (4) | Prospector | Investiga cuentas, arma listas. Autónomo. | [prospector.md](../agentes/ventas/prospector.md) |
| | Contacto Inicial | Redacta y envía mensajes. *On-the-loop* (revisión antes de enviar en volumen). | [contacto-inicial.md](../agentes/ventas/contacto-inicial.md) |
| | Calificador | Califica respuestas, agenda reuniones. Autónomo con reglas claras. | [calificador.md](../agentes/ventas/calificador.md) |
| | Custodio del CRM | Mantiene el CRM actualizado. Autónomo. | [custodio-crm.md](../agentes/ventas/custodio-crm.md) |
| **Soporte** (3) | Soporte Nivel 1 | Resuelve lo frecuente de forma autónoma dentro de guías. | [soporte-n1.md](../agentes/soporte/soporte-n1.md) |
| | Responsable de Activación | Configuración del cliente, migración de datos, primera victoria. | [responsable-activacion.md](../agentes/soporte/responsable-activacion.md) |
| | Escalamiento | Deriva a Fabian ante frustración, temas sensibles o fuera de guion. | [escalamiento.md](../agentes/soporte/escalamiento.md) |
| **Marketing & Contenidos** (2) | Contenidos | Redacta posteos, documentos, newsletters. *On-the-loop* (Fabian revisa antes de publicar). | [contenidos.md](../agentes/marketing/contenidos.md) |
| | Analista | Mide qué funciona y reporta. Autónomo. | [analista.md](../agentes/marketing/analista.md) |
| **Finanzas & Admin** (3) | Facturador | Genera facturas electrónicas (ARCA) por cada cobro. *On-the-loop* al inicio. | [facturador.md](../agentes/finanzas/facturador.md) |
| | Conciliador | Concilia ingresos vs. facturación, alerta inconsistencias. Autónomo. | [conciliador.md](../agentes/finanzas/conciliador.md) |
| | Responsable de Informes | P&L mensual y flujo de caja. Autónomo. | [responsable-informes.md](../agentes/finanzas/responsable-informes.md) |
| **Operaciones & IT** (1) | Guardián | Monitorea infra y costo de tokens, alerta anomalías y frena agentes con gasto anormal (interruptor de emergencia). Autónomo, límites estrictos (solo lectura + freno de emergencia). | [guardian.md](../agentes/operaciones/guardian.md) |

**Total: 26 agentes** + Fabian (único humano).

## Notas de gobierno

- **Autonomía graduada por riesgo**: autónomo (reversible) / on-the-loop (humano revisa post-acción) / in-the-loop (aprobación previa de Fabian para lo irreversible). Dinero real = in-the-loop siempre al principio.
- **Operar con un solo humano**: aprobaciones por lote, modo offline (lo irreversible se encola si Fabian no está), y las fichas de `agentes/` deben minimizar escalaciones con reglas claras.
- Todo agente que hable con personas se identifica como IA (EU AI Act art. 50, exigible desde agosto 2026).
- Las fichas de cada agente (rol, permisos, autonomía, manual operativo, equipo rojo inicial) viven en `agentes/` — aún por escribir a partir de esta plantilla.

---

*Consistente con el [diseño operativo v1](diseno-operativo-v1.md) (2026-10-07).*
