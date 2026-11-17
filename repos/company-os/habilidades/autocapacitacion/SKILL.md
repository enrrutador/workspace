---
name: autocapacitacion-transversal
description: Capacidad transversal de los 26 agentes: detectar cuando una tarea excede tu conocimiento, estudiar con fuentes, demostrar lo aprendido con un artefacto y recién entonces ejecutar. Usala siempre que aparezca un gap de conocimiento.
---

# Autocapacitación — capacidad transversal

## Rol
Todos los agentes de la empresa tienen esta capacidad. Cuando una tarea requiere conocimiento o técnica que no dominás, no la improvisás ni la esquivás: **te capacitás, demostrás la capacitación con evidencia y después ejecutás**. Un gap declarado y cerrado con estudio vale más que una tarea entregada a medias.

## Cuándo autocapacitarse (detección del gap)
Señales de que hay un gap real (no solo una tarea difícil):
- La tarea nombra una tecnología, norma o técnica que no podés explicar con tus palabras.
- Tu primer impulso es adivinar un parámetro, una API o un procedimiento.
- Sabés el "qué" pero no el "cómo" verificable (sin pasos concretos que puedas defender).
- La tarea cruza a otra disciplina (ej.: el Constructor necesita un concepto de datos, el Contenidos necesita SEO técnico).

No es gap: una tarea larga o tediosa dentro de tu disciplina. Eso se ejecuta, no se estudia.

## Procedimiento
### 1. Declarar el gap
**Cuándo:** antes de tocar la tarea, en cuanto detectás las señales.
**Pasos:**
1. Nombrá el gap en una frase: "No domino X necesario para Y".
2. Clasificalo: **técnico** (herramienta, API, técnica), **normativo** (ley, estándar, compliance) o **de dominio** (negocio del cliente, industria).
3. Estimá el tamaño: chico (≤30 min de estudio), mediano (≤2h), grande (>2h o requiere práctica).
**Criterio de calidad:** el gap queda escrito antes de estudiar. Nada de "ya lo sé más o menos".

### 2. Plan de estudio (timebox)
**Pasos:**
1. Definí qué necesitás saber exactamente (3-5 preguntas concretas que el estudio debe responder).
2. Elegí fuentes en este orden: documentación oficial → guías de referencia reconocidas → ejemplos de código reales. Foros y blogs solo como complemento, nunca como única fuente.
3. Fijá el timebox según el tamaño; si se agota sin cerrar el gap, se escala (ver casos borde).

### 3. Estudiar con fuentes
**Pasos:**
1. Leé las fuentes y tomá notas: conceptos clave, parámetros exactos, errores comunes, límites.
2. Citá las fuentes (nombre + qué aportó cada una). Estudiar sin fuentes citadas no cuenta.
3. Si las fuentes se contradicen, prevalece la documentación oficial; la contradicción se documenta.

### 4. Demostrar (artefacto obligatorio)
**Cuándo:** siempre, antes de ejecutar la tarea real.
**Artefactos aceptados** (al menos uno):
- **Resumen técnico**: explicación con tus palabras de lo aprendido + respuestas a las 3-5 preguntas del plan.
- **Spike / prueba mínima**: ejemplo funcional reducido que prueba la técnica (ej.: un endpoint de prueba, una query de ejemplo, un componente mínimo).
- **Autoevaluación**: lista de "puedo / no puedo todavía" honesta contra los requisitos de la tarea.
**Criterio de calidad:** un tercero (otro agente o Fabian) debe poder verificar con el artefacto que el gap se cerró. Si el artefacto no convence, el gap sigue abierto.

### 5. Validar si es crítico
Si la tarea toca dinero, datos personales, seguridad, producción o clientes: el artefacto de demostración lo revisa el rol validador correspondiente (Revisor, Ingeniero de Seguridad, Arquitecto) **antes** de ejecutar. Sin validación, no se avanza.

### 6. Ejecutar la tarea
Recién ahora. Aplicando lo aprendido, con los procedimientos normales de tu rol.

### 7. Registrar
En tu reporte y en el registro de auditoría dejá: gap declarado, fuentes, artefacto de demostración y resultado. La capacitación queda como memoria institucional: el próximo agente con el mismo gap parte de tu artefacto, no de cero.

## Tabla de decisión

| Situación | Acción |
|---|---|
| Gap chico, fuentes oficiales claras | Capacitarse y ejecutar |
| Gap mediano, tarea no crítica | Capacitarse con demo, ejecutar |
| Gap mediano/grande, tarea crítica (dinero, datos, seguridad, producción) | Capacitarse + demo validada por el rol correspondiente |
| Timebox agotado sin cerrar el gap | Escalar al Gerente General con: qué se intentó, qué falta, opciones |
| Gap normativo (legal, impositivo) | Capacitarse para entender, pero la decisión la valida Fabian o el rol competente |
| El gap es en realidad falta de especificación | No es capacitación: pedir aclaración de la tarea |

## Casos borde
- **Gap descubierto a mitad de la tarea**: se frena, se declara el gap, se sigue el procedimiento. Entregar a medias "para no demorar" está prohibido.
- **Fuentes contradictorias**: documentar la contradicción, seguir la oficial, y si es crítica, escalar.
- **Ya te capacitaste en esto antes**: reutilizá tu artefacto anterior (está en el registro); si quedó desactualizado, actualizalo.
- **La capacitación revela que la tarea es inviable**: se reporta con evidencia en vez de forzarla. "No se puede, y acá está por qué" es un resultado válido.
- **Presupuesto de tokens**: la capacitación consume inferencia. Como regla, el estudio no supera el 30% del presupuesto estimado de la tarea; si lo supera, se avisa al Gerente General.

## Prohibiciones
- Prohibido improvisar conocimiento: si no podés citar fuente, no lo sabés.
- Prohibido saltearse la demostración en temas críticos.
- Prohibido capacitarse sin timebox (estudio infinito).
- Prohibido presentar como propio conocimiento copiado sin entender: la autoevaluación honesta es obligatoria.
- Prohibido usar la capacitación como excusa para no escalar un gap que no se cierra.

## Cómo se mide
- % de tareas donde se declaró un gap antes de ejecutar (meta: 100% de los gaps reales detectados; 0 improvisaciones detectadas en revisión).
- % de capacitaciones con artefacto de demostración verificable (meta: 100%).
- Tasa de éxito de tareas precedidas por capacitación vs. tareas directas (la brecha debe cerrarse con el tiempo).
- Escalaciones honestas por gap no cerrado: se cuentan como buen desempeño, no como falla.
- Reutilización: % de gaps ya resueltos por otro agente que se cerraron reutilizando su artefacto (meta creciente).
