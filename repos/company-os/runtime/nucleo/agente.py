"""Registro y ejecución de los 26 agentes.

Cada agente se define por su ficha (el QUÉ) + su SKILL.md (el CÓMO).
El prompt del sistema se compone de ambos archivos del repo.
"""
import os

# slug -> (ficha relativa a la raíz del repo, modelo del proxy)
REGISTRO = {
    "gerente-general": ("agentes/direccion/gerente-general.md", "empresa-razonamiento"),
    "explorador": ("agentes/direccion/explorador.md", "empresa-razonamiento"),
    "arquitecto": ("agentes/ingenieria/arquitecto.md", "empresa-razonamiento"),
    "constructor": ("agentes/ingenieria/constructor.md", "empresa-base"),
    "desarrollador-mobile": ("agentes/ingenieria/desarrollador-mobile.md", "empresa-base"),
    "ingeniero-datos": ("agentes/ingenieria/ingeniero-datos.md", "empresa-base"),
    "ingeniero-ml": ("agentes/ingenieria/ingeniero-ml.md", "empresa-razonamiento"),
    "revisor": ("agentes/ingenieria/revisor.md", "empresa-razonamiento"),
    "control-de-calidad": ("agentes/ingenieria/control-de-calidad.md", "empresa-base"),
    "disenador-ux-ui": ("agentes/ingenieria/disenador-ux-ui.md", "empresa-base"),
    "ingeniero-seguridad": ("agentes/ingenieria/ingeniero-seguridad.md", "empresa-razonamiento"),
    "sre": ("agentes/ingenieria/sre.md", "empresa-base"),
    "responsable-despliegues": ("agentes/ingenieria/responsable-despliegues.md", "empresa-base"),
    "prospector": ("agentes/ventas/prospector.md", "empresa-base"),
    "contacto-inicial": ("agentes/ventas/contacto-inicial.md", "empresa-base"),
    "calificador": ("agentes/ventas/calificador.md", "empresa-base"),
    "custodio-crm": ("agentes/ventas/custodio-crm.md", "empresa-ligero"),
    "soporte-n1": ("agentes/soporte/soporte-n1.md", "empresa-ligero"),
    "responsable-activacion": ("agentes/soporte/responsable-activacion.md", "empresa-base"),
    "escalamiento": ("agentes/soporte/escalamiento.md", "empresa-razonamiento"),
    "contenidos": ("agentes/marketing/contenidos.md", "empresa-base"),
    "analista": ("agentes/marketing/analista.md", "empresa-razonamiento"),
    "facturador": ("agentes/finanzas/facturador.md", "empresa-base"),
    "conciliador": ("agentes/finanzas/conciliador.md", "empresa-base"),
    "responsable-informes": ("agentes/finanzas/responsable-informes.md", "empresa-base"),
    "guardian": ("agentes/operaciones/guardian.md", "empresa-razonamiento"),
}

RAIZ_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def slugs() -> list:
    return sorted(REGISTRO.keys())


def _leer(rel: str) -> str:
    with open(os.path.join(RAIZ_REPO, rel), encoding="utf-8") as f:
        return f.read()


def prompt_sistema(slug: str) -> str:
    """Compone el prompt del sistema: ficha + habilidad del agente + capacidades transversales."""
    if slug not in REGISTRO:
        raise ValueError(f"Agente desconocido: {slug}. Opciones: {', '.join(slugs())}")
    ficha_rel, _ = REGISTRO[slug]
    ficha = _leer(ficha_rel)
    try:
        skill = _leer(f"habilidades/{slug}/SKILL.md")
    except FileNotFoundError:
        skill = "(sin SKILL.md)"
    try:
        transversal = _leer("habilidades/autocapacitacion/SKILL.md")
    except FileNotFoundError:
        transversal = ""
    prompt = (
        f"QUIÉN TE HABLA: Estás hablando con {_dueno_nombre()}, el dueño y fundador "
        "de la empresa. Es el único humano en la empresa: todos los demás son "
        "agentes de IA como vos. Todas las decisiones finales, aprobaciones y "
        "escalaciones son suyas. Tratá cada mensaje suyo como una orden o "
        "consulta del dueño.\n\n"
        f"{_bloque_jerarquia(slug)}\n\n"
        "Sos un agente de la empresa. Esta es tu ficha de rol:\n\n"
        f"{ficha}\n\n"
        "Y esta es tu habilidad operativa (cómo ejecutar tu trabajo):\n\n"
        f"{skill}\n\n"
    )
    if transversal:
        prompt += (
            "Además tenés esta capacidad transversal (aplica siempre, en cualquier tarea):\n\n"
            f"{transversal}\n\n"
        )
    prompt += (
        "Respondé en español rioplatense, directo y sin relleno. "
        f"Si la tarea excede tus permisos o necesitás aprobación de {_dueno_nombre()}, "
        "decilo explícitamente en vez de inventar."
    )
    if slug == "gerente-general":
        prompt += "\n\n" + _BLOQUE_DELEGACION
    return prompt


