# Dashboard — consola de la empresa

El tablero de comando de Fabian: manejar y configurar toda la empresa desde el
navegador, sin tocar la terminal.

## Iniciar

```bash
# Desde la raíz del repo
python3 dashboard/servidor.py

# Abrir: http://localhost:8080
```

Solo usa la biblioteca estándar de Python: no instala nada nuevo.

## Qué incluye

| Vista | Qué hace |
|---|---|
| **Agentes** | Los 26 agentes agrupados por área, con buscador. Cada tarjeta muestra avatar, misión en 2 líneas, modelo efectivo e indicador de actividad ("activo hace X"). Clic → se abre el **chat** en un panel lateral: múltiples mensajes con historial (Enter para enviar), **selector de modelo** en la caja de mensajería, indicador de "escribiendo", respuestas con formato (títulos, listas, tablas, código) y botón Detener. El Gerente General orquesta por defecto (delegación en vivo con traza); con **Directa** se le pregunta sin delegar (1 llamada, más rápido). Los chats y las orquestaciones sobreviven a recargar la página. |
| **Pipeline** | Ejecuta las etapas del pipeline (tesis, validación, construcción, comercial, producto) con un objetivo en lenguaje natural. Corre en segundo plano con veredictos (SEGUIR/MATAR, VALIDADO/DESCARTADO), traza y artefactos expandibles. El despliegue frena en `PENDIENTE_APROBACION_FABIAN` salvo que tildes la aprobación. |
| **Actividad** | Feed de ejecuciones auditadas: quién hizo qué, cuándo (tiempo relativo), con qué modelo y cuántos tokens. Filtrable por agente; clic en un evento para ver tarea y respuesta completas. |
| **Empresa** | Estado de un vistazo: agentes, ejecuciones auditadas, productos en portfolio, proveedor conectado. Pipeline de producto como stepper visual (etapas 0–9). |
| **Configuración** | Tu API key del **proveedor** y la clave maestra **local** por separado (antes se confundían), más los modelos (base / razonamiento / ligero) y la URL base. Al guardar, los nombres de modelo se sincronizan para el proxy y el modo directo. **Probar conexión** verifica en vivo que cada modelo configurado responde (detecta modelos retirados, p. ej. HTTP 410, antes de ejecutar). |

En móvil la navegación pasa a barra inferior y el chat ocupa toda la pantalla.

## Cómo funciona

```
navegador ──▶ dashboard/servidor.py ──▶ runtime/nucleo ──▶ proxy LiteLLM ──▶ tu proveedor
              (http://localhost:8080)     (agentes + auditoría)   (localhost:4000)
```

El dashboard **no reemplaza** al proxy: los agentes siguen saliendo por LiteLLM.
El dashboard solo les habla y les muestra la configuración del `.env`.

**Precedencia de configuración:** lo que guardás en Configuración
(archivo `infraestructura/litellm/.env`) rige de inmediato para las próximas
ejecuciones y es lo que muestran las tarjetas. Las variables de entorno del
proceso que el archivo no menciona (p. ej. los secretos de Kaggle) se respetan
tal cual.

## Seguridad

- Escucha **solo en 127.0.0.1**: accesible únicamente desde tu máquina.
- **Nunca lo expongas a internet** (sin autenticación, la configuración incluye secretos).
- La API key se guarda en `infraestructura/litellm/.env` (ignorado por git) y la
  API del dashboard la devuelve enmascarada.
