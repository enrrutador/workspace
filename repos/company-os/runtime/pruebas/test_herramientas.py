"""Tests del Tool Gateway y herramientas reales (secciones 11, 13, 15).

Cubre: contexto, registro, políticas, aprobaciones, gateway, sandbox de
filesystem, aislamiento entre tenants y tool calling del cliente.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from herramientas import (
    ContextoEjecucion, RegistroHerramientas, EspecHerramienta,
    MotorPoliticas, PerfilAutonomia, Decision, RIESGO,
    GestorAprobaciones, EstadoAprobacion,
    GatewayHerramientas, ResultadoHerramienta,
)
from herramientas import archivos
from herramientas.aprobaciones import hash_argumentos
from nucleo import cliente as modulo_cliente

PASADOS = []
FALLOS = []


def check(nombre, cond, detalle=""):
    (PASADOS if cond else FALLOS).append(nombre)
    print(f"[{'OK' if cond else 'FALLO'}] {nombre}" + (f" — {detalle}" if detalle and not cond else ""))


def nuevo_registro():
    r = RegistroHerramientas()
    archivos.registrar_herramientas(r)
    return r


def ctx_agente(agent_id="constructor", tenant="principal"):
    return ContextoEjecucion(tenant_id=tenant, agent_id=agent_id)


# ---------- 1. Contexto ----------
c = ContextoEjecucion(agent_id="constructor")
check("ctx: defaults", c.tenant_id == "principal" and c.user_id == "fabian")
try:
    c.tenant_id = "otro"
    check("ctx: inmutable", False)
except Exception:
    check("ctx: inmutable", True)
hijo = c.derivar("revisor", tenant_id="intruso")
check("ctx: derivar hereda tenant", hijo.tenant_id == "principal")
check("ctx: derivar enlaza padre", hijo.parent_execution_id == c.execution_id)
check("ctx: derivar ignora tenant intruso", hijo.tenant_id != "intruso")

# ---------- 2. Registro ----------
r = nuevo_registro()
check("registro: 4 herramientas fs", r.nombres() == ["buscar_archivos", "escribir_archivo",
      "leer_archivo", "listar_archivos"])
check("registro: desconocida → None", r.obtener("no_existe") is None)
esp = r.obtener("leer_archivo").espec
sch = esp.esquema_openai()
check("registro: esquema openai", sch["type"] == "function"
      and sch["function"]["name"] == "leer_archivo"
      and "ruta" in sch["function"]["parameters"]["required"])
ok, err = esp.validar_argumentos({})
check("registro: valida requeridos", not ok and "ruta" in err)
ok, _ = esp.validar_argumentos({"ruta": "a.md", "otra": 1})
check("registro: rechaza param desconocido", not ok)

# ---------- 3. Sandbox filesystem ----------
import herramientas.archivos as ma
ma.RAIZ_WORKSPACES = tempfile.mkdtemp(prefix="ws-test-")
ctx = ctx_agente()
ma.escribir_archivo(ctx, "notas/hola.md", "contenido secreto del tenant")
check("fs: write+read", ma.leer_archivo(ctx, "notas/hola.md") == "contenido secreto del tenant")
check("fs: listar", "hola.md" in ma.listar_archivos(ctx, "notas"))
check("fs: buscar", "notas/hola.md" in ma.buscar_archivos(ctx, "secreto"))

for mala in ["../escape.md", "../../x.md", "/etc/passwd", "a/../../b.md"]:
    try:
        ma.leer_archivo(ctx, mala)
        check(f"fs: bloquea {mala}", False)
    except Exception:
        check(f"fs: bloquea {mala}", True)

# symlink que escapa
fuera = os.path.join(tempfile.mkdtemp(prefix="fuera-"), "victima.txt")
open(fuera, "w").write("victima")
link = os.path.join(ma.workspace_tenant("principal"), "link-malo")
try:
    os.symlink(fuera, link)
    try:
        ma.leer_archivo(ctx, "link-malo")
        check("fs: bloquea symlink que escapa", False)
    except Exception:
        check("fs: bloquea symlink que escapa", True)
finally:
    if os.path.islink(link):
        os.unlink(link)

# aislamiento entre tenants
ctx_b = ctx_agente(tenant="otro-tenant")
try:
    ma.leer_archivo(ctx_b, "notas/hola.md")
    check("fs: tenant B no lee archivo de A", False)
except Exception:
    check("fs: tenant B no lee archivo de A", True)

# ---------- 4. Políticas ----------
m = MotorPoliticas(PerfilAutonomia.ESTANDAR)
check("pol: LOW estandar → ALLOW",
      m.decidir(RIESGO.LOW).decision == Decision.ALLOW)
check("pol: MEDIUM estandar → ALLOW",
      m.decidir(RIESGO.MEDIUM).decision == Decision.ALLOW)
check("pol: HIGH estandar → REQUIRE_APPROVAL",
      m.decidir(RIESGO.HIGH).decision == Decision.REQUIRE_APPROVAL)
check("pol: CRITICAL estandar → DENY",
      m.decidir(RIESGO.CRITICAL).decision == Decision.DENY)
mc = MotorPoliticas(PerfilAutonomia.CONSERVADOR)
check("pol: MEDIUM conservador → APPROVAL",
      mc.decidir(RIESGO.MEDIUM).decision == Decision.REQUIRE_APPROVAL)
maut = MotorPoliticas(PerfilAutonomia.AUTONOMO)
check("pol: CRITICAL autonomo → REQUIRE_APPROVAL (no ALLOW)",
      maut.decidir(RIESGO.CRITICAL).decision == Decision.REQUIRE_APPROVAL)
check("pol: cruce tenant siempre DENY",
      maut.decidir(RIESGO.LOW, cruce_tenant=True).decision == Decision.DENY)
check("pol: exfiltración siempre DENY",
      maut.decidir(RIESGO.LOW, exfiltra_credencial=True).decision == Decision.DENY)

# ---------- 5. Aprobaciones ----------
g = GestorAprobaciones(ttl_segundos=60)
ctx = ctx_agente()
ap = g.solicitar(ctx, "escribir_archivo", "escribir_archivo", "MEDIUM",
                 {"ruta": "a.md", "contenido": "x"})
check("apr: estado inicial PENDIENTE", ap.estado == EstadoAprobacion.PENDIENTE)
check("apr: aprobar otro tenant → None",
      g.aprobar(ap.id, "fabian", "otro-tenant") is None)
g.aprobar(ap.id, "fabian", "principal")
ok, _ = g.validar_y_consumir(ap.id, ctx, "escribir_archivo",
                             {"ruta": "a.md", "contenido": "x"})
check("apr: flujo válido consume", ok)
ok, err = g.validar_y_consumir(ap.id, ctx, "escribir_archivo",
                               {"ruta": "a.md", "contenido": "x"})
check("apr: reuso denegado", not ok and "consumida" in err)

ap2 = g.solicitar(ctx, "escribir_archivo", "escribir_archivo", "MEDIUM",
                  {"ruta": "b.md", "contenido": "x"})
g.aprobar(ap2.id, "fabian", "principal")
ok, err = g.validar_y_consumir(ap2.id, ctx, "escribir_archivo",
                               {"ruta": "b.md", "contenido": "DISTINTO"})
check("apr: args distintos denegado", not ok and "argumentos" in err)

g_corto = GestorAprobaciones(ttl_segundos=-1)
ap3 = g_corto.solicitar(ctx, "escribir_archivo", "escribir_archivo", "MEDIUM", {})
check("apr: expirada no se aprueba", g_corto.aprobar(ap3.id, "fabian", "principal") is None)

# ---------- 6. Gateway ----------
gw = GatewayHerramientas(registro=nuevo_registro())
ctx = ctx_agente("constructor")
res = gw.ejecutar(ctx, "no_existe", {})
check("gw: herramienta desconocida → deny",
      not res.ok and res.codigo == "tool_error")
res = gw.ejecutar(ctx, "leer_archivo", {"ruta": "x.md"})
check("gw: sin permiso → permission_denied",
      not res.ok and res.codigo == "permission_denied")

gw.permitir("constructor", ["leer_archivo", "escribir_archivo", "listar_archivos"])
res = gw.ejecutar(ctx, "leer_archivo", {})
check("gw: esquema inválido → validation_error",
      not res.ok and res.codigo == "validation_error")
res = gw.ejecutar(ctx, "escribir_archivo", {"ruta": "gw-test.md", "contenido": "hola"})
check("gw: MEDIUM estandar → ALLOW directo",
      res.ok and res.decision_politica == Decision.ALLOW, res.error)
res = gw.ejecutar(ctx, "leer_archivo", {"ruta": "gw-test.md"})
check("gw: leer lo escrito", res.ok and res.datos == "hola")
res = gw.ejecutar(ctx, "leer_archivo", {"ruta": "../escape.md"})
check("gw: sandbox vía gateway → tenant_violation",
      not res.ok and res.codigo == "tenant_violation")

# HIGH requiere aprobación: registro una herramienta HIGH de prueba
reg2 = nuevo_registro()
reg2.registrar(
    EspecHerramienta(nombre="deploy_produccion", descripcion="Despliega.",
                     esquema_entrada={}, riesgo="HIGH",
                     permisos=("deploy",), idempotente=False),
    lambda ctx, args: "desplegado")
gw2 = GatewayHerramientas(registro=reg2)
gw2.permitir("sre", ["deploy_produccion"])
ctx_sre = ctx_agente("sre")
res = gw2.ejecutar(ctx_sre, "deploy_produccion", {})
check("gw: HIGH → approval_required con id",
      not res.ok and res.codigo == "approval_required" and res.aprobacion_id)
ap_id = res.aprobacion_id
gw2.aprobaciones.aprobar(ap_id, "fabian", "principal")
res = gw2.ejecutar(ctx_sre, "deploy_produccion", {}, aprobacion_id=ap_id)
check("gw: con aprobación válida ejecuta", res.ok and res.datos == "desplegado")
res = gw2.ejecutar(ctx_sre, "deploy_produccion", {}, aprobacion_id=ap_id)
check("gw: aprobación de un solo uso", not res.ok)

# ---------- 7. Tool calling del cliente (mock) ----------
class _Msg:
    def __init__(self, content="", tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class _TC:
    def __init__(self, id_, name, args):
        self.id = id_
        self.function = type("F", (), {"name": name,
                                       "arguments": json.dumps(args)})()


class _Choice:
    def __init__(self, msg):
        self.message = msg


class _Resp:
    def __init__(self, msg):
        self.choices = [_Choice(msg)]
        self.usage = type("U", (), {"prompt_tokens": 5, "completion_tokens": 5})()


class MockCliente:
    def __init__(self, secuencia):
        self.secuencia = list(secuencia)
        self.llamadas = []
    @property
    def chat(self):
        return self
    @property
    def completions(self):
        return self
    def create(self, **kw):
        self.llamadas.append(kw)
        return self.secuencia.pop(0)


tools = [{"type": "function",
          "function": {"name": "leer_archivo", "description": "lee",
                       "parameters": {"type": "object", "properties": {}}},
          }]
cli = MockCliente([
    _Resp(_Msg(tool_calls=[_TC("c1", "leer_archivo", {"ruta": "a.md"})])),
    _Resp(_Msg(content="Listo, leí el archivo.")),
])
visto = {}
def fake_tool(nombre, args):
    visto["nombre"] = nombre
    visto["args"] = args
    return "contenido del archivo"
out = modulo_cliente.completar_con_herramientas(
    cli, "modelo-x", "system", "tarea", tools, fake_tool)
check("toolloop: llama la tool", visto.get("nombre") == "leer_archivo")
check("toolloop: texto final", out["texto"] == "Listo, leí el archivo.")
check("toolloop: trazabilidad", out["llamadas_herramientas"] == [
    {"herramienta": "leer_archivo", "argumentos": {"ruta": "a.md"}, "ok": True}])
check("toolloop: tools viajan al provider",
      cli.llamadas[0].get("tools") == tools)

# límite de iteraciones: modelo que siempre pide tools
cli2 = MockCliente([_Resp(_Msg(tool_calls=[_TC("c9", "leer_archivo", {})]))] * 15)
out2 = modulo_cliente.completar_con_herramientas(
    cli2, "m", "s", "t", tools, lambda n, a: "x", max_iteraciones=4)
check("toolloop: respeta max_iteraciones", len(cli2.llamadas) == 4)

# sin tools equivale a completar()
cli3 = MockCliente([_Resp(_Msg(content="hola"))])
out3 = modulo_cliente.completar_con_herramientas(cli3, "m", "s", "t", [], fake_tool)
check("toolloop: sin tools no pide tool_choice",
      "tools" not in cli3.llamadas[0] and out3["texto"] == "hola")

print()
print(f"PASADOS: {len(PASADOS)}  FALLOS: {len(FALLOS)}")
if FALLOS:
    print("FALLOS:", FALLOS)
    sys.exit(1)
print("TODO OK — gateway y herramientas reales")
