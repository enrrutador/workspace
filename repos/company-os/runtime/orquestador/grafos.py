"""Grafos LangGraph que implementan las etapas del pipeline.

Etapas implementadas:
  tesis        (1): GG escribe la tesis, el equipo rojo la ataca, GG decide SEGUIR/MATAR
  validacion   (2): investigación, landing, cobro de preventa, veredicto VALIDADO/DESCARTADO
  construccion (3): spec → diseño → UX → build → revisión → seguridad
                   → QA --(rechazo)--> build (reintento, máx 2)
                   → SRE (SLOs) → Despliegues (frena sin aprobación de Fabian)
  comercial    (6): ICP, outreach, criterios de calificación, plan comercial
  producto     (modo empresa): tesis → validacion → construccion → comercial,
               con compuertas: si una etapa mata el producto, se detiene.

Cada nodo ejecuta un agente con el runtime existente y deja su artefacto
en el estado; el siguiente nodo lo recibe como contexto. Todo queda en la
auditoría como ejecuciones individuales.
"""
import operator
import os
import re
from typing import TypedDict, Annotated

from langgraph.graph import StateGraph, END

from nucleo import agente as modulo_agente
from nucleo import cliente as modulo_cliente

MAX_REINTENTOS_QA = 2
MAX_CHARS_ARTEFACTO = 6000


class Estado(TypedDict):
    objetivo: str
    componentes: list
    artefactos: Annotated[dict, operator.or_]
    traza: Annotated[list, operator.add]
    reintentos_qa: int
    veredictos: Annotated[dict, operator.or_]


def _resumen_artefactos(artefactos: dict) -> str:
    if not artefactos:
        return "(sin artefactos previos)"
    partes = []
    for nombre, texto in artefactos.items():
        recorte = texto[:MAX_CHARS_ARTEFACTO]
        if len(texto) > MAX_CHARS_ARTEFACTO:
            recorte += "\n[...recortado...]"
        partes.append(f"--- {nombre} ---\n{recorte}")
    return "\n\n".join(partes)


def _nodo(slug: str, artefacto: str, plantilla: str):
    """Crea un nodo que ejecuta un agente y guarda su artefacto."""
    def fn(state: Estado) -> dict:
        c = modulo_cliente.crear_cliente()
        tarea = plantilla.format(
            objetivo=state["objetivo"],
            artefactos=_resumen_artefactos(state["artefactos"]),
        )
        r = modulo_agente.ejecutar_agente(slug, tarea, c)
        return {
            "artefactos": {artefacto: r["texto"]},
            "traza": [f"{slug}: artefacto '{artefacto}' generado"],
        }
    fn.__name__ = f"nodo_{slug}_{artefacto}"
    return fn


def _nodo_build(state: Estado) -> dict:
    """Ejecuta los builders según los componentes pedidos (constructor por defecto)."""
    c = modulo_cliente.crear_cliente()
    artefactos, traza = {}, []
    for slug in state.get("componentes") or ["constructor"]:
        tarea = (
            f"Objetivo del producto: {state['objetivo']}\n\n"
            f"Artefactos previos:\n{_resumen_artefactos(state['artefactos'])}\n\n"
            "Implementá tu parte según tu rol. Si algo de la especificación o el "
            "diseño es ambiguo, declará el supuesto explícitamente en tu entrega."
        )
        r = modulo_agente.ejecutar_agente(slug, tarea, c)
        artefactos[f"build_{slug}"] = r["texto"]
        traza.append(f"{slug}: build completado")
    return {"artefactos": artefactos, "traza": traza}


def _nodo_despacho_qa(state: Estado) -> str:
    """Borde condicional: si QA rechaza, se reintenta el build (máx 2)."""
    reporte = state["artefactos"].get("reporte_qa", "")
    reintentos = state.get("reintentos_qa") or 0
    if "VEREDICTO: RECHAZADO" in reporte and reintentos < MAX_REINTENTOS_QA:
        return "reintentar"
    return "seguir"


def _nodo_reintento(state: Estado) -> dict:
    return {
        "reintentos_qa": (state.get("reintentos_qa") or 0) + 1,
        "traza": ["control-de-calidad: veredicto RECHAZADO, se reintenta el build"],
    }


