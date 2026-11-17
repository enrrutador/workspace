# Diseño operativo v1 — La empresa como plantel de agentes

*Fecha: 2026-10-07 · Estado: borrador para revisión con Fabian.*

## La idea en una línea

Una empresa multi-producto donde cada función (ingeniería, ventas, soporte, finanzas, marketing) la ejecuta un equipo de agentes de IA con roles definidos, permisos mínimos y supervisión humana solo en decisiones irreversibles. Fabian dirige; los agentes operan.

## Principios no negociables

1. **Cada agente es un empleado con identidad propia**: credenciales propias, permisos mínimos, dueño humano nombrado (al principio, Fabian).
2. **Autonomía graduada por riesgo**: autónomo para lo reversible (borradores, lecturas); humano *on-the-loop* para lo medio (correos, CRM); humano *in-the-loop* (aprobación previa) para lo irreversible (dinero, clientes, accesos, despliegues).
3. **Todo queda registrado**: qué hizo cada agente, con qué datos, quién lo aprobó. Sin registro, no existe.
4. **El presupuesto vive fuera del agente**: techos de gasto en el gateway, no en el código del agente.
5. **Se empieza chico**: un agente, una función, una tarea medible. Se escala lo que ya funciona y está auditado.
6. **Costo total = 0** (restricción de Fabian): nada pago. Todo de código abierto, autohospedado, con modelos locales o de planes gratuitos.
7. **Un solo humano, para siempre**: Fabian es la única persona. No hay empleados, socios ni contratistas. Todo *human-in-the-loop* y toda escalación caen en él: el diseño debe funcionar con aprobaciones por lote y cola de espera cuando no esté disponible.

## Organigrama de agentes (plantilla v1)

### Dirección
- **Gerente General (agente)**: el directivo después de Fabian. Recibe sus objetivos, los descompone en tareas, los delega a cada sector, supervisa la ejecución y reporta avance. Es el único que habla con todos.
- **Fabian (único humano, para siempre)**: define objetivos, aprueba lo irreversible, es dueño de todos los agentes y destino final de toda escalación. No hay nadie más: ni socios, ni empleados, ni contratistas.

### Operar con un solo humano
- **Aprobaciones por lote**: lo irreversible se acumula en una cola y Fabian lo aprueba en ventanas diarias (p. ej. mañana y tarde) desde el celular, en vez de interrumpirlo todo el día.
- **Modo offline**: si Fabian no está disponible, los agentes siguen con lo autónomo y encolan lo irreversible. Nada irreversible se ejecuta sin él.
- **Escalación = Fabian**: soporte, ventas y cualquier caso fuera de guion terminan en él. El diseño de cada agente debe minimizar esas escalaciones con reglas claras.
- **Punto único de fallo**: documentar manuales operativos por agente para que cualquiera (o un futuro yo) pueda retomar; los registros son la memoria institucional.

### Ingeniería & Producto
- **Constructor**: implementa funcionalidades y correcciones. Escribe código, no despliega solo.
- **Revisor**: revisa el código del Constructor (segundo par de ojos; planificador ≠ ejecutor).
- **Control de Calidad**: corre pruebas, reporta fallos. Autónomo.
- **Responsable de Despliegues**: despliega solo con aprobación humana (*in-the-loop*).

### Ventas
- **Prospector**: investiga cuentas, arma listas. Autónomo.
- **Contacto Inicial**: redacta y envía mensajes. *On-the-loop* (revisión antes de enviar en volumen).
- **Calificador**: califica respuestas, agenda reuniones. Autónomo con reglas claras.
- **Custodio del CRM**: mantiene el CRM actualizado. Autónomo.

### Soporte
- **Soporte Nivel 1**: resuelve lo frecuente de forma autónoma dentro de guías.
- **Responsable de Activación**: configuración del cliente, migración de datos, primera victoria. Recién cuando el cliente está activo, la venta está realmente cerrada.
- **Escalamiento**: deriva a Fabian ante frustración, temas sensibles o fuera de guion. El camino al humano siempre existe (lección de Klarna 2024–2026: recortar humanos de más degradó la calidad y hubo que recontratar).
- Todo agente que hable con personas se identifica como IA (EU AI Act art. 50, exigible desde agosto 2026).

### Marketing & Contenidos
- **Contenidos**: redacta posteos, documentos, newsletters. *On-the-loop* (Fabian revisa antes de publicar).
- **Analista**: mide qué funciona y reporta. Autónomo.

### Finanzas & Admin
- **Facturador**: genera facturas electrónicas (ARCA) por cada cobro. *On-the-loop* al inicio.
- **Conciliador**: concilia ingresos vs. facturación, alerta inconsistencias. Autónomo.
- **Responsable de Informes**: P&L mensual y flujo de caja. Autónomo.
- Dinero real = *in-the-loop* siempre al principio, con montos máximos por transacción/día definidos por Fabian.

