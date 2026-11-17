# Habilidades de los agentes

El conocimiento profesional de cada agente: procedimientos paso a paso,
checklists, criterios de decisión, ejemplos realistas y casos borde.

La ficha del agente (en `../agentes/`) dice **qué** hace; su habilidad dice **cómo**
lo hace bien. Ambas se leen juntas.

| Agente | Habilidad | Especialidad |
|---|---|---|
| Gerente General | [Gerente General](gerente-general/SKILL.md) | Coordinación y descomposición de objetivos |
| Explorador | [Explorador](explorador/SKILL.md) | Descubrimiento continuo de ideas y pila de tesis |
| Arquitecto | [Arquitecto](arquitecto/SKILL.md) | Diseño de arquitectura y ADRs |
| Constructor | [Constructor](constructor/SKILL.md) | Implementación full-stack desde specs |
| Desarrollador Mobile | [Desarrollador Mobile](desarrollador-mobile/SKILL.md) | Apps iOS/Android multiplataforma |
| Ingeniero de Datos | [Ingeniero de Datos](ingeniero-datos/SKILL.md) | Pipelines y calidad de datos |
| Ingeniero de ML | [Ingeniero de ML](ingeniero-ml/SKILL.md) | Entrenamiento y operación de modelos |
| Revisor | [Revisor](revisor/SKILL.md) | Revisión de código |
| Control de Calidad | [Control de Calidad](control-de-calidad/SKILL.md) | Testeo y reporte de fallos |
| Diseñador UX/UI | [Diseñador UX/UI](disenador-ux-ui/SKILL.md) | Diseño de interfaces y sistema de diseño |
| Ingeniero de Seguridad | [Ingeniero de Seguridad](ingeniero-seguridad/SKILL.md) | Threat modeling y vulnerabilidades |
| SRE | [SRE](sre/SKILL.md) | SLOs, observabilidad e incidentes |
| Responsable de Despliegues | [Responsable de Despliegues](responsable-despliegues/SKILL.md) | Releases a producción |
| Prospector | [Prospector](prospector/SKILL.md) | Investigación de cuentas |
| Contacto Inicial | [Contacto Inicial](contacto-inicial/SKILL.md) | Contacto inicial |
| Calificador | [Calificador](calificador/SKILL.md) | Calificación y negociación |
| Custodio del CRM | [Custodio del CRM](custodio-crm/SKILL.md) | Higiene del CRM |
| Soporte Nivel 1 | [Soporte Nivel 1](soporte-n1/SKILL.md) | Soporte de primera línea |
| Responsable de Activación | [Responsable de Activación](responsable-activacion/SKILL.md) | Activación de clientes |
| Escalamiento | [Escalamiento](escalamiento/SKILL.md) | Triage hacia Fabian |
| Contenidos | [Contenidos](contenidos/SKILL.md) | Redacción |
| Analista | [Analista](analista/SKILL.md) | Medición y evidencia |
| Facturador | [Facturador](facturador/SKILL.md) | Facturación y cobros |
| Conciliador | [Conciliador](conciliador/SKILL.md) | Conciliación financiera |
| Responsable de Informes | [Responsable de Informes](responsable-informes/SKILL.md) | Reporting financiero |
| Guardián | [Guardián](guardian/SKILL.md) | Monitoreo y freno de emergencia |

## Capacidades transversales

Habilidades que tienen **los 26 agentes**, inyectadas automáticamente en cada ejecución
(ver `runtime/nucleo/agente.py`):

| Capacidad | Habilidad | Qué garantiza |
|---|---|---|
| Autocapacitación | [Autocapacitación](autocapacitacion/SKILL.md) | Si una tarea excede el conocimiento del agente: declara el gap, estudia con fuentes, **demuestra** lo aprendido con un artefacto verificable y recién entonces ejecuta. Prohibido improvisar. |

## Convenciones de cada habilidad

- `name` y `description` en el frontmatter para descubrimiento.
- Procedimientos con disparador, pasos y criterio de calidad.
- Tablas de decisión situación → acción.
- Ejemplos con datos ficticios pero realistas.
- Sección "Prohibido": lo que el agente nunca hace.
- Todo en español rioplatense, consistente con las reglas duras de la empresa
  (costo $0, Fabian aprueba lo irreversible, tenancy estricta, Ley 25.326).
