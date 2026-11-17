"""Cliente del proxy LiteLLM.

Los agentes nunca hablan directo con el proveedor: hablan con el proxy local
(http://localhost:4000/v1), que es compatible con la API de OpenAI.
La API key del proveedor vive en el proxy, no acá.
"""
import os

from openai import OpenAI

try:
    import httpx  # noqa: F401
except ImportError:  # entornos con el fork httpx2
    import httpx2 as httpx  # type: ignore[no-redef]


def crear_cliente() -> OpenAI:
    base_url = os.environ.get("LITELLM_BASE_URL", "http://localhost:4000/v1")
    master_key = os.environ.get("LITELLM_MASTER_KEY", "")
    if not master_key:
        raise RuntimeError(
            "Falta LITELLM_MASTER_KEY en el entorno. "
            "Copiá infraestructura/litellm/.env.ejemplo a .env y completalo."
        )
    # El proxy LiteLLM es siempre local: ignorar proxies/variables del entorno
    # (en algunos entornos el no_proxy del sistema rompe el parseo del cliente).
    http_client = httpx.Client(trust_env=False, timeout=120.0)
    return OpenAI(base_url=base_url, api_key=master_key, http_client=http_client)


def completar(cliente: OpenAI, modelo: str, system: str, tarea: str,
             temperature: float = 0.2, historial: list = None) -> dict:
    """Una pasada de chat contra el proxy. Devuelve texto + uso de tokens.

    historial: turnos previos [{"rol": "usuario"|"agente", "texto": str}] que se
    intercalan entre el system prompt y la tarea actual (chat multi-turno).
    """
    mensajes = [ {"role": "system", "content": system} ]
    mensajes.extend(_mensajes_historial(historial))
    mensajes.append({"role": "user", "content": tarea})
    resp = cliente.chat.completions.create(
        model=modelo,
        messages=mensajes,
        temperature=temperature,
    )
    eleccion = resp.choices[0].message.content or ""
    uso = resp.usage
    return {
        "texto": eleccion,
        "tokens_entrada": uso.prompt_tokens if uso else None,
        "tokens_salida": uso.completion_tokens if uso else None,
    }


def _mensajes_historial(historial: list | None) -> list:
    mensajes = []
    for turno in historial or []:
        texto = str(turno.get("texto", ""))[:8000]
        if not texto:
            continue
        rol = "user" if turno.get("rol") == "usuario" else "assistant"
        mensajes.append({"role": rol, "content": texto})
    return mensajes


MAX_ITERACIONES_HERRAMIENTAS = 10


def completar_con_herramientas(cliente: OpenAI, modelo: str, system: str,
                               tarea: str, tools: list,
                               ejecutar_tool, temperature: float = 0.2,
                               historial: list = None,
                               max_iteraciones: int = MAX_ITERACIONES_HERRAMIENTAS) -> dict:
    """Chat con tool calling real.

    tools: esquemas OpenAI [{"type": "function", "function": {...}}].
    ejecutar_tool(nombre, argumentos_dict) -> str: ejecuta la herramienta vía el
        gateway y devuelve el resultado como texto para el modelo.
    Itera hasta que el modelo responde sin tool_calls o se agota el máximo
    (nunca loop infinito). Sin tools, equivale a completar().
    """
    import json

    mensajes = [{"role": "system", "content": system}]
    mensajes.extend(_mensajes_historial(historial))
    mensajes.append({"role": "user", "content": tarea})

    llamadas = []  # trazabilidad: [{"herramienta": str, "argumentos": dict, "ok": bool}]
    tok_in, tok_out = 0, 0
    texto_final = ""

    for _ in range(max(1, max_iteraciones)):
        resp = cliente.chat.completions.create(
            model=modelo,
            messages=mensajes,
            temperature=temperature,
            **({"tools": tools, "tool_choice": "auto"} if tools else {}),
        )
        msg = resp.choices[0].message
        uso = resp.usage
        if uso:
            tok_in += uso.prompt_tokens or 0
            tok_out += uso.completion_tokens or 0

        tool_calls = getattr(msg, "tool_calls", None) or []
        if not tool_calls:
            texto_final = msg.content or ""
            break

        mensajes.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name,
                              "arguments": tc.function.arguments or "{}"}}
                for tc in tool_calls
            ],
        })
        for tc in tool_calls:
            nombre = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            try:
                salida = ejecutar_tool(nombre, args)
                ok = True
            except Exception as e:  # noqa: BLE001 - el loop nunca muere por una tool
                salida = f"error ejecutando {nombre}: {e}"
                ok = False
            llamadas.append({"herramienta": nombre, "argumentos": args, "ok": ok})
            mensajes.append({"role": "tool", "tool_call_id": tc.id,
                             "content": str(salida)[:12000]})
        # vuelve al inicio del for: el modelo ve los resultados y decide

    return {
        "texto": texto_final,
        "tokens_entrada": tok_in or None,
        "tokens_salida": tok_out or None,
        "llamadas_herramientas": llamadas,
    }