### Operaciones & IT
- **Guardián**: monitorea infra y costo de tokens, alerta anomalías y puede frenar agentes con gasto anormal (interruptor de emergencia). Autónomo, con límites estrictos (solo lectura + freno de emergencia).

**Total v1: 18 agentes** (+ Fabian como humano). Ampliación 2026-10-07: 25 agentes (Ingeniería & Producto pasa de 4 a 11 con Arquitecto, Desarrollador Mobile, Ingeniero de Datos, Ingeniero de ML, Diseñador UX/UI, Ingeniero de Seguridad y SRE). Ampliación 2026-10-08: 26 agentes (Dirección suma al Explorador, dueño de la etapa 0 del pipeline: descubrimiento continuo de ideas). Excepciones diseñadas al "ningún agente tiene poder sobre otro": autoridad de delegación del Gerente General, freno de emergencia del Guardián y freno por riesgo crítico del Ingeniero de Seguridad.

## Infraestructura (pila sugerida, bajo capital)

| Capa | Elección | Por qué |
|---|---|---|
| Modelos | De código abierto locales (Ollama/vLLM: Qwen, Llama, etc.) o planes gratuitos | $0. Contrapartida honesta: rinden menos que los modelos de punta en tareas agénticas complejas; el diseño prioriza tareas acotadas donde los modelos chicos rinden bien |
| Orquestación | LangGraph (Python) | Consenso 2026: auditable, puntos de control, human-in-the-loop nativo. Código abierto |
| Integraciones | MCP | Estándar abierto; cada sistema y cada producto futuro expone un servidor MCP. **Es además tu tesis**: la empresa entera interoperable |
| Gateway y presupuestos | LiteLLM proxy (autohospedado) | Techos por solicitud/sesión/clave, cortacircuitos; la política de gasto vive acá, no en el agente. Con costo 0, el gateway controla cuotas de los planes gratuitos y uso de GPU local |
| Observabilidad | Langfuse (autohospedado) | Código abierto; gratis total si se auto-hospeda |
| Aprobaciones | Bot propio (Telegram/correo) | Aprobar/rechazar desde el celular lo irreversible, sin costo |
| Identidad | 1 identidad no-humana por agente | Permisos mínimos, tokens de corta vida, dueño nombrado |
| Hosting | Hardware propio o nube con plan gratuito | $0; escalar solo cuando un agente pague su propia infra con el valor que genera |

**Costo total: $0.** Toda la pila es de código abierto y autohospedada. El único "costo" es tiempo de ingeniería y el hardware que Fabian ya tenga. Regla: ningún agente incorpora un servicio pago sin que el valor que genera lo justifique y Fabian lo apruebe.

## Gobernanza mínima viable (primeras 48h de cada agente)

1. Inventariar qué puede leer y escribir; revocar escrituras no esenciales.
2. Clasificar sus acciones: reversibles vs. irreversibles.
3. Longitud máxima de cadena (anti-loops) + presupuesto en el gateway.
4. Bot de aprobación para lo irreversible.
5. Registro de solo adición de todo (qué leyó, qué hizo, quién aprobó).
6. Equipo rojo básico: intentar romperlo antes de que lo haga un cliente.

Regla de oro reportada: **máxima restricción al lanzar; más autonomía solo tras ~30 días con tasa de aprobación alta.**

## Secuencia de implementación

- **Fase 0 — Piloto (semanas 1–4)**: un agente, una función, una tarea medible. Medir la *línea base* ANTES de automatizar. Candidatos: **Conciliador** (finanzas) o **Control de Calidad** (ingeniería) — tareas acotadas y medibles.
- **Fase 1 — Primera función completa (meses 2–3)**: el equipo de una función (p. ej. soporte L1) con gobernanza mínima.
- **Fase 2 — Multi-función (meses 4–6)**: un equipo por función, Gerente General coordinando.
- **Fase 3 — Escala por producto**: cada producto nuevo nace "listo para agentes" sobre la misma infra compartida (MCP + gateway + observabilidad). **Esta es la ventaja estructural** frente a una empresa tradicional.

## Pipeline de producto (compuertas de etapa) — v3

El flujo no es una línea, es un ciclo con compuertas. Fabian abre y cierra cada etapa. **Cada traspaso exige un artefacto explícito**: sin entregable no hay pase.

**0. Búsqueda (continuo)** — Analista escanea mercado, competencia y pedidos de clientes en forma permanente y mantiene una **pila de tesis** priorizada. El pipeline nunca depende de la inspiración del momento.

