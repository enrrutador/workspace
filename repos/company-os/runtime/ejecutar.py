#!/usr/bin/env python3
"""CLI para ejecutar agentes de la empresa.

Uso:
    python3 ejecutar.py <slug-agente> "<tarea>" [--modelo empresa-base]
    python3 ejecutar.py gerente-general "<tarea>" --orquestar

Requiere:
    1. El proxy LiteLLM levantado (infraestructura/litellm/README.md),
       o LITELLM_BASE_URL apuntando directo al proveedor.
    2. Variables de entorno LITELLM_BASE_URL y LITELLM_MASTER_KEY
       (cargalas desde infraestructura/litellm/.env).

Ejemplo:
    python3 ejecutar.py conciliador "Conciliá estos movimientos: ..."

Con --orquestar (solo gerente-general), el GG delega a especialistas
vía bloques DELEGAR: y consolida la respuesta final.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

from nucleo import agente, cliente


def main() -> int:
    # El .env vive junto al proxy; también acepta variables ya exportadas.
    repo = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(repo, "..", "infraestructura", "litellm", ".env"))

    parser = argparse.ArgumentParser(description="Ejecuta un agente de la empresa.")
    parser.add_argument("slug", help=f"Agente a ejecutar. Opciones: {', '.join(agente.slugs())}")
    parser.add_argument("tarea", help="Tarea en lenguaje natural, entre comillas.")
    parser.add_argument("--modelo", default="", help="Forzar modelo del proxy (ej. empresa-ligero).")
    parser.add_argument("--orquestar", action="store_true",
                        help="Modo orquestador: solo con gerente-general, delega a "
                             "especialistas y consolida.")
    args = parser.parse_args()

    if args.orquestar and args.slug != "gerente-general":
        print("Error: --orquestar solo funciona con gerente-general.", file=sys.stderr)
        return 1

    try:
        c = cliente.crear_cliente()
        if args.orquestar:
            from nucleo import delegacion as modulo_delegacion
            r = modulo_delegacion.orquestar(args.tarea, c, forzar_modelo=args.modelo)
            print("--- gerente-general (orquestador) ---\n")
            if r["delegaciones"]:
                print("Delegaciones:")
                for d in r["delegaciones"]:
                    estado = "ok" if d["ok"] else f"FALLO: {d.get('error', '')}"
                    print(f"  • {d['agente']}: {estado}")
                print()
            print(r["texto"])
            return 0
        resultado = agente.ejecutar_agente(args.slug, args.tarea, c, forzar_modelo=args.modelo)
    except Exception as e:  # noqa: BLE001 - CLI: mostrar el error y salir
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"--- {resultado['agente']} ({resultado['modelo']}) ---\n")
    print(resultado["texto"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
