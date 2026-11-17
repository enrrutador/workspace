# Cómo contribuir

Este repo es la definición operativa de la empresa. Lo mantienen Fabian y sus
agentes de IA.

## Quién puede cambiar qué

- **Fabian**: todo.
- **Agentes**: solo lo que su ficha les permite, siempre en rama y con solicitud de cambios. Ningún agente sube directo a `main`.

## Flujo

1. Creá una rama desde `main`: `docs/<tema>` o `agente/<nombre-del-agente>`.
2. Hacé el cambio. Si tocás `agentes/`, `pipeline/` o `gobernanza/`, actualizá
   también los índices y READMEs que los mencionen.
3. Verificá los enlaces relativos: ninguno puede apuntar fuera del repo ni a un
   archivo que no exista.
4. Abrí una solicitud de cambios con la plantilla. Cambios en fichas de agentes o en el
   pipeline requieren aprobación de Fabian.

## Convenciones

- Markdown en español rioplatense, tono directo.
- Un concepto por archivo; los índices solo enlazan, no duplican contenido.
- Sin secretos en el repo: tokens, contraseñas y claves van en la bóveda de
  credenciales, nunca en un commit.
