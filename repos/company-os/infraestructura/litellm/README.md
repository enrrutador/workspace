# Conector de modelos — LiteLLM

Este es el enchufe entre la empresa y los proveedores de LLM. Un solo proxy local
habla con el proveedor que elijas; los 26 agentes hablan solo con el proxy.
Cambiar de proveedor o de modelo = cambiar dos líneas del `.env`, sin tocar código.

## Puesta en marcha (5 minutos)

```bash
cd infraestructura/litellm

# 1. Instalar el proxy
pip install 'litellm[proxy]'

# 2. Crear tu configuración (la key vive acá, solo en tu máquina)
cp .env.ejemplo .env
# Editá .env: pegá tu LLM_API_KEY y elegí tus MODELO_*

# 3. Levantar el proxy
litellm --config config.yaml --port 4000
```

Verificá que responde:

```bash
curl http://localhost:4000/v1/models \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY"
```

## Qué modelo poner en cada variable

| Variable | Uso | Sugerencia |
|---|---|---|
| `MODELO_EMPRESA_BASE` | Agente por defecto | Tu modelo equilibrado (ej. `openai/gpt-4o-mini`) |
| `MODELO_EMPRESA_RAZONAMIENTO` | Análisis pesado, decisiones, equipo rojo | Tu modelo más capaz (ej. `openai/gpt-4o`) |
| `MODELO_EMPRESA_LIGERO` | Alto volumen, bajo costo (Soporte N1, borradores) | El más barato que te sirva |

Formato: `<proveedor>/<modelo>` según la convención de LiteLLM.
Ejemplos: `anthropic/claude-sonnet-4-20250514`, `openrouter/deepseek/deepseek-chat`,
`gemini/gemini-2.0-flash`.

## Seguridad

- El `.env` está en el `.gitignore`: tu key **nunca** se sube al repo.
- No pegues la key en el chat ni en ningún documento.
- La `LITELLM_MASTER_KEY` es solo para que los agentes se autentiquen contra
  tu proxy local; no es la key del proveedor y no sale de tu máquina.

## Costo

El proxy y todo el software son costo $0. El consumo de inferencia depende del
proveedor y modelo que elijas: corre por tu cuenta, con tu key. Monitoreá tu
uso en el panel de tu proveedor.
