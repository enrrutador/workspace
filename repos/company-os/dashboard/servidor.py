#!/usr/bin/env python3
"""Dashboard web local de la empresa (Company OS).

Panel visual para manejar y configurar todo sin tocar la terminal:
  - Agentes: ver los 26, buscarlos, asignarles tareas, leer respuestas.
  - Auditoría: quién hizo qué, cuándo, cuántos tokens (filtrable, expandible).
  - Configuración: API key y modelos en formulario, con prueba de conexión
    en vivo contra el proveedor (detecta modelos muertos antes de ejecutar).
  - Empresa: pipeline y productos de un vistazo.

Uso:
    python3 servidor.py [--puerto 8080]

    Abrir en el navegador: http://localhost:8080

Solo biblioteca estándar (sin dependencias nuevas), salvo la importación
perezosa de `openai` al ejecutar o probar modelos. Escucha únicamente en
127.0.0.1: nunca exponer a internet — la configuración incluye secretos.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

RAIZ_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DIR_DASHBOARD = os.path.dirname(os.path.abspath(__file__))
RUTA_ENV = os.path.join(RAIZ_REPO, "infraestructura", "litellm", ".env")
RUTA_CHATS = os.path.join(RAIZ_REPO, "runtime", "registro", "chats.json")

sys.path.insert(0, os.path.join(RAIZ_REPO, "runtime"))
from nucleo import agente as modulo_agente  # noqa: E402
# NOTA: `nucleo.cliente` (requiere `openai`) se importa perezoso solo al ejecutar
# o probar modelos, para que el dashboard abra sin dependencias más allá de la
# biblioteca estándar.

CLAVES_ENV = [
    "LLM_API_KEY",
    "MODELO_EMPRESA_BASE",
    "MODELO_EMPRESA_RAZONAMIENTO",
    "MODELO_EMPRESA_LIGERO",
    "LITELLM_BASE_URL",
    "LITELLM_MASTER_KEY",
]
CLAVES_SECRETAS = {"LLM_API_KEY", "LITELLM_MASTER_KEY"}
# Modelos que se prueban en "Probar conexión": (clave de env, etiqueta).
MODELOS_PROBABLES = [
    ("MODELO_EMPRESA_BASE", "base"),
    ("MODELO_EMPRESA_RAZONAMIENTO", "razonamiento"),
    ("MODELO_EMPRESA_LIGERO", "ligero"),
]


# ---------------------------------------------------------------- .env
def leer_env() -> dict:
    valores = {}
    if os.path.exists(RUTA_ENV):
        with open(RUTA_ENV, encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea or linea.startswith("#") or "=" not in linea:
                    continue
                k, v = linea.split("=", 1)
                valores[k.strip()] = v.strip()
    return valores


def escribir_env(nuevos: dict) -> None:
    """Actualiza solo las claves recibidas, preservando comentarios y orden."""
    lineas = []
    vistas = set()
    if os.path.exists(RUTA_ENV):
        with open(RUTA_ENV, encoding="utf-8") as f:
            lineas = f.readlines()
    salida = []
    for linea in lineas:
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", linea.strip())
        if m and m.group(1) in nuevos:
            salida.append(f"{m.group(1)}={nuevos[m.group(1)]}\n")
            vistas.add(m.group(1))
        else:
            salida.append(linea)
    for k, v in nuevos.items():
        if k not in vistas:
            salida.append(f"{k}={v}\n")
    os.makedirs(os.path.dirname(RUTA_ENV), exist_ok=True)
    tmp = RUTA_ENV + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.writelines(salida)
    os.replace(tmp, RUTA_ENV)


def aplicar_env() -> dict:
    """Aplica el .env del dashboard sobre el entorno del proceso.

    El archivo es la fuente de verdad de lo que se configuró en la pestaña
    Configuración: lo que se guarda ahí es lo que se usa al ejecutar.
    Las claves que el archivo no trae (p. ej. en Kaggle, donde los secretos
    viven como variables de entorno) se dejan intactas.
    """
    valores = leer_env()
    for k, v in valores.items():
        if k in CLAVES_ENV:
            os.environ[k] = v
    return valores


def config_publica() -> dict:
    aplicar_env()
    valores = {k: os.environ.get(k, "") for k in CLAVES_ENV}
    pub = {}
    for k in CLAVES_ENV:
        v = valores.get(k, "")
        if k in CLAVES_SECRETAS:
            pub[k] = {"configurada": bool(v), "ultimos4": v[-4:] if len(v) >= 4 else ""}
        else:
            pub[k] = v
    return pub


# ---------------------------------------------------------------- datos
def _mision_ficha(lineas: list) -> str:
    """Extrae el texto de '## Misión' de la ficha (2 líneas, sin el header)."""
    texto = []
    dentro = False
    for ln in lineas:
        if re.match(r"##\s+Misión", ln):
            dentro = True
            continue
        if dentro:
            if ln.startswith("##"):
                break
            if ln.strip():
                texto.append(ln.strip())
            if len(texto) >= 2:
                break
    return " ".join(texto)[:220]


def _ultima_actividad() -> dict:
    """slug → marca_tiempo ISO de su ejecución más reciente (del audit log)."""
    from nucleo import auditoria
    ult = {}
    try:
        with open(auditoria.ARCHIVO, encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea:
                    continue
                try:
                    e = json.loads(linea)
                except json.JSONDecodeError:
                    continue
                slug = e.get("agente", "")
                ts = e.get("marca_tiempo", "")
                if slug and ts and ts > ult.get(slug, ""):
                    ult[slug] = ts
    except FileNotFoundError:
        pass
    return ult


def info_agentes() -> list:
    aplicar_env()
    ult = _ultima_actividad()
    datos = []
    for slug in modulo_agente.slugs():
        ficha_rel, modelo = modulo_agente.REGISTRO[slug]
        try:
            with open(os.path.join(RAIZ_REPO, ficha_rel), encoding="utf-8") as f:
                lineas = f.read().splitlines()
            nombre = lineas[0].lstrip("# ").strip() if lineas else slug
            area = ""
            for ln in lineas[1:8]:
                m = re.match(r"\*\*Área\*\*:\s*(.+)", ln)
                if m:
                    area = m.group(1).strip()
                    break
            resumen = _mision_ficha(lineas)
        except OSError:
            nombre, area, resumen = slug, "", ""
        datos.append({"slug": slug, "nombre": nombre, "area": area, "modelo": modelo,
                      "modelo_efectivo": modulo_agente._resolver_modelo(modelo),
                      "resumen": resumen,
                      "ultima_actividad": ult.get(slug, "")})
    return datos


def leer_chats() -> dict:
    """Historiales de chat por agente, persistidos en el servidor.

    El localStorage del navegador es por origen (cada túnel nuevo es un origen
    distinto y lo vacía); el servidor es la fuente de verdad que sobrevive a
    cambios de URL del túnel.
    """
    try:
        with open(RUTA_CHATS, encoding="utf-8") as f:
            datos = json.load(f)
            return datos if isinstance(datos, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _sanear_historial(hist) -> list:
    return [
        {"rol": t.get("rol"), "texto": str(t.get("texto", ""))[:8000]}
        for t in (hist or [])[-50:] if isinstance(t, dict) and t.get("texto")
    ]


def _sanear_trabajo(fuente: dict) -> dict:
    """Conserva el vínculo con un trabajo en curso (para reengancharlo)."""
    item = {}
    tid = fuente.get("trabajoId")
    if isinstance(tid, str) and tid:
        item["trabajoId"] = tid[:32]
    if fuente.get("terminado") is False:
        item["terminado"] = False
    try:
        item["vistos"] = max(0, int(fuente.get("vistos", 0) or 0))
    except (TypeError, ValueError):
        item["vistos"] = 0
    return item


def guardar_chats(chats: dict) -> None:
    os.makedirs(os.path.dirname(RUTA_CHATS), exist_ok=True)
    # Higiene: guardar solo historial (los trabajos en curso no sobreviven al
    # reinicio del servidor; el frontend los re-sondea o los marca).
    # Formato v2: {slug: {conversaciones: [{id, titulo, creada, actualizada,
    # historial, trabajoId?, terminado?, vistos?}], activa: id}}.
    # Se acepta el formato v1 ({slug: {historial, ...}}) y se conserva.
    limpio = {}
    for slug, estado in (chats or {}).items():
        if not isinstance(estado, dict):
            continue
        if isinstance(estado.get("conversaciones"), list):
            convs = []
            for c in estado["conversaciones"][-10:]:
                if not isinstance(c, dict):
                    continue
                item = {"historial": _sanear_historial(c.get("historial"))}
                cid = c.get("id")
                if isinstance(cid, str) and cid:
                    item["id"] = cid[:32]
                tit = c.get("titulo")
                if isinstance(tit, str) and tit:
                    item["titulo"] = tit[:120]
                for k in ("creada", "actualizada"):
                    v = c.get(k)
                    if isinstance(v, str) and v:
                        item[k] = v[:32]
                item.update(_sanear_trabajo(c))
                if item["historial"] or item.get("id"):
                    convs.append(item)
            if not convs:
                continue
            ids = {c.get("id") for c in convs if c.get("id")}
            act = estado.get("activa")
            limpio[slug] = {"conversaciones": convs,
                            "activa": act if act in ids else convs[-1].get("id")}
        else:
            hist = estado.get("historial") or []
            item = {"historial": _sanear_historial(hist)}
            item.update(_sanear_trabajo(estado))
            limpio[slug] = item
    with open(RUTA_CHATS, "w", encoding="utf-8") as f:
        json.dump(limpio, f, ensure_ascii=False)


def leer_auditoria(limite: int = 50, agente: str = "") -> dict:
    from nucleo import auditoria
    eventos = []
    try:
        with open(auditoria.ARCHIVO, encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if linea:
                    try:
                        eventos.append(json.loads(linea))
                    except json.JSONDecodeError:
                        continue
    except FileNotFoundError:
        pass
    total = len(eventos)
    if agente:
        eventos = [e for e in eventos if e.get("agente") == agente]
    tokens = sum((e.get("tokens_entrada") or 0) + (e.get("tokens_salida") or 0)
                 for e in eventos)
    return {
        "total": total,
        "filtrados": len(eventos),
        "tokens": tokens,
        "eventos": eventos[-limite:][::-1],
    }


def _build_hash() -> str:
    """Hash corto del commit en ejecución: permite verificar qué versión corre."""
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ_REPO,
                             capture_output=True, text=True, timeout=10)
        h = out.stdout.strip()
        return h if re.fullmatch(r"[0-9a-f]{4,40}", h) else "local"
    except Exception:
        return "local"


BUILD = _build_hash()



_TRABAJOS = {}
_TRABAJOS_LOCK = threading.Lock()


def _nuevo_trabajo(tarea: str, modelo: str, historial: list = None) -> str:
    """Crea un trabajo de orquestación que corre en segundo plano."""
    job_id = uuid.uuid4().hex[:12]
    with _TRABAJOS_LOCK:
        viejos = [k for k, v in _TRABAJOS.items() if v["terminado"]]
        for k in viejos[:max(0, len(viejos) - 20)]:
            del _TRABAJOS[k]
        _TRABAJOS[job_id] = {"eventos": [], "terminado": False,
                             "cancelado": False, "tarea": tarea[:120],
                             "historial": historial or []}
    h = threading.Thread(target=_correr_trabajo, args=(job_id, tarea, modelo),
                         daemon=True)
    h.start()
    return job_id


def _correr_trabajo(job_id: str, tarea: str, modelo: str) -> None:
    """Ejecuta la orquestación en un hilo: sobrevive a que se cierre el chat."""
    from nucleo import cliente as modulo_cliente
    from nucleo import delegacion as modulo_delegacion
    job = _TRABAJOS[job_id]
    try:
        aplicar_env()
        c = modulo_cliente.crear_cliente()
        for ev in modulo_delegacion.orquestar_eventos(tarea, c,
                                                     forzar_modelo=modelo,
                                                     historial=job.get("historial")):
            with _TRABAJOS_LOCK:
                if job["cancelado"]:
                    job["eventos"].append({
                        "tipo": "final",
                        "texto": "(Orquestación detenida por el dueño.)",
                        "delega": True, "delegaciones": [],
                        "cancelado": True})
                    break
                job["eventos"].append(ev)
            if ev.get("tipo") == "final":
                break
    except Exception as e:  # noqa: BLE001 - se reporta al dashboard
        with _TRABAJOS_LOCK:
            job["eventos"].append({"tipo": "error", "error": str(e)[:500]})
    finally:
        with _TRABAJOS_LOCK:
            job["terminado"] = True


def _nuevo_trabajo_pipeline(etapa: str, objetivo: str, componentes: list,
                            aprobacion: bool) -> str:
    """Crea un trabajo de pipeline (etapa LangGraph) en segundo plano."""
    job_id = uuid.uuid4().hex[:12]
    with _TRABAJOS_LOCK:
        viejos = [k for k, v in _TRABAJOS.items() if v["terminado"]]
        for k in viejos[:max(0, len(viejos) - 20)]:
            del _TRABAJOS[k]
        _TRABAJOS[job_id] = {"eventos": [], "terminado": False,
                             "cancelado": False, "tarea": f"{etapa}: {objetivo[:100]}",
                             "tipo": "pipeline"}
    h = threading.Thread(target=_correr_pipeline,
                         args=(job_id, etapa, objetivo, componentes, aprobacion),
                         daemon=True)
    h.start()
    return job_id


def _correr_pipeline(job_id: str, etapa: str, objetivo: str,
                     componentes: list, aprobacion: bool) -> None:
    """Ejecuta una etapa del pipeline en un hilo (puede tardar varios minutos)."""
    job = _TRABAJOS[job_id]
    try:
        aplicar_env()
        try:
            from orquestador import grafos
        except ImportError:
            raise RuntimeError(
                "Falta 'langgraph': instalá dependencias con "
                "`pip install -r runtime/requirements.txt`."
            )
        if etapa not in grafos.ETAPAS:
            raise ValueError(
                f"Etapa desconocida: {etapa}. Disponibles: {', '.join(grafos.ETAPAS)}")
        with _TRABAJOS_LOCK:
            job["eventos"].append({"tipo": "inicio", "etapa": etapa})
        # APROBACION_DESPLIEGUE rige solo para este trabajo (se restaura después).
        anterior = os.environ.get("APROBACION_DESPLIEGUE")
        if aprobacion:
            os.environ["APROBACION_DESPLIEGUE"] = "si"
        try:
            final = grafos.ejecutar_etapa(etapa, objetivo, componentes=componentes)
        finally:
            if anterior is None:
                os.environ.pop("APROBACION_DESPLIEGUE", None)
            else:
                os.environ["APROBACION_DESPLIEGUE"] = anterior
        with _TRABAJOS_LOCK:
            if job["cancelado"]:
                job["eventos"].append({"tipo": "final", "etapa": etapa,
                                       "cancelado": True,
                                       "texto": "(Pipeline detenido por el dueño.)"})
            else:
                job["eventos"].append({"tipo": "final", "etapa": etapa,
                                       "traza": final.get("traza", []),
                                       "artefactos": final.get("artefactos", {}),
                                       "veredictos": final.get("veredictos", {}),
                                       "reintentos_qa": final.get("reintentos_qa", 0)})
    except Exception as e:  # noqa: BLE001 - se reporta al dashboard
        with _TRABAJOS_LOCK:
            job["eventos"].append({"tipo": "error", "error": str(e)[:500]})
    finally:
        with _TRABAJOS_LOCK:
            job["terminado"] = True


def estado_empresa() -> dict:
    aplicar_env()
    etapas = []
    try:
        with open(os.path.join(RAIZ_REPO, "pipeline", "etapas.md"), encoding="utf-8") as f:
            for linea in f:
                m = re.match(r"##\s+(\d+)\.\s+(.+)", linea)
                if m:
                    etapas.append({"n": int(m.group(1)), "nombre": m.group(2).strip()})
    except OSError:
        pass
    productos = []
    dir_prod = os.path.join(RAIZ_REPO, "productos")
    try:
        for fn in sorted(os.listdir(dir_prod)):
            if fn.endswith(".md") and fn != "README.md":
                productos.append(fn[:-3])
    except OSError:
        pass
    return {
        "agentes": len(modulo_agente.slugs()),
        "etapas": etapas,
        "productos": productos,
        "proxy_configurado": bool(os.environ.get("LITELLM_MASTER_KEY")),
        "build": BUILD,
    }


def probar_modelos() -> dict:
    """Prueba en vivo cada modelo configurado contra el proveedor.

    Devuelve por modelo: ok True/False, latencia en ms o mensaje de error.
    Detecta modelos muertos/retirados (p. ej. HTTP 410) antes de ejecutar.
    """
    aplicar_env()
    try:
        from nucleo import cliente as modulo_cliente
    except ImportError:
        raise RuntimeError(
            "Falta el paquete 'openai': instalá dependencias con "
            "`pip install -r runtime/requirements.txt`."
        )
    c = modulo_cliente.crear_cliente()
    try:
        publicados = [m.id for m in c.models.list(timeout=30)]
    except Exception:  # noqa: BLE001 - no es fatal para la prueba
        publicados = []
    resultados = []
    for clave, etiqueta in MODELOS_PROBABLES:
        modelo = os.environ.get(clave, "")
        if not modelo:
            resultados.append({"clave": clave, "etiqueta": etiqueta, "modelo": "",
                               "ok": False, "error": "no configurado"})
            continue
        t0 = time.monotonic()
        try:
            r = c.chat.completions.create(
                model=modelo,
                messages=[{"role": "user",
                           "content": "Responde con una sola palabra: ok"}],
                max_tokens=16,
                temperature=0,
                timeout=45,
            )
            texto = (r.choices[0].message.content or "").strip()
            ms = int((time.monotonic() - t0) * 1000)
            if texto:
                resultados.append({"clave": clave, "etiqueta": etiqueta,
                                   "modelo": modelo, "ok": True,
                                   "latencia_ms": ms,
                                   "en_catalogo": (modelo in publicados) if publicados else None})
            else:
                resultados.append({"clave": clave, "etiqueta": etiqueta,
                                   "modelo": modelo, "ok": False,
                                   "error": "el modelo respondió vacío"})
        except Exception as e:  # noqa: BLE001 - se reporta en el resultado
            resultados.append({"clave": clave, "etiqueta": etiqueta,
                               "modelo": modelo, "ok": False,
                               "error": str(e)[:220]})
    return {"modelos_publicados": len(publicados), "resultados": resultados}


# ---------------------------------------------------------------- servidor
class Manejador(BaseHTTPRequestHandler):
    server_version = "CompanyOS/1.0"

    def _json(self, obj, codigo=200):
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _html(self):
        with open(os.path.join(DIR_DASHBOARD, "index.html"), "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _cuerpo(self) -> dict:
        largo = int(self.headers.get("Content-Length", 0) or 0)
        if not largo:
            return {}
        try:
            return json.loads(self.rfile.read(largo) or b"{}")
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _entero(qs, clave, defecto, minimo=1, maximo=200):
        try:
            v = int(qs.get(clave, [str(defecto)])[0])
        except (ValueError, TypeError):
            v = defecto
        return max(minimo, min(maximo, v))

    def do_GET(self):  # noqa: N802
        ruta = urlparse(self.path)
        if ruta.path in ("/", "/index.html"):
            self._html()
        elif ruta.path == "/api/agentes":
            self._json(info_agentes())
        elif ruta.path == "/api/auditoria":
            qs = parse_qs(ruta.query)
            limite = self._entero(qs, "limite", 50)
            agente = (qs.get("agente", [""])[0] or "").strip()
            if agente and agente not in modulo_agente.slugs():
                self._json({"ok": False, "error": "agente desconocido"}, 400)
                return
            self._json(leer_auditoria(limite, agente))
        elif ruta.path == "/api/config":
            self._json(config_publica())
        elif ruta.path == "/api/empresa":
            self._json(estado_empresa())
        elif ruta.path == "/api/modelos":
            # Modelos por nivel ya resueltos (para el selector del chat).
            aplicar_env()
            self._json({
                "base": modulo_agente._resolver_modelo("empresa-base"),
                "razonamiento": modulo_agente._resolver_modelo("empresa-razonamiento"),
                "ligero": modulo_agente._resolver_modelo("empresa-ligero"),
            })
        elif ruta.path == "/api/pipeline":
            # Etapas ejecutables del pipeline (requiere langgraph instalado).
            try:
                from orquestador import grafos as _grafos
                etapas = [{"id": k, "nombre": v[0]} for k, v in _grafos.ETAPAS.items()]
                self._json({"ok": True, "etapas": etapas})
            except ImportError:
                self._json({"ok": False,
                            "error": "Falta 'langgraph': pip install -r runtime/requirements.txt."})
        elif ruta.path == "/api/trabajos":
            qs = parse_qs(ruta.query)
            job_id = qs.get("id", [""])[0]
            try:
                desde = int(qs.get("desde", ["0"])[0] or 0)
            except ValueError:
                desde = 0
            with _TRABAJOS_LOCK:
                job = _TRABAJOS.get(job_id)
                if not job:
                    self._json({"ok": False, "error": "trabajo no encontrado"}, 404)
                    return
                eventos = job["eventos"][desde:]
                terminado = job["terminado"]
            self._json({"ok": True, "eventos": eventos, "terminado": terminado})
        elif ruta.path == "/api/chats":
            self._json({"ok": True, "chats": leer_chats()})
        else:
            self._json({"ok": False, "error": "no encontrado"}, 404)

    def do_POST(self):  # noqa: N802
        ruta = urlparse(self.path)
        if ruta.path == "/api/ejecutar":
            cuerpo = self._cuerpo()
            slug = cuerpo.get("slug", "")
            tarea = cuerpo.get("tarea", "")
            if not slug or not tarea:
                self._json({"ok": False, "error": "faltan slug o tarea"}, 400)
                return
            if slug not in modulo_agente.slugs():
                self._json({"ok": False, "error": "agente desconocido"}, 400)
                return
            try:
                aplicar_env()
                try:
                    from nucleo import cliente as modulo_cliente
                except ImportError:
                    raise RuntimeError(
                        "Falta el paquete 'openai': instalá dependencias con "
                        "`pip install -r runtime/requirements.txt`."
                    )
                c = modulo_cliente.crear_cliente()
                historial = cuerpo.get("historial", [])
                if not isinstance(historial, list):
                    historial = []
                r = modulo_agente.ejecutar_agente(
                    slug, tarea, c, forzar_modelo=cuerpo.get("modelo", ""),
                    historial=historial)
                self._json({"ok": True, "agente": r["agente"], "modelo": r["modelo"],
                            "texto": r["texto"],
                            "tokens_entrada": r["tokens_entrada"],
                            "tokens_salida": r["tokens_salida"]})
            except Exception as e:  # noqa: BLE001 - se reporta al dashboard
                self._json({"ok": False, "error": str(e)})
        elif ruta.path == "/api/orquestar":
            # El Gerente General planifica, delega a especialistas y consolida.
            cuerpo = self._cuerpo()
            tarea = cuerpo.get("tarea", "")
            if not tarea:
                self._json({"ok": False, "error": "falta tarea"}, 400)
                return
            try:
                aplicar_env()
                try:
                    from nucleo import cliente as modulo_cliente
                    from nucleo import delegacion as modulo_delegacion
                except ImportError:
                    raise RuntimeError(
                        "Falta el paquete 'openai': instalá dependencias con "
                        "`pip install -r runtime/requirements.txt`."
                    )
                c = modulo_cliente.crear_cliente()
                modelo = cuerpo.get("modelo", "")
                r = modulo_delegacion.orquestar(tarea, c, forzar_modelo=modelo)
                self._json({"ok": True, **r})
            except Exception as e:  # noqa: BLE001 - se reporta al dashboard
                self._json({"ok": False, "error": str(e)})
        elif ruta.path == "/api/trabajos":
            # Crea un trabajo de orquestación en segundo plano y devuelve su id.
            # El trabajo sigue corriendo aunque se cierre el chat.
            cuerpo = self._cuerpo()
            tarea = cuerpo.get("tarea", "")
            if not tarea:
                self._json({"ok": False, "error": "falta tarea"}, 400)
                return
            job_id = _nuevo_trabajo(tarea, cuerpo.get("modelo", ""),
                                    historial=cuerpo.get("historial") if isinstance(
                                        cuerpo.get("historial"), list) else None)
            self._json({"ok": True, "id": job_id})
        elif ruta.path == "/api/trabajos/cancelar":
            cuerpo = self._cuerpo()
            with _TRABAJOS_LOCK:
                job = _TRABAJOS.get(cuerpo.get("id", ""))
                if job and not job["terminado"]:
                    job["cancelado"] = True
            self._json({"ok": True})
        elif ruta.path == "/api/pipeline":
            # Crea un trabajo de pipeline en segundo plano y devuelve su id.
            # Se sondea igual que la orquestación: GET /api/trabajos?id=...
            cuerpo = self._cuerpo()
            etapa = (cuerpo.get("etapa") or "").strip()
            objetivo = (cuerpo.get("objetivo") or "").strip()
            if not etapa or not objetivo:
                self._json({"ok": False, "error": "faltan etapa u objetivo"}, 400)
                return
            try:
                from orquestador import grafos as _grafos
                if etapa not in _grafos.ETAPAS:
                    self._json({"ok": False,
                                "error": f"etapa desconocida: {etapa}"}, 400)
                    return
            except ImportError:
                self._json({"ok": False,
                            "error": "Falta 'langgraph': pip install -r runtime/requirements.txt."},
                           400)
                return
            comp = cuerpo.get("componentes") or ["constructor"]
            if isinstance(comp, str):
                comp = [c.strip() for c in comp.split(",") if c.strip()] or ["constructor"]
            comp = [c for c in comp if c in modulo_agente.slugs()] or ["constructor"]
            job_id = _nuevo_trabajo_pipeline(
                etapa, objetivo, comp, bool(cuerpo.get("aprobacion_despliegue")))
            self._json({"ok": True, "id": job_id})
        elif ruta.path == "/api/chats":
            # Persiste historiales de chat en el servidor (sobreviven a cambios
            # de URL del túnel; el localStorage es por origen y se vacía).
            cuerpo = self._cuerpo()
            chats = cuerpo.get("chats")
            if not isinstance(chats, dict):
                self._json({"ok": False, "error": "chats inválido"}, 400)
                return
            try:
                guardar_chats(chats)
                self._json({"ok": True})
            except Exception as e:  # noqa: BLE001 - se reporta al dashboard
                self._json({"ok": False, "error": str(e)})
        elif ruta.path == "/api/probar":
            try:
                r = probar_modelos()
                self._json({"ok": True, **r})
            except Exception as e:  # noqa: BLE001 - se reporta al dashboard
                self._json({"ok": False, "error": str(e)})
        elif ruta.path == "/api/config":
            cuerpo = self._cuerpo()
            nuevos = {}
            for k in CLAVES_ENV:
                if k in cuerpo and isinstance(cuerpo[k], str):
                    v = cuerpo[k].strip().split("\n")[0]
                    # clave secreta vacía = conservar la actual
                    if k in CLAVES_SECRETAS and not v:
                        continue
                    nuevos[k] = v
            # El proxy (config.yaml) lee MODELO_BASE/_RAZONAMIENTO/_LIGERO y el
            # runtime directo lee MODELO_EMPRESA_*: se escriben ambos para que
            # los dos modos funcionen con lo configurado acá.
            for suf in ("BASE", "RAZONAMIENTO", "LIGERO"):
                v = nuevos.get(f"MODELO_EMPRESA_{suf}", "").strip()
                if v:
                    nuevos[f"MODELO_{suf}"] = v
            escribir_env(nuevos)
            self._json({"ok": True, "config": config_publica()})
        else:
            self._json({"ok": False, "error": "no encontrado"}, 404)

    def log_message(self, *args):  # noqa: N802
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description="Dashboard web local de la empresa.")
    ap.add_argument("--puerto", type=int, default=int(os.environ.get("DASHBOARD_PORT", "8080")))
    args = ap.parse_args()
    servidor = ThreadingHTTPServer(("127.0.0.1", args.puerto), Manejador)
    print(f"Dashboard en http://localhost:{args.puerto}  (Ctrl+C para detener)")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