1. **Tesis** (Fabian + Gerente General) → artefacto: hipótesis escrita + criterios de cierre + revisión de WIP. **El Gerente General somete la hipótesis al equipo rojo** antes de gastar un ciclo de validación.
2. **Validación** (investigación/Analista) → artefacto: evidencia, **precios validados con método** (prueba en landing/preventa a precio real, no "¿pagarías X?"), mapa de competencia, **lista de lanzamiento** (entrevistados → CRM como prospectos interesados). Entrevistas asincrónicas por agentes (formularios, landing, chat); Fabian solo cierra 2–3 clave. La preventa exige infra de cobro lista y promesa explícita (reembolsable). *Compuerta 1 — Fabian: se construye o se mata.*
3. **Construcción** (Constructor, Revisor, Control de Calidad) → artefacto: **especificación escrita** desde la evidencia + PMV + kit de ventas (resumen de una página, demo, precios) + legales base (términos, privacidad) + lista de verificación: dependencias evaluadas a costo $0, configuración de cobro por producto, nombre/marca/dominio.
4. **Uso interno** → criterios de salida explícitos: ¿lo usaríamos nosotros? ¿pasa el umbral? *Compuerta 2.*
5. **Lanzamiento** — *Compuerta 3 — Fabian aprueba salir a vender.*
6. **Comercial** (Prospector, Contacto Inicial, Calificador, Custodio del CRM) → prospección saliente con cumplimiento (baja, límites de volumen, Ley 25.326 de datos personales); Calificador negocia dentro de **matriz pre-aprobada** (descuentos/condiciones); **revisión de acuerdos**: lo vendido = lo que existe. Venta concretada = contrato (plantilla + firma electrónica) + primer pago.
7. **Activación** (Responsable de Activación) → bóveda de credenciales de clientes (mínimo privilegio); cliente activo = configuración completa + primer valor entregado. Recién acá la venta está realmente cerrada.
8. **Operación** (Soporte Nivel 1, Facturador, Conciliador) → entregan, cobran (gestión de cobranza automatizada), soportan con SLAs definidos, miden **P&L por producto** (Responsable de Informes).
9. **Ciclos**: devolución → pila → Construcción (producto); testimonios/casos de éxito → Comercial (salida al mercado).

**Capa portafolio** (clave multi-producto): los productos compiten entre sí por capacidad de agentes y atención de Fabian. **Mapa de dependencias entre productos** obligatorio (la tesis los conecta: matar uno puede romper otro). **Proceso de discontinuación** para productos con clientes: comunicación, migración, reembolsos. Revisión periódica: lo que no tracciona se mata o se pausa. El pipeline crea productos, pero también los mata — con agentes baratos, el riesgo es el cementerio de productos zombies.

**Reglas de flujo**:
- WIP máximo por etapa (p. ej. 2 en Validación, 1 en Construcción). Sin excepciones.
- Compuertas con SLA: Fabian decide en 48h o la etapa se pausa sola.
- **Presupuesto semanal de atención de Fabian**: el pipeline se estrangula a sus horas reales. Es el WIP maestro.
- **Tablero del pipeline** (Analista): conversión por etapa, tiempo de ciclo, tasa de cierre. Sin métricas, las compuertas son intuición.
- **Aislamiento de datos**: tenancy por producto/cliente; ningún agente cruza datos entre clientes.
- Validar ANTES de construir. Construir para validar solo con el MVP más chico posible.

## Riesgos que más importan

- **Gasto descontrolado**: loops multi-agente que queman miles sin aviso (hay casos reales de USD 47k en 11 días) → mitigado por presupuestos en el gateway.
- **Sobre-automatización**: degradar calidad por sacar humanos → escalamiento a humano diseñado desde el día uno.
- **Seguridad**: inyección de prompts / envenenamiento de herramientas, fuga de datos en registros → ocultar los datos personales, MCP solo de fuentes confiables.
- **Legal**: la empresa responde por lo que hagan sus agentes → contratos con límites de autoridad claros, registros de auditoría, identificarse como IA ante personas. Si un agente factura o mueve dinero: facturación electrónica ARCA desde el día uno, todo trazable.

## Qué NO hacer

- Comprar plataforma empresarial cara al inicio (construirlo uno mismo es 10–100x más barato a bajo volumen).
- Darle a un agente escritura amplia "para probar".
- Automatizar dinero o clientes sin aprobación humana ni audit trail.
- Escalar sin medir calidad: no solo "cuánto se automatizó" sino "qué tan bien".

## Próximos pasos propuestos

1. Revisar este diseño con Fabian y ajustar funciones/roles.
2. Elegir el agente piloto (recomendación: Conciliador o Control de Calidad).
3. Definir nombre de la empresa (lo necesita la SAS y la identidad de los agentes).
4. En paralelo: trámite SAS con objeto social amplio. Nota legal: la SAS unipersonal exige designar a un tercero como administrador suplente【3364522048620189890†L33-L35】 — es una formalidad registral, no un rol operativo; no contradice el principio de "un solo humano".

---

*Basado en investigación de ~25 fuentes (octubre 2026; informe completo en archivos internos del objetivo) y en patrones de operación de agentes en producción. Las cifras marcadas como "estimación" son aproximadas: verificar precios oficiales antes de contratar.*
