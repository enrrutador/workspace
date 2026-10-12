"""Herramientas de filesystem con sandbox por tenant.

Cada tenant tiene su workspace: workspace/tenants/<tenant_id>/. Toda ruta se
resuelve a real y debe quedar dentro del workspace. Bloquea: "..", rutas
absolutas, symlinks que escapen y directorios del sistema.

Herramientas: leer_archivo, escribir_archivo, listar_archivos, buscar_archivos.
"""
from __future__ import annotations

import fnmatch
import os

from .contexto import ContextoEjecucion
from .registro import EspecHerramienta, REGISTRO_GLOBAL

RAIZ_WORKSPACES = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "workspace", "tenants")
)

# Nombres que nunca se tocan, ni dentro del workspace.
_BLOQUEADOS = {".env", ".git", "__pycache__"}


class ViolacionSandbox(Exception):
    pass


def workspace_tenant(tenant_id: str) -> str:
    ruta = os.path.join(RAIZ_WORKSPACES, tenant_id)
    os.makedirs(ruta, exist_ok=True)
    return os.path.realpath(ruta)


def resolver_ruta(ctx: ContextoEjecucion, ruta: str) -> str:
    """Resuelve una ruta relativa dentro del workspace del tenant o falla."""
    if not isinstance(ruta, str) or not ruta.strip():
        raise ViolacionSandbox("ruta vacía")
    if os.path.isabs(ruta):
        raise ViolacionSandbox("rutas absolutas no permitidas")
    # Normalizar antes de unir para detectar ".." temprano.
    partes = ruta.replace("\\", "/").split("/")
    if ".." in partes:
        raise ViolacionSandbox("'..' no permitido")
    base = workspace_tenant(ctx.tenant_id)
    candidato = os.path.realpath(os.path.join(base, *partes))
    if candidato != base and not candidato.startswith(base + os.sep):
        raise ViolacionSandbox("la ruta escapa del workspace del tenant")
    nombre = os.path.basename(candidato)
    if nombre in _BLOQUEADOS:
        raise ViolacionSandbox(f"nombre bloqueado: {nombre}")
    return candidato


def leer_archivo(ctx: ContextoEjecucion, ruta: str, max_chars: int = 20000) -> str:
    real = resolver_ruta(ctx, ruta)
    if not os.path.isfile(real):
        raise FileNotFoundError(f"no existe: {ruta}")
    with open(real, encoding="utf-8", errors="replace") as f:
        return f.read(max_chars)


def escribir_archivo(ctx: ContextoEjecucion, ruta: str, contenido: str,
                      anexar: bool = False) -> str:
    real = resolver_ruta(ctx, ruta)
    os.makedirs(os.path.dirname(real), exist_ok=True)
    modo = "a" if anexar else "w"
    with open(real, modo, encoding="utf-8") as f:
        f.write(contenido)
    return f"escrito: {ruta} ({len(contenido)} chars)"


def listar_archivos(ctx: ContextoEjecucion, ruta: str = ".",
                    patron: str = "*") -> list:
    real = resolver_ruta(ctx, ruta)
    if not os.path.isdir(real):
        raise NotADirectoryError(f"no es un directorio: {ruta}")
    return sorted(n for n in os.listdir(real) if fnmatch.fnmatch(n, patron))


def buscar_archivos(ctx: ContextoEjecucion, texto: str, ruta: str = ".",
                    patron: str = "*.md", max_resultados: int = 20) -> list:
    base = resolver_ruta(ctx, ruta)
    hallados = []
    for dirpath, _dirs, archivos in os.walk(base):
        # No seguir symlinks que salgan del workspace.
        _dirs[:] = [d for d in _dirs
                    if not os.path.islink(os.path.join(dirpath, d))]
        for nombre in archivos:
            if not fnmatch.fnmatch(nombre, patron):
                continue
            completo = os.path.join(dirpath, nombre)
            if os.path.islink(completo):
                continue
            try:
                with open(completo, encoding="utf-8", errors="ignore") as f:
                    contenido = f.read(200000)
            except OSError:
                continue
            if texto.lower() in contenido.lower():
                rel = os.path.relpath(completo, base)
                hallados.append(rel)
                if len(hallados) >= max_resultados:
                    return hallados
    return hallados


def registrar_herramientas(registro=REGISTRO_GLOBAL) -> None:
    registro.registrar(
        EspecHerramienta(
            nombre="leer_archivo",
            descripcion="Lee un archivo de texto del workspace del tenant.",
            esquema_entrada={
                "ruta": {"tipo": "string", "descripcion": "Ruta relativa dentro del workspace", "requerido": True},
                "max_chars": {"tipo": "integer", "descripcion": "Máximo de caracteres a leer", "requerido": False},
            },
            riesgo="LOW", permisos=("archivos.leer",), idempotente=True,
        ),
        lambda ctx, args: leer_archivo(ctx, args["ruta"], args.get("max_chars", 20000)),
    )
    registro.registrar(
        EspecHerramienta(
            nombre="escribir_archivo",
            descripcion="Escribe (o anexa) un archivo de texto en el workspace del tenant.",
            esquema_entrada={
                "ruta": {"tipo": "string", "descripcion": "Ruta relativa dentro del workspace", "requerido": True},
                "contenido": {"tipo": "string", "descripcion": "Contenido a escribir", "requerido": True},
                "anexar": {"tipo": "boolean", "descripcion": "Anexar en vez de sobrescribir", "requerido": False},
            },
            riesgo="MEDIUM", permisos=("archivos.escribir",), idempotente=False,
        ),
        lambda ctx, args: escribir_archivo(ctx, args["ruta"], args["contenido"],
                                           args.get("anexar", False)),
    )
    registro.registrar(
        EspecHerramienta(
            nombre="listar_archivos",
            descripcion="Lista archivos de un directorio del workspace del tenant.",
            esquema_entrada={
                "ruta": {"tipo": "string", "descripcion": "Directorio relativo ('.' = raíz)", "requerido": False},
                "patron": {"tipo": "string", "descripcion": "Patrón glob, p. ej. *.md", "requerido": False},
            },
            riesgo="LOW", permisos=("archivos.leer",), idempotente=True,
        ),
        lambda ctx, args: listar_archivos(ctx, args.get("ruta", "."),
                                          args.get("patron", "*")),
    )
    registro.registrar(
        EspecHerramienta(
            nombre="buscar_archivos",
            descripcion="Busca texto dentro de archivos del workspace del tenant.",
            esquema_entrada={
                "texto": {"tipo": "string", "descripcion": "Texto a buscar", "requerido": True},
                "ruta": {"tipo": "string", "descripcion": "Directorio relativo donde buscar", "requerido": False},
                "patron": {"tipo": "string", "descripcion": "Patrón glob de archivos", "requerido": False},
                "max_resultados": {"tipo": "integer", "descripcion": "Tope de resultados", "requerido": False},
            },
            riesgo="LOW", permisos=("archivos.leer",), idempotente=True,
        ),
        lambda ctx, args: buscar_archivos(ctx, args["texto"], args.get("ruta", "."),
                                          args.get("patron", "*.md"),
                                          args.get("max_resultados", 20)),
    )