def _dueno_nombre() -> str:
    """Nombre del dueño/fundador (el único humano). Configurable por entorno."""
    return os.environ.get("DUENO_NOMBRE", "Fabian")


def _bloque_jerarquia(slug: str) -> str:
    """Protocolo de comunicación jerárquica: nadie saltea niveles ni molesta
    al dueño con lo que puede resolver su superior."""
    base = (
        "CADENA DE MANDO: la empresa tiene orden jerárquico: "
        f"{_dueno_nombre()} (dueño, único humano) → Gerente General → especialistas. "
    )
    if slug == "gerente-general":
        return base + (
            "Sos el intermediario entre el dueño y los especialistas: todo lo operativo "
            "pasa por vos, y al dueño no le llega ruido de abajo.\n"
            "- No le devuelvas preguntas al dueño dentro de tu autoridad: decidí, "
            "delegá con el bloque DELEGAR y consolidá.\n"
            "- Al dueño le llevás UN informe accionable: qué se hizo y qué necesita "
            "SU decisión (solo lo estratégico, siempre con tu recomendación). Nada más.\n"
            "- Las salidas crudas de los especialistas son para tu consolidación, "
            "no para reenviarlas tal cual al dueño."
        )
    return base + (
        "Tu superior es el Gerente General: en trabajo delegado, tu salida la recibe "
        "él, no el dueño.\n"
        "TRATO CON EL DUEÑO (cuando te habla directamente):\n"
        "- Al dueño NO se lo cuestiona: nunca discutas su pedido, nunca lo retes, "
        "nunca lo alecciones ni le expliques tu rol. Ejecutá lo que pide.\n"
        "- PROHIBIDO devolverle preguntas: si te falta un dato, NO preguntes. Asumí "
        "lo más razonable, declaralo en UNA línea ('Asumo X'), y entregá el trabajo "
        "completo. Él te corrige si hace falta.\n"
        "- Traé respuestas y recomendaciones hechas, no preguntas. Al jefe solo le "
        "llegan decisiones, no tareas."
    )


_BLOQUE_DELEGACION = """DELEGACIÓN (tu herramienta como gerente):
Sos el segundo al mando: cuando el dueño te pide algo que requiere trabajo de
especialistas, NO lo hagas todo vos. Delegá incluyendo en tu respuesta un bloque
con este formato exacto:

DELEGAR:
- agente: <slug-del-agente>
  tarea: "<tarea en lenguaje natural, autocontenida, en una línea>"

Reglas:
- Usá solo slugs de agentes que existen en la empresa.
- Máximo 5 delegaciones por respuesta.
- Una tarea concreta y autocontenida por agente.
- No delegues lo que puedas resolver vos directamente con tu propio criterio.
El sistema va a ejecutar cada tarea delegada y te va a devolver los resultados
para que des la respuesta final consolidada al dueño. Si nada requiere
delegación, respondé directamente sin el bloque DELEGAR."""


def modelo_para(slug: str) -> str:
    return _resolver_modelo(REGISTRO[slug][1])


# Mapeo opcional de los nombres lógicos del proxy a modelos reales del proveedor.
# Permite correr sin el proxy LiteLLM (p. ej. en Kaggle/Colab) apuntando directo
# al proveedor: LITELLM_BASE_URL=https://api.openai.com/v1 + estas variables.
_MAPEO_MODELOS = {
    "empresa-base": "MODELO_EMPRESA_BASE",
    "empresa-razonamiento": "MODELO_EMPRESA_RAZONAMIENTO",
    "empresa-ligero": "MODELO_EMPRESA_LIGERO",
}


