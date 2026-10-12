# Etapas del pipeline (0 a 9)

Detalle operativo de cada etapa. Convención: **quién ejecuta**, **artefacto de traspaso obligatorio** (sin entregable no hay pase) y **qué compuerta la cierra** (quién decide).

---

## 0. Búsqueda (continuo)

- **Ejecuta:** [Explorador](../agentes/direccion/explorador.md). Autónomo.
- **Qué hace:** escanea mercado, competencia y pedidos de clientes en forma permanente; mantiene una **pila de tesis priorizada**. El pipeline nunca depende de la inspiración del momento. (Antes lo hacía el Analista; desde 2026-10-08 es un rol dedicado.)
- **Artefacto de traspaso:** pila de tesis priorizada (cada entrada: problema, segmento, evidencia inicial).
- **Compuerta:** ninguna; es continuo. El Gerente General selecciona qué tesis entra a la etapa 1 según WIP disponible.

## 1. Tesis

- **Ejecutan:** Fabian + [Gerente General](../agentes/direccion/gerente-general.md).
- **Qué pasa:** se formula la hipótesis escrita + criterios de cierre + revisión de WIP. El **Gerente General somete la hipótesis al equipo rojo** (Arquitecto + Ingeniero de Seguridad + Analista: viabilidad técnica, riesgos y evidencia) antes de gastar un ciclo de validación.
- **Artefacto de traspaso:** hipótesis escrita, criterios de cierre definidos, revisión de WIP de Validación aprobada.
- **Compuerta:** implícita de Fabian — si la tesis no sobrevive al equipo rojo o no hay WIP, no pasa.

## 2. Validación

- **Ejecutan:** [Analista](../agentes/marketing/analista.md) (investigación) con entrevistas asincrónicas por agentes (formularios, landing, chat); [Constructor](../agentes/ingenieria/constructor.md) arma la landing de validación; [Facturador](../agentes/finanzas/facturador.md) deja lista la infra de cobro para la preventa; Fabian solo cierra 2–3 entrevistas clave.
- **Qué pasa:** se busca evidencia real. **Precios validados con método** (prueba en landing/preventa a precio real, no "¿pagarías X?"). La preventa exige infra de cobro lista y promesa explícita (reembolsable).
- **Artefacto de traspaso:** evidencia documentada + precios validados + **mapa de competencia** + **lista de lanzamiento** (entrevistados → CRM como prospectos interesados).
- **Compuerta 1 — decide Fabian:** *se construye o se mata*. SLA 48h; sin decisión, la etapa se pausa sola.

## 3. Construcción

- **Ejecutan (en secuencia):**
  1. [Gerente General](../agentes/direccion/gerente-general.md): escribe la **especificación funcional** desde la evidencia de validación (qué se construye, para quién, criterios de aceptación).
  2. [Arquitecto](../agentes/ingenieria/arquitecto.md): diseña la arquitectura y registra ADRs.
  3. [Diseñador UX/UI](../agentes/ingenieria/disenador-ux-ui.md): flujos y pantallas; el diseño entra antes del código.
  4. [Constructor](../agentes/ingenieria/constructor.md) (web full-stack), [Desarrollador Mobile](../agentes/ingenieria/desarrollador-mobile.md) (apps), [Ingeniero de Datos](../agentes/ingenieria/ingeniero-datos.md) (pipelines), [Ingeniero de ML](../agentes/ingenieria/ingeniero-ml.md) (modelos): construyen en paralelo según el producto.
  5. [Revisor](../agentes/ingenieria/revisor.md) (código; planificador ≠ ejecutor ≠ validador) + [Ingeniero de Seguridad](../agentes/ingenieria/ingeniero-seguridad.md) (cambios sensibles).
  6. [Control de Calidad](../agentes/ingenieria/control-de-calidad.md) (autónomo) + QA visual del Diseñador UX/UI.
  7. [SRE](../agentes/ingenieria/sre.md): define SLOs y observabilidad base del producto.
  8. [Responsable de Despliegues](../agentes/ingenieria/responsable-despliegues.md): despliega solo con aprobación de Fabian.
- **Qué pasa:** especificación → PMV + kit de ventas (resumen de una página, demo, precios) + legales base (términos, privacidad: plantillas que mantiene el Gerente General, aprueba Fabian) + lista de verificación: dependencias evaluadas a costo $0, configuración de cobro por producto, nombre/marca/dominio.
- **Artefacto de traspaso:** PMV funcional + kit de ventas + legales base + lista de verificación $0/cobro/nombre completa.
- **Compuerta:** revisión del Gerente General (que lo construido = lo validado); el pase al Uso interno lo habilita Fabian.

