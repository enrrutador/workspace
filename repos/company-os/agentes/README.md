# Agentes de la empresa

Acá vive la definición de cada agente: qué hace, qué puede hacer solo, qué necesita que apruebe Fabian, qué herramientas usa y cómo se mide su trabajo. Todo es consistente con el [diseño operativo v1(../empresa/diseno-operativo-v1.md.

## Cómo leer una ficha

Cada ficha de agente tiene el mismo formato:

- **Área**: a qué función de la empresa pertenece.
- **Misión (2 líneas)**: para qué existe este agente, en dos líneas.
- **Responsabilidades**: qué hace en el día a día, en lista.
- **Autonomía**: qué hace solo y qué requiere aprobación previa de Fabian.
- **Herramientas (vía MCP)**: servidores MCP que usa, en formato `mcp:<servidor>`, con una explicación de para qué lo usa cada uno.
- **Límites y guardarraíles**: qué no puede hacer y qué restricciones lo frenan.
- **Métricas**: cómo se mide su trabajo, con 2–4 métricas concretas.
- **Dueño**: Fabian — siempre, para todos los agentes.

## Los 3 niveles de autonomía

La autonomía se gradúa **por riesgo**, no por capacidad. Del diseño operativo:

- **Autónomo** — acciones reversibles: leer, redactar borradores, correr tests, actualizar datos internos. El agente actúa solo y deja log de lo que hizo.
- **On-the-loop** — riesgo medio: el agente actúa y Fabian revisa después. Aplica a lo que sale hacia afuera pero se puede corregir (emails, movimientos en el CRM). La revisión post-acción permite detectar y corregir a tiempo.
- **In-the-loop** — acciones irreversibles o de alto impacto: dinero, clientes, accesos, despliegues. Nada se ejecuta sin la aprobación previa de Fabian. Lo irreversible se acumula en una cola y Fabian lo aprueba por lote desde el celular en ventanas diarias; si no está disponible, los agentes siguen con lo autónomo y encolan lo irreversible. Nada irreversible se ejecuta sin él.

Regla de oro: máxima restricción al lanzar; más autonomía solo tras ~30 días con tasa de aprobación alta.

## Principio: planificador ≠ ejecutor ≠ validador

Ningún agente tiene poder sobre otro ni puede autovalidarse:

- El que **planifica** una tarea no es el que la **ejecuta**.
- El que la ejecuta no es el que la **valida**.
- Un cuarto rol **registra** (logger): todo queda en un log append-only — qué se hizo, con qué datos, quién lo aprobó. Sin log, no existe.

## Habilidades: el cómo profesional

Cada agente tiene además su **skill** en [`../habilidades/`](../habilidades/): procedimientos
paso a paso, listas de verificación, criterios de decisión, ejemplos y casos borde. La ficha
dice *qué* hace el agente; la skill dice *cómo* lo hace bien.

## Las 7 áreas

1. [Dirección](./direccion/) — Gerente General: el directivo después de Fabian; delega a cada sector, supervisa y reporta avance.
2. [Ingeniería & Producto](./ingenieria/) — Arquitecto, Constructor full-stack, Desarrollador Mobile, Ingeniero de Datos, Ingeniero de ML, Revisor, Control de Calidad, Diseñador UX/UI, Ingeniero de Seguridad, SRE, Responsable de Despliegues: diseñan, construyen, aseguran y operan los productos.
3. [Ventas](./ventas/) — Prospector, Contacto Inicial, Calificador, Custodio del CRM: investigan, contactan, califican y mantienen el CRM.
4. [Soporte](./soporte/) — Soporte Nivel 1, Responsable de Activación, Escalamiento: resuelven, activan clientes y derivan a Fabian lo sensible.
5. [Marketing & Contenidos](./marketing/) — Contenidos, Analista: redactan y miden qué funciona.
6. [Finanzas & Admin](./finanzas/) — Facturador, Conciliador, Responsable de Informes: facturan, concilian y reportan el P&L.
7. [Operaciones & IT](./operaciones/) — Guardián: monitorea infra y costo, alerta anomalías y puede frenar agentes (interruptor de emergencia).

Fabian es el único humano, para siempre: define objetivos, aprueba lo irreversible, es dueño de todos los agentes y destino final de toda escalación.
