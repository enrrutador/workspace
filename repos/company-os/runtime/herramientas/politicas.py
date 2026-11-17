"""Motor de políticas determinista.

El riesgo se DECLARA por herramienta en código (EspecHerramienta.riesgo), no se
infiere por acción ni lo decide el LLM. El motor mapea (riesgo, perfil) a una
decisión: ALLOW, REQUIRE_APPROVAL o DENY.

Límites absolutos (ningún perfil los supera):
  - acceso cruzado entre tenants → siempre DENY
  - exfiltración de credenciales → siempre DENY
"""
from __future__ import annotations

from dataclasses import dataclass


class RIESGO:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Decision:
    ALLOW = "ALLOW"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    DENY = "DENY"


class PerfilAutonomia:
    CONSERVADOR = "conservador"
    ESTANDAR = "estandar"
    AUTONOMO = "autonomo"


# (perfil, riesgo) -> decisión. Ningún perfil permite CRITICAL sin freno.
_TABLA = {
    (PerfilAutonomia.CONSERVADOR, RIESGO.LOW): Decision.ALLOW,
    (PerfilAutonomia.CONSERVADOR, RIESGO.MEDIUM): Decision.REQUIRE_APPROVAL,
    (PerfilAutonomia.CONSERVADOR, RIESGO.HIGH): Decision.REQUIRE_APPROVAL,
    (PerfilAutonomia.CONSERVADOR, RIESGO.CRITICAL): Decision.DENY,
    (PerfilAutonomia.ESTANDAR, RIESGO.LOW): Decision.ALLOW,
    (PerfilAutonomia.ESTANDAR, RIESGO.MEDIUM): Decision.ALLOW,
    (PerfilAutonomia.ESTANDAR, RIESGO.HIGH): Decision.REQUIRE_APPROVAL,
    (PerfilAutonomia.ESTANDAR, RIESGO.CRITICAL): Decision.DENY,
    (PerfilAutonomia.AUTONOMO, RIESGO.LOW): Decision.ALLOW,
    (PerfilAutonomia.AUTONOMO, RIESGO.MEDIUM): Decision.ALLOW,
    (PerfilAutonomia.AUTONOMO, RIESGO.HIGH): Decision.ALLOW,
    (PerfilAutonomia.AUTONOMO, RIESGO.CRITICAL): Decision.REQUIRE_APPROVAL,
}


@dataclass(frozen=True)
class Veredicto:
    decision: str
    motivo: str
    riesgo: str


class MotorPoliticas:
    """Decide si una operación puede ejecutarse. Sin estado, sin LLM."""

    def __init__(self, perfil: str = PerfilAutonomia.ESTANDAR):
        if perfil not in (PerfilAutonomia.CONSERVADOR, PerfilAutonomia.ESTANDAR,
                          PerfilAutonomia.AUTONOMO):
            raise ValueError(f"perfil inválido: {perfil}")
        self.perfil = perfil

    def decidir(self, riesgo: str, cruce_tenant: bool = False,
               exfiltra_credencial: bool = False) -> Veredicto:
        # Límites absolutos: ningún perfil los supera.
        if cruce_tenant:
            return Veredicto(Decision.DENY, "acceso cruzado entre tenants", RIESGO.CRITICAL)
        if exfiltra_credencial:
            return Veredicto(Decision.DENY, "exfiltración de credenciales", RIESGO.CRITICAL)
        decision = _TABLA.get((self.perfil, riesgo))
        if decision is None:
            return Veredicto(Decision.DENY, f"riesgo desconocido: {riesgo}", RIESGO.CRITICAL)
        return Veredicto(decision, f"perfil {self.perfil} + riesgo {riesgo}", riesgo)
