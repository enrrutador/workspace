#!/usr/bin/env python3
"""Pruebas del protocolo jerárquico y del parseo tolerante de veredictos.

1. Todo prompt incluye CADENA DE MANDO.
2. El GG es el intermediario (no devuelve preguntas, consolida).
3. Los especialistas reportan al GG y no molestan al dueño.
4. El veredicto tolera mayúsculas/espacios/markdown, pero sigue fail-closed.
"""
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "runtime"))

from nucleo import agente as modulo_agente  # noqa: E402


def main() -> int:
    fallos = []

    def check(nombre, cond, detalle=""):
        if not cond:
            fallos.append(f"{nombre} {detalle}")

    p_gg = modulo_agente.prompt_sistema("gerente-general")
    p_an = modulo_agente.prompt_sistema("analista")
    p_ex = modulo_agente.prompt_sistema("explorador")

    for nombre, p in [("gg", p_gg), ("analista", p_an), ("explorador", p_ex)]:
        check(f"cadena de mando en {nombre}", "CADENA DE MANDO" in p)

    check("GG es intermediario", "intermediario" in p_gg)
    check("GG no devuelve preguntas",
          "No le devuelvas preguntas al dueño dentro de tu autoridad" in p_gg)
    check("GG consolida", "UN informe accionable" in p_gg)
    check("GG no reenvía crudo",
          "no para reenviarlas tal cual al dueño" in p_gg)

    check("especialista reporta al GG",
          "Tu superior es el Gerente General" in p_an)
    check("especialista no molesta al dueño",
          "Al jefe solo le llegan decisiones, no tareas." in p_an)
    check("especialista no cuestiona al dueño",
          "Al dueño NO se lo cuestiona" in p_an)
    check("especialista no devuelve preguntas",
          "PROHIBIDO devolverle preguntas" in p_an)
    check("especialista asume y declara",
          "Asumo X" in p_an)
    check("explorador también tiene protocolo",
          "Tu superior es el Gerente General" in p_ex)
    check("explorador no cuestiona al dueño",
          "Al dueño NO se lo cuestiona" in p_ex)

    # Veredictos tolerantes pero fail-closed
    from orquestador import grafos as G
    pat = G._patron_veredicto("VEREDICTO: SEGUIR")
    for variante in ["VEREDICTO: SEGUIR", "veredicto:seguir",
                     "VEREDICTO:SEGUIR", "**VEREDICTO: SEGUIR**",
                     "algo antes\nVEREDICTO:  SEGUIR\nfin"]:
        check(f"veredicto tolera {variante!r}", bool(pat.search(variante)), variante)
    for negativa in ["VEREDICTO: MATAR", "sin veredicto", "",
                     "VEREDICTO: SEGUIRÉ", "casi VEREDICTO SEGUIR"]:
        check(f"veredicto rechaza {negativa!r}", not pat.search(negativa), negativa)

    pat_v = G._patron_veredicto("VEREDICTO: VALIDADO")
    check("validado exacto", bool(pat_v.search("VEREDICTO: VALIDADO")))
    check("validado minúsculas", bool(pat_v.search("veredicto: validado")))
    check("descartado no es validado", not pat_v.search("VEREDICTO: DESCARTADO"))

    if fallos:
        print("FALLÓ:")
        for f in fallos:
            print(f"  - {f}")
        return 1
    print("OK: protocolo jerárquico + veredictos tolerantes y fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
