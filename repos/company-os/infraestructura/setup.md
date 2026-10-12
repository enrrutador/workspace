# Puesta en marcha — levantar todo a costo $0 en hardware propio

> Guía paso a paso. Los comandos son **indicativos**: verificá las versiones vigentes de cada herramienta al momento de ejecutar (la documentación oficial manda). El objetivo es tener la pila completa corriendo en hardware propio sin gastar un peso.

## 0. Requisitos de hardware orientativos

| Componente | Mínimo viable | Recomendado |
|---|---|---|
| CPU | 4 núcleos modernos | 8+ núcleos |
| RAM | 16 GB | 32 GB |
| GPU | No indispensable para empezar | NVIDIA con 8–12 GB VRAM (modelos 8B–14B cuantizados) o 24 GB (32B) |
| Disco | 50 GB libres (los modelos pesan varios GB cada uno) | 200 GB+ SSD |
| Red | Conexión estable (para planes gratuitos y actualizaciones) | — |
| SO | Linux (Ubuntu/Debian) | — |

Sin GPU se puede empezar igual: modelos chicos en CPU para tareas acotadas, y planes gratuitos para lo que necesite más músculo. La GPU se justifica cuando el uso lo pida, no antes.

---

## 1. Ollama + primer modelo local

```bash
# Instalar Ollama (verificar el comando vigente en ollama.com)
curl -fsSL https://ollama.com/install.sh | sh

# Verificar
ollama --version

# Descargar y correr el primer modelo (elegir tamaño según tu hardware, ver modelos.md)
ollama pull qwen2.5:7b
ollama run qwen2.5:7b "Respondé en una línea: ¿estás funcionando?"
```

Si todo va bien, tenés inferencia local funcionando en `localhost:11434`.

---

## 2. Python + LangGraph

```bash
# Python 3.11+ (verificar versión vigente)
python3 --version

# Entorno virtual
python3 -m venv ~/company-os/venv
source ~/company-os/venv/bin/activate

# Instalar LangGraph y dependencias base
pip install --upgrade pip
pip install langgraph langchain-core httpx
```

Probar con un grafo mínimo (un nodo que llama al modelo local vía Ollama) antes de seguir: si el "hola mundo" agéntico no funciona, no tiene sentido levantar el resto.

---

## 3. LiteLLM proxy autohospedado con techos y cuotas

El proxy es el único punto de entrada de los agentes a los modelos. **La política de gasto vive acá.**

```bash
pip install 'litellm[proxy]'
```

Crear `litellm_config.yaml` (ejemplo mínimo — adaptar modelos y límites):

```yaml
model_list:
  - model_name: local-rapido
    litellm_params:
      model: ollama/qwen2.5:7b
      api_base: http://localhost:11434
  # - model_name: freetier-reserva   # descomentar cuando se configure un plan gratuito
  #   litellm_params:
  #     model: <proveedor>/<modelo>
  #     api_key: os.environ/FREETIER_API_KEY

general_settings:
  master_key: sk-cambiar-esta-clave   # cada agente usa su propia key derivada

# Techos: aunque el costo sea $0, las cuotas ya quedan configuradas
```

Levantar el proxy:

```bash
litellm --config litellm_config.yaml --port 4000
```

Verificar:

```bash
curl http://localhost:4000/v1/models -H "Authorization: Bearer sk-cambiar-esta-clave"
```

**Configurar desde el día uno** (aunque todo sea $0): techos por solicitud, por sesión y por clave; cortacircuitos; alertas de uso anómalo. Cuando el Guardián monitoree gasto, mirará acá.

---

## 4. Langfuse autohospedado (observabilidad)

```bash
# Clonar y levantar con Docker (verificar el repo y tags vigentes)
git clone https://github.com/langfuse/langfuse.git
cd langfuse
docker compose up -d
```

Abrir `http://localhost:3000`, crear cuenta local, generar las claves del proyecto y configurarlas en los agentes (variables de entorno `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`).

Verificación: correr el grafo mínimo del paso 2 y confirmar que la traza aparece en Langfuse.

---

## 5. Primer servidor MCP

Elegir algo simple y útil: un servidor MCP que exponga el sistema de archivos del workspace o una base SQLite local.

```bash
pip install mcp
```

Opciones para el primer servidor:

- **SDK oficial de Python** (`mcp`): escribir un servidor mínimo con 2–3 herramientas (p. ej. `leer_archivo`, `listar_directorio`) siguiendo el ejemplo de la documentación oficial.
- **Servidores de referencia**: la organización del protocolo publica servidores de ejemplo (filesystem, sqlite, etc.) listos para correr.

Conectar el servidor al grafo LangGraph del paso 2 como cliente MCP y verificar que el agente puede llamar una herramienta y recibir el resultado. **Ese es el momento "sistema nervioso"**: el agente ya no solo habla, actúa.

Registrar el servidor en el inventario (qué herramientas expone, qué agente lo usa, con qué permisos).

---

## 6. Bot de aprobaciones (Telegram/correo)

El bot es como Fabian aprueba lo irreversible desde el celular. Dos caminos, elegir uno:

**Opción A — Telegram (recomendado para empezar):**
1. Crear el bot con [@BotFather](https://t.me/BotFather) y guardar el token.
2. Escribir un script mínimo (Python + `python-telegram-bot`) que:
   - Reciba solicitudes de aprobación (acción pendiente + contexto) y las muestre con botones **Aprobar / Rechazar**.
   - Registre la decisión (quién, qué, cuándo) en el registro de solo adición.
3. Probarlo aprobando una acción simulada.

**Opción B — Correo:**
- El agente envía un correo con la acción pendiente; Fabian responde con "APROBADO" o "RECHAZADO" en el asunto; un lector procesa la respuesta y la registra.
- Más lento pero no requiere instalar nada.

En ambos casos: **toda decisión queda en el registro**. Sin registro, no existe.

---

## 7. Verificación end-to-end con el agente piloto

El piloto es **un agente, una función, una tarea medible** (candidatos: Conciliador o Control de Calidad — ver `../pipeline/`).

Lista de verificación:

- [ ] El agente corre en LangGraph y responde a través del LiteLLM proxy (no directo al modelo).
- [ ] Usa al menos una herramienta vía MCP.
- [ ] Sus trazas aparecen en Langfuse (qué hizo, con qué datos, cuánto tardó).
- [ ] Una acción irreversible de prueba llega al bot y **solo se ejecuta tras la aprobación de Fabian**.
- [ ] El registro de solo adición deja constancia de: qué leyó, qué hizo, quién aprobó.
- [ ] El Guardián (o una revisión manual equivalente) confirma techos configurados en el proxy.

Si los 6 puntos están en verde, la infraestructura está lista para la Fase 0. Recién ahí se escala a más agentes.

---

## Notas de mantenimiento

- **Actualizar con criterio**: fijar versiones de todo; actualizar una cosa por vez y re-correr la verificación del paso 7.
- **Copias de seguridad**: el registro de solo adición, la config del proxy y la base de Langfuse se respaldan. Perder los registros es perder la memoria institucional.
- **Documentar desvíos**: si un comando de esta guía no funcionó y usaste otro, anotarlo acá. La guía viva vale más que la guía perfecta.