def _nodo_despliegue(state: Estado) -> dict:
    """In-the-loop: sin aprobación explícita de Fabian no se despliega."""
    if os.environ.get("APROBACION_DESPLIEGUE", "").lower() != "si":
        return {
            "artefactos": {
                "despliegue": (
                    "PENDIENTE_APROBACION_FABIAN: el plan de despliegue está listo "
                    "pero no se ejecutó. Fabian debe aprobar (in-the-loop)."
                )
            },
            "traza": ["responsable-despliegues: frenado, pendiente aprobación de Fabian"],
        }
    c = modulo_cliente.crear_cliente()
    tarea = (
        f"Objetivo del producto: {state['objetivo']}\n\n"
        f"Artefactos previos:\n{_resumen_artefactos(state['artefactos'])}\n\n"
        "Fabian APROBÓ el despliegue. Ejecutá el plan de despliegue según tu rol."
    )
    r = modulo_agente.ejecutar_agente("responsable-despliegues", tarea, c)
    return {
        "artefactos": {"despliegue": r["texto"]},
        "traza": ["responsable-despliegues: despliegue ejecutado con aprobación"],
    }


def grafo_construccion():
    """Construye y compila el grafo de la etapa 3."""
    g = StateGraph(Estado)

    g.add_node("spec", _nodo(
        "gerente-general", "especificacion",
        "Objetivo del producto: {objetivo}\n\n"
        "Escribí la especificación funcional completa: qué se construye, para quién, "
        "criterios de aceptación verificables y criterios de salida del uso interno."))
    g.add_node("diseno", _nodo(
        "arquitecto", "diseno",
        "Especificación:\n{artefactos}\n\n"
        "Diseñá la arquitectura (C4) y registrá los ADRs de las decisiones relevantes."))
    g.add_node("ux", _nodo(
        "disenador-ux-ui", "diseno_ux",
        "Especificación y diseño:\n{artefactos}\n\n"
        "Diseñá flujos y pantallas según tu rol. El diseño entra antes del código."))
    g.add_node("build", _nodo_build)
    g.add_node("revision", _nodo(
        "revisor", "revision",
        "Artefactos previos:\n{artefactos}\n\n"
        "Revisá el código entregado en los artefactos build_*. Marcá bloqueantes y "
        "sugerencias. Cerrá con tu veredicto."))
    g.add_node("seguridad", _nodo(
        "ingeniero-seguridad", "revision_seguridad",
        "Artefactos previos:\n{artefactos}\n\n"
        "Revisá la seguridad de lo construido (threat model ligero + OWASP). "
        "Si hay riesgo crítico, declaralo y FRENÁ el flujo con justificación."))
    g.add_node("qa", _nodo(
        "control-de-calidad", "reporte_qa",
        "Artefactos previos:\n{artefactos}\n\n"
        "Probá lo construido y reportá. Cerrá SIEMPRE con una línea exacta: "
        "'VEREDICTO: APROBADO' o 'VEREDICTO: RECHAZADO' (con motivos si rechazás)."))
    g.add_node("reintento", _nodo_reintento)
    g.add_node("sre", _nodo(
        "sre", "slos",
        "Artefactos previos:\n{artefactos}\n\n"
        "Definí los SLOs del producto (disponibilidad, latencia, errores) y la "
        "observabilidad mínima para el lanzamiento."))
    g.add_node("despliegue", _nodo_despliegue)

    g.set_entry_point("spec")
    g.add_edge("spec", "diseno")
    g.add_edge("diseno", "ux")
    g.add_edge("ux", "build")
    g.add_edge("build", "revision")
    g.add_edge("revision", "seguridad")
    g.add_edge("seguridad", "qa")
    g.add_conditional_edges("qa", _nodo_despacho_qa,
                            {"reintentar": "reintento", "seguir": "sre"})
    g.add_edge("reintento", "build")
    g.add_edge("sre", "despliegue")
    g.add_edge("despliegue", END)

    return g.compile()


# Registro de etapas implementadas (extensible: una entrada = un grafo).
# Los constructores se asignan al final del archivo.
ETAPAS: dict = {}


def _patron_veredicto(marca_ok: str) -> "re.Pattern":
    r"""'VEREDICTO: SEGUIR' → /\bVEREDICTO\s*:\s*SEGUIR\b/i.

    Tolera mayúsculas/minúsculas y espacios (el modelo a veces escribe
    'veredicto:seguir' o '**VEREDICTO: SEGUIR**'). Si no hay marca,
    fail-closed: el llamador devuelve el valor_ko.
    """
    partes = [re.escape(p) for p in marca_ok.strip().split()]
    return re.compile(r"\b" + r"\s*".join(partes) + r"\b", re.IGNORECASE)


def _nodo_veredicto(clave: str, artefacto_fuente: str,
                    marca_ok: str, valor_ok: str, valor_ko: str):
    """Lee el veredicto de un artefacto y lo guarda en el estado."""
    patron = _patron_veredicto(marca_ok)

    def fn(state: Estado) -> dict:
        texto = state["artefactos"].get(artefacto_fuente, "")
        veredicto = valor_ok if patron.search(texto) else valor_ko
        return {
            "veredictos": {clave: veredicto},
            "traza": [f"veredicto {clave}: {veredicto}"],
        }
    fn.__name__ = f"nodo_veredicto_{clave}"
    return fn


