# Matriz de aprobaciones

*Fuente de verdad: [Diseño operativo v1](../empresa/diseno-operativo-v1.md) · Fecha: 2026-10-07*

Fabian es el único humano y el único que puede aprobar lo irreversible. Este documento define qué requiere su aprobación previa, cómo se pide y qué pasa cuando no está disponible.

## Qué requiere aprobación previa de Fabian (in-the-loop)

Todo lo irreversible. En concreto:

1. **Dinero**: cualquier cobro, débito, reembolso, ajuste o transferencia. Montos máximos por transacción y por día, definidos por Fabian. *Dinero real = in-the-loop siempre al principio.*
2. **Despliegues**: cualquier despliegue a producción (Responsable de Despliegues). Staging y entornos de prueba no requieren aprobación.
3. **Envíos masivos**: campañas de correo, mensajes o publicaciones enviadas en volumen (Contacto Inicial, Contenidos). El primer envío de cada segmento/campaña nueva requiere aprobación; después rige el esquema on-the-loop definido en [autonomia.md](autonomia.md).
4. **Cambios de acceso**: otorgar, modificar o revocar accesos a sistemas, datos o credenciales (incluye credenciales de clientes en el vault).
5. **Publicación de contenido**: publicar posteos, newsletters, documentos públicos o cualquier contenido que represente a la empresa (Contenidos). Fabian revisa antes de publicar, siempre.
6. **Negociación fuera de matriz**: Calificador negocia solo dentro de la matriz pre-aprobada (descuentos, condiciones). Cualquier término fuera de esa matriz requiere aprobación.
7. **Cierre/discontinuación de productos**: dar de baja o pausar un producto, especialmente con clientes activos (proceso de discontinuación: comunicación, migración, reembolsos).
8. **Compuertas del pipeline de producto**: abrir y cerrar cada etapa del pipeline (búsqueda → tesis → validación → construcción → uso interno → lanzamiento → comercial → activación → operación). Fabian abre y cierra cada etapa.
9. **Cambios de gobernanza**: subir o bajar el nivel de autonomía de un agente, otorgar nuevos permisos a una identidad, cambiar montos máximos.

**SLA en compuertas del pipeline: Fabian decide en 48h o la etapa se pausa sola.** El pipeline nunca avanza por silencio.

## Aprobaciones por lote

Lo irreversible se acumula en una **cola de aprobaciones** y Fabian lo resuelve en **ventanas diarias** (mañana y tarde), en vez de interrumpirlo todo el día:

- El canal es un **bot propio de Telegram o correo** (costo $0): cada solicitud llega con contexto resumido (qué se pide, por qué, riesgo, monto si aplica) y botones de aprobar/rechazar.
- Cada solicitud en la cola tiene prioridad y vencimiento. Si una solicitud vence sin respuesta, **no se ejecuta** (el valor por defecto es "no").
- La decisión de Fabian (aprobar/rechazar, con motivo) queda registrada en [auditoria.md](auditoria.md).
- El **presupuesto semanal de atención de Fabian** es el WIP maestro: la cantidad de solicitudes en cola se estrangula a sus horas reales. Si la cola crece más rápido de lo que puede procesar, el Gerente General reduce el ritmo de las funciones que la alimentan.

## Modo offline

Si Fabian no está disponible (fuera de horario, sin conexión):

- Los agentes **siguen operando con lo autónomo** (Nivel 1) y con lo on-the-loop ya validado.
- **Todo lo irreversible se encola.** Nada irreversible se ejecuta sin él. Sin excepciones.
- Las escalaciones urgentes (soporte, temas sensibles, fuera de guion) van a la cola prioritaria de Fabian; si el caso no puede esperar, se aplica el manual de contingencia del agente (p. ej. Soporte Nivel 1 ofrece disculpa y compromiso de respuesta, nunca promete lo que no puede cumplir).

## Escalación

Escalación = Fabian. Soporte, ventas y cualquier caso fuera de guion terminan en él. Todo agente que hable con personas **se identifica como IA** (EU AI Act art. 50, exigible desde agosto 2026).

- **Soporte Nivel 1** escala ante frustración del cliente, temas sensibles o cualquier cosa fuera de sus guías aprobadas.
- **Escalamiento** es el camino dedicado: deriva a Fabian y mantiene al cliente informado mientras tanto.
- **Calificador** escala negociaciones fuera de matriz y señales de abandono en cuentas clave.
- El diseño de cada agente debe **minimizar escalaciones** con reglas claras, pero el camino al humano siempre existe (lección de Klarna 2024–2026: recortar humanos de más degradó la calidad y hubo que recontratar).

## Frenos de emergencia (bloquean, no aprueban)

Tres agentes pueden **frenar** (nunca aprobar en nombre de Fabian). Todo freno se registra, se alerta de inmediato y se levanta corrigiendo la causa o con decisión explícita de Fabian:

1. **Guardián** — interruptor de emergencia: frena agentes con gasto o comportamiento anormal según umbrales de Fabian.
2. **Ingeniero de Seguridad** — frena un despliegue por riesgo crítico de seguridad documentado.
3. **SRE** — con el error budget agotado se frenan lanzamientos no críticos hasta recuperar (lo decide con el Gerente General).

## Qué NO hacer

- Nunca aprobar por silencio: la falta de respuesta no es aprobación.
- Nunca encadenar aprobaciones ("aprobado una vez, aprobado siempre"): cada acción irreversible se aprueba por separado, salvo que Fabian defina una regla explícita con límites (monto, frecuencia, ventana).
- Nunca dejar que un agente apruebe en nombre de Fabian, ni siquiera el Gerente General.
