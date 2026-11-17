# Niveles de autonomía por riesgo

*Fuente de verdad: [Diseño operativo v1](../empresa/diseno-operativo-v1.md) · Fecha: 2026-10-07*

Cada agente opera en uno de tres niveles, definidos **por el riesgo de sus acciones, no por su capacidad**. El nivel se asigna en el lanzamiento, se revisa periódicamente y solo se flexibiliza con evidencia (ver "Regla de oro" abajo).

## Nivel 1 — Autónomo

El agente actúa por su cuenta, sin revisión humana. Se reserva para acciones **reversibles**: lecturas, borradores, análisis, cálculos. Todo queda registrado ([auditoria.md](auditoria.md)) para poder revisar después.

**Ejemplos:**

- **Control de Calidad**: corre la suite de pruebas y reporta resultados. Si encuentra un fallo, lo registra y avisa; no corrige ni despliega.
- **Prospector**: investiga cuentas y arma listas de prospectos. No contacta a nadie.
- **Calificador**: califica respuestas según reglas explícitas y agenda reuniones dentro de parámetros pre-aprobados.
- **Custodio del CRM**: actualiza el CRM con datos verificados de conversaciones ya ocurridas.
- **Analista**: mide métricas y produce reportes. No publica ni cambia estrategias.
- **Conciliador**: concilia ingresos vs. facturación. Si detecta una inconsistencia, alerta; no mueve dinero.
- **Responsable de Informes**: genera P&L mensual y reportes de flujo de caja a partir de datos ya registrados.

## Nivel 2 — On-the-loop (revisión post-acción)

El agente actúa, pero un humano (Fabian) revisa el resultado. Se usa cuando la acción tiene **consecuencias visibles o difícilmente reversibles**, pero el volumen hace inviable aprobar cada una de antemano. La revisión puede revertir o frenar.

**Ejemplos:**

- **Contacto Inicial**: redacta y envía mensajes de prospección. En volumen, Fabian revisa muestras y puede pausar la campaña. El primer envío a un segmento nuevo es in-the-loop hasta validar el guion.
- **Contenidos**: redacta posteos, documentos y newsletters. Fabian revisa **antes de publicar** (publicar siempre requiere aprobación previa — ver [aprobaciones.md](aprobaciones.md)).
- **Soporte Nivel 1**: resuelve lo frecuente de forma autónoma **dentro de guías aprobadas**. Todo lo que salga del guion escala (ver [escalación en aprobaciones.md](aprobaciones.md#escalación)).
- **Responsable de Activación**: ejecuta configuraciones y migraciones de datos de clientes siguiendo manuales operativos aprobados. Errores con datos de clientes escalan.
- **Facturador**: genera facturas electrónicas (ARCA) por cada cobro. *On-the-loop al inicio*; pasa a in-the-loop permanente si mueve dinero (ver abajo).
- **Constructor**: escribe código, no despliega. El código pasa por Revisor antes de avanzar.

## Nivel 3 — In-the-loop (aprobación previa obligatoria)

Nada se ejecuta sin la aprobación explícita de Fabian. Reservado para lo **irreversible**: dinero, clientes, accesos y despliegues.

**Ejemplos:**

- **Responsable de Despliegues**: despliega a producción **solo con aprobación previa**. Nunca despliega solo.
- **Facturador**: cualquier movimiento real de dinero (débito, reembolso, ajuste) requiere aprobación previa. *Dinero real = in-the-loop siempre al principio*, con montos máximos por transacción y por día definidos por Fabian.
- **Guardián**: su operación diaria (monitoreo de infra y costo de tokens) es autónoma **con límites estrictos** (solo lectura + freno de emergencia). Activar el interruptor de emergencia sobre un agente con gasto anormal es su única acción ejecutiva, y se reporta de inmediato para revisión de Fabian.
- **Revisor**: su aprobación del código es una compuerta, pero no sustituye la aprobación de Fabian para el despliegue. *Planificador ≠ ejecutor ≠ validador.*

**Matriz completa de qué requiere aprobación previa:** ver [aprobaciones.md](aprobaciones.md).

## Regla de oro

> **Máxima restricción al lanzar; más autonomía solo tras ~30 días con tasa de aprobación alta.**

Todo agente nuevo arranca en el nivel más restrictivo que aplique a su función (como mínimo, un nivel más restrictivo que su objetivo). Después de ~30 días de operación, si la tasa de aprobación de sus acciones es alta y sostenida, y los registros no muestran incidentes, se puede subir un nivel. La decisión de flexibilizar la documenta Fabian con la evidencia; nunca es automática.

## Reglas transversales

- **Separación de funciones**: planificador ≠ ejecutor ≠ validador ≠ logger. Ningún agente ejecuta el trabajo de otro sector ni revoca veredictos ajenos. **Excepción diseñada**: el Gerente General tiene autoridad de delegación y supervisión sobre los sectores (asigna tareas, exige avances, reprioriza dentro de los objetivos vigentes), pero no aprueba acciones irreversibles en nombre de Fabian — eso sigue siendo solo de Fabian.
- **Longitud máxima de cadena**: todo agente tiene un límite de pasos por tarea (anti-bucles) y un presupuesto en el gateway. El presupuesto vive en el gateway, no en el código del agente.
- **Identidad y permisos** determinan lo que *puede* hacer un agente; la autonomía determina lo que puede hacer *sin Fabian*: ver [identidades.md](identidades.md).
- Todo cambio de nivel de autonomía queda registrado en [auditoria.md](auditoria.md) como un cambio de gobernanza.
