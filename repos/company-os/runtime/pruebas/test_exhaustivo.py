#!/usr/bin/env python3
"""Examen exhaustivo punta a punta de la empresa (Company OS).

Verifica punto por punto que todo esté configurado y conectado:
  1. Registry <-> fichas <-> skills (bidireccional, 26 agentes).
  2. Los 26 prompts se componen (ficha + skill + transversal autocapacitación).
  3. Dashboard: API de agentes, empresa y config (con servidor real).
  4. Ejecución vía dashboard contra un mock (agente nuevo y uno viejo).
  5. Consistencia documental: links relativos, referencias a agentes en el pipeline,
     conteos ("26 agentes") y los tres frenos en gobernanza.

Uso:  python3 pruebas/test_exhaustivo.py
Salida: reporte con OK/FALLO por punto y código de salida.
"""
import json
import os
import re
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import Request, urlopen

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "runtime"))
sys.path.insert(0, os.path.join(REPO, "dashboard"))

FALLOS = []


def check(nombre, cond, detalle=""):
    estado = "OK  " if cond else "FALLO"
    print(f"[{estado}] {nombre}" + (f" — {detalle}" if detalle and not cond else ""))
    if not cond:
        FALLOS.append(nombre)


# ---------------------------------------------------------------- 1 y 2
from nucleo import agente  # noqa: E402

slugs = agente.slugs()
check("registry tiene 26 agentes", len(slugs) == 26, f"hay {len(slugs)}")

fichas_en_disco = set()
for root, _, fns in os.walk(os.path.join(REPO, "agentes")):
    for f in fns:
        if f.endswith(".md") and f != "README.md":
            fichas_en_disco.add(os.path.splitext(f)[0])
skills_en_disco = set(d for d in os.listdir(os.path.join(REPO, "habilidades"))
                      if os.path.isdir(os.path.join(REPO, "habilidades", d))
                      and d != "autocapacitacion"
                      and os.path.exists(os.path.join(REPO, "habilidades", d, "SKILL.md")))

check("toda ficha tiene entrada en registry", fichas_en_disco <= set(slugs),
      f"sin registry: {fichas_en_disco - set(slugs)}")
check("todo slug tiene ficha", set(slugs) <= fichas_en_disco,
      f"sin ficha: {set(slugs) - fichas_en_disco}")
check("todo slug tiene SKILL.md", set(slugs) <= skills_en_disco,
      f"sin skill: {set(slugs) - skills_en_disco}")
check("toda skill tiene slug en registry", skills_en_disco <= set(slugs),
      f"huérfanas: {skills_en_disco - set(slugs)}")
check("existe skill transversal autocapacitación",
      os.path.exists(os.path.join(REPO, "habilidades", "autocapacitacion", "SKILL.md")))

prompts_ok, transversal_ok = 0, 0
for s in slugs:
    try:
        p = agente.prompt_sistema(s)
        if len(p) > 2000:
            prompts_ok += 1
        if "autocapacit" in p.lower():
            transversal_ok += 1
    except Exception as e:  # noqa: BLE001
        FALLOS.append(f"prompt roto: {s} ({e})")
check("26/26 prompts se componen", prompts_ok == 26, f"{prompts_ok}/26")
check("26/26 prompts incluyen autocapacitación", transversal_ok == 26, f"{transversal_ok}/26")

# ---------------------------------------------------------------- 3 y 4
MOCK_TXT = "MOCK exhaustivo OK"


