"""Registro de herramientas: metadata confiable declarada en código.

Ninguna metadata de herramienta viene del modelo. Cada herramienta declara su
nombre, descripción, esquema de entrada, riesgo y permisos. El gateway solo
ejecuta herramientas registradas.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


RIESGOS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")


@dataclass(frozen=True)
class EspecHerramienta:
    """Especificación de una herramienta real."""

    nombre: str
    descripcion: str
    esquema_entrada: dict  # {"param": {"tipo": "string", "descripcion": str, "requerido": bool}}
    riesgo: str = "LOW"
    permisos: tuple = ()
    solo_tenant: bool = True
    destructiva: bool = False
    idempotente: bool = True
    requiere_aprobacion: bool = False

    def __post_init__(self):
        if self.riesgo not in RIESGOS:
            raise ValueError(f"riesgo inválido: {self.riesgo}")

    def esquema_openai(self) -> dict:
        """Convierte el esquema interno al formato tools de chat.completions."""
        props, requeridos = {}, []
        for nombre, spec in self.esquema_entrada.items():
            props[nombre] = {
                "type": spec.get("tipo", "string"),
                "description": spec.get("descripcion", ""),
            }
            if spec.get("requerido"):
                requeridos.append(nombre)
        return {
            "type": "function",
            "function": {
                "name": self.nombre,
                "description": self.descripcion,
                "parameters": {
                    "type": "object",
                    "properties": props,
                    "required": requeridos,
                    "additionalProperties": False,
                },
            },
        }

    def validar_argumentos(self, args: dict) -> tuple[bool, str]:
        """Valida argumentos contra el esquema. Devuelve (ok, error)."""
        if not isinstance(args, dict):
            return False, "los argumentos deben ser un objeto"
        for nombre, spec in self.esquema_entrada.items():
            if spec.get("requerido") and nombre not in args:
                return False, f"falta el parámetro requerido: {nombre}"
        conocidos = set(self.esquema_entrada)
        for nombre in args:
            if nombre not in conocidos:
                return False, f"parámetro desconocido: {nombre}"
        return True, ""


@dataclass
class _Entrada:
    espec: EspecHerramienta
    funcion: Callable


class RegistroHerramientas:
    """Catálogo de herramientas disponibles. Una instancia global por defecto."""

    def __init__(self):
        self._herramientas: dict[str, _Entrada] = {}

    def registrar(self, espec: EspecHerramienta, funcion: Callable) -> None:
        if espec.nombre in self._herramientas:
            raise ValueError(f"herramienta duplicada: {espec.nombre}")
        self._herramientas[espec.nombre] = _Entrada(espec, funcion)

    def obtener(self, nombre: str) -> _Entrada | None:
        return self._herramientas.get(nombre)

    def nombres(self) -> list:
        return sorted(self._herramientas)

    def esquemas_openai(self, nombres: list | None = None) -> list:
        """Esquemas listos para chat.completions.create(tools=...)."""
        sel = nombres or self.nombres()
        return [self._herramientas[n].espec.esquema_openai()
                for n in sel if n in self._herramientas]


REGISTRO_GLOBAL = RegistroHerramientas()
