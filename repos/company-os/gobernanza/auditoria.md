# Auditoría y registros

*Fuente de verdad: [Diseño operativo v1](../empresa/diseno-operativo-v1.md) · Fecha: 2026-10-07*

Principio: **todo queda registrado. Sin registro, no existe.** La empresa responde por lo que hagan sus agentes; los registros son la prueba.

## Qué se registra de cada acción

Cada acción de cada agente registra, como mínimo:

- **Marca de tiempo**: fecha y hora exacta de la acción.
- **Agente**: qué identidad no-humana actuó ([identidades.md](identidades.md)).
- **Acción**: qué hizo, en términos verificables (no solo "procesó datos").
- **Resumen de entradas**: con qué información trabajó, resumida (no el contenido crudo completo).
- **Datos accedidos**: qué leyó y qué escribió (qué sistemas, qué registros).
- **Estado de aprobación**: autónomo / on-the-loop (revisado por Fabian: sí/no, cuándo) / in-the-loop (aprobado por Fabian: sí/no, cuándo, con qué alcance).
- **Resultado**: éxito, fallo, escalación; y a qué derivó (siguiente acción, caso, cola de aprobación).

## Registro de solo adición e inmutable

- El registro es **de solo adición**: se agrega, nunca se edita ni se borra. Una corrección se registra como una nueva entrada que referencia a la anterior.
- Ningún agente puede modificar ni eliminar entradas del registro, ni siquiera las propias. Escribir en el registro y ejecutar acciones son permisos separados (registrador ≠ ejecutor).
- Si un agente factura o mueve dinero: facturación electrónica ARCA desde el día uno, todo trazable contra el registro.

## Retención y ocultamiento de datos personales

- **Ocultar datos personales antes de registrar**: los datos personales (nombres, correos, teléfonos, documentos, datos de pago) se ocultan o se reemplazan por referencias antes de entrar al registro. El registro dice *qué tipo de dato* se usó, no el dato.
- Los secretos y credenciales nunca aparecen en texto plano: solo referencias a la bóveda de secretos ([identidades.md](identidades.md)).
- **Retención**: los registros se conservan por el plazo que exija la normativa aplicable (fiscal, protección de datos) y por el tiempo que la operación necesite para investigar incidentes. Definir los plazos concretos con asesoría legal antes del primer cliente; documentarlos acá cuando existan.
- Riesgo conocido: fuga de datos en registros e inyección de prompts / envenenamiento de herramientas → el ocultamiento de datos personales y el uso de MCP solo de fuentes confiables son mitigaciones obligatorias, no opcionales.

## Tenancy: aislamiento por producto y por cliente

- **Ningún agente cruza datos entre clientes.** Cada producto y cada cliente opera en su propio tenant lógico: sus datos, sus credenciales, sus registros.
- El CRM, la bóveda de secretos y los registros están particionados por tenant. Una consulta de un agente solo ve el tenant para el que está autorizado en esa tarea.
- El aislamiento se verifica en el equipo rojo inicial de cada agente y en revisiones periódicas: intentar acceder a datos de otro tenant debe fallar y debe quedar registrado el intento.

## Los registros como memoria institucional

Fabian es el único humano: si él no está, la empresa sigue operando con agentes. Los registros son la **memoria institucional** que permite retomar, investigar y aprender:

- **Manuales operativos por agente**: documentan cómo opera cada agente, sus límites y sus procedimientos de contingencia. Son el punto único de fallo declarado: si algo le pasa a Fabian, cualquiera (o un futuro él) retoma desde los manuales operativos + los registros.
- Los reportes del Analista y del Responsable de Informes se construyen sobre los registros, no sobre memoria de agentes.
- Revisión periódica: los registros alimentan la revisión de niveles de autonomía ([autonomia.md](autonomia.md) — regla de oro de los ~30 días) y la detección de patrones anómalos (Guardián).
