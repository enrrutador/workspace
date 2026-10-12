"""Registro de auditoría append-only de cada ejecución.

Cada corrida de un agente deja una línea JSONL con marca de tiempo, agente,
modelo, tarea y uso de tokens. Es la fuente de verdad operativa
(ver gobernanza/auditoria.md).
"""
import json
import os
from datetime import datetime, timezone

DIR_REGISTRO = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "registro")
)
ARCHIVO = os.path.join(DIR_REGISTRO, "auditoria.jsonl")


def registrar(agente: str, modelo: str, tarea: str, respuesta: str,
              tokens_entrada=None, tokens_salida=None, **extras) -> None:
    """Registra un evento. extras admite campos nuevos (herramienta, riesgo,
    decision_politica, tenant_id, execution_id, ...) sin romper lectores viejos."""
    os.makedirs(DIR_REGISTRO, exist_ok=True)
    evento = {
        "marca_tiempo": datetime.now(timezone.utc).isoformat(),
        "agente": agente,
        "modelo": modelo,
        "tarea": tarea[:500],
        "respuesta": respuesta[:4000],
        "tokens_entrada": tokens_entrada,
        "tokens_salida": tokens_salida,
    }
    for k, v in extras.items():
        if v is None or v == "":
            continue
        evento[k] = v() if callable(v) else v
    with open(ARCHIVO, "a", encoding="utf-8") as f:
        f.write(json.dumps(evento, ensure_ascii=False) + "\n")