class Mock(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        largo = int(self.headers.get("Content-Length", 0))
        self.rfile.read(largo)
        payload = {"choices": [{"message": {"role": "assistant", "content": MOCK_TXT}}],
                   "usage": {"prompt_tokens": 5, "completion_tokens": 5}}
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


mock = HTTPServer(("127.0.0.1", 4101), Mock)
threading.Thread(target=mock.serve_forever, daemon=True).start()

import servidor as srv  # noqa: E402

os.environ["LITELLM_BASE_URL"] = "http://127.0.0.1:4101/v1"
os.environ["LITELLM_MASTER_KEY"] = "test-key"
dash = HTTPServer(("127.0.0.1", 8098), srv.Manejador)
threading.Thread(target=dash.serve_forever, daemon=True).start()
time.sleep(0.5)


def get(path):
    return json.load(urlopen(f"http://127.0.0.1:8098{path}", timeout=10))


def post(path, body):
    req = Request(f"http://127.0.0.1:8098{path}", data=json.dumps(body).encode(),
                  headers={"Content-Type": "application/json"}, method="POST")
    return json.load(urlopen(req, timeout=90))


agentes_api = get("/api/agentes")
check("dashboard /api/agentes trae 26", len(agentes_api) == 26, f"trae {len(agentes_api)}")
check("dashboard incluye a los 7 nuevos",
      all(a in [x["slug"] for x in agentes_api]
          for a in ["arquitecto", "ingeniero-datos", "ingeniero-ml",
                    "desarrollador-mobile", "ingeniero-seguridad", "sre", "disenador-ux-ui"]))

empresa = get("/api/empresa")
check("dashboard /api/empresa: 26 agentes", empresa["agentes"] == 26)
check("dashboard /api/empresa: 10 etapas", len(empresa["etapas"]) == 10)

for slug_prueba in ["arquitecto", "conciliador"]:
    r = post("/api/ejecutar", {"slug": slug_prueba, "tarea": "tarea de prueba"})
    check(f"ejecución vía dashboard: {slug_prueba}",
          r.get("ok") and r.get("texto") == MOCK_TXT, str(r)[:120])

dash.shutdown()
mock.shutdown()

# ---------------------------------------------------------------- 5
rotos = []
for root, _, fns in os.walk(REPO):
    if "node_modules" in root or "/.git" in root:
        continue
    for fn in fns:
        if fn.endswith(".md"):
            f = os.path.join(root, fn)
            t = open(f, encoding="utf-8").read()
            for m in re.finditer(r"\[[^\]]*\]\(([^)#]+)(?:#[^)]*)?\)", t):
                url = m.group(1)
                if url.startswith(("http", "mailto:")):
                    continue
                if not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(f), url))):
                    rotos.append((os.path.relpath(f, REPO), url))
check("cero links relativos rotos en el repo", not rotos, str(rotos[:3]))

# agentes enlazados en el pipeline existen en el registry
etapas = open(os.path.join(REPO, "pipeline", "etapas.md"), encoding="utf-8").read()
enlazados = set(re.findall(r"agentes/(?:\w+/)?([\w-]+)\.md", etapas))
check("agentes del pipeline existen en registry", enlazados <= set(slugs),
      f"faltan: {enlazados - set(slugs)}")

# conteos viejos
viejos = []
for root, _, fns in os.walk(REPO):
    for fn in fns:
        if fn.endswith((".md", ".py", ".html")):
            f = os.path.join(root, fn)
            t = open(f, encoding="utf-8").read()
            # la línea histórica de diseno-operativo-v1 está anotada a propósito;
            # este mismo test se excluye (su código menciona el patrón buscado)
            if "diseno-operativo-v1.md" in f:
                t = t.replace("Total v1: 18 agentes", "")
            if "test_exhaustivo.py" in f:
                continue
            if re.search(r"\b18 agentes\b", t):
                viejos.append(os.path.relpath(f, REPO))
check("sin referencias viejas a '18 agentes'", not viejos, str(viejos[:5]))

aprob = open(os.path.join(REPO, "gobernanza", "aprobaciones.md"), encoding="utf-8").read()
check("gobernanza documenta los 3 frenos",
      all(k in aprob for k in ["Guardián", "Ingeniero de Seguridad", "SRE"])
      and "Frenos de emergencia" in aprob)

# ---------------------------------------------------------------- reporte
print()
if FALLOS:
    print(f"RESULTADO: {len(FALLOS)} FALLOS")
    for f in FALLOS:
        print("  -", f)
    sys.exit(1)
print("RESULTADO: TODO OK — empresa 100% funcional punto por punto")
