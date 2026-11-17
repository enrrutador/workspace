"""Herramientas reales gobernadas para los agentes.

Capa de ejecución alrededor del runtime existente (no lo reemplaza):

    Agente → Gateway → Registro → Política → Aprobación → Herramienta → Auditoría

Todo lo que un agente ejecuta pasa por el gateway. Nada ejecuta herramientas
directamente. Los secretos nunca llegan al prompt del modelo.
"""
from .contexto import ContextoEjecucion
from .registro import RegistroHerramientas, EspecHerramienta, RIESGOS, REGISTRO_GLOBAL
from .politicas import MotorPoliticas, PerfilAutonomia, Decision, RIESGO
from .aprobaciones import GestorAprobaciones, EstadoAprobacion
from .gateway import GatewayHerramientas, ResultadoHerramienta

__all__ = [
    "ContextoEjecucion",
    "RegistroHerramientas",
    "EspecHerramienta",
    "RIESGOS",
    "REGISTRO_GLOBAL",
    "MotorPoliticas",
    "PerfilAutonomia",
    "Decision",
    "RIESGO",
    "GestorAprobaciones",
    "EstadoAprobacion",
    "GatewayHerramientas",
    "ResultadoHerramienta",
]