def grafo_tesis():
    """Etapa 1: el Gerente General escribe la tesis, el equipo rojo la ataca,
    el Gerente General decide SEGUIR o MATAR."""
    g = StateGraph(Estado)
    g.add_node("tesis", _nodo(
        "gerente-general", "tesis",
        "Objetivo del producto: {objetivo}\n\n"
        "Escribí la tesis: problema, cliente, propuesta de valor, hipótesis "
        "falsables y criterios de cierre (qué evidencia la mataría)."))
    g.add_node("rojo_arquitecto", _nodo(
        "arquitecto", "ataque_arquitecto",
        "Tesis:\n{artefactos}\n\n"
        "Atacá la tesis como equipo rojo: qué supuestos técnicos son débiles, "
        "qué la haría inviable de construir. Sé despiadado y concreto."))
    g.add_node("rojo_seguridad", _nodo(
        "ingeniero-seguridad", "ataque_seguridad",
        "Tesis:\n{artefactos}\n\n"
        "Atacá la tesis como equipo rojo: riesgos legales, regulatorios y de "
        "seguridad (fuentes de datos, términos de servicio, privacidad)."))
    g.add_node("rojo_analista", _nodo(
        "analista", "ataque_analista",
        "Tesis:\n{artefactos}\n\n"
        "Atacá la tesis como equipo rojo: evidencia de mercado en contra, "
        "competidores, por qué podría no haber demanda real."))
    g.add_node("tesis_final", _nodo(
        "gerente-general", "tesis_final",
        "Tesis y ataques del equipo rojo:\n{artefactos}\n\n"
        "Revisá la tesis a la luz de los ataques: reforzala o matala. "
        "Cerrá SIEMPRE con una línea exacta: 'VEREDICTO: SEGUIR' o 'VEREDICTO: MATAR'."))
    g.add_node("veredicto", _nodo_veredicto(
        "tesis", "tesis_final", "VEREDICTO: SEGUIR", "SEGUIR", "MATAR"))

    g.set_entry_point("tesis")
    g.add_edge("tesis", "rojo_arquitecto")
    g.add_edge("rojo_arquitecto", "rojo_seguridad")
    g.add_edge("rojo_seguridad", "rojo_analista")
    g.add_edge("rojo_analista", "tesis_final")
    g.add_edge("tesis_final", "veredicto")
    g.add_edge("veredicto", END)
    return g.compile()


def grafo_validacion():
    """Etapa 2: investigación, landing de validación y cobro de preventa.
    El Gerente General decide VALIDADO o DESCARTADO según la evidencia."""
    g = StateGraph(Estado)
    g.add_node("investigacion", _nodo(
        "analista", "investigacion",
        "Tesis:\n{artefactos}\n\n"
        "Investigá la evidencia de demanda: tamaño del dolor, disposición a pagar, "
        "competidores y sus precios. Datos concretos, no opiniones."))
    g.add_node("landing", _nodo(
        "constructor", "landing",
        "Tesis e investigación:\n{artefactos}\n\n"
        "Armá la landing de validación: propuesta de valor, prueba social futura, "
        "llamado a la acción para la preventa. Entregá el copy y la estructura."))
    g.add_node("preventa", _nodo(
        "facturador", "cobro_preventa",
        "Tesis y landing:\n{artefactos}\n\n"
        "Diseñá el mecanismo de cobro de la preventa: precio, qué incluye, "
        "cómo se cobra y cómo se devuelve si no se construye."))
    g.add_node("veredicto", _nodo(
        "gerente-general", "veredicto_validacion",
        "Tesis, investigación, landing y preventa:\n{artefactos}\n\n"
        "¿Hay señal suficiente para construir? Evaluá la evidencia como si el "
        "dinero fuera tuyo. Cerrá SIEMPRE con 'VEREDICTO: VALIDADO' o "
        "'VEREDICTO: DESCARTADO'."))
    g.add_node("cierre", _nodo_veredicto(
        "validacion", "veredicto_validacion",
        "VEREDICTO: VALIDADO", "VALIDADO", "DESCARTADO"))

    g.set_entry_point("investigacion")
    g.add_edge("investigacion", "landing")
    g.add_edge("landing", "preventa")
    g.add_edge("preventa", "veredicto")
    g.add_edge("veredicto", "cierre")
    g.add_edge("cierre", END)
    return g.compile()


