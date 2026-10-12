#!/usr/bin/env python3
"""Pruebas del dashboard: endpoints nuevos y regresiones (contra mock, sin gastar).

Valida:
  1. GET /api/pipeline trae las 5 etapas (incluye producto).
  2. POST /api/pipeline valida (400 si faltan datos o etapa desconocida).
  3. Un trabajo de pipeline tesis corre punta a punta y da SEGUIR.
  4. /api/chats conserva trabajoId/terminado/vistos (reenganche tras recarga).
  5. GET /api/trabajos de un id inexistente da 404 con forma {ok:false}.
  6. GET /api/config expone LLM_API_KEY enmascarada (no el valor).

Uso:  python3 pruebas/test_dashboard.py
"""
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "runtime"))


class MockOpenAI(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        largo = int(self.headers.get("Content-Length", 0))
        cuerpo = json.loads(self.rfile.read(largo) or b"{}")
        msgs = cuerpo.get("messages", [])
        user = " ".join(m.get("content", "") for m in msgs if m.get("role") == "user")
        if "'VEREDICTO: SEGUIR'" in user:
            txt = "Tesis OK. VEREDICTO: SEGUIR"
        else:
            txt = "MOCK artefacto de prueba."
        payload = {
            "id": "chatcmpl-mock", "object": "chat.completion",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": txt},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
        }
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


def _get(base, path):
    with urllib.request.urlopen(base + path, timeout=30) as r:
        return r.status, json.loads(r.read())


def _post(base, path, datos):
    req = urllib.request.Request(
        base + path, data=json.dumps(datos).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def main() -> int:
    fallos = []
    mock = HTTPServer(("127.0.0.1", 0), MockOpenAI)
    mp = mock.server_address[1]
    threading.Thread(target=mock.serve_forever, daemon=True).start()

    env = dict(os.environ, LITELLM_BASE_URL=f"http://127.0.0.1:{mp}/v1",
               LITELLM_MASTER_KEY="test-key")
    srv = subprocess.Popen(
        [sys.executable, "dashboard/servidor.py", "--puerto", "18084"],
        env=env, cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = "http://127.0.0.1:18084"
    try:
        for _ in range(30):
            try:
                _get(base, "/api/empresa")
                break
            except OSError:
                time.sleep(0.5)
        else:
            print("FALLO: el dashboard no levantó")
            return 1

        # 1. Etapas del pipeline
        _, r = _get(base, "/api/pipeline")
        ids = [e["id"] for e in r.get("etapas", [])] if r.get("ok") else []
        if set(ids) != {"tesis", "validacion", "construccion", "comercial", "producto"}:
            fallos.append(f"etapas inesperadas: {ids}")

        # 2. Validación de entrada
        code, r = _post(base, "/api/pipeline", {"etapa": "tesis"})
        if not (code == 400 and not r.get("ok")):
            fallos.append("falta validar objetivo ausente")
        code, r = _post(base, "/api/pipeline", {"etapa": "noexiste", "objetivo": "x"})
        if not (code == 400 and not r.get("ok")):
            fallos.append("falta validar etapa desconocida")

        # 3. Trabajo tesis punta a punta
        _, r = _post(base, "/api/pipeline",
                     {"etapa": "tesis", "objetivo": "Producto de prueba"})
        jid = r.get("id", "")
        if not r.get("ok") or not jid:
            fallos.append("no se pudo crear el trabajo de pipeline")
        else:
            fin = None
            for _ in range(40):
                time.sleep(3)
                _, d = _get(base, f"/api/trabajos?id={jid}&desde=0")
                if d.get("terminado"):
                    fin = [e for e in d.get("eventos", []) if e.get("tipo") == "final"]
                    break
            if not fin:
                fallos.append("el trabajo de pipeline no terminó")
            elif fin[0].get("veredictos", {}).get("tesis") != "SEGUIR":
                fallos.append(f"veredicto inesperado: {fin[0].get('veredictos')}")
            elif len(fin[0].get("artefactos", {})) != 5:
                fallos.append("artefactos incompletos en tesis")

        # 4. Chats conservan el vínculo del trabajo
        chats = {"gerente-general": {
            "historial": [{"rol": "usuario", "texto": "h"}],
            "trabajoId": "abc123", "terminado": False, "vistos": 2}}
        _, r = _post(base, "/api/chats", {"chats": chats})
        _, r = _get(base, "/api/chats")
        gg = (r.get("chats") or {}).get("gerente-general", {})
        if gg.get("trabajoId") != "abc123" or gg.get("terminado") is not False:
            fallos.append(f"chats no conserva el trabajo: {gg}")

        # 4b. Chats v2: conversaciones múltiples con fecha sobreviven
        v2 = {"analista": {"conversaciones": [
            {"id": "c1", "titulo": "Vieja", "creada": "2026-09-01T00:00:00Z",
             "actualizada": "2026-09-02T00:00:00Z",
             "historial": [{"rol": "usuario", "texto": "hola"}]},
            {"id": "c2", "titulo": "Nueva", "creada": "2026-10-10T00:00:00Z",
             "actualizada": "2026-10-10T00:00:00Z",
             "historial": [{"rol": "usuario", "texto": "qué tal"}],
             "trabajoId": "job9", "terminado": False, "vistos": 1}],
            "activa": "c2"}}
        _, r = _post(base, "/api/chats", {"chats": v2})
        _, r = _get(base, "/api/chats")
        an = (r.get("chats") or {}).get("analista", {})
        convs = an.get("conversaciones", [])
        if len(convs) != 2 or an.get("activa") != "c2":
            fallos.append(f"chats v2 incompleto: {an}")
        elif convs[1].get("trabajoId") != "job9" or convs[1].get("terminado") is not False:
            fallos.append(f"chats v2 no conserva el trabajo: {convs[1]}")

        # 5. Trabajo inexistente → 404 con forma
        try:
            with urllib.request.urlopen(base + "/api/trabajos?id=noexiste&desde=0",
                                        timeout=30) as resp:
                fallos.append("se esperaba 404 para trabajo inexistente")
        except urllib.error.HTTPError as e:
            cuerpo = json.loads(e.read() or b"{}")
            if not (e.code == 404 and cuerpo.get("ok") is False):
                fallos.append("forma inesperada del 404 de trabajos")

        # 6. Config enmascara la provider key
        _, r = _get(base, "/api/config")
        if not isinstance(r.get("LLM_API_KEY"), dict) or "ultimos4" not in r["LLM_API_KEY"]:
            fallos.append("config no expone LLM_API_KEY enmascarada")
    finally:
        srv.terminate()
        try:
            srv.wait(timeout=10)
        except subprocess.TimeoutExpired:
            srv.kill()
        mock.shutdown()

    if fallos:
        print("FALLO:")
        for f in fallos:
            print(f"  - {f}")
        return 1
    print("OK: dashboard (pipeline + chats + validaciones)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
