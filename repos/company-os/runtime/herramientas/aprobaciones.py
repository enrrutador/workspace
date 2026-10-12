"""Modelo explícito de aprobaciones.

Una aprobación es específica (operación + argumentos exactos vía hash), temporal
(expira) y de un solo uso (se consume al ejecutarse). Estados: PENDIENTE,
APROBADA, RECHAZADA, EXPIRADA, CONSUMIDA.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field

from .contexto import ContextoEjecucion


class EstadoAprobacion:
    PENDIENTE = "PENDIENTE"
    APROBADA = "APROBADA"
    RECHAZADA = "RECHAZADA"
    EXPIRADA = "EXPIRADA"
    CONSUMIDA = "CONSUMIDA"


def hash_argumentos(args: dict) -> str:
    """Hash canónico de los argumentos: la aprobación vale solo para estos."""
    canon = json.dumps(args, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:32]


@dataclass
class Aprobacion:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    tenant_id: str = ""
    execution_id: str = ""
    agent_id: str = ""
    herramienta: str = ""
    operacion: str = ""
    riesgo: str = ""
    argumentos_hash: str = ""
    solicitante: str = ""
    aprobador: str = ""
    creada_en: float = field(default_factory=time.time)
    expira_en: float = 0
    estado: str = EstadoAprobacion.PENDIENTE

    def vigente(self) -> bool:
        return self.estado == EstadoAprobacion.APROBADA and time.time() < self.expira_en


class GestorAprobaciones:
    """Crea y valida aprobaciones. En memoria (el estado vive en el proceso)."""

    def __init__(self, ttl_segundos: int = 3600):
        self.ttl = ttl_segundos
        self._aprobaciones: dict[str, Aprobacion] = {}

    def solicitar(self, ctx: ContextoEjecucion, herramienta: str, operacion: str,
                  riesgo: str, argumentos: dict) -> Aprobacion:
        ap = Aprobacion(
            tenant_id=ctx.tenant_id,
            execution_id=ctx.execution_id,
            agent_id=ctx.agent_id,
            herramienta=herramienta,
            operacion=operacion,
            riesgo=riesgo,
            argumentos_hash=hash_argumentos(argumentos),
            solicitante=ctx.agent_id,
            expira_en=time.time() + self.ttl,
        )
        self._aprobaciones[ap.id] = ap
        return ap

    def aprobar(self, aprobacion_id: str, aprobador: str,
                tenant_id: str) -> Aprobacion | None:
        ap = self._aprobaciones.get(aprobacion_id)
        if ap is None or ap.tenant_id != tenant_id:
            return None
        if ap.estado != EstadoAprobacion.PENDIENTE:
            return None
        if time.time() >= ap.expira_en:
            ap.estado = EstadoAprobacion.EXPIRADA
            return None
        ap.estado = EstadoAprobacion.APROBADA
        ap.aprobador = aprobador
        return ap

    def rechazar(self, aprobacion_id: str, aprobador: str, tenant_id: str) -> bool:
        ap = self._aprobaciones.get(aprobacion_id)
        if ap is None or ap.tenant_id != tenant_id:
            return False
        if ap.estado != EstadoAprobacion.PENDIENTE:
            return False
        ap.estado = EstadoAprobacion.RECHAZADA
        ap.aprobador = aprobador
        return True

    def validar_y_consumir(self, aprobacion_id: str, ctx: ContextoEjecucion,
                           herramienta: str, argumentos: dict) -> tuple[bool, str]:
        """Verifica que la aprobación sea válida para ESTA operación y la consume.

        Falla cerrado ante: id inexistente, tenant distinto, expirada, rechazada,
        ya consumida, herramienta distinta o argumentos distintos (hash).
        """
        ap = self._aprobaciones.get(aprobacion_id)
        if ap is None:
            return False, "aprobación inexistente"
        if ap.tenant_id != ctx.tenant_id:
            return False, "la aprobación es de otro tenant"
        if ap.estado == EstadoAprobacion.CONSUMIDA:
            return False, "aprobación ya consumida (un solo uso)"
        if ap.estado != EstadoAprobacion.APROBADA:
            return False, f"aprobación en estado {ap.estado}"
        if time.time() >= ap.expira_en:
            ap.estado = EstadoAprobacion.EXPIRADA
            return False, "aprobación expirada"
        if ap.herramienta != herramienta:
            return False, "la aprobación es para otra herramienta"
        if ap.argumentos_hash != hash_argumentos(argumentos):
            return False, "los argumentos no coinciden con los aprobados"
        ap.estado = EstadoAprobacion.CONSUMIDA
        return True, ""

    def pendiente(self, aprobacion_id: str) -> Aprobacion | None:
        return self._aprobaciones.get(aprobacion_id)
