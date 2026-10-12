#!/usr/bin/env python3
"""Pruebas del protocolo de delegación del Gerente General.

1. Parseo de bloques DELEGAR: (válidos, múltiples, tope de 5, sin bloque,
   formato roto, quitar_bloques).
2. Flujo orquestar() contra mock: el GG delega a 2 especialistas, se ejecutan
   y el GG consolida. Sin llamadas HTTP reales (monkeypatch por slug).
3. Caso sin delegación: el GG responde directo.

Uso:  python3 pruebas/test_delegacion.py
"""
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "runtime"))

from nucleo import delegacion as D  # noqa: E402


def main() -> int:
    fallos = []

    def check(nombre, cond, detalle=""):
        if not cond:
            fallos.append(f"{nombre} {detalle}")

    # --- 1. Parseo ---
    t1 = ("Análisis listo.\nDELEGAR:\n- agente: analista\n"
          '  tarea: "investigar el mercado"\n- agente: constructor\n'
          '  tarea: "armar la landing"\n')
    d1 = D.extraer_delegaciones(t1)
    check("parsea 2 delegaciones", d1 == [("analista", "investigar el mercado"),
                                          ("constructor", "armar la landing")], str(d1))

    check("sin bloque → vacío", D.extraer_delegaciones("texto plano") == [])

    t3 = "DELEGAR:\n" + "".join(
        f"- agente: a{i}\n  tarea: \"t{i}\"\n" for i in range(8))
    check("tope de 5", len(D.extraer_delegaciones(t3)) == 5)

    t4 = "DELEGAR:\n- agente analista sin dos puntos\n  tarea: \"x\"\n"
    check("formato roto se ignora", D.extraer_delegaciones(t4) == [])

    check("quitar_bloques", "DELEGAR" not in D.quitar_bloques(t1)
          and "Análisis listo." in D.quitar_bloques(t1))

    # --- 2 y 3. Flujo orquestar contra mock ---
    from nucleo import agente as modulo_agente
    llamadas = []

    def falso_ejecutar(slug, tarea, cliente, forzar_modelo=""):
        llamadas.append(slug)
        n = sum(1 for s in llamadas if s == slug)
        if slug == "gerente-general" and n == 1:
            return {"agente": slug, "modelo": "m",
                    "texto": "Plan: ataco por dos frentes.\nDELEGAR:\n"
                             "- agente: analista\n  tarea: \"investigar X\"\n"
                             "- agente: constructor\n  tarea: \"armar Y\"\n"}
        if slug == "gerente-general":
            assert "investigar X" in tarea or "Resultado" in tarea or "resultados" in tarea, tarea[:80]
            return {"agente": slug, "modelo": "m", "texto": "CONSOLIDADO FINAL"}
        return {"agente": slug, "modelo": "m", "texto": f"resultado de {slug}"}

    _orig = modulo_agente.ejecutar_agente
    modulo_agente.ejecutar_agente = falso_ejecutar
    try:
        r = D.orquestar("tarea del dueño", cliente=None)
    finally:
        modulo_agente.ejecutar_agente = _orig

    check("orquestar delega", r["delega"] is True)
    check("orquestar: 2 en traza", len(r["delegaciones"]) == 2, str(r["delegaciones"]))
    check("orquestar: traza ok",
          all(d["ok"] and d["agente"] in ("analista", "constructor")
              for d in r["delegaciones"]))
    check("orquestar: consolida", r["texto"] == "CONSOLIDADO FINAL")
    check("orquestar: plan limpio",
          "DELEGAR" not in r["plan"] and "Plan:" in r["plan"])
    check("orquestar: orden de llamadas",
          llamadas == ["gerente-general", "analista", "constructor", "gerente-general"],
          str(llamadas))

    # GG que no delega
    def falso_directo(slug, tarea, cliente, forzar_modelo=""):
        return {"agente": slug, "modelo": "m", "texto": "Lo resuelvo yo directamente."}

    modulo_agente.ejecutar_agente = falso_directo
    try:
        r2 = D.orquestar("otra tarea", cliente=None)
    finally:
        modulo_agente.ejecutar_agente = _orig

    check("sin delegación: delega=False",
          r2["delega"] is False and r2["delegaciones"] == [])
    check("sin delegación: texto directo",
          r2["texto"] == "Lo resuelvo yo directamente.")

    if fallos:
        print("FALLÓ:")
        for f in fallos:
            print(f"  - {f}")
        return 1
    print("OK: delegación (parseo + orquestación + caso directo)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
