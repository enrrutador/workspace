#!/usr/bin/env python3
"""Prueba del orquestador LangGraph contra un mock (sin gastar ni un centavo).

El mock responde según el agente que llama (lo detecta en el system prompt):
  - control-de-calidad: 1ª vez "VEREDICTO: RECHAZADO", después "VEREDICTO: APROBADO"
  - resto: texto genérico OK

Valida:
  1. El grafo de Construcción corre punta a punta (8 nodos).
  2. El borde condicional funciona: QA rechaza → se reintenta el build (1 vez).
  3. El despliegue frena sin APROBACION_DESPLIEGUE=si (in-the-loop).
  4. Los artefactos se encadenan (el diseño menciona la especificación, etc.).
  5. Todo queda en la auditoría.

Uso:  python3 pruebas/test_orquestador_mock.py
"""
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "runtime"))

LLAMADAS = {"qa": 0}
ES_TURNO_QA = {"activo": False}
TEXTO_RECHAZO = "Reporte QA: 1 fallo crítico en login. VEREDICTO: RECHAZADO"
TEXTO_APROBADO = "Reporte QA: todo verificado. VEREDICTO: APROBADO"


class Mock(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        largo = int(self.headers.get("Content-Length", 0))
        self.rfile.read(largo)
        # La detección del agente se hace por slug (ver monkeypatch abajo),
        # no por texto del prompt: otros agentes mencionan "Control de Calidad".
        if ES_TURNO_QA["activo"]:
            LLAMADAS["qa"] += 1
            texto = TEXTO_RECHAZO if LLAMADAS["qa"] == 1 else TEXTO_APROBADO
        else:
            texto = "MOCK: artefacto generado correctamente."
        payload = {"choices": [{"message": {"role": "assistant", "content": texto}}],
                   "usage": {"prompt_tokens": 5, "completion_tokens": 5}}
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


def main() -> int:
    servidor = HTTPServer(("127.0.0.1", 0), Mock)
    puerto = servidor.server_address[1]
    threading.Thread(target=servidor.serve_forever, daemon=True).start()

    os.environ["LITELLM_BASE_URL"] = f"http://127.0.0.1:{puerto}/v1"
    os.environ["LITELLM_MASTER_KEY"] = "test-key"
    os.environ.pop("APROBACION_DESPLIEGUE", None)

    import nucleo.auditoria as auditoria
    auditoria.ARCHIVO = "/tmp/auditoria_test_orq.jsonl"
    if os.path.exists(auditoria.ARCHIVO):
        os.remove(auditoria.ARCHIVO)

    from orquestador import grafos

    # Monkeypatch: marcar el turno real del agente QA por slug (robusto).
    _orig_ejecutar = grafos.modulo_agente.ejecutar_agente

    def _wrap(slug, tarea, cliente, forzar_modelo=""):
        ES_TURNO_QA["activo"] = (slug == "control-de-calidad")
        try:
            return _orig_ejecutar(slug, tarea, cliente, forzar_modelo=forzar_modelo)
        finally:
            ES_TURNO_QA["activo"] = False

    grafos.modulo_agente.ejecutar_agente = _wrap
    try:
        fallos = []
        final = grafos.ejecutar_etapa("construccion", "App de prueba: lista de tareas",
                                      componentes=["constructor"])
    finally:
        grafos.modulo_agente.ejecutar_agente = _orig_ejecutar

    # 1. Traza completa: 8 nodos + 1 reintento
    traza = final["traza"]
    esperados = ["gerente-general", "arquitecto", "disenador-ux-ui", "constructor",
                 "revisor", "ingeniero-seguridad", "control-de-calidad",
                 "sre", "responsable-despliegues"]
    for slug in esperados:
        if not any(slug in t for t in traza):
            fallos.append(f"falta en traza: {slug}")

    # 2. Reintento de QA
    if final["reintentos_qa"] != 1:
        fallos.append(f"reintentos_qa={final['reintentos_qa']}, esperado 1")
    builds = sum(1 for t in traza if t.startswith("constructor: build"))
    if builds != 2:
        fallos.append(f"builds ejecutados={builds}, esperado 2 (1 inicial + 1 reintento)")

    # 3. Despliegue frenado
    desp = final["artefactos"].get("despliegue", "")
    if "PENDIENTE_APROBACION_FABIAN" not in desp:
        fallos.append("el despliegue no frenó sin aprobación")

    # 4. Artefactos encadenados
    arts = final["artefactos"]
    for nombre in ["especificacion", "diseno", "diseno_ux", "build_constructor",
                   "revision", "revision_seguridad", "reporte_qa", "slos", "despliegue"]:
        if nombre not in arts:
            fallos.append(f"falta artefacto: {nombre}")

    # 5. Auditoría
    if os.path.exists(auditoria.ARCHIVO):
        n = sum(1 for _ in open(auditoria.ARCHIVO, encoding="utf-8"))
        if n < 9:
            fallos.append(f"auditoría con {n} entradas, esperado >= 9")
    else:
        fallos.append("no se escribió la auditoría")

    servidor.shutdown()

    if fallos:
        print("FALLÓ:")
        for f in fallos:
            print(f"  - {f}")
        return 1
    print(f"OK: orquestador punta a punta "
          f"({len(traza)} pasos en traza, {len(arts)} artefactos, 1 reintento QA, despliegue frenado)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
