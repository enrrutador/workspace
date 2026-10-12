#!/usr/bin/env python3
"""Prueba del modo empresa (grafo 'producto') contra un mock.

Dos escenarios:
  1. Camino feliz: tesis SEGUIR → validación VALIDADO → construcción
     (QA aprueba) → comercial. El despliegue frena sin aprobación de Fabian.
  2. Kill en tesis: el Gerente General mata la tesis → el grafo se detiene
     ahí: no corre validación, ni construcción, ni comercial.

El mock responde por slug de agente (monkeypatch), con un guion por llamada.

Uso:  python3 pruebas/test_producto_mock.py
"""
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "runtime"))

TURNO = {"slug": None}


class Guion:
    def __init__(self, matar_en_tesis: bool = False):
        self.matar = matar_en_tesis
        self.n = {}

    def texto(self, slug: str) -> str:
        self.n[slug] = self.n.get(slug, 0) + 1
        k = self.n[slug]
        if slug == "control-de-calidad":
            return "Todo verificado. VEREDICTO: APROBADO"
        if slug == "gerente-general":
            # 1=tesis, 2=tesis_final, 3=veredicto_validacion, 4=plan_comercial
            if k == 1:
                return "Tesis: producto de prueba."
            if k == 2:
                return ("Tesis final. VEREDICTO: MATAR"
                        if self.matar else "Tesis final. VEREDICTO: SEGUIR")
            if k == 3:
                return "Evidencia suficiente. VEREDICTO: VALIDADO"
            return "Plan comercial: afiliados + alertas premium."
        return "MOCK: artefacto generado correctamente."


GUION = {"actual": None}


class Mock(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        largo = int(self.headers.get("Content-Length", 0))
        self.rfile.read(largo)
        import json
        texto = GUION["actual"].texto(TURNO["slug"] or "")
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


def correr(matar_en_tesis: bool) -> dict:
    from orquestador import grafos
    GUION["actual"] = Guion(matar_en_tesis=matar_en_tesis)
    _orig = grafos.modulo_agente.ejecutar_agente

    def _wrap(slug, tarea, cliente, forzar_modelo=""):
        TURNO["slug"] = slug
        try:
            return _orig(slug, tarea, cliente, forzar_modelo=forzar_modelo)
        finally:
            TURNO["slug"] = None

    grafos.modulo_agente.ejecutar_agente = _wrap
    try:
        return grafos.ejecutar_etapa("producto", "Producto de prueba",
                                     componentes=["constructor"])
    finally:
        grafos.modulo_agente.ejecutar_agente = _orig


def main() -> int:
    servidor = HTTPServer(("127.0.0.1", 0), Mock)
    puerto = servidor.server_address[1]
    threading.Thread(target=servidor.serve_forever, daemon=True).start()

    os.environ["LITELLM_BASE_URL"] = f"http://127.0.0.1:{puerto}/v1"
    os.environ["LITELLM_MASTER_KEY"] = "test-key"
    os.environ.pop("APROBACION_DESPLIEGUE", None)

    import nucleo.auditoria as auditoria
    auditoria.ARCHIVO = "/tmp/auditoria_test_producto.jsonl"
    if os.path.exists(auditoria.ARCHIVO):
        os.remove(auditoria.ARCHIVO)

    fallos = []

    # --- Escenario 1: camino feliz ---
    feliz = correr(matar_en_tesis=False)
    if feliz.get("veredictos", {}).get("tesis") != "SEGUIR":
        fallos.append("camino feliz: tesis no dio SEGUIR")
    if feliz.get("veredictos", {}).get("validacion") != "VALIDADO":
        fallos.append("camino feliz: validación no dio VALIDADO")
    arts = feliz.get("artefactos", {})
    for nombre in ["tesis", "ataque_arquitecto", "ataque_seguridad", "ataque_analista",
                   "tesis_final", "investigacion", "landing", "cobro_preventa",
                   "veredicto_validacion", "especificacion", "diseno", "diseno_ux",
                   "build_constructor", "revision", "revision_seguridad", "reporte_qa",
                   "slos", "despliegue", "icp_canales", "borrador_outreach",
                   "criterios_calificacion", "plan_comercial"]:
        if nombre not in arts:
            fallos.append(f"camino feliz: falta artefacto {nombre}")
    if "PENDIENTE_APROBACION_FABIAN" not in arts.get("despliegue", ""):
        fallos.append("camino feliz: el despliegue no frenó sin aprobación")

    # --- Escenario 2: kill en tesis ---
    kill = correr(matar_en_tesis=True)
    if kill.get("veredictos", {}).get("tesis") != "MATAR":
        fallos.append("kill: tesis no dio MATAR")
    arts_k = kill.get("artefactos", {})
    for nombre in ["investigacion", "especificacion", "plan_comercial"]:
        if nombre in arts_k:
            fallos.append(f"kill: la etapa siguió corriendo ({nombre} existe)")

    servidor.shutdown()

    if fallos:
        print("FALLÓ:")
        for f in fallos:
            print(f"  - {f}")
        return 1
    print(f"OK: modo empresa ({len(feliz['traza'])} pasos camino feliz, "
          f"kill en tesis detiene el grafo, despliegue frenado)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
