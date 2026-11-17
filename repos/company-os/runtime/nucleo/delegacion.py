"""Protocolo de delegación del Gerente General.

El GG incluye bloques DELEGAR: en su respuesta cuando una tarea requiere
trabajo de especialistas. Este módulo los extrae, valida y ejecuta, y le
devuelve los resultados al GG para la consolidación final.

Formato del bloque (lo genera el GG en su respuesta):

    DELEGAR:
    - agente: <slug>
      tarea: "<tarea en una línea>"

Profundidad máxima: 1 (los delegados no pueden delegar a su vez).
"""
import re

MAX_DELEGACIONES = 5
MAX_CHARS_RESULTADO = 6000

_BLOQUE = re.compile(
    r"^DELEGAR:\s*$\n((?:^[ \t]*-\s*agente:\s*\S+\s*$\n(?:^[ \t]+tarea:\s*.+$\n?)?)+)",
    re.IGNORECASE | re.MULTILINE,
)
_ITEM = re.compile(
    r"^[ \t]*-\s*agente:\s*(\S+)\s*$\n^[ \t]+tarea:\s*(.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def extraer_delegaciones(texto: str) -> list:
    """Devuelve [(slug, tarea), ...] en orden. Máximo MAX_DELEGACIONES."""
    delegaciones = []
    for bloque in _BLOQUE.findall(texto or ""):
        for slug, tarea in _ITEM.findall(bloque):
            tarea = tarea.strip().strip('"').strip("'").strip()
            slug = slug.strip().lower()
            if slug and tarea:
                delegaciones.append((slug, tarea))
    return delegaciones[:MAX_DELEGACIONES]


def quitar_bloques(texto: str) -> str:
    """Saca los bloques DELEGAR: del texto (para mostrar el plan limpio)."""
    return _BLOQUE.sub("", texto or "").strip()


def orquestar_eventos(tarea: str, cliente, forzar_modelo: str = "",
                      historial: list = None):
    """Versión en streaming de orquestar(): genera eventos para SSE.

    Eventos (dicts serializables):
    - plan: {"tipo", "texto", "delega"}
    - delegacion_inicio: {"tipo", "agente", "tarea", "indice", "total"}
    - delegacion_fin: {"tipo", "agente", "tarea", "ok", "modelo"/"error",
      "texto", "indice", "total"}
    - consolidando: {"tipo"}
    - final: {"tipo", "texto", "delega", "delegaciones"}
    """
    from . import agente as modulo_agente

    plan_r = modulo_agente.ejecutar_agente("gerente-general", tarea, cliente,
                                          forzar_modelo=forzar_modelo,
                                          historial=historial)
    delegaciones = extraer_delegaciones(plan_r["texto"])
    plan_limpio = quitar_bloques(plan_r["texto"])
    yield {"tipo": "plan", "texto": plan_limpio, "delega": bool(delegaciones)}

    if not delegaciones:
        yield {"tipo": "final", "texto": plan_r["texto"], "delega": False,
               "delegaciones": []}
        return

    resultados = []
    traza = []
    total = len(delegaciones)
    for i, (slug, subtarea) in enumerate(delegaciones):
        yield {"tipo": "delegacion_inicio", "agente": slug, "tarea": subtarea,
               "indice": i + 1, "total": total}
        if slug not in modulo_agente.REGISTRO:
            item = {"agente": slug, "tarea": subtarea, "ok": False,
                    "error": f"agente desconocido: {slug}"}
        else:
            try:
                r = modulo_agente.ejecutar_agente(slug, subtarea, cliente,
                                                 forzar_modelo=forzar_modelo)
                resultados.append((slug, subtarea, r["texto"]))
                item = {"agente": slug, "tarea": subtarea, "ok": True,
                        "modelo": r["modelo"], "texto": r["texto"][:2000]}
            except Exception as e:  # noqa: BLE001 - se reporta en la traza
                item = {"agente": slug, "tarea": subtarea, "ok": False,
                        "error": str(e)[:300]}
        traza.append(item)
        yield {"tipo": "delegacion_fin", "indice": i + 1, "total": total, **item}

    yield {"tipo": "consolidando"}
    contexto = "\n\n".join(
        f"--- {slug} ---\nTarea delegada: {t}\nResultado:\n{txt[:MAX_CHARS_RESULTADO]}"
        for slug, t, txt in resultados
    )
    consolidacion = (
        f"Tarea original del dueño: {tarea}\n\n"
        f"Delegaste este trabajo y estos fueron los resultados:\n{contexto}\n\n"
        "Ahora consolidá la respuesta final para el dueño: directa, accionable, "
        "en español rioplatense. No repitas el bloque DELEGAR."
    )
    final_r = modulo_agente.ejecutar_agente("gerente-general", consolidacion, cliente,
                                           forzar_modelo=forzar_modelo)
    yield {"tipo": "final", "texto": final_r["texto"], "delega": True,
           "delegaciones": traza}


def orquestar(tarea: str, cliente, forzar_modelo: str = "") -> dict:
    """El Gerente General planifica, delega a especialistas y consolida.

    forzar_modelo: si se indica, TODAS las llamadas (GG + delegados) usan ese
    modelo en vez del de cada agente.

    Devuelve {"texto", "plan", "delegaciones": [...], "delega": bool}.
    Cada delegación: {"agente", "tarea", "ok", "modelo"/"error", "texto"}.
    """
    from . import agente as modulo_agente

    plan_r = modulo_agente.ejecutar_agente("gerente-general", tarea, cliente,
                                          forzar_modelo=forzar_modelo)
    delegaciones = extraer_delegaciones(plan_r["texto"])
    plan_limpio = quitar_bloques(plan_r["texto"])

    if not delegaciones:
        return {
            "texto": plan_r["texto"],
            "plan": plan_limpio,
            "delegaciones": [],
            "delega": False,
        }

    resultados = []
    traza = []
    for slug, subtarea in delegaciones:
        if slug not in modulo_agente.REGISTRO:
            traza.append({"agente": slug, "tarea": subtarea, "ok": False,
                          "error": f"agente desconocido: {slug}"})
            continue
        try:
            r = modulo_agente.ejecutar_agente(slug, subtarea, cliente,
                                             forzar_modelo=forzar_modelo)
            resultados.append((slug, subtarea, r["texto"]))
            traza.append({"agente": slug, "tarea": subtarea, "ok": True,
                          "modelo": r["modelo"],
                          "texto": r["texto"][:2000]})
        except Exception as e:  # noqa: BLE001 - se reporta en la traza
            traza.append({"agente": slug, "tarea": subtarea, "ok": False,
                          "error": str(e)[:300]})

    contexto = "\n\n".join(
        f"--- {slug} ---\nTarea delegada: {t}\nResultado:\n{txt[:MAX_CHARS_RESULTADO]}"
        for slug, t, txt in resultados
    )
    consolidacion = (
        f"Tarea original del dueño: {tarea}\n\n"
        f"Delegaste este trabajo y estos fueron los resultados:\n{contexto}\n\n"
        "Ahora consolidá la respuesta final para el dueño: directa, accionable, "
        "en español rioplatense. No repitas el bloque DELEGAR."
    )
    final_r = modulo_agente.ejecutar_agente("gerente-general", consolidacion, cliente,
                                           forzar_modelo=forzar_modelo)
    return {
        "texto": final_r["texto"],
        "plan": plan_limpio,
        "delegaciones": traza,
        "delega": True,
    }