def grafo_comercial():
    """Etapa 6: plan de venta — ICP, outreach y criterios de calificación."""
    g = StateGraph(Estado)
    g.add_node("icp", _nodo(
        "prospector", "icp_canales",
        "Producto construido:\n{artefactos}\n\n"
        "Definí el cliente ideal (ICP), los canales de adquisición y el mensaje "
        "por canal. Concreto y accionable."))
    g.add_node("outreach", _nodo(
        "contacto-inicial", "borrador_outreach",
        "ICP y canales:\n{artefactos}\n\n"
        "Escribí el borrador del primer contacto por canal: asunto, cuerpo, "
        "llamado a la acción. Tono humano, sin spam."))
    g.add_node("criterios", _nodo(
        "calificador", "criterios_calificacion",
        "ICP y borradores:\n{artefactos}\n\n"
        "Definí los criterios de calificación: qué hace que un interesado sea "
        "un prospecto válido y cuándo se descarta."))
    g.add_node("plan", _nodo(
        "gerente-general", "plan_comercial",
        "Todo lo anterior:\n{artefactos}\n\n"
        "Consolidá el plan comercial: a quién vendemos, por dónde, con qué "
        "mensaje, cómo calificamos y qué métricas miramos los primeros 90 días."))

    g.set_entry_point("icp")
    g.add_edge("icp", "outreach")
    g.add_edge("outreach", "criterios")
    g.add_edge("criterios", "plan")
    g.add_edge("plan", END)
    return g.compile()


def _pasa_tesis(state: Estado) -> str:
    return "seguir" if state.get("veredictos", {}).get("tesis") == "SEGUIR" else "fin"


def _pasa_validacion(state: Estado) -> str:
    return "seguir" if state.get("veredictos", {}).get("validacion") == "VALIDADO" else "fin"


def grafo_producto():
    """Modo empresa: pipeline punta a punta en lenguaje natural.

    tesis → [compuerta] → validacion → [compuerta] → construccion → comercial.
    Si una etapa mata el producto, el grafo se detiene y lo reporta.

    Cada etapa corre con sub-estado fresco (traza/veredictos propios) y el nodo
    devuelve solo sus deltas: así la traza del grafo padre no se duplica en las
    fronteras entre subgrafos. Los artefactos sí se heredan (la validación lee
    la tesis, la construcción lee la validación, etc.).
    """
    def _nodo_etapa(nombre: str, constructor):
        def fn(state: Estado) -> dict:
            previos = set(state.get("artefactos", {}))
            sub = constructor().invoke({
                **state,
                "traza": [],
                "veredictos": {},
                "reintentos_qa": 0,
            })
            nuevos_arts = {k: v for k, v in sub["artefactos"].items()
                           if k not in previos}
            return {
                "artefactos": nuevos_arts,
                "traza": [f"--- etapa {nombre} ---"] + sub["traza"],
                "veredictos": sub["veredictos"],
                "reintentos_qa": sub["reintentos_qa"],
            }
        fn.__name__ = f"nodo_etapa_{nombre}"
        return fn

    g = StateGraph(Estado)
    g.add_node("tesis", _nodo_etapa("tesis", grafo_tesis))
    g.add_node("validacion", _nodo_etapa("validacion", grafo_validacion))
    g.add_node("construccion", _nodo_etapa("construccion", grafo_construccion))
    g.add_node("comercial", _nodo_etapa("comercial", grafo_comercial))

    g.set_entry_point("tesis")
    g.add_conditional_edges("tesis", _pasa_tesis, {"seguir": "validacion", "fin": END})
    g.add_conditional_edges("validacion", _pasa_validacion,
                            {"seguir": "construccion", "fin": END})
    g.add_edge("construccion", "comercial")
    g.add_edge("comercial", END)
    return g.compile()


ETAPAS["tesis"] = ("Etapa 1 — Tesis", grafo_tesis)
ETAPAS["validacion"] = ("Etapa 2 — Validación", grafo_validacion)
ETAPAS["construccion"] = ("Etapa 3 — Construcción", grafo_construccion)
ETAPAS["comercial"] = ("Etapa 6 — Comercial", grafo_comercial)
ETAPAS["producto"] = ("Modo empresa — pipeline punta a punta", grafo_producto)


def ejecutar_etapa(etapa: str, objetivo: str, componentes: list | None = None) -> dict:
    """Ejecuta una etapa del pipeline y devuelve el estado final."""
    if etapa not in ETAPAS:
        raise ValueError(f"Etapa desconocida: {etapa}. Disponibles: {', '.join(ETAPAS)}")
    _, constructor = ETAPAS[etapa]
    grafo = constructor()
    estado_inicial: Estado = {
        "objetivo": objetivo,
        "componentes": componentes or ["constructor"],
        "artefactos": {},
        "traza": [],
        "reintentos_qa": 0,
        "veredictos": {},
    }
    return grafo.invoke(estado_inicial)
