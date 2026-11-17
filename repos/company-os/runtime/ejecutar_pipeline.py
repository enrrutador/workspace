#!/usr/bin/env python3
"""CLI para ejecutar etapas del pipeline con el orquestador multi-agente.

Uso:
    python3 ejecutar_pipeline.py construccion --objetivo "..." [--componentes constructor,mobile]
    python3 ejecutar_pipeline.py producto --objetivo "Tu objetivo en lenguaje natural"

    El modo "producto" es el modo empresa: el Gerente General orquesta el pipeline
    punta a punta (tesis → validación → construcción → comercial) y cada etapa
    puede matar el producto con su veredicto.

Requiere:
    1. El proxy LiteLLM levantado (infraestructura/litellm/README.md).
    2. Variables de entorno LITELLM_BASE_URL y LITELLM_MASTER_KEY
       (cargalas desde infraestructura/litellm/.env).
    3. langgraph instalado: pip install -r requirements.txt

El despliegue queda PENDIENTE_APROBACION_FABIAN salvo que se exporte
APROBACION_DESPLIEGUE=si (in-the-loop: lo irreversible lo aprueba Fabian).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

from orquestador import grafos


def main() -> int:
    repo = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(repo, "..", "infraestructura", "litellm", ".env"))

    parser = argparse.ArgumentParser(description="Ejecuta una etapa del pipeline.")
    parser.add_argument("etapa", help=f"Etapa a ejecutar. Disponibles: {', '.join(grafos.ETAPAS)}")
    parser.add_argument("--objetivo", required=True, help="Objetivo del producto, entre comillas.")
    parser.add_argument("--componentes", default="constructor",
                        help="Builders separados por coma (constructor, desarrollador-mobile, ingeniero-datos, ingeniero-ml).")
    args = parser.parse_args()

    try:
        final = grafos.ejecutar_etapa(
            args.etapa, args.objetivo,
            componentes=[c.strip() for c in args.componentes.split(",") if c.strip()],
        )
    except Exception as e:  # noqa: BLE001 - CLI: mostrar el error y salir
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"=== Etapa '{args.etapa}' completada ===\n")
    print("-- Traza --")
    for paso in final["traza"]:
        print(f"  • {paso}")
    print(f"\n-- Artefactos ({len(final['artefactos'])}) --")
    for nombre in final["artefactos"]:
        print(f"  • {nombre}")
    print(f"\nReintentos de QA: {final['reintentos_qa']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