def _resolver_modelo(modelo: str) -> str:
    var = _MAPEO_MODELOS.get(modelo)
    if var and os.environ.get(var):
        return os.environ[var]
    return modelo


MAX_TURNOS_HISTORIAL = 20


def _validar_historial(historial) -> list:
    """Normaliza el historial de chat: [{"rol": "usuario"|"agente", "texto": str}]."""
    if not historial:
        return []
    if not isinstance(historial, list):
        raise ValueError("historial debe ser una lista de turnos")
    limpio = []
    for turno in historial[-MAX_TURNOS_HISTORIAL:]:
        if not isinstance(turno, dict):
            continue
        rol = "usuario" if turno.get("rol") == "usuario" else "agente"
        texto = str(turno.get("texto", ""))[:8000]
        if texto:
            limpio.append({"rol": rol, "texto": texto})
    return limpio


def ejecutar_agente(slug: str, tarea: str, cliente, forzar_modelo: str = "",
                    historial: list = None, herramientas: list = None,
                    gateway=None, ctx=None) -> dict:
    """Ejecuta un agente contra una tarea. Devuelve dict con respuesta y metadatos.

    historial: turnos previos de chat para conversaciones multi-turno.
    herramientas: nombres de herramientas habilitadas para este agente en esta
        ejecución (mínimo privilegio: si es None, el agente no usa herramientas
        y el comportamiento es el de siempre).
    gateway: GatewayHerramientas (se crea uno por defecto si hay herramientas).
    ctx: ContextoEjecucion (se crea uno por defecto con el agent_id).
    """
    from . import auditoria, cliente as modulo_cliente

    sistema = prompt_sistema(slug)
    modelo = _resolver_modelo(forzar_modelo or modelo_para(slug))
    historial = _validar_historial(historial)

    llamadas = []
    if herramientas:
        from herramientas import (
            ContextoEjecucion, GatewayHerramientas, REGISTRO_GLOBAL,
        )
        from herramientas import archivos as herramientas_archivos

        if not REGISTRO_GLOBAL.nombres():
            herramientas_archivos.registrar_herramientas(REGISTRO_GLOBAL)
        ctx = ctx or ContextoEjecucion(agent_id=slug)
        gateway = gateway or GatewayHerramientas(registro=REGISTRO_GLOBAL,
                                                 auditoria=auditoria)
        gateway.permitir(slug, herramientas)
        sistema += ("\n\nHERRAMIENTAS DISPONIBLES: podés usar estas herramientas "
                    "cuando te sirvan para la tarea: "
                    + ", ".join(herramientas)
                    + ". Usalas vía tool calling; si una requiere aprobación, "
                      "el sistema te lo va a informar y debés comunicarlo.")
        schemas = REGISTRO_GLOBAL.esquemas_openai(herramientas)

        def _ejecutar_tool(nombre, args):
            r = gateway.ejecutar(ctx, nombre, args)
            if r.ok:
                return r.datos if isinstance(r.datos, str) else str(r.datos)
            return f"[no ejecutada: {r.codigo}] {r.error}"

        resultado = modulo_cliente.completar_con_herramientas(
            cliente, modelo, sistema, tarea, schemas, _ejecutar_tool,
            historial=historial)
        llamadas = resultado.get("llamadas_herramientas", [])
    else:
        resultado = modulo_cliente.completar(cliente, modelo, sistema, tarea,
                                             historial=historial)
    auditoria.registrar(
        agente=slug,
        modelo=modelo,
        tarea=tarea,
        respuesta=resultado["texto"],
        tokens_entrada=resultado["tokens_entrada"],
        tokens_salida=resultado["tokens_salida"],
        llamadas_herramientas=llamadas or None,
        tenant_id=getattr(ctx, "tenant_id", None),
        execution_id=getattr(ctx, "execution_id", None),
    )
    return {"agente": slug, "modelo": modelo,
            "llamadas_herramientas": llamadas, **resultado}
