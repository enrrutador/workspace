# ARCA

Arquitectura cognitiva local de recursos mínimos. El nombre "LLM" es heredado: **ARCA no entrena pesos ni los crece** — su inteligencia se construye en tiempo de respuesta recuperando evidencia real de la web y de sus memorias persistentes, y respondiendo citando fuentes.

## Filosofía

- **Peso fijo**: el modelo recurrente incluido (~2 MB) nunca cambia de tamaño ni se reentrena en producción.
- **Corre en un teléfono de gama baja**: presupuesto objetivo ≤ 1 GB de RAM (típico: ~40 MB) y ≤ 16 GB de disco (típico: < 500 MB con backups).
- **Sin dependencias de LLMs externos**: sin claves API, sin servicios de IA en la nube. Solo Python 3.12 + numpy + la stdlib.
- **No inventa**: si no hay evidencia suficiente, lo dice y pide reformular. Nunca genera texto verosímil sin fuente.
- **Trazable**: cada respuesta expone `trace` (pasos) y las URLs usadas.

## Cómo responde ARCA

```
pregunta
  ├─ plantilla interna de agente host → respuesta determinista instantánea
  ├─ saludo / frase social → plantilla local en español
  ├─ contexto ("qué hora es" / "qué día es hoy") → reloj local del sistema
  ├─ enseñanza ("recuerda el procedimiento X: 1) ... 2) ...") → memoria procedural
  ├─ hecho ("recuerda que...") / cálculo → asistente cognitivo simbólico
  ├─ continuación ("contame más", "¿y cuándo...?") → responde desde el
  │    GRAFO de evidencia local del tema activo (sin red, instantáneo)
  └─ pregunta con contenido:
        1. definicionales ("¿qué es X?", "¿cómo funciona X?") → web primero;
           resto → memoria primero
        2. búsqueda escalonada con degradación elegante:
           resumen REST de Wikipedia → títulos → full-text (con corrección
           ortográfica por sugerencia) → DuckDuckGo; un motor caído no tira
           los demás
        3. gate conceptual: la evidencia debe contener el concepto completo
           (matching difuso tolerante a typos y acentos) en una oración
           definitoria; un documento cuyo título ES el concepto respalda el
           caso
        4. desambiguación activa: si el concepto tiene varios sentidos
           (Barco la embarcación vs Valentín Barco el futbolista), ARCA
           pregunta a cuál se refiere y guarda tu elección en la sesión
        5. minería a grafo de evidencia: cada documento leído se convierte
           en conceptos + triplas tipadas + pasajes por aspecto
           (definición/tipos/usos/mecanismo/historia)
        6. composición en prosa: el planificador (búsqueda A*) llena los
           slots discursivos con oraciones reales trazables a su fuente,
           con conectores naturales; respeta el tema sin inventar
        7. sin evidencia → mensaje honesto pidiendo reformular
```

La inteligencia emerge de la **experiencia indexada**: cada consulta enriquece
un grafo en disco (SQLite) que ARCA consulta luego al instante, sin pesos ni
entrenamiento. Comando `arca index` mina masivamente los documentos cacheados.

Cada documento descargado queda en memoria SQLite (dedup por URL): repetir un tema responde desde caché local y ARCA "aprende" con el uso sin tocar sus pesos.

## Memorias persistentes

| Tipo | Tabla / archivo | Uso |
|---|---|---|
| Semántica | `assertions` | hechos versionados (`recuerda que...`) |
| Procedural | `procedures` | pasos enseñados por el usuario, recuperables por "cómo X" |
| Evidencia web | `documents` | cache de páginas (poda automática a `--max-docs`) |
| Episódica | `episodes` | registro auditable de cada interacción |
| Trabajo | `*.sessions.json` | contexto conversacional por sesión |

Todo el estado vive en `arca.db` + el JSON de sesiones: dos archivos portables (migrables al teléfono con `arca export`).

## Flujo completo local

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .

# (opcional) el modelo nativo sigue disponible como componente aislado
arca-native-lm train --text corpus.txt --output models/arca-native.npz --epochs 10

arca-serve --model models/arca-native.npz --db arca.db
```

Servidor: `http://127.0.0.1:8787/v1`

### Flags del servidor

```bash
arca-serve --model models/arca-native.npz --db arca.db \
  --max-docs 500          # tope de documentos web cacheados (poda automática)
  --fetch-bytes 500000    # presupuesto de descarga por página
  --answer-chars 1200     # largo máximo de respuesta compuesta
  --max-web-docs 3        # páginas fetcheadas por pregunta
  --backup-dir backups    # snapshot SQLite consistente al iniciar
  --keep-backups 7        # retención rotativa
```

## Integración con OpenCode

El endpoint implementa `GET /v1/models`, `POST /v1/chat/completions` (**con streaming SSE y contenido como array de partes**, el formato que envía el AI-SDK), conserva sesiones vía header `X-ARCA-Session`, devuelve trazas y telemetría en el campo `arca`.

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "arca": {
      "npm": "@ai-sdk/openai-compatible",
      "options": { "baseURL": "http://127.0.0.1:8787/v1" },
      "models": { "arca-native": { "name": "ARCA Native" } }
    }
  }
}
```

Seleccioná `arca/arca-native` en OpenCode.

## CLI

```bash
arca chat                                   # REPL interactivo
arca ask "¿Qué es Kubernetes?" --trace      # una consulta con trazabilidad
arca export --db arca.db --out memoria.arcamem   # portar memoria (ej: al teléfono)
arca import memoria.arcamem                 # restaurar en otro dispositivo
```

### Enseñar procedimientos

Por API o chat:

```
recuerda el procedimiento desplegar app: 1) compilar el proyecto 2) correr los tests 3) publicar la imagen
```

Luego: `"cómo es el procedimiento desplegar app?"` lo recupera instantáneamente, con contador de usos.

## Estado honesto

Las respuestas son **extractivas** (oraciones reales citando fuentes), no redactadas fluidamente: es el compromiso de ser autosuficiente sin pesos externos. La búsqueda usa DuckDuckGo Lite; fallos de red derivan en caché local o pedido de reformulación, nunca en invención. Antes de producción en un teléfono concreto hay que medir latencia de red, batería y estabilidad.

## Tests

```bash
python -m unittest discover tests   # 27 tests unitarios
```