## 4. Uso interno

- **Ejecutan:** los propios agentes + Fabian como usuario; coordina el [Gerente General](../agentes/direccion/gerente-general.md).
- **Qué pasa:** se usa el producto de verdad, con **criterios de salida explícitos** (definidos por el Gerente General en la especificación de la etapa 3): ¿lo usaríamos nosotros? ¿pasa el umbral?
- **Artefacto de traspaso:** resultados del uso interno contra los criterios de salida (pasa/no pasa, con evidencia).
- **Compuerta 2 — decide Fabian:** el producto pasa el umbral para avanzar al lanzamiento.

## 5. Lanzamiento

- **Ejecutan:** [Gerente General](../agentes/direccion/gerente-general.md) coordina; [Contenidos](../agentes/marketing/contenidos.md) (on-the-loop: Fabian revisa antes de publicar), equipo comercial preparado.
- **Qué pasa:** se sale a vender con posicionamiento, materiales y equipo alineados.
- **Artefacto de traspaso:** plan de lanzamiento ejecutado + materiales publicados + equipo comercial listo.
- **Compuerta 3 — decide Fabian:** *aprobación para salir a vender*.

## 6. Comercial

- **Ejecutan:** [Prospector](../agentes/ventas/prospector.md) (listas), [Contacto Inicial](../agentes/ventas/contacto-inicial.md) (on-the-loop: revisión antes de enviar en volumen), [Calificador](../agentes/ventas/calificador.md) (califica y agenda), [Custodio del CRM](../agentes/ventas/custodio-crm.md) (CRM actualizado).
- **Qué pasa:** prospección saliente con cumplimiento (baja, límites de volumen, Ley 25.326 de datos personales); Calificador negocia dentro de **matriz pre-aprobada** (descuentos/condiciones); **revisión de acuerdos**: lo vendido = lo que existe.
- **Artefacto de traspaso:** contrato (plantilla + firma electrónica) + **primer pago**. Venta concretada = contrato + primer pago, nada menos.
- **Compuerta:** revisión de acuerdos del Gerente General — si lo vendido no es lo que existe, no pasa a Activación.

## 7. Activación

- **Ejecuta:** [Responsable de Activación](../agentes/soporte/responsable-activacion.md).
- **Qué pasa:** configuración del cliente, migración de datos, primera victoria. Bóveda de credenciales de clientes (mínimo privilegio): la mantiene el Responsable de Activación, auditada por el Guardián. Aislamiento de datos: tenancy por producto/cliente; ningún agente cruza datos entre clientes. El Responsable de Activación acompaña al cliente los primeros 90 días (retención temprana; el rol dedicado de éxito del cliente se crea en fase 2).
- **Artefacto de traspaso:** cliente activo = configuración completa + primer valor entregado (verificable).
- **Compuerta:** ninguna de Fabian; el criterio es objetivo. **Recién acá la venta está realmente cerrada.**

## 8. Operación

- **Ejecutan:** [Soporte Nivel 1](../agentes/soporte/soporte-n1.md), [SRE](../agentes/ingenieria/sre.md) (SLOs, incidentes, error budgets), [Facturador](../agentes/finanzas/facturador.md) (facturación electrónica ARCA), [Conciliador](../agentes/finanzas/conciliador.md) (concilia y alerta), [Responsable de Informes](../agentes/finanzas/responsable-informes.md) (P&L por producto), [Guardián](../agentes/operaciones/guardian.md) (monitoreo de infra y costo, interruptor de emergencia).
- **Qué pasa:** entregan, cobran (gestión de cobranza automatizada), soportan con SLAs definidos, responden incidentes con post-mortems sin culpas, miden **P&L por producto**.
- **Artefacto de traspaso:** P&L por producto al día + SLAs cumplidos (reporte continuo, no un pase único).
- **Compuerta:** revisión periódica de portafolio (ver [portfolio.md](portfolio.md)): lo que no tracciona se mata o se pausa.

## 9. Ciclos

- **Ejecutan:** [Analista](../agentes/marketing/analista.md) (devolución → pila), equipo comercial (testimonios).
- **Qué pasa:** devolución de clientes → pila → Construcción (el producto itera); testimonios/casos de éxito → Comercial (salida al mercado).
- **Artefacto de traspaso:** pila de producto actualizada + casos de éxito documentados.
- **Compuerta:** ninguna; es el ciclo permanente que alimenta la búsqueda y la construcción.

---

**Ver también:** [reglas.md](reglas.md) · [portfolio.md](portfolio.md) · [README.md](README.md)
