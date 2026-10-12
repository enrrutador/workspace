# Identidades no-humanas

*Fuente de verdad: [Diseño operativo v1](../empresa/diseno-operativo-v1.md) · Fecha: 2026-10-07*

## Principio

**Cada agente es una identidad no-humana propia.** Igual que un empleado tiene su usuario y su tarjeta de acceso, cada uno de los 26 agentes tiene credenciales propias, permisos mínimos y un dueño humano nombrado. **El dueño de cada identidad es Fabian**, para siempre.

Lo que una identidad *puede* hacer está limitado por sus permisos; lo que puede hacer *sin aprobación* está limitado por su nivel de autonomía ([autonomia.md](autonomia.md)). Son dos capas distintas y ambas aplican siempre.

## Reglas de identidad

1. **Credenciales propias por agente**: ningún agente comparte credenciales con otro, ni usa las credenciales personales de Fabian para operar.
2. **Permisos mínimos por tarea**: cada identidad solo puede leer y escribir lo que su función exige. Se inventaría qué puede leer y escribir cada agente en sus primeras 48h; las escrituras no esenciales se revocan.
3. **Tokens de corta vida**: las credenciales operativas expiran rápido y se renuevan automáticamente. Un token filtrado deja de servir en minutos, no en meses.
4. **Nunca hereda privilegios de Fabian**: que Fabian sea el dueño no significa que el agente actúe con sus permisos. La identidad del agente tiene sus propios límites, siempre por debajo de los del humano.
5. **Ningún agente tiene poder sobre otro**: una identidad no puede modificar, suplantar ni aprobar acciones de otra identidad. Planificador ≠ ejecutor ≠ validador ≠ logger.

## Bóveda de credenciales

Las credenciales de clientes y de servicios externos viven en una **bóveda de secretos**, no en el código ni en los prompts de los agentes:

- Cada secreto se entrega a un agente con **mínimo privilegio**: solo el secreto que necesita, solo para la tarea que lo necesita, solo durante el tiempo que lo necesita.
- El Responsable de Activación gestiona la bóveda de credenciales de clientes durante la configuración; el Guardián audita accesos anómalos.
- Los secretos nunca se registran en texto plano ([auditoria.md](auditoria.md)): en los registros aparecen como referencias ocultas.

## Rotación y revocación

- **Rotación programada**: los tokens y secretos se rotan en intervalos definidos (corto para servicios críticos, p. ej. cobros y accesos a producción).
- **Rotación ante incidentes**: si hay sospecha de filtración, el secreto se rota de inmediato y se revoca el anterior.
- **Revocación inmediata**: ante comportamiento anómalo de un agente, su identidad se puede revocar sin afectar a las demás. Revocar una identidad no borra sus registros: la trazabilidad se conserva.

## Interruptor de emergencia

El **Guardián** es el dueño operativo del interruptor de emergencia: monitorea infra y costo de tokens, y ante gasto anormal o comportamiento anómalo **puede frenar un agente** (revocar temporalmente su capacidad de actuar). Opera con límites estrictos: su día a día es solo lectura + freno de emergencia.

- Activar el interruptor de emergencia genera una alerta inmediata a Fabian y un registro en [auditoria.md](auditoria.md).
- Solo Fabian puede rehabilitar al agente frenado, después de revisar qué pasó.
- Es de emergencia, no de gestión: no se usa para pausar trabajo normal.

## Gobernanza mínima viable (primeras 48h de cada agente)

1. Inventariar qué puede leer y escribir; revocar escrituras no esenciales.
2. Clasificar sus acciones: reversibles vs. irreversibles.
3. Longitud máxima de cadena (anti-loops) + presupuesto en el gateway.
4. Bot de aprobación para lo irreversible ([aprobaciones.md](aprobaciones.md)).
5. Registro de solo adición de todo (qué leyó, qué hizo, quién aprobó) ([auditoria.md](auditoria.md)).
6. Equipo rojo básico: intentar romperlo antes de que lo haga un cliente.
