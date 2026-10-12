"""Gateway central de herramientas: el único punto autorizado para ejecutarlas.

Flujo por cada llamada:

    contexto → registro → permiso del agente → política de riesgo →
    aprobación (si aplica) → ejecución → resultado estructurado → auditoría

Ningún agente ejecuta herramientas directamente: siempre pasa por acá.
Los secretos nunca llegan al modelo: la herramienta pide una capacidad y el
runtime usa la credencial internamente (las herramientas registradas no reciben
secretos en sus argumentos).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .aprobaciones import GestorAprobaciones
from .contexto import ContextoEjecucion
from .politicas import Decision, MotorPoliticas
from .registro import RegistroHerramientas


@dataclass
class ResultadoHerramienta:
    ok: bool
    datos: Any = None
    error: str = ""
    codigo: str = ""          # permission_denied | policy_denied | approval_required |
                              # tenant_violation | validation_error | tool_error | timeout
    reintentable: bool = False
    decision_politica: str = ""
    riesgo: str = ""
    aprobacion_id: str = ""
    duracion_ms: int = 0


# Códigos que indican "no lo intentes de nuevo igual".
_NO_REINTENTAR = {"permission_denied", "policy_denied", "tenant_violation",
                  "validation_error"}


class GatewayHerramientas:
    """Ejecuta herramientas gobernadas. Una instancia por proceso (inyectable)."""

    def __init__(self, registro: RegistroHerramientas,
                 politicas: MotorPoliticas | None = None,
                 aprobaciones: GestorAprobaciones | None = None,
                 auditoria=None,
                 herramientas_por_agente: dict[str, list[str]] | None = None):
        self.registro = registro
        self.politicas = politicas or MotorPoliticas()
        self.aprobaciones = aprobaciones or GestorAprobaciones()
        self.auditoria = auditoria
        # agent_id -> herramientas permitidas. Vacío = el agente no tiene herramientas.
        self.herramientas_por_agente = herramientas_por_agente or {}

    def permitir(self, agent_id: str, herramientas: list[str]) -> None:
        """Otorga herramientas a un agente (mínimo privilegio: explícito)."""
        self.herramientas_por_agente[agent_id] = list(herramientas)

    def _auditar(self, ctx: ContextoEjecucion, herramienta: str, args: dict,
                 resultado: ResultadoHerramienta) -> None:
        if self.auditoria is None:
            return
        try:
            self.auditoria.registrar(
                agente=ctx.agent_id,
                modelo="",
                tarea=f"[herramienta] {herramienta}",
                respuesta=str(resultado.datos)[:2000] if resultado.ok else resultado.error[:500],
                herramienta=herramienta,
                riesgo=resultado.riesgo,
                decision_politica=resultado.decision_politica,
                aprobacion_id=resultado.aprobacion_id,
                codigo_resultado=resultado.codigo,
                duracion_ms=resultado.duracion_ms,
                tenant_id=ctx.tenant_id,
                execution_id=ctx.execution_id,
                parent_execution_id=ctx.parent_execution_id,
            )
        except TypeError:
            # auditoría vieja sin kwargs nuevos: no romper
            pass

    def ejecutar(self, ctx: ContextoEjecucion, nombre: str, args: dict,
                 aprobacion_id: str = "") -> ResultadoHerramienta:
        t0 = time.time()
        entrada = self.registro.obtener(nombre)
        if entrada is None:
            return self._fallo(ctx, nombre, args, "", "", "tool_error",
                               f"herramienta desconocida: {nombre}", t0)
        espec = entrada.espec

        # 1. Permiso del agente (mínimo privilegio).
        permitidas = self.herramientas_por_agente.get(ctx.agent_id, [])
        if nombre not in permitidas:
            return self._fallo(ctx, nombre, args, espec.riesgo, "", "permission_denied",
                               f"el agente '{ctx.agent_id}' no tiene permiso para '{nombre}'", t0)

        # 2. Validación de esquema.
        ok, err = espec.validar_argumentos(args or {})
        if not ok:
            return self._fallo(ctx, nombre, args, espec.riesgo, "", "validation_error", err, t0)

        # 3. Aislamiento de tenant: la herramienta solo ve su tenant.
        if espec.solo_tenant and not ctx.tenant_id:
            return self._fallo(ctx, nombre, args, espec.riesgo, "", "tenant_violation",
                               "contexto sin tenant", t0)

        # 4. Política de riesgo (el riesgo lo declara la herramienta, no el LLM).
        veredicto = self.politicas.decidir(espec.riesgo)
        if veredicto.decision == Decision.DENY:
            return self._fallo(ctx, nombre, args, espec.riesgo, veredicto.decision,
                               "policy_denied",
                               f"política DENY: {veredicto.motivo}", t0)

        # 5. Aprobación si la política la exige.
        if veredicto.decision == Decision.REQUIRE_APPROVAL or espec.requiere_aprobacion:
            if not aprobacion_id:
                ap = self.aprobaciones.solicitar(ctx, nombre, nombre, espec.riesgo, args)
                r = ResultadoHerramienta(
                    ok=False, codigo="approval_required", reintentable=False,
                    error=f"requiere aprobación humana (id: {ap.id})",
                    decision_politica=veredicto.decision, riesgo=espec.riesgo,
                    aprobacion_id=ap.id, duracion_ms=self._ms(t0))
                self._auditar(ctx, nombre, args, r)
                return r
            ok_ap, err_ap = self.aprobaciones.validar_y_consumir(
                aprobacion_id, ctx, nombre, args)
            if not ok_ap:
                return self._fallo(ctx, nombre, args, espec.riesgo, veredicto.decision,
                                   "policy_denied", f"aprobación inválida: {err_ap}", t0)

        # 6. Ejecución.
        try:
            datos = entrada.funcion(ctx, args or {})
        except Exception as e:  # noqa: BLE001 - el gateway nunca propaga excepciones
            codigo = "tool_error"
            mensaje = str(e)
            if "ViolacionSandbox" in type(e).__name__ or "no permitid" in mensaje:
                codigo = "tenant_violation"
            return self._fallo(ctx, nombre, args, espec.riesgo, veredicto.decision,
                               codigo, mensaje[:500], t0,
                               reintentable=codigo not in _NO_REINTENTAR)
        r = ResultadoHerramienta(
            ok=True, datos=datos, decision_politica=veredicto.decision,
            riesgo=espec.riesgo, aprobacion_id=aprobacion_id,
            duracion_ms=self._ms(t0))
        self._auditar(ctx, nombre, args, r)
        return r

    @staticmethod
    def _ms(t0: float) -> int:
        return int((time.time() - t0) * 1000)

    def _fallo(self, ctx, nombre, args, riesgo, decision, codigo, error, t0,
               reintentable=False) -> ResultadoHerramienta:
        r = ResultadoHerramienta(ok=False, error=error, codigo=codigo,
                                 reintentable=reintentable,
                                 decision_politica=decision, riesgo=riesgo,
                                 duracion_ms=self._ms(t0))
        self._auditar(ctx, nombre, args, r)
        return r
